"""Dependências FastAPI: identidade do jogador, repositório, MJ e limite de taxa.

Os recursos de processo (MJ e repositório) vivem em ``app.state.recursos`` — um
container por instância de app — e nunca em variáveis de módulo: assim requests
concorrentes e testes isolados não compartilham estado mutável. Os providers
``obter_mj`` e ``obter_repositorio`` fazem lazy init e podem ser substituídos em
testes via ``app.dependency_overrides``.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, Request

from backend.config import JOGADOR_ANONIMO, PADRAO_ID
from backend.erros import ServicoIndisponivel
from backend.limite_taxa import limitador_padrao
from backend.persistencia import RepositorioCampanhas
from integrations.deepseek_mj import DeepSeekMJ


@dataclass
class Recursos:
    """Recursos de processo criados no máximo uma vez por instância de app."""

    mj: DeepSeekMJ | None = None
    repositorio: RepositorioCampanhas | None = None


def obter_recursos(request: Request) -> Recursos:
    return request.app.state.recursos


def obter_mj(recursos: Recursos = Depends(obter_recursos)) -> DeepSeekMJ:
    if recursos.mj is None:
        try:
            recursos.mj = DeepSeekMJ()
        except RuntimeError as exc:
            raise ServicoIndisponivel(str(exc)) from exc
    return recursos.mj


def obter_repositorio(recursos: Recursos = Depends(obter_recursos)) -> RepositorioCampanhas:
    if recursos.repositorio is None:
        recursos.repositorio = RepositorioCampanhas()
    return recursos.repositorio


def obter_jogador(
    x_jogador_id: str | None = Header(default=None, pattern=PADRAO_ID),
) -> str:
    return x_jogador_id or JOGADOR_ANONIMO


# Limite de taxa das rotas que chamam o MJ (cada chamada custa uma requisição ao
# provedor). É estado de processo por desenho — memória por processo, por jogador.
_limitador_mj = limitador_padrao()


def limitar_chamadas_mj(jogador: str = Depends(obter_jogador)) -> None:
    _limitador_mj.verificar(jogador)
