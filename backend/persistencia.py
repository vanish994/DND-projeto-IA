"""Persistência de campanhas e mensagens do MJ.

Usa SQLAlchemy Core para funcionar com SQLite (desenvolvimento) e Postgres
(produção, via DATABASE_URL). Cada campanha pertence a um jogador_id gerado
no navegador até que exista login.
"""

from __future__ import annotations

import json
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
    case,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

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
    # Rolagens do Rule Engine guardadas como JSON para a interface reexibir o dado.
    Column("rolagens", Text, nullable=True),
    Column("criada_em", DateTime(timezone=True), nullable=False),
)


personagens = Table(
    "personagens",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("campanha_id", String(64), ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("entrada", Text, nullable=False),
    Column("ficha", Text, nullable=False),
    Column("pv_atual", Integer, nullable=False),
    Column("criado_em", DateTime(timezone=True), nullable=False),
    Column("atualizado_em", DateTime(timezone=True), nullable=False),
)

fichas_salvas = Table(
    "fichas_salvas",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("jogador_id", String(128), nullable=False, index=True),
    Column("nome", String(80), nullable=False),
    Column("entrada", Text, nullable=False),
    Column("ficha", Text, nullable=False),
    Column("criado_em", DateTime(timezone=True), nullable=False),
    Column("atualizado_em", DateTime(timezone=True), nullable=False),
)

# Chave única por campanha. Só existe registro para uma operação confirmada;
# resposta, rolagens, fichas e mensagens participam da mesma transação.
operacoes_mj = Table(
    "operacoes_mj",
    metadata,
    Column("campanha_id", String(64), ForeignKey("campanhas.id", ondelete="CASCADE"), primary_key=True),
    Column("operacao_id", String(64), primary_key=True),
    Column("pergunta", Text, nullable=False),
    Column("resposta", Text, nullable=False),
    Column("rolagens", Text, nullable=False),
    Column("criada_em", DateTime(timezone=True), nullable=False),
)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(valor: datetime) -> str:
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.isoformat()


def _rolagens_da_linha(valor: str | None) -> list[dict[str, Any]]:
    """Lê as rolagens salvas em JSON, ignorando registros corrompidos ou vazios."""
    if not valor:
        return []
    try:
        dados = json.loads(valor)
    except (TypeError, ValueError):
        return []
    return [item for item in dados if isinstance(item, dict)] if isinstance(dados, list) else []


def normalizar_url_banco(url: str) -> str:
    """Converte URLs do Render (postgres://) para o driver psycopg 3."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def url_banco_padrao() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return normalizar_url_banco(url)
    caminho = Path(__file__).resolve().parents[1] / "data" / "mj.sqlite3"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{caminho}"


class ConflitoEstadoCampanha(RuntimeError):
    """A resposta foi calculada sobre uma ficha que já mudou ou foi removida."""


class OperacaoIncompativel(ConflitoEstadoCampanha):
    """Uma chave de operação não pode ser reutilizada para outra mensagem."""


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
        self._garantir_coluna_rolagens()
        self._remover_tabela_mapa_tatico()

    def _garantir_coluna_rolagens(self) -> None:
        """Adiciona ``mensagens.rolagens`` em bancos criados antes da animação de dados.

        ``metadata.create_all`` não altera tabelas existentes; sem isso, campanhas
        antigas em SQLite ou Postgres quebrariam ao gravar uma rolagem.
        """
        inspetor = inspect(self.engine)
        if "mensagens" not in inspetor.get_table_names():
            return
        colunas = {coluna["name"] for coluna in inspetor.get_columns("mensagens")}
        if "rolagens" in colunas:
            return
        with self.engine.begin() as conn:
            conn.execute(text("ALTER TABLE mensagens ADD COLUMN rolagens TEXT"))

    def _remover_tabela_mapa_tatico(self) -> None:
        """Apaga ``encontros_taticos`` (estado do mapa tático, recurso removido).

        Idempotente: sem efeito quando a tabela não existe. Os estados salvos
        dos mapas são descartados junto com ela.
        """
        if "encontros_taticos" not in inspect(self.engine).get_table_names():
            return
        with self.engine.begin() as conn:
            conn.execute(text("DROP TABLE encontros_taticos"))

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
            conn.execute(delete(operacoes_mj).where(operacoes_mj.c.campanha_id == campanha_id))
            conn.execute(delete(mensagens).where(mensagens.c.campanha_id == campanha_id))
            conn.execute(delete(personagens).where(personagens.c.campanha_id == campanha_id))
            conn.execute(delete(campanhas).where(campanhas.c.id == campanha_id))
        return True

    def mensagens(self, jogador_id: str, campanha_id: str, limite: int | None = None) -> list[dict[str, Any]] | None:
        with self.engine.connect() as conn:
            if self._linha(conn, jogador_id, campanha_id) is None:
                return None
            consulta = select(mensagens).where(mensagens.c.campanha_id == campanha_id).order_by(mensagens.c.id.desc())
            if limite is not None:
                consulta = consulta.limit(limite)
            linhas = list(reversed(conn.execute(consulta).all()))
        return [
            {
                "id": linha.id,
                "papel": linha.papel,
                "conteudo": linha.conteudo,
                "rolagens": _rolagens_da_linha(linha.rolagens),
                "criada_em": _iso(linha.criada_em),
            }
            for linha in linhas
        ]

    def historico_llm(self, jogador_id: str, campanha_id: str, limite: int) -> list[dict[str, str]]:
        registros = self.mensagens(jogador_id, campanha_id, limite) or []
        return [{"role": r["papel"], "content": r["conteudo"]} for r in registros]

    def obter_operacao(
        self, jogador_id: str, campanha_id: str, operacao_id: str, pergunta: str
    ) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            if not self._da_campanha(conn, jogador_id, campanha_id):
                raise ConflitoEstadoCampanha("Campanha indisponível")
            linha = conn.execute(
                select(operacoes_mj).where(
                    operacoes_mj.c.campanha_id == campanha_id,
                    operacoes_mj.c.operacao_id == operacao_id,
                )
            ).first()
        if linha is None:
            return None
        if linha.pergunta != pergunta:
            raise OperacaoIncompativel(
                "Identificador já utilizado por outra mensagem. Use um novo envio para outra ação."
            )
        return {"resposta": linha.resposta, "rolagens": _rolagens_da_linha(linha.rolagens)}

    def registrar_troca(
        self,
        jogador_id: str,
        campanha_id: str,
        pergunta: str,
        resposta: str,
        rolagens: list[dict[str, Any]] | None = None,
        *,
        atualizacoes_ficha: dict[str, dict[str, Any]] | None = None,
        fichas_esperadas: dict[str, dict[str, Any]] | None = None,
        operacao_id: str | None = None,
    ) -> dict[str, Any]:
        """Confirma fichas e mensagens juntas, sem transação durante a chamada da IA.

        O snapshot/compare-and-swap impede uma resposta atrasada de sobrescrever
        recursos alterados por outro pedido. Qualquer falha desfaz todo o lote.
        """
        if operacao_id:
            anterior = self.obter_operacao(jogador_id, campanha_id, operacao_id, pergunta)
            if anterior is not None:
                return anterior
        agora = _agora()
        rolagens_json = json.dumps(rolagens, ensure_ascii=False) if rolagens else None
        try:
            with self.engine.begin() as conn:
                if not self._da_campanha(conn, jogador_id, campanha_id):
                    raise ConflitoEstadoCampanha("Campanha indisponível")
                if operacao_id:
                    # Inserir antes das fichas: disputas pela mesma chave são decididas
                    # pela restrição única, antes de qualquer segundo gasto.
                    conn.execute(
                        insert(operacoes_mj).values(
                            campanha_id=campanha_id,
                            operacao_id=operacao_id,
                            pergunta=pergunta,
                            resposta=resposta,
                            rolagens=json.dumps(rolagens or [], ensure_ascii=False),
                            criada_em=agora,
                        )
                    )
                for personagem_id, ficha in sorted((atualizacoes_ficha or {}).items()):
                    esperado = (fichas_esperadas or {}).get(personagem_id)
                    linha = conn.execute(
                        select(personagens).where(
                            personagens.c.id == personagem_id,
                            personagens.c.campanha_id == campanha_id,
                        )
                    ).first()
                    if (
                        esperado is None
                        or linha is None
                        or _iso(linha.atualizado_em) != esperado["atualizado_em"]
                        or linha.pv_atual != esperado["pv_atual"]
                    ):
                        raise ConflitoEstadoCampanha("A ficha mudou durante a resposta")
                    atualizado = conn.execute(
                        update(personagens)
                        .where(
                            personagens.c.id == personagem_id,
                            personagens.c.campanha_id == campanha_id,
                            personagens.c.atualizado_em == linha.atualizado_em,
                            personagens.c.ficha == linha.ficha,
                            personagens.c.pv_atual == linha.pv_atual,
                        )
                        .values(ficha=json.dumps(ficha, ensure_ascii=False), atualizado_em=agora)
                    )
                    if atualizado.rowcount != 1:
                        raise ConflitoEstadoCampanha("A ficha mudou durante a confirmação")
                conn.execute(
                    insert(mensagens),
                    [
                        {
                            "campanha_id": campanha_id,
                            "papel": "user",
                            "conteudo": pergunta,
                            "rolagens": None,
                            "criada_em": agora,
                        },
                        {
                            "campanha_id": campanha_id,
                            "papel": "assistant",
                            "conteudo": resposta,
                            "rolagens": rolagens_json,
                            "criada_em": agora,
                        },
                    ],
                )
                conn.execute(
                    update(campanhas)
                    .where(campanhas.c.id == campanha_id, campanhas.c.jogador_id == jogador_id)
                    .values(atualizada_em=agora)
                )

        except IntegrityError:
            # Em Postgres/SQLite a transação perdedora já foi revertida aqui.
            if operacao_id:
                anterior = self.obter_operacao(jogador_id, campanha_id, operacao_id, pergunta)
                if anterior is not None:
                    return anterior
            raise
        return {"resposta": resposta, "rolagens": rolagens or []}

    def _ficha_salva(self, linha: Any) -> dict[str, Any]:
        entrada = json.loads(linha.entrada)
        ficha = json.loads(linha.ficha)
        return {
            "id": linha.id,
            "jogador_id": linha.jogador_id,
            "nome": linha.nome,
            **ficha,
            "entrada": entrada,
            "criado_em": _iso(linha.criado_em),
            "atualizado_em": _iso(linha.atualizado_em),
            "pv_atual": int(ficha.get("pv_maximo", 1)),
        }

    def criar_ficha_salva(self, jogador_id: str, entrada: dict[str, Any], ficha: dict[str, Any]) -> dict[str, Any]:
        agora = _agora()
        registro = {
            "id": f"ficha-{uuid.uuid4().hex[:12]}",
            "jogador_id": jogador_id,
            "nome": str(ficha.get("nome") or entrada.get("nome") or "Personagem").strip(),
            "entrada": json.dumps(entrada, ensure_ascii=False),
            "ficha": json.dumps(ficha, ensure_ascii=False),
            "criado_em": agora,
            "atualizado_em": agora,
        }
        with self.engine.begin() as conn:
            conn.execute(insert(fichas_salvas).values(**registro))
        return self.obter_ficha_salva(jogador_id, registro["id"])  # type: ignore[return-value]

    def listar_fichas_salvas(self, jogador_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as conn:
            linhas = conn.execute(
                select(fichas_salvas)
                .where(fichas_salvas.c.jogador_id == jogador_id)
                .order_by(fichas_salvas.c.atualizado_em.desc(), fichas_salvas.c.id)
            ).all()
        return [self._ficha_salva(linha) for linha in linhas]

    def obter_ficha_salva(self, jogador_id: str, ficha_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            linha = conn.execute(
                select(fichas_salvas).where(
                    fichas_salvas.c.id == ficha_id,
                    fichas_salvas.c.jogador_id == jogador_id,
                )
            ).first()
        return self._ficha_salva(linha) if linha else None

    def apagar_ficha_salva(self, jogador_id: str, ficha_id: str) -> bool:
        with self.engine.begin() as conn:
            resultado = conn.execute(
                delete(fichas_salvas).where(
                    fichas_salvas.c.id == ficha_id,
                    fichas_salvas.c.jogador_id == jogador_id,
                )
            )
        return resultado.rowcount == 1

    def vincular_ficha_salva(self, jogador_id: str, campanha_id: str, ficha_id: str) -> dict[str, Any] | None:
        """Copia uma ficha validada da biblioteca para o grupo de uma campanha."""
        agora = _agora()
        with self.engine.begin() as conn:
            if not self._da_campanha(conn, jogador_id, campanha_id):
                return None
            salva = conn.execute(
                select(fichas_salvas).where(
                    fichas_salvas.c.id == ficha_id,
                    fichas_salvas.c.jogador_id == jogador_id,
                )
            ).first()
            if salva is None:
                return None
            ficha = json.loads(salva.ficha)
            registro = {
                "id": f"personagem-{uuid.uuid4().hex[:12]}",
                "campanha_id": campanha_id,
                "entrada": salva.entrada,
                "ficha": salva.ficha,
                "pv_atual": int(ficha["pv_maximo"]),
                "criado_em": agora,
                "atualizado_em": agora,
            }
            conn.execute(insert(personagens).values(**registro))
        return self.obter_personagem(jogador_id, campanha_id, registro["id"])

    def _personagem(self, linha: Any) -> dict[str, Any]:
        ficha = json.loads(linha.ficha)
        return {
            "id": linha.id,
            "campanha_id": linha.campanha_id,
            **ficha,
            "pv_atual": linha.pv_atual,
            "entrada": json.loads(linha.entrada),
            "criado_em": _iso(linha.criado_em),
            "atualizado_em": _iso(linha.atualizado_em),
        }

    def _da_campanha(self, conn: Any, jogador_id: str, campanha_id: str) -> bool:
        return self._linha(conn, jogador_id, campanha_id) is not None

    def criar_personagem(
        self, jogador_id: str, campanha_id: str, entrada: dict[str, Any], ficha: dict[str, Any]
    ) -> dict[str, Any] | None:
        agora = _agora()
        registro = {
            "id": f"personagem-{uuid.uuid4().hex[:12]}",
            "campanha_id": campanha_id,
            "entrada": json.dumps(entrada, ensure_ascii=False),
            "ficha": json.dumps(ficha, ensure_ascii=False),
            "pv_atual": ficha["pv_maximo"],
            "criado_em": agora,
            "atualizado_em": agora,
        }
        with self.engine.begin() as conn:
            if not self._da_campanha(conn, jogador_id, campanha_id):
                return None
            conn.execute(insert(personagens).values(**registro))
        return self.obter_personagem(jogador_id, campanha_id, registro["id"])

    def listar_personagens(self, jogador_id: str, campanha_id: str) -> list[dict[str, Any]] | None:
        with self.engine.connect() as conn:
            if not self._da_campanha(conn, jogador_id, campanha_id):
                return None
            linhas = conn.execute(
                select(personagens)
                .where(personagens.c.campanha_id == campanha_id)
                .order_by(personagens.c.criado_em, personagens.c.id)
            ).all()
        return [self._personagem(linha) for linha in linhas]

    def obter_personagem(self, jogador_id: str, campanha_id: str, personagem_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            if not self._da_campanha(conn, jogador_id, campanha_id):
                return None
            linha = conn.execute(
                select(personagens).where(personagens.c.id == personagem_id, personagens.c.campanha_id == campanha_id)
            ).first()
        return self._personagem(linha) if linha else None

    def atualizar_personagem(
        self,
        jogador_id: str,
        campanha_id: str,
        personagem_id: str,
        *,
        entrada: dict[str, Any] | None = None,
        ficha: dict[str, Any] | None = None,
        pv_atual: int | None = None,
    ) -> dict[str, Any] | None:
        atual = self.obter_personagem(jogador_id, campanha_id, personagem_id)
        if atual is None:
            return None
        valores: dict[str, Any] = {"atualizado_em": _agora()}
        pv_maximo = atual["pv_maximo"]
        if entrada is not None and ficha is not None:
            valores["entrada"] = json.dumps(entrada, ensure_ascii=False)
            valores["ficha"] = json.dumps(ficha, ensure_ascii=False)
            pv_maximo = ficha["pv_maximo"]
            valores["pv_atual"] = min(atual["pv_atual"], pv_maximo)
        if pv_atual is not None:
            valores["pv_atual"] = max(0, min(pv_atual, pv_maximo))
        with self.engine.begin() as conn:
            conn.execute(update(personagens).where(personagens.c.id == personagem_id).values(**valores))
        return self.obter_personagem(jogador_id, campanha_id, personagem_id)

    def atualizar_dados_ficha(
        self, jogador_id: str, campanha_id: str, personagem_id: str, ficha: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Atualiza escolhas complementares sem alterar PV ou dados de criação."""
        if self.obter_personagem(jogador_id, campanha_id, personagem_id) is None:
            return None
        with self.engine.begin() as conn:
            conn.execute(
                update(personagens)
                .where(personagens.c.id == personagem_id, personagens.c.campanha_id == campanha_id)
                .values(ficha=json.dumps(ficha, ensure_ascii=False), atualizado_em=_agora())
            )
        return self.obter_personagem(jogador_id, campanha_id, personagem_id)

    def ajustar_pv_personagem(
        self, jogador_id: str, campanha_id: str, personagem_id: str, delta: int
    ) -> dict[str, Any] | None:
        """Aplica dano/cura como operação atômica, sem valores absolutos obsoletos."""
        atual = self.obter_personagem(jogador_id, campanha_id, personagem_id)
        if atual is None:
            return None
        maximo = int(atual["pv_maximo"])
        novo = personagens.c.pv_atual + int(delta)
        limitado = case((novo < 0, 0), (novo > maximo, maximo), else_=novo)
        with self.engine.begin() as conn:
            resultado = conn.execute(
                update(personagens)
                .where(personagens.c.id == personagem_id, personagens.c.campanha_id == campanha_id)
                .values(pv_atual=limitado, atualizado_em=_agora())
            )
            if resultado.rowcount == 0:
                return None
        return self.obter_personagem(jogador_id, campanha_id, personagem_id)

    def apagar_personagem(self, jogador_id: str, campanha_id: str, personagem_id: str) -> bool:
        if self.obter_personagem(jogador_id, campanha_id, personagem_id) is None:
            return False
        with self.engine.begin() as conn:
            conn.execute(delete(personagens).where(personagens.c.id == personagem_id))
        return True
