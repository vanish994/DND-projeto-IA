"""Dependências FastAPI: identidade do jogador, repositório, MJ e limite de taxa.

Os providers ficam registrados uma única vez e são injetados nas rotas com
``Depends``; a suíte de testes substitui instâncias via ``dependency_overrides``.
"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from backend.config import JOGADOR_ANONIMO, PADRAO_ID
from backend.limite_taxa import limitador_padrao
from backend.persistencia import RepositorioCampanhas
from integrations.deepseek_mj import DeepSeekMJ

_mj: DeepSeekMJ | None = None
_repositorio: RepositorioCampanhas | None = None


def obter_mj() -> DeepSeekMJ:
    global _mj
    if _mj is None:
        try:
            _mj = DeepSeekMJ()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _mj


def obter_repositorio() -> RepositorioCampanhas:
    global _repositorio
    if _repositorio is None:
        _repositorio = RepositorioCampanhas()
    return _repositorio


def obter_jogador(
    x_jogador_id: str | None = Header(default=None, pattern=PADRAO_ID),
) -> str:
    return x_jogador_id or JOGADOR_ANONIMO


# Limite de taxa das rotas que chamam o MJ (cada chamada custa uma requisição ao provedor).
_limitador_mj = limitador_padrao()


def limitar_chamadas_mj(jogador: str = Depends(obter_jogador)) -> None:
    _limitador_mj.verificar(jogador)
