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
        result = resolver_magia({"magia": "SERVO MINUSCULO", "espaco": 3})
        self.assertEqual(result["magia"], "Servo Minúsculo")
        self.assertEqual(result["resultado"], "nao_implementado")

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
        # PHB 2024: 2d4 + modificador, +2d4 por círculo acima do 1.º (2.º círculo = 4d4)
        self.assertEqual(result["mecanica"]["dados_cura"], "4d4")
        self.assertEqual(result["mecanica"]["acao"], "bonus")
        self.assertTrue(result["mecanica"]["soma_modificador_conjuracao"])

    def test_thunderwave_returns_save_area_and_push(self):
        result = resolver_magia({"magia": "onda trovejante", "espaco": 2})
        self.assertEqual(result["mecanica"]["dados_dano"], "3d8")
        self.assertEqual(result["mecanica"]["salvaguarda"], "constituicao")
        self.assertTrue(result["mecanica"]["sucesso_metade"])
        self.assertEqual(result["mecanica"]["area"]["lado_m"], 4.5)
        self.assertEqual(result["mecanica"]["empurra_m"], 3)

    def test_burning_hands_scales_fire_damage_and_cone_area(self):
        result = resolver_magia({"magia": "mãos flamejantes", "espaco": 3})
        self.assertEqual(result["mecanica"]["dados_dano"], "5d6")
        self.assertEqual(result["mecanica"]["tipo_dano"], "igneo")
        self.assertEqual(result["mecanica"]["salvaguarda"], "destreza")
        self.assertTrue(result["mecanica"]["sucesso_metade"])
        self.assertEqual(result["mecanica"]["area"]["forma"], "cone")
        self.assertEqual(result["mecanica"]["area"]["comprimento_m"], 4.5)

    def test_mage_armor_blocks_target_already_wearing_armor(self):
        result = resolver_magia({"magia": "armadura arcana", "alvo_veste_armadura": True})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "alvo_ja_veste_armadura")

    def test_mage_armor_returns_structured_armor_class(self):
        result = resolver_magia({"magia": "armadura arcana"})
        self.assertEqual(result["mecanica"]["ca_base"], 13)
        self.assertTrue(result["mecanica"]["adiciona_modificador_destreza"])
        self.assertTrue(result["mecanica"]["exige_alvo_sem_armadura"])

    def test_shield_of_faith_has_bonus_action_concentration_and_ac_bonus(self):
        result = resolver_magia({"magia": "escudo da fé"})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["bonus_ca"], 2)
        self.assertEqual(result["mecanica"]["acao"], "bonus")
        self.assertTrue(result["mecanica"]["concentracao"])
        self.assertEqual(result["mecanica"]["duracao"], "ate_10_minutos")

    def test_missing_components_still_blocks_spell(self):
        result = resolver_magia({"magia": "bola de fogo", "componentes_disponiveis": ["V"]})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "componentes_ausentes")




class MagiasSalvaguardaEControleTests(unittest.TestCase):
    """Magias do PHB 2024 modeladas em 'mecanica' estruturada (texto oficial)."""

    def test_inflict_wounds_scales_and_halves_on_save(self):
        result = resolver_magia({"magia": "infligir ferimentos", "espaco": 3})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["dados_dano"], "4d10")
        self.assertEqual(result["mecanica"]["tipo_dano"], "necrotico")
        self.assertEqual(result["mecanica"]["salvaguarda"], "constituicao")
        self.assertTrue(result["mecanica"]["sucesso_metade"])

    def test_command_uses_wisdom_save_and_one_target_at_first_level(self):
        result = resolver_magia({"magia": "comando", "espaco": 1})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["salvaguarda"], "sabedoria")
        self.assertEqual(result["mecanica"]["alvos"], 1)
        self.assertIn("parar", result["mecanica"]["comandos"])

    def test_sleep_is_concentration_sphere_with_incapacitated_condition(self):
        result = resolver_magia({"magia": "sono", "espaco": 1})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertTrue(result["concentracao"])
        self.assertEqual(result["mecanica"]["area"]["raio_m"], 1.5)
        self.assertEqual(result["mecanica"]["condicao_inicial"], "incapacitado")
        self.assertEqual(result["mecanica"]["condicao_apos_segunda_falha"], "inconsciente")

    def test_heroism_scales_targets_and_grants_immunity(self):
        result = resolver_magia({"magia": "heroismo", "espaco": 3})
        self.assertEqual(result["mecanica"]["alvos"], 3)
        self.assertIn("amedrontado", result["mecanica"]["condicao_imune"])
        self.assertEqual(result["duracao"], "concentração, até 1 minuto")

    def test_aid_scales_max_hp_bonus_by_slot_level(self):
        result = resolver_magia({"magia": "auxílio", "espaco": 4})
        self.assertEqual(result["mecanica"]["alvos"], 3)
        self.assertEqual(result["mecanica"]["pv_bonus"], 15)
        self.assertEqual(result["duracao"], "8 horas")

    def test_sanctuary_is_bonus_action_and_ignores_areas(self):
        result = resolver_magia({"magia": "santuário", "espaco": 1})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["acao"], "bonus")
        self.assertIn("area", result["mecanica"]["nao_protege_contra"])


class MagiasControleProtecaoTests(unittest.TestCase):
    """Lote 2 de magias do PHB 2024 (texto oficial)."""

    def test_scorching_ray_adds_rays_not_dice(self):
        result = resolver_magia({"magia": "raio ardente", "espaco": 4})
        self.assertEqual(result["mecanica"]["alvos"], 5)
        self.assertEqual(result["mecanica"]["dados_dano"], "2d6")
        self.assertEqual(result["mecanica"]["tipo_dano"], "igneo")

    def test_web_is_cube_with_dex_save_and_restrained(self):
        result = resolver_magia({"magia": "teia", "espaco": 2})
        self.assertEqual(result["mecanica"]["area"], {"forma": "cubo", "lado_m": 6})
        self.assertEqual(result["mecanica"]["salvaguarda"], "destreza")
        self.assertEqual(result["mecanica"]["condicao"], "contido")
        self.assertEqual(result["duracao"], "concentração, até 1 hora")

    def test_dispel_magic_ends_spells_up_to_slot_level(self):
        result = resolver_magia({"magia": "dissipar magia", "espaco": 5})
        self.assertEqual(result["mecanica"]["dissipa_ate_circulo"], 5)

    def test_counterspell_is_reaction(self):
        result = resolver_magia({"magia": "contramagia", "espaco": 3})
        self.assertEqual(result["mecanica"]["acao"], "reacao")
        self.assertEqual(result["mecanica"]["salvaguarda"], "constituicao")

    def test_feather_fall_is_reaction_for_up_to_five(self):
        result = resolver_magia({"magia": "queda suave", "espaco": 1})
        self.assertEqual(result["mecanica"]["alvos"], 5)
        self.assertEqual(result["mecanica"]["acao"], "reacao")

    def test_lesser_restoration_removes_one_listed_condition(self):
        result = resolver_magia({"magia": "restauração menor", "espaco": 2})
        self.assertEqual(result["mecanica"]["acao"], "bonus")
        self.assertIn("envenenado", result["mecanica"]["condicoes_removiveis"])

    def test_protection_from_energy_lists_five_damage_types(self):
        result = resolver_magia({"magia": "proteção contra energia", "espaco": 3})
        self.assertEqual(len(result["mecanica"]["tipos_escolha"]), 5)
        self.assertTrue(result["concentracao"])


class TruquesEPrimeiroCirculoTests(unittest.TestCase):
    """Lote de truques e magias de 1.º círculo do PHB 2024 (texto oficial)."""

    def test_cantrip_dice_scale_with_character_level(self):
        from rule_engine.spells import mecanica_de_magia
        self.assertEqual(mecanica_de_magia("chicote de espinhos", nivel_personagem=5)["dados_dano"], "2d6")
        self.assertEqual(mecanica_de_magia("chicote de espinhos", nivel_personagem=17)["dados_dano"], "4d6")
        self.assertEqual(mecanica_de_magia("raio de gelo", nivel_personagem=11)["dados_dano"], "3d8")

    def test_eldritch_blast_like_beams_scale_targets_not_dice(self):
        from rule_engine.spells import mecanica_de_magia
        mec = mecanica_de_magia("raio místico", nivel_personagem=11)
        self.assertEqual(mec["dados_dano"], "1d10")
        self.assertEqual(mec["alvos"], 3)

    def test_acudir_range_doubles_at_5_11_17(self):
        from rule_engine.spells import mecanica_de_magia
        self.assertEqual(mecanica_de_magia("acudir os moribundos", nivel_personagem=5)["alcance_m"], 9)
        self.assertEqual(mecanica_de_magia("acudir os moribundos", nivel_personagem=17)["alcance_m"], 36)

    def test_cantrip_does_not_consume_slot(self):
        result = resolver_magia({"magia": "raio de gelo"})
        self.assertEqual(result["resultado"], "conjurada")
        self.assertEqual(result["mecanica"]["dados_dano"], "1d8")

    def test_vitalidade_vazia_adds_five_temp_hp_per_extra_slot_level(self):
        result = resolver_magia({"magia": "vitalidade vazia", "espaco": 3})
        self.assertEqual(result["mecanica"]["pv_temporarios_extra"], 10)
        self.assertEqual(result["mecanica"]["pv_temporarios_base"], "2d4")

    def test_salto_targets_scale_with_slot(self):
        result = resolver_magia({"magia": "salto", "espaco": 3})
        self.assertEqual(result["mecanica"]["alvos"], 3)

    def test_dissipar_style_detection_and_identify_are_resolved(self):
        self.assertEqual(resolver_magia({"magia": "detectar magia", "espaco": 1})["resultado"], "conjurada")
        self.assertEqual(resolver_magia({"magia": "identificar", "espaco": 1})["resultado"], "conjurada")

    def test_resistance_lists_eleven_damage_types(self):
        result = resolver_magia({"magia": "resistência"})
        self.assertEqual(len(result["mecanica"]["tipos_escolha"]), 11)
        self.assertEqual(result["mecanica"]["reducao_dano_base"], "1d4")


if __name__ == "__main__":
    unittest.main()
