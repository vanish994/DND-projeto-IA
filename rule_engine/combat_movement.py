"""Sentidos, movimento especial, montaria e combate subaquático."""

from __future__ import annotations

from typing import Any, Mapping


def resolver_sentidos(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Determina como sentidos especiais interagem com escuridão e invisibilidade."""
    sentido = str(fatos.get("sense", "visao_normal")).lower()
    escuridao = bool(fatos.get("darkness", False))
    alvo_invisivel = bool(fatos.get("invisible_target", False))
    alvo_oculto = bool(fatos.get("hidden_target", False))
    alcance = fatos.get("sense_range")
    if sentido == "visao_normal":
        percebido = not escuridao and not alvo_invisivel and not alvo_oculto
        return {"resultado": "percebido" if percebido else "não_percebido", "desvantagem": not percebido}
    if sentido == "visao_no_escuro":
        percebido = not alvo_invisivel and not alvo_oculto
        return {
            "resultado": "percebido" if percebido else "não_percebido",
            "desvantagem": not percebido,
            "alcance": alcance,
        }
    if sentido == "visao_as_cegas":
        return {
            "resultado": "percebido" if not alvo_oculto else "não_percebido",
            "ignora_invisibilidade": True,
            "alcance": alcance,
        }
    if sentido == "sentido_tremor":
        no_chao = bool(fatos.get("alvo_em_contato_com_o_solo", False))
        return {
            "resultado": "percebido" if no_chao else "não_percebido",
            "não_detecta_voo": not no_chao,
            "alcance": alcance,
        }
    if sentido == "visao_verdadeira":
        return {
            "resultado": "percebido" if not alvo_oculto else "não_percebido",
            "ignora_invisibilidade": True,
            "ignora_ilusoes": True,
            "alcance": alcance,
        }
    raise ValueError("Sentido especial inválido")


def custo_movimento(
    distancia: int,
    *,
    terreno_dificil: bool = False,
    rastejando: bool = False,
    escalando: bool = False,
    nadando: bool = False,
    deslocamento_especial: bool = False,
) -> int:
    """Calcula o custo de movimento especial em unidades de deslocamento."""
    distancia = int(distancia)
    if distancia < 0:
        raise ValueError("A distância não pode ser negativa")
    multiplicador = 1
    if not deslocamento_especial and (terreno_dificil or rastejando or escalando or nadando):
        multiplicador *= 2
    return distancia * multiplicador


def resolver_movimento_especial(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve movimento especial e levantar-se da condição Caído."""
    if fatos.get("stand_from_prone", False):
        deslocamento = int(fatos["movement_max"])
        return {
            "resultado": "levantou",
            "custo": deslocamento // 2,
            "movimento_restante": max(0, int(fatos.get("movement_remaining", 0)) - deslocamento // 2),
        }
    custo = custo_movimento(
        fatos["distance"],
        terreno_dificil=bool(fatos.get("difficult_terrain", False)),
        rastejando=bool(fatos.get("crawling", False)),
        escalando=bool(fatos.get("climbing", False)),
        nadando=bool(fatos.get("swimming", False)),
        deslocamento_especial=bool(fatos.get("special_speed", False)),
    )
    if custo > int(fatos.get("movement_remaining", custo)):
        return {"resultado": "bloqueado", "motivo": "movimento_insuficiente", "custo": custo}
    return {
        "resultado": "permitido",
        "custo": custo,
        "movimento_restante": int(fatos.get("movement_remaining", custo)) - custo,
    }


def resolver_montaria(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve montar, desmontar, controle e queda do cavaleiro."""
    acao = fatos.get("action", "montar")
    if acao in {"montar", "desmontar"}:
        if not bool(fatos.get("montaria_disposta", False)):
            return {"resultado": "bloqueado", "motivo": "montaria_indisposta"}
        if int(fatos.get("tamanho_montaria", 0)) <= int(fatos.get("tamanho_cavaleiro", 0)):
            return {"resultado": "bloqueado", "motivo": "montaria_nao_e_maior"}
        deslocamento = int(fatos.get("deslocamento_cavaleiro", 0))
        return {"resultado": "permitido", "acao": acao, "custo_movimento": deslocamento // 2}
    if acao == "controle_montaria":
        return {
            "resultado": "controlada" if bool(fatos.get("montaria_controlada", False)) else "independente",
            "iniciativa": "cavaleiro" if fatos.get("montaria_controlada", False) else "montaria",
        }
    if acao == "queda_montaria":
        rolagem = int(fatos.get("salvaguarda_destreza", 0))
        return {"resultado": "permanece_montado" if rolagem >= 10 else "caiu", "cd": 10}
    raise ValueError("Ação de montaria inválida")


def resolver_ataque_subaquatico(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Aplica as limitações de ataques subaquáticos."""
    if not bool(fatos.get("submerso", False)):
        return {"resultado": "normal"}
    tipo = fatos.get("tipo_ataque", "corpo_a_corpo")
    propriedade = fatos.get("propriedade_arma", "")
    distancia = float(fatos.get("distancia", 0))
    alcance = float(fatos.get("alcance", 0))
    if tipo == "corpo_a_corpo" and propriedade != "perfurante":
        return {"resultado": "permitido", "desvantagem": True, "motivo": "arma_nao_perfurante"}
    if tipo == "a_distancia" and distancia > alcance:
        return {"resultado": "bloqueado", "motivo": "fora_do_alcance_normal"}
    return {"resultado": "permitido", "desvantagem": tipo == "a_distancia", "motivo": "combate_subaquatico"}


def resolver_objeto(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a defesa básica de um objeto durante o combate."""
    if bool(fatos.get("imune_ao_tipo_de_dano", False)):
        dano = 0
    else:
        dano = max(0, int(fatos.get("dano", 0)))
    pv = max(0, int(fatos.get("pontos_de_vida", 0)) - dano)
    return {"resultado": "destruido" if pv == 0 else "danificado", "pv_restantes": pv, "ca": fatos.get("ca")}
