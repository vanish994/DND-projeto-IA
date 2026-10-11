import unittest

from rule_engine.martial_subclasses import resolver_subclasse_marcial


class SubclassCoverageTruthfulnessTests(unittest.TestCase):
    def test_catalogued_but_unimplemented_feature_is_not_resolved(self):
        result = resolver_subclasse_marcial({
            "subclasse": "trilha_do_berserker",
            "nivel": 14,
            "caracteristica": "presenca_intimidante",
        })
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["caracteristica"], "presenca_intimidante")
        self.assertEqual(
            result["motivo"],
            "caracteristica_catalogada_sem_resolver_especifico",
        )

    def test_implemented_feature_still_resolves(self):
        result = resolver_subclasse_marcial({
            "subclasse": "trilha_do_berserker",
            "nivel": 6,
            "caracteristica": "furia_irracional",
        })
        self.assertEqual(result["resultado"], "resolvido")
        self.assertIn("amedrontado", result["imunidades"])

    def test_missing_feature_name_does_not_claim_success(self):
        result = resolver_subclasse_marcial({
            "subclasse": "campeao",
            "nivel": 3,
        })
        self.assertEqual(result["resultado"], "requer_caracteristica")

    def test_feature_not_yet_unlocked_remains_blocked(self):
        result = resolver_subclasse_marcial({
            "subclasse": "trilha_do_berserker",
            "nivel": 3,
            "caracteristica": "presenca_intimidante",
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "caracteristica_ainda_nao_disponivel")


    def test_tree_of_world_features_do_not_use_generic_success_fallback(self):
        result = resolver_subclasse_marcial({
            "subclasse": "trilha_da_arvore_do_mundo",
            "nivel": 3,
            "caracteristica": "vitalidade_da_arvore",
        })
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["motivo"], "caracteristica_catalogada_sem_resolver_especifico")


if __name__ == "__main__":
    unittest.main()
