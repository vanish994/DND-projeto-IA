"""Sistema de magias do Livro do Jogador 2024.

O catálogo reaproveita as centenas de entradas extraídas do livro e adiciona
metadados executáveis, componentes, concentração, efeitos e escalonamento.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any
from .catalog import CATALOGO_MAGIAS

ESCOLAS = {"abjuração", "adivinhação", "conjuração", "encantamento", "evocação", "ilusão", "necromancia", "transmutação"}

def _nome_limpo(nome: str) -> str:
    nome = re.sub(r"\s+", " ", nome).strip(" -–")
    return nome

MAGIAS: dict[str, dict[str, Any]] = {}
for bruto, meta in CATALOGO_MAGIAS.items():
    partes = re.split(r"\s{2,}", bruto.strip())
    nome = _nome_limpo(partes[0])
    if nome and nome.lower() not in {"a opção que você escolheu para golpes abençoados", "após usar", "como uma ação usar"}:
        MAGIAS.setdefault(nome.lower(), {"nome": nome, "circulo": 0, "escola": meta["escola"].lower(), "componentes": "V, S" + (", M" if meta.get("material") else ""), "concentracao": bool(meta.get("concentracao")), "ritual": bool(meta.get("ritual")), "duracao": "concentração" if meta.get("concentracao") else "instantânea"})

# Entradas de referência com círculo, componentes e efeitos precisos do PHB 2024.
_DETALHADAS = {
    "armadura de agathys": (1, "abjuração", "V, S, M (um caco de vidro azul)", False, "5 PV temporários; 5 dano gélido ao atacante", {"pv_temporarios": "+5 por círculo", "dano_retorno": "+5 por círculo"}),
    "mísseis mágicos": (1, "evocação", "V, S", False, "3 dardos de 1d4+1 dano energético", {"dardos": "+1 por círculo"}),
    "escudo": (1, "abjuração", "V, S", False, "+5 CA até o início do próximo turno", {}),
    "cura pelas mãos": (1, "abjuração", "V, S", False, "cura 2d8", {"cura": "+2d8 por círculo"}),
    "curar ferimentos": (1, "necromancia", "V, S", False, "cura 2d8", {"cura": "+2d8 por círculo"}),
    "benção": (1, "encantamento", "V, S, M (uma gota de água benta)", True, "até três criaturas adicionam 1d4", {"alvos": "+1 por círculo"}),
    "dardo místico": (0, "evocação", "V, S", False, "1d10 dano energético", {"dano": "+1d10 nos níveis 5, 11 e 17"}),
    "raio místico": (0, "evocação", "V, S", False, "1d10 dano energético", {"raios": "+1 nos níveis 5, 11 e 17"}),
    "bola de fogo": (3, "evocação", "V, S, M (uma bola de guano de morcego e enxofre)", False, "8d6 dano ígneo em esfera de 6m", {"dano": "+1d6 por círculo"}),
    "relâmpago": (3, "evocação", "V, S, M (um pouco de pelo e uma haste de âmbar, cristal ou vidro)", False, "8d6 dano elétrico em linha", {"dano": "+1d6 por círculo"}),
    "contramagia": (3, "abjuração", "S", False, "interrompe magia", {}),
    "voo": (3, "transmutação", "V, S, M (uma pena de qualquer ave)", True, "deslocamento de voo 18m", {"alvos": "+1 por círculo"}),
    "invisibilidade": (2, "ilusão", "V, S, M (uma pestana envolta em goma)", True, "condição Invisível", {"alvos": "+1 por círculo"}),
    "passo nebuloso": (2, "conjuração", "V", False, "teleporta 9m", {}),
    "reviver os mortos": (5, "necromancia", "V, S, M (um diamante de 500 PO)", False, "retorna criatura morta à vida", {}),
    "dissipar magia": (3, "abjuração", "V, S", False, "encerra efeitos mágicos", {}),
    "banimento": (4, "abjuração", "V, S, M (um item desagradável ao alvo)", True, "salvaguarda ou banido", {"alvos": "+1 por círculo"}),
    "cura completa": (6, "necromancia", "V, S", False, "cura 70 PV", {"cura": "+10 por círculo"}),
}
for nome, (circulo, escola, componentes, conc, efeito, upcast) in _DETALHADAS.items():
    MAGIAS[nome] = {"nome": nome.title(), "circulo": circulo, "escola": escola, "componentes": componentes, "concentracao": conc, "ritual": False, "duracao": "concentração" if conc else "instantânea", "efeito": efeito, "upcasting": upcast}


def listar_magias(escola: str | None = None, circulo: int | None = None) -> list[dict[str, Any]]:
    resultado = list(MAGIAS.values())
    if escola:
        resultado = [m for m in resultado if m["escola"] == escola.lower()]
    if circulo is not None:
        resultado = [m for m in resultado if m["circulo"] == int(circulo)]
    return sorted(resultado, key=lambda m: (m["circulo"], m["nome"]))


def _normalizar_nome_magia(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\\s+", " ", texto).replace("-", " ")


def obter_magia(nome: str) -> dict[str, Any] | None:
    direta = MAGIAS.get(str(nome).strip().lower())
    if direta is not None:
        return direta
    chave = _normalizar_nome_magia(nome)
    for magia in MAGIAS.values():
        if _normalizar_nome_magia(magia["nome"]) == chave:
            return magia
    return None


def _circulo_efetivo(base: int, usado: int) -> int:
    if not 0 <= usado <= 9:
        raise ValueError("O espaço de magia deve estar entre 0 e 9")
    if base == 0 and usado != 0:
        raise ValueError("Truques não usam espaços de magia")
    if base > 0 and usado == 0:
        raise ValueError("Magias de círculo 1 ou superior exigem espaço de magia")
    if usado < base:
        raise ValueError("O espaço usado não pode ser inferior ao círculo da magia")
    return usado - base


def resolver_magia(fatos: dict) -> dict[str, Any]:
    nome = str(fatos.get("magia", fatos.get("spell", ""))).lower()
    magia = obter_magia(nome)
    if not magia:
        return {"resultado": "bloqueado", "motivo": "magia_desconhecida", "magia": nome}
    try:
        usado = int(fatos.get("espaco", fatos.get("spell_level", magia["circulo"])))
        aumento = _circulo_efetivo(magia["circulo"], usado)
    except (TypeError, ValueError) as erro:
        return {"resultado": "bloqueado", "motivo": "circulo_invalido", "detalhe": str(erro)}
    componentes = set(magia["componentes"].replace("(", ",").replace(")", ",").split(","))
    requeridos = {c.strip() for c in componentes if c.strip() in {"V", "S", "M"}}
    disponiveis = set(fatos.get("componentes_disponiveis", ["V", "S", "M"]))
    faltantes = requeridos - disponiveis
    if faltantes:
        return {"resultado": "bloqueado", "motivo": "componentes_ausentes", "faltantes": sorted(faltantes)}
    if magia["concentracao"] and fatos.get("concentrando") and fatos.get("nova_concentracao", True):
        encerra = fatos["concentrando"]
    else:
        encerra = None
    resultado = {
        "magia": magia["nome"], "circulo_base": magia["circulo"],
        "circulo_usado": usado, "upcasting": aumento, "escola": magia["escola"],
        "componentes": sorted(requeridos), "concentracao": magia["concentracao"],
        "duracao": magia["duracao"], "encerra_concentracao": encerra,
    }
    if "efeito" not in magia:
        # Metadados do catálogo não bastam para executar uma magia com fidelidade.
        # Não declarar a conjuração resolvida enquanto o efeito específico não existir.
        resultado.update({
            "resultado": "nao_implementado",
            "motivo": "magia_catalogada_sem_resolucao_especifica",
        })
        return resultado
    resultado.update({"resultado": "conjurada", "efeito": magia["efeito"]})
    if aumento and magia.get("upcasting"):
        resultado["escalonamento"] = magia["upcasting"]
    return resultado
