"""Motor determinístico de regras do projeto DND-projeto-IA."""

from .engine import Rule, RuleEngine, Resolution
from .core import ResultadoD20, bonus_proficiencia, modificador_atributo, resolver_teste_d20
from .combat_special import (
    cd_ataque_desarmado, resolver_agarrar, resolver_ataque_oportunidade,
    resolver_empurrar, resolver_escape_agarramento,
)
from .rules import build_default_engine
from .turns import EstadoTurno, Participante, RastreadorCombate, ordenar_iniciativa

__all__ = [
    "Rule", "RuleEngine", "Resolution", "ResultadoD20", "bonus_proficiencia",
    "modificador_atributo", "resolver_teste_d20", "build_default_engine",
    "Participante", "EstadoTurno", "RastreadorCombate", "ordenar_iniciativa",
    "cd_ataque_desarmado", "resolver_agarrar", "resolver_ataque_oportunidade",
    "resolver_empurrar", "resolver_escape_agarramento",
]
