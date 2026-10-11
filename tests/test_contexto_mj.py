import unittest

from backend.app import _resumo_grupo
from integrations.deepseek_mj import PROMPT_NORMATIVO


class RepositorioFalso:
    def __init__(self, personagens):
        self.personagens = personagens

    def listar_personagens(self, jogador, campanha_id):
        return self.personagens


class ContextoMestreTests(unittest.TestCase):
    def test_ficha_completa_inclui_nome_e_nao_permite_reinventar_identidade(self):
        personagem = {
            "id": "p-1",
            "nome": "Vex",
            "especie": "draconato",
            "classe": "artifice",
            "subclasse": None,
            "nivel": 1,
            "antecedente": "investigador",
            "pv_atual": 8,
            "pv_maximo": 8,
            "bonus_proficiencia": 2,
            "atributos": {
                "forca": 8, "destreza": 13, "constituicao": 10,
                "inteligencia": 16, "sabedoria": 12, "carisma": 16,
            },
            "modificadores": {
                "forca": -1, "destreza": 1, "constituicao": 0,
                "inteligencia": 3, "sabedoria": 1, "carisma": 3,
            },
            "pericias": ["investigacao", "percepcao"],
            "ferramenta": "ferramentas de ladrão",
            "talentos": ["olho_agucado"],
            "deslocamento": 9,
            "equipamento_antecedente": {"A": "kit de investigador"},
            "conjuracao": {"truques": [], "magias_preparadas": [], "espacos_totais": {}},
        }
        contexto = _resumo_grupo(RepositorioFalso([personagem]), "jogador", "campanha")

        self.assertIn("nome=Vex", contexto)
        self.assertIn("espécie=draconato", contexto)
        self.assertIn("classe=artifice", contexto)
        self.assertIn("nível=1", contexto)
        self.assertIn("INTELIGENCIA 16", contexto)
        self.assertIn("truques=nenhum registrado", contexto)
        self.assertIn("Não invente nome", contexto)

    def test_sem_personagem_instrui_mj_a_nao_inventar_um(self):
        contexto = _resumo_grupo(RepositorioFalso([]), "jogador", "campanha")
        self.assertIn("nenhum personagem está cadastrado", contexto)
        self.assertIn("Não invente nem presuma nome", contexto)

    def test_prompt_exige_consultar_ficha_e_motor(self):
        self.assertIn("REGRA PRIORITÁRIA — FICHA E INÍCIO DA CAMPANHA", PROMPT_NORMATIVO)
        self.assertIn("não simule que o motor a validou", PROMPT_NORMATIVO)


if __name__ == "__main__":
    unittest.main()
