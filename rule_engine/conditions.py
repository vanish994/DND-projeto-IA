"""Estado persistente e efeitos das 15 condições do Livro do Jogador 2024."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Mapping

CONDICOES = {
    "cego",
    "enfeiticado",
    "surdo",
    "exaustao",
    "amedrontado",
    "agarrado",
    "incapacitado",
    "invisivel",
    "paralisado",
    "petrificado",
    "envenenado",
    "caido",
    "contido",
    "atordoado",
    "inconsciente",
}
ALIASES = {
    "blinded": "cego",
    "charmed": "enfeiticado",
    "deafened": "surdo",
    "exhaustion": "exaustao",
    "frightened": "amedrontado",
    "grappled": "agarrado",
    "incapacitated": "incapacitado",
    "invisible": "invisivel",
    "paralyzed": "paralisado",
    "petrified": "petrificado",
    "poisoned": "envenenado",
    "prone": "caido",
    "restrained": "contido",
    "stunned": "atordoado",
    "unconscious": "inconsciente",
}


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
        for condicao in self.ativas | self.imunidades:
            validar_condicao(condicao)
        self.exaustao = min(6, max(0, int(self.exaustao)))
        if self.exaustao:
            self.ativas.add("exaustao")

    def aplicar(self, condicao: str, duracao: int | str | None = None) -> dict[str, Any]:
        c = normalizar_condicao(condicao)
        validar_condicao(c)
        if c in self.imunidades:
            return {"resultado": "não_aplicada", "motivo": "imune", "condicao": c}
        if isinstance(duracao, int) and not isinstance(duracao, bool) and duracao < 1:
            raise ValueError("A duração deve ser positiva")
        if isinstance(duracao, str) and not duracao.strip():
            raise ValueError("A duração textual não pode ser vazia")
        if duracao is not None and not isinstance(duracao, (int, str)):
            raise TypeError("A duração deve ser um número de unidades ou uma descrição textual")
        if c == "exaustao":
            self.exaustao = min(6, self.exaustao + max(1, int(duracao or 1)))
            self.ativas.add(c)
            return {"resultado": "aplicada", "condicao": c, "nivel": self.exaustao, "morto": self.exaustao >= 6}
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

    def encerrar_por_salvaguarda(self, condicao: str, rolagem: int, modificador: int, cd: int) -> dict[str, Any]:
        """Resolve uma salvaguarda explícita para encerrar uma condição.

        O chamador deve invocar este método somente quando o efeito permitir
        uma nova salvaguarda (por exemplo, no fim do turno). A rolagem é
        fornecida pelo motor para manter aleatoriedade e contexto fora do estado.
        """
        c = normalizar_condicao(condicao)
        validar_condicao(c)
        for nome, valor in (("rolagem", rolagem), ("modificador", modificador), ("cd", cd)):
            if isinstance(valor, bool) or not isinstance(valor, int):
                raise TypeError(f"{nome} deve ser inteiro")
        if not 1 <= rolagem <= 20:
            raise ValueError("A rolagem deve estar entre 1 e 20")
        if c not in self.ativas:
            return {"resultado": "não_ativa", "condicao": c, "encerrada": False}
        total = rolagem + modificador
        sucesso = total >= cd
        if sucesso:
            self.remover(c)
        return {
            "resultado": "encerrada" if sucesso else "continua",
            "condicao": c,
            "rolagem": rolagem,
            "modificador": modificador,
            "total": total,
            "cd": cd,
            "encerrada": sucesso,
        }

    def reduzir_duracoes(self, unidades: int = 1) -> list[str]:
        if isinstance(unidades, bool) or not isinstance(unidades, int) or unidades < 1:
            raise ValueError("As unidades de duração devem ser um inteiro positivo")
        encerradas = []
        for c, duracao in list(self.duracoes.items()):
            if isinstance(duracao, int) and not isinstance(duracao, bool):
                nova = duracao - unidades
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
        validar_condicao(c)
        return {
            "resultado": "ativa" if c in estado.ativas else "não_ativa",
            "condicao": c,
            "nivel_exaustao": estado.exaustao,
        }
    raise ValueError("Operação de condição inválida")


def resolver_efeitos_condicao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    alvo = {normalizar_condicao(c) for c in fatos.get("target_conditions", fatos.get("condicoes_alvo", ()))}
    atacante = {normalizar_condicao(c) for c in fatos.get("attacker_conditions", fatos.get("condicoes_atacante", ()))}
    acao = str(fatos.get("action", "")).lower()
    distancia_raw = fatos.get("distance")
    distancia = str(distancia_raw).lower() if distancia_raw is not None else None
    resultado: dict[str, Any] = {"tipo": "condition_effect", "resultado": "normal", "result": "normal"}

    if acao == "attack":
        incapacitantes_atacante = {"incapacitado", "paralisado", "petrificado", "atordoado", "inconsciente"} & atacante
        if incapacitantes_atacante:
            return {
                **resultado,
                "resultado": "bloqueado",
                "result": "blocked",
                "motivo": "atacante_incapacitado",
                "condicoes": sorted(incapacitantes_atacante),
            }
        if "enfeiticado" in atacante and fatos.get("alvo_e_enfeiticador", False):
            return {
                **resultado,
                "resultado": "bloqueado",
                "result": "blocked",
                "motivo": "nao_pode_atacar_ou_afetar_enfeiticador",
            }
        atacante_invisivel_visto = bool(fatos.get("alvo_pode_ver_atacante", False))
        alvo_invisivel_visto = bool(fatos.get("atacante_pode_ver_alvo", False))
        vantagem = bool({"cego", "contido", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo) or (
            "invisivel" in atacante and not atacante_invisivel_visto
        )
        desvantagem = bool({"cego", "envenenado", "contido", "caido"} & atacante) or (
            "invisivel" in alvo and not alvo_invisivel_visto
        )
        if "agarrado" in atacante and not fatos.get("alvo_e_agarrador", False):
            desvantagem = True
        if "amedrontado" in atacante and fatos.get("fonte_no_campo_de_visao", True):
            desvantagem = True
        if fatos.get("alvo_esquivando", False) and fatos.get("atacante_visivel_para_alvo", True):
            desvantagem = True
        if "caido" in alvo:
            distancia_m = fatos.get("distancia_m", fatos.get("distance_m"))
            if distancia_m is not None:
                if float(distancia_m) <= 1.5:
                    vantagem = True
                else:
                    desvantagem = True
            elif distancia == "corpo_a_corpo":
                vantagem = True
            elif distancia in {"a_distancia", "ranged", "distancia"}:
                desvantagem = True
            else:
                resultado["distancia_indefinida_para_caido"] = True
        resultado["resultado"] = "normal" if vantagem == desvantagem else "vantagem" if vantagem else "desvantagem"
        resultado["result"] = resultado["resultado"]
        distancia_m = fatos.get("distancia_m", fatos.get("distance_m"))
        resultado["acerto_critico_automatico"] = bool(
            {"paralisado", "inconsciente"} & alvo and distancia_m is not None and float(distancia_m) <= 1.5
        )
        return resultado

    incapacitado = {"incapacitado", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo
    resultado.update(
        {
            "pode_mover": not bool(
                {"agarrado", "contido", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo
            ),
            "deslocamento": (
                0
                if {"agarrado", "contido", "paralisado", "petrificado", "atordoado", "inconsciente"} & alvo
                else "normal"
            ),
            "pode_realizar_acoes": not bool(incapacitado),
            "pode_realizar_reacoes": not bool(incapacitado),
            # Incapacitado, isoladamente, não impede a fala; Paralisado,
            # Petrificado e Inconsciente impedem. Atordoado permite fala vacilante.
            "pode_falar": not bool({"paralisado", "petrificado", "inconsciente"} & alvo),
            "fala_vacilante": "atordoado" in alvo,
            "pode_ver": "cego" not in alvo,
            "pode_ouvir": "surdo" not in alvo,
            "falha_automaticamente_teste_que_exige_visao": "cego" in alvo,
            "falha_automaticamente_teste_que_exige_audicao": "surdo" in alvo,
            "encerra_concentracao": bool(incapacitado),
            "desvantagem_salvaguardas": False,
            "desvantagem_salvaguarda_destreza": "contido" in alvo,
            "desvantagem_testes_habilidade": ("envenenado" in alvo)
            or ("amedrontado" in alvo and fatos.get("fonte_no_campo_de_visao", True)),
            "falha_salvaguardas_forca_destreza": bool(
                {"paralisado", "petrificado", "atordoado", "inconsciente"} & alvo
            ),
        }
    )
    if "petrificado" in alvo:
        resultado.update(
            {
                "resistencia_todos_danos": True,
                "imune_envenenado_e_doenca": True,
                "pode_falar": False,
                "peso_multiplicado": 10,
                "envelhecimento_suspenso": True,
            }
        )
    if "inconsciente" in alvo:
        resultado.update({"tambem_caido": True, "derruba_objetos_empunhados": True, "desatento_ao_ambiente": True})
    if "agarrado" in alvo and (
        fatos.get("agarrador_incapacitado", False)
        or fatos.get("distancia_agarrador_m") is not None
        and float(fatos["distancia_agarrador_m"]) > float(fatos.get("alcance_agarrador_m", 1.5))
    ):
        resultado["agarrado_termina"] = True
    if "amedrontado" in alvo:
        resultado["não_pode_se_aproximar_da_fonte"] = True
    if "enfeiticado" in alvo:
        resultado.update(
            {"não_pode_atacar_o_enfeiticador": True, "não_pode_afetar_o_enfeiticador_com_efeito_nocivo": True}
        )
        if fatos.get("atacante_e_enfeiticador", False):
            resultado["vantagem_em_testes_sociais_contra_alvo"] = True
    if "invisivel" in alvo:
        resultado["não_pode_ser_visto"] = True
    if "caido" in alvo:
        resultado["movimento_para_levantar"] = "metade_do_deslocamento"
        resultado["pode_rastejar"] = True
    if "exaustao" in alvo:
        nivel = int(fatos.get("exaustao_niveis", fatos.get("exhaustion_niveis", fatos.get("exhaustion_levels", 1))))
        resultado["modificador_d20"] = -2 * nivel
        resultado["deslocamento_reduzido_m"] = 1.5 * nivel
        resultado["morre_no_nivel_6"] = nivel >= 6

    return resultado
