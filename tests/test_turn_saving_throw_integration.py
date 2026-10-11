import unittest

from pydantic import ValidationError

from backend.app import AcaoAvancarTurno


class TurnSavingThrowPayloadTests(unittest.TestCase):
    def test_turn_advance_accepts_end_of_turn_saving_throws(self):
        request = AcaoAvancarTurno.model_validate({
            "token_id": "goblin-1",
            "salvaguardas": [{
                "condicao": "paralisado",
                "modificador": 2,
                "cd": 14,
            }],
        })
        self.assertEqual(request.salvaguardas[0].condicao, "paralisado")
        self.assertEqual(request.salvaguardas[0].modificador, 2)

    def test_turn_saving_throw_rejects_invalid_dc(self):
        with self.assertRaises(ValidationError):
            AcaoAvancarTurno.model_validate({
                "salvaguardas": [{
                    "condicao": "paralisado",
                    "modificador": 0,
                    "cd": 0,
                }],
            })

    def test_turn_advance_defaults_to_no_manual_saving_throws(self):
        request = AcaoAvancarTurno.model_validate({})
        self.assertEqual(request.salvaguardas, [])

    def test_condition_application_accepts_repeat_save_metadata(self):
        from backend.app import AtualizarCondicaoPersonagem

        request = AtualizarCondicaoPersonagem.model_validate({
            "operacao": "apply",
            "condicao": "paralisado",
            "duracao": "até o fim do próximo turno",
            "salvaguarda_fim_turno": {"atributo": "sabedoria", "cd": 15},
        })
        self.assertEqual(request.salvaguarda_fim_turno.atributo, "sabedoria")
        self.assertEqual(request.salvaguarda_fim_turno.cd, 15)

    def test_condition_application_rejects_invalid_save_ability(self):
        from backend.app import AtualizarCondicaoPersonagem

        with self.assertRaises(ValidationError):
            AtualizarCondicaoPersonagem.model_validate({
                "operacao": "apply",
                "condicao": "paralisado",
                "salvaguarda_fim_turno": {"atributo": "sorte", "cd": 15},
            })


if __name__ == "__main__":
    unittest.main()
