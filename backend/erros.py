"""Exceções de domínio e mapeamento HTTP em um único lugar.

Os serviços levantam exceções de domínio (sem conhecer HTTP); ``registrar_tratadores_de_erro``
instala o único ponto que as converte em resposta HTTP — com o mesmo formato
``{"detail": ...}`` do FastAPI — para que status e mensagens sejam previsíveis.

O limite de taxa continua levantando ``HTTPException`` (429 com header
``Retry-After``): é infraestrutura de proteção da rota, não regra de domínio.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ErroDominio(Exception):
    """Falha de domínio com representação HTTP estável."""

    status_code: int = 500

    def __init__(self, detalhe: Any):
        self.detalhe = detalhe
        super().__init__(detalhe if isinstance(detalhe, str) else str(detalhe))


class ErroDeValidacao(ErroDominio):
    """Entrada ou estado regrado inválido (422)."""

    status_code = 422


class NaoEncontrado(ErroDominio):
    """Recurso inexistente para o jogador (404)."""

    status_code = 404


class ConflitoDeOperacao(ErroDominio):
    """Estado da campanha mudou ou operação incompatível (409)."""

    status_code = 409


class ErroDeProvedor(ErroDominio):
    """Falha temporária do provedor de IA (502)."""

    status_code = 502


class ServicoIndisponivel(ErroDominio):
    """Configuração/provedor indisponível no startup (503)."""

    status_code = 503


def resposta_de_erro(exc: ErroDominio) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detalhe})


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    """Registra o mapeamento único exceção de domínio → HTTP."""

    def tratar(request: Request, exc: ErroDominio) -> JSONResponse:
        return resposta_de_erro(exc)

    app.add_exception_handler(ErroDominio, tratar)
