import unittest

from rule_engine import (
    build_default_engine,
    resolver_bruxo,
    resolver_feiticeiro,
    resolver_guardiao,
    resolver_paladino,
    resolver_progressao_conjuracao,
)


class SpellcastingProgressionTests(unittest.TestCase):
    def test_wizard_prepares_level_plus_intelligence_modifier(self):
        result = resolver_progressao_conjuracao({
            "classe": "mago", "nivel": 5, "inteligencia": 16,
        })
        self.assertEqual(result["magias_preparadas"], 8)
        self.assertEqual(result["espacos"], [4, 3, 2])

    def test_level_17_full_caster_has_three_level_five_slots(self):
        result = resolver_progressao_conjuracao({
            "classe": "mago", "nivel": 17, "inteligencia": 20,
        })
        self.assertEqual(result["espacos"], [4, 3, 3, 3, 3, 1, 1, 1, 1])

    def test_cantrips_follow_class_and_level_breakpoints(self):
        cases = [
            ("bardo", 1, 2), ("bardo", 4, 3), ("bardo", 10, 4),
            ("clérigo", 1, 3), ("clérigo", 4, 4), ("clérigo", 10, 5),
            ("druida", 1, 2), ("druida", 4, 3), ("druida", 10, 4),
            ("mago", 1, 3), ("mago", 4, 4), ("mago", 10, 5),
        ]
        for classe, nivel, esperado in cases:
            with self.subTest(classe=classe, nivel=nivel):
                result = resolver_progressao_conjuracao({
                    "classe": classe, "nivel": nivel,
                })
                self.assertEqual(result["truques"], esperado)

    def test_paladin_progression_is_registered_in_the_engine(self):
        result = build_default_engine().evaluate({
            "type": "advanced_caster_feature",
            "classe": "paladino",
            "nivel": 5,
            "carisma": 16,
        })
        self.assertEqual(result.outcome["resultado"], "resolvido")
        self.assertEqual(result.outcome["espacos"], [4, 2])
        self.assertEqual(result.outcome["atributo_conjuracao"], "carisma")
        self.assertEqual(result.outcome["pontos_de_cura_maos_consagradas"], 25)

    def test_paladin_high_level_slots_are_correct(self):
        result = resolver_paladino({"nivel": 19, "carisma": 20})
        self.assertEqual(result["espacos"], [4, 3, 3, 3, 2])

    def test_sorcerer_progression_includes_spell_slots(self):
        result = resolver_feiticeiro({"nivel": 17})
        self.assertEqual(result["espacos"], [4, 3, 3, 3, 3, 1, 1, 1, 1])

    def test_invalid_levels_are_blocked_in_advanced_casters(self):
        for resolver, facts in [
            (resolver_bruxo, {"nivel": 0}),
            (resolver_feiticeiro, {"nivel": 21}),
            (resolver_guardiao, {"nivel": 0}),
            (resolver_paladino, {"nivel": 21}),
        ]:
            with self.subTest(resolver=resolver.__name__):
                self.assertEqual(resolver(facts)["motivo"], "nivel_invalido")

    def test_invalid_level_is_blocked_in_full_caster_progression(self):
        result = resolver_progressao_conjuracao({
            "classe": "mago", "nivel": 21,
        })
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "classe_ou_nivel_invalido")


if __name__ == "__main__":
    unittest.main()
