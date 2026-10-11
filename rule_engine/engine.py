from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

Condition = Callable[[Mapping[str, Any]], bool]
Resolver = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class Rule:
    """Regra declarativa: quando aplicável, produz uma resolução."""

    rule_id: str
    description: str
    priority: int
    when: Condition
    resolve: Resolver
    source: str = "core"


@dataclass
class Resolution:
    """Resultado auditável que pode ser usado pelo programa ou pela IA."""

    status: str
    outcome: dict[str, Any]
    matched_rules: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)

    def to_ai_instruction(self) -> str:
        """Converte a decisão em instrução curta e verificável para um LLM."""
        rules = ", ".join(self.matched_rules) if self.matched_rules else "nenhuma"
        details = "; ".join(f"{key}={value}" for key, value in self.outcome.items())
        return (
            "Aplique a decisão do motor de regras sem contradizê-la. "
            f"Regras aplicadas: {rules}. Resultado: {details}."
        )


class RuleEngine:
    """Motor pequeno e determinístico com prioridade e trilha de auditoria."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = list(rules or [])

    def register(self, rule: Rule) -> None:
        if any(existing.rule_id == rule.rule_id for existing in self._rules):
            raise ValueError(f"Regra já registrada: {rule.rule_id}")
        self._rules.append(rule)

    def evaluate(self, facts: Mapping[str, Any]) -> Resolution:
        ordered = sorted(self._rules, key=lambda rule: (-rule.priority, rule.rule_id))
        trace: list[str] = []
        matched: list[str] = []

        for rule in ordered:
            try:
                applies = bool(rule.when(facts))
            except (KeyError, TypeError, ValueError) as exc:
                trace.append(f"{rule.rule_id}: ignorada ({exc.__class__.__name__})")
                continue
            trace.append(f"{rule.rule_id}: {'aplicável' if applies else 'não aplicável'}")
            if applies:
                matched.append(rule.rule_id)
                outcome = dict(rule.resolve(facts))
                outcome.setdefault("rule_source", rule.source)
                return Resolution("resolved", outcome, matched, trace)

        return Resolution(
            "undetermined",
            {"reason": "Nenhuma regra aplicável aos fatos fornecidos"},
            matched,
            trace,
        )
