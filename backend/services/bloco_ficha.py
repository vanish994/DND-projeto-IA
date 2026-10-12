"""Bloco derivado da ficha: CA, ataque, dano, salvaguardas e perícias.

Valores calculados pelo servidor para exibição da ficha. Nada aqui é inventado
pelo cliente: os números saem do catálogo oficial somados aos modificadores já
validados pelo Rule Engine.
"""
from __future__ import annotations

from rule_engine.ability_checks import PERICIAS
from rule_engine.catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS

# Armas simples do catálogo; as demais do CATALOGO_ARMAS são marciais.
ARMAS_SIMPLES = {
    "Clava", "Clava Grande", "Adaga", "Dardo", "Machadinha", "Martelo Leve", "Maça",
    "Cajado", "Funda", "Azagaia", "Arco Curto", "Besta Leve",
}

# Proficiências específicas concedidas por classe que não usam o nome da arma.
ALIAS_PROFICIENCIA_ARMA = {
    "Besta de Mão": "bestas_de_mao", "Espada Longa": "espadas_longas",
    "Rapieira": "rapieiras", "Espada Curta": "espadas_curtas",
    "Adaga": "adagas", "Dardo": "dardos", "Funda": "fundas",
    "Cajado": "cajados", "Besta Leve": "bestas_leves", "Clava": "clavas",
    "Clava Grande": "clavas_grandes", "Machadinha": "machadinhas",
    "Azagaia": "azagaias", "Martelo Leve": "martelos_leves", "Maça": "macas",
    "Cimitarra": "cimitarras", "Foice": "foices", "Lança": "lancas",
}

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


def pes(metros: float) -> int:
    """Converte o alcance do catálogo (metros) para pés, como o mapa tático usa."""
    return max(ALCANCE_CORPO_A_CORPO_PES, round(float(metros) * 3.28084))


def proficiente_com_arma(personagem: dict, nome_arma: str) -> bool:
    profs = personagem.get("proficiencias_classe") or {}
    if not isinstance(profs, dict):
        return False
    conhecidas = set(profs.get("armas", []))
    categoria = "simples" if nome_arma in ARMAS_SIMPLES else "marciais"
    return categoria in conhecidas or ALIAS_PROFICIENCIA_ARMA.get(nome_arma) in conhecidas


def resolver_arma_ficha(personagem: dict, nome_arma: str | None) -> dict:
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
    alcance_pes = pes(arma.get("alcance", 0)) if a_distancia or "arremesso" in conjunto else (
        ALCANCE_EXTENSAO_PES if "extensao" in conjunto else ALCANCE_CORPO_A_CORPO_PES
    )
    quantidade, lados = (int(parte) for parte in str(arma["dano"]).lower().split("d"))
    dano_medio = int(quantidade * (lados + 1) / 2) + modificador
    sinal = "+" if modificador >= 0 else "−"
    return {
        "nome": nome_arma, "desarmado": False, "catalogo": True,
        "proficiente": proficiente_com_arma(personagem, nome_arma),
        "atributo": atributo, "modificador": modificador,
        "ataque": proficiencia + modificador,
        "dado": arma["dano"], "modificador_dano": modificador,
        "expressao_dano": f"{arma['dano']} {sinal} {abs(modificador)}",
        "dano_medio": max(0, dano_medio), "tipo": arma["tipo"],
        "alcance_pes": alcance_pes, "propriedades": propriedades,
        "a_distancia": a_distancia, "arremesso": "arremesso" in conjunto,
    }


def calcular_ca_ficha(personagem: dict) -> int:
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


def bloco_salvaguardas(personagem: dict) -> list[dict]:
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


def bloco_pericias(personagem: dict) -> list[dict]:
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


def bloco_conjuracao(personagem: dict) -> dict | None:
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


def bloco_ficha(personagem: dict) -> dict:
    """Valores derivados calculados pelo servidor para exibição da ficha.

    Nada aqui é inventado pelo cliente: CA, ataque, dano, salvaguardas e perícias
    saem do catálogo oficial somados aos modificadores já validados pelo motor.
    """
    equipamento = personagem.get("equipamento") or {}
    armadura = CATALOGO_ARMADURAS.get(equipamento.get("armadura") or "")
    return {
        "fonte": "rule_engine",
        "ca": calcular_ca_ficha(personagem),
        "iniciativa": int((personagem.get("modificadores") or {}).get("destreza", 0)),
        "bonus_proficiencia": int(personagem.get("bonus_proficiencia") or 2),
        "arma": resolver_arma_ficha(personagem, equipamento.get("arma")),
        "armadura": {
            "nome": equipamento.get("armadura"), "escudo": bool(equipamento.get("escudo")),
            "categoria": armadura["categoria"] if armadura else None,
            "ca_base": armadura["ca"] if armadura else None,
        },
        "conjuracao": bloco_conjuracao(personagem),
        "salvaguardas": bloco_salvaguardas(personagem),
        "pericias": bloco_pericias(personagem),
    }


def com_bloco(personagem: dict) -> dict:
    """Anexa o bloco derivado à ficha devolvida pelas rotas de personagem."""
    if not isinstance(personagem, dict):
        return personagem
    return {**personagem, "bloco": bloco_ficha(personagem)}
