"""Rotas de personagens da campanha: ficha, conjuração, equipamento e condições.

Os helpers de regra (resolução de ficha, bloco derivado, condições) vivem aqui
temporariamente; a extração para ``backend/services`` é a etapa seguinte do
refactor de responsabilidades.
"""
from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from backend.dependencies import obter_jogador, obter_repositorio
from backend.persistencia import RepositorioCampanhas
from backend.routes.campanhas import _campanha_ou_404
from backend.routes.catalogo import ALIAS_PROFICIENCIA_ARMA, ARMAS_SIMPLES
from backend.schemas import (
    AtualizarCondicaoPersonagem,
    AtualizarEquipamentoPersonagem,
    AtualizarMagiasPersonagem,
    AtualizarPersonagem,
    AtualizarProficienciasPersonagem,
    NovoPersonagem,
)
from rule_engine import (
    ANTECEDENTES,
    build_default_engine,
    criar_personagem,
    ficha_personagem,
    gerar_atributos_compra_pontos,
    gerar_atributos_matriz_padrao,
)
from rule_engine.ability_checks import PERICIAS
from rule_engine.catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS
from rule_engine.character import escolha_ferramenta_do_antecedente
from rule_engine.conditions import EstadoCondicoes, normalizar_condicao, resolver_efeitos_condicao
from rule_engine.species import escolha_de_especie
from rule_engine.spellcasting import validar_escolhas_artifice
from rule_engine.spells import obter_magia

router = APIRouter()


def _exigir_escolhas_de_criacao(dados: NovoPersonagem) -> None:
    """A criação só termina quando a ficha não depende de escolhas pendentes."""
    escolha = escolha_de_especie(dados.especie)
    if escolha and not dados.heranca_draconica:
        raise HTTPException(status_code=422, detail=f"Escolha a {escolha['rotulo']} do {dados.especie}.")
    ferramenta = escolha_ferramenta_do_antecedente(dados.antecedente)
    if ferramenta and not dados.ferramenta_antecedente:
        raise HTTPException(status_code=422, detail=f"Escolha o tipo de {ferramenta['rotulo']} do antecedente {dados.antecedente}.")
    if dados.antecedente in ANTECEDENTES and not dados.equipamento_antecedente:
        raise HTTPException(status_code=422, detail="Escolha o equipamento de antecedente A ou B.")


def _resolver_ficha(dados: NovoPersonagem) -> tuple[dict, dict]:
    """Toda ficha passa pelo Rule Engine; nada é calculado no cliente."""
    try:
        if dados.metodo_atributos == "compra_pontos":
            base = gerar_atributos_compra_pontos(dados.atributos)
        else:
            base = dict(dados.atributos)
            if sorted(base.values()) != sorted(gerar_atributos_matriz_padrao().values()):
                raise ValueError("A matriz padrão usa exatamente 15, 14, 13, 12, 10 e 8")
        personagem = criar_personagem({
            "name": dados.nome,
            "species": dados.especie,
            "class": dados.classe,
            "level": dados.nivel,
            "subclass": dados.subclasse,
            "ability_scores": base,
            "background": dados.antecedente,
            "background_increases": dados.aumentos_antecedente,
            "background_feat": dados.talento_antecedente,
            **({"class_skill_proficiencies": dados.pericias_classe} if dados.pericias_classe is not None else {}),
            **({"artisan_tool_proficiency": dados.ferramenta_artesao} if dados.ferramenta_artesao is not None else {}),
            **({"heranca_draconica": dados.heranca_draconica} if dados.heranca_draconica is not None else {}),
            **({"ferramenta_antecedente": dados.ferramenta_antecedente} if dados.ferramenta_antecedente is not None else {}),
            **({"equipamento_antecedente": dados.equipamento_antecedente} if dados.equipamento_antecedente is not None else {}),
        })
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc).strip("'\"")) from exc
    if personagem.antecedente not in ANTECEDENTES:
        raise HTTPException(status_code=422, detail="Antecedente inválido")
    return dados.model_dump(), ficha_personagem(personagem)


def _personagem_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str) -> dict:
    personagem = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return personagem


def _validar_conjuracao(personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> None:
    """Nomes, círculos e progressão validada são conferidos pelo motor, nunca pelo cliente."""
    for nome_magia in truques:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") != 0:
            raise HTTPException(status_code=422, detail=f"Truque inválido: {nome_magia}")
    for nome_magia in preparadas:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") is None or magia.get("circulo") == 0:
            raise HTTPException(status_code=422, detail=f"Magia preparada inválida: {nome_magia}")
    if any(not isinstance(n, int) or n < 0 or n > 20 for n in espacos_totais.values()):
        raise HTTPException(status_code=422, detail="Quantidade de espaços inválida")
    if personagem.get("classe") == "artifice":
        try:
            validar_escolhas_artifice(
                int(personagem.get("nivel", 1)),
                int((personagem.get("atributos") or {}).get("inteligencia", 10)),
                truques, preparadas, espacos_totais,
                subclasse=personagem.get("subclasse") or personagem.get("subclass"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def _aplicar_conjuracao(repo, jogador: str, campanha_id: str, personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> dict:
    """Grava magias e espaços sem zerar os espaços já gastos se a progressão não mudou."""
    espacos = {str(circulo): int(total) for circulo, total in espacos_totais.items()}
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    anterior = personagem.get("conjuracao") or {}
    restantes_anteriores = anterior.get("espacos_restantes") or {}
    if anterior.get("espacos_totais") == espacos and restantes_anteriores:
        restantes = {c: max(0, min(total, int(restantes_anteriores.get(c, total)))) for c, total in espacos.items() if total > 0}
    else:
        restantes = {c: total for c, total in espacos.items() if total > 0}
    ficha["conjuracao"] = {"truques": truques, "magias_preparadas": preparadas,
                           "espacos_totais": espacos, "espacos_restantes": restantes}
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


def _validar_turno_ativo(estado: dict, token_id: str) -> None:
    if estado.get("combate_ativo") and estado.get("token_ativo") != token_id:
        raise HTTPException(status_code=409, detail={
            "motivo": "turno_de_outra_criatura",
            "token_ativo": estado.get("token_ativo"),
            "token_solicitado": token_id,
        })


def _condicoes_da_ficha(ficha: dict) -> EstadoCondicoes:
    return EstadoCondicoes(
        ativas=set(ficha.get("condicoes_ativas") or []),
        imunidades=set(ficha.get("imunidades_condicoes") or []),
        duracoes=dict(ficha.get("duracoes_condicoes") or {}),
        exaustao=int(ficha.get("exaustao_nivel", 0)),
    )


def _duracao_textual_expira(duracao: Any, momento: str) -> bool:
    if not isinstance(duracao, str):
        return False
    texto = duracao.casefold()
    if momento == "fim":
        return "até o fim do próximo turno" in texto or "until the end of its next turn" in texto
    return "até o início do próximo turno" in texto or "until the start of its next turn" in texto


def _expirar_duracoes_textuais_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, ficha: dict, momento: str) -> list[str]:
    estado = _condicoes_da_ficha(ficha)
    encerradas = []
    for condicao, duracao in list(estado.duracoes.items()):
        if _duracao_textual_expira(duracao, momento):
            estado.remover(condicao)
            encerradas.append(normalizar_condicao(condicao))
    if encerradas:
        _salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
    return encerradas


def _reduzir_duracoes_numericas_token(token: dict) -> list[str]:
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


def _expirar_duracoes_textuais_token(token: dict, momento: str) -> list[str]:
    duracoes = token.get("condition_durations") or {}
    condicoes = token.get("conditions") or []
    encerradas = []
    for condicao, duracao in list(duracoes.items()):
        if _duracao_textual_expira(duracao, momento):
            chave = normalizar_condicao(condicao)
            token["conditions"] = [c for c in condicoes if normalizar_condicao(c) != chave]
            condicoes = token["conditions"]
            duracoes.pop(condicao, None)
            encerradas.append(chave)
    token["condition_durations"] = duracoes
    return encerradas


def _salvar_condicoes_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem: dict, estado: EstadoCondicoes) -> dict:
    dados = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    dados["condicoes_ativas"] = sorted(estado.ativas)
    dados["imunidades_condicoes"] = sorted(estado.imunidades)
    dados["duracoes_condicoes"] = dict(estado.duracoes)
    dados["exaustao_nivel"] = estado.exaustao
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], dados)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


def _resolver_concentracao_apos_dano(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dano: int) -> dict | None:
    """Aplica a salvaguarda de concentração ao dano real recebido pelo personagem."""
    ficha = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if not ficha:
        return None
    magia = ficha.get("concentrando")
    if not magia:
        return {"resultado": "não_concentrando", "concentracao_mantida": False}
    estado = _condicoes_da_ficha(ficha)
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


def _calcular_ca_ficha(personagem: dict) -> int:
    mods = personagem.get("modificadores") or {}
    dex = int(mods.get("destreza", 0))
    equipamento = personagem.get("equipamento") or {}
    nome_armadura = equipamento.get("armadura")
    if nome_armadura:
        armadura = CATALOGO_ARMADURAS[nome_armadura]
        categoria = armadura["categoria"]
        if categoria == "leve":
            ca = int(armadura["ca"]) + dex
        elif categoria == "media":
            ca = int(armadura["ca"]) + min(2, dex)
        elif categoria == "pesada":
            ca = int(armadura["ca"])
        else:
            ca = 10 + dex
    else:
        ca = 10 + dex
    if equipamento.get("escudo") or (nome_armadura and CATALOGO_ARMADURAS[nome_armadura]["categoria"] == "escudo"):
        ca += 2
    return ca


# Atributo de conjuração por classe, conforme declarado pelo próprio motor:
# rule_engine/spellcasters.py (mago, clérigo, druida, bardo),
# rule_engine/advanced_casters.py (bruxo, feiticeiro, guardião, paladino) e
# rule_engine/class_features.py (artífice). Classes sem conjuração ficam fora do mapa.
ATRIBUTO_CONJURACAO_CLASSE = {
    "mago": "inteligencia",
    "artifice": "inteligencia",
    "clerigo": "sabedoria",
    "druida": "sabedoria",
    "guardiao": "sabedoria",
    "bardo": "carisma",
    "bruxo": "carisma",
    "feiticeiro": "carisma",
    "paladino": "carisma",
}

ALCANCE_CORPO_A_CORPO_PES = 5
ALCANCE_EXTENSAO_PES = 10


def _pes(metros: float) -> int:
    """Converte o alcance do catálogo (metros) para pés, como o mapa tático usa."""
    return max(ALCANCE_CORPO_A_CORPO_PES, round(float(metros) * 3.28084))


def _proficiente_com_arma(personagem: dict, nome_arma: str) -> bool:
    profs = personagem.get("proficiencias_classe") or {}
    if not isinstance(profs, dict):
        return False
    conhecidas = set(profs.get("armas", []))
    categoria = "simples" if nome_arma in ARMAS_SIMPLES else "marciais"
    return categoria in conhecidas or ALIAS_PROFICIENCIA_ARMA.get(nome_arma) in conhecidas


def _resolver_arma_ficha(personagem: dict, nome_arma: str | None) -> dict:
    """Bônus de ataque e dano a partir do catálogo oficial e dos modificadores da ficha.

    Armas de munição usam Destreza; as demais usam Força, ou Destreza quando a
    arma tem Acuidade e o modificador de Destreza é maior.
    """
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    forca = int(mods.get("forca", 0))
    destreza = int(mods.get("destreza", 0))
    if not nome_arma:
        sinal_negativo = "\u2212"
        return {
            "nome": None, "desarmado": True, "catalogo": False, "proficiente": True,
            "atributo": "forca", "modificador": forca, "ataque": proficiencia + forca,
            "dado": None, "modificador_dano": forca,
            "expressao_dano": "1 {} {}".format("+" if forca >= 0 else sinal_negativo, abs(forca)),
            "dano_medio": max(0, 1 + forca), "tipo": "contundente",
            "alcance_pes": ALCANCE_CORPO_A_CORPO_PES, "propriedades": [],
            "a_distancia": False, "arremesso": False,
        }
    arma = CATALOGO_ARMAS.get(nome_arma)
    if arma is None:
        return {"nome": nome_arma, "catalogo": False, "proficiente": False, "erro": "arma_fora_do_catalogo"}
    propriedades = list(arma.get("propriedades") or [])
    conjunto = set(propriedades)
    atributo = "destreza" if "municao" in conjunto or ("acuidade" in conjunto and destreza > forca) else "forca"
    modificador = destreza if atributo == "destreza" else forca
    a_distancia = "municao" in conjunto
    alcance_pes = _pes(arma.get("alcance", 0)) if a_distancia or "arremesso" in conjunto else (
        ALCANCE_EXTENSAO_PES if "extensao" in conjunto else ALCANCE_CORPO_A_CORPO_PES
    )
    quantidade, lados = (int(parte) for parte in str(arma["dano"]).lower().split("d"))
    dano_medio = int(quantidade * (lados + 1) / 2) + modificador
    sinal = "+" if modificador >= 0 else "−"
    return {
        "nome": nome_arma, "desarmado": False, "catalogo": True,
        "proficiente": _proficiente_com_arma(personagem, nome_arma),
        "atributo": atributo, "modificador": modificador,
        "ataque": proficiencia + modificador,
        "dado": arma["dano"], "modificador_dano": modificador,
        "expressao_dano": f"{arma['dano']} {sinal} {abs(modificador)}",
        "dano_medio": max(0, dano_medio), "tipo": arma["tipo"],
        "alcance_pes": alcance_pes, "propriedades": propriedades,
        "a_distancia": a_distancia, "arremesso": "arremesso" in conjunto,
    }


def _bloco_salvaguardas(personagem: dict) -> list[dict]:
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    proficientes = set(personagem.get("proficiencias_salvaguarda") or [])
    linhas = []
    for atributo in ("forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"):
        base = int(mods.get(atributo, 0))
        proficiente = atributo in proficientes
        linhas.append({
            "atributo": atributo, "proficiente": proficiente,
            "modificador": base, "total": base + (proficiencia if proficiente else 0),
        })
    return linhas


def _bloco_pericias(personagem: dict) -> list[dict]:
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    proficientes = set(personagem.get("pericias") or [])
    linhas = []
    for pericia, atributo in PERICIAS.items():
        base = int(mods.get(atributo, 0))
        proficiente = pericia in proficientes
        linhas.append({
            "pericia": pericia, "atributo": atributo, "proficiente": proficiente,
            "modificador": base, "total": base + (proficiencia if proficiente else 0),
        })
    linhas.sort(key=lambda linha: (-int(linha["proficiente"]), linha["pericia"]))
    return linhas


def _bloco_conjuracao(personagem: dict) -> dict | None:
    atributo = ATRIBUTO_CONJURACAO_CLASSE.get(str(personagem.get("classe") or "").lower())
    if not atributo:
        return None
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    modificador = int(mods.get(atributo, 0))
    return {
        "atributo": atributo, "modificador": modificador,
        "cd": 8 + proficiencia + modificador, "ataque": proficiencia + modificador,
    }


def _bloco_ficha(personagem: dict) -> dict:
    """Valores derivados calculados pelo servidor para exibição da ficha.

    Nada aqui é inventado pelo cliente: CA, ataque, dano, salvaguardas e perícias
    saem do catálogo oficial somados aos modificadores já validados pelo motor.
    """
    equipamento = personagem.get("equipamento") or {}
    armadura = CATALOGO_ARMADURAS.get(equipamento.get("armadura") or "")
    return {
        "fonte": "rule_engine",
        "ca": _calcular_ca_ficha(personagem),
        "iniciativa": int((personagem.get("modificadores") or {}).get("destreza", 0)),
        "bonus_proficiencia": int(personagem.get("bonus_proficiencia") or 2),
        "arma": _resolver_arma_ficha(personagem, equipamento.get("arma")),
        "armadura": {
            "nome": equipamento.get("armadura"), "escudo": bool(equipamento.get("escudo")),
            "categoria": armadura["categoria"] if armadura else None,
            "ca_base": armadura["ca"] if armadura else None,
        },
        "conjuracao": _bloco_conjuracao(personagem),
        "salvaguardas": _bloco_salvaguardas(personagem),
        "pericias": _bloco_pericias(personagem),
    }


def _com_bloco(personagem: dict) -> dict:
    """Anexa o bloco derivado à ficha devolvida pelas rotas de personagem."""
    if not isinstance(personagem, dict):
        return personagem
    return {**personagem, "bloco": _bloco_ficha(personagem)}


@router.get("/v1/campanhas/{campanha_id}/personagens")
def listar_personagens(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    grupo = repo.listar_personagens(jogador, campanha_id)
    if grupo is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return [_com_bloco(p) for p in grupo]


@router.post("/v1/campanhas/{campanha_id}/personagens", status_code=201)
def criar_personagem_campanha(
    campanha_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    _exigir_escolhas_de_criacao(dados)
    entrada, ficha = _resolver_ficha(dados)
    escolhas = None
    if dados.magias_iniciais:
        truques = list(dict.fromkeys(dados.magias_iniciais.truques))
        preparadas = list(dict.fromkeys(dados.magias_iniciais.magias_preparadas))
        if len(truques) != len(dados.magias_iniciais.truques) or len(preparadas) != len(dados.magias_iniciais.magias_preparadas):
            raise HTTPException(status_code=422, detail="Não repita magias na ficha")
        _validar_conjuracao(ficha, truques, preparadas, dados.magias_iniciais.espacos_totais)
        escolhas = (truques, preparadas, dados.magias_iniciais.espacos_totais)
    personagem = repo.criar_personagem(jogador, campanha_id, entrada, ficha)
    if escolhas:
        personagem = _aplicar_conjuracao(repo, jogador, campanha_id, personagem, *escolhas)
    return _com_bloco(personagem)


@router.get("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def obter_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return _com_bloco(_personagem_ou_404(repo, jogador, campanha_id, personagem_id))


@router.put("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def substituir_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    _exigir_escolhas_de_criacao(dados)
    entrada, ficha = _resolver_ficha(dados)
    return _com_bloco(repo.atualizar_personagem(jogador, campanha_id, personagem_id, entrada=entrada, ficha=ficha))


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def atualizar_pv_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    atualizado = repo.ajustar_pv_personagem(jogador, campanha_id, personagem_id, dados.ajuste_pv)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return _com_bloco(atualizado)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/proficiencias")
def atualizar_proficiencias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarProficienciasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    entrada = dict(personagem.get("entrada") or {})
    entrada["pericias_classe"] = dados.pericias_classe
    entrada["ferramenta_artesao"] = dados.ferramenta_artesao
    for campo in ("heranca_draconica", "ferramenta_antecedente", "equipamento_antecedente"):
        valor = getattr(dados, campo)
        if valor is not None:
            entrada[campo] = valor
    try:
        novo = NovoPersonagem.model_validate(entrada)
        nova_entrada, nova_ficha = _resolver_ficha(novo)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for chave in ("conjuracao", "equipamento"):
        if personagem.get(chave):
            nova_ficha[chave] = personagem[chave]
    atualizado = repo.atualizar_personagem(
        jogador, campanha_id, personagem_id, entrada=nova_entrada, ficha=nova_ficha
    )
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return _com_bloco(atualizado)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/equipamento")
def atualizar_equipamento_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarEquipamentoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    if dados.arma is not None and dados.arma not in CATALOGO_ARMAS:
        raise HTTPException(status_code=422, detail="Arma não encontrada no catálogo")
    if dados.armadura is not None and dados.armadura not in CATALOGO_ARMADURAS:
        raise HTTPException(status_code=422, detail="Armadura não encontrada no catálogo")
    profs = personagem.get("proficiencias_classe") or {}
    armaduras = set(profs.get("armaduras", [])) if isinstance(profs, dict) else set()
    if dados.armadura:
        categoria = CATALOGO_ARMADURAS[dados.armadura]["categoria"]
        if categoria == "escudo":
            raise HTTPException(status_code=422, detail="Registre escudos no campo escudo, não como armadura")
        categoria_normalizada = {"media": "medias", "leve": "leves", "pesada": "pesadas"}.get(categoria, categoria)
        if categoria_normalizada not in armaduras and categoria not in armaduras:
            raise HTTPException(status_code=422, detail="A ficha não registra proficiência nesta categoria de armadura")
    if dados.escudo and "escudos" not in armaduras:
        raise HTTPException(status_code=422, detail="A ficha não registra proficiência com escudos")
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    ficha["equipamento"] = {"arma": dados.arma, "armadura": dados.armadura, "escudo": dados.escudo}
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return _com_bloco(atualizado)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/magias")
def atualizar_magias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarMagiasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    truques = list(dict.fromkeys(dados.truques))
    preparadas = list(dict.fromkeys(dados.magias_preparadas))
    if len(truques) != len(dados.truques) or len(preparadas) != len(dados.magias_preparadas):
        raise HTTPException(status_code=422, detail="Não repita magias na ficha")
    _validar_conjuracao(personagem, truques, preparadas, dados.espacos_totais)
    return _com_bloco(_aplicar_conjuracao(repo, jogador, campanha_id, personagem, truques, preparadas, dados.espacos_totais))


@router.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/descanso-longo")
def recuperar_espacos_descanso_longo(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    ficha = {
        k: v for k, v in personagem.items()
        if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}
    }
    conjuracao = dict(ficha.get("conjuracao") or {})
    totais = {str(k): int(v) for k, v in (conjuracao.get("espacos_totais") or {}).items() if int(v) > 0}
    conjuracao["espacos_restantes"] = dict(totais)
    ficha["conjuracao"] = conjuracao
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return _com_bloco(atualizado)


@router.delete("/v1/campanhas/{campanha_id}/personagens/{personagem_id}", status_code=204)
def apagar_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar_personagem(jogador, campanha_id, personagem_id):
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return Response(status_code=204)


@router.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/condicoes")
def atualizar_condicoes_personagem(
    campanha_id: str,
    personagem_id: str,
    pedido: AtualizarCondicaoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    ficha = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    estado = _condicoes_da_ficha(ficha)
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
        ficha = _salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
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
