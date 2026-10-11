import unittest

from rule_engine.feats import resolver_talento


class FeatCoverageTests(unittest.TestCase):
    def test_catalogued_feat_without_specific_resolver_is_not_reported_resolved(self):
        result = resolver_talento({"talento": "alerta", "nivel": 1})
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["motivo"], "talento_catalogado_sem_resolucao_especifica")
        self.assertIn("proficiência_iniciativa", result["efeitos"])

    def test_existing_specific_feat_resolver_still_works(self):
        result = resolver_talento({"talento": "vigoroso", "nivel": 5})
        self.assertEqual(result["resultado"], "resolvido")
        self.assertEqual(result["pv_adicionais"], 10)
        self.assertNotIn("motivo", result)

    def test_partial_feat_effects_are_not_reported_as_fully_resolved(self):
        for feat in ("sortudo", "conjurador_ritualista", "lider_inspirador", "dadiva_da_velocidade", "dadiva_da_resistencia_a_energia"):
            with self.subTest(feat=feat):
                result = resolver_talento({"talento": feat, "nivel": 19, "caracteristica_conjuracao": True})
                self.assertEqual(result["resultado"], "nao_implementado")

    def test_feat_name_normalizes_accents_and_spaces(self):
        result = resolver_talento({"talento": "telecinético", "nivel": 4})
        self.assertEqual(result["talento"], "telecinetico")
        self.assertEqual(result["resultado"], "nao_implementado")

    def test_unknown_feat_is_blocked(self):
        result = resolver_talento({"talento": "talento_inventado", "nivel": 4})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "talento_desconhecido")


if __name__ == "__main__":
    unittest.main()
