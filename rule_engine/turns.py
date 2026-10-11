"""Regras de iniciativa, rodadas, turnos e ações do combate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Participante:
    """Participante ordenável da iniciativa."""

    identificador: str
    iniciativa: int
    desempate: int = 0
    surpreendido: bool = False


@dataclass
class EstadoTurno:
    """Recursos disponíveis para o turno atual de uma criatura."""

    identificador: str
    rodada: int
    acao_disponivel: bool = True
    acao_bonus_disponivel: bool = True
    reacao_disponivel: bool = True
    movimento_restante: int = 0
    movimento_maximo: int = 0
    surpreendido: bool = False


@dataclass
class RastreadorCombate:
    """Controla a ordem de iniciativa e o ciclo de rodadas."""

    participantes: list[Participante]
    ordem: list[Participante] = field(init=False)
    indice: int = -1
    rodada: int = 0
    turno_atual: EstadoTurno | None = None
    deslocamentos: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.participantes:
            raise ValueError("O combate precisa de pelo menos um participante")
        ids = [p.identificador for p in self.participantes]
        if len(set(ids)) != len(ids):
            raise ValueError("Os identificadores dos participantes devem ser únicos")
        self.ordem = ordenar_iniciativa(self.participantes)

    def iniciar_proximo_turno(self) -> EstadoTurno:
        """Avança para o próximo participante e inicia seu turno."""
        self.indice = (self.indice + 1) % len(self.ordem)
        if self.indice == 0:
            self.rodada += 1
        participante = self.ordem[self.indice]
        movimento = int(self.deslocamentos.get(participante.identificador, 0))
        surpreendido = participante.surpreendido and self.rodada == 1
        self.turno_atual = EstadoTurno(
            identificador=participante.identificador,
            rodada=self.rodada,
            acao_disponivel=not surpreendido,
            acao_bonus_disponivel=not surpreendido,
            reacao_disponivel=not surpreendido,
            movimento_restante=0 if surpreendido else movimento,
            movimento_maximo=movimento,
            surpreendido=surpreendido,
        )
        return self.turno_atual

    def gastar(self, recurso: str) -> None:
        """Gasta uma ação, ação bônus ou reação no turno atual."""
        turno = self._exigir_turno()
        atributos = {
            "acao": "acao_disponivel",
            "acao_bonus": "acao_bonus_disponivel",
            "reacao": "reacao_disponivel",
        }
        if recurso not in atributos:
            raise ValueError("Recurso inválido; use acao, acao_bonus ou reacao")
        atributo = atributos[recurso]
        if not getattr(turno, atributo):
            raise ValueError(f"{recurso} já foi gasto ou está indisponível")
        setattr(turno, atributo, False)

    def mover(self, distancia: int) -> int:
        """Consome movimento e retorna o movimento restante."""
        turno = self._exigir_turno()
        distancia = int(distancia)
        if distancia < 0:
            raise ValueError("A distância não pode ser negativa")
        if distancia > turno.movimento_restante:
            raise ValueError("Movimento insuficiente")
        turno.movimento_restante -= distancia
        return turno.movimento_restante

    def correr(self) -> int:
        """Executa Correr: gasta a ação e concede movimento adicional igual ao máximo."""
        turno = self._exigir_turno()
        self.gastar("acao")
        turno.movimento_restante += turno.movimento_maximo
        return turno.movimento_restante

    def _exigir_turno(self) -> EstadoTurno:
        if self.turno_atual is None:
            raise ValueError("O combate ainda não iniciou um turno")
        return self.turno_atual


def ordenar_iniciativa(participantes: Iterable[Participante]) -> list[Participante]:
    """Ordena iniciativa maior primeiro; desempate maior primeiro e depois nome."""
    return sorted(
        list(participantes),
        key=lambda participante: (
            -int(participante.iniciativa),
            -int(participante.desempate),
            participante.identificador,
        ),
    )
