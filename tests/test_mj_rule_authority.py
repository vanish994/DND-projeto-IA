import unittest

from integrations.deepseek_mj import DeepSeekMJ


class MJRuleAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ(client=object(), model="test")
        self.personagem = {
            "id": "char-1",
            "nome": "Vex",
            "atributos": {
                "forca": 16, "destreza": 14, "constituicao": 13,
                "inteligencia": 12, "sabedoria": 10, "carisma": 8,
            },
            "modificadores": {
                "forca": 3, "destreza": 2, "constituicao": 1,
                "inteligencia": 1, "sabedoria": 0, "carisma": -1,
            },
            "bonus_proficiencia": 2,
            "pericias": ["investigacao"],
        }

    def test_atletismo_usa_forca_e_ignora_modificador_inventado(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "atletismo",
            "modifier": 999,
            "proficiente": True,
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["ability"], "forca")
        self.assertEqual(resultado["skill"], "atletismo")
        self.assertEqual(resultado["modifier"], 3)
        self.assertEqual(resultado["modifier_source"], "ficha_autoritativa")

    def test_pericia_registrada_recebe_bonus_de_proficiencia_da_ficha(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "investigacao",
            "modifier": -999,
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["ability"], "inteligencia")
        self.assertEqual(resultado["modifier"], 3)
        self.assertEqual(resultado["proficiency_applied"], 2)

    def test_motor_rejeita_atributo_incompativel_com_pericia(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "atletismo",
            "ability": "destreza",
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "atributo_incompativel_com_pericia")
        self.assertEqual(resultado["atributo_correto"], "forca")

    def test_motor_nao_resolve_teste_sem_personagem_identificado(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check", "ability": "forca", "dc": 10,
        }}, [])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "personagem_ausente_ou_nao_identificado")


if __name__ == "__main__":
    unittest.main()
