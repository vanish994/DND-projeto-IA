"""Alcance, cobertura, linha de visão, tamanho, distância e queda."""

from __future__ import annotations

from math import ceil, sqrt
from typing import Any, Mapping, Sequence

TAMANHOS = {
    "minúsculo": 0,
    "pequeno": 1,
    "médio": 1,
    "grande": 2,
    "enorme": 3,
    "imenso": 4,
}


def distancia_grade(dx: int, dy: int, *, diagonal_alternada: bool = False) -> int:
    """Calcula distância em quadrados; cada quadrado equivale a 1,5 m."""
    dx, dy = abs(int(dx)), abs(int(dy))
    if diagonal_alternada:
        diagonais = min(dx, dy)
        retas = max(dx, dy) - diagonais
        return retas + (diagonais * 3 + 1) // 2
    return max(dx, dy)


def distancia_euclidiana(dx: float, dy: float) -> float:
    return sqrt(float(dx) ** 2 + float(dy) ** 2)


def espaco_por_tamanho(tamanho: str | int) -> int:
    """Retorna o lado ocupado em quadrados por uma criatura."""
    if isinstance(tamanho, str):
        if tamanho.lower() not in TAMANHOS:
            raise ValueError("Tamanho de criatura inválido")
        categoria = TAMANHOS[tamanho.lower()]
    else:
        categoria = int(tamanho)
    if categoria < 0 or categoria > 4:
        raise ValueError("Tamanho de criatura inválido")
    return 1 if categoria <= 1 else 2 ** (categoria - 1)


def resolver_alcance(
    distancia: float,
    *,
    alcance: float,
    alcance_maximo: float | None = None,
    ataque_a_distancia: bool = False,
    alcance_estendido: bool = False,
) -> dict[str, Any]:
    """Verifica alcance normal, máximo e Desvantagem além do alcance normal."""
    distancia = float(distancia)
    alcance = float(alcance)
    maximo = float(alcance_maximo if alcance_maximo is not None else alcance)
    if distancia < 0 or alcance < 0 or maximo < alcance:
        raise ValueError("Distâncias de alcance inválidas")
    if distancia > maximo:
        return {"resultado": "fora_de_alcance", "distancia": distancia, "alcance_maximo": maximo}
    desvantagem = bool(ataque_a_distancia and distancia > alcance and not alcance_estendido)
    return {
        "resultado": "dentro_do_alcance",
        "distancia": distancia,
        "desvantagem_por_alcance": desvantagem,
    }


def resolver_cobertura(cobertura: str, *, linha_de_visao: bool = True) -> dict[str, Any]:
    """Resolve o bônus de CA e o bloqueio da Cobertura Total."""
    cobertura = cobertura.lower()
    bonus = {"nenhuma": 0, "meia": 2, "tres_quartos": 5, "total": 0}
    if cobertura not in bonus:
        raise ValueError("Cobertura inválida")
    if cobertura == "total" or not linha_de_visao:
        return {"resultado": "bloqueado", "motivo": "cobertura_total_ou_sem_linha_de_visao"}
    return {"resultado": "permitido", "bonus_ca": bonus[cobertura], "cobertura": cobertura}


def resolver_linha_de_visao(*, bloqueada: bool = False, cobertura: str = "nenhuma") -> dict[str, Any]:
    """Determina se o alvo pode ser escolhido pela linha de visão."""
    if bloqueada or cobertura.lower() == "total":
        return {"resultado": "bloqueada"}
    return {"resultado": "livre"}


def resolver_ataque_geometria(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Combina distância, alcance, linha de visão e cobertura antes do ataque."""
    alcance = resolver_alcance(
        fatos["distance"],
        alcance=fatos["range"],
        alcance_maximo=fatos.get("maximum_range"),
        ataque_a_distancia=bool(fatos.get("ranged_attack", False)),
        alcance_estendido=bool(fatos.get("extended_range", False)),
    )
    if alcance["resultado"] == "fora_de_alcance":
        return {"tipo": "geometria_ataque", "resultado": "bloqueado", "motivo": "fora_de_alcance"}
    visao = resolver_linha_de_visao(
        bloqueada=bool(fatos.get("line_of_sight_blocked", False)),
        cobertura=fatos.get("cover", "nenhuma"),
    )
    if visao["resultado"] == "bloqueada":
        return {"tipo": "geometria_ataque", "resultado": "bloqueado", "motivo": "linha_de_visao"}
    cobertura = resolver_cobertura(fatos.get("cover", "nenhuma"))
    if cobertura["resultado"] == "bloqueado":
        return {"tipo": "geometria_ataque", "resultado": "bloqueado", "motivo": cobertura["motivo"]}
    return {
        "tipo": "geometria_ataque",
        "resultado": "permitido",
        "desvantagem_por_alcance": alcance["desvantagem_por_alcance"],
        "bonus_ca_por_cobertura": cobertura["bonus_ca"],
    }


def resolver_queda(distancia: float, *, rolagens: Sequence[int] | None = None) -> dict[str, Any]:
    """Resolve queda: 1d6 por 3 m, máximo 20d6, e condição Caído."""
    distancia = float(distancia)
    if distancia < 0:
        raise ValueError("A distância da queda não pode ser negativa")
    dados = min(20, int(ceil(distancia / 3)))
    rolagens = tuple(int(valor) for valor in (rolagens or ()))
    if any(valor < 1 or valor > 6 for valor in rolagens):
        raise ValueError("Dados de queda devem estar entre 1 e 6")
    resultado: dict[str, Any] = {
        "tipo": "queda",
        "distancia": distancia,
        "dados_d6": dados,
        "condicao": "caido" if distancia > 0 else None,
    }
    if rolagens:
        if len(rolagens) != dados:
            raise ValueError("A quantidade de dados não corresponde à distância da queda")
        resultado["dano"] = sum(rolagens)
    return resultado
