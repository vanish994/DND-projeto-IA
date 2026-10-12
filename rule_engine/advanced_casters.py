"""Características do Bruxo, Feiticeiro, Guardião e Paladino — PHB 2024."""

from .spellcasters import FULL_CASTER_SLOTS

HALF_CASTER_SLOTS = {
    1: [2],
    2: [2],
    3: [3],
    4: [3],
    5: [4, 2],
    6: [4, 2],
    7: [4, 3],
    8: [4, 3],
    9: [4, 3, 2],
    10: [4, 3, 2],
    11: [4, 3, 3],
    12: [4, 3, 3],
    13: [4, 3, 3, 1],
    14: [4, 3, 3, 1],
    15: [4, 3, 3, 2],
    16: [4, 3, 3, 2],
    17: [4, 3, 3, 3],
    18: [4, 3, 3, 3],
    19: [4, 3, 3, 3, 2],
    20: [4, 3, 3, 3, 2],
}
PACT_SLOTS = {
    1: (1, 1),
    2: (2, 1),
    3: (2, 2),
    4: (2, 2),
    5: (2, 3),
    6: (2, 3),
    7: (2, 4),
    8: (2, 4),
    9: (2, 5),
    10: (2, 5),
    11: (3, 5),
    12: (3, 5),
    13: (3, 5),
    14: (3, 5),
    15: (3, 5),
    16: (3, 5),
    17: (4, 5),
    18: (4, 5),
    19: (4, 5),
    20: (4, 5),
}


def _mod(value: int) -> int:
    return (int(value) - 10) // 2


def _nivel_valido(fatos: dict) -> int | None:
    try:
        nivel = int(fatos.get("nivel", 0))
    except (TypeError, ValueError):
        return None
    return nivel if 1 <= nivel <= 20 else None


def resolver_bruxo(fatos: dict) -> dict:
    nivel = _nivel_valido(fatos)
    if nivel is None:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    acao = str(fatos.get("acao", "progressao")).lower()
    espacos, circulo = PACT_SLOTS[max(k for k in PACT_SLOTS if k <= nivel)]
    invocacoes = (
        1
        if nivel == 1
        else (
            3
            if nivel < 5
            else (
                5
                if nivel < 9
                else 6 if nivel < 12 else 7 if nivel < 15 else 8 if nivel < 18 else 9 if nivel < 20 else 10
            )
        )
    )
    if acao == "astucia_magica":
        return {"resultado": "recuperado", "espacos_recuperados": (espacos + 1) // 2, "recarga": "descanso_longo"}
    if acao == "arcana_mistica":
        circulo_arcana = {11: 6, 13: 7, 15: 8, 17: 9}.get(nivel)
        if circulo_arcana is None:
            return {"resultado": "bloqueado", "motivo": "nivel_sem_arcana_mistica"}
        return {"resultado": "resolvido", "circulo": circulo_arcana, "usos": 1, "recarga": "descanso_longo"}
    if acao == "progressao":
        return {
            "resultado": "resolvido",
            "espacos": espacos,
            "circulo": circulo,
            "invocacoes": invocacoes,
            "atributo_conjuracao": "carisma",
        }
    return {"resultado": "bloqueado", "motivo": "acao_desconhecida", "acao": acao}


def resolver_feiticeiro(fatos: dict) -> dict:
    nivel = _nivel_valido(fatos)
    if nivel is None:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    acao = str(fatos.get("acao", "progressao")).lower()
    pontos = max(0, nivel)
    if nivel < 2:
        pontos = 0
    if acao == "feitiçaria_inata" or acao == "feiticaria_inata":
        return {"resultado": "ativada", "duracao": "1 minuto", "usos": 2, "bonus_cd": 1, "vantagem_ataque_magia": True}
    if acao == "metamagia":
        opcoes = 2 if nivel < 10 else 4 if nivel < 17 else 6
        return {
            "resultado": "resolvido",
            "opcoes_conhecidas": opcoes,
            "pontos_disponiveis": pontos,
            "limite_por_magia": 1,
        }
    if acao == "restauracao_feiticeira":
        return {"resultado": "recuperado", "pontos": nivel // 2, "recarga": "descanso_longo"}
    if acao == "feiticaria_encarnada":
        return {"resultado": "ativada", "custo": 2, "metamagias_por_magia": 2}
    if acao == "apoteose_arcana":
        return {"resultado": "resolvido", "metamagia_gratuita_por_turno": True}
    if acao == "progressao":
        return {
            "resultado": "resolvido",
            "pontos_de_feiticaria": pontos,
            "espacos": list(FULL_CASTER_SLOTS[nivel]),
            "atributo_conjuracao": "carisma",
        }
    return {"resultado": "bloqueado", "motivo": "acao_desconhecida", "acao": acao}


def resolver_guardiao(fatos: dict) -> dict:
    nivel = _nivel_valido(fatos)
    if nivel is None:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    acao = str(fatos.get("acao", "progressao")).lower()
    if acao == "progressao":
        return {
            "resultado": "resolvido",
            "espacos": HALF_CASTER_SLOTS[nivel],
            "atributo_conjuracao": "sabedoria",
            "inimigo_favorito_usos": (
                2 if nivel < 5 else 3 if nivel < 9 else 4 if nivel < 13 else 5 if nivel < 17 else 6
            ),
        }
    if acao == "inimigo_favorito":
        return {
            "resultado": "ativado",
            "magia_preparada": "marca_do_predador",
            "usos": 2 if nivel < 5 else 3 if nivel < 9 else 4 if nivel < 13 else 5 if nivel < 17 else 6,
            "recarga": "descanso_longo",
        }
    if acao == "explorador_habil":
        return {"resultado": "resolvido", "especializacao": 1, "idiomas_adicionais": 2}
    if acao == "incansavel":
        return {
            "resultado": "resolvido",
            "pontos_de_vida_temporarios": int(fatos.get("rolagem_d8", 0))
            + max(1, _mod(int(fatos.get("sabedoria", 10)))),
            "usos": max(1, _mod(int(fatos.get("sabedoria", 10)))),
        }
    if acao == "veu_da_natureza":
        return {
            "resultado": "ativado",
            "acao": "bonus",
            "duracao": "ate_o_fim_do_proximo_turno",
            "invisivel": True,
            "usos": max(1, _mod(int(fatos.get("sabedoria", 10)))),
        }
    if acao == "predador_implacavel":
        return {"resultado": "resolvido", "mantem_concentracao_ao_sofrer_dano": True}
    return {"resultado": "bloqueado", "motivo": "acao_desconhecida", "acao": acao}


def resolver_paladino(fatos: dict) -> dict:
    """Progressão de conjuração e recursos básicos do Paladino 2024."""
    nivel = _nivel_valido(fatos)
    if nivel is None:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    acao = str(fatos.get("acao", "progressao")).lower()
    carisma = int(fatos.get("carisma", 10))
    if acao == "progressao":
        return {
            "resultado": "resolvido",
            "classe": "paladino",
            "espacos": list(HALF_CASTER_SLOTS[nivel]),
            "atributo_conjuracao": "carisma",
            "magias_preparadas": max(1, nivel // 2 + _mod(carisma)),
            "pontos_de_cura_maos_consagradas": 5 * nivel,
        }
    if acao == "maos_consagradas":
        quantidade = int(fatos.get("quantidade", 0))
        disponivel = max(0, 5 * nivel)
        if quantidade < 0 or quantidade > disponivel:
            return {"resultado": "bloqueado", "motivo": "quantidade_de_cura_invalida", "maximo": disponivel}
        return {"resultado": "resolvido", "cura": quantidade, "pontos_restantes": disponivel - quantidade}
    if acao == "destruicao_do_paladino":
        espaco = int(fatos.get("espaco", 0))
        if not 1 <= espaco <= 5:
            return {"resultado": "bloqueado", "motivo": "espaco_invalido"}
        return {
            "resultado": "requer_resolucao_de_dano",
            "dado_adicional": f"{espaco + 1}d8",
            "dano_extra_contra": ["morto_vivo", "imundo"],
            "dado_extra_contra": "1d8",
            "tipo": "radiante",
            "acao": "bonus",
        }
    return {"resultado": "bloqueado", "motivo": "acao_desconhecida", "acao": acao}
