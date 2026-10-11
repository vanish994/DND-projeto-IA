from __future__ import annotations

from typing import Any, Mapping

from .engine import Rule, RuleEngine


def _check_total(facts: Mapping[str, Any]) -> int:
    return int(facts["roll"]) + int(facts.get("modifier", 0))


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
    return engine
