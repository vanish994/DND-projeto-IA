import unittest

from integrations.deepseek_mj import DeepSeekMJ, TOOLS


class CharacterCreationToolTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ(client=object(), model="test")

    def test_tool_is_exposed_to_model(self):
        names = {tool["function"]["name"] for tool in TOOLS}
        self.assertIn("criar_personagem", names)

    def test_creation_uses_rule_engine_and_returns_derived_sheet(self):
        result = self.mj._tool(
            "criar_personagem",
            {
                "fatos": {
                    "name": "Vanish",
                    "species": "humano",
                    "class": "artifice",
                    "level": 1,
                    "ability_scores": {
                        "forca": 8,
                        "destreza": 14,
                        "constituicao": 13,
                        "inteligencia": 15,
                        "sabedoria": 12,
                        "carisma": 10,
                    },
                }
            },
        )
        self.assertEqual(result["resultado"], "ficha_validada")
        ficha = result["personagem"]
        self.assertEqual(ficha["nome"], "Vanish")
        self.assertEqual(ficha["classe"], "artifice")
        self.assertEqual(ficha["nivel"], 1)
        self.assertEqual(ficha["bonus_proficiencia"], 2)
        self.assertEqual(ficha["pv_maximo"], 9)
        self.assertIn("modificadores", ficha)

    def test_missing_required_fields_are_reported_without_guessing(self):
        result = self.mj._tool("criar_personagem", {"fatos": {"name": "Vanish"}})
        self.assertEqual(result["resultado"], "incompleto")
        self.assertCountEqual(
            result["campos_obrigatorios_ausentes"],
            ["species", "class", "ability_scores"],
        )

    def test_invalid_class_is_rejected_by_rules_engine(self):
        result = self.mj._tool(
            "criar_personagem",
            {
                "fatos": {
                    "name": "Vanish",
                    "species": "humano",
                    "class": "classe_inventada",
                    "ability_scores": {
                        "forca": 8,
                        "destreza": 14,
                        "constituicao": 13,
                        "inteligencia": 15,
                        "sabedoria": 12,
                        "carisma": 10,
                    },
                }
            },
        )
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "dados_de_criacao_invalidos")


if __name__ == "__main__":
    unittest.main()
