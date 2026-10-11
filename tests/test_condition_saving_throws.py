import unittest

from rule_engine.conditions import EstadoCondicoes


class ConditionSavingThrowTests(unittest.TestCase):
    def test_successful_save_ends_active_condition_and_clears_duration(self):
        state = EstadoCondicoes()
        state.aplicar("paralisado", 3)

        result = state.encerrar_por_salvaguarda("paralisado", 12, 2, 14)

        self.assertTrue(result["encerrada"])
        self.assertEqual(result["resultado"], "encerrada")
        self.assertNotIn("paralisado", state.ativas)
        self.assertNotIn("paralisado", state.duracoes)

    def test_failed_save_keeps_condition_active(self):
        state = EstadoCondicoes()
        state.aplicar("contido", 3)

        result = state.encerrar_por_salvaguarda("restrained", 8, 2, 14)

        self.assertFalse(result["encerrada"])
        self.assertEqual(result["total"], 10)
        self.assertIn("contido", state.ativas)
        self.assertEqual(state.duracoes["contido"], 3)

    def test_save_for_inactive_condition_does_not_change_state(self):
        state = EstadoCondicoes()

        result = state.encerrar_por_salvaguarda("amedrontado", 20, 5, 10)

        self.assertEqual(result["resultado"], "não_ativa")
        self.assertFalse(result["encerrada"])

    def test_invalid_d20_roll_is_rejected(self):
        state = EstadoCondicoes()
        state.aplicar("envenenado")

        with self.assertRaises(ValueError):
            state.encerrar_por_salvaguarda("envenenado", 21, 0, 12)


if __name__ == "__main__":
    unittest.main()
