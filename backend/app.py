"""Backend HTTP do MJ DeepSeek.

A chave do provedor permanece no servidor. O cliente envia apenas mensagens;
o DeepSeek conduz a conversa e usa o Rule Engine por ferramentas. Campanhas e
mensagens ficam persistidas em banco (SQLite local ou Postgres via DATABASE_URL).

Este módulo é o composition root: cria a aplicação, registra as rotas e expõe
as dependências de injeção usadas por testes e clientes (``obter_mj``,
``obter_repositorio``, ``obter_jogador``, ``limitar_chamadas_mj``).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Superfície pública de injeção de dependências do app (usada pela suíte para
# injetar dublês via ``dependency_overrides``).
from backend.dependencies import (  # noqa: F401
    Recursos,
    limitar_chamadas_mj,
    obter_jogador,
    obter_mj,
    obter_repositorio,
)
from backend.erros import registrar_tratadores_de_erro
from backend.routes import campanhas, catalogo, personagens, sistema

app = FastAPI(
    title="D&D Projeto IA — MJ",
    version="1.1.0",
    description="MJ DeepSeek com Rule Engine determinístico para mecânicas oficiais.",
)

# Container de recursos de processo (MJ e repositório), um por instância de app.
app.state.recursos = Recursos()

# Mapeamento único exceção de domínio → HTTP (backend/erros.py).
registrar_tratadores_de_erro(app)

app.include_router(sistema.router)
app.include_router(campanhas.router)
app.include_router(catalogo.router)
app.include_router(personagens.router)

_frontend = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/", StaticFiles(directory=_frontend, html=True), name="interface")
