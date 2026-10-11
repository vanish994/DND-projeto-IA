"""Backend HTTP do MJ DeepSeek.

A chave do provedor permanece no servidor. O cliente envia apenas mensagens;
o DeepSeek conduz a conversa e usa o Rule Engine por ferramentas.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from integrations.deepseek_mj import DeepSeekMJ

logger = logging.getLogger(__name__)

app = FastAPI(
    title="D&D Projeto IA — MJ",
    version="1.0.0",
    description="MJ DeepSeek com Rule Engine determinístico para mecânicas oficiais.",
)

_mj: DeepSeekMJ | None = None
_sessoes: dict[str, list[dict[str, Any]]] = {}


class MensagemMJ(BaseModel):
    sessao_id: str = Field(min_length=1, max_length=128)
    mensagem: str = Field(min_length=1, max_length=20000)


class RespostaMJ(BaseModel):
    sessao_id: str
    resposta: str
    narrativa_fora_do_motor: bool = True


def obter_mj() -> DeepSeekMJ:
    global _mj
    if _mj is None:
        try:
            _mj = DeepSeekMJ()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _mj


@app.get("/v1/status")
def status() -> dict[str, str]:
    return {
        "status": "online",
        "servico": "mj-deepseek",
        "motor_regras": "deterministico",
    }


@app.post("/v1/mj/mensagem", response_model=RespostaMJ)
def mensagem_mj(pedido: MensagemMJ) -> RespostaMJ:
    mj = obter_mj()
    historico = _sessoes.setdefault(pedido.sessao_id, [])
    try:
        resposta = mj.responder(pedido.mensagem, historico)
    except Exception as exc:
        logger.exception("Falha na chamada do provedor do MJ: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Falha ao consultar o MJ configurado") from exc
    historico.extend([
        {"role": "user", "content": pedido.mensagem},
        {"role": "assistant", "content": resposta},
    ])
    return RespostaMJ(sessao_id=pedido.sessao_id, resposta=resposta)


@app.delete("/v1/mj/sessoes/{sessao_id}", status_code=204)
def apagar_sessao(sessao_id: str) -> None:
    _sessoes.pop(sessao_id, None)
