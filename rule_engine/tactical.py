"""Combate tático avançado: grade, posição, cobertura e linha de efeito."""
from __future__ import annotations
from math import ceil
from typing import Any, Iterable
from .combat_geometry import distancia_grade, resolver_alcance, resolver_cobertura

Posicao = tuple[int, int]


def _pos(valor: Iterable[int]) -> Posicao:
    x, y = valor
    return int(x), int(y)


def caminho_grade(fatos: dict) -> dict[str, Any]:
    caminho = [_pos(p) for p in fatos.get("caminho", [])]
    if len(caminho) < 2:
        return {"resultado": "permitido", "custo": 0, "destino": caminho[0] if caminho else None}
    terreno = {_pos(p) for p in fatos.get("terreno_dificil", [])}
    bloqueados = {_pos(p) for p in fatos.get("bloqueados", [])}
    custo = 0
    for origem, destino in zip(caminho, caminho[1:]):
        if destino in bloqueados:
            return {"resultado": "bloqueado", "motivo": "casula_bloqueada", "posicao": destino}
        dx, dy = abs(destino[0] - origem[0]), abs(destino[1] - origem[1])
        if max(dx, dy) != 1:
            return {"resultado": "bloqueado", "motivo": "passo_invalido", "posicao": destino}
        custo += 2 if destino in terreno else 1
    disponivel = int(fatos.get("movimento_disponivel", custo))
    return {"resultado": "permitido" if custo <= disponivel else "bloqueado", "motivo": None if custo <= disponivel else "movimento_insuficiente", "custo": custo, "movimento_restante": max(0, disponivel - custo), "destino": caminho[-1]}


def resolver_flanco(fatos: dict) -> dict[str, Any]:
    alvo = _pos(fatos["alvo"])
    aliados = [_pos(p) for p in fatos.get("aliados", [])]
    atacante = _pos(fatos["atacante"])
    adjacentes = [p for p in aliados if distancia_grade(p[0] - alvo[0], p[1] - alvo[1]) <= 1 and p != atacante]
    vetor = (atacante[0] - alvo[0], atacante[1] - alvo[1])
    opostos = any((p[0] - alvo[0]) * vetor[0] + (p[1] - alvo[1]) * vetor[1] < 0 for p in adjacentes)
    return {"resultado": "flanqueado" if opostos else "nao_flanqueado", "vantagem": opostos, "alvo": alvo}


def resolver_linha_grade(fatos: dict) -> dict[str, Any]:
    origem, alvo = _pos(fatos["origem"]), _pos(fatos["alvo"])
    bloqueados = {_pos(p) for p in fatos.get("bloqueados", [])}
    passos = max(abs(alvo[0] - origem[0]), abs(alvo[1] - origem[1]))
    atravessados = []
    for i in range(1, passos):
        p = (round(origem[0] + (alvo[0] - origem[0]) * i / passos), round(origem[1] + (alvo[1] - origem[1]) * i / passos))
        if p in bloqueados:
            atravessados.append(p)
    return {"resultado": "bloqueada" if atravessados else "livre", "bloqueadores": atravessados}


def resolver_ataque_tatico(fatos: dict) -> dict[str, Any]:
    alcance = resolver_alcance(fatos["distancia"], alcance=fatos["alcance"], alcance_maximo=fatos.get("alcance_maximo"), ataque_a_distancia=bool(fatos.get("ataque_a_distancia", False)), alcance_estendido=bool(fatos.get("alcance_estendido", False)))
    if alcance["resultado"] == "fora_de_alcance":
        return {"resultado": "bloqueado", "motivo": "fora_de_alcance"}
    linha = resolver_linha_grade(fatos) if fatos.get("origem") is not None and fatos.get("alvo") is not None else {"resultado": "livre"}
    if linha["resultado"] == "bloqueada":
        return {"resultado": "bloqueado", "motivo": "linha_de_efeito", "bloqueadores": linha["bloqueadores"]}
    cobertura = resolver_cobertura(fatos.get("cobertura", "nenhuma"))
    if cobertura["resultado"] == "bloqueado":
        return {"resultado": "bloqueado", "motivo": "cobertura_total"}
    flanco = resolver_flanco({"atacante": fatos["atacante"], "alvo": fatos["alvo_posicao"], "aliados": fatos.get("aliados", [])}) if fatos.get("atacante") is not None and fatos.get("alvo_posicao") is not None else {"vantagem": False}
    vantagem = bool(fatos.get("vantagem", False)) or flanco["vantagem"]
    desvantagem = bool(alcance.get("desvantagem_por_alcance", False)) or bool(fatos.get("desvantagem", False))
    estado = "normal" if vantagem == desvantagem else "vantagem" if vantagem else "desvantagem"
    return {"resultado": "permitido", "estado_jogada": estado, "vantagem": vantagem, "desvantagem": desvantagem, "bonus_ca_por_cobertura": cobertura["bonus_ca"], "flanqueando": flanco["vantagem"], "distancia": fatos["distancia"]}


def resolver_terreno(fatos: dict) -> dict[str, Any]:
    distancia = int(fatos.get("distancia", 0))
    custo = distancia * (2 if fatos.get("terreno_dificil", False) else 1)
    if fatos.get("rastejando", False):
        custo *= 2
    return {"resultado": "permitido" if custo <= int(fatos.get("movimento_disponivel", custo)) else "bloqueado", "custo": custo, "movimento_restante": max(0, int(fatos.get("movimento_disponivel", custo)) - custo)}
