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

    def test_surprised_participant_keeps_actions_in_2024(self):
        rastreador = RastreadorCombate([
            Participante("A", 10, surpreendido=True),
        ], deslocamentos={"A": 9})
        turno = rastreador.iniciar_proximo_turno()
        self.assertTrue(turno.surpreendido)
        self.assertTrue(turno.acao_disponivel)
        self.assertTrue(turno.acao_bonus_disponivel)
        self.assertTrue(turno.reacao_disponivel)
        self.assertEqual(turno.movimento_restante, 9)

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

    def test_all_player_handbook_conditions_are_available(self):
        from rule_engine import CONDICOES
        self.assertEqual(len(CONDICOES), 15)
        self.assertIn("cego", CONDICOES)
        self.assertNotIn("lento", CONDICOES)
        self.assertIn("inconsciente", CONDICOES)

    def test_condition_state_applies_immunity_and_expires_duration(self):
        from rule_engine import EstadoCondicoes
        estado = EstadoCondicoes(imunidades={"envenenado"})
        immune = self.engine.evaluate({
            "type": "condition_state", "estado": estado,
            "operation": "apply", "condition": "envenenado", "duration": 2,
        })
        self.assertEqual(immune.outcome["resultado"], "não_aplicada")
        applied = self.engine.evaluate({
            "type": "condition_state", "estado": estado,
            "operation": "apply", "condition": "cego", "duration": 2,
        })
        self.assertEqual(applied.outcome["resultado"], "aplicada")
        tick = self.engine.evaluate({
            "type": "condition_state", "estado": estado,
            "operation": "tick", "units": 2,
        })
        self.assertEqual(tick.outcome["encerradas"], ["cego"])

    def test_condition_effects_block_actions_movement_and_speech(self):
        result = self.engine.evaluate({
            "type": "condition_effect", "action": "move",
            "target_conditions": ["unconscious", "grappled", "deafened"],
        })
        self.assertFalse(result.outcome["pode_mover"])
        self.assertFalse(result.outcome["pode_realizar_acoes"])
        self.assertFalse(result.outcome["pode_falar"])
        self.assertFalse(result.outcome["pode_ouvir"])

    def test_paralyzed_target_fails_strength_and_dexterity_saves_and_is_critically_hit(self):
        result = self.engine.evaluate({
            "type": "condition_effect", "action": "attack",
            "target_conditions": ["paralyzed"], "distance": "corpo_a_corpo", "distancia_m": 1.5,
        })
        self.assertTrue(result.outcome["acerto_critico_automatico"])
        saves = self.engine.evaluate({
            "type": "condition_effect", "action": "save",
            "target_conditions": ["paralyzed"],
        })
        self.assertTrue(saves.outcome["falha_salvaguardas_forca_destreza"])

    def test_invisible_and_blinded_conditions_create_opposing_attack_effects(self):
        result = self.engine.evaluate({
            "type": "condition_effect", "action": "attack",
            "attacker_conditions": ["blinded"], "target_conditions": ["invisible"],
        })
        self.assertEqual(result.outcome["resultado"], "desvantagem")

    def test_frightened_charmed_prone_and_exhaustion_have_effects(self):
        result = self.engine.evaluate({
            "type": "condition_effect", "action": "move",
            "target_conditions": ["frightened", "charmed", "prone", "exhaustion"],
            "exhaustion_niveis": 2,
        })
        self.assertTrue(result.outcome["não_pode_se_aproximar_da_fonte"])
        self.assertTrue(result.outcome["não_pode_atacar_o_enfeiticador"])
        self.assertEqual(result.outcome["movimento_para_levantar"], "metade_do_deslocamento")
        self.assertEqual(result.outcome["deslocamento_reduzido_m"], 3)
        self.assertEqual(result.outcome["modificador_d20"], -4)

    def test_armor_class_uses_dexterity_cap_and_shield(self):
        result = self.engine.evaluate({
            "type": "armor_class", "armor": "media", "armor_bonus": 4,
            "dexterity_modifier": 4, "shield": True, "shield_bonus": 2,
        })
        self.assertEqual(result.outcome["ca"], 18)

    def test_heavy_armor_requires_strength_and_proficiency(self):
        weak = self.engine.evaluate({
            "type": "armor_class", "armor": "pesada", "armor_bonus": 16,
            "strength": 12, "minimum_strength": 13,
        })
        self.assertEqual(weak.outcome["motivo"], "forca_insuficiente")
        untrained = self.engine.evaluate({
            "type": "armor_class", "armor": "leve", "dexterity_modifier": 2,
            "armor_bonus": 1, "armor_proficient": False,
        })
        self.assertEqual(untrained.outcome["motivo"], "sem_proficiencia_em_armadura")

    def test_weapon_properties_mastery_and_two_light_weapons(self):
        weapon = self.engine.evaluate({
            "type": "weapon", "weapon": "espada curta",
            "properties": ["leve", "acuidade"], "proficient": True, "mastery": "agil",
        })
        self.assertEqual(weapon.outcome["resultado"], "permitida")
        two = self.engine.evaluate({
            "type": "two_weapon_attack", "primary_properties": ["leve"],
            "secondary_properties": ["leve"],
        })
        self.assertTrue(two.outcome["usa_acao_bonus"])

    def test_carrying_capacity_detects_overload(self):
        result = self.engine.evaluate({
            "type": "carrying_capacity", "strength": 10, "weight": 76,
        })
        self.assertEqual(result.outcome["resultado"], "sobrecarregado")
        self.assertEqual(result.outcome["capacidade"], 75)

    def test_spell_casting_validates_preparation_components_and_ritual(self):
        blocked = self.engine.evaluate({
            "type": "spell_cast_complete", "spell": "mísseis mágicos",
            "spell_level": 1, "prepared": False, "has_slot": True,
        })
        self.assertEqual(blocked.outcome["motivo"], "magia_nao_preparada")
        ritual = self.engine.evaluate({
            "type": "spell_cast_complete", "spell": "detectar magia",
            "spell_level": 1, "ritual": True, "ritualista": True,
            "required_components": ["V", "S"], "available_components": ["V", "S"],
        })
        self.assertEqual(ritual.outcome["tempo_extra_minutos"], 10)

    def test_spell_targets_and_area(self):
        target = self.engine.evaluate({
            "type": "spell_targets", "distance": 12, "range": 18,
            "line_of_effect": True, "targets": 2, "max_targets": 3,
        })
        self.assertEqual(target.outcome["resultado"], "alvos_validos")
        area = self.engine.evaluate({
            "type": "spell_area", "shape": "cone", "size": 18,
        })
        self.assertEqual(area.outcome["resultado"], "area_valida")

    def test_catalog_contains_weapons_armor_equipment_and_spells(self):
        from rule_engine import CATALOGO_ARMAS, CATALOGO_ARMADURAS, CATALOGO_EQUIPAMENTOS, CATALOGO_MAGIAS
        self.assertGreaterEqual(len(CATALOGO_ARMAS), 34)
        self.assertGreaterEqual(len(CATALOGO_ARMADURAS), 13)
        self.assertGreaterEqual(len(CATALOGO_EQUIPAMENTOS), 45)
        self.assertGreaterEqual(len(CATALOGO_MAGIAS), 300)
        self.assertIn("Bola de Fogo", CATALOGO_MAGIAS)

    def test_catalog_lookup_is_available_through_rule_engine(self):
        result = self.engine.evaluate({
            "type": "catalog_lookup", "category": "armas", "name": "Rapieira",
        })
        self.assertEqual(result.outcome["resultado"], "encontrado")
        self.assertIn("acuidade", result.outcome["data"]["propriedades"])
        listed = self.engine.evaluate({"type": "catalog_list", "category": "armaduras"})
        self.assertIn("Placas", listed.outcome["names"])

    def test_standard_array_and_point_buy(self):
        from rule_engine import gerar_atributos_matriz_padrao, gerar_atributos_compra_pontos
        self.assertEqual(sum(gerar_atributos_matriz_padrao().values()), 72)
        bought = gerar_atributos_compra_pontos({
            "forca": 15, "destreza": 14, "constituicao": 13,
            "inteligencia": 10, "sabedoria": 10, "carisma": 8,
        })
        self.assertEqual(bought["forca"], 15)

    def test_character_creation_validates_class_species_and_subclass_level(self):
        result = self.engine.evaluate({
            "type": "character_creation", "name": "Lia", "species": "humano",
            "class": "guerreiro", "level": 3,
            "ability_scores": {"forca": 15, "destreza": 14, "constituicao": 13,
                                "inteligencia": 10, "sabedoria": 10, "carisma": 8},
            "subclass": "campeao", "background": "soldado",
        })
        self.assertEqual(result.outcome["resultado"], "criado")
        self.assertEqual(result.outcome["personagem"].bonus_proficiencia, 2)

    def test_subclass_cannot_be_selected_before_level_three(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate({
                "type": "character_creation", "name": "Lia", "species": "humano",
                "class": "guerreiro", "level": 2, "subclass": "campeao",
                "ability_scores": {"forca": 15, "destreza": 14, "constituicao": 13,
                                    "inteligencia": 10, "sabedoria": 10, "carisma": 8},
            })

    def test_level_up_grants_subclass_and_asi_or_feat_choices(self):
        subclass = self.engine.evaluate({"type": "level_up", "class": "mago", "current_level": 2})
        self.assertTrue(subclass.outcome["escolha_subclasse"])
        asi = self.engine.evaluate({"type": "level_up", "class": "mago", "current_level": 3})
        self.assertEqual(asi.outcome["escolha"], "aumento_de_atributo_ou_talento")

    def test_multiclass_checks_prerequisites(self):
        permitted = self.engine.evaluate({
            "type": "multiclass", "new_class": "mago",
            "ability_scores": {"forca": 8, "destreza": 10, "constituicao": 10,
                                "inteligencia": 13, "sabedoria": 10, "carisma": 10},
        })
        self.assertEqual(permitted.outcome["resultado"], "permitido")
        blocked = self.engine.evaluate({
            "type": "multiclass", "new_class": "paladino",
            "ability_scores": {"forca": 12, "destreza": 10, "constituicao": 10,
                                "inteligencia": 10, "sabedoria": 10, "carisma": 12},
        })
        self.assertEqual(blocked.outcome["resultado"], "bloqueado")

    def test_artificer_is_a_playable_class(self):
        from rule_engine import CLASSES
        self.assertEqual(CLASSES["artifice"]["dado_vida"], 8)
        result = self.engine.evaluate({
            "type": "character_creation", "name": "Nilo", "species": "gnomo",
            "class": "artifice", "level": 1,
            "ability_scores": {"forca": 8, "destreza": 14, "constituicao": 13,
                                "inteligencia": 15, "sabedoria": 10, "carisma": 10},
        })
        self.assertEqual(result.outcome["resultado"], "criado")

    def test_ravenloft_subclasses_are_available_at_level_three(self):
        from rule_engine import SUBCLASSES_RAVENLOFT
        self.assertEqual(len(SUBCLASSES_RAVENLOFT), 7)
        cases = [
            ("artifice", "reanimador"), ("bardo", "colegio_dos_espiritos"),
            ("clerigo", "dominio_da_sepultura"), ("guardiao", "guardiao_oculto"),
            ("ladino", "fantasma"), ("feiticeiro", "feiticaria_das_sombras"),
            ("bruxo", "patrono_morto_vivo"),
        ]
        scores = {"forca": 13, "destreza": 13, "constituicao": 13,
                  "inteligencia": 13, "sabedoria": 13, "carisma": 13}
        for classe, subclasse in cases:
            result = self.engine.evaluate({
                "type": "character_creation", "name": "Teste", "species": "humano",
                "class": classe, "level": 3, "subclass": subclasse,
                "ability_scores": scores,
            })
            self.assertEqual(result.outcome["resultado"], "criado")

    def test_class_progression_exposes_features_and_extra_asi_levels(self):
        from rule_engine import caracteristicas_no_nivel, subclasses_da_classe
        self.assertIn("Fúria", caracteristicas_no_nivel("barbaro", 1))
        self.assertIn("Lampejo de Gênio", caracteristicas_no_nivel("artifice", 7))
        self.assertIn("mestre_da_batalha", subclasses_da_classe("guerreiro"))
        fighter = self.engine.evaluate({"type": "level_up", "class": "guerreiro", "current_level": 5})
        self.assertEqual(fighter.outcome["nivel"], 6)
        self.assertIn("escolha", fighter.outcome)
        rogue = self.engine.evaluate({"type": "level_up", "class": "ladino", "current_level": 9})
        self.assertEqual(rogue.outcome["nivel"], 10)
        self.assertIn("escolha", rogue.outcome)

    def test_martial_extra_attack_and_fighter_progression(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "ataque_extra", "classe": "guerreiro", "nivel": 20})
        self.assertEqual(result.outcome["ataques"], 4)
        result = self.engine.evaluate({"type": "martial_feature", "feature": "ataque_extra", "classe": "barbaro", "nivel": 5})
        self.assertEqual(result.outcome["ataques"], 2)

    def test_barbarian_rage_has_damage_bonus_and_resistance(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "furia", "nivel": 10, "acao": "ativar"})
        self.assertEqual(result.outcome["resultado"], "ativada")
        self.assertEqual(result.outcome["dano_adicional"], 3)
        self.assertIn("contundente", result.outcome["resistencias"])
        blocked = self.engine.evaluate({"type": "martial_feature", "feature": "furia", "nivel": 1, "acao": "ativar", "armadura_pesada": True})
        self.assertEqual(blocked.outcome["resultado"], "bloqueado")

    def test_fighter_second_wind_and_weapon_mastery(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "recuperar_folego", "nivel": 5, "rolagem_d10": 7})
        self.assertEqual(result.outcome["cura"], 12)
        result = self.engine.evaluate({"type": "martial_feature", "feature": "maestria_em_arma", "classe": "guerreiro", "nivel": 10, "armas": ["espada", "machado", "arco", "lança", "martelo"]})
        self.assertEqual(result.outcome["resultado"], "resolvido")

    def test_rogue_sneak_attack_scales_and_uncanny_dodge(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "ataque_furtivo", "nivel": 11, "vantagem": True, "acuidade_ou_distancia": True})
        self.assertEqual(result.outcome["dados"], 6)
        result = self.engine.evaluate({"type": "martial_feature", "feature": "esquiva_sobrenatural", "dano": 17})
        self.assertEqual(result.outcome["dano_final"], 8)

    def test_monk_focus_and_deflect_attacks(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "foco_monge", "nivel": 10, "acao": "torrente_de_golpes", "foco_disponivel": 10})
        self.assertIn("tres_ataques_desarmados", result.outcome["efeitos"])
        result = self.engine.evaluate({"type": "martial_feature", "feature": "defletir_ataques", "nivel": 3, "rolagem_d10": 6, "modificador_destreza": 3, "dano": 9, "foco_disponivel": 1})
        self.assertEqual(result.outcome["dano_restante"], 0)
        self.assertTrue(result.outcome["pode_redirecionar"])

    def test_martial_evasion(self):
        result = self.engine.evaluate({"type": "martial_feature", "feature": "evasao", "dano": 30, "sucesso": True})
        self.assertEqual(result.outcome["dano_final"], 0)

    def test_martial_subclass_catalog_contains_all_four_fighter_subclasses(self):
        from rule_engine import SUBCLASS_FEATURES
        for name in ("campeao", "cavaleiro_mistico", "combatente_psiquico", "mestre_da_batalha"):
            self.assertIn(name, SUBCLASS_FEATURES)
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "campeao", "nivel": 3, "caracteristica": "critico_aprimorado"})
        self.assertEqual(result.outcome["critico_com"], [19, 20])

    def test_barbarian_subclasses_resolve_core_features(self):
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "berserker", "nivel": 6, "caracteristica": "furia_irracional"})
        self.assertIn("amedrontado", result.outcome["imunidades"])
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "trilha_do_fanatico", "nivel": 3, "caracteristica": "furia_divina", "tipo_dano": "radiante"})
        self.assertEqual(result.outcome["tipo"], "radiante")

    def test_monk_and_rogue_subclasses_resolve_core_features(self):
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "combatente_das_sombras", "nivel": 6, "caracteristica": "passo_da_sombra"})
        self.assertEqual(result.outcome["teleporte"], 18)
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "assassino", "nivel": 3, "caracteristica": "assassinar", "alvo_surpreso": True})
        self.assertTrue(result.outcome["critico"])

    def test_unavailable_subclass_feature_is_blocked(self):
        result = self.engine.evaluate({"type": "martial_subclass_feature", "subclasse": "campeao", "nivel": 3, "caracteristica": "sobrevivente"})
        self.assertEqual(result.outcome["resultado"], "bloqueado")

    def test_full_caster_progression_uses_correct_ability_and_slots(self):
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "progressao_conjuracao", "classe": "mago", "nivel": 5, "inteligencia": 16})
        self.assertEqual(result.outcome["atributo_conjuracao"], "inteligencia")
        self.assertEqual(result.outcome["espacos"], [4, 3, 2])
        self.assertEqual(result.outcome["magias_preparadas"], 9)

    def test_bardic_inspiration_scales_and_recovers(self):
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "inspiracao_bardo", "nivel": 10, "carisma": 16})
        self.assertEqual(result.outcome["dado"], "d10")
        recovered = self.engine.evaluate({"type": "spellcaster_feature", "feature": "inspiracao_bardo", "nivel": 5, "carisma": 14, "acao": "recuperar"})
        self.assertEqual(recovered.outcome["recupera_em"], "descanso_curto_ou_longo")

    def test_cleric_channel_divinity_and_druid_wild_shape(self):
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "canalizar_divindade", "nivel": 7, "acao": "centelha_divina"})
        self.assertEqual(result.outcome["usos_maximos"], 3)
        self.assertIn("3d8", result.outcome["escalonamento"].values())
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "forma_selvagem", "nivel": 18, "forma": "fera"})
        self.assertTrue(result.outcome["pode_conjurar"])
        self.assertEqual(result.outcome["pontos_de_vida_temporarios"], 18)

    def test_wizard_spellbook_features(self):
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "livro_de_magias", "nivel": 1, "acao": "consultar"})
        self.assertEqual(result.outcome["magias_iniciais"], 6)
        result = self.engine.evaluate({"type": "spellcaster_feature", "feature": "livro_de_magias", "nivel": 9, "acao": "recuperacao_arcana"})
        self.assertEqual(result.outcome["limite_circulos"], 5)

    def test_warlock_pact_magic_invocations_and_mystic_arcanum(self):
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "bruxo", "nivel": 9})
        self.assertEqual(result.outcome["espacos"], 2)
        self.assertEqual(result.outcome["circulo"], 5)
        self.assertEqual(result.outcome["invocacoes"], 6)
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "bruxo", "nivel": 11, "acao": "arcana_mistica"})
        self.assertEqual(result.outcome["circulo"], 6)

    def test_sorcerer_metamagic_and_innate_sorcery(self):
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "feiticeiro", "nivel": 10, "acao": "metamagia"})
        self.assertEqual(result.outcome["opcoes_conhecidas"], 4)
        self.assertEqual(result.outcome["pontos_disponiveis"], 10)
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "feiticeiro", "nivel": 1, "acao": "feiticaria_inata"})
        self.assertEqual(result.outcome["bonus_cd"], 1)

    def test_ranger_progression_favored_enemy_and_nature_veil(self):
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "guardiao", "nivel": 9, "acao": "progressao"})
        self.assertEqual(result.outcome["atributo_conjuracao"], "sabedoria")
        self.assertEqual(result.outcome["espacos"], [4, 3, 2])
        result = self.engine.evaluate({"type": "advanced_caster_feature", "classe": "guardiao", "nivel": 14, "acao": "veu_da_natureza", "sabedoria": 16})
        self.assertTrue(result.outcome["invisivel"])
        self.assertEqual(result.outcome["usos"], 3)

    def test_all_phb_warlock_invocations_are_catalogued(self):
        from rule_engine import INVOCATIONS
        self.assertGreaterEqual(len(INVOCATIONS), 27)
        for name in ("explosao_agonizante", "lamina_sedenta", "pacto_da_corrente", "pacto_da_lamina", "pacto_do_tomo", "visao_da_bruxa", "vigor_infero"):
            self.assertIn(name, INVOCATIONS)

    def test_invocation_prerequisites_block_low_level_and_missing_pact(self):
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "visao_da_bruxa", "nivel": 9, "operation": "validate"})
        self.assertEqual(result.outcome["resultado"], "bloqueado")
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "lamina_sedenta", "nivel": 5, "operation": "validate"})
        self.assertEqual(result.outcome["motivo"], "pacto_obrigatorio")
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "explosao_agonizante", "nivel": 2, "truque_causa_dano": False, "operation": "validate"})
        self.assertEqual(result.outcome["motivo"], "truque_de_dano_obrigatorio")

    def test_invocation_effects_cover_blast_blade_vision_and_familiar(self):
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "explosao_agonizante", "nivel": 2, "carisma": 18, "truque_causa_dano": True})
        self.assertEqual(result.outcome["bonus_dano"], 4)
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "explosao_repulsiva", "nivel": 2, "truque_exige_jogada_ataque": True})
        self.assertEqual(result.outcome["empurra_metros"], 3)
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "visao_diabolica", "nivel": 2})
        self.assertEqual(result.outcome["visao_escuro_m"], 36)
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "investimento_do_mestre_da_corrente", "nivel": 5, "pactos": ["pacto_da_corrente"]})
        self.assertTrue(result.outcome["resistencia_familiar_reacao"])

    def test_pact_invocations_and_smite_effects(self):
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "pacto_da_lamina", "nivel": 1})
        self.assertEqual(result.outcome["atributo_ataque_dano"], "carisma")
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "lamina_sedenta", "nivel": 5, "pactos": ["pacto_da_lamina"]})
        self.assertEqual(result.outcome["ataques_com_arma_pacto"], 2)
        result = self.engine.evaluate({"type": "warlock_invocation", "invocacao": "punicao_mistica", "nivel": 5, "pactos": ["pacto_da_lamina"], "circulo_espaco": 3, "tamanho_alvo": "Grande"})
        self.assertEqual(result.outcome["dano_energetico"], 32)

    def test_talent_catalog_has_origin_general_and_epic_categories(self):
        from rule_engine import EPIC_FEATS, FEATS, GENERAL_FEATS, ORIGIN_FEATS
        self.assertGreaterEqual(len(ORIGIN_FEATS), 10)
        self.assertGreaterEqual(len(GENERAL_FEATS), 40)
        self.assertGreaterEqual(len(EPIC_FEATS), 8)
        self.assertIn("alerta", ORIGIN_FEATS)
        self.assertIn("conjurador_belico", GENERAL_FEATS)
        self.assertIn("dadiva_do_destino", EPIC_FEATS)
        self.assertEqual(FEATS["alerta"]["categoria"], "origem")

    def test_origin_talents_resolve_core_effects(self):
        result = self.engine.evaluate({"type": "feat", "talento": "alerta", "nivel": 1})
        self.assertIn("proficiência_iniciativa", result.outcome["efeitos"])
        result = self.engine.evaluate({"type": "feat", "talento": "vigoroso", "nivel": 5})
        self.assertEqual(result.outcome["pv_adicionais"], 10)
        result = self.engine.evaluate({"type": "feat", "talento": "sortudo", "nivel": 1, "bonus_proficiencia": 2})
        self.assertEqual(result.outcome["pontos_de_sorte"], 2)

    def test_general_talent_prerequisites_and_effects(self):
        blocked = self.engine.evaluate({"type": "feat", "talento": "conjurador_belico", "nivel": 4, "caracteristica_conjuracao": False})
        self.assertEqual(blocked.outcome["motivo"], "requer_conjuracao")
        result = self.engine.evaluate({"type": "feat", "talento": "conjurador_belico", "nivel": 4, "caracteristica_conjuracao": True})
        self.assertIn("vantagem_concentracao", result.outcome["efeitos"])
        result = self.engine.evaluate({"type": "feat", "talento": "sentinela", "nivel": 4, "forca": 13})
        self.assertIn("zera_deslocamento", result.outcome["efeitos"])

    def test_epic_talents_require_level_19_and_resolve_effects(self):
        blocked = self.engine.evaluate({"type": "feat", "talento": "dadiva_da_velocidade", "nivel": 18})
        self.assertEqual(blocked.outcome["motivo"], "nivel_insuficiente")
        result = self.engine.evaluate({"type": "feat", "talento": "dadiva_da_velocidade", "nivel": 19})
        self.assertEqual(result.outcome["deslocamento_adicional_m"], 9)
        result = self.engine.evaluate({"type": "feat", "talento": "dadiva_da_visao_verdadeira", "nivel": 19})
        self.assertEqual(result.outcome["visao_verdadeira_m"], 18)

    def test_spell_catalog_is_queryable_by_school_and_circle(self):
        from rule_engine import ESCOLAS, listar_magias, obter_magia
        self.assertEqual(len(ESCOLAS), 8)
        self.assertEqual(obter_magia("Bola de Fogo")["escola"], "evocação")
        self.assertTrue(all(m["escola"] == "evocação" for m in listar_magias("evocação", 3)))

    def test_spell_cast_validates_components_concentration_and_upcasting(self):
        result = self.engine.evaluate({"type": "spell_cast", "magia": "bola de fogo", "espaco": 5})
        self.assertEqual(result.outcome["circulo_usado"], 5)
        self.assertEqual(result.outcome["upcasting"], 2)
        self.assertIn("+1d6", result.outcome["escalonamento"]["dano"])
        result = self.engine.evaluate({"type": "spell_cast", "magia": "benção", "espaco": 1, "concentrando": "invisibilidade"})
        self.assertEqual(result.outcome["encerra_concentracao"], "invisibilidade")

    def test_spell_cast_blocks_missing_material_component_and_bad_slot(self):
        result = self.engine.evaluate({"type": "spell_cast", "magia": "bola de fogo", "espaco": 3, "componentes_disponiveis": ["V", "S"]})
        self.assertEqual(result.outcome["motivo"], "componentes_ausentes")
        result = self.engine.evaluate({"type": "spell_cast", "magia": "bola de fogo", "espaco": 2})
        self.assertEqual(result.outcome["motivo"], "circulo_invalido")

    def test_spell_lookup_rule_exposes_components(self):
        result = self.engine.evaluate({"type": "spell_catalog", "operation": "lookup", "magia": "armadura de agathys"})
        self.assertEqual(result.outcome["magia"]["circulo"], 1)
        self.assertIn("M", result.outcome["magia"]["componentes"])

    def test_coin_conversion_and_equipment_purchase(self):
        from rule_engine import converter_de_po, converter_para_po
        self.assertEqual(converter_para_po({"po": 1, "pp": 10}), 2.0)
        self.assertEqual(converter_de_po(2), {"po": 2})
        result = self.engine.evaluate({"type": "economy", "operation": "buy", "item": "Corda", "moedas": {"po": 2}})
        self.assertEqual(result.outcome["resultado"], "comprado")
        blocked = self.engine.evaluate({"type": "economy", "operation": "buy", "item": "Placas", "categoria": "armaduras", "moedas": {"po": 10}})
        self.assertEqual(blocked.outcome["motivo"], "saldo_insuficiente")

    def test_equipment_inventory_and_sale(self):
        result = self.engine.evaluate({"type": "equipment", "operation": "inventory", "forca": 10, "peso_atual": 70, "peso_adicionado": 10})
        self.assertEqual(result.outcome["resultado"], "sobrecarregado")
        result = self.engine.evaluate({"type": "economy", "operation": "sell", "item": "Corda", "moedas": {"po": 0}})
        self.assertEqual(result.outcome["recebe_po"], 0.5)

    def test_magic_item_attunement_limit_and_charges(self):
        result = self.engine.evaluate({"type": "magic_item", "operation": "attune", "item": "anel_de_protecao", "sintonizados": []})
        self.assertEqual(result.outcome["resultado"], "sintonizado")
        blocked = self.engine.evaluate({"type": "magic_item", "operation": "attune", "item": "amuleto_de_saude", "sintonizados": ["anel_de_protecao", "manto_de_protecao", "botas_de_velocidade"]})
        self.assertEqual(blocked.outcome["motivo"], "limite_de_tres_itens")
        result = self.engine.evaluate({"type": "magic_item", "operation": "use", "item": "varinha_de_misseis", "cargas": 2})
        self.assertEqual(result.outcome["cargas_restantes"], 1)

    def test_condition_effects_include_petrified_restraining_and_stunned_states(self):
        result = self.engine.evaluate({"type": "condition_effect", "action": "move", "target_conditions": ["petrified"]})
        self.assertEqual(result.outcome["deslocamento"], 0)
        self.assertTrue(result.outcome["resistencia_todos_danos"])
        self.assertTrue(result.outcome["imune_envenenado_e_doenca"])
        result = self.engine.evaluate({"type": "condition_effect", "action": "move", "target_conditions": ["restrained"]})
        self.assertEqual(result.outcome["deslocamento"], 0)
        self.assertTrue(result.outcome["desvantagem_salvaguarda_destreza"])
        result = self.engine.evaluate({"type": "condition_effect", "action": "move", "target_conditions": ["stunned"]})
        self.assertFalse(result.outcome["pode_realizar_reacoes"])
        self.assertTrue(result.outcome["falha_salvaguardas_forca_destreza"])

    def test_incapacitated_creature_cannot_speak_or_attack(self):
        from rule_engine import resolver_efeitos_condicao
        move = resolver_efeitos_condicao({"action": "move", "target_conditions": ["incapacitated"]})
        attack = resolver_efeitos_condicao({"action": "attack", "attacker_conditions": ["incapacitated"], "target_conditions": []})
        self.assertFalse(move["pode_falar"])
        self.assertEqual(attack["resultado"], "bloqueado")

    def test_frightened_and_poisoned_do_not_impose_saving_throw_disadvantage(self):
        from rule_engine import resolver_efeitos_condicao
        result = resolver_efeitos_condicao({"action": "save", "target_conditions": ["frightened", "poisoned"]})
        self.assertFalse(result["desvantagem_salvaguardas"])
        self.assertTrue(result["desvantagem_testes_habilidade"])
    def test_exhaustion_reduces_speed_and_does_not_mislabel_other_conditions(self):
        from rule_engine import resolver_efeitos_condicao
        result = resolver_efeitos_condicao({"action": "move", "target_conditions": ["exhaustion"], "exhaustion_niveis": 3})
        self.assertEqual(result["modificador_d20"], -6)
        self.assertEqual(result["deslocamento_reduzido_m"], 4.5)
        self.assertFalse(result["morre_no_nivel_6"])

    def test_short_rest_tracks_spent_hit_dice_and_long_rest_restores_them(self):
        estado = EstadoVital(20, 5, dados_vida_maximos=4)
        self.engine.evaluate({"type": "short_rest", "estado": estado, "hit_dice_rolls": [4, 6], "constitution_modifier": 2, "duration_hours": 1})
        self.assertEqual(estado.dados_vida_disponiveis, 2)
        self.engine.evaluate({"type": "long_rest", "estado": estado, "duration_hours": 8})
        self.assertEqual(estado.dados_vida_disponiveis, 4)

    def test_stabilization_requires_medicine_check_or_healers_kit(self):
        from rule_engine import estabilizar
        estado = EstadoVital(10, 0, inconsciente=True)
        self.assertEqual(estabilizar(estado)["resultado"], "bloqueado")
        self.assertEqual(estabilizar(estado, teste_medicina=9)["resultado"], "falha")
        self.assertEqual(estabilizar(estado, kit_medico=True)["resultado"], "sucesso")
    def test_long_rest_does_not_erase_temporary_hit_points_by_default(self):
        estado = EstadoVital(20, 10, pv_temporarios=5)
        self.engine.evaluate({"type": "long_rest", "estado": estado, "duration_hours": 8})
        self.assertEqual(estado.pv_atuais, 20)
        self.assertEqual(estado.pv_temporarios, 5)

    def test_damage_to_already_unconscious_target_is_not_instant_death_by_overflow_rule(self):
        estado = EstadoVital(10, 0, inconsciente=True)
        result = self.engine.evaluate({"type": "damage_application", "estado": estado, "damage": 10})
        self.assertNotEqual(result.outcome.get("estado"), "morto")
        self.assertEqual(estado.salvaguardas_falha, 1)
    def test_condition_aliases_and_exhaustion_levels_are_normalized(self):
        estado = __import__("rule_engine", fromlist=["EstadoCondicoes"]).EstadoCondicoes()
        result = self.engine.evaluate({"type": "condition_state", "estado": estado, "operation": "apply", "condition": "Poisoned", "duration": 2})
        self.assertEqual(result.outcome["condicao"], "envenenado")
        result = self.engine.evaluate({"type": "condition_effect", "action": "move", "target_conditions": ["exhaustion"], "exhaustion_niveis": 3})
        self.assertEqual(result.outcome["modificador_d20"], -6)

    def test_tactical_grid_movement_respects_difficult_terrain_and_blockers(self):
        result = self.engine.evaluate({"type": "tactical_movement", "caminho": [(0, 0), (1, 0), (2, 0)], "terreno_dificil": [(1, 0)], "movimento_disponivel": 4})
        self.assertEqual(result.outcome["custo"], 3)
        blocked = self.engine.evaluate({"type": "tactical_movement", "caminho": [(0, 0), (1, 0)], "bloqueados": [(1, 0)]})
        self.assertEqual(blocked.outcome["motivo"], "casula_bloqueada")

    def test_tactical_line_and_flanking(self):
        blocked = self.engine.evaluate({"type": "tactical_line", "origem": (0, 0), "alvo": (3, 0), "bloqueados": [(1, 0)]})
        self.assertEqual(blocked.outcome["resultado"], "bloqueada")
        flank = self.engine.evaluate({"type": "tactical_flanking", "atacante": (0, 1), "alvo": (1, 1), "aliados": [(2, 1)]})
        self.assertTrue(flank.outcome["vantagem"])

    def test_tactical_attack_combines_cover_range_and_flanking(self):
        result = self.engine.evaluate({"type": "tactical_attack", "distancia": 9, "alcance": 9, "ataque_a_distancia": True, "cobertura": "meia", "atacante": (0, 1), "alvo_posicao": (1, 1), "aliados": [(2, 1)]})
        self.assertEqual(result.outcome["estado_jogada"], "vantagem")
        self.assertEqual(result.outcome["bonus_ca_por_cobertura"], 2)
        blocked = self.engine.evaluate({"type": "tactical_attack", "distancia": 9, "alcance": 9, "cobertura": "total"})
        self.assertEqual(blocked.outcome["motivo"], "cobertura_total")

    def test_tactical_terrain_costs_rushing_and_crawling(self):
        result = self.engine.evaluate({"type": "tactical_terrain", "distancia": 3, "terreno_dificil": True, "rastejando": True, "movimento_disponivel": 12})
        self.assertEqual(result.outcome["custo"], 12)

    def test_class_features_cover_core_barbarian_fighter_and_rogue_rules(self):
        result = self.engine.evaluate({"type": "class_feature", "classe": "barbaro", "recurso": "defesa_sem_armadura", "destreza": 14, "constituicao": 16})
        self.assertEqual(result.outcome["ca"], 15)
        result = self.engine.evaluate({"type": "class_feature", "classe": "guerreiro", "recurso": "indomavel", "nivel": 13})
        self.assertEqual(result.outcome["usos"], 2)
        result = self.engine.evaluate({"type": "class_feature", "classe": "ladino", "recurso": "talento_confiavel", "rolagem_d20": 4, "bonus": 5, "proficiente": True})
        self.assertEqual(result.outcome["total"], 15)

    def test_class_features_cover_monk_paladin_and_ranger_rules(self):
        result = self.engine.evaluate({"type": "class_feature", "classe": "monge", "recurso": "golpe_atordoante", "nivel": 5, "sabedoria": 16, "bonus_proficiencia": 3, "salvaguarda_constituicao": 12})
        self.assertEqual(result.outcome["resultado"], "atordoado")
        result = self.engine.evaluate({"type": "class_feature", "classe": "paladino", "recurso": "aura_de_protecao", "carisma": 18})
        self.assertEqual(result.outcome["bonus_salvaguardas"], 4)
        result = self.engine.evaluate({"type": "class_feature", "classe": "guardiao", "recurso": "errante"})
        self.assertTrue(result.outcome["escalada_igual_deslocamento"])

    def test_progression_contains_asi_epic_boon_and_subclass_milestones(self):
        result = self.engine.evaluate({"type": "level_up", "current_level": 18, "class": "guerreiro"})
        self.assertIn("Dádiva Épica", result.outcome["caracteristicas"])
        result = self.engine.evaluate({"type": "level_up", "current_level": 5, "class": "bardo"})
        self.assertIn("Característica de Subclasse", result.outcome["caracteristicas"])

    def test_second_batch_bard_cleric_and_druid_features(self):
        bard = self.engine.evaluate({"type": "class_feature", "classe": "bardo", "recurso": "inspiracao_de_bardo", "nivel": 10, "carisma": 18})
        self.assertEqual(bard.outcome["dado"], "d10")
        self.assertEqual(bard.outcome["usos"], 4)
        cleric = self.engine.evaluate({"type": "class_feature", "classe": "clerigo", "recurso": "fulminar_mortos_vivos", "nivel": 5, "sabedoria": 16, "bonus_proficiencia": 3, "falhou_salvaguarda": True})
        self.assertEqual(cleric.outcome["resultado"], "destruido")
        druid = self.engine.evaluate({"type": "class_feature", "classe": "druida", "recurso": "magias_bestiais", "nivel": 18})
        self.assertTrue(druid.outcome["pode_conjurar_em_forma_selvagem"])

    def test_second_batch_wizard_sorcerer_and_warlock_features(self):
        wizard = self.engine.evaluate({"type": "class_feature", "classe": "mago", "recurso": "maestria_de_magias", "nivel": 18})
        self.assertEqual(wizard.outcome["magias_sem_espaco"], 2)
        sorcerer = self.engine.evaluate({"type": "class_feature", "classe": "feiticeiro", "recurso": "fonte_de_magia", "nivel": 12})
        self.assertEqual(sorcerer.outcome["pontos"], 12)
        warlock = self.engine.evaluate({"type": "class_feature", "classe": "bruxo", "recurso": "arcana_mistica", "nivel": 17})
        self.assertEqual(warlock.outcome["circulo"], 9)

    def test_second_batch_artificer_features(self):
        genius = self.engine.evaluate({"type": "class_feature", "classe": "artifice", "recurso": "flash_of_genius", "nivel": 7, "inteligencia": 18})
        self.assertEqual(genius.outcome["bonus"], 4)
        stored = self.engine.evaluate({"type": "class_feature", "classe": "artifice", "recurso": "spell_storing_item", "nivel": 11, "inteligencia": 18})
        self.assertEqual(stored.outcome["conjuracoes"], 8)
        soul = self.engine.evaluate({"type": "class_feature", "classe": "artifice", "recurso": "soul_of_artifice", "nivel": 20})
        self.assertTrue(soul.outcome["reacao_evitar_morte"])


if __name__ == "__main__":
    unittest.main()
