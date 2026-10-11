from __future__ import annotations

from typing import Any, Mapping

from .engine import Rule, RuleEngine


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
    return engine
