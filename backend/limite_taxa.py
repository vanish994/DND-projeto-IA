"""Limite de taxa por jogador para os endpoints que chamam o MJ (provedor pago).

Janela deslizante em memória, por processo. Configurável por ambiente:
- MJ_LIMITE_REQUISICOES (padrão 30): mensagens aceitas por janela.
- MJ_LIMITE_JANELA_SEGUNDOS (padrão 60): tamanho da janela.
Valores inválidos voltam ao padrão. Quando o limite é atingido, responde 429 com Retry-After.
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections import deque
from typing import Callable

from fastapi import HTTPException

PADRAO_REQUISICOES = 30
PADRAO_JANELA_SEGUNDOS = 60.0
_LIMITE_SWEEP = 1000


class LimitadorTaxa:
    def __init__(
        self,
        maximo: int = PADRAO_REQUISICOES,
        janela_segundos: float = PADRAO_JANELA_SEGUNDOS,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        if maximo < 1:
            raise ValueError("O limite deve ser de pelo menos 1 requisição")
        if janela_segundos <= 0:
            raise ValueError("A janela deve ser positiva")
        self._maximo = int(maximo)
        self._janela = float(janela_segundos)
        self._relogio = relogio
        self._eventos: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def verificar(self, chave: str) -> None:
        agora = self._relogio()
        with self._lock:
            if len(self._eventos) > _LIMITE_SWEEP:
                self._varrer(agora)
            fila = self._eventos.setdefault(chave, deque())
            self._expirar(fila, agora)
            if len(fila) >= self._maximo:
                espera = max(1, math.ceil(self._janela - (agora - fila[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Muitas mensagens em pouco tempo. Aguarde {espera} segundos e tente de novo.",
                    headers={"Retry-After": str(espera)},
                )
            fila.append(agora)

    def reiniciar(self) -> None:
        with self._lock:
            self._eventos.clear()

    def _expirar(self, fila: deque[float], agora: float) -> None:
        while fila and agora - fila[0] >= self._janela:
            fila.popleft()

    def _varrer(self, agora: float) -> None:
        for chave in list(self._eventos):
            fila = self._eventos[chave]
            self._expirar(fila, agora)
            if not fila:
                del self._eventos[chave]


def _inteiro_de_ambiente(nome: str, padrao: int) -> int:
    try:
        valor = int(os.environ.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao
    return valor if valor >= 1 else padrao


def _numero_de_ambiente(nome: str, padrao: float) -> float:
    try:
        valor = float(os.environ.get(nome, padrao))
    except (TypeError, ValueError):
        return padrao
    return valor if valor > 0 else padrao


def limitador_padrao() -> LimitadorTaxa:
    return LimitadorTaxa(
        maximo=_inteiro_de_ambiente("MJ_LIMITE_REQUISICOES", PADRAO_REQUISICOES),
        janela_segundos=_numero_de_ambiente("MJ_LIMITE_JANELA_SEGUNDOS", PADRAO_JANELA_SEGUNDOS),
    )
