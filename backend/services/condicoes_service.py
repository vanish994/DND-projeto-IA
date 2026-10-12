"""Condições, durações e concentração das fichas e tokens de monstro."""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import HTTPException

from backend.persistencia import RepositorioCampanhas
from backend.schemas import AtualizarCondicaoPersonagem
from rule_engine import build_default_engine
from rule_engine.conditions import EstadoCondicoes, normalizar_condicao, resolver_efeitos_condicao


def condicoes_da_ficha(ficha: dict) -> EstadoCondicoes:
    return EstadoCondicoes(
        ativas=set(ficha.get("condicoes_ativas") or []),
        imunidades=set(ficha.get("imunidades_condicoes") or []),
        duracoes=dict(ficha.get("duracoes_condicoes") or {}),
        exaustao=int(ficha.get("exaustao_nivel", 0)),
    )


def duracao_textual_expira(duracao: Any, momento: str) -> bool:
    if not isinstance(duracao, str):
        return False
    texto = duracao.casefold()
    if momento == "fim":
        return "até o fim do próximo turno" in texto or "until the end of its next turn" in texto
    return "até o início do próximo turno" in texto or "until the start of its next turn" in texto


def salvar_condicoes_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem: dict, estado: EstadoCondicoes) -> dict:
    dados = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    dados["condicoes_ativas"] = sorted(estado.ativas)
    dados["imunidades_condicoes"] = sorted(estado.imunidades)
    dados["duracoes_condicoes"] = dict(estado.duracoes)
    dados["exaustao_nivel"] = estado.exaustao
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], dados)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


def expirar_duracoes_textuais_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, ficha: dict, momento: str) -> list[str]:
    estado = condicoes_da_ficha(ficha)
    encerradas = []
    for condicao, duracao in list(estado.duracoes.items()):
        if duracao_textual_expira(duracao, momento):
            estado.remover(condicao)
            encerradas.append(normalizar_condicao(condicao))
    if encerradas:
        salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
    return encerradas


def reduzir_duracoes_numericas_token(token: dict) -> list[str]:
    """Reduz no fim do turno as durações numéricas das condições de um monstro."""
    duracoes = token.get("condition_durations") or {}
    condicoes = token.get("conditions") or []
    encerradas = []
    for condicao, duracao in list(duracoes.items()):
        if not isinstance(duracao, int) or isinstance(duracao, bool):
            continue
        restante = duracao - 1
        chave = normalizar_condicao(condicao)
        if restante <= 0:
            token["conditions"] = [c for c in condicoes if normalizar_condicao(c) != chave]
            condicoes = token["conditions"]
            duracoes.pop(condicao, None)
            encerradas.append(chave)
        else:
            duracoes[condicao] = restante
    token["condition_durations"] = duracoes
    return encerradas


def expirar_duracoes_textuais_token(token: dict, momento: str) -> list[str]:
    duracoes = token.get("condition_durations") or {}
    condicoes = token.get("conditions") or []
    encerradas = []
    for condicao, duracao in list(duracoes.items()):
        if duracao_textual_expira(duracao, momento):
            chave = normalizar_condicao(condicao)
            token["conditions"] = [c for c in condicoes if normalizar_condicao(c) != chave]
            condicoes = token["conditions"]
            duracoes.pop(condicao, None)
            encerradas.append(chave)
    token["condition_durations"] = duracoes
    return encerradas


def validar_turno_ativo(estado: dict, token_id: str) -> None:
    if estado.get("combate_ativo") and estado.get("token_ativo") != token_id:
        raise HTTPException(status_code=409, detail={
            "motivo": "turno_de_outra_criatura",
            "token_ativo": estado.get("token_ativo"),
            "token_solicitado": token_id,
        })


def resolver_concentracao_apos_dano(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dano: int) -> dict | None:
    """Aplica a salvaguarda de concentração ao dano real recebido pelo personagem."""
    ficha = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if not ficha:
        return None
    magia = ficha.get("concentrando")
    if not magia:
        return {"resultado": "não_concentrando", "concentracao_mantida": False}
    estado = condicoes_da_ficha(ficha)
    efeitos = resolver_efeitos_condicao({"action": "move", "target_conditions": list(estado.ativas)})
    if ficha.get("pv_atual", 1) <= 0 or efeitos.get("encerra_concentracao"):
        ficha_atualizada = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        ficha_atualizada["concentrando"] = None
        repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha_atualizada)
        return {"resultado": "concentracao_encerrada", "concentracao_mantida": False, "motivo": "incapacitado_ou_inconsciente", "magia": magia}
    modificadores = ficha.get("modificadores") or {}
    profs = ficha.get("proficiencias_salvaguarda") or ficha.get("proficiencias_salvacao") or []
    if isinstance(profs, str):
        profs = [profs]
    bonus = int(modificadores.get("constituicao", 0))
    if "constituicao" in {str(p).casefold() for p in profs}:
        bonus += int(ficha.get("bonus_proficiencia", 2))
    rolagem = secrets.randbelow(20) + 1
    resolucao = build_default_engine().evaluate({
        "type": "concentration_check", "concentrating": True,
        "damage": int(dano), "roll": rolagem, "constitution_modifier": bonus,
    }).outcome
    resolucao["magia"] = magia
    resolucao["rolagem"] = rolagem
    resolucao["bonus_constituicao"] = bonus
    if not resolucao.get("concentracao_mantida"):
        dados = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados["concentrando"] = None
        repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, dados)
    return resolucao


def atualizar_condicoes(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, pedido: AtualizarCondicaoPersonagem) -> dict:
    """Aplica, remove, consulta ou avança as condições de uma ficha."""
    ficha = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if ficha is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    estado = condicoes_da_ficha(ficha)
    fatos = {"estado": estado, "operation": pedido.operacao, "units": pedido.unidades}
    if pedido.operacao != "tick":
        if not pedido.condicao:
            raise HTTPException(status_code=422, detail="Informe a condição para aplicar, remover ou consultar")
        fatos["condition"] = pedido.condicao
    if pedido.operacao == "apply":
        fatos["duration"] = pedido.duracao
    try:
        resultado = build_default_engine().evaluate({"type": "condition_state", **fatos}).outcome
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if pedido.operacao in {"apply", "remove", "tick"}:
        ficha = salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
        metadados = dict(ficha.get("salvaguardas_fim_condicoes") or {})
        if pedido.operacao == "apply" and pedido.condicao:
            chave_condicao = normalizar_condicao(pedido.condicao)
            if pedido.salvaguarda_fim_turno:
                metadados[chave_condicao] = pedido.salvaguarda_fim_turno.model_dump()
            else:
                metadados.pop(chave_condicao, None)
        elif pedido.operacao == "remove" and pedido.condicao:
            metadados.pop(normalizar_condicao(pedido.condicao), None)
        elif pedido.operacao == "tick":
            metadados = {k: v for k, v in metadados.items() if normalizar_condicao(k) in estado.ativas}
        dados_ficha = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados_ficha["salvaguardas_fim_condicoes"] = metadados
        ficha = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, dados_ficha) or ficha
    return {"personagem_id": personagem_id, "condicoes_ativas": sorted(estado.ativas), "duracoes": dict(estado.duracoes), "salvaguardas_fim_condicoes": ficha.get("salvaguardas_fim_condicoes", {}), "exaustao_nivel": estado.exaustao, "resolucao": resultado}
