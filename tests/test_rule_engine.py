import unittest

from rule_engine import build_default_engine


class RuleEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_default_engine()

    def test_success_when_total_meets_dc(self):
        result = self.engine.evaluate({"type": "ability_check", "roll": 12, "modifier": 3, "dc": 15})
        self.assertEqual(result.outcome["result"], "success")
        self.assertEqual(result.outcome["total"], 15)
        self.assertEqual(result.matched_rules, ["ability-check.meets-dc"])

    def test_natural_twenty_has_priority(self):
        result = self.engine.evaluate({"type": "ability_check", "roll": 20, "modifier": -10, "dc": 30})
        self.assertEqual(result.outcome["reason"], "natural_20")
        self.assertEqual(result.matched_rules, ["ability-check.natural-20"])

    def test_natural_one_has_priority(self):
        result = self.engine.evaluate({"type": "ability_check", "roll": 1, "modifier": 20, "dc": 5})
        self.assertEqual(result.outcome["reason"], "natural_1")

    def test_unknown_input_is_undetermined(self):
        result = self.engine.evaluate({"type": "initiative", "roll": 10})
        self.assertEqual(result.status, "undetermined")
        self.assertEqual(result.matched_rules, [])

    def test_ai_instruction_is_auditable(self):
        result = self.engine.evaluate({"type": "ability_check", "roll": 8, "modifier": 0, "dc": 15})
        instruction = result.to_ai_instruction()
        self.assertIn("ability-check.below-dc", instruction)
        self.assertIn("result=failure", instruction)


if __name__ == "__main__":
    unittest.main()
