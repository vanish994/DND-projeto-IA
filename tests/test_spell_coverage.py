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

    def test_unknown_spell_levels_are_not_misclassified_as_cantrips(self):
        from rule_engine import listar_magias
        unknown = next(nome for nome, magia in MAGIAS.items() if magia["circulo"] is None)
        result = resolver_magia({"magia": unknown})
        self.assertEqual(result["resultado"], "nao_implementado")
        self.assertEqual(result["motivo_secundario"], "circulo_da_magia_nao_catalogado")
        self.assertNotIn(unknown, {m["nome"].lower() for m in listar_magias(circulo=0)})

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

    def test_fireball_returns_structured_damage_and_upcasting(self):
        result = resolver_magia({"magia": "bola de fogo", "espaco": 4})
        self.assertEqual(result["mecanica"]["dados_dano"], "9d6")
        self.assertEqual(result["mecanica"]["tipo_dano"], "igneo")
        self.assertEqual(result["mecanica"]["salvaguarda"], "destreza")
        self.assertEqual(result["mecanica"]["area"]["raio_m"], 6)

    def test_cure_wounds_returns_structured_healing(self):
        result = resolver_magia({"magia": "curar ferimentos", "espaco": 2})
        self.assertEqual(result["mecanica"]["dados_cura"], "4d8")
        self.assertTrue(result["mecanica"]["soma_modificador_conjuracao"])

    def test_magic_missile_scales_number_of_darts(self):
        result = resolver_magia({"magia": "mísseis mágicos", "espaco": 3})
        self.assertEqual(result["mecanica"]["dardos"], 5)
        self.assertEqual(result["mecanica"]["dano_por_dardo"], "1d4+1")

    def test_bless_scales_number_of_targets(self):
        result = resolver_magia({"magia": "benção", "espaco": 2})
        self.assertEqual(result["mecanica"]["alvos"], 4)
        self.assertEqual(result["mecanica"]["bonus"], "1d4")

    def test_healing_word_scales_and_uses_bonus_action(self):
        result = resolver_magia({"magia": "palavra curativa", "espaco": 2})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["dados_cura"], "2d4")
        self.assertEqual(result["mecanica"]["acao"], "bonus")
        self.assertTrue(result["mecanica"]["soma_modificador_conjuracao"])

    def test_thunderwave_returns_save_area_and_push(self):
        result = resolver_magia({"magia": "onda trovejante", "espaco": 2})
        self.assertEqual(result["mecanica"]["dados_dano"], "3d8")
        self.assertEqual(result["mecanica"]["salvaguarda"], "constituicao")
        self.assertTrue(result["mecanica"]["sucesso_metade"])
        self.assertEqual(result["mecanica"]["area"]["lado_m"], 4.5)
        self.assertEqual(result["mecanica"]["empurra_m"], 3)

    def test_mage_armor_blocks_target_already_wearing_armor(self):
        result = resolver_magia({"magia": "armadura arcana", "alvo_veste_armadura": True})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "alvo_ja_veste_armadura")

    def test_mage_armor_returns_structured_armor_class(self):
        result = resolver_magia({"magia": "armadura arcana"})
        self.assertEqual(result["mecanica"]["ca_base"], 13)
        self.assertTrue(result["mecanica"]["adiciona_modificador_destreza"])
        self.assertTrue(result["mecanica"]["exige_alvo_sem_armadura"])

    def test_missing_components_still_blocks_spell(self):
        result = resolver_magia({"magia": "bola de fogo", "componentes_disponiveis": ["V"]})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "componentes_ausentes")


if __name__ == "__main__":
    unittest.main()
