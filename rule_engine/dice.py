"""Rolagens auditáveis usadas pelo Rule Engine."""
from __future__ import annotations

import random
import secrets
from typing import Any, Mapping


def rolar_d20_auditavel(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Gera o d20 no motor e permite reproduzir o resultado usando ``seed``.

    Quando a semente não é fornecida, o motor cria uma semente criptograficamente
    aleatória e a devolve na resolução para auditoria e repetição.
    """
    seed = fatos.get("seed")
    if seed is None:
        seed = secrets.randbits(64)
    rng = random.Random(str(seed))
    roll = rng.randint(1, 20)
    modifier = int(fatos.get("modifier", 0))
    total = roll + modifier
    outcome: dict[str, Any] = {
        "type": "ability_check",
        "ability": fatos.get("ability"),
        "skill": fatos.get("skill"),
        "roll": roll,
        "die": "d20",
        "seed": str(seed),
        "modifier": modifier,
        "total": total,
        "roll_source": "rule_engine",
    }
    if "dc" not in fatos or fatos.get("dc") is None:
        outcome.update({"result": "requires_dc", "reason": "cd_do_mj_ausente"})
        return outcome
    dc = int(fatos["dc"])
    outcome["dc"] = dc
    outcome["result"] = "success" if total >= dc else "failure"
    outcome["reason"] = "total_meets_dc" if total >= dc else "total_below_dc"
    return outcome
