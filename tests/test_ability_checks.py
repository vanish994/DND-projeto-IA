import unittest

from rule_engine import (
    build_default_engine,
    resolver_iniciativa,
    resolver_inspiracao_heroica,
    resolver_salvaguarda,
    resolver_teste_grupo,
    resolver_teste_habilidade,
    resolver_teste_passivo,
)


class AbilityCheckTests(unittest.TestCase):
    def test_skill_check_uses_skill_default_ability_and_proficiency_once(self):
        result = resolver_teste_habilidade(
            {"pericia": "furtividade", "valor_atributo": 16, "nivel": 5, "proficiente": True, "roll": 10, "cd": 15}
        )
        self.assertEqual(result["atributo"], "destreza")
        self.assertEqual(result["bonus_proficiencia_aplicado"], 3)
        self.assertEqual(result["total"], 16)
        self.assertEqual(result["resultado"], "sucesso")

    def test_expertise_doubles_proficiency_but_not_attribute(self):
        result = resolver_teste_habilidade(
            {"pericia": "arcanismo", "valor_atributo": 14, "nivel": 9, "expertise": True, "roll": 5, "cd": 15}
        )
        self.assertEqual(result["bonus_proficiencia_aplicado"], 8)
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["resultado"], "sucesso")

    def test_advantage_and_disadvantage_cancel(self):
        result = resolver_teste_habilidade(
            {
                "pericia": "percepcao",
                "modificador_atributo": 2,
                "roll": 4,
                "vantagem": True,
                "desvantagem": True,
                "cd": 15,
            }
        )
        self.assertEqual(result["dado"], 4)
        self.assertFalse(result["vantagem"])
        self.assertFalse(result["desvantagem"])

    def test_tool_and_skill_proficiency_grant_advantage_not_double_proficiency(self):
        result = resolver_teste_habilidade(
            {
                "pericia": "investigacao",
                "modificador_atributo": 1,
                "bonus_proficiencia": 3,
                "proficiente": True,
                "proficiente_ferramenta": True,
                "proficiente_pericia": True,
                "dados": [8, 12],
                "cd": 15,
            }
        )
        self.assertTrue(result["vantagem_por_pericia_e_ferramenta"])
        self.assertEqual(result["bonus_proficiencia_aplicado"], 3)
        self.assertEqual(result["dado"], 12)

    def test_passive_check_adds_five_for_advantage_and_minus_five_for_disadvantage(self):
        advantage = resolver_teste_passivo(
            {
                "pericia": "percepcao",
                "modificador_atributo": 3,
                "proficiente": True,
                "bonus_proficiencia": 2,
                "vantagem": True,
            }
        )
        disadvantage = resolver_teste_passivo(
            {
                "pericia": "percepcao",
                "modificador_atributo": 3,
                "proficiente": True,
                "bonus_proficiencia": 2,
                "desvantagem": True,
            }
        )
        self.assertEqual(advantage["valor_passivo"], 20)
        self.assertEqual(disadvantage["valor_passivo"], 10)

    def test_group_check_requires_at_least_half_successes(self):
        result = resolver_teste_grupo({"participantes": [True, False, True, False, False]})
        self.assertEqual(result["sucessos_necessarios"], 3)
        self.assertEqual(result["resultado"], "falha")

    def test_heroic_inspiration_requires_resource_and_uses_new_roll(self):
        blocked = resolver_inspiracao_heroica({"dado_original": 4, "rerrolagem": 17})
        self.assertEqual(blocked["resultado"], "bloqueado")
        result = resolver_inspiracao_heroica({"tem_inspiracao_heroica": True, "dado_original": 4, "rerrolagem": 17})
        self.assertEqual(result["dado_usado"], 17)
        self.assertTrue(result["inspiracao_heroica_consumida"])

    def test_missing_character_modifiers_are_blocked_instead_of_assumed_zero(self):
        result = resolver_teste_habilidade({"pericia": "atletismo", "roll": 12, "cd": 15})
        self.assertEqual(result["resultado"], "bloqueado")
        self.assertEqual(result["motivo"], "modificador_de_atributo_ausente")

    def test_heroic_inspiration_can_reroll_any_die_not_only_a_d20(self):
        result = resolver_inspiracao_heroica(
            {"tem_inspiracao_heroica": True, "dado_original": 2, "rerrolagem": 5, "lados_dado": 6}
        )
        self.assertEqual(result["dado_usado"], 5)
        self.assertTrue(result["inspiracao_heroica_consumida"])
        delayed = resolver_inspiracao_heroica(
            {
                "tem_inspiracao_heroica": True,
                "dado_original": 2,
                "rerrolagem": 5,
                "lados_dado": 6,
                "imediatamente_apos_rolar": False,
            }
        )
        self.assertEqual(delayed["resultado"], "bloqueado")

    def test_saving_throw_uses_attribute_proficiency_and_d20_rules(self):
        result = resolver_salvaguarda(
            {
                "atributo": "destreza",
                "valor_atributo": 14,
                "nivel": 5,
                "proficiencias_salvaguarda": ["destreza"],
                "roll": 10,
                "cd": 14,
            }
        )
        self.assertEqual(result["bonus_proficiencia_aplicado"], 3)
        self.assertEqual(result["total"], 15)
        self.assertEqual(result["resultado"], "sucesso")

    def test_initiative_uses_dexterity_modifier_and_explicit_bonus(self):
        from rule_engine import resolver_iniciativa

        result = resolver_iniciativa({"modificador_destreza": 2, "roll": 13, "bonus_iniciativa": 1})
        self.assertEqual(result["total"], 16)
        self.assertEqual(result["atributo"], "destreza")

    def test_surprise_imposes_disadvantage_on_initiative_not_action_loss(self):
        result = resolver_iniciativa({"modificador_destreza": 2, "dados": [14, 6], "surpreendido": True})
        self.assertEqual(result["dado"], 6)
        self.assertEqual(result["total"], 8)

    def test_initiative_score_uses_ten_plus_dexterity_and_five_for_advantage(self):
        normal = resolver_iniciativa({"modificador_destreza": 2, "usar_escore": True})
        advantage = resolver_iniciativa({"modificador_destreza": 2, "usar_escore": True, "invisivel": True})
        disadvantage = resolver_iniciativa({"modificador_destreza": 2, "usar_escore": True, "surpreendido": True})
        both = resolver_iniciativa(
            {"modificador_destreza": 2, "usar_escore": True, "invisivel": True, "surpreendido": True}
        )
        self.assertEqual(normal["total"], 12)
        self.assertEqual(advantage["total"], 17)
        self.assertEqual(disadvantage["total"], 7)
        self.assertEqual(both["total"], 12)

    def test_engine_registers_saving_throw_and_initiative(self):
        engine = build_default_engine()
        save = engine.evaluate(
            {"type": "saving_throw_check", "atributo": "forca", "modificador_atributo": 2, "roll": 12, "cd": 14}
        )
        self.assertEqual(save.outcome["resultado"], "sucesso")
        initiative = engine.evaluate({"type": "initiative_check", "modificador_destreza": 3, "roll": 10})
        self.assertEqual(initiative.outcome["total"], 13)

    def test_engine_registers_new_rule_types(self):
        engine = build_default_engine()
        result = engine.evaluate(
            {"type": "skill_check", "pericia": "atletismo", "modificador_atributo": 3, "roll": 12, "cd": 15}
        )
        self.assertEqual(result.outcome["resultado"], "sucesso")
        passive = engine.evaluate({"type": "passive_check", "pericia": "percepcao", "modificador_atributo": 2})
        self.assertEqual(passive.outcome["valor_passivo"], 12)
        self.assertEqual(passive.outcome["resultado"], "calculado")
        group = engine.evaluate({"type": "group_check", "participantes": [True, True, False]})
        self.assertEqual(group.outcome["resultado"], "sucesso")


if __name__ == "__main__":
    unittest.main()
