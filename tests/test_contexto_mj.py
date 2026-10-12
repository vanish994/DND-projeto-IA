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
        self.assertIn("não invente nome", contexto)

    def test_sem_personagem_instrui_mj_a_nao_inventar_um(self):
        contexto = _resumo_grupo(RepositorioFalso([]), "jogador", "campanha")
        self.assertIn("nenhum personagem está cadastrado", contexto)
        self.assertIn("Não invente nem presuma nome", contexto)

    def test_prompt_exige_consultar_ficha_e_motor(self):
        # Comparação sobre texto normalizado: pins de guardrail não podem
        # quebrar por causa de uma quebra de linha no prompt.
        normalizado = " ".join(PROMPT_NORMATIVO.split())
        pins = (
            "REGRA PRIORITÁRIA — FICHA E INÍCIO DA CAMPANHA",
            "não simule que o motor a validou",
            "Nunca invente conteúdo mecânico",
            "nunca conte espaços de cabeça",
            "NÃO são jogadas de ataque",
            "Não afirme atualização de ficha sem confirmação de operação persistida",
            "Sem personagem cadastrado, não comece com um personagem fictício",
        )
        for frase in pins:
            self.assertIn(frase, normalizado, f"guardrail perdido do prompt: {frase}")

    def test_prompt_economiza_tokens_sem_perder_contratos(self):
        """O prompt ensina fluxo, não derivação: precisa caber em 5.000 chars."""
        self.assertLess(len(PROMPT_NORMATIVO), 5000)


if __name__ == "__main__":
    unittest.main()
