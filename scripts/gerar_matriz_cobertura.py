"""Gera inventário auditável, não um percentual de regras corretas.

python scripts/gerar_matriz_cobertura.py
Probes usam apenas resolvedores puros. Nenhuma campanha ou provedor é acessado.
Referências a testes são correspondências textuais AST, não prova de cobertura.
"""

from __future__ import annotations

import ast
import csv
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rule_engine.backgrounds import ANTECEDENTES
from rule_engine.character import ESPECIES
from rule_engine.class_features import resolver_caracteristica
from rule_engine.class_progression import FEATURES_BY_CLASS, SUBCLASSES_BY_CLASS
from rule_engine.economy import ITENS_MAGICOS
from rule_engine.feats import FEATS, resolver_talento
from rule_engine.martial_subclasses import SUBCLASS_FEATURES, resolver_subclasse_marcial
from rule_engine.spells import listar_magias, resolver_magia, suporte_magia


def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto).casefold())
    return "_".join(
        "".join(c for c in texto if not unicodedata.combining(c)).replace("_", " ").replace("-", " ").split()
    )


def indice_testes():
    indice = defaultdict(set)
    for path in sorted((ROOT / "tests").glob("test_*.py")):
        if path.name == "test_matriz_cobertura.py":
            continue  # Não indexar testes do inventário como pistas de mecânica.
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("test_"):
                continue
            for literal in ast.walk(node):
                if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                    indice[normalizar(literal.value)].add(f"{path.relative_to(ROOT)}:{node.lineno}::{node.name}")
    return indice


# Rotas já existentes a inspecionar ANTES de implementar um segundo resolvedor.
# São referências manuais explícitas, não equivalência automática de comportamento.
ROTAS = {
    "furia": "rule_engine/martial.py::resolver_furia",
    "ataque_extra": "rule_engine/martial.py::resolver_ataque_extra",
    "dois_ataques_extras": "rule_engine/martial.py::resolver_ataque_extra",
    "tres_ataques_extras": "rule_engine/martial.py::resolver_ataque_extra",
    "maestria_em_arma": "rule_engine/martial.py::resolver_maestria_arma",
    "ataque_furtivo": "rule_engine/martial.py::resolver_ataque_furtivo",
    "recuperar_folego": "rule_engine/martial.py::resolver_recuperar_folego",
    "foco_do_monge": "rule_engine/martial.py::resolver_foco_monge",
    "defletir_ataques": "rule_engine/martial.py::resolver_defletir_ataques",
    "esquiva_sobrenatural": "rule_engine/martial.py::resolver_esquiva_sobrenatural",
    "evasao": "rule_engine/martial.py::resolver_evasao",
    "conjuracao": "rule_engine/spellcasters.py::resolver_progressao_conjuracao; rule_engine/spellcasting.py::progresso_artifice; rule_engine/advanced_casters.py",
    "inspiracao_de_bardo": "rule_engine/spellcasters.py::resolver_inspiracao_bardo",
    "canalizar_divindade": "rule_engine/spellcasters.py::resolver_canalizar_divindade",
    "forma_selvagem": "rule_engine/spellcasters.py::resolver_forma_selvagem",
    "livro_de_magias": "rule_engine/spellcasters.py::resolver_livro_de_magias",
    "recuperacao_arcana": "rule_engine/spellcasters.py::resolver_livro_de_magias (acao=recuperacao_arcana)",
    "memorizar_magia": "rule_engine/spellcasters.py::resolver_livro_de_magias (acao=memorizar)",
    "magia_de_pacto": "rule_engine/advanced_casters.py::resolver_bruxo",
    "invocacoes_misticas": "rule_engine/warlock_invocations.py; rule_engine/advanced_casters.py::resolver_bruxo",
    "astucia_magica": "rule_engine/advanced_casters.py::resolver_bruxo",
    "arcana_mistica": "rule_engine/advanced_casters.py::resolver_bruxo",
    "fonte_de_magia": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "metamagia": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "feiticaria_inata": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "restauracao_feiticeira": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "feiticaria_encarnada": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "apoteose_arcana": "rule_engine/advanced_casters.py::resolver_feiticeiro",
    "inimigo_favorito": "rule_engine/advanced_casters.py::resolver_guardiao",
    "explorador_habil": "rule_engine/advanced_casters.py::resolver_guardiao",
    "incansavel": "rule_engine/advanced_casters.py::resolver_guardiao",
    "veu_da_natureza": "rule_engine/advanced_casters.py::resolver_guardiao",
    "predador_implacavel": "rule_engine/advanced_casters.py::resolver_guardiao",
    "maos_consagradas": "rule_engine/advanced_casters.py::resolver_paladino",
    "destruicao_do_paladino": "rule_engine/advanced_casters.py::resolver_paladino",
}


def probe(resolver, fatos):
    try:
        return resolver(dict(fatos))
    except (KeyError, ValueError, TypeError) as error:
        return {"resultado": "probe_exige_outros_dados", "erro": f"{type(error).__name__}: {error}"}


def gerar_linhas():
    testes = indice_testes()
    rows = []

    def add(familia, grupo, recurso, fonte, **extra):
        row = dict(
            familia=familia,
            grupo=grupo,
            recurso=recurso,
            niveis="",
            fonte=fonte,
            catalogo="presente",
            retorno_probe="nao_executado",
            fatos_probe="",
            evidencia="",
            rotas_relacionadas="",
            integracao="nao_comprovada_por_este_inventario",
            lacuna="Validar requisitos, aplicação, consumo, recuperação e persistência.",
            prioridade="P1",
            referencias_testes="; ".join(sorted(testes.get(normalizar(recurso), []))),
        )
        row.update(extra)
        rows.append(row)

    for classe, niveis in sorted(FEATURES_BY_CLASS.items()):
        features = defaultdict(list)
        for nivel, nomes in sorted(niveis.items()):
            for nome in nomes:
                features[nome].append(nivel)
        for nome, levels in sorted(features.items()):
            fatos = dict(classe=classe, nivel=min(levels), recurso=normalizar(nome))
            result = probe(resolver_caracteristica, fatos)
            abaixo = probe(resolver_caracteristica, {**fatos, "nivel": min(levels) - 1}) if min(levels) > 1 else None
            falha_nivel = abaixo and abaixo.get("resultado") not in {
                "bloqueado",
                "nao_implementado",
                "probe_exige_outros_dados",
                "requer_caracteristica",
            }
            add(
                "caracteristica_classe",
                classe,
                nome,
                "rule_engine/class_progression.py; rule_engine/class_features.py::resolver_caracteristica",
                niveis=",".join(map(str, levels)),
                retorno_probe=result.get("resultado"),
                fatos_probe=json.dumps(fatos, ensure_ascii=False),
                evidencia=json.dumps({"no_desbloqueio": result, "um_nivel_antes": abaixo}, ensure_ascii=False),
                rotas_relacionadas=ROTAS.get(normalizar(nome), ""),
                prioridade="P0" if falha_nivel else "P1",
                lacuna=(
                    "Probe aceita recurso antes do marco da própria matriz; confirmar fonte e centralizar validação. "
                    if falha_nivel
                    else ""
                )
                + "Não confundir retorno do resolvedor genérico com cobertura das rotas alternativas ou estado persistido.",
            )

    for classe, subclasses in sorted(SUBCLASSES_BY_CLASS.items()):
        for nome in sorted(subclasses):
            add(
                "subclasse_catalogo",
                classe,
                nome,
                "rule_engine/class_progression.py::SUBCLASSES_BY_CLASS",
                evidencia=(
                    "Possui tabela marcial"
                    if nome in SUBCLASS_FEATURES
                    else "Não possui entrada em SUBCLASS_FEATURES; não exclui rotas em outros módulos."
                ),
                rotas_relacionadas="rule_engine/martial_subclasses.py; rule_engine/spellcasters.py; rule_engine/advanced_casters.py",
            )
    for subclasse, niveis in sorted(SUBCLASS_FEATURES.items()):
        features = defaultdict(list)
        for nivel, nomes in sorted(niveis.items()):
            for nome in nomes:
                features[nome].append(nivel)
        for nome, levels in sorted(features.items()):
            fatos = dict(subclasse=subclasse, nivel=min(levels), caracteristica=nome)
            result = probe(resolver_subclasse_marcial, fatos)
            add(
                "caracteristica_subclasse",
                subclasse,
                nome,
                "rule_engine/martial_subclasses.py::resolver_subclasse_marcial",
                niveis=",".join(map(str, levels)),
                retorno_probe=result.get("resultado"),
                fatos_probe=json.dumps(fatos, ensure_ascii=False),
                evidencia=json.dumps(result, ensure_ascii=False),
            )

    for nome, meta in sorted(FEATS.items()):
        fatos = dict(
            talento=nome,
            nivel=max(1, meta.get("nivel", 1)),
            campanha_ravenloft=True,
            caracteristica_conjuracao=True,
            forca=13,
            destreza=13,
        )
        result = probe(resolver_talento, fatos)
        add(
            "talento",
            meta["categoria"],
            nome,
            "rule_engine/feats.py::resolver_talento",
            niveis=str(fatos["nivel"]),
            retorno_probe=result.get("resultado"),
            fatos_probe=json.dumps(fatos, ensure_ascii=False),
            evidencia=json.dumps(result, ensure_ascii=False),
            integracao=(
                "PV máximos em rule_engine/character.py::ficha_personagem"
                if nome == "vigoroso"
                else "nao_comprovada_por_este_inventario"
            ),
        )

    for nome in sorted(ESPECIES):
        add(
            "especie",
            "criacao",
            nome,
            "rule_engine/character.py::ESPECIES",
            prioridade="P2",
            integracao=(
                "Criação e ficha; Draconato também tem sopro no chat"
                if nome == "draconato"
                else "Criação e campos básicos da ficha"
            ),
            rotas_relacionadas=(
                "rule_engine/species.py; orchestrator/preparo.py::resolver_ataque_de_sopro"
                if nome == "draconato"
                else ""
            ),
            lacuna="Inventário é por espécie, não por todos os traços do livro; faltam provas de usos, recarga e efeitos de cada traço.",
        )
    for nome in sorted(ANTECEDENTES):
        add(
            "antecedente",
            "criacao",
            nome,
            "rule_engine/backgrounds.py; rule_engine/character.py",
            prioridade="P2",
            integracao="Criação: atributos, perícias, escolhas de ferramentas/equipamento e talento registrado.",
            lacuna="Registro de talento não implica execução de seus efeitos; conferir cada opção.",
        )
    for magia in listar_magias():
        nome = magia["nome"]
        fatos = {"magia": nome}
        result = probe(resolver_magia, fatos)
        suporte = suporte_magia(nome)
        add(
            "magia",
            "truque" if magia["circulo"] == 0 else "circulo_" + str(magia["circulo"]),
            nome,
            "rule_engine/spells.py::resolver_magia",
            retorno_probe=result.get("resultado"),
            fatos_probe=json.dumps(fatos, ensure_ascii=False),
            evidencia=json.dumps(suporte, ensure_ascii=False),
            integracao=suporte["rotulo"],
            lacuna="Conferir efeito completo e edição; mapa restrito a Artífice; chat e persistência são etapas distintas.",
        )
    for nome, item in sorted(ITENS_MAGICOS.items()):
        add(
            "item_magico",
            "economia",
            nome,
            "rule_engine/economy.py::usar_item_magico",
            evidencia=json.dumps(item, ensure_ascii=False),
            integracao="Resolvedor devolve identificador de efeito; não comprova aplicação/persistência.",
            lacuna="Executar efeito e registrar consumo/cargas/sintonia na ficha; não repetir catálogo.",
        )
    return rows


def main():
    rows = gerar_linhas()
    path = ROOT / "docs/matriz_cobertura.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(
        json.dumps(
            {
                "arquivo": str(path.relative_to(ROOT)),
                "linhas": len(rows),
                "familias": dict(Counter(r["familia"] for r in rows)),
                "probes_por_familia": {
                    f: dict(Counter(r["retorno_probe"] for r in rows if r["familia"] == f))
                    for f in sorted({r["familia"] for r in rows})
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
