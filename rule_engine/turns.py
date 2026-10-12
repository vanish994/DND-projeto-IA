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
    ataques_oportunidade_bloqueados: bool = False
    esquivando: bool = False
    acao_preparada: dict[str, str] | None = None


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
        # PHB 2024: Surpresa impõe desvantagem na iniciativa; não remove ações do turno.
        self.turno_atual = EstadoTurno(
            identificador=participante.identificador,
            rodada=self.rodada,
            acao_disponivel=True,
            acao_bonus_disponivel=True,
            reacao_disponivel=True,
            movimento_restante=movimento,
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

    def mover(self, distancia: int, *, terreno_dificil: bool = False) -> int:
        """Consome movimento; terreno difícil custa o dobro por metro."""
        turno = self._exigir_turno()
        distancia = int(distancia)
        if distancia < 0:
            raise ValueError("A distância não pode ser negativa")
        custo = distancia * (2 if terreno_dificil else 1)
        if custo > turno.movimento_restante:
            raise ValueError("Movimento insuficiente")
        turno.movimento_restante -= custo
        return turno.movimento_restante

    def correr(self) -> int:
        """Executa Correr: gasta a ação e concede movimento adicional igual ao máximo."""
        turno = self._exigir_turno()
        self.gastar("acao")
        turno.movimento_restante += turno.movimento_maximo
        return turno.movimento_restante

    def executar_acao(self, nome: str, **parametros: str) -> dict[str, object]:
        """Executa uma ação estruturada e retorna seus efeitos auditáveis."""
        nome = nome.strip().lower()
        if nome == "correr":
            movimento = self.correr()
            return {"acao": nome, "resultado": "executada", "movimento_restante": movimento}

        nomes_acao = {
            "ajudar",
            "atacar",
            "analisar",
            "desengajar",
            "esconder",
            "esquivar",
            "influenciar",
            "preparar",
            "procurar",
            "usar_magia",
            "usar_objeto",
        }
        if nome not in nomes_acao:
            raise ValueError(f"Ação inválida: {nome}")
        if nome == "preparar" and (
            not parametros.get("gatilho", "").strip() or not parametros.get("resposta", "").strip()
        ):
            raise ValueError("Preparar exige gatilho e resposta")
        self.gastar("acao")
        turno = self._exigir_turno()
        efeitos: dict[str, object] = {"acao": nome, "resultado": "executada"}

        if nome == "desengajar":
            turno.ataques_oportunidade_bloqueados = True
            efeitos["ataques_oportunidade_bloqueados"] = True
        elif nome == "esquivar":
            turno.esquivando = True
            efeitos["esquivando"] = True
        elif nome == "preparar":
            gatilho = parametros.get("gatilho", "").strip()
            resposta = parametros.get("resposta", "").strip()
            turno.acao_preparada = {"gatilho": gatilho, "resposta": resposta}
            efeitos["acao_preparada"] = turno.acao_preparada
        elif nome == "esconder":
            efeitos["requer_teste_furtividade"] = True
        elif nome == "procurar":
            efeitos["requer_teste_percepcao_ou_investigacao"] = True
        elif nome == "ajudar":
            efeitos["alvo_deve_ser_especificado"] = True
        elif nome == "atacar":
            efeitos["pode_realizar_jogada_de_ataque"] = True
        elif nome == "usar_magia":
            efeitos["deve_validar_conjuracao"] = True
        elif nome == "influenciar":
            efeitos["deve_resolver_interacao_social"] = True
        return efeitos

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
