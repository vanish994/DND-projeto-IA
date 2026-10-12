"""Casos de uso de personagem: ficha, proficiências, equipamento e conjuração.

Toda ficha passa pelo Rule Engine (``resolver_ficha``); nada é calculado no
cliente. As funções públicas são os casos de uso chamados pelas rotas.
"""
from __future__ import annotations

from fastapi import HTTPException

from backend.persistencia import RepositorioCampanhas
from backend.schemas import (
    AtualizarEquipamentoPersonagem,
    AtualizarMagiasPersonagem,
    AtualizarProficienciasPersonagem,
    NovoPersonagem,
)
from backend.services.bloco_ficha import com_bloco
from rule_engine import (
    ANTECEDENTES,
    criar_personagem as criar_personagem_no_motor,
    ficha_personagem,
    gerar_atributos_compra_pontos,
    gerar_atributos_matriz_padrao,
)
from rule_engine.catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS
from rule_engine.character import escolha_ferramenta_do_antecedente
from rule_engine.species import escolha_de_especie
from rule_engine.spellcasting import validar_escolhas_artifice
from rule_engine.spells import obter_magia

_CAMPOS_PERSISTENCIA = {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}


def exigir_escolhas_de_criacao(dados: NovoPersonagem) -> None:
    """A criação só termina quando a ficha não depende de escolhas pendentes."""
    escolha = escolha_de_especie(dados.especie)
    if escolha and not dados.heranca_draconica:
        raise HTTPException(status_code=422, detail=f"Escolha a {escolha['rotulo']} do {dados.especie}.")
    ferramenta = escolha_ferramenta_do_antecedente(dados.antecedente)
    if ferramenta and not dados.ferramenta_antecedente:
        raise HTTPException(status_code=422, detail=f"Escolha o tipo de {ferramenta['rotulo']} do antecedente {dados.antecedente}.")
    if dados.antecedente in ANTECEDENTES and not dados.equipamento_antecedente:
        raise HTTPException(status_code=422, detail="Escolha o equipamento de antecedente A ou B.")


def resolver_ficha(dados: NovoPersonagem) -> tuple[dict, dict]:
    """Toda ficha passa pelo Rule Engine; nada é calculado no cliente."""
    try:
        if dados.metodo_atributos == "compra_pontos":
            base = gerar_atributos_compra_pontos(dados.atributos)
        else:
            base = dict(dados.atributos)
            if sorted(base.values()) != sorted(gerar_atributos_matriz_padrao().values()):
                raise ValueError("A matriz padrão usa exatamente 15, 14, 13, 12, 10 e 8")
        personagem = criar_personagem_no_motor({
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


def personagem_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str) -> dict:
    personagem = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return personagem


def validar_conjuracao(personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> None:
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


def aplicar_conjuracao(repo, jogador: str, campanha_id: str, personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> dict:
    """Grava magias e espaços sem zerar os espaços já gastos se a progressão não mudou."""
    espacos = {str(circulo): int(total) for circulo, total in espacos_totais.items()}
    ficha = {k: v for k, v in personagem.items() if k not in _CAMPOS_PERSISTENCIA}
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


def criar_personagem(repo: RepositorioCampanhas, jogador: str, campanha_id: str, dados: NovoPersonagem) -> dict:
    exigir_escolhas_de_criacao(dados)
    entrada, ficha = resolver_ficha(dados)
    escolhas = None
    if dados.magias_iniciais:
        truques = list(dict.fromkeys(dados.magias_iniciais.truques))
        preparadas = list(dict.fromkeys(dados.magias_iniciais.magias_preparadas))
        if len(truques) != len(dados.magias_iniciais.truques) or len(preparadas) != len(dados.magias_iniciais.magias_preparadas):
            raise HTTPException(status_code=422, detail="Não repita magias na ficha")
        validar_conjuracao(ficha, truques, preparadas, dados.magias_iniciais.espacos_totais)
        escolhas = (truques, preparadas, dados.magias_iniciais.espacos_totais)
    personagem = repo.criar_personagem(jogador, campanha_id, entrada, ficha)
    if escolhas:
        personagem = aplicar_conjuracao(repo, jogador, campanha_id, personagem, *escolhas)
    return com_bloco(personagem)


def substituir_personagem(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dados: NovoPersonagem) -> dict:
    personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    exigir_escolhas_de_criacao(dados)
    entrada, ficha = resolver_ficha(dados)
    return com_bloco(repo.atualizar_personagem(jogador, campanha_id, personagem_id, entrada=entrada, ficha=ficha))


def ajustar_pv(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, ajuste_pv: int) -> dict:
    personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    atualizado = repo.ajustar_pv_personagem(jogador, campanha_id, personagem_id, ajuste_pv)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return com_bloco(atualizado)


def atualizar_proficiencias(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dados: AtualizarProficienciasPersonagem) -> dict:
    personagem = personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    entrada = dict(personagem.get("entrada") or {})
    entrada["pericias_classe"] = dados.pericias_classe
    entrada["ferramenta_artesao"] = dados.ferramenta_artesao
    for campo in ("heranca_draconica", "ferramenta_antecedente", "equipamento_antecedente"):
        valor = getattr(dados, campo)
        if valor is not None:
            entrada[campo] = valor
    try:
        novo = NovoPersonagem.model_validate(entrada)
        nova_entrada, nova_ficha = resolver_ficha(novo)
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
    return com_bloco(atualizado)


def atualizar_equipamento(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dados: AtualizarEquipamentoPersonagem) -> dict:
    personagem = personagem_ou_404(repo, jogador, campanha_id, personagem_id)
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
    ficha = {k: v for k, v in personagem.items() if k not in _CAMPOS_PERSISTENCIA}
    ficha["equipamento"] = {"arma": dados.arma, "armadura": dados.armadura, "escudo": dados.escudo}
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return com_bloco(atualizado)


def atualizar_magias(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dados: AtualizarMagiasPersonagem) -> dict:
    personagem = personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    truques = list(dict.fromkeys(dados.truques))
    preparadas = list(dict.fromkeys(dados.magias_preparadas))
    if len(truques) != len(dados.truques) or len(preparadas) != len(dados.magias_preparadas):
        raise HTTPException(status_code=422, detail="Não repita magias na ficha")
    validar_conjuracao(personagem, truques, preparadas, dados.espacos_totais)
    return com_bloco(aplicar_conjuracao(repo, jogador, campanha_id, personagem, truques, preparadas, dados.espacos_totais))


def descanso_longo(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str) -> dict:
    personagem = personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    ficha = {k: v for k, v in personagem.items() if k not in _CAMPOS_PERSISTENCIA}
    conjuracao = dict(ficha.get("conjuracao") or {})
    totais = {str(k): int(v) for k, v in (conjuracao.get("espacos_totais") or {}).items() if int(v) > 0}
    conjuracao["espacos_restantes"] = dict(totais)
    ficha["conjuracao"] = conjuracao
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return com_bloco(atualizado)
