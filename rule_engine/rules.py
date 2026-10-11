from __future__ import annotations

from typing import Any, Mapping

from .combat_special import (
    resolver_agarrar,
    resolver_ataque_oportunidade,
    resolver_empurrar,
    resolver_escape_agarramento,
)
from .engine import Rule, RuleEngine
from .combat_geometry import (
    resolver_ataque_geometria, resolver_alcance, resolver_cobertura,
    resolver_queda, resolver_linha_de_visao, espaco_por_tamanho,
)
from .combat_movement import (
    resolver_ataque_subaquatico, resolver_montaria, resolver_movimento_especial,
    resolver_objeto, resolver_sentidos,
)
from .survival import (
    adicionar_exaustao, ajustar_dano, aplicar_dano, curar,
    descanso_curto, descanso_longo, resolver_descanso, salvaguarda_contra_morte, estabilizar,
)


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
    engine.register(Rule(
        rule_id="ability-check.natural-20",
        description="Um 20 natural resolve o teste como sucesso automático.",
        priority=100,
        when=lambda f: f["type"] == "ability_check" and int(f["roll"]) == 20,
        resolve=lambda f: {"type": f["type"], "result": "success", "reason": "natural_20"},
        source="D&D 2024 — teste de d20",
    ))
    engine.register(Rule(
        rule_id="ability-check.natural-1",
        description="Um 1 natural resolve o teste como falha automática.",
        priority=100,
        when=lambda f: f["type"] == "ability_check" and int(f["roll"]) == 1,
        resolve=lambda f: {"type": f["type"], "result": "failure", "reason": "natural_1"},
        source="D&D 2024 — teste de d20",
    ))
    engine.register(Rule(
        rule_id="ability-check.meets-dc",
        description="O total do teste iguala ou supera a Classe de Dificuldade.",
        priority=50,
        when=lambda f: f["type"] == "ability_check" and _check_total(f) >= int(f["dc"]),
        resolve=lambda f: {
            "type": f["type"], "result": "success", "reason": "total_meets_dc",
            "total": _check_total(f), "dc": int(f["dc"]),
        },
        source="D&D 2024 — testes de d20",
    ))
    engine.register(Rule(
        rule_id="ability-check.below-dc",
        description="O total do teste fica abaixo da Classe de Dificuldade.",
        priority=40,
        when=lambda f: f["type"] == "ability_check" and _check_total(f) < int(f["dc"]),
        resolve=lambda f: {
            "type": f["type"], "result": "failure", "reason": "total_below_dc",
            "total": _check_total(f), "dc": int(f["dc"]),
        },
        source="D&D 2024 — testes de d20",
    ))
    engine.register(Rule(
        rule_id="attack.natural-20",
        description="Um 20 natural supera a Classe de Armadura e causa um acerto crítico.",
        priority=100,
        when=lambda f: f["type"] == "attack" and int(f["roll"]) == 20,
        resolve=lambda f: {
            "type": f["type"], "result": "hit", "critical": True,
            "reason": "natural_20", "total": _check_total(f),
        },
        source="D&D 2024 — jogadas de ataque",
    ))
    engine.register(Rule(
        rule_id="attack.natural-1",
        description="Um 1 natural falha na jogada de ataque.",
        priority=100,
        when=lambda f: f["type"] == "attack" and int(f["roll"]) == 1,
        resolve=lambda f: {
            "type": f["type"], "result": "miss", "critical": False,
            "reason": "natural_1", "total": _check_total(f),
        },
        source="D&D 2024 — jogadas de ataque",
    ))
    engine.register(Rule(
        rule_id="attack.meets-ac",
        description="O total da jogada de ataque iguala ou supera a Classe de Armadura.",
        priority=50,
        when=lambda f: f["type"] == "attack" and _check_total(f) >= int(f["target_ac"]),
        resolve=lambda f: {
            "type": f["type"], "result": "hit", "critical": False,
            "reason": "total_meets_ac", "total": _check_total(f),
            "target_ac": int(f["target_ac"]),
        },
        source="D&D 2024 — jogadas de ataque",
    ))
    engine.register(Rule(
        rule_id="attack.below-ac",
        description="O total da jogada de ataque fica abaixo da Classe de Armadura.",
        priority=40,
        when=lambda f: f["type"] == "attack" and _check_total(f) < int(f["target_ac"]),
        resolve=lambda f: {
            "type": f["type"], "result": "miss", "critical": False,
            "reason": "total_below_ac", "total": _check_total(f),
            "target_ac": int(f["target_ac"]),
        },
        source="D&D 2024 — jogadas de ataque",
    ))
    engine.register(Rule(
        rule_id="damage.critical",
        description="No acerto crítico, os dados de dano são rolados duas vezes; o modificador é somado uma vez.",
        priority=100,
        when=lambda f: f["type"] == "damage" and bool(f.get("critical", False)),
        resolve=lambda f: {
            "type": f["type"], "result": "damage", "critical": True,
            "total": _damage_total(f, critical=True),
            "dice_count": len(f.get("damage_dice", [])) * 2,
            "modifier": int(f.get("damage_modifier", 0)),
        },
        source="D&D 2024 — acertos críticos",
    ))
    engine.register(Rule(
        rule_id="damage.normal",
        description="O dano normal soma os resultados dos dados ao modificador de dano.",
        priority=50,
        when=lambda f: f["type"] == "damage" and not bool(f.get("critical", False)),
        resolve=lambda f: {
            "type": f["type"], "result": "damage", "critical": False,
            "total": _damage_total(f), "dice_count": len(f.get("damage_dice", [])),
            "modifier": int(f.get("damage_modifier", 0)),
        },
        source="D&D 2024 — dano",
    ))
    engine.register(Rule(
        rule_id="saving-throw.natural-20",
        description="Um 20 natural obtém sucesso automático na salvaguarda.",
        priority=100,
        when=lambda f: f["type"] == "saving_throw" and int(f["roll"]) == 20,
        resolve=lambda f: {
            "type": f["type"], "result": "success", "reason": "natural_20",
            "total": _check_total(f),
        },
        source="D&D 2024 — salvaguardas",
    ))
    engine.register(Rule(
        rule_id="saving-throw.natural-1",
        description="Um 1 natural falha automaticamente na salvaguarda.",
        priority=100,
        when=lambda f: f["type"] == "saving_throw" and int(f["roll"]) == 1,
        resolve=lambda f: {
            "type": f["type"], "result": "failure", "reason": "natural_1",
            "total": _check_total(f),
        },
        source="D&D 2024 — salvaguardas",
    ))
    engine.register(Rule(
        rule_id="saving-throw.meets-dc",
        description="O total da salvaguarda iguala ou supera a Classe de Dificuldade.",
        priority=50,
        when=lambda f: f["type"] == "saving_throw" and _check_total(f) >= int(f["dc"]),
        resolve=lambda f: {
            "type": f["type"], "result": "success", "reason": "total_meets_dc",
            "total": _check_total(f), "dc": int(f["dc"]),
        },
        source="D&D 2024 — salvaguardas",
    ))
    engine.register(Rule(
        rule_id="saving-throw.below-dc",
        description="O total da salvaguarda fica abaixo da Classe de Dificuldade.",
        priority=40,
        when=lambda f: f["type"] == "saving_throw" and _check_total(f) < int(f["dc"]),
        resolve=lambda f: {
            "type": f["type"], "result": "failure", "reason": "total_below_dc",
            "total": _check_total(f), "dc": int(f["dc"]),
        },
        source="D&D 2024 — salvaguardas",
    ))
    engine.register(Rule(
        rule_id="spell.cast.no-slot",
        description="A magia não pode ser conjurada sem um espaço de magia disponível.",
        priority=100,
        when=lambda f: f["type"] == "spell_cast" and not bool(f.get("has_slot", False)),
        resolve=lambda f: {
            "type": f["type"], "result": "blocked", "reason": "no_slot",
            "spell_level": int(f["spell_level"]),
        },
        source="D&D 2024 — conjuração",
    ))
    engine.register(Rule(
        rule_id="spell.cast.slot-too-low",
        description="O espaço de magia precisa ser do nível da magia ou superior.",
        priority=90,
        when=lambda f: (
            f["type"] == "spell_cast" and bool(f.get("has_slot", False))
            and int(f["slot_level"]) < int(f["spell_level"])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "blocked", "reason": "slot_level_too_low",
            "spell_level": int(f["spell_level"]), "slot_level": int(f["slot_level"]),
        },
        source="D&D 2024 — conjuração",
    ))
    engine.register(Rule(
        rule_id="spell.cast.concentration-replaced",
        description="Conjurar outra magia de concentração encerra a concentração anterior.",
        priority=80,
        when=lambda f: (
            f["type"] == "spell_cast" and bool(f.get("has_slot", False))
            and int(f["slot_level"]) >= int(f["spell_level"])
            and bool(f.get("concentration_required", False))
            and bool(f.get("concentrating", False))
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "cast", "reason": "concentration_replaced",
            "ends_previous_concentration": True,
        },
        source="D&D 2024 — concentração",
    ))
    engine.register(Rule(
        rule_id="spell.cast.valid",
        description="A magia pode ser conjurada com o espaço disponível.",
        priority=40,
        when=lambda f: (
            f["type"] == "spell_cast" and bool(f.get("has_slot", False))
            and int(f["slot_level"]) >= int(f["spell_level"])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "cast", "reason": "valid_spell_slot",
            "ends_previous_concentration": False,
        },
        source="D&D 2024 — conjuração",
    ))
    engine.register(Rule(
        rule_id="condition.apply.immune",
        description="Uma criatura imune não recebe a condição.",
        priority=100,
        when=lambda f: (
            f["type"] == "condition" and f.get("operation") == "apply"
            and f.get("condition") in f.get("immunities", [])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "not_applied", "reason": "immune",
            "condition": f["condition"],
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.apply.already-active",
        description="Uma condição já ativa não é aplicada novamente por esta resolução.",
        priority=90,
        when=lambda f: (
            f["type"] == "condition" and f.get("operation") == "apply"
            and f.get("condition") in f.get("active_conditions", [])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "already_active", "condition": f["condition"],
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.apply",
        description="A condição é aplicada ao alvo.",
        priority=50,
        when=lambda f: f["type"] == "condition" and f.get("operation") == "apply",
        resolve=lambda f: {
            "type": f["type"], "result": "applied", "condition": f["condition"],
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.remove.active",
        description="A condição ativa é removida do alvo.",
        priority=60,
        when=lambda f: (
            f["type"] == "condition" and f.get("operation") == "remove"
            and f.get("condition") in f.get("active_conditions", [])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "removed", "condition": f["condition"],
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.remove.absent",
        description="Não há condição ativa para remover.",
        priority=40,
        when=lambda f: (
            f["type"] == "condition" and f.get("operation") == "remove"
            and f.get("condition") not in f.get("active_conditions", [])
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "not_active", "condition": f["condition"],
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.attack.cancelled",
        description="Vantagem e desvantagem na mesma jogada se cancelam.",
        priority=100,
        when=lambda f: (
            f["type"] == "condition_effect" and f.get("action") == "attack"
            and bool(set(f.get("attacker_conditions", [])) & {"blinded", "poisoned", "restrained"})
            and bool(set(f.get("target_conditions", [])) & {"blinded", "restrained"})
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "normal", "reason": "advantage_disadvantage_cancel",
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.attack.advantage",
        description="Atacar uma criatura cega ou impedida concede vantagem.",
        priority=60,
        when=lambda f: (
            f["type"] == "condition_effect" and f.get("action") == "attack"
            and bool(set(f.get("target_conditions", [])) & {"blinded", "restrained"})
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "advantage", "reason": "target_condition",
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="condition.attack.disadvantage",
        description="Atacar enquanto cego, envenenado ou impedido impõe desvantagem.",
        priority=50,
        when=lambda f: (
            f["type"] == "condition_effect" and f.get("action") == "attack"
            and bool(set(f.get("attacker_conditions", [])) & {"blinded", "poisoned", "restrained"})
        ),
        resolve=lambda f: {
            "type": f["type"], "result": "disadvantage", "reason": "attacker_condition",
        },
        source="D&D 2024 — condições",
    ))
    engine.register(Rule(
        rule_id="attack.opportunity",
        description="Uma criatura que sai do alcance pode provocar um ataque de oportunidade.",
        priority=50,
        when=lambda f: f["type"] == "opportunity_attack",
        resolve=resolver_ataque_oportunidade,
        source="D&D 2024 — ataques de oportunidade",
    ))
    engine.register(Rule(
        rule_id="unarmed.shove",
        description="Empurrar exige uma salvaguarda de Força ou Destreza e permite empurrar ou deixar Caído.",
        priority=50,
        when=lambda f: f["type"] == "shove",
        resolve=resolver_empurrar,
        source="D&D 2024 — Ataque Desarmado",
    ))
    engine.register(Rule(
        rule_id="unarmed.grapple",
        description="Agarrar exige uma salvaguarda de Força ou Destreza e pode aplicar Imobilizado.",
        priority=50,
        when=lambda f: f["type"] == "grapple",
        resolve=resolver_agarrar,
        source="D&D 2024 — Ataque Desarmado",
    ))
    engine.register(Rule(
        rule_id="grapple.escape",
        description="A criatura agarrada pode escapar com Atletismo ou Acrobacia contra a CD do agarramento.",
        priority=50,
        when=lambda f: f["type"] == "grapple_escape",
        resolve=resolver_escape_agarramento,
        source="D&D 2024 — Imobilizado",
    ))
    engine.register(Rule(
        rule_id="survival.damage",
        description="Aplica dano aos PV e absorve primeiro os PV Temporários.",
        priority=50,
        when=lambda f: f["type"] == "damage_application",
        resolve=lambda f: aplicar_dano(
            f["estado"], f["damage"], critico=bool(f.get("critical", False)),
            dano_ajustado=bool(f.get("adjusted", False)), tipo_dano=f.get("damage_type"),
            origem=f.get("source"), resistencias=f.get("resistances", ()),
            vulnerabilidades=f.get("vulnerabilities", ()), imunidades=f.get("immunities", ()),
        ),
        source="D&D 2024 — Pontos de Vida",
    ))
    engine.register(Rule(
        rule_id="survival.healing",
        description="Cura PV sem ultrapassar os PV máximos.",
        priority=50,
        when=lambda f: f["type"] == "healing",
        resolve=lambda f: curar(f["estado"], f["amount"]),
        source="D&D 2024 — Cura",
    ))
    engine.register(Rule(
        rule_id="survival.death-save",
        description="Resolve uma Salvaguarda contra a Morte.",
        priority=50,
        when=lambda f: f["type"] == "death_save",
        resolve=lambda f: salvaguarda_contra_morte(f["estado"], f["roll"]),
        source="D&D 2024 — Salvaguardas contra a Morte",
    ))
    engine.register(Rule(
        rule_id="survival.stabilize",
        description="Estabiliza uma criatura com 0 PV.",
        priority=50,
        when=lambda f: f["type"] == "stabilize",
        resolve=lambda f: estabilizar(f["estado"], teste_medicina=f.get("medicine_test")),
        source="D&D 2024 — Estabilização",
    ))
    engine.register(Rule(
        rule_id="survival.exhaustion",
        description="Adiciona níveis de Exaustão e aplica seu modificador.",
        priority=50,
        when=lambda f: f["type"] == "exhaustion",
        resolve=lambda f: adicionar_exaustao(f["estado"], f.get("levels", 1)),
        source="D&D 2024 — Exaustão",
    ))
    engine.register(Rule(
        rule_id="survival.short-rest",
        description="Gasta Dados de Vida e recupera PV durante um Descanso Curto.",
        priority=50,
        when=lambda f: f["type"] == "short_rest",
        resolve=lambda f: resolver_descanso({**f, "rest_type": "curto"}),
        source="D&D 2024 — Descanso Curto",
    ))
    engine.register(Rule(
        rule_id="survival.long-rest",
        description="Recupera PV e reduz um nível de Exaustão em um Descanso Longo.",
        priority=50,
        when=lambda f: f["type"] == "long_rest",
        resolve=lambda f: resolver_descanso({**f, "rest_type": "longo"}),
        source="D&D 2024 — Descanso Longo",
    ))
    engine.register(Rule(
        rule_id="combat.attack-geometry",
        description="Valida distância, alcance, linha de visão e cobertura antes do ataque.",
        priority=50,
        when=lambda f: f["type"] == "attack_geometry",
        resolve=resolver_ataque_geometria,
        source="D&D 2024 — Combate: alcance e cobertura",
    ))
    engine.register(Rule(
        rule_id="combat.range",
        description="Verifica alcance normal e alcance máximo de um ataque.",
        priority=50,
        when=lambda f: f["type"] == "range",
        resolve=lambda f: resolver_alcance(
            f["distance"], alcance=f["range"], alcance_maximo=f.get("maximum_range"),
            ataque_a_distancia=bool(f.get("ranged_attack", False)),
            alcance_estendido=bool(f.get("extended_range", False)),
        ),
        source="D&D 2024 — alcance",
    ))
    engine.register(Rule(
        rule_id="combat.cover",
        description="Aplica o bônus de CA da cobertura ou bloqueia Cobertura Total.",
        priority=50,
        when=lambda f: f["type"] == "cover",
        resolve=lambda f: resolver_cobertura(f["cover"], linha_de_visao=bool(f.get("line_of_sight", True))),
        source="D&D 2024 — cobertura",
    ))
    engine.register(Rule(
        rule_id="combat.line-of-sight",
        description="Verifica se há linha de visão até o alvo.",
        priority=50,
        when=lambda f: f["type"] == "line_of_sight",
        resolve=lambda f: resolver_linha_de_visao(
            bloqueada=bool(f.get("blocked", False)), cobertura=f.get("cover", "nenhuma")
        ),
        source="D&D 2024 — linha de visão",
    ))
    engine.register(Rule(
        rule_id="combat.fall",
        description="Aplica dano de queda e a condição Caído.",
        priority=50,
        when=lambda f: f["type"] == "fall",
        resolve=lambda f: resolver_queda(f["distance"], rolagens=f.get("rolls")),
        source="D&D 2024 — queda",
    ))
    engine.register(Rule(
        rule_id="combat.senses",
        description="Resolve Visão no Escuro, Visão às Cegas, Sentido de Tremor e Visão Verdadeira.",
        priority=50,
        when=lambda f: f["type"] == "senses",
        resolve=resolver_sentidos,
        source="D&D 2024 — sentidos especiais",
    ))
    engine.register(Rule(
        rule_id="combat.special-movement",
        description="Resolve rastejar, escalar, nadar e levantar-se de Caído.",
        priority=50,
        when=lambda f: f["type"] == "special_movement",
        resolve=resolver_movimento_especial,
        source="D&D 2024 — movimento especial",
    ))
    engine.register(Rule(
        rule_id="combat.mounted",
        description="Resolve montar, desmontar, controle da montaria e queda do cavaleiro.",
        priority=50,
        when=lambda f: f["type"] == "mounted_combat",
        resolve=resolver_montaria,
        source="D&D 2024 — combate montado",
    ))
    engine.register(Rule(
        rule_id="combat.underwater",
        description="Aplica limitações de armas e alcance no combate subaquático.",
        priority=50,
        when=lambda f: f["type"] == "underwater_attack",
        resolve=resolver_ataque_subaquatico,
        source="D&D 2024 — combate subaquático",
    ))
    engine.register(Rule(
        rule_id="combat.object",
        description="Aplica dano aos Pontos de Vida de um objeto.",
        priority=50,
        when=lambda f: f["type"] == "object_damage",
        resolve=resolver_objeto,
        source="D&D 2024 — objetos",
    ))
    return engine
