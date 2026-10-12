"""Contratos estruturados entre o MJ, o Orquestrador e o Rule Engine.

O MJ não fala mais "execute esta regra": ele declara uma :class:`Acao` — uma
intenção com alvo e parâmetros — e recebe de volta um :class:`ResultadoAcao`
com o que o motor decidiu, o que mudou no estado e quais dados foram rolados.

Nenhum dos dois lados precisa conhecer o formato interno do outro, e a
interface continua recebendo o mesmo dicionário de sempre por meio de
``ResultadoAcao.para_ferramenta()``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Ferramentas que o MJ pode chamar. Qualquer outra coisa é recusada.
FERRAMENTAS_CONHECIDAS = {"sugerir_monstros", "consultar_monstro", "resolver_regra"}


@dataclass(frozen=True)
class Acao:
    """Intenção estruturada enviada pelo MJ.

    ``tipo`` é o tipo de fato do motor (``attack``, ``spell_cast``,
    ``ability_check``, ``bestiary``...). ``parametros`` são os fatos declarados
    pelo MJ, sem nada derivado: modificador, CA e proficiência nunca vêm daqui.
    """

    ferramenta: str
    tipo: str
    parametros: Mapping[str, Any] = field(default_factory=dict)
    personagem_id: str | None = None
    alvo: str | None = None

    @classmethod
    def de_ferramenta(cls, nome: str, argumentos: Mapping[str, Any] | None = None) -> "Acao":
        """Traduz a chamada de ferramenta do MJ em intenção estruturada.

        Esta é a etapa "interpretar o pedido estruturado": nada de regra é
        decidido aqui, apenas o reconhecimento do formato.
        """
        argumentos = dict(argumentos or {})
        if nome == "sugerir_monstros":
            fatos: dict[str, Any] = {"type": "bestiary", "operacao": "sugerir", **argumentos}
        elif nome == "consultar_monstro":
            fatos = {"type": "bestiary", "operacao": "bloco_completo", **argumentos}
        elif nome == "resolver_regra":
            fatos = dict(argumentos.get("fatos") or {})
        else:
            return cls(ferramenta=nome, tipo="desconhecida", parametros=argumentos)
        return cls(
            ferramenta=nome,
            tipo=str(fatos.get("type") or ""),
            parametros=fatos,
            personagem_id=fatos.get("character_id"),
            alvo=fatos.get("target_name") or fatos.get("alvo"),
        )

    def para_fatos(self) -> dict[str, Any]:
        """Devolve uma cópia mutável dos fatos que vão ao motor."""
        return dict(self.parametros)


@dataclass
class ResultadoAcao:
    """Resultado estruturado de uma ação.

    ``status`` descreve o desfecho da ação (``resolvido`` ou ``bloqueado``),
    ``dados`` é o payload entregue ao MJ, ``alteracoes`` é o que foi aplicado
    ao estado canônico e ``rolagens`` são os dados que o motor rolou.
    """

    status: str
    dados: dict[str, Any] = field(default_factory=dict)
    alteracoes: list[dict[str, Any]] = field(default_factory=list)
    rolagens: list[dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def bloqueado(motivo: str, **detalhes: Any) -> "ResultadoAcao":
        """Recusa explícita: o sistema diz o que faltou em vez de inventar."""
        return ResultadoAcao("bloqueado", {"resultado": "bloqueado", "motivo": motivo, **detalhes})

    def para_ferramenta(self) -> dict[str, Any]:
        """Formato de resposta da ferramenta, consumido pelo MJ."""
        return dict(self.dados)

    @property
    def motivo(self) -> str | None:
        return self.dados.get("motivo")
