import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend import app as backend_app
from backend.persistencia import RepositorioCampanhas
from rule_engine.character import criar_personagem, ficha_personagem
from rule_engine.spellcasting import (
    listar_magias_artifice,
    progresso_artifice,
    validar_escolhas_artifice,
)
from rule_engine.spells import obter_magia


class ProficienciasClasseTests(unittest.TestCase):
    def fatos(self, **extra):
        dados = {
            "name": "Vex",
            "species": "draconato",
            "class": "artifice",
            "level": 1,
            "ability_scores": {
                "forca": 8, "destreza": 13, "constituicao": 10,
                "inteligencia": 16, "sabedoria": 12, "carisma": 16,
            },
            "background": "investigador",
            "class_skill_proficiencies": ["arcanismo", "historia"],
            "artisan_tool_proficiency": "Ferramentas de Carpinteiro",
        }
        dados.update(extra)
        return dados

    def test_artifice_exige_quantidade_correta_de_pericias(self):
        with self.assertRaisesRegex(ValueError, "exatamente 2 perícias"):
            criar_personagem(self.fatos(class_skill_proficiencies=["arcanismo"]))

    def test_artifice_nao_aceita_pericia_fora_da_lista(self):
        with self.assertRaisesRegex(ValueError, "não disponível para esta classe"):
            criar_personagem(self.fatos(class_skill_proficiencies=["arcanismo", "atletismo"]))

    def test_ficha_combina_pericias_de_classe_e_antecedente_sem_duplicar(self):
        personagem = criar_personagem(self.fatos(
            class_skill_proficiencies=["investigacao", "arcanismo"]
        ))
        ficha = ficha_personagem(personagem)
        self.assertEqual(ficha["pericias_classe"], ["arcanismo", "investigacao"])
        self.assertEqual(ficha["pericias"].count("investigacao"), 1)
        self.assertIn("intuicao", ficha["pericias"])
        self.assertEqual(ficha["proficiencias_salvaguarda"], ["constituicao", "inteligencia"])
        self.assertFalse(ficha["proficiencias_pendentes"])


class ArtificerSpellValidationTests(unittest.TestCase):
    def test_progressao_nivel_um_com_inteligencia_16(self):
        resultado = progresso_artifice(1, 16)
        self.assertEqual(resultado["truques"], 2)
        self.assertEqual(resultado["magias_preparadas"], 3)
        self.assertEqual(resultado["espacos_totais"], {"1": 2})
        self.assertEqual(resultado["circulo_maximo"], 1)

    def test_catalogo_artifice_filtra_por_nivel(self):
        magias = listar_magias_artifice(1)
        nomes = {m["nome"].lower() for m in magias}
        self.assertIn("luz", nomes)
        self.assertIn("alarme", nomes)
        self.assertNotIn("bola de fogo", nomes)

    def test_catalogo_define_circulo_de_magias_do_artifice(self):
        self.assertEqual(obter_magia("Luz")["circulo"], 0)
        self.assertEqual(obter_magia("Alarme")["circulo"], 1)

    def test_escolhas_validas_sao_aceitas(self):
        resultado = validar_escolhas_artifice(
            1, 16,
            ["Luz", "Raio de Gelo"],
            ["Alarme", "Curar Ferimentos", "Onda Trovejante"],
            {"1": 2},
        )
        self.assertEqual(resultado["resultado"], "resolvido")

    def test_bloqueia_magia_de_classe_ou_circulo_indisponivel(self):
        with self.assertRaisesRegex(ValueError, "não disponível para Artífice"):
            validar_escolhas_artifice(
                1, 16, ["Luz", "Raio de Gelo"],
                ["Alarme", "Curar Ferimentos", "Bola de Fogo"], {"1": 2},
            )

    def test_bloqueia_quantidade_incorreta_de_truques_e_magias(self):
        with self.assertRaisesRegex(ValueError, "exatamente 2 truques"):
            validar_escolhas_artifice(1, 16, ["Luz"], ["Alarme", "Curar Ferimentos", "Onda Trovejante"], {"1": 2})
        with self.assertRaisesRegex(ValueError, "exatamente 3 magias preparadas"):
            validar_escolhas_artifice(1, 16, ["Luz", "Raio de Gelo"], ["Alarme"], {"1": 2})

    def test_bloqueia_total_de_espacos_inventado(self):
        with self.assertRaisesRegex(ValueError, "Espaços de magia incorretos"):
            validar_escolhas_artifice(
                1, 16, ["Luz", "Raio de Gelo"],
                ["Alarme", "Curar Ferimentos", "Onda Trovejante"], {"1": 9},
            )


class BackendProficienciesAndSpellsTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "playtest-player"}
        self.campaign_id = self.client.post(
            "/v1/campanhas", json={"titulo": "Playtest"}, headers=self.headers
        ).json()["id"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def criar_artifice(self):
        payload = {
            "nome": "Vex", "especie": "draconato", "classe": "artifice", "nivel": 1,
            "metodo_atributos": "matriz_padrao",
            "atributos": {
                "forca": 8, "destreza": 13, "constituicao": 10,
                "inteligencia": 15, "sabedoria": 12, "carisma": 14,
            },
            "antecedente": "investigador",
            "aumentos_antecedente": {"inteligencia": 2, "sabedoria": 1},
            "pericias_classe": ["arcanismo", "historia"],
            "ferramenta_artesao": "Ferramentas de Carpinteiro",
        }
        resposta = self.client.post(
            f"/v1/campanhas/{self.campaign_id}/personagens",
            json=payload, headers=self.headers,
        )
        self.assertEqual(resposta.status_code, 201, resposta.text)
        return resposta.json()

    def test_api_persiste_proficiências_escolhidas(self):
        p = self.criar_artifice()
        self.assertEqual(p["pericias_classe"], ["arcanismo", "historia"])
        self.assertIn("investigacao", p["pericias"])
        self.assertEqual(p["ferramenta_artesao"], "Ferramentas de Carpinteiro")
        self.assertEqual(p["proficiencias_salvaguarda"], ["constituicao", "inteligencia"])
        self.assertFalse(p["proficiencias_pendentes"])
        atualizado = self.client.patch(
            f"/v1/campanhas/{self.campaign_id}/personagens/{p['id']}/proficiencias",
            json={"pericias_classe": ["investigacao", "arcanismo"], "ferramenta_artesao": "Ferramentas de Carpinteiro"},
            headers=self.headers,
        )
        self.assertEqual(atualizado.status_code, 200, atualizado.text)
        self.assertEqual(atualizado.json()["pericias_classe"], ["arcanismo", "investigacao"])

    def test_api_valida_magias_e_slots_do_artifice(self):
        p = self.criar_artifice()
        url = f"/v1/campanhas/{self.campaign_id}/personagens/{p['id']}/magias"
        payload = {
            "truques": ["Luz", "Raio de Gelo"],
            "magias_preparadas": ["Alarme", "Curar Ferimentos", "Onda Trovejante"],
            "espacos_totais": {"1": 2},
        }
        resposta = self.client.patch(url, json=payload, headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["conjuracao"]["espacos_restantes"], {"1": 2})
        invalida = dict(payload, magias_preparadas=["Alarme", "Curar Ferimentos", "Bola de Fogo"])
        resposta = self.client.patch(url, json=invalida, headers=self.headers)
        self.assertEqual(resposta.status_code, 422, resposta.text)

    def test_api_recupera_slots_apos_descanso_longo(self):
        p = self.criar_artifice()
        url = f"/v1/campanhas/{self.campaign_id}/personagens/{p['id']}/magias"
        resposta = self.client.patch(url, json={
            "truques": ["Luz", "Raio de Gelo"],
            "magias_preparadas": ["Alarme", "Curar Ferimentos", "Onda Trovejante"],
            "espacos_totais": {"1": 2},
        }, headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        ficha = {k: v for k, v in resposta.json().items() if k not in {
            "id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"
        }}
        ficha["conjuracao"]["espacos_restantes"] = {"1": 0}
        self.repo.atualizar_dados_ficha(self.headers["X-Jogador-Id"], self.campaign_id, p["id"], ficha)
        descanso = self.client.post(
            f"/v1/campanhas/{self.campaign_id}/personagens/{p['id']}/descanso-longo",
            headers=self.headers,
        )
        self.assertEqual(descanso.status_code, 200, descanso.text)
        self.assertEqual(descanso.json()["conjuracao"]["espacos_restantes"], {"1": 2})


if __name__ == "__main__":
    unittest.main()
