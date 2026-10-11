"""Estado e efeitos das condições do Livro do Jogador 2024."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


CONDICOES = {
    "cego", "enfeiticado", "surdo", "exaustao", "amedrontado", "agarrado",
    "incapacitado", "invisivel", "paralisado", "petrificado", "envenenado",
    "caido", "contido", "lento", "atordoado", "inconsciente",
}
ALIASES = {
    "blinded": "cego", "charmed": "enfeiticado", "deafened": "surdo",
    "exhaustion": "exaustao", "frightened": "amedrontado", "grappled": "agarrado",
    "incapacitated": "incapacitado", "invisible": "invisivel", "paralyzed": "paralisado",
    "petrified": "petrificado", "poisoned": "envenenado", "prone": "caido",
    "restrained": "contido", "slowed": "lento", "stunned": "atordoado",
    "unconscious": "inconsciente",
}


def normalizar_condicao(condicao: str) -> str:
    return ALIASES.get(condicao.lower(), condicao.lower())


@dataclass
class EstadoCondicoes:
    """Condições ativas, imunidades e durações de uma criatura."""

    ativas: set[str] = field(default_factory=set)
    imunidades: set[str] = field(default_factory=set)
    duracoes: dict[str, int | str] = field(default_factory=dict)

    def aplicar(self, condicao: str, duracao: int | str | None = None) -> dict[str, Any]:
        condicao = normalizar_condicao(condicao)
        validar_condicao(condicao)
        if condicao in self.imunidades:
            return {"resultado": "não_aplicada", "motivo": "imune", "condicao": condicao}
        if condicao in self.ativas:
            return {"resultado": "já_ativa", "condicao": condicao}
        self.ativas.add(condicao)
        if duracao is not None:
            self.duracoes[condicao] = duracao
        return {"resultado": "aplicada", "condicao": condicao}

    def remover(self, condicao: str) -> dict[str, Any]:
        condicao = normalizar_condicao(condicao)
        validar_condicao(condicao)
        if condicao not in self.ativas:
            return {"resultado": "não_ativa", "condicao": condicao}
        self.ativas.remove(condicao)
        self.duracoes.pop(condicao, None)
        return {"resultado": "removida", "condicao": condicao}

    def reduzir_duracoes(self, unidades: int = 1) -> list[str]:
        encerradas: list[str] = []
        for condicao, duracao in list(self.duracoes.items()):
            if isinstance(duracao, int):
                nova = duracao - int(unidades)
                if nova <= 0:
                    encerradas.append(condicao)
                    self.remover(condicao)
                else:
                    self.duracoes[condicao] = nova
        return encerradas


def validar_condicao(condicao: str) -> None:
    if normalizar_condicao(condicao) not in CONDICOES:
        raise ValueError(f"Condição inválida: {condicao}")


def resolver_estado_condicao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    estado = fatos["estado"]
    operacao = fatos.get("operation", "query")
    if operacao == "apply":
        return estado.aplicar(fatos["condition"], fatos.get("duration"))
    if operacao == "remove":
        return estado.remover(fatos["condition"])
    if operacao == "tick":
        return {"resultado": "durações_reduzidas", "encerradas": estado.reduzir_duracoes(fatos.get("units", 1))}
    if operacao == "query":
        return {"resultado": "ativa" if fatos["condition"] in estado.ativas else "não_ativa"}
    raise ValueError("Operação de condição inválida")


def resolver_efeitos_condicao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Retorna os efeitos derivados de todas as condições relevantes."""
    atacante = {normalizar_condicao(condicao) for condicao in fatos.get("attacker_conditions", ())}
    alvo = {normalizar_condicao(condicao) for condicao in fatos.get("target_conditions", ())}
    acao = fatos.get("action", "")
    resultado: dict[str, Any] = {"tipo": "condition_effect", "resultado": "normal", "result": "normal"}

    if acao == "attack":
        vantagem = bool({"cego", "envenenado", "contido", "amedrontado"} & atacante)
        desvantagem = bool({"cego", "envenenado", "contido", "caido"} & atacante)
        if "invisivel" in atacante:
            vantagem = True
        if "cego" in alvo or "contido" in alvo or "paralisado" in alvo or "inconsciente" in alvo:
            vantagem = True
        if "invisivel" in alvo:
            desvantagem = True
        if "caido" in alvo and fatos.get("distancia", "corpo_a_corpo") != "corpo_a_corpo":
            desvantagem = True
        if vantagem and desvantagem:
            resultado["resultado"] = "normal"
        elif vantagem:
            resultado["resultado"] = "vantagem"
        elif desvantagem:
            resultado["resultado"] = "desvantagem"
        resultado["result"] = resultado["resultado"]
        if ("paralisado" in alvo or "inconsciente" in alvo) and fatos.get("distancia", "corpo_a_corpo") == "corpo_a_corpo":
            resultado["acerto_critico_automatico"] = True
        return resultado

    resultado.update({
        "pode_mover": not bool({"agarrado", "incapacitado", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo),
        "pode_realizar_acoes": not bool({"incapacitado", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo),
        "pode_falar": not bool({"incapacitado", "inconsciente"} & alvo),
        "pode_ver": "cego" not in alvo,
        "pode_ouvir": "surdo" not in alvo,
        "desvantagem_salvaguardas": "amedrontado" in alvo or "envenenado" in alvo,
        "falha_salvaguardas_forca_destreza": bool({"paralisado", "petrificado", "inconsciente"} & alvo),
    })
    if "amedrontado" in alvo:
        resultado["não_pode_se_aproximar_da_fonte"] = True
    if "enfeiticado" in alvo:
        resultado["não_pode_atacar_o_enfeiticador"] = True
    if "invisivel" in alvo:
        resultado["não_pode_ser_visto"] = True
    if "caido" in alvo:
        resultado["movimento_para_levantar"] = "metade_do_deslocamento"
    if "lento" in alvo:
        resultado["deslocamento_reduzido"] = True
    if "exaustao" in alvo:
        niveis_exaustao = fatos.get(
            "exaustao_niveis", fatos.get("exhaustion_niveis", fatos.get("exhaustion_levels", 1))
        )
        resultado["modificador_d20"] = -2 * int(niveis_exaustao)
    return resultado
