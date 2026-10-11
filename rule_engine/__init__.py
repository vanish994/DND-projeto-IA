"""Motor determinístico de regras do projeto DND-projeto-IA."""

from .engine import Rule, RuleEngine, Resolution
from .rules import build_default_engine

__all__ = ["Rule", "RuleEngine", "Resolution", "build_default_engine"]
