import unittest

from pydantic import ValidationError

from backend.app import AcaoAvancarTurno


class TurnSavingThrowPayloadTests(unittest.TestCase):
    def test_turn_advance_accepts_end_of_turn_saving_throws(self):
        request = AcaoAvancarTurno.model_validate({
            "token_id": "goblin-1",
            "salvaguardas": [{
                "condicao": "paralisado",
                "rolagem": 12,
                "modificador": 2,
                "cd": 14,
            }],
        })
        self.assertEqual(request.salvaguardas[0].condicao, "paralisado")
        self.assertEqual(request.salvaguardas[0].rolagem, 12)

    def test_turn_saving_throw_rejects_invalid_d20(self):
        with self.assertRaises(ValidationError):
            AcaoAvancarTurno.model_validate({
                "salvaguardas": [{
                    "condicao": "paralisado",
                    "rolagem": 21,
                    "modificador": 0,
                    "cd": 14,
                }],
            })

    def test_turn_advance_defaults_to_no_saving_throws(self):
        request = AcaoAvancarTurno.model_validate({})
        self.assertEqual(request.salvaguardas, [])


if __name__ == "__main__":
    unittest.main()
