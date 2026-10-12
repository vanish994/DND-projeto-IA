"""Atributo de conjuração por classe, resolvido pelas regras do motor.

Fonte única para o backend e para o MJ: o atributo sai das regras de classe
(Livro do Jogador 2024) e nunca de um palpite de quem chama. A ficha sempre tem
precedência: se ela declara ``conjuracao.atributo_conjuracao``, é ele que vale.
"""

from __future__ import annotations

from typing import Any, Mapping

from .spellcasting import progresso_artifice

# Classes cujo atributo de conjuração o motor resolve por regra própria.
CLASSES_AVANCADAS = ("bruxo", "feiticeiro", "guardiao", "paladino")


def normalizar_classe(classe: Any) -> str:
    return str(classe or "").strip().lower().replace("í", "i").replace(" ", "")


def atributo_da_ficha(personagem: Mapping[str, Any] | None) -> str | None:
    """Atributo declarado na própria ficha, quando existir."""
    conjuracao = (personagem or {}).get("conjuracao") or {}
    informado = str(conjuracao.get("atributo_conjuracao") or "").strip().lower()
    return informado or None


def atributo_da_classe(
    engine: Any,
    classe: Any,
    *,
    nivel: int = 1,
    inteligencia: int = 10,
) -> str | None:
    """Atributo de conjuração das regras de classe, ou ``None`` se não houver."""
    normalizada = normalizar_classe(classe)
    if not normalizada:
        return None
    nivel = max(1, int(nivel or 1))
    if normalizada in {"artifice", "artificer"}:
        progresso = progresso_artifice(nivel, int(inteligencia))
        atributo = progresso.get("atributo_conjuracao")
        return str(atributo).lower() if atributo else None
    for fatos in (
        {"type": "spellcaster_feature", "feature": "progressao_conjuracao", "classe": normalizada, "nivel": nivel},
        {"type": "advanced_caster_feature", "classe": normalizada, "nivel": nivel},
    ):
        atributo = engine.evaluate(fatos).outcome.get("atributo_conjuracao")
        if atributo:
            return str(atributo).lower()
    return None


def atributo_de_conjuracao(
    engine: Any,
    personagem: Mapping[str, Any] | None,
    *,
    classe: Any = None,
    nivel: int | None = None,
) -> str | None:
    """Atributo de conjuração da ficha; sem ele, o das regras de classe."""
    personagem = personagem or {}
    declarado = atributo_da_ficha(personagem)
    if declarado:
        return declarado
    classe = classe if classe is not None else personagem.get("classe")
    nivel = nivel if nivel is not None else personagem.get("nivel", 1)
    inteligencia = int((personagem.get("atributos") or {}).get("inteligencia", 10))
    return atributo_da_classe(engine, classe, nivel=int(nivel or 1), inteligencia=inteligencia)
