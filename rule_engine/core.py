"""Primitivas compartilhadas pelas regras do Livro do Jogador 2024."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Iterable


@dataclass(frozen=True)
class ResultadoD20:
    """Resultado auditável da seleção de dados e do total do teste."""

    dado_selecionado: int
    dados_rolados: tuple[int, ...]
    vantagem: bool
    desvantagem: bool
    modificador: int
    total: int
    sucesso: bool | None = None


def modificador_atributo(valor: int) -> int:
    """Calcula o modificador de atributo pela regra do Livro do Jogador."""
    if not 1 <= int(valor) <= 30:
        raise ValueError("O valor de atributo deve estar entre 1 e 30")
    return floor((int(valor) - 10) / 2)


def bonus_proficiencia(nivel_ou_nd: int) -> int:
    """Calcula o Bônus de Proficiência de personagens ou monstros."""
    nivel_ou_nd = int(nivel_ou_nd)
    if not 1 <= nivel_ou_nd <= 30:
        raise ValueError("O nível ou ND deve estar entre 1 e 30")
    return 2 + (nivel_ou_nd - 1) // 4


def selecionar_d20(
    dados: Iterable[int], *, vantagem: bool = False, desvantagem: bool = False
) -> tuple[int, tuple[int, ...], bool, bool]:
    """Seleciona o maior/menor d20, cancelando vantagem e desvantagem."""
    dados = tuple(int(dado) for dado in dados)
    if any(dado < 1 or dado > 20 for dado in dados):
        raise ValueError("Cada resultado de d20 deve estar entre 1 e 20")
    if vantagem and desvantagem:
        vantagem = desvantagem = False
    if vantagem or desvantagem:
        if len(dados) != 2:
            raise ValueError("Vantagem ou desvantagem exigem exatamente dois d20")
        selecionado = max(dados) if vantagem else min(dados)
    else:
        if len(dados) != 1:
            raise ValueError("Sem vantagem ou desvantagem, use exatamente um d20")
        selecionado = dados[0]
    return selecionado, dados, vantagem, desvantagem


def resolver_teste_d20(
    dados: Iterable[int],
    *,
    modificador: int = 0,
    cd: int | None = None,
    vantagem: bool = False,
    desvantagem: bool = False,
) -> ResultadoD20:
    """Resolve a rolagem comum e compara com uma CD quando fornecida."""
    selecionado, rolados, vantagem, desvantagem = selecionar_d20(dados, vantagem=vantagem, desvantagem=desvantagem)
    total = selecionado + int(modificador)
    return ResultadoD20(
        dado_selecionado=selecionado,
        dados_rolados=rolados,
        vantagem=vantagem,
        desvantagem=desvantagem,
        modificador=int(modificador),
        total=total,
        sucesso=None if cd is None else total >= int(cd),
    )
