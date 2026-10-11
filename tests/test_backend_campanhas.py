import unittest

try:
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from sqlalchemy import create_engine

    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas, normalizar_url_banco
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - backend opcional fora do CI
    DEPENDENCIAS = False


class MJFalso:
    def __init__(self):
        self.chamadas = []

    def responder(self, texto, historico=None):
        self.chamadas.append((texto, list(historico or [])))
        return f"MJ: {texto}"


class MJComFalha:
    def responder(self, texto, historico=None):
        raise RuntimeError("provedor fora do ar")


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class BackendCampanhasTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        self.repo = RepositorioCampanhas(engine=engine)
        self.mj = MJFalso()
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        backend_app.app.dependency_overrides[backend_app.obter_mj] = lambda: self.mj
        self.client = TestClient(backend_app.app)
        self.jogador = {"X-Jogador-Id": "jogador-a"}

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def test_criar_listar_e_obter_campanha(self):
        criada = self.client.post("/v1/campanhas", json={"titulo": "Ruínas de Ravenloft"}, headers=self.jogador)
        self.assertEqual(criada.status_code, 201)
        campanha = criada.json()
        self.assertEqual(campanha["titulo"], "Ruínas de Ravenloft")
        self.assertEqual(campanha["total_mensagens"], 0)

        lista = self.client.get("/v1/campanhas", headers=self.jogador).json()
        self.assertEqual([c["id"] for c in lista], [campanha["id"]])

        detalhe = self.client.get(f"/v1/campanhas/{campanha['id']}", headers=self.jogador).json()
        self.assertEqual(detalhe["mensagens"], [])

    def test_titulo_vazio_usa_padrao(self):
        campanha = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()
        self.assertEqual(campanha["titulo"], "Campanha sem título")

    def test_mensagens_persistem_e_alimentam_historico(self):
        cid = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()["id"]
        r1 = self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": "Entro na taverna."}, headers=self.jogador)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()["resposta"], "MJ: Entro na taverna.")
        self.assertEqual(r1.json()["campanha"]["total_mensagens"], 2)

        self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": "Peço uma bebida."}, headers=self.jogador)
        _, historico = self.mj.chamadas[-1]
        self.assertEqual(historico[0]["role"], "system")
        self.assertIn("nenhum personagem está cadastrado", historico[0]["content"])
        self.assertEqual(historico[1:], [
            {"role": "user", "content": "Entro na taverna."},
            {"role": "assistant", "content": "MJ: Entro na taverna."},
        ])

        detalhe = self.client.get(f"/v1/campanhas/{cid}", headers=self.jogador).json()
        self.assertEqual([m["papel"] for m in detalhe["mensagens"]], ["user", "assistant", "user", "assistant"])
        self.assertEqual(detalhe["ultima_mensagem"], "MJ: Peço uma bebida.")

    def test_historico_enviado_ao_mj_e_limitado(self):
        cid = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()["id"]
        limite_original = backend_app.HISTORICO_MAX
        backend_app.HISTORICO_MAX = 2
        try:
            for i in range(3):
                self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": f"m{i}"}, headers=self.jogador)
        finally:
            backend_app.HISTORICO_MAX = limite_original
        _, historico = self.mj.chamadas[-1]
        self.assertEqual(historico[0]["role"], "system")
        self.assertEqual([h["content"] for h in historico[1:]], ["m1", "MJ: m1"])

    def test_campanhas_isoladas_por_jogador(self):
        cid = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()["id"]
        outro = {"X-Jogador-Id": "jogador-b"}
        self.assertEqual(self.client.get("/v1/campanhas", headers=outro).json(), [])
        self.assertEqual(self.client.get(f"/v1/campanhas/{cid}", headers=outro).status_code, 404)
        self.assertEqual(self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": "oi"}, headers=outro).status_code, 404)
        self.assertEqual(self.client.delete(f"/v1/campanhas/{cid}", headers=outro).status_code, 404)

    def test_renomear_e_apagar(self):
        cid = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()["id"]
        renomeada = self.client.patch(f"/v1/campanhas/{cid}", json={"titulo": "Forja do Artífice"}, headers=self.jogador)
        self.assertEqual(renomeada.json()["titulo"], "Forja do Artífice")
        self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": "oi"}, headers=self.jogador)
        self.assertEqual(self.client.delete(f"/v1/campanhas/{cid}", headers=self.jogador).status_code, 204)
        self.assertEqual(self.client.get(f"/v1/campanhas/{cid}", headers=self.jogador).status_code, 404)

    def test_lista_ordenada_pela_atividade_mais_recente(self):
        a = self.client.post("/v1/campanhas", json={"titulo": "A"}, headers=self.jogador).json()["id"]
        b = self.client.post("/v1/campanhas", json={"titulo": "B"}, headers=self.jogador).json()["id"]
        self.client.post(f"/v1/campanhas/{a}/mensagens", json={"mensagem": "retomando"}, headers=self.jogador)
        ids = [c["id"] for c in self.client.get("/v1/campanhas", headers=self.jogador).json()]
        self.assertEqual(ids, [a, b])

    def test_falha_do_provedor_nao_grava_mensagem(self):
        backend_app.app.dependency_overrides[backend_app.obter_mj] = lambda: MJComFalha()
        cid = self.client.post("/v1/campanhas", json={}, headers=self.jogador).json()["id"]
        resposta = self.client.post(f"/v1/campanhas/{cid}/mensagens", json={"mensagem": "oi"}, headers=self.jogador)
        self.assertEqual(resposta.status_code, 502)
        self.assertEqual(self.client.get(f"/v1/campanhas/{cid}", headers=self.jogador).json()["mensagens"], [])

    def test_jogador_id_invalido_e_rejeitado(self):
        resposta = self.client.get("/v1/campanhas", headers={"X-Jogador-Id": "nada valido!"})
        self.assertEqual(resposta.status_code, 422)

    def test_endpoint_legado_persiste_sessao(self):
        resposta = self.client.post("/v1/mj/mensagem", json={"sessao_id": "campanha-legada", "mensagem": "Olá"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["resposta"], "MJ: Olá")
        detalhe = self.client.get("/v1/campanhas/campanha-legada").json()
        self.assertEqual(detalhe["total_mensagens"], 2)
        self.assertEqual(self.client.delete("/v1/mj/sessoes/campanha-legada").status_code, 204)
        self.assertEqual(self.client.get("/v1/campanhas/campanha-legada").status_code, 404)

    def test_status_continua_online(self):
        self.assertEqual(self.client.get("/v1/status").json()["status"], "online")

    def test_url_do_render_usa_psycopg(self):
        self.assertEqual(normalizar_url_banco("postgres://u:p@h/db"), "postgresql+psycopg://u:p@h/db")
        self.assertEqual(normalizar_url_banco("postgresql://u:p@h/db"), "postgresql+psycopg://u:p@h/db")
        self.assertEqual(normalizar_url_banco("sqlite:///x.db"), "sqlite:///x.db")


if __name__ == "__main__":
    unittest.main()
