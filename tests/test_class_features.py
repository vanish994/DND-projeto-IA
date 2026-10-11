import unittest

from rule_engine import resolver_caracteristica


class ClassFeatureCoverageTests(unittest.TestCase):
    def test_unknown_feature_is_not_reported_as_resolved(self):
        result = resolver_caracteristica({"classe": "barbaro", "nivel": 3, "recurso": "caracteristica_inventada"})
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["motivo"], "caracteristica_catalogada_sem_resolver_especifico")

    def test_missing_feature_name_requests_the_feature(self):
        result = resolver_caracteristica({"classe": "barbaro", "nivel": 3})
        self.assertEqual(result["resultado"], "requer_caracteristica")

    def test_known_feature_still_resolves(self):
        result = resolver_caracteristica({"classe": "guerreiro", "nivel": 2, "recurso": "surto_de_acao"})
        self.assertEqual(result["resultado"], "resolvido")
        self.assertTrue(result["acao_adicional"])

    def test_portuguese_accents_are_normalized(self):
        result = resolver_caracteristica({"classe": "clérigo", "nivel": 2, "recurso": "canalizar divindade"})
        self.assertEqual(result["resultado"], "resolvido")
        self.assertEqual(result["usos"], 2)

    def test_paladin_lay_on_hands_cannot_spend_negative_or_unavailable_pool(self):
        negative = resolver_caracteristica({
            "classe": "paladino", "nivel": 3, "recurso": "maos_consagradas", "custo": -1,
        })
        self.assertEqual(negative["resultado"], "bloqueado")
        overdrawn = resolver_caracteristica({
            "classe": "paladino", "nivel": 3, "recurso": "maos_consagradas",
            "custo": 6, "pool_restante": 5,
        })
        self.assertEqual(overdrawn["resultado"], "bloqueado")
        valid = resolver_caracteristica({
            "classe": "paladino", "nivel": 3, "recurso": "maos_consagradas",
            "custo": 4, "pool_restante": 5,
        })
        self.assertEqual(valid["cura"], 4)
        self.assertEqual(valid["pool_restante"], 1)

    def test_unknown_class_is_blocked(self):
        result = resolver_caracteristica({"classe": "classe_fantasma", "nivel": 3, "recurso": "qualquer_coisa"})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "classe_desconhecida")


if __name__ == "__main__":
    unittest.main()
