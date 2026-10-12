import unittest

from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine


class CombatIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ.__new__(DeepSeekMJ)
        self.mj.engine = build_default_engine()
        self.personagem = {
            "id": "hero-1",
            "nome": "Heroi",
            "classe": "guerreiro",
            "nivel": 1,
            "atributos": {
                "forca": 16, "destreza": 12, "constituicao": 14,
                "inteligencia": 10, "sabedoria": 10, "carisma": 10,
            },
        }

    def test_attack_derives_modifier_from_character_weapon_and_bestiary(self):
        result = self.mj._tool(
            "resolver_regra",
            {"fatos": {
                "type": "attack", "character_id": "hero-1",
                "weapon": "Adaga", "target_name": "Baboon", "seed": "integration-test",
            }},
            [self.personagem],
        )
        self.assertEqual(result.get("roll_source"), "rule_engine")
        self.assertIn(result.get("result"), {"hit", "miss"})
        self.assertEqual(result.get("modifier"), 5)
        self.assertEqual(result.get("weapon"), "Adaga")
        self.assertEqual(result.get("weapon_damage"), "1d4")
        self.assertEqual(result.get("damage_type"), "perfurante")
        self.assertEqual(result.get("target_name"), "Baboon")
        self.assertEqual(result.get("modifier_source"), "ficha_autoritativa")

    def test_attack_blocks_weapon_not_in_catalog(self):
        result = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "attack", "weapon": "Espada Inventada", "target_name": "Baboon"}},
            [self.personagem],
        )
        self.assertEqual(result.get("resultado"), "bloqueado")
        self.assertEqual(result.get("motivo"), "arma_nao_encontrada_no_catalogo")

    def test_attack_blocks_character_without_weapon_proficiency(self):
        wizard = {**self.personagem, "classe": "mago"}
        result = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "attack", "weapon": "Espada Grande", "target_name": "Baboon"}},
            [wizard],
        )
        self.assertEqual(result.get("resultado"), "bloqueado")
        self.assertEqual(result.get("motivo"), "personagem_sem_proficiencia_na_arma")

    def test_initiative_uses_character_dexterity_modifier(self):
        result = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "initiative", "character_id": "hero-1", "seed": "initiative-test"}},
            [self.personagem],
        )
        self.assertEqual(result.get("type"), "initiative")
        self.assertEqual(result.get("modifier"), 1)
        self.assertEqual(result.get("modifier_source"), "ficha_autoritativa")
        self.assertEqual(result.get("roll_source"), "rule_engine")


if __name__ == "__main__":
    unittest.main()
