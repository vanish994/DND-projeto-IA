"""Regras especiais de combate do Livro do Jogador 2024."""

from __future__ import annotations

from typing import Any, Mapping


def cd_ataque_desarmado(fatos: Mapping[str, Any]) -> int:
    """Calcula a CD de Empurrar ou Imobilizar."""
    return 8 + int(fatos.get("forca_modificador", 0)) + int(fatos["bonus_proficiencia"])


def alvo_pode_ser_afetado(fatos: Mapping[str, Any]) -> bool:
    """Verifica o limite de tamanho: no máximo um tamanho maior."""
    return int(fatos["tamanho_alvo"]) <= int(fatos["tamanho_atacante"]) + 1


def resolver_ataque_oportunidade(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Determina se a saída do alcance permite um ataque de oportunidade."""
    impedido = (
        bool(fatos.get("desengajou", False))
        or bool(fatos.get("teleportou", False))
        or bool(fatos.get("movimento_forcado", False))
        or not bool(fatos.get("saiu_do_alcance", False))
        or not bool(fatos.get("reacao_disponivel", False))
    )
    if impedido:
        return {"tipo": "ataque_oportunidade", "resultado": "bloqueado"}
    return {
        "tipo": "ataque_oportunidade",
        "resultado": "permitido",
        "reacao_gasta": True,
    }


def resolver_empurrar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Empurrar por Ataque Desarmado."""
    cd = cd_ataque_desarmado(fatos)
    if not alvo_pode_ser_afetado(fatos):
        return {"tipo": "empurrar", "resultado": "bloqueado", "motivo": "tamanho_invalido", "cd": cd}
    total = int(fatos["rolagem"]) + int(fatos.get("modificador_salvaguarda", 0))
    if total >= cd:
        return {"tipo": "empurrar", "resultado": "resistido", "cd": cd, "total": total}
    return {
        "tipo": "empurrar",
        "resultado": "aplicado",
        "cd": cd,
        "total": total,
        "efeito": "caido" if fatos.get("efeito") == "caido" else "empurrado_1_5_m",
    }


def resolver_agarrar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Agarrar; uma falha na salvaguarda aplica a condição Agarrado."""
    cd = cd_ataque_desarmado(fatos)
    if not alvo_pode_ser_afetado(fatos):
        return {"tipo": "agarrar", "resultado": "bloqueado", "motivo": "tamanho_invalido", "cd": cd}
    total = int(fatos["rolagem"]) + int(fatos.get("modificador_salvaguarda", 0))
    if total >= cd:
        return {"tipo": "agarrar", "resultado": "resistido", "cd": cd, "total": total}
    return {
        "tipo": "agarrar",
        "resultado": "aplicado",
        "cd": cd,
        "total": total,
        "condicao": "agarrado",
    }


def resolver_escape_agarramento(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Atletismo ou Acrobacia contra a CD que impôs o agarramento."""
    total = int(fatos["rolagem"]) + int(fatos.get("modificador", 0))
    cd = int(fatos["cd_agarramento"])
    return {
        "tipo": "escape_agarramento",
        "resultado": "escapou" if total >= cd else "continua_agarrado",
        "total": total,
        "cd": cd,
    }
