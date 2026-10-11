"""Persistência de campanhas e mensagens do MJ.

Usa SQLAlchemy Core para funcionar com SQLite (desenvolvimento) e Postgres
(produção, via DATABASE_URL). Cada campanha pertence a um jogador_id gerado
no navegador até que exista login.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine

TITULO_PADRAO = "Campanha sem título"

metadata = MetaData()

campanhas = Table(
    "campanhas",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("jogador_id", String(128), nullable=False, index=True),
    Column("titulo", String(120), nullable=False),
    Column("criada_em", DateTime(timezone=True), nullable=False),
    Column("atualizada_em", DateTime(timezone=True), nullable=False),
)

mensagens = Table(
    "mensagens",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("campanha_id", String(64), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("papel", String(16), nullable=False),
    Column("conteudo", Text, nullable=False),
    Column("criada_em", DateTime(timezone=True), nullable=False),
)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: datetime) -> str:
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.isoformat()


def normalizar_url_banco(url: str) -> str:
    """Converte URLs do Render (postgres://) para o driver psycopg 3."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def url_banco_padrao() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return normalizar_url_banco(url)
    caminho = Path(__file__).resolve().parents[1] / "data" / "mj.sqlite3"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{caminho}"


class RepositorioCampanhas:
    def __init__(self, url: str | None = None, *, engine: Engine | None = None):
        if engine is None:
            url = normalizar_url_banco(url) if url else url_banco_padrao()
            kwargs: dict[str, Any] = {"pool_pre_ping": True}
            if url.startswith("sqlite"):
                kwargs["connect_args"] = {"check_same_thread": False}
            engine = create_engine(url, **kwargs)
        self.engine = engine
        metadata.create_all(self.engine)

    def _resumo(self, linha: Any, ultima: str | None, total: int) -> dict[str, Any]:
        return {
            "id": linha.id,
            "titulo": linha.titulo,
            "criada_em": _iso(linha.criada_em),
            "atualizada_em": _iso(linha.atualizada_em),
            "ultima_mensagem": ultima,
            "total_mensagens": total,
        }

    def criar(self, jogador_id: str, titulo: str | None = None, campanha_id: str | None = None) -> dict[str, Any]:
        agora = _agora()
        registro = {
            "id": campanha_id or f"campanha-{uuid.uuid4().hex[:12]}",
            "jogador_id": jogador_id,
            "titulo": (titulo or "").strip() or TITULO_PADRAO,
            "criada_em": agora,
            "atualizada_em": agora,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(campanhas).values(**registro))
        return self.obter(jogador_id, registro["id"])  # type: ignore[return-value]

    def _linha(self, conn: Any, jogador_id: str, campanha_id: str) -> Any:
        return conn.execute(
            select(campanhas).where(campanhas.c.id == campanha_id, campanhas.c.jogador_id == jogador_id)
        ).first()

    def obter(self, jogador_id: str, campanha_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            linha = self._linha(conn, jogador_id, campanha_id)
            if linha is None:
                return None
            total = conn.execute(
                select(func.count()).select_from(mensagens).where(mensagens.c.campanha_id == campanha_id)
            ).scalar_one()
            ultima = conn.execute(
                select(mensagens.c.conteudo)
                .where(mensagens.c.campanha_id == campanha_id)
                .order_by(mensagens.c.id.desc())
                .limit(1)
            ).scalar()
        return self._resumo(linha, ultima, total)

    def existe_em_outro_jogador(self, jogador_id: str, campanha_id: str) -> bool:
        with self.engine.connect() as conn:
            dono = conn.execute(select(campanhas.c.jogador_id).where(campanhas.c.id == campanha_id)).scalar()
        return dono is not None and dono != jogador_id

    def listar(self, jogador_id: str, limite: int = 50) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            linhas = conn.execute(
                select(campanhas)
                .where(campanhas.c.jogador_id == jogador_id)
                .order_by(campanhas.c.atualizada_em.desc())
                .limit(limite)
            ).all()
            resultado = []
            for linha in linhas:
                total = conn.execute(
                    select(func.count()).select_from(mensagens).where(mensagens.c.campanha_id == linha.id)
                ).scalar_one()
                ultima = conn.execute(
                    select(mensagens.c.conteudo)
                    .where(mensagens.c.campanha_id == linha.id)
                    .order_by(mensagens.c.id.desc())
                    .limit(1)
                ).scalar()
                resultado.append(self._resumo(linha, ultima, total))
        return resultado

    def renomear(self, jogador_id: str, campanha_id: str, titulo: str) -> dict[str, Any] | None:
        with self.engine.begin() as conn:
            resultado = conn.execute(
                update(campanhas)
                .where(campanhas.c.id == campanha_id, campanhas.c.jogador_id == jogador_id)
                .values(titulo=titulo.strip() or TITULO_PADRAO, atualizada_em=_agora())
            )
        if resultado.rowcount == 0:
            return None
        return self.obter(jogador_id, campanha_id)

    def apagar(self, jogador_id: str, campanha_id: str) -> bool:
        with self.engine.begin() as conn:
            if self._linha(conn, jogador_id, campanha_id) is None:
                return False
            conn.execute(delete(mensagens).where(mensagens.c.campanha_id == campanha_id))
            conn.execute(delete(campanhas).where(campanhas.c.id == campanha_id))
        return True

    def mensagens(self, jogador_id: str, campanha_id: str, limite: int | None = None) -> list[dict[str, Any]] | None:
        with self.engine.connect() as conn:
            if self._linha(conn, jogador_id, campanha_id) is None:
                return None
            consulta = (
                select(mensagens)
                .where(mensagens.c.campanha_id == campanha_id)
                .order_by(mensagens.c.id.desc())
            )
            if limite is not None:
                consulta = consulta.limit(limite)
            linhas = list(reversed(conn.execute(consulta).all()))
        return [
            {"id": l.id, "papel": l.papel, "conteudo": l.conteudo, "criada_em": _iso(l.criada_em)}
            for l in linhas
        ]

    def historico_llm(self, jogador_id: str, campanha_id: str, limite: int) -> list[dict[str, str]]:
        registros = self.mensagens(jogador_id, campanha_id, limite) or []
        return [{"role": r["papel"], "content": r["conteudo"]} for r in registros]

    def registrar_troca(self, jogador_id: str, campanha_id: str, pergunta: str, resposta: str) -> None:
        agora = _agora()
        with self.engine.begin() as conn:
            conn.execute(
                insert(mensagens),
                [
                    {"campanha_id": campanha_id, "papel": "user", "conteudo": pergunta, "criada_em": agora},
                    {"campanha_id": campanha_id, "papel": "assistant", "conteudo": resposta, "criada_em": agora},
                ],
            )
            conn.execute(
                update(campanhas)
                .where(campanhas.c.id == campanha_id, campanhas.c.jogador_id == jogador_id)
                .values(atualizada_em=agora)
            )
