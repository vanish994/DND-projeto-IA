import unittest

from rule_engine import ANTECEDENTES, criar_personagem, ficha_personagem
from rule_engine.feats import DARK_GIFT_FEATS

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover
    DEPENDENCIAS = False

BASE = {"forca": 8, "destreza": 14, "constituicao": 13, "inteligencia": 15, "sabedoria": 12, "carisma": 10}


def fatos(**extra):
    dados = {"name": "Vex", "species": "elfo", "class": "mago", "level": 1, "ability_scores": dict(BASE)}
    dados.update(extra)
    return dados


class AntecedentesTests(unittest.TestCase):
    def test_catalogo_tem_16_do_phb_e_4_de_ravenloft(self):
        fontes = [dados["fonte"] for dados in ANTECEDENTES.values()]
        self.assertEqual(sum("Livro do Jogador" in f for f in fontes), 16)
        self.assertEqual(sum("Ravenloft" in f for f in fontes), 4)
        for dados in ANTECEDENTES.values():
            self.assertEqual(len(dados["atributos"]), 3)
            self.assertEqual(len(dados["pericias"]), 2)
            self.assertEqual(dados["equipamento"]["B"], "50 PO")

    def test_sabio_aplica_mais_dois_mais_um_e_iniciado_em_magia(self):
        p = criar_personagem(fatos(background="sabio", background_increases={"inteligencia": 2, "constituicao": 1}))
        self.assertEqual(p.atributos["inteligencia"], 17)
        self.assertEqual(p.atributos["constituicao"], 14)
        self.assertIn("iniciado_em_magia", p.talentos)

    def test_tres_mais_um_e_aceito(self):
        p = criar_personagem(fatos(background="sabio", background_increases={"inteligencia": 1, "constituicao": 1, "sabedoria": 1}))
        self.assertEqual(p.atributos["sabedoria"], 13)

    def test_aumento_fora_do_antecedente_e_bloqueado(self):
        with self.assertRaises(ValueError):
            criar_personagem(fatos(background="sabio", background_increases={"forca": 2, "inteligencia": 1}))

    def test_aumentos_explicitamente_vazios_sao_rejeitados(self):
        with self.assertRaises(ValueError):
            criar_personagem(fatos(background="sabio", background_increases={}))

    def test_distribuicao_invalida_e_bloqueada(self):
        with self.assertRaises(ValueError):
            criar_personagem(fatos(background="sabio", background_increases={"inteligencia": 3}))

    def test_limite_de_20(self):
        atributos = dict(BASE, inteligencia=19)
        with self.assertRaises(ValueError):
            criar_personagem(fatos(ability_scores=atributos, background="sabio", background_increases={"inteligencia": 2, "sabedoria": 1}))

    def test_medium_espiritual_exige_dadiva_sombria(self):
        with self.assertRaises(ValueError):
            criar_personagem(fatos(background="medium_espiritual"))
        p = criar_personagem(fatos(background="medium_espiritual", background_feat="sussurros_reunidos"))
        self.assertIn("sussurros_reunidos", p.talentos)

    def test_olho_agucado_tem_efeitos_catalogados(self):
        from rule_engine.feats import FEATS
        efeitos = FEATS["olho_agucado"]["efeitos"]
        self.assertIn("vantagem_em_teste_de_atributo_da_acao_procurar_ou_estudar", efeitos)
        self.assertIn("usos_iguais_bonus_proficiencia_por_descanso_longo", efeitos)
        self.assertIn("uso_gasto_somente_em_sucesso", efeitos)

    def test_sobrevivente_tem_efeitos_catalogados(self):
        from rule_engine.feats import FEATS
        efeitos = FEATS["sobrevivente"]["efeitos"]
        self.assertEqual(len(efeitos), 2)
        self.assertTrue(efeitos[0].startswith("hipervigilancia"))
        self.assertTrue(efeitos[1].startswith("controlar_se"))

    def test_investigador_aceita_olho_agucado_ou_dadiva(self):
        self.assertIn("olho_agucado", criar_personagem(fatos(background="investigador")).talentos)
        p = criar_personagem(fatos(background="investigador", background_feat="observadores"))
        self.assertIn("observadores", p.talentos)
        with self.assertRaises(ValueError):
            criar_personagem(fatos(background="sabio", background_feat="observadores"))

    def test_dadiva_sombria_exige_contexto_ravenloft(self):
        from rule_engine.feats import validar_talento
        self.assertEqual(validar_talento({"talento": "sombra_viva"})["motivo"], "requer_campanha_ravenloft")
        self.assertEqual(validar_talento({"talento": "sombra_viva", "campanha_ravenloft": True})["resultado"], "disponivel")

    def test_escolha_da_lista_de_iniciado_em_magia_persiste(self):
        p = criar_personagem(fatos(background="sabio", background_feat="iniciado_em_magia:mago"))
        self.assertEqual(ficha_personagem(p)["escolhas_talentos"]["iniciado_em_magia"], "mago")

    def test_dadivas_sombrias_catalogadas(self):
        self.assertEqual(len(DARK_GIFT_FEATS), 9)

    def test_ficha_derivada(self):
        p = criar_personagem(fatos(background="fazendeiro", background_increases={"constituicao": 2, "forca": 1}))
        ficha = ficha_personagem(p)
        self.assertEqual(ficha["modificadores"]["constituicao"], 2)
        self.assertEqual(ficha["pv_maximo"], 6 + 2 + 2)  # mago d6 + CON + Vigoroso
        self.assertEqual(ficha["pericias"], ["lidar_com_animais", "natureza"])
        self.assertEqual(ficha["bonus_proficiencia"], 2)


class MJFalso:
    def __init__(self):
        self.chamadas = []

    def responder(self, texto, historico=None):
        self.chamadas.append((texto, list(historico or [])))
        return "ok"


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class BackendPersonagensTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        self.mj = MJFalso()
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        backend_app.app.dependency_overrides[backend_app.obter_mj] = lambda: self.mj
        self.client = TestClient(backend_app.app)
        self.h = {"X-Jogador-Id": "jogador-a"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Teste"}, headers=self.h).json()["id"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def payload(self, **extra):
        dados = {
            "nome": "Vex", "especie": "elfo", "classe": "mago", "metodo_atributos": "matriz_padrao",
            "atributos": {"forca": 8, "destreza": 14, "constituicao": 13, "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "antecedente": "sabio", "aumentos_antecedente": {"inteligencia": 2, "constituicao": 1},
        }
        dados.update(extra)
        return dados

    def url(self, sufixo=""):
        return f"/v1/campanhas/{self.cid}/personagens{sufixo}"

    def test_catalogo(self):
        cat = self.client.get("/v1/catalogo/personagens").json()
        self.assertEqual(len(cat["antecedentes"]), 20)
        self.assertEqual(cat["matriz_padrao"], [15, 14, 13, 12, 10, 8])

    def test_crud_completo(self):
        r = self.client.post(self.url(), json=self.payload(), headers=self.h)
        self.assertEqual(r.status_code, 201, r.text)
        p = r.json()
        self.assertEqual(p["atributos"]["inteligencia"], 17)
        self.assertEqual(p["pv_atual"], p["pv_maximo"])
        self.assertEqual(len(self.client.get(self.url(), headers=self.h).json()), 1)
        r = self.client.patch(self.url(f"/{p['id']}"), json={"ajuste_pv": -1}, headers=self.h)
        self.assertEqual(r.json()["pv_atual"], p["pv_maximo"] - 1)
        r = self.client.patch(self.url(f"/{p['id']}"), json={"ajuste_pv": -1}, headers=self.h)
        self.assertEqual(r.json()["pv_atual"], p["pv_maximo"] - 2)
        r = self.client.patch(self.url(f"/{p['id']}"), json={"ajuste_pv": 100}, headers=self.h)
        self.assertEqual(r.json()["pv_atual"], p["pv_maximo"])
        r = self.client.put(self.url(f"/{p['id']}"), json=self.payload(nome="Vex II"), headers=self.h)
        self.assertEqual(r.json()["nome"], "Vex II")
        self.assertEqual(self.client.delete(self.url(f"/{p['id']}"), headers=self.h).status_code, 204)
        self.assertEqual(self.client.get(self.url(f"/{p['id']}"), headers=self.h).status_code, 404)

    def test_validacao_pelo_motor(self):
        r = self.client.post(self.url(), json=self.payload(atributos={"forca": 15, "destreza": 15, "constituicao": 15, "inteligencia": 15, "sabedoria": 15, "carisma": 15}), headers=self.h)
        self.assertEqual(r.status_code, 422)
        r = self.client.post(self.url(), json=self.payload(metodo_atributos="compra_pontos", atributos={"forca": 15, "destreza": 15, "constituicao": 15, "inteligencia": 10, "sabedoria": 8, "carisma": 8}), headers=self.h)
        self.assertEqual(r.status_code, 422)
        r = self.client.post(self.url(), json=self.payload(antecedente="inexistente"), headers=self.h)
        self.assertEqual(r.status_code, 422)

    def test_outro_jogador_nao_ve(self):
        self.client.post(self.url(), json=self.payload(), headers=self.h)
        r = self.client.get(self.url(), headers={"X-Jogador-Id": "jogador-b"})
        self.assertEqual(r.status_code, 404)

    def test_apagar_campanha_remove_personagens(self):
        self.client.post(self.url(), json=self.payload(), headers=self.h)
        self.client.delete(f"/v1/campanhas/{self.cid}", headers=self.h)
        self.assertEqual(self.repo.listar_personagens("jogador-a", self.cid), None)

    def test_mj_recebe_resumo_do_grupo(self):
        self.client.post(self.url(), json=self.payload(), headers=self.h)
        self.client.post(f"/v1/campanhas/{self.cid}/mensagens", json={"mensagem": "Olá"}, headers=self.h)
        _, historico = self.mj.chamadas[-1]
        self.assertEqual(historico[0]["role"], "system")
        self.assertIn("FICHA AUTORITATIVA #1", historico[0]["content"])
        self.assertIn("nome=Vex", historico[0]["content"])
        self.assertIn("classe=mago", historico[0]["content"])
