"""Escolhas que a criação precisa registrar para a ficha não ficar pela metade.

Cobre a Herança Dracônica do Draconato (Livro do Jogador 2024, p. 188-194),
a ferramenta do antecedente e o pacote de equipamento A/B.
"""
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend import app as backend_app
from backend.persistencia import RepositorioCampanhas
from rule_engine.catalog import INSTRUMENTOS_MUSICAIS, KITS_DE_JOGOS
from rule_engine.character import (
    CATEGORIAS_FERRAMENTA_ANTECEDENTE,
    escolha_ferramenta_do_antecedente,
    criar_personagem,
    ficha_personagem,
)
from rule_engine.species import HERANCA_DRACONICA, dado_sopro


ATRIBUTOS = {
    "forca": 8, "destreza": 14, "constituicao": 12,
    "inteligencia": 15, "sabedoria": 12, "carisma": 14,
}


def fatos(**extra):
    dados = {
        "name": "Vanish", "species": "draconato", "class": "artifice", "level": 1,
        "ability_scores": dict(ATRIBUTOS),
        "background": "artesao",
        "class_skill_proficiencies": ["arcanismo", "investigacao"],
        "artisan_tool_proficiency": "Ferramentas de Ferreiro",
    }
    dados.update(extra)
    return dados


class HerancaDraconicaTests(unittest.TestCase):
    def test_tabela_oficial_tem_as_dez_linhagens(self):
        self.assertEqual(len(HERANCA_DRACONICA), 10)
        self.assertEqual(HERANCA_DRACONICA["ouro"]["dano"], "ígneo")
        self.assertEqual(HERANCA_DRACONICA["negro"]["dano"], "ácido")
        self.assertEqual(HERANCA_DRACONICA["branco"]["dano"], "gélido")
        self.assertEqual(HERANCA_DRACONICA["verde"]["dano"], "venenoso")

    def test_draconato_sem_heranca_fica_pendente(self):
        ficha = ficha_personagem(criar_personagem(fatos()))
        self.assertIsNone(ficha["heranca_draconica"])
        self.assertIn("Herança Dracônica", ficha["escolhas_pendentes"])

    def test_heranca_registrada_entra_na_ficha_com_sopro_e_resistencia(self):
        ficha = ficha_personagem(criar_personagem(fatos(heranca_draconica="ouro")))
        heranca = ficha["heranca_draconica"]
        self.assertEqual(heranca["linhagem"], "Dragão Ouro")
        self.assertEqual(heranca["tipo_dano"], "ígneo")
        self.assertEqual(heranca["resistencia"], "dano ígneo")
        self.assertEqual(heranca["sopro"]["dado"], "1d10")
        self.assertEqual(heranca["sopro"]["cd"], 8 + 1 + 2)  # 8 + CON + proficiência
        self.assertEqual(heranca["sopro"]["usos"], 2)
        self.assertNotIn("Herança Dracônica", ficha["escolhas_pendentes"])

    def test_heranca_invalida_e_recusada(self):
        with self.assertRaisesRegex(ValueError, "Herança Dracônica inválida"):
            criar_personagem(fatos(heranca_draconica="roxo"))

    def test_outra_especie_nao_aceita_heranca(self):
        with self.assertRaisesRegex(ValueError, "não exige escolha adicional"):
            criar_personagem(fatos(species="elfo", heranca_draconica="ouro"))

    def test_dano_do_sopro_cresce_por_nivel(self):
        self.assertEqual(dado_sopro(1), "1d10")
        self.assertEqual(dado_sopro(4), "1d10")
        self.assertEqual(dado_sopro(5), "2d10")
        self.assertEqual(dado_sopro(11), "3d10")
        self.assertEqual(dado_sopro(17), "4d10")


class FerramentaAntecedenteTests(unittest.TestCase):
    def test_categorias_vem_do_catalogo_oficial(self):
        self.assertEqual(sorted(CATEGORIAS_FERRAMENTA_ANTECEDENTE), ["ferramentas de artesão", "instrumento musical", "kit de jogos"])
        self.assertIn("Violino", INSTRUMENTOS_MUSICAIS)
        self.assertIn("Xadrez-do-Dragão", KITS_DE_JOGOS)

    def test_somente_os_antecedentes_com_escolha_exigem_ferramenta(self):
        self.assertIsNotNone(escolha_ferramenta_do_antecedente("artesao"))
        self.assertIsNotNone(escolha_ferramenta_do_antecedente("artista"))
        self.assertIsNotNone(escolha_ferramenta_do_antecedente("soldado"))
        self.assertIsNone(escolha_ferramenta_do_antecedente("sabio"))
        self.assertIsNone(escolha_ferramenta_do_antecedente("inexistente"))

    def test_artesao_sem_ferramenta_fica_pendente(self):
        ficha = ficha_personagem(criar_personagem(fatos()))
        self.assertTrue(ficha["ferramenta_pendente"])
        self.assertIsNone(ficha["ferramenta"])
        self.assertIn("Ferramentas de Artesão (antecedente)", ficha["escolhas_pendentes"])

    def test_ferramenta_escolhida_entra_na_ficha(self):
        ficha = ficha_personagem(criar_personagem(fatos(ferramenta_antecedente="Ferramentas de Ferreiro")))
        self.assertEqual(ficha["ferramenta"], "Ferramentas de Ferreiro")
        self.assertFalse(ficha["ferramenta_pendente"])

    def test_instrumento_musical_recebe_o_rotulo_da_categoria(self):
        ficha = ficha_personagem(criar_personagem(fatos(background="artista", ferramenta_antecedente="Violino")))
        self.assertEqual(ficha["ferramenta"], "Instrumento Musical (Violino)")

    def test_ferramenta_fora_da_categoria_e_recusada(self):
        with self.assertRaisesRegex(ValueError, "Ferramenta inválida"):
            criar_personagem(fatos(background="artista", ferramenta_antecedente="Ferramentas de Ferreiro"))

    def test_antecedente_sem_escolha_usa_a_ferramenta_fixa(self):
        ficha = ficha_personagem(criar_personagem(fatos(background="sabio")))
        self.assertEqual(ficha["ferramenta"], "Suprimentos de Calígrafo")
        self.assertFalse(ficha["ferramenta_pendente"])


class EquipamentoAntecedenteTests(unittest.TestCase):
    def test_sem_escolha_o_pacote_fica_pendente(self):
        ficha = ficha_personagem(criar_personagem(fatos()))
        self.assertTrue(ficha["equipamento_pendente"])
        self.assertIn("Equipamento de antecedente (A ou B)", ficha["escolhas_pendentes"])

    def test_pacote_a_recebe_a_ferramenta_escolhida(self):
        ficha = ficha_personagem(criar_personagem(fatos(ferramenta_antecedente="Ferramentas de Ferreiro", equipamento_antecedente="a")))
        equipamento = ficha["equipamento_antecedente"]
        self.assertEqual(equipamento["escolha"], "A")
        self.assertIn("Ferramentas de Ferreiro", equipamento["A"])
        self.assertNotIn("a mesma que acima", equipamento["A"])
        self.assertFalse(ficha["equipamento_pendente"])

    def test_pacote_b_e_cinquenta_pecas_de_ouro(self):
        ficha = ficha_personagem(criar_personagem(fatos(equipamento_antecedente="B")))
        self.assertEqual(ficha["equipamento_antecedente"]["escolha"], "B")
        self.assertEqual(ficha["equipamento_antecedente"]["B"], "50 PO")

    def test_pacote_invalido_e_recusado(self):
        with self.assertRaisesRegex(ValueError, "equipamento de antecedente A ou B"):
            criar_personagem(fatos(equipamento_antecedente="C"))


class BackendEscolhasCriacaoTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-escolhas"}
        self.campaign_id = self.client.post("/v1/campanhas", json={"titulo": "Escolhas"}, headers=self.headers).json()["id"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def payload(self, **extra):
        dados = {
            "nome": "Vanish", "especie": "draconato", "classe": "artifice", "nivel": 1,
            "metodo_atributos": "matriz_padrao",
            "atributos": {"forca": 8, "destreza": 13, "constituicao": 10, "inteligencia": 15, "sabedoria": 12, "carisma": 14},
            "antecedente": "artesao", "aumentos_antecedente": {"inteligencia": 2, "destreza": 1},
            "pericias_classe": ["arcanismo", "investigacao"],
            "ferramenta_artesao": "Ferramentas de Ferreiro",
            "heranca_draconica": "ouro",
            "ferramenta_antecedente": "Ferramentas de Ferreiro",
            "equipamento_antecedente": "A",
        }
        dados.update(extra)
        return dados

    def url(self, sufixo=""):
        return f"/v1/campanhas/{self.campaign_id}/personagens{sufixo}"

    def test_catalogo_expõe_as_escolhas_de_especie_e_de_ferramenta(self):
        catalogo = self.client.get("/v1/catalogo/personagens").json()
        self.assertEqual(len(catalogo["escolhas_especie"]["draconato"]["opcoes"]), 10)
        self.assertEqual(catalogo["escolhas_especie"]["draconato"]["rotulo"], "Herança Dracônica")
        self.assertIn("Violino", catalogo["ferramentas_antecedente"]["artista"]["opcoes"])
        self.assertIn("Dados", catalogo["ferramentas_antecedente"]["soldado"]["opcoes"])
        self.assertNotIn("sabio", catalogo["ferramentas_antecedente"])
        self.assertEqual(catalogo["atributo_conjuracao"]["artifice"], "inteligencia")

    def test_criacao_exige_a_heranca_do_draconato(self):
        resposta = self.client.post(self.url(), json=self.payload(heranca_draconica=None), headers=self.headers)
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("Herança Dracônica", resposta.json()["detail"])

    def test_criacao_exige_a_ferramenta_do_antecedente(self):
        resposta = self.client.post(self.url(), json=self.payload(ferramenta_antecedente=None), headers=self.headers)
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("Ferramentas de Artesão", resposta.json()["detail"])

    def test_criacao_exige_o_pacote_de_equipamento(self):
        resposta = self.client.post(self.url(), json=self.payload(equipamento_antecedente=None), headers=self.headers)
        self.assertEqual(resposta.status_code, 422)
        self.assertIn("equipamento de antecedente", resposta.json()["detail"])

    def test_criacao_completa_registra_tudo(self):
        resposta = self.client.post(self.url(), json=self.payload(), headers=self.headers)
        self.assertEqual(resposta.status_code, 201, resposta.text)
        ficha = resposta.json()
        self.assertEqual(ficha["heranca_draconica"]["nome"], "Ouro")
        self.assertEqual(ficha["ferramenta"], "Ferramentas de Ferreiro")
        self.assertEqual(ficha["equipamento_antecedente"]["escolha"], "A")
        self.assertEqual(ficha["escolhas_pendentes"], [])

    def test_criacao_aceita_as_magias_iniciais_do_conjurador(self):
        magias = {"truques": ["Luz", "Raio de Gelo"], "magias_preparadas": ["Alarme", "Curar Ferimentos", "Onda Trovejante"], "espacos_totais": {"1": 2}}
        resposta = self.client.post(self.url(), json=self.payload(magias_iniciais=magias), headers=self.headers)
        self.assertEqual(resposta.status_code, 201, resposta.text)
        self.assertEqual(resposta.json()["conjuracao"]["truques"], ["Luz", "Raio de Gelo"])
        self.assertEqual(resposta.json()["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_magias_iniciais_fora_da_regra_sao_recusadas(self):
        magias = {"truques": ["Luz"], "magias_preparadas": [], "espacos_totais": {"1": 2}}
        resposta = self.client.post(self.url(), json=self.payload(magias_iniciais=magias), headers=self.headers)
        self.assertEqual(resposta.status_code, 422)

    def test_ficha_antiga_pode_ser_concluida_sem_perder_a_conjuracao(self):
        criado = self.client.post(self.url(), json=self.payload(), headers=self.headers).json()
        magias = {"truques": ["Luz", "Raio de Gelo"], "magias_preparadas": ["Alarme", "Curar Ferimentos", "Onda Trovejante"], "espacos_totais": {"1": 2}}
        self.client.patch(self.url(f"/{criado['id']}/magias"), json=magias, headers=self.headers)
        # Simula uma ficha criada antes das escolhas existirem.
        personagem = self.repo.obter_personagem("jogador-escolhas", self.campaign_id, criado["id"])
        entrada = dict(personagem["entrada"])
        entrada.pop("equipamento_antecedente", None)
        entrada.pop("ferramenta_antecedente", None)
        ficha_antiga = {chave: valor for chave, valor in personagem.items()
                        if chave not in {"id", "campanha_id", "pv_atual", "entrada", "criado_em", "atualizado_em"}}
        self.repo.atualizar_personagem("jogador-escolhas", self.campaign_id, criado["id"], entrada=entrada, ficha=ficha_antiga)

        resposta = self.client.patch(self.url(f"/{criado['id']}/proficiencias"), json={
            "pericias_classe": ["arcanismo", "investigacao"],
            "ferramenta_artesao": "Ferramentas de Ferreiro",
            "ferramenta_antecedente": "Ferramentas de Ferreiro",
            "equipamento_antecedente": "B",
        }, headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        ficha = resposta.json()
        self.assertEqual(ficha["equipamento_antecedente"]["escolha"], "B")
        self.assertEqual(ficha["escolhas_pendentes"], [])
        self.assertEqual(ficha["conjuracao"]["truques"], ["Luz", "Raio de Gelo"])

    def test_conjuracao_de_classes_com_progressao_no_motor(self):
        for classe, atributo in (("mago", "inteligencia"), ("clerigo", "sabedoria"), ("bardo", "carisma")):
            resposta = self.client.get(f"/v1/catalogo/conjuracao?classe={classe}&nivel=1&{atributo}=16")
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(resposta.json()["resultado"], "resolvido")
            self.assertEqual(resposta.json()["espacos_totais"], {"1": 2})
        resposta = self.client.get("/v1/catalogo/conjuracao?classe=ladino&nivel=1")
        self.assertEqual(resposta.json()["resultado"], "nao_implementado")


if __name__ == "__main__":
    unittest.main()
