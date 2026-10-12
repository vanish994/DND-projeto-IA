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



def rolar_ataque_auditavel(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Rola d20 e resolve ataque com resultado reproduzível por seed."""
    if fatos.get('target_ac') is None:
        return {'type': 'attack', 'result': 'blocked', 'reason': 'target_ac_ausente'}
    seed = fatos.get('seed')
    if seed is None:
        seed = secrets.randbits(64)
    rng = random.Random(str(seed))
    vantagem = bool(fatos.get('advantage', False))
    desvantagem = bool(fatos.get('disadvantage', False))
    if vantagem and desvantagem:
        vantagem = desvantagem = False
    dados = [rng.randint(1, 20) for _ in range(2 if vantagem or desvantagem else 1)]
    roll = max(dados) if vantagem else min(dados) if desvantagem else dados[0]
    modifier = int(fatos.get('modifier', 0))
    total = roll + modifier
    ac = int(fatos['target_ac'])
    critical = roll == 20
    hit = critical or (roll != 1 and total >= ac)
    return {'type': 'attack', 'result': 'hit' if hit else 'miss', 'reason': 'natural_20' if critical else 'natural_1' if roll == 1 else 'total_meets_ac' if hit else 'total_below_ac', 'critical': critical, 'roll': roll, 'rolls': dados, 'die': 'd20', 'seed': str(seed), 'modifier': modifier, 'total': total, 'target_ac': ac, 'advantage': vantagem, 'disadvantage': desvantagem, 'roll_source': 'rule_engine'}


def rolar_iniciativa_auditavel(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Rola iniciativa; surpresa aplica desvantagem conforme D&D 2024."""
    seed = fatos.get('seed')
    if seed is None:
        seed = secrets.randbits(64)
    rng = random.Random(str(seed))
    vantagem = bool(fatos.get('advantage', False))
    desvantagem = bool(fatos.get('disadvantage', False)) or bool(fatos.get('surprised', False))
    if vantagem and desvantagem:
        vantagem = desvantagem = False
    dados = [rng.randint(1, 20) for _ in range(2 if vantagem or desvantagem else 1)]
    roll = max(dados) if vantagem else min(dados) if desvantagem else dados[0]
    modifier = int(fatos.get('modifier', 0))
    return {'type': 'initiative', 'result': 'rolled', 'roll': roll, 'rolls': dados, 'die': 'd20', 'seed': str(seed), 'modifier': modifier, 'total': roll + modifier, 'surprised': bool(fatos.get('surprised', False)), 'advantage': vantagem, 'disadvantage': desvantagem, 'roll_source': 'rule_engine'}


def rolar_salvaguarda_auditavel(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Rola a salvaguarda no motor, com o mesmo d20 reproduzível por ``seed``.

    Sem CD informada, a rolagem fica pendente (``requires_dc``) para o MJ
    definir a dificuldade e reaproveitar a mesma semente.
    """
    seed = fatos.get("seed")
    if seed is None:
        seed = secrets.randbits(64)
    rng = random.Random(str(seed))
    vantagem = bool(fatos.get("advantage", fatos.get("vantagem", False)))
    desvantagem = bool(fatos.get("disadvantage", fatos.get("desvantagem", False)))
    if vantagem and desvantagem:
        vantagem = desvantagem = False
    dados = [rng.randint(1, 20) for _ in range(2 if vantagem or desvantagem else 1)]
    roll = max(dados) if vantagem else min(dados) if desvantagem else dados[0]
    modifier = int(fatos.get("modifier", 0))
    total = roll + modifier
    outcome: dict[str, Any] = {
        "type": "saving_throw",
        "ability": fatos.get("ability", fatos.get("atributo")),
        "roll": roll,
        "rolls": dados,
        "die": "d20",
        "seed": str(seed),
        "modifier": modifier,
        "total": total,
        "advantage": vantagem,
        "disadvantage": desvantagem,
        "roll_source": "rule_engine",
    }
    dc = fatos.get("dc", fatos.get("cd"))
    if dc is None:
        outcome.update({"result": "requires_dc", "reason": "cd_do_mj_ausente"})
        return outcome
    outcome["dc"] = int(dc)
    outcome["result"] = "success" if total >= int(dc) else "failure"
    outcome["reason"] = "total_meets_dc" if total >= int(dc) else "total_below_dc"
    return outcome
