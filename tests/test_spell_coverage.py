import unittest

from rule_engine import MAGIAS, resolver_magia


class SpellCoverageTests(unittest.TestCase):
    def test_catalog_metadata_without_effect_is_not_claimed_as_cast(self):
        nome = next(nome for nome, magia in MAGIAS.items() if "efeito" not in magia)
        result = resolver_magia({"magia": nome})
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["motivo"], "magia_catalogada_sem_resolucao_especifica")
        self.assertNotIn("efeito", result)

    def test_detailed_spell_still_resolves(self):
        result = resolver_magia({"magia": "bola de fogo", "espaco": 4})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertIn("8d6", result["efeito"])
        self.assertEqual(result["upcasting"], 1)
        self.assertIn("escalonamento", result)

    def test_spell_names_are_normalized_without_accents(self):
        result = resolver_magia({"magia": "RAIO MISTICO"})
        self.assertEqual(result["magia"], "Raio Místico")
        self.assertEqual(result["resultado"], "conjurada")

    def test_cantrips_cannot_spend_spell_slots(self):
        result = resolver_magia({"magia": "raio místico", "espaco": 1})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "circulo_invalido")
        self.assertIn("Truques não usam espaços", result["detalhe"])

    def test_spell_slot_above_ninth_level_is_blocked(self):
        result = resolver_magia({"magia": "bola de fogo", "espaco": 10})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "circulo_invalido")

    def test_missing_components_still_blocks_spell(self):
        result = resolver_magia({"magia": "bola de fogo", "componentes_disponiveis": ["V"]})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "componentes_ausentes")


if __name__ == "__main__":
    unittest.main()
