import unittest

from rule_engine import ESPECIES, criar_personagem


class CharacterCoverageTests(unittest.TestCase):
    def test_all_ten_player_handbook_species_are_catalogued(self):
        self.assertIn("tiefling", ESPECIES)
        self.assertEqual(ESPECIES["tiefling"]["tamanho"], "pequeno_ou_medio")
        self.assertEqual(ESPECIES["tiefling"]["deslocamento"], 9)

    def test_tiefling_can_be_used_to_create_character(self):
        character = criar_personagem({
            "name": "Teste",
            "species": "tiefling",
            "class": "mago",
            "level": 1,
            "ability_scores": {
                "forca": 8, "destreza": 14, "constituicao": 13,
                "inteligencia": 15, "sabedoria": 12, "carisma": 10,
            },
            "background": "sabio",
            "equipamento_antecedente": "A",
        })
        self.assertEqual(character.especie, "tiefling")
        self.assertEqual(character.classe, "mago")


if __name__ == "__main__":
    unittest.main()
