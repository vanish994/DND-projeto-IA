"""O bloco derivado da ficha é calculado pelo servidor, nunca no cliente."""
import unittest

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover
    DEPENDENCIAS = False


GUERREIRO = {
    "nome": "Vex", "especie": "humano", "classe": "guerreiro", "nivel": 1,
    "metodo_atributos": "matriz_padrao",
    "atributos": {"forca": 15, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8},
    "antecedente": "soldado", "aumentos_antecedente": {"forca": 2, "constituicao": 1},
}

MAGO = {
    "nome": "Niv", "especie": "elfo", "classe": "mago", "nivel": 1,
    "metodo_atributos": "matriz_padrao",
    "atributos": {"forca": 8, "destreza": 14, "constituicao": 13, "inteligencia": 15, "sabedoria": 12, "carisma": 10},
    "antecedente": "sabio", "aumentos_antecedente": {"inteligencia": 2, "constituicao": 1},
    "pericias_classe": ["arcanismo", "historia"],
}


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class BlocoFichaTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-ficha"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Ficha"}, headers=self.headers).json()["id"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def criar(self, payload):
        resposta = self.client.post(f"/v1/campanhas/{self.cid}/personagens", json=payload, headers=self.headers)
        self.assertEqual(resposta.status_code, 201, resposta.text)
        return resposta.json()

    def equipar(self, personagem_id, corpo):
        return self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{personagem_id}/equipamento",
            headers=self.headers, json=corpo,
        )

    def test_ficha_devolve_bloco_derivado(self):
        personagem = self.criar(GUERREIRO)
        bloco = personagem["bloco"]
        self.assertEqual(bloco["fonte"], "rule_engine")
        self.assertEqual(bloco["ca"], 12)  # 10 + Destreza +2
        self.assertEqual(bloco["iniciativa"], 2)
        self.assertEqual(bloco["bonus_proficiencia"], 2)
        self.assertTrue(bloco["arma"]["desarmado"])
        self.assertEqual(bloco["arma"]["ataque"], 5)  # proficiência +2 e Força +3
        self.assertIsNone(bloco["conjuracao"])

    def test_armadura_e_escudo_compõem_a_ca(self):
        personagem = self.criar(GUERREIRO)
        resposta = self.equipar(personagem["id"], {"armadura": "Cota de Malha", "escudo": True})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        bloco = resposta.json()["bloco"]
        self.assertEqual(bloco["ca"], 18)  # 16 da cota de malha + 2 do escudo
        self.assertEqual(bloco["armadura"]["categoria"], "pesada")

    def test_arma_do_catalogo_traz_ataque_e_dano(self):
        personagem = self.criar(GUERREIRO)
        resposta = self.equipar(personagem["id"], {"arma": "Espada Longa"})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        arma = resposta.json()["bloco"]["arma"]
        self.assertEqual(arma["nome"], "Espada Longa")
        self.assertEqual(arma["atributo"], "forca")
        self.assertEqual(arma["ataque"], 5)
        self.assertEqual(arma["dado"], "1d8")
        self.assertEqual(arma["expressao_dano"], "1d8 + 3")
        self.assertEqual(arma["tipo"], "cortante")
        self.assertTrue(arma["proficiente"])

    def test_arma_de_municao_usa_destreza(self):
        personagem = self.criar(GUERREIRO)
        resposta = self.equipar(personagem["id"], {"arma": "Arco Curto"})
        self.assertEqual(resposta.status_code, 200, resposta.text)
        arma = resposta.json()["bloco"]["arma"]
        self.assertEqual(arma["atributo"], "destreza")
        self.assertEqual(arma["ataque"], 4)  # proficiência +2 e Destreza +2
        self.assertTrue(arma["a_distancia"])
        self.assertEqual(arma["alcance_pes"], 79)

    def test_conjurador_recebe_cd_e_ataque_magico(self):
        personagem = self.criar(MAGO)
        conjuracao = personagem["bloco"]["conjuracao"]
        self.assertEqual(conjuracao["atributo"], "inteligencia")
        self.assertEqual(conjuracao["modificador"], 3)  # Inteligência 17
        self.assertEqual(conjuracao["cd"], 13)  # 8 + proficiência +2 + Inteligência +3
        self.assertEqual(conjuracao["ataque"], 5)

    def test_pericias_e_salvaguardas_marcam_proficiencia(self):
        personagem = self.criar(MAGO)
        bloco = personagem["bloco"]
        pericias = {linha["pericia"]: linha for linha in bloco["pericias"]}
        self.assertTrue(pericias["arcanismo"]["proficiente"])
        self.assertEqual(pericias["arcanismo"]["atributo"], "inteligencia")
        self.assertEqual(pericias["arcanismo"]["total"], 5)  # +3 de Inteligência e +2 de proficiência
        self.assertFalse(pericias["atletismo"]["proficiente"])
        self.assertEqual(pericias["atletismo"]["total"], -1)
        salvaguardas = {linha["atributo"]: linha for linha in bloco["salvaguardas"]}
        self.assertTrue(salvaguardas["inteligencia"]["proficiente"])
        self.assertTrue(salvaguardas["sabedoria"]["proficiente"])
        self.assertEqual(salvaguardas["inteligencia"]["total"], 5)
        self.assertFalse(salvaguardas["forca"]["proficiente"])

    def test_catalogo_de_equipamento_expõe_os_catálogos_oficiais(self):
        resposta = self.client.get("/v1/catalogo/equipamento", headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertIn("Espada Longa", corpo["armas"])
        self.assertEqual(corpo["armas"]["Espada Longa"]["dano"], "1d8")
        self.assertEqual(corpo["armaduras"]["Cota de Malha"]["ca"], 16)
        self.assertEqual(corpo["pericias_atributo"]["furtividade"], "destreza")

    def test_bloco_acompanha_ajuste_de_pontos_de_vida(self):
        personagem = self.criar(GUERREIRO)
        resposta = self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{personagem['id']}",
            headers=self.headers, json={"ajuste_pv": -1},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["pv_atual"], personagem["pv_maximo"] - 1)
        self.assertIn("bloco", resposta.json())


if __name__ == "__main__":
    unittest.main()
