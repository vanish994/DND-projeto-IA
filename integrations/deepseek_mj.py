"""MJ conversacional baseado na API do DeepSeek.

O DeepSeek conduz a conversa, a narrativa e as decisões de apresentação.
O Rule Engine é a autoridade exclusiva para mecânicas de D&D chamadas por
ferramentas. Este módulo não envia a história inteira ao motor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from rule_engine import build_default_engine


SYSTEM_PROMPT = """Você é o Mestre de Jogo (MJ) da campanha.

A história, a ambientação, os personagens narrativos, os diálogos, os conflitos,
as cenas e a criatividade são livres e pertencem ao MJ. Não gere uma aventura
pré-fabricada nem tente controlar a imaginação do usuário.

Quando houver uma afirmação mecânica de D&D — monstro, magia, item, condição,
ataque, dano, cura, CD, resistência, imunidade, XP ou outra regra — use uma das
ferramentas disponíveis. Nunca invente conteúdo mecânico e nunca apresente uma
regra caseira como oficial. Se o Rule Engine bloquear ou não encontrar algo,
informe isso claramente e peça uma decisão narrativa ao MJ.

As ferramentas devolvem dados normativos. Você decide como apresentar e narrar
o resultado, sem alterar os valores oficiais. A escolha final de monstros e o
rumo da história permanecem com o MJ.
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sugerir_monstros",
            "description": "Lista candidatos oficiais do bestiário para o MJ escolher; não escolhe nem inventa monstros.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipos": {"type": "array", "items": {"type": "string"}},
                    "nd_min": {"type": "string"},
                    "nd_max": {"type": "string"},
                    "limite": {"type": "integer"},
                },
                "required": ["tipos", "nd_min", "nd_max", "limite"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_monstro",
            "description": "Obtém o bloco completo de um monstro oficial existente no SRD.",
            "parameters": {
                "type": "object",
                "properties": {"nome": {"type": "string"}},
                "required": ["nome"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolver_regra",
            "description": "Resolve fatos mecânicos usando o Rule Engine determinístico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fatos": {"type": "object", "additionalProperties": True},
                },
                "required": ["fatos"],
                "additionalProperties": False,
            },
        },
    },
]


def _carregar_env_local() -> None:
    """Carrega variáveis simples de .env sem sobrescrever o ambiente atual."""
    caminho = Path(__file__).resolve().parents[1] / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        nome, valor = nome.strip(), valor.strip().strip('"').strip("'")
        if nome and valor and nome not in os.environ:
            os.environ[nome] = valor


class DeepSeekMJ:
    """Orquestra conversa do MJ e chamadas normativas ao Rule Engine."""

    def __init__(self, client: Any | None = None, *, model: str | None = None):
        _carregar_env_local()
        self.uses_tokenharbor = bool(os.getenv("TOKENHARBOR_API_KEY"))
        default_model = "deepseek-v4.1-flash:free" if os.getenv("TOKENHARBOR_API_KEY") else "deepseek-flash"
        if client is None:
            from openai import OpenAI

            tokenharbor_key = os.getenv("TOKENHARBOR_API_KEY")
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            api_key = tokenharbor_key or deepseek_key
            if not api_key:
                raise RuntimeError("Defina TOKENHARBOR_API_KEY ou DEEPSEEK_API_KEY")
            if tokenharbor_key:
                base_url = os.getenv("TOKENHARBOR_BASE_URL", "https://tokenharbor.ai/v1")
            else:
                base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        self.client = client
        self.model = model or os.getenv("DEEPSEEK_MODEL", default_model)
        self.engine = build_default_engine()

    def _tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "sugerir_monstros":
            facts = {"type": "bestiary", "operacao": "sugerir", **args}
        elif name == "consultar_monstro":
            facts = {"type": "bestiary", "operacao": "bloco_completo", **args}
        elif name == "resolver_regra":
            facts = args["fatos"]
        else:
            return {"resultado": "bloqueado", "motivo": "ferramenta_desconhecida"}
        resolution = self.engine.evaluate(facts)
        return {"status": resolution.status, **dict(resolution.outcome)}

    @staticmethod
    def _message_dict(message: Any) -> dict[str, Any]:
        if hasattr(message, "model_dump"):
            return message.model_dump(exclude_none=True)
        if isinstance(message, dict):
            return message
        return {
            "role": getattr(message, "role", "assistant"),
            "content": getattr(message, "content", None),
            "reasoning_content": getattr(message, "reasoning_content", None),
            "tool_calls": getattr(message, "tool_calls", None),
        }

    def responder(self, texto: str, historico: list[dict[str, Any]] | None = None) -> str:
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        mensagens.extend(historico or [])
        mensagens.append({"role": "user", "content": texto})

        for _ in range(8):
            parametros = {
                "model": self.model,
                "messages": mensagens,
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_tokens": 4096,
            }
            if not self.uses_tokenharbor:
                parametros["extra_body"] = {"thinking": {"type": "disabled"}}
            resposta = self.client.chat.completions.create(**parametros)
            mensagem = resposta.choices[0].message
            mensagens.append(self._message_dict(mensagem))
            chamadas = getattr(mensagem, "tool_calls", None) or []
            if not chamadas:
                return getattr(mensagem, "content", "") or ""
            for chamada in chamadas:
                funcao = chamada.function
                resultado = self._tool(funcao.name, json.loads(funcao.arguments))
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })
        raise RuntimeError("O MJ excedeu o limite de chamadas de ferramentas")
