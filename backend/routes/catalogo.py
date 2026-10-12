"""Rotas de catálogo: opções de ficha, equipamento, magias e conjuração.

Tudo aqui é leitura do Rule Engine; nada é estimado no cliente.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from backend.erros import ErroDeValidacao
from backend.services.bloco_ficha import ALIAS_PROFICIENCIA_ARMA, ARMAS_SIMPLES
from rule_engine import (
    ANTECEDENTES,
    CLASSES,
    ESPECIES,
    gerar_atributos_matriz_padrao,
)
from rule_engine.ability_checks import PERICIAS
from rule_engine.catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS, INSTRUMENTOS_MUSICAIS, KITS_DE_JOGOS
from rule_engine.character import (
    FERRAMENTAS_ARTESAO,
    PERICIAS_CLASSE_OPCOES,
    QUANTIDADE_PERICIAS_CLASSE,
    escolha_ferramenta_do_antecedente,
)
from rule_engine.feats import DARK_GIFT_FEATS, ORIGIN_FEATS
from rule_engine.spellcasters import CASTING_ABILITY, resolver_progressao_conjuracao
from rule_engine.spellcasting import listar_magias_artifice, progresso_artifice
from rule_engine.spells import listar_magias, suporte_magia
from rule_engine.species import ESCOLHAS_ESPECIE, HERANCA_DRACONICA

router = APIRouter()


@router.get("/v1/catalogo/personagens")
def catalogo_personagens() -> dict:
    return {
        "especies": ESPECIES,
        "classes": CLASSES,
        "antecedentes": ANTECEDENTES,
        "talentos_origem": sorted(ORIGIN_FEATS),
        "dadivas_sombrias": sorted(DARK_GIFT_FEATS),
        "pericias_classe_opcoes": {classe: sorted(opcoes) for classe, opcoes in PERICIAS_CLASSE_OPCOES.items()},
        "quantidade_pericias_classe": dict(QUANTIDADE_PERICIAS_CLASSE),
        "ferramentas_artesao": sorted(FERRAMENTAS_ARTESAO),
        "escolhas_especie": {
            especie: {"rotulo": escolha["rotulo"], "nota": escolha["nota"], "opcoes": [
                {"chave": chave, "nome": dados["nome"], "dano": dados["dano"]}
                for chave, dados in escolha["opcoes"].items()
            ]}
            for especie, escolha in ESCOLHAS_ESPECIE.items()
        },
        "heranca_draconica": HERANCA_DRACONICA,
        "ferramentas_antecedente": {
            antecedente: escolha_ferramenta_do_antecedente(antecedente)
            for antecedente in ANTECEDENTES
            if escolha_ferramenta_do_antecedente(antecedente)
        },
        "instrumentos_musicais": INSTRUMENTOS_MUSICAIS,
        "kits_de_jogos": KITS_DE_JOGOS,
        "atributo_conjuracao": {"artifice": "inteligencia", **CASTING_ABILITY},
        "matriz_padrao": sorted(gerar_atributos_matriz_padrao().values(), reverse=True),
        "compra_pontos": {"total": 27, "custos": {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}},
    }


@router.get("/v1/catalogo/equipamento")
def catalogo_equipamento() -> dict:
    """Catálogo oficial de armas e armaduras para a ficha não manter listas próprias."""
    return {
        "armas": {nome: dict(dados) for nome, dados in CATALOGO_ARMAS.items()},
        "armaduras": {nome: dict(dados) for nome, dados in CATALOGO_ARMADURAS.items()},
        "pericias_atributo": dict(PERICIAS),
        "arma_simples": sorted(ARMAS_SIMPLES),
        "alias_proficiencia_arma": dict(ALIAS_PROFICIENCIA_ARMA),
        "fonte": "Livro do Jogador 2024 — catálogos do Rule Engine",
    }


@router.get("/v1/catalogo/magias")
def catalogo_magias(
    classe: str | None = Query(default=None, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
) -> list[dict]:
    classe_normalizada = (classe or "").strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada in {"artifice", "artífice"}:
        magias = listar_magias_artifice(nivel)
    else:
        magias = listar_magias()
    return [{**m, "suporte": suporte_magia(m["nome"])} for m in magias]


@router.get("/v1/catalogo/conjuracao")
def catalogo_conjuracao(
    classe: str = Query(min_length=1, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
    inteligencia: int = Query(default=10, ge=1, le=30),
    sabedoria: int = Query(default=10, ge=1, le=30),
    carisma: int = Query(default=10, ge=1, le=30),
) -> dict:
    """Progressão de conjuração calculada pelo motor; nada é estimado no cliente."""
    classe_normalizada = classe.strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada in {"artifice", "artífice"}:
        try:
            progresso = progresso_artifice(nivel, inteligencia)
        except ValueError as exc:
            raise ErroDeValidacao(str(exc)) from exc
        return {**progresso, "validacao_escolhas": True}
    progresso = resolver_progressao_conjuracao({
        "classe": classe_normalizada,
        "nivel": nivel,
        "inteligencia": inteligencia,
        "sabedoria": sabedoria,
        "carisma": carisma,
    })
    if progresso.get("resultado") != "resolvido":
        return {"resultado": "nao_implementado", "motivo": progresso.get("motivo") or "progressao_de_conjuracao_ainda_nao_validada_para_esta_classe"}
    espacos = {str(indice + 1): total for indice, total in enumerate(progresso["espacos"]) if total}
    return {
        "resultado": "resolvido",
        "classe": classe_normalizada,
        "nivel": nivel,
        "atributo_conjuracao": progresso["atributo_conjuracao"],
        "truques": progresso["truques"],
        "magias_preparadas": progresso["magias_preparadas"],
        "circulo_maximo": max((int(circulo) for circulo in espacos), default=0),
        "espacos_totais": espacos,
        "validacao_escolhas": False,
    }
