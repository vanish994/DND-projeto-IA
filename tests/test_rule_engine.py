import unittest

from rule_engine import (
    bonus_proficiencia,
    build_default_engine,
    modificador_atributo,
    Participante,
    RastreadorCombate,
    EstadoVital,
    resolver_teste_d20,
)


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

    def test_attack_hits_and_is_not_critical(self):
        result = self.engine.evaluate({"type": "attack", "roll": 12, "modifier": 5, "target_ac": 17})
        self.assertEqual(result.outcome["result"], "hit")
        self.assertFalse(result.outcome["critical"])
        self.assertEqual(result.matched_rules, ["attack.meets-ac"])

    def test_natural_twenty_attack_is_critical(self):
        result = self.engine.evaluate({"type": "attack", "roll": 20, "modifier": -2, "target_ac": 25})
        self.assertTrue(result.outcome["critical"])
        self.assertEqual(result.outcome["reason"], "natural_20")

    def test_critical_damage_doubles_dice_not_modifier(self):
        result = self.engine.evaluate({
            "type": "damage", "damage_dice": [5, 3], "damage_modifier": 4, "critical": True,
        })
        self.assertEqual(result.outcome["total"], 20)
        self.assertEqual(result.outcome["dice_count"], 4)

    def test_saving_throw_fails_below_dc(self):
        result = self.engine.evaluate({"type": "saving_throw", "roll": 9, "modifier": 2, "dc": 15})
        self.assertEqual(result.outcome["result"], "failure")
        self.assertEqual(result.matched_rules, ["saving-throw.below-dc"])

    def test_natural_one_saving_throw_overrides_total(self):
        result = self.engine.evaluate({"type": "saving_throw", "roll": 1, "modifier": 20, "dc": 10})
        self.assertEqual(result.outcome["reason"], "natural_1")

    def test_spell_cast_is_blocked_without_slot(self):
        result = self.engine.evaluate({
            "type": "spell_cast", "spell_level": 3, "slot_level": 3, "has_slot": False,
        })
        self.assertEqual(result.outcome["result"], "blocked")
        self.assertEqual(result.outcome["reason"], "no_slot")

    def test_spell_cast_replaces_previous_concentration(self):
        result = self.engine.evaluate({
            "type": "spell_cast", "spell_level": 2, "slot_level": 3, "has_slot": True,
            "concentration_required": True, "concentrating": True,
        })
        self.assertEqual(result.outcome["result"], "cast")
        self.assertTrue(result.outcome["ends_previous_concentration"])

    def test_spell_cast_is_blocked_when_slot_is_too_low(self):
        result = self.engine.evaluate({
            "type": "spell_cast", "spell_level": 4, "slot_level": 2, "has_slot": True,
        })
        self.assertEqual(result.outcome["reason"], "slot_level_too_low")

    def test_immune_target_does_not_receive_condition(self):
        result = self.engine.evaluate({
            "type": "condition", "operation": "apply", "condition": "poisoned",
            "immunities": ["poisoned"],
        })
        self.assertEqual(result.outcome["result"], "not_applied")

    def test_active_condition_can_be_removed(self):
        result = self.engine.evaluate({
            "type": "condition", "operation": "remove", "condition": "restrained",
            "active_conditions": ["restrained"],
        })
        self.assertEqual(result.outcome["result"], "removed")

    def test_conditions_can_cancel_advantage_and_disadvantage(self):
        result = self.engine.evaluate({
            "type": "condition_effect", "action": "attack",
            "attacker_conditions": ["poisoned"], "target_conditions": ["blinded"],
        })
        self.assertEqual(result.outcome["result"], "normal")

    def test_attribute_modifier_uses_floor_for_odd_values(self):
        self.assertEqual(modificador_atributo(1), -5)
        self.assertEqual(modificador_atributo(9), -1)
        self.assertEqual(modificador_atributo(10), 0)
        self.assertEqual(modificador_atributo(20), 5)

    def test_proficiency_bonus_uses_level_boundaries(self):
        self.assertEqual(bonus_proficiencia(1), 2)
        self.assertEqual(bonus_proficiencia(4), 2)
        self.assertEqual(bonus_proficiencia(5), 3)
        self.assertEqual(bonus_proficiencia(17), 6)
        self.assertEqual(bonus_proficiencia(30), 9)

    def test_advantage_selects_highest_d20(self):
        result = resolver_teste_d20([4, 18], vantagem=True, modificador=2, cd=20)
        self.assertEqual(result.dado_selecionado, 18)
        self.assertEqual(result.total, 20)
        self.assertTrue(result.sucesso)

    def test_disadvantage_selects_lowest_d20(self):
        result = resolver_teste_d20([4, 18], desvantagem=True, modificador=2, cd=10)
        self.assertEqual(result.dado_selecionado, 4)
        self.assertFalse(result.sucesso)

    def test_advantage_and_disadvantage_cancel(self):
        result = resolver_teste_d20([4], vantagem=True, desvantagem=True)
        self.assertEqual(result.dado_selecionado, 4)
        self.assertFalse(result.vantagem)
        self.assertFalse(result.desvantagem)

    def test_initiative_orders_by_roll_then_tiebreak(self):
        rastreador = RastreadorCombate([
            Participante("Goblin", 12, 1),
            Participante("Aventureiro", 12, 4),
            Participante("Dragão", 18, 0),
        ])
        self.assertEqual([p.identificador for p in rastreador.ordem], ["Dragão", "Aventureiro", "Goblin"])

    def test_round_and_turn_advance_in_order(self):
        rastreador = RastreadorCombate([
            Participante("A", 10), Participante("B", 5),
        ])
        self.assertEqual(rastreador.iniciar_proximo_turno().identificador, "A")
        self.assertEqual(rastreador.rodada, 1)
        self.assertEqual(rastreador.iniciar_proximo_turno().identificador, "B")
        self.assertEqual(rastreador.rodada, 1)
        self.assertEqual(rastreador.iniciar_proximo_turno().identificador, "A")
        self.assertEqual(rastreador.rodada, 2)

    def test_turn_resources_are_limited_and_reset_next_turn(self):
        rastreador = RastreadorCombate([Participante("A", 10)])
        rastreador.iniciar_proximo_turno()
        rastreador.gastar("acao")
        with self.assertRaises(ValueError):
            rastreador.gastar("acao")
        rastreador.iniciar_proximo_turno()
        rastreador.gastar("acao")

    def test_movement_and_dash(self):
        rastreador = RastreadorCombate(
            [Participante("A", 10)], deslocamentos={"A": 9}
        )
        turno = rastreador.iniciar_proximo_turno()
        self.assertEqual(turno.movimento_restante, 9)
        rastreador.mover(3)
        self.assertEqual(rastreador.correr(), 15)
        rastreador.mover(15)
        self.assertEqual(turno.movimento_restante, 0)

    def test_surprised_participant_cannot_act_on_first_turn(self):
        rastreador = RastreadorCombate([
            Participante("A", 10, surpreendido=True),
        ], deslocamentos={"A": 9})
        turno = rastreador.iniciar_proximo_turno()
        self.assertTrue(turno.surpreendido)
        self.assertFalse(turno.acao_disponivel)
        self.assertEqual(turno.movimento_restante, 0)

    def test_disengage_blocks_opportunity_attacks(self):
        rastreador = RastreadorCombate([Participante("A", 10)])
        turno = rastreador.iniciar_proximo_turno()
        efeito = rastreador.executar_acao("desengajar")
        self.assertTrue(efeito["ataques_oportunidade_bloqueados"])
        self.assertTrue(turno.ataques_oportunidade_bloqueados)

    def test_dodge_marks_turn_as_dodging(self):
        rastreador = RastreadorCombate([Participante("A", 10)])
        turno = rastreador.iniciar_proximo_turno()
        rastreador.executar_acao("esquivar")
        self.assertTrue(turno.esquivando)

    def test_ready_requires_trigger_and_response(self):
        rastreador = RastreadorCombate([Participante("A", 10)])
        rastreador.iniciar_proximo_turno()
        with self.assertRaises(ValueError):
            rastreador.executar_acao("preparar", gatilho="", resposta="atacar")
        efeito = rastreador.executar_acao(
            "preparar", gatilho="o inimigo aparecer", resposta="usar o arco"
        )
        self.assertEqual(efeito["resultado"], "executada")

    def test_hide_search_and_spell_actions_return_required_follow_up(self):
        rastreador = RastreadorCombate([Participante("A", 10)])
        rastreador.iniciar_proximo_turno()
        self.assertTrue(rastreador.executar_acao("esconder")["requer_teste_furtividade"])
        rastreador.iniciar_proximo_turno()
        self.assertTrue(rastreador.executar_acao("procurar")["requer_teste_percepcao_ou_investigacao"])
        rastreador.iniciar_proximo_turno()
        self.assertTrue(rastreador.executar_acao("usar_magia")["deve_validar_conjuracao"])

    def test_difficult_terrain_costs_extra_movement(self):
        rastreador = RastreadorCombate([Participante("A", 10)], deslocamentos={"A": 9})
        turno = rastreador.iniciar_proximo_turno()
        rastreador.mover(3, terreno_dificil=True)
        self.assertEqual(turno.movimento_restante, 3)

    def test_opportunity_attack_is_allowed_when_leaving_reach(self):
        result = self.engine.evaluate({
            "type": "opportunity_attack", "saiu_do_alcance": True,
            "reacao_disponivel": True,
        })
        self.assertEqual(result.outcome["resultado"], "permitido")
        self.assertTrue(result.outcome["reacao_gasta"])

    def test_disengage_teleport_and_forced_movement_block_opportunity_attack(self):
        for facts in (
            {"desengajou": True},
            {"teleportou": True},
            {"movimento_forcado": True},
        ):
            result = self.engine.evaluate({
                "type": "opportunity_attack", "saiu_do_alcance": True,
                "reacao_disponivel": True, **facts,
            })
            self.assertEqual(result.outcome["resultado"], "bloqueado")

    def test_shove_uses_strength_modifier_and_can_knock_prone(self):
        result = self.engine.evaluate({
            "type": "shove", "forca_modificador": 4, "bonus_proficiencia": 3,
            "tamanho_atacante": 2, "tamanho_alvo": 2,
            "rolagem": 8, "modificador_salvaguarda": 2, "efeito": "caido",
        })
        self.assertEqual(result.outcome["cd"], 15)
        self.assertEqual(result.outcome["resultado"], "aplicado")
        self.assertEqual(result.outcome["efeito"], "caido")

    def test_grapple_is_blocked_against_target_two_sizes_larger(self):
        result = self.engine.evaluate({
            "type": "grapple", "forca_modificador": 3, "bonus_proficiencia": 2,
            "tamanho_atacante": 1, "tamanho_alvo": 3,
            "rolagem": 1, "modificador_salvaguarda": -1,
        })
        self.assertEqual(result.outcome["resultado"], "bloqueado")
        self.assertEqual(result.outcome["motivo"], "tamanho_invalido")

    def test_grapple_applies_immobilized_and_can_be_escaped(self):
        result = self.engine.evaluate({
            "type": "grapple", "forca_modificador": 3, "bonus_proficiencia": 2,
            "tamanho_atacante": 2, "tamanho_alvo": 2,
            "rolagem": 5, "modificador_salvaguarda": 1,
        })
        self.assertEqual(result.outcome["resultado"], "aplicado")
        self.assertEqual(result.outcome["condicao"], "imobilizado")
        escape = self.engine.evaluate({
            "type": "grapple_escape", "rolagem": 13, "modificador": 2,
            "cd_agarramento": result.outcome["cd"],
        })
        self.assertEqual(escape.outcome["resultado"], "escapou")

    def test_damage_consumes_temporary_hit_points_first(self):
        estado = EstadoVital(20, 20, pv_temporarios=5)
        result = self.engine.evaluate({"type": "damage_application", "estado": estado, "damage": 8})
        self.assertEqual(result.outcome["dano_absorvido_pv_temporarios"], 5)
        self.assertEqual(estado.pv_atuais, 17)
        self.assertEqual(estado.pv_temporarios, 0)

    def test_resistance_then_vulnerability_and_immunity(self):
        from rule_engine import ajustar_dano
        self.assertEqual(ajustar_dano(25, resistente=True), 12)
        self.assertEqual(ajustar_dano(25, vulneravel=True), 50)
        self.assertEqual(ajustar_dano(25, imune=True), 0)

    def test_damage_application_uses_damage_type_and_origin(self):
        estado = EstadoVital(20, 20)
        result = self.engine.evaluate({
            "type": "damage_application", "estado": estado, "damage": 20,
            "damage_type": "fogo", "source": "bola de fogo", "resistances": ["fogo"],
        })
        self.assertEqual(result.outcome["dano_total"], 10)
        self.assertEqual(result.outcome["tipo_dano"], "fogo")
        self.assertEqual(result.outcome["origem"], "bola de fogo")

    def test_healing_removes_unconsciousness_without_exceeding_maximum(self):
        estado = EstadoVital(20, 0, inconsciente=True)
        result = self.engine.evaluate({"type": "healing", "estado": estado, "amount": 25})
        self.assertEqual(result.outcome["pv_atuais"], 20)
        self.assertFalse(estado.inconsciente)

    def test_death_save_natural_one_counts_as_two_failures(self):
        estado = EstadoVital(20, 0, inconsciente=True)
        self.engine.evaluate({"type": "death_save", "estado": estado, "roll": 1})
        self.assertEqual(estado.salvaguardas_falha, 2)

    def test_three_death_save_successes_stabilize(self):
        estado = EstadoVital(20, 0, inconsciente=True)
        for _ in range(3):
            self.engine.evaluate({"type": "death_save", "estado": estado, "roll": 10})
        self.assertTrue(estado.estavel)

    def test_exhaustion_six_kills_and_long_rest_reduces_one(self):
        estado = EstadoVital(20, 20)
        self.engine.evaluate({"type": "exhaustion", "estado": estado, "levels": 5})
        self.assertEqual(estado.exaustao, 5)
        self.engine.evaluate({"type": "long_rest", "estado": estado, "duration_hours": 8})
        self.assertEqual(estado.exaustao, 4)
        self.engine.evaluate({"type": "exhaustion", "estado": estado, "levels": 2})
        self.assertTrue(estado.morto)

    def test_short_rest_spends_hit_dice_and_long_rest_restores_pv(self):
        estado = EstadoVital(20, 5)
        curto = self.engine.evaluate({
            "type": "short_rest", "estado": estado,
            "hit_dice_rolls": [4, 6], "constitution_modifier": 2, "duration_hours": 1,
        })
        self.assertEqual(curto.outcome["pv_atuais"], 19)
        estado.pv_atuais = 10
        self.engine.evaluate({"type": "long_rest", "estado": estado, "duration_hours": 8})
        self.assertEqual(estado.pv_atuais, 20)

    def test_interrupted_rest_does_not_grant_benefits(self):
        estado = EstadoVital(20, 5)
        result = self.engine.evaluate({
            "type": "short_rest", "estado": estado, "duration_hours": 1,
            "interrupted": True, "hit_dice_rolls": [8],
        })
        self.assertEqual(result.outcome["resultado"], "interrompido_ou_invalido")
        self.assertEqual(estado.pv_atuais, 5)

    def test_long_rest_requires_sixteen_hour_interval(self):
        estado = EstadoVital(20, 5)
        result = self.engine.evaluate({
            "type": "long_rest", "estado": estado, "duration_hours": 8,
            "hours_since_last_long_rest": 8,
        })
        self.assertEqual(result.outcome["resultado"], "intervalo_insuficiente")
        self.assertEqual(estado.pv_atuais, 5)

    def test_long_rest_returns_declared_resources(self):
        estado = EstadoVital(20, 5)
        result = self.engine.evaluate({
            "type": "long_rest", "estado": estado, "duration_hours": 8,
            "recoverable_resources": {"dados_de_vida": "todos", "espacos_de_magia": "todos"},
        })
        self.assertEqual(result.outcome["recursos_recuperados"]["espacos_de_magia"], "todos")

    def test_grid_distance_and_creature_space(self):
        from rule_engine import distancia_grade, espaco_por_tamanho
        self.assertEqual(distancia_grade(3, 2), 3)
        self.assertEqual(distancia_grade(3, 2, diagonal_alternada=True), 4)
        self.assertEqual(espaco_por_tamanho("médio"), 1)
        self.assertEqual(espaco_por_tamanho("grande"), 2)

    def test_range_allows_normal_and_extended_ranged_attack(self):
        normal = self.engine.evaluate({
            "type": "range", "distance": 9, "range": 18,
            "maximum_range": 72, "ranged_attack": True,
        })
        self.assertFalse(normal.outcome["desvantagem_por_alcance"])
        extended = self.engine.evaluate({
            "type": "range", "distance": 36, "range": 18,
            "maximum_range": 72, "ranged_attack": True,
        })
        self.assertTrue(extended.outcome["desvantagem_por_alcance"])

    def test_cover_adds_ac_bonus_and_total_cover_blocks(self):
        meia = self.engine.evaluate({"type": "cover", "cover": "meia"})
        self.assertEqual(meia.outcome["bonus_ca"], 2)
        total = self.engine.evaluate({"type": "cover", "cover": "total"})
        self.assertEqual(total.outcome["resultado"], "bloqueado")

    def test_attack_geometry_checks_range_line_of_sight_and_cover(self):
        result = self.engine.evaluate({
            "type": "attack_geometry", "distance": 12, "range": 18,
            "maximum_range": 72, "attack_a_distancia": True,
            "cover": "tres_quartos",
        })
        self.assertEqual(result.outcome["resultado"], "permitido")
        self.assertEqual(result.outcome["bonus_ca_por_cobertura"], 5)

    def test_fall_deals_one_d6_per_three_meters_and_knocks_prone(self):
        result = self.engine.evaluate({
            "type": "fall", "distance": 6, "rolls": [3, 4],
        })
        self.assertEqual(result.outcome["dados_d6"], 2)
        self.assertEqual(result.outcome["dano"], 7)
        self.assertEqual(result.outcome["condicao"], "caido")

    def test_special_senses_handle_darkness_and_invisibility(self):
        normal = self.engine.evaluate({
            "type": "senses", "sense": "visao_normal", "darkness": True,
        })
        self.assertEqual(normal.outcome["resultado"], "não_percebido")
        blindsight = self.engine.evaluate({
            "type": "senses", "sense": "visao_as_cegas", "invisible_target": True,
        })
        self.assertTrue(blindsight.outcome["ignora_invisibilidade"])

    def test_special_movement_doubles_crawling_cost_and_standing_costs_half_speed(self):
        rastejar = self.engine.evaluate({
            "type": "special_movement", "distance": 3,
            "movement_remaining": 6, "crawling": True,
        })
        self.assertEqual(rastejar.outcome["custo"], 6)
        levantar = self.engine.evaluate({
            "type": "special_movement", "stand_from_prone": True,
            "movement_max": 9, "movement_remaining": 9,
        })
        self.assertEqual(levantar.outcome["custo"], 4)

    def test_mounting_requires_a_willing_mount_one_size_larger(self):
        bloqueado = self.engine.evaluate({
            "type": "mounted_combat", "action": "montar",
            "montaria_disposta": True, "tamanho_montaria": 2,
            "tamanho_cavaleiro": 2,
        })
        self.assertEqual(bloqueado.outcome["resultado"], "bloqueado")
        permitido = self.engine.evaluate({
            "type": "mounted_combat", "action": "montar",
            "montaria_disposta": True, "tamanho_montaria": 3,
            "tamanho_cavaleiro": 2, "deslocamento_cavaleiro": 9,
        })
        self.assertEqual(permitido.outcome["custo_movimento"], 4)

    def test_mount_fall_requires_dexterity_save_dc_ten(self):
        result = self.engine.evaluate({
            "type": "mounted_combat", "action": "queda_montaria",
            "salvaguarda_destreza": 8,
        })
        self.assertEqual(result.outcome["resultado"], "caiu")
        self.assertEqual(result.outcome["cd"], 10)

    def test_underwater_attacks_apply_weapon_and_range_limits(self):
        melee = self.engine.evaluate({
            "type": "underwater_attack", "submerso": True,
            "tipo_ataque": "corpo_a_corpo", "propriedade_arma": "cortante",
        })
        self.assertTrue(melee.outcome["desvantagem"])
        ranged = self.engine.evaluate({
            "type": "underwater_attack", "submerso": True,
            "tipo_ataque": "a_distancia", "distancia": 30, "alcance": 18,
        })
        self.assertEqual(ranged.outcome["resultado"], "bloqueado")

    def test_object_damage_reduces_hit_points_and_can_destroy_object(self):
        result = self.engine.evaluate({
            "type": "object_damage", "pontos_de_vida": 10, "dano": 10, "ca": 15,
        })
        self.assertEqual(result.outcome["resultado"], "destruido")
        self.assertEqual(result.outcome["pv_restantes"], 0)


if __name__ == "__main__":
    unittest.main()
