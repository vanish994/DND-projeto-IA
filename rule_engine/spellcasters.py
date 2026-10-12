"""Características centrais das classes conjuradoras do PHB 2024."""

import unicodedata

FULL_CASTER_SLOTS = {
    1: [2],
    2: [3],
    3: [4, 2],
    4: [4, 3],
    5: [4, 3, 2],
    6: [4, 3, 3],
    7: [4, 3, 3, 1],
    8: [4, 3, 3, 2],
    9: [4, 3, 3, 3, 1],
    10: [4, 3, 3, 3, 2],
    11: [4, 3, 3, 3, 2, 1],
    12: [4, 3, 3, 3, 2, 1],
    13: [4, 3, 3, 3, 2, 1, 1],
    14: [4, 3, 3, 3, 2, 1, 1],
    15: [4, 3, 3, 3, 2, 1, 1, 1],
    16: [4, 3, 3, 3, 2, 1, 1, 1],
    17: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}

CASTING_ABILITY = {"mago": "inteligencia", "clerigo": "sabedoria", "druida": "sabedoria", "bardo": "carisma"}


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def _normalizar_classe(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.replace("-", "_").replace(" ", "_")


def _quantidade_truques(classe: str, nivel: int) -> int:
    """Quantidade de truques conhecidos por classe e marcos do PHB 2024."""
    base = {"bardo": 2, "clerigo": 3, "druida": 2, "mago": 3}[classe]
    if nivel >= 10:
        return base + 2
    if nivel >= 4:
        return base + 1
    return base


def resolver_progressao_conjuracao(fatos: dict) -> dict:
    classe = _normalizar_classe(fatos.get("classe", ""))
    try:
        nivel = int(fatos.get("nivel", 0))
    except (TypeError, ValueError):
        nivel = 0
    if classe not in CASTING_ABILITY or not 1 <= nivel <= 20:
        return {"resultado": "bloqueado", "motivo": "classe_ou_nivel_invalido"}
    atributo = CASTING_ABILITY[classe]
    modificador = _mod(int(fatos.get(atributo, 10)))
    magias_bardo = {
        1: 4,
        2: 5,
        3: 6,
        4: 7,
        5: 9,
        6: 10,
        7: 11,
        8: 12,
        9: 14,
        10: 15,
        11: 15,
        12: 16,
        13: 16,
        14: 17,
        15: 17,
        16: 18,
        17: 19,
        18: 20,
        19: 21,
        20: 22,
    }
    preparados = magias_bardo[nivel] if classe == "bardo" else max(1, nivel + modificador)
    return {
        "resultado": "resolvido",
        "classe": classe,
        "atributo_conjuracao": atributo,
        "espacos": list(FULL_CASTER_SLOTS[nivel]),
        "magias_preparadas": preparados,
        "truques": _quantidade_truques(classe, nivel),
        "foco": (
            "instrumento_musical"
            if classe == "bardo"
            else "simbolo_sagrado" if classe == "clerigo" else "foco_druida" if classe == "druida" else "foco_arcano"
        ),
    }


def resolver_inspiracao_bardo(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    carisma = int(fatos.get("carisma", 10))
    usos = max(1, _mod(carisma))
    dado = "d6" if nivel < 5 else "d8" if nivel < 10 else "d10" if nivel < 15 else "d12"
    if fatos.get("acao") == "recuperar":
        return {
            "resultado": "recuperado",
            "usos": usos,
            "recupera_em": "descanso_curto_ou_longo" if nivel >= 5 else "descanso_longo",
        }
    return {"resultado": "usado", "dado": dado, "usos_maximos": usos, "acao": "bonus"}


def resolver_canalizar_divindade(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    usos = 2 if nivel < 6 else 3 if nivel < 18 else 4
    acao = str(fatos.get("acao", "centelha_divina")).lower()
    if acao == "recuperar":
        return {"resultado": "recuperado", "usos": usos, "recupera_em": "descanso_curto_ou_longo"}
    resultado = {"resultado": "usado", "usos_maximos": usos, "acao": acao}
    if acao == "centelha_divina":
        resultado.update(
            {"cura_ou_dano": "2d8 + modificador de Sabedoria", "escalonamento": {7: "3d8", 13: "4d8", 18: "5d8"}}
        )
    elif acao == "expulsar_mortos_vivos":
        resultado["alvo"] = "mortos_vivos_em_emanacao"
    return resultado


def resolver_forma_selvagem(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    acao = str(fatos.get("acao", "ativar")).lower()
    usos = 2
    if acao == "recuperar":
        return {"resultado": "recuperado", "usos": usos, "recupera_em": "descanso_curto_ou_longo"}
    if fatos.get("incapacitado", False):
        return {"resultado": "bloqueado", "motivo": "incapacitado"}
    return {
        "resultado": "ativada",
        "usos_maximos": usos,
        "duracao": "2 horas",
        "pontos_de_vida_temporarios": nivel,
        "pode_conjurar": nivel >= 18,
        "pode_falar": False,
        "requer_forma": fatos.get("forma", "fera"),
    }


def resolver_livro_de_magias(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    acao = str(fatos.get("acao", "consultar")).lower()
    if acao == "adicionar":
        return {"resultado": "adicionado", "magias_adicionadas": 2 if nivel > 1 else 6, "fonte": "livro_de_magias"}
    if acao == "recuperacao_arcana":
        limite = (nivel + 1) // 2
        return {
            "resultado": "recuperado",
            "limite_circulos": limite,
            "nao_recupera": [6, 7, 8, 9],
            "recarga": "descanso_longo",
        }
    if acao == "memorizar":
        return {"resultado": "trocado", "requer": "descanso_curto", "limite": "uma_magia_de_circulo_1_ou_superior"}
    return {"resultado": "consultado", "magias_iniciais": 6 if nivel == 1 else 2}
