from __future__ import annotations

from typing import Any, Mapping

from .ability_checks import (
    resolver_iniciativa,
    resolver_inspiracao_heroica,
    resolver_salvaguarda,
    resolver_teste_grupo,
    resolver_teste_habilidade,
    resolver_teste_passivo,
)
from .advanced_casters import resolver_bruxo, resolver_feiticeiro, resolver_guardiao, resolver_paladino
from .bestiary import resolver_bestiario
from .catalog import buscar_catalogo, listar_catalogo
from .character import (
    criar_personagem,
    gerar_atributos_compra_pontos,
    gerar_atributos_matriz_padrao,
    resolver_multiclasse,
    resolver_progressao,
)
from .class_features import resolver_caracteristica
from .combat_geometry import (
    resolver_alcance,
    resolver_ataque_geometria,
    resolver_cobertura,
    resolver_linha_de_visao,
    resolver_queda,
)
from .combat_movement import (
    resolver_ataque_subaquatico,
    resolver_montaria,
    resolver_movimento_especial,
    resolver_objeto,
    resolver_sentidos,
)
from .combat_special import (
    resolver_agarrar,
    resolver_ataque_oportunidade,
    resolver_empurrar,
    resolver_escape_agarramento,
)
from .conditions import resolver_efeitos_condicao, resolver_estado_condicao
from .dice import (
    rolar_ataque_auditavel,
    rolar_d20_auditavel,
    rolar_dano_auditavel,
    rolar_iniciativa_auditavel,
    rolar_salvaguarda_auditavel,
)
from .economy import (
    comprar_item,
    consultar_item,
    resolver_inventario,
    resolver_sintonizacao,
    usar_item_magico,
    vender_item,
)
from .engine import Rule, RuleEngine
from .exploration_actions import (
    resolver_acao_ajudar,
    resolver_acao_esconder,
    resolver_acao_esquivar,
    resolver_acao_estudar,
    resolver_acao_influenciar,
    resolver_acao_procurar,
    resolver_fim_esconderijo,
)
from .feats import resolver_talento, validar_talento
from .magic_equipment import (
    calcular_ca,
    resolver_alvo_magia,
    resolver_area_magia,
    resolver_arma,
    resolver_carga,
    resolver_conjuracao,
    resolver_duas_armas,
    resolver_salvaguarda_concentracao,
)
from .martial import (
    resolver_ataque_extra,
    resolver_ataque_furtivo,
    resolver_defletir_ataques,
    resolver_esquiva_sobrenatural,
    resolver_evasao,
    resolver_foco_monge,
    resolver_furia,
    resolver_maestria_arma,
    resolver_recuperar_folego,
)
from .martial_subclasses import resolver_subclasse_marcial
from .spellcasters import (
    resolver_canalizar_divindade,
    resolver_forma_selvagem,
    resolver_inspiracao_bardo,
    resolver_livro_de_magias,
    resolver_progressao_conjuracao,
)
from .spells import listar_magias, obter_magia, resolver_magia
from .survival import (
    adicionar_exaustao,
    aplicar_dano,
    curar,
    estabilizar,
    resolver_descanso,
    salvaguarda_contra_morte,
)
from .warlock_invocations import resolver_invocacao, validar_invocacao


def _check_total(facts: Mapping[str, Any]) -> int:
    return int(facts["roll"]) + int(facts.get("modifier", 0))


def _damage_total(facts: Mapping[str, Any], critical: bool = False) -> int:
    dice = [int(value) for value in facts.get("damage_dice", [])]
    if critical:
        dice = dice + dice
    return sum(dice) + int(facts.get("damage_modifier", 0))


def build_default_engine() -> RuleEngine:
    """Cria regras iniciais de resolução de testes de D&D.

    As regras ficam isoladas para que possam ser substituídas por uma versão
    específica de edição, cenário ou mesa sem alterar o motor.
    """

    engine = RuleEngine()
    engine.register(
        Rule(
            rule_id="ability-check.engine-roll",
            description="O motor gera um d20 auditável; a CD pode ser definida pelo MJ.",
            priority=80,
            when=lambda f: f["type"] == "ability_check" and "roll" not in f,
            resolve=rolar_d20_auditavel,
            source="D&D 2024 — teste de d20; rolagem auditável do motor",
        )
    )
    engine.register(
        Rule(
            rule_id="ability-check.natural-20",
            description="Um 20 natural resolve o teste como sucesso automático.",
            priority=100,
            when=lambda f: f["type"] == "ability_check" and int(f["roll"]) == 20,
            resolve=lambda f: {"type": f["type"], "result": "success", "reason": "natural_20"},
            source="D&D 2024 — teste de d20",
        )
    )
    engine.register(
        Rule(
            rule_id="ability-check.natural-1",
            description="Um 1 natural resolve o teste como falha automática.",
            priority=100,
            when=lambda f: f["type"] == "ability_check" and int(f["roll"]) == 1,
            resolve=lambda f: {"type": f["type"], "result": "failure", "reason": "natural_1"},
            source="D&D 2024 — teste de d20",
        )
    )
    engine.register(
        Rule(
            rule_id="ability-check.meets-dc",
            description="O total do teste iguala ou supera a Classe de Dificuldade.",
            priority=50,
            when=lambda f: f["type"] == "ability_check" and _check_total(f) >= int(f["dc"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "success",
                "reason": "total_meets_dc",
                "total": _check_total(f),
                "dc": int(f["dc"]),
            },
            source="D&D 2024 — testes de d20",
        )
    )
    engine.register(
        Rule(
            rule_id="ability-check.below-dc",
            description="O total do teste fica abaixo da Classe de Dificuldade.",
            priority=40,
            when=lambda f: f["type"] == "ability_check" and _check_total(f) < int(f["dc"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "failure",
                "reason": "total_below_dc",
                "total": _check_total(f),
                "dc": int(f["dc"]),
            },
            source="D&D 2024 — testes de d20",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.engine-roll",
            description="O motor gera um d20 auditável e resolve acerto, erro e crítico.",
            priority=110,
            when=lambda f: f["type"] == "attack" and "roll" not in f,
            resolve=rolar_ataque_auditavel,
            source="D&D 2024 — jogadas de ataque",
        )
    )
    engine.register(
        Rule(
            rule_id="initiative.engine-roll",
            description="O motor gera iniciativa; surpresa impõe desvantagem, sem teste separado.",
            priority=110,
            when=lambda f: f["type"] == "initiative" and "roll" not in f,
            resolve=rolar_iniciativa_auditavel,
            source="D&D 2024 — iniciativa e surpresa",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.natural-20",
            description="Um 20 natural supera a Classe de Armadura e causa um acerto crítico.",
            priority=100,
            when=lambda f: f["type"] == "attack" and int(f["roll"]) == 20,
            resolve=lambda f: {
                "type": f["type"],
                "result": "hit",
                "critical": True,
                "reason": "natural_20",
                "total": _check_total(f),
            },
            source="D&D 2024 — jogadas de ataque",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.natural-1",
            description="Um 1 natural falha na jogada de ataque.",
            priority=100,
            when=lambda f: f["type"] == "attack" and int(f["roll"]) == 1,
            resolve=lambda f: {
                "type": f["type"],
                "result": "miss",
                "critical": False,
                "reason": "natural_1",
                "total": _check_total(f),
            },
            source="D&D 2024 — jogadas de ataque",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.meets-ac",
            description="O total da jogada de ataque iguala ou supera a Classe de Armadura.",
            priority=50,
            when=lambda f: f["type"] == "attack" and _check_total(f) >= int(f["target_ac"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "hit",
                "critical": False,
                "reason": "total_meets_ac",
                "total": _check_total(f),
                "target_ac": int(f["target_ac"]),
            },
            source="D&D 2024 — jogadas de ataque",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.below-ac",
            description="O total da jogada de ataque fica abaixo da Classe de Armadura.",
            priority=40,
            when=lambda f: f["type"] == "attack" and _check_total(f) < int(f["target_ac"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "miss",
                "critical": False,
                "reason": "total_below_ac",
                "total": _check_total(f),
                "target_ac": int(f["target_ac"]),
            },
            source="D&D 2024 — jogadas de ataque",
        )
    )
    engine.register(
        Rule(
            rule_id="damage.engine-roll",
            description=(
                "O motor rola os dados de dano a partir da expressão oficial "
                "(arma, magia ou truque) e mantém o resultado auditável pela seed."
            ),
            priority=110,
            # Só rola quando existe uma expressão oficial. Ataque desarmado e dano
            # fixo continuam sem dados e caem nas regras de dano existentes.
            when=lambda f: f["type"] == "damage" and not f.get("damage_dice") and bool(f.get("damage_expression")),
            resolve=rolar_dano_auditavel,
            source="D&D 2024 — dano",
        )
    )
    engine.register(
        Rule(
            rule_id="damage.critical",
            description="No acerto crítico, os dados de dano são rolados duas vezes; o modificador é somado uma vez.",
            priority=100,
            when=lambda f: f["type"] == "damage" and bool(f.get("critical", False)),
            resolve=lambda f: {
                "type": f["type"],
                "result": "damage",
                "critical": True,
                "total": _damage_total(f, critical=True),
                "dice_count": len(f.get("damage_dice", [])) * 2,
                "modifier": int(f.get("damage_modifier", 0)),
            },
            source="D&D 2024 — acertos críticos",
        )
    )
    engine.register(
        Rule(
            rule_id="damage.normal",
            description="O dano normal soma os resultados dos dados ao modificador de dano.",
            priority=50,
            when=lambda f: f["type"] == "damage" and not bool(f.get("critical", False)),
            resolve=lambda f: {
                "type": f["type"],
                "result": "damage",
                "critical": False,
                "total": _damage_total(f),
                "dice_count": len(f.get("damage_dice", [])),
                "modifier": int(f.get("damage_modifier", 0)),
            },
            source="D&D 2024 — dano",
        )
    )
    engine.register(
        Rule(
            rule_id="saving-throw.engine-roll",
            description="O motor gera o d20 auditável da salvaguarda; a CD pode ser definida pelo MJ.",
            priority=80,
            when=lambda f: f["type"] == "saving_throw" and "roll" not in f,
            resolve=rolar_salvaguarda_auditavel,
            source="D&D 2024 — salvaguardas; rolagem auditável do motor",
        )
    )
    engine.register(
        Rule(
            rule_id="saving-throw.natural-20",
            description="Um 20 natural obtém sucesso automático na salvaguarda.",
            priority=100,
            when=lambda f: f["type"] == "saving_throw" and int(f["roll"]) == 20,
            resolve=lambda f: {
                "type": f["type"],
                "result": "success",
                "reason": "natural_20",
                "total": _check_total(f),
            },
            source="D&D 2024 — salvaguardas",
        )
    )
    engine.register(
        Rule(
            rule_id="saving-throw.natural-1",
            description="Um 1 natural falha automaticamente na salvaguarda.",
            priority=100,
            when=lambda f: f["type"] == "saving_throw" and int(f["roll"]) == 1,
            resolve=lambda f: {
                "type": f["type"],
                "result": "failure",
                "reason": "natural_1",
                "total": _check_total(f),
            },
            source="D&D 2024 — salvaguardas",
        )
    )
    engine.register(
        Rule(
            rule_id="saving-throw.meets-dc",
            description="O total da salvaguarda iguala ou supera a Classe de Dificuldade.",
            priority=50,
            when=lambda f: f["type"] == "saving_throw" and _check_total(f) >= int(f["dc"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "success",
                "reason": "total_meets_dc",
                "total": _check_total(f),
                "dc": int(f["dc"]),
            },
            source="D&D 2024 — salvaguardas",
        )
    )
    engine.register(
        Rule(
            rule_id="saving-throw.below-dc",
            description="O total da salvaguarda fica abaixo da Classe de Dificuldade.",
            priority=40,
            when=lambda f: f["type"] == "saving_throw" and _check_total(f) < int(f["dc"]),
            resolve=lambda f: {
                "type": f["type"],
                "result": "failure",
                "reason": "total_below_dc",
                "total": _check_total(f),
                "dc": int(f["dc"]),
            },
            source="D&D 2024 — salvaguardas",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.cast.no-slot",
            description="A magia não pode ser conjurada sem um espaço de magia disponível.",
            priority=100,
            when=lambda f: f["type"] == "spell_cast" and not bool(f.get("has_slot", False)),
            resolve=lambda f: {
                "type": f["type"],
                "result": "blocked",
                "reason": "no_slot",
                "spell_level": int(f["spell_level"]),
            },
            source="D&D 2024 — conjuração",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.cast.slot-too-low",
            description="O espaço de magia precisa ser do nível da magia ou superior.",
            priority=90,
            when=lambda f: (
                f["type"] == "spell_cast"
                and bool(f.get("has_slot", False))
                and int(f["slot_level"]) < int(f["spell_level"])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "blocked",
                "reason": "slot_level_too_low",
                "spell_level": int(f["spell_level"]),
                "slot_level": int(f["slot_level"]),
            },
            source="D&D 2024 — conjuração",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.cast.concentration-replaced",
            description="Conjurar outra magia de concentração encerra a concentração anterior.",
            priority=80,
            when=lambda f: (
                f["type"] == "spell_cast"
                and bool(f.get("has_slot", False))
                and int(f["slot_level"]) >= int(f["spell_level"])
                and bool(f.get("concentration_required", False))
                and bool(f.get("concentrating", False))
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "cast",
                "reason": "concentration_replaced",
                "ends_previous_concentration": True,
            },
            source="D&D 2024 — concentração",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.cast.valid",
            description="A magia pode ser conjurada com o espaço disponível.",
            priority=40,
            when=lambda f: (
                f["type"] == "spell_cast"
                and bool(f.get("has_slot", False))
                and int(f["slot_level"]) >= int(f["spell_level"])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "cast",
                "reason": "valid_spell_slot",
                "ends_previous_concentration": False,
            },
            source="D&D 2024 — conjuração",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.apply.immune",
            description="Uma criatura imune não recebe a condição.",
            priority=100,
            when=lambda f: (
                f["type"] == "condition"
                and f.get("operation") == "apply"
                and f.get("condition") in f.get("immunities", [])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "not_applied",
                "reason": "immune",
                "condition": f["condition"],
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.apply.already-active",
            description="Uma condição já ativa não é aplicada novamente por esta resolução.",
            priority=90,
            when=lambda f: (
                f["type"] == "condition"
                and f.get("operation") == "apply"
                and f.get("condition") in f.get("active_conditions", [])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "already_active",
                "condition": f["condition"],
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.apply",
            description="A condição é aplicada ao alvo.",
            priority=50,
            when=lambda f: f["type"] == "condition" and f.get("operation") == "apply",
            resolve=lambda f: {
                "type": f["type"],
                "result": "applied",
                "condition": f["condition"],
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.remove.active",
            description="A condição ativa é removida do alvo.",
            priority=60,
            when=lambda f: (
                f["type"] == "condition"
                and f.get("operation") == "remove"
                and f.get("condition") in f.get("active_conditions", [])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "removed",
                "condition": f["condition"],
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.remove.absent",
            description="Não há condição ativa para remover.",
            priority=40,
            when=lambda f: (
                f["type"] == "condition"
                and f.get("operation") == "remove"
                and f.get("condition") not in f.get("active_conditions", [])
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "not_active",
                "condition": f["condition"],
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="concentration.damage-save",
            description="Resolve a salvaguarda de Constituição para manter concentração após dano; incapacidade encerra concentração.",
            priority=110,
            when=lambda f: f["type"] == "concentration_check",
            resolve=resolver_salvaguarda_concentracao,
            source="D&D 2024 — concentração",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.state",
            description="Aplica, remove, consulta e atualiza a duração de condições persistentes.",
            priority=110,
            when=lambda f: f["type"] == "condition_state",
            resolve=resolver_estado_condicao,
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.effects.complete",
            description="Resolve os efeitos completos das condições sobre ações, movimento e sentidos.",
            priority=110,
            when=lambda f: f["type"] == "condition_effect",
            resolve=resolver_efeitos_condicao,
            source="D&D 2024 — efeitos de condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.attack.cancelled",
            description="Vantagem e desvantagem na mesma jogada se cancelam.",
            priority=100,
            when=lambda f: (
                f["type"] == "condition_effect"
                and f.get("action") == "attack"
                and bool(set(f.get("attacker_conditions", [])) & {"blinded", "poisoned", "restrained"})
                and bool(set(f.get("target_conditions", [])) & {"blinded", "restrained"})
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "normal",
                "reason": "advantage_disadvantage_cancel",
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.attack.advantage",
            description="Atacar uma criatura cega ou impedida concede vantagem.",
            priority=60,
            when=lambda f: (
                f["type"] == "condition_effect"
                and f.get("action") == "attack"
                and bool(set(f.get("target_conditions", [])) & {"blinded", "restrained"})
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "advantage",
                "reason": "target_condition",
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="condition.attack.disadvantage",
            description="Atacar enquanto cego, envenenado ou impedido impõe desvantagem.",
            priority=50,
            when=lambda f: (
                f["type"] == "condition_effect"
                and f.get("action") == "attack"
                and bool(set(f.get("attacker_conditions", [])) & {"blinded", "poisoned", "restrained"})
            ),
            resolve=lambda f: {
                "type": f["type"],
                "result": "disadvantage",
                "reason": "attacker_condition",
            },
            source="D&D 2024 — condições",
        )
    )
    engine.register(
        Rule(
            rule_id="attack.opportunity",
            description="Uma criatura que sai do alcance pode provocar um ataque de oportunidade.",
            priority=50,
            when=lambda f: f["type"] == "opportunity_attack",
            resolve=resolver_ataque_oportunidade,
            source="D&D 2024 — ataques de oportunidade",
        )
    )
    engine.register(
        Rule(
            rule_id="unarmed.shove",
            description="Empurrar exige uma salvaguarda de Força ou Destreza e permite empurrar ou deixar Caído.",
            priority=50,
            when=lambda f: f["type"] == "shove",
            resolve=resolver_empurrar,
            source="D&D 2024 — Ataque Desarmado",
        )
    )
    engine.register(
        Rule(
            rule_id="unarmed.grapple",
            description="Agarrar exige uma salvaguarda de Força ou Destreza e aplica a condição Agarrado se falhar.",
            priority=50,
            when=lambda f: f["type"] == "grapple",
            resolve=resolver_agarrar,
            source="D&D 2024 — Ataque Desarmado",
        )
    )
    engine.register(
        Rule(
            rule_id="grapple.escape",
            description="A criatura agarrada pode escapar com Atletismo ou Acrobacia contra a CD do agarramento.",
            priority=50,
            when=lambda f: f["type"] == "grapple_escape",
            resolve=resolver_escape_agarramento,
            source="D&D 2024 — condição Agarrado",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.damage",
            description="Aplica dano aos PV e absorve primeiro os PV Temporários.",
            priority=50,
            when=lambda f: f["type"] == "damage_application",
            resolve=lambda f: aplicar_dano(
                f["estado"],
                f["damage"],
                critico=bool(f.get("critical", False)),
                dano_ajustado=bool(f.get("adjusted", False)),
                tipo_dano=f.get("damage_type"),
                origem=f.get("source"),
                resistencias=f.get("resistances", ()),
                vulnerabilidades=f.get("vulnerabilities", ()),
                imunidades=f.get("immunities", ()),
            ),
            source="D&D 2024 — Pontos de Vida",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.healing",
            description="Cura PV sem ultrapassar os PV máximos.",
            priority=50,
            when=lambda f: f["type"] == "healing",
            resolve=lambda f: curar(f["estado"], f["amount"]),
            source="D&D 2024 — Cura",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.death-save",
            description="Resolve uma Salvaguarda contra a Morte.",
            priority=50,
            when=lambda f: f["type"] == "death_save",
            resolve=lambda f: salvaguarda_contra_morte(f["estado"], f["roll"]),
            source="D&D 2024 — Salvaguardas contra a Morte",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.stabilize",
            description="Estabiliza uma criatura com 0 PV.",
            priority=50,
            when=lambda f: f["type"] == "stabilize",
            resolve=lambda f: estabilizar(
                f["estado"], teste_medicina=f.get("medicine_test"), kit_medico=bool(f.get("healer_kit", False))
            ),
            source="D&D 2024 — Estabilização",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.exhaustion",
            description="Adiciona níveis de Exaustão e aplica seu modificador.",
            priority=50,
            when=lambda f: f["type"] == "exhaustion",
            resolve=lambda f: adicionar_exaustao(f["estado"], f.get("levels", 1)),
            source="D&D 2024 — Exaustão",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.short-rest",
            description="Gasta Dados de Vida e recupera PV durante um Descanso Curto.",
            priority=50,
            when=lambda f: f["type"] == "short_rest",
            resolve=lambda f: resolver_descanso({**f, "rest_type": "curto"}),
            source="D&D 2024 — Descanso Curto",
        )
    )
    engine.register(
        Rule(
            rule_id="survival.long-rest",
            description="Recupera PV e reduz um nível de Exaustão em um Descanso Longo.",
            priority=50,
            when=lambda f: f["type"] == "long_rest",
            resolve=lambda f: resolver_descanso({**f, "rest_type": "longo"}),
            source="D&D 2024 — Descanso Longo",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.attack-geometry",
            description="Valida distância, alcance, linha de visão e cobertura antes do ataque.",
            priority=50,
            when=lambda f: f["type"] == "attack_geometry",
            resolve=resolver_ataque_geometria,
            source="D&D 2024 — Combate: alcance e cobertura",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.range",
            description="Verifica alcance normal e alcance máximo de um ataque.",
            priority=50,
            when=lambda f: f["type"] == "range",
            resolve=lambda f: resolver_alcance(
                f["distance"],
                alcance=f["range"],
                alcance_maximo=f.get("maximum_range"),
                ataque_a_distancia=bool(f.get("ranged_attack", False)),
                alcance_estendido=bool(f.get("extended_range", False)),
            ),
            source="D&D 2024 — alcance",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.cover",
            description="Aplica o bônus de CA da cobertura ou bloqueia Cobertura Total.",
            priority=50,
            when=lambda f: f["type"] == "cover",
            resolve=lambda f: resolver_cobertura(f["cover"], linha_de_visao=bool(f.get("line_of_sight", True))),
            source="D&D 2024 — cobertura",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.line-of-sight",
            description="Verifica se há linha de visão até o alvo.",
            priority=50,
            when=lambda f: f["type"] == "line_of_sight",
            resolve=lambda f: resolver_linha_de_visao(
                bloqueada=bool(f.get("blocked", False)), cobertura=f.get("cover", "nenhuma")
            ),
            source="D&D 2024 — linha de visão",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.fall",
            description="Aplica dano de queda e a condição Caído.",
            priority=50,
            when=lambda f: f["type"] == "fall",
            resolve=lambda f: resolver_queda(f["distance"], rolagens=f.get("rolls")),
            source="D&D 2024 — queda",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.senses",
            description="Resolve Visão no Escuro, Visão às Cegas, Sentido de Tremor e Visão Verdadeira.",
            priority=50,
            when=lambda f: f["type"] == "senses",
            resolve=resolver_sentidos,
            source="D&D 2024 — sentidos especiais",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.special-movement",
            description="Resolve rastejar, escalar, nadar e levantar-se de Caído.",
            priority=50,
            when=lambda f: f["type"] == "special_movement",
            resolve=resolver_movimento_especial,
            source="D&D 2024 — movimento especial",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.mounted",
            description="Resolve montar, desmontar, controle da montaria e queda do cavaleiro.",
            priority=50,
            when=lambda f: f["type"] == "mounted_combat",
            resolve=resolver_montaria,
            source="D&D 2024 — combate montado",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.underwater",
            description="Aplica limitações de armas e alcance no combate subaquático.",
            priority=50,
            when=lambda f: f["type"] == "underwater_attack",
            resolve=resolver_ataque_subaquatico,
            source="D&D 2024 — combate subaquático",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.object",
            description="Aplica dano aos Pontos de Vida de um objeto.",
            priority=50,
            when=lambda f: f["type"] == "object_damage",
            resolve=resolver_objeto,
            source="D&D 2024 — objetos",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.armor-class",
            description="Calcula CA com armadura, Destreza, escudo e requisitos de Força.",
            priority=50,
            when=lambda f: f["type"] == "armor_class",
            resolve=calcular_ca,
            source="D&D 2024 — armaduras e escudos",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.weapon",
            description="Valida propriedades, proficiência e maestria de uma arma.",
            priority=50,
            when=lambda f: f["type"] == "weapon",
            resolve=resolver_arma,
            source="D&D 2024 — armas",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.two-weapons",
            description="Valida o ataque adicional com duas armas Leves.",
            priority=50,
            when=lambda f: f["type"] == "two_weapon_attack",
            resolve=resolver_duas_armas,
            source="D&D 2024 — armas Leves",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.carrying-capacity",
            description="Calcula a Capacidade de Carga e sobrecarga.",
            priority=50,
            when=lambda f: f["type"] == "carrying_capacity",
            resolve=resolver_carga,
            source="D&D 2024 — equipamentos",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.casting-complete",
            description="Valida preparação, espaço, componentes, ritual e concentração.",
            priority=110,
            when=lambda f: f["type"] == "spell_cast_complete",
            resolve=resolver_conjuracao,
            source="D&D 2024 — conjuração",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.targets",
            description="Valida alcance, linha de efeito e quantidade de alvos da magia.",
            priority=50,
            when=lambda f: f["type"] == "spell_targets",
            resolve=resolver_alvo_magia,
            source="D&D 2024 — alvos de magia",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.area",
            description="Valida as formas e medidas das áreas de efeito.",
            priority=50,
            when=lambda f: f["type"] == "spell_area",
            resolve=resolver_area_magia,
            source="D&D 2024 — áreas de efeito",
        )
    )
    engine.register(
        Rule(
            rule_id="catalog.lookup",
            description="Consulta uma entrada estruturada de arma, armadura, equipamento ou magia.",
            priority=50,
            when=lambda f: f["type"] == "catalog_lookup",
            resolve=lambda f: {
                "resultado": (
                    "encontrado" if buscar_catalogo(f["category"], f["name"]) is not None else "não_encontrado"
                ),
                "category": f["category"],
                "name": f["name"],
                "data": buscar_catalogo(f["category"], f["name"]),
            },
            source="D&D 2024 — catálogos",
        )
    )
    engine.register(
        Rule(
            rule_id="catalog.list",
            description="Lista os nomes disponíveis em uma categoria de catálogo.",
            priority=50,
            when=lambda f: f["type"] == "catalog_list",
            resolve=lambda f: {
                "resultado": "listado",
                "category": f["category"],
                "names": listar_catalogo(f["category"]),
            },
            source="D&D 2024 — catálogos",
        )
    )
    engine.register(
        Rule(
            rule_id="character.creation",
            description="Valida espécie, classe, nível, atributos, subclasse e talentos.",
            priority=50,
            when=lambda f: f["type"] == "character_creation",
            resolve=lambda f: {
                "resultado": "criado",
                "personagem": criar_personagem(f),
            },
            source="D&D 2024 — criação de personagens",
        )
    )
    engine.register(
        Rule(
            rule_id="character.ability-scores",
            description="Gera atributos pela matriz padrão ou compra por pontos.",
            priority=50,
            when=lambda f: f["type"] == "ability_generation",
            resolve=lambda f: {
                "resultado": "gerado",
                "atributos": (
                    gerar_atributos_matriz_padrao()
                    if f.get("method") == "matriz_padrao"
                    else gerar_atributos_compra_pontos(f["scores"])
                ),
            },
            source="D&D 2024 — criação de personagens",
        )
    )
    engine.register(
        Rule(
            rule_id="character.level-up",
            description="Resolve progressão de nível, aumento de atributo, talento e subclasse.",
            priority=50,
            when=lambda f: f["type"] == "level_up",
            resolve=resolver_progressao,
            source="D&D 2024 — progressão",
        )
    )
    engine.register(
        Rule(
            rule_id="character.multiclass",
            description="Valida os pré-requisitos de atributo para multiclasse.",
            priority=50,
            when=lambda f: f["type"] == "multiclass",
            resolve=resolver_multiclasse,
            source="D&D 2024 — multiclasse",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.extra-attack",
            description="Calcula a quantidade de ataques da ação Atacar por classe e nível.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "ataque_extra",
            resolve=resolver_ataque_extra,
            source="D&D 2024 — características marciais",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.weapon-mastery",
            description="Valida a quantidade de escolhas de Maestria em Arma.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "maestria_em_arma",
            resolve=resolver_maestria_arma,
            source="D&D 2024 — Maestria em Arma",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.rage",
            description="Resolve ativação, dano, resistências e encerramento da Fúria.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "furia",
            resolve=resolver_furia,
            source="D&D 2024 — Bárbaro",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.second-wind",
            description="Resolve Recuperar Fôlego do Guerreiro.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "recuperar_folego",
            resolve=resolver_recuperar_folego,
            source="D&D 2024 — Guerreiro",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.sneak-attack",
            description="Valida e calcula os dados de Ataque Furtivo do Ladino.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "ataque_furtivo",
            resolve=resolver_ataque_furtivo,
            source="D&D 2024 — Ladino",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.monk-focus",
            description="Resolve gastos e efeitos básicos do Foco do Monge.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "foco_monge",
            resolve=resolver_foco_monge,
            source="D&D 2024 — Monge",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.deflect-attacks",
            description="Resolve Defletir Ataques e seu redirecionamento.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "defletir_ataques",
            resolve=resolver_defletir_ataques,
            source="D&D 2024 — Monge",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.uncanny-dodge",
            description="Reduz pela metade o dano de um ataque que acertou o Ladino.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "esquiva_sobrenatural",
            resolve=resolver_esquiva_sobrenatural,
            source="D&D 2024 — Ladino",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.evasion",
            description="Resolve Evasão em salvaguardas de Destreza para metade do dano.",
            priority=60,
            when=lambda f: f["type"] == "martial_feature" and f.get("feature") == "evasao",
            resolve=resolver_evasao,
            source="D&D 2024 — Evasão",
        )
    )
    engine.register(
        Rule(
            rule_id="martial.subclass-feature",
            description="Resolve características e efeitos centrais das subclasses marciais.",
            priority=65,
            when=lambda f: f["type"] == "martial_subclass_feature",
            resolve=resolver_subclasse_marcial,
            source="D&D 2024 — subclasses marciais",
        )
    )
    engine.register(
        Rule(
            rule_id="spellcaster.progression",
            description="Resolve atributo, espaços, foco e magias preparadas das classes conjuradoras.",
            priority=60,
            when=lambda f: f["type"] == "spellcaster_feature" and f.get("feature") == "progressao_conjuracao",
            resolve=resolver_progressao_conjuracao,
            source="D&D 2024 — conjuração por classe",
        )
    )
    engine.register(
        Rule(
            rule_id="bard.bardic-inspiration",
            description="Resolve Inspiração de Bardo, dado, usos e recuperação.",
            priority=60,
            when=lambda f: f["type"] == "spellcaster_feature" and f.get("feature") == "inspiracao_bardo",
            resolve=resolver_inspiracao_bardo,
            source="D&D 2024 — Bardo",
        )
    )
    engine.register(
        Rule(
            rule_id="cleric.channel-divinity",
            description="Resolve Canalizar Divindade, Centelha Divina e Expulsar Mortos-Vivos.",
            priority=60,
            when=lambda f: f["type"] == "spellcaster_feature" and f.get("feature") == "canalizar_divindade",
            resolve=resolver_canalizar_divindade,
            source="D&D 2024 — Clérigo",
        )
    )
    engine.register(
        Rule(
            rule_id="druid.wild-shape",
            description="Resolve usos, duração e limitações da Forma Selvagem.",
            priority=60,
            when=lambda f: f["type"] == "spellcaster_feature" and f.get("feature") == "forma_selvagem",
            resolve=resolver_forma_selvagem,
            source="D&D 2024 — Druida",
        )
    )
    engine.register(
        Rule(
            rule_id="wizard.spellbook",
            description="Resolve Livro de Magias, Recuperação Arcana e Memorizar Magia.",
            priority=60,
            when=lambda f: f["type"] == "spellcaster_feature" and f.get("feature") == "livro_de_magias",
            resolve=resolver_livro_de_magias,
            source="D&D 2024 — Mago",
        )
    )
    engine.register(
        Rule(
            rule_id="warlock.features",
            description="Resolve Magia de Pacto, Invocações, Astúcia Mágica e Arcana Mística.",
            priority=60,
            when=lambda f: f["type"] == "advanced_caster_feature" and f.get("classe") == "bruxo",
            resolve=resolver_bruxo,
            source="D&D 2024 — Bruxo",
        )
    )
    engine.register(
        Rule(
            rule_id="warlock.invocation.validate",
            description="Valida nome, nível, pacto, truque e repetição de uma Invocação Mística.",
            priority=70,
            when=lambda f: f["type"] == "warlock_invocation" and f.get("operation", "resolve") == "validate",
            resolve=validar_invocacao,
            source="D&D 2024 — Invocações Místicas",
        )
    )
    engine.register(
        Rule(
            rule_id="warlock.invocation.resolve",
            description="Resolve o efeito detalhado de uma Invocação Mística do Bruxo.",
            priority=70,
            when=lambda f: f["type"] == "warlock_invocation" and f.get("operation", "resolve") != "validate",
            resolve=resolver_invocacao,
            source="D&D 2024 — Invocações Místicas",
        )
    )
    engine.register(
        Rule(
            rule_id="sorcerer.features",
            description="Resolve Fonte de Magia, Metamagia e Feitiçaria Inata.",
            priority=60,
            when=lambda f: f["type"] == "advanced_caster_feature" and f.get("classe") == "feiticeiro",
            resolve=resolver_feiticeiro,
            source="D&D 2024 — Feiticeiro",
        )
    )
    engine.register(
        Rule(
            rule_id="ranger.features",
            description="Resolve progressão de Guardião, Inimigo Favorito e recursos de exploração.",
            priority=60,
            when=lambda f: f["type"] == "advanced_caster_feature" and f.get("classe") == "guardiao",
            resolve=resolver_guardiao,
            source="D&D 2024 — Guardião",
        )
    )
    engine.register(
        Rule(
            rule_id="paladin.features",
            description="Resolve progressão de conjuração e recursos do Paladino.",
            priority=60,
            when=lambda f: f["type"] == "advanced_caster_feature" and f.get("classe") == "paladino",
            resolve=resolver_paladino,
            source="D&D 2024 — Paladino",
        )
    )
    engine.register(
        Rule(
            rule_id="feat.validate",
            description="Valida categoria, nível, pré-requisitos e disponibilidade de talentos.",
            priority=70,
            when=lambda f: f["type"] == "feat" and f.get("operation", "resolve") == "validate",
            resolve=validar_talento,
            source="D&D 2024 — Talentos",
        )
    )
    engine.register(
        Rule(
            rule_id="feat.resolve",
            description="Resolve os efeitos determinísticos de talentos de Origem, Gerais e Épicos.",
            priority=70,
            when=lambda f: f["type"] == "feat" and f.get("operation", "resolve") != "validate",
            resolve=resolver_talento,
            source="D&D 2024 — Talentos",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.list",
            description="Lista magias por escola e círculo.",
            priority=70,
            when=lambda f: f["type"] == "spell_catalog" and f.get("operation") == "list",
            resolve=lambda f: {"resultado": "listado", "magias": listar_magias(f.get("escola"), f.get("circulo"))},
            source="D&D 2024 — Magias",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.lookup",
            description="Consulta escola, círculo, componentes e duração de uma magia.",
            priority=70,
            when=lambda f: f["type"] == "spell_catalog" and f.get("operation") == "lookup",
            resolve=lambda f: (
                {"resultado": "encontrada", "magia": obter_magia(f["magia"])}
                if obter_magia(f["magia"])
                else {"resultado": "bloqueado", "motivo": "magia_desconhecida"}
            ),
            source="D&D 2024 — Magias",
        )
    )
    engine.register(
        Rule(
            rule_id="spell.cast-complete",
            description="Resolve componentes, concentração, círculo usado e upcasting.",
            priority=110,
            when=lambda f: f["type"] in {"spell", "spell_cast"} and "magia" in f,
            resolve=resolver_magia,
            source="D&D 2024 — Magias",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.lookup",
            description="Consulta armas, armaduras, equipamentos e itens mágicos.",
            priority=70,
            when=lambda f: f["type"] == "equipment" and f.get("operation") == "lookup",
            resolve=lambda f: (
                {"resultado": "encontrado", "item": consultar_item(f["item"], f.get("categoria"))}
                if consultar_item(f["item"], f.get("categoria"))
                else {"resultado": "bloqueado", "motivo": "item_desconhecido"}
            ),
            source="D&D 2024 — Equipamento",
        )
    )
    engine.register(
        Rule(
            rule_id="equipment.inventory",
            description="Calcula carga, capacidade e inventário carregado.",
            priority=70,
            when=lambda f: f["type"] == "equipment" and f.get("operation") == "inventory",
            resolve=resolver_inventario,
            source="D&D 2024 — Capacidade de Carga",
        )
    )
    engine.register(
        Rule(
            rule_id="economy.buy",
            description="Compra equipamentos usando moedas e verifica saldo.",
            priority=70,
            when=lambda f: f["type"] == "economy" and f.get("operation") == "buy",
            resolve=comprar_item,
            source="D&D 2024 — Economia",
        )
    )
    engine.register(
        Rule(
            rule_id="economy.sell",
            description="Vende equipamentos pela fração de venda informada.",
            priority=70,
            when=lambda f: f["type"] == "economy" and f.get("operation") == "sell",
            resolve=vender_item,
            source="D&D 2024 — Economia",
        )
    )
    engine.register(
        Rule(
            rule_id="magic-item.attunement",
            description="Controla sintonização, limite de três itens e descanso curto.",
            priority=70,
            when=lambda f: f["type"] == "magic_item" and f.get("operation") == "attune",
            resolve=resolver_sintonizacao,
            source="D&D 2024 — Itens Mágicos",
        )
    )
    engine.register(
        Rule(
            rule_id="magic-item.use",
            description="Usa item mágico, valida sintonização e consome cargas.",
            priority=70,
            when=lambda f: f["type"] == "magic_item" and f.get("operation") == "use",
            resolve=usar_item_magico,
            source="D&D 2024 — Itens Mágicos",
        )
    )
    engine.register(
        Rule(
            rule_id="class.feature",
            description="Resolve características executáveis das 13 classes, incluindo recursos marciais, auras, perícias e capstones.",
            priority=80,
            when=lambda f: f["type"] == "class_feature",
            resolve=resolver_caracteristica,
            source="D&D 2024 — características de classe",
        )
    )
    engine.register(
        Rule(
            rule_id="bestiary.catalog",
            description="Consulta monstros do SRD 5.2.1, filtra o catálogo e calcula XP de ND ou encontro.",
            priority=80,
            when=lambda f: f["type"] == "bestiary",
            resolve=resolver_bestiario,
            source="SRD 5.2.1 — bestiário",
        )
    )
    engine.register(
        Rule(
            rule_id="ability.skill-check",
            description="Resolve teste ativo de habilidade com perícia, proficiência, vantagem e modificadores.",
            priority=75,
            when=lambda f: f["type"] == "skill_check",
            resolve=resolver_teste_habilidade,
            source="D&D 2024 — Testes de D20 e perícias",
        )
    )
    engine.register(
        Rule(
            rule_id="ability.passive-check",
            description="Calcula teste passivo com ajuste de vantagem ou desvantagem.",
            priority=75,
            when=lambda f: f["type"] == "passive_check",
            resolve=resolver_teste_passivo,
            source="D&D 2024 — Testes passivos",
        )
    )
    engine.register(
        Rule(
            rule_id="ability.group-check",
            description="Resolve teste de grupo pela regra de pelo menos metade dos participantes.",
            priority=75,
            when=lambda f: f["type"] == "group_check",
            resolve=resolver_teste_grupo,
            source="D&D 2024 — Testes em grupo",
        )
    )
    engine.register(
        Rule(
            rule_id="heroic-inspiration.reroll",
            description="Consome Inspiração Heroica para rerrolar um d20 e usar o novo resultado.",
            priority=75,
            when=lambda f: f["type"] == "heroic_inspiration",
            resolve=resolver_inspiracao_heroica,
            source="D&D 2024 — Inspiração Heroica",
        )
    )

    engine.register(
        Rule(
            rule_id="saving-throw.complete",
            description="Resolve salvaguarda com atributo, bônus de proficiência e vantagem/desvantagem.",
            priority=120,
            when=lambda f: f["type"] == "saving_throw_check",
            resolve=resolver_salvaguarda,
            source="D&D 2024 — Salvaguardas",
        )
    )
    engine.register(
        Rule(
            rule_id="initiative.complete",
            description="Resolve iniciativa como teste de Destreza com bônus e vantagem/desvantagem.",
            priority=120,
            when=lambda f: f["type"] == "initiative_check",
            resolve=resolver_iniciativa,
            source="D&D 2024 — Iniciativa",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.hide",
            description="Resolve a ação Esconder-se com os requisitos do PHB 2024.",
            priority=70,
            when=lambda f: f["type"] == "hide_action",
            resolve=resolver_acao_esconder,
            source="D&D 2024 — Esconder-se",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.influence",
            description="Resolve a ação Influenciar com disposição, perícia social e CD padrão.",
            priority=70,
            when=lambda f: f["type"] == "influence_action",
            resolve=resolver_acao_influenciar,
            source="D&D 2024 — Influenciar",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.hide-event",
            description="Encerra esconderijo quando ocorre som alto, descoberta, ataque ou magia verbal.",
            priority=70,
            when=lambda f: f["type"] == "hide_event",
            resolve=resolver_fim_esconderijo,
            source="D&D 2024 — Esconder-se",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.search",
            description="Resolve Search usando as perícias sugeridas pelo PHB 2024.",
            priority=70,
            when=lambda f: f["type"] == "search_action",
            resolve=resolver_acao_procurar,
            source="D&D 2024 — Search",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.help",
            description="Prepara vantagem para o próximo teste ou ataque com a ação Ajuda.",
            priority=70,
            when=lambda f: f["type"] == "help_action",
            resolve=resolver_acao_ajudar,
            source="D&D 2024 — Help",
        )
    )
    engine.register(
        Rule(
            rule_id="exploration.study",
            description="Resolve Study usando as perícias de Inteligência do PHB 2024.",
            priority=70,
            when=lambda f: f["type"] == "study_action",
            resolve=resolver_acao_estudar,
            source="D&D 2024 — Study",
        )
    )
    engine.register(
        Rule(
            rule_id="combat.dodge",
            description="Resolve Esquivar: ataques contra a criatura têm desvantagem se ela vir o atacante; salvaguardas de Destreza têm vantagem.",
            priority=70,
            when=lambda f: f["type"] == "dodge_action",
            resolve=resolver_acao_esquivar,
            source="D&D 2024 — Esquivar",
        )
    )
    return engine
