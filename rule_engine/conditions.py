"""Estado persistente e efeitos das 16 condições do Livro do Jogador 2024."""
from __future__ import annotations
from dataclasses import dataclass, field
import unicodedata
from typing import Any, Mapping

CONDICOES = {"cego", "enfeiticado", "surdo", "exaustao", "amedrontado", "agarrado", "incapacitado", "invisivel", "paralisado", "petrificado", "envenenado", "caido", "contido", "lento", "atordoado", "inconsciente"}
ALIASES = {"blinded": "cego", "charmed": "enfeiticado", "deafened": "surdo", "exhaustion": "exaustao", "frightened": "amedrontado", "grappled": "agarrado", "incapacitated": "incapacitado", "invisible": "invisivel", "paralyzed": "paralisado", "petrified": "petrificado", "poisoned": "envenenado", "prone": "caido", "restrained": "contido", "slowed": "lento", "stunned": "atordoado", "unconscious": "inconsciente"}


def _chave(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    return "".join(c for c in texto if not unicodedata.combining(c)).replace("-", "_").replace(" ", "_")


def normalizar_condicao(condicao: str) -> str:
    chave = _chave(condicao)
    return ALIASES.get(chave, chave)


def validar_condicao(condicao: str) -> None:
    if normalizar_condicao(condicao) not in CONDICOES:
        raise ValueError(f"Condição inválida: {condicao}")


@dataclass
class EstadoCondicoes:
    """Condições, imunidades, durações e níveis de Exaustão de uma criatura."""
    ativas: set[str] = field(default_factory=set)
    imunidades: set[str] = field(default_factory=set)
    duracoes: dict[str, int | str] = field(default_factory=dict)
    exaustao: int = 0

    def __post_init__(self) -> None:
        self.ativas = {normalizar_condicao(c) for c in self.ativas}
        self.imunidades = {normalizar_condicao(c) for c in self.imunidades}
        self.exaustao = max(0, int(self.exaustao))

    def aplicar(self, condicao: str, duracao: int | str | None = None) -> dict[str, Any]:
        c = normalizar_condicao(condicao)
        validar_condicao(c)
        if c == "exaustao":
            self.exaustao = min(6, self.exaustao + max(1, int(duracao or 1)))
            self.ativas.add(c)
            return {"resultado": "aplicada", "condicao": c, "nivel": self.exaustao}
        if c in self.imunidades:
            return {"resultado": "não_aplicada", "motivo": "imune", "condicao": c}
        if c in self.ativas:
            if duracao is not None:
                self.duracoes[c] = duracao
            return {"resultado": "já_ativa", "condicao": c}
        self.ativas.add(c)
        if duracao is not None:
            self.duracoes[c] = duracao
        return {"resultado": "aplicada", "condicao": c, "duracao": duracao}

    def remover(self, condicao: str) -> dict[str, Any]:
        c = normalizar_condicao(condicao)
        validar_condicao(c)
        if c == "exaustao":
            if self.exaustao <= 0:
                return {"resultado": "não_ativa", "condicao": c}
            self.exaustao -= 1
            if self.exaustao == 0:
                self.ativas.discard(c)
            return {"resultado": "removida", "condicao": c, "nivel": self.exaustao}
        if c not in self.ativas:
            return {"resultado": "não_ativa", "condicao": c}
        self.ativas.remove(c)
        self.duracoes.pop(c, None)
        return {"resultado": "removida", "condicao": c}

    def reduzir_duracoes(self, unidades: int = 1) -> list[str]:
        encerradas = []
        for c, duracao in list(self.duracoes.items()):
            if isinstance(duracao, int):
                nova = duracao - max(1, int(unidades))
                if nova <= 0:
                    encerradas.append(c)
                    self.remover(c)
                else:
                    self.duracoes[c] = nova
        return encerradas


def resolver_estado_condicao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    estado = fatos["estado"]
    operacao = fatos.get("operation", "query")
    c = normalizar_condicao(fatos.get("condition", ""))
    if operacao == "apply":
        return estado.aplicar(c, fatos.get("duration"))
    if operacao == "remove":
        return estado.remover(c)
    if operacao == "tick":
        return {"resultado": "durações_reduzidas", "encerradas": estado.reduzir_duracoes(fatos.get("units", 1))}
    if operacao == "query":
        return {"resultado": "ativa" if c in estado.ativas else "não_ativa", "condicao": c, "nivel_exaustao": estado.exaustao}
    raise ValueError("Operação de condição inválida")


def resolver_efeitos_condicao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    alvo = {normalizar_condicao(c) for c in fatos.get("target_conditions", fatos.get("condicoes_alvo", ())) }
    atacante = {normalizar_condicao(c) for c in fatos.get("attacker_conditions", fatos.get("condicoes_atacante", ())) }
    acao = str(fatos.get("action", "")).lower()
    distancia = str(fatos.get("distance", "corpo_a_corpo")).lower()
    resultado: dict[str, Any] = {"tipo": "condition_effect", "resultado": "normal", "result": "normal"}

    if acao == "attack":
        vantagem = bool({"cego", "contido", "paralisado", "atordoado", "inconsciente"} & alvo) or "invisivel" in atacante or "cego" in atacante
        desvantagem = bool({"cego", "envenenado", "contido"} & atacante) or "invisivel" in alvo
        if "amedrontado" in atacante and fatos.get("fonte_no_campo_de_visao", True):
            desvantagem = True
        if "caido" in alvo and distancia != "corpo_a_corpo":
            desvantagem = True
        if "caido" in alvo and distancia == "corpo_a_corpo":
            vantagem = True
        resultado["resultado"] = "normal" if vantagem == desvantagem else "vantagem" if vantagem else "desvantagem"
        resultado["result"] = resultado["resultado"]
        resultado["acerto_critico_automatico"] = bool({"paralisado", "inconsciente"} & alvo and distancia == "corpo_a_corpo")
        return resultado

    incapacitado = {"incapacitado", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo
    resultado.update({
        "pode_mover": not bool({"agarrado", "contido", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo),
        "deslocamento": 0 if {"agarrado", "contido", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo else "normal",
        "pode_realizar_acoes": not bool(incapacitado),
        "pode_realizar_reacoes": not bool(incapacitado),
        "pode_falar": not bool({"incapacitado", "inconsciente"} & alvo),
        "pode_ver": "cego" not in alvo,
        "pode_ouvir": "surdo" not in alvo,
        "desvantagem_salvaguardas": bool({"amedrontado", "envenenado", "contido"} & alvo),
        "desvantagem_salvaguarda_destreza": "contido" in alvo,
        "falha_salvaguardas_forca_destreza": bool({"paralisado", "petrificado", "atordoado", "inconsciente"} & alvo),
    })
    if "petrificado" in alvo:
        resultado.update({"resistencia_todos_danos": True, "imune_envenenado_e_doenca": True})
    if "amedrontado" in alvo:
        resultado["não_pode_se_aproximar_da_fonte"] = True
    if "enfeiticado" in alvo:
        resultado["não_pode_atacar_o_enfeiticador"] = True
    if "invisivel" in alvo:
        resultado["não_pode_ser_visto"] = True
    if "caido" in alvo:
        resultado["movimento_para_levantar"] = "metade_do_deslocamento"
        resultado["pode_rastejar"] = True
    if "exaustao" in alvo:
        nivel = int(fatos.get("exaustao_niveis", fatos.get("exhaustion_niveis", fatos.get("exhaustion_levels", 1))))
        resultado["modificador_d20"] = -2 * nivel
    if "lento" in alvo:
        resultado["deslocamento_reduzido_m"] = int(fatos.get("reducao_lento_m", 3))
        resultado["deslocamento_reduzido"] = True
    return resultado
