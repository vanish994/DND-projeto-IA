"""Características marciais do Livro do Jogador 2024.

As funções são determinísticas: a IA fornece os dados da jogada e o módulo
resolve apenas a regra, sem rolar dados implicitamente.
"""


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def resolver_ataque_extra(fatos: dict) -> dict:
    classe = str(fatos["classe"]).lower()
    nivel = int(fatos["nivel"])
    ataques = 1
    if nivel >= 5 and classe in {"barbaro", "guerreiro", "monge", "paladino", "guardiao"}:
        ataques = 2
    if classe == "guerreiro" and nivel >= 11:
        ataques = 3
    if classe == "guerreiro" and nivel >= 20:
        ataques = 4
    return {"resultado": "resolvido", "caracteristica": "ataque_extra", "ataques": ataques}


def resolver_maestria_arma(fatos: dict) -> dict:
    classe = str(fatos["classe"]).lower()
    nivel = int(fatos["nivel"])
    limites = {
        "guerreiro": (3, 4, 5, 6),
        "barbaro": (2, 3, 4, 4),
        "paladino": (2, 3, 4, 4),
        "guardiao": (2, 3, 4, 4),
        "ladino": (2, 2, 2, 2),
    }
    tabela = limites.get(classe, (0, 0, 0, 0))
    quantidade = tabela[0] if nivel < 4 else tabela[1] if nivel < 10 else tabela[2] if nivel < 16 else tabela[3]
    escolhidas = list(fatos.get("armas", []))
    if len(escolhidas) > quantidade:
        return {"resultado": "bloqueado", "motivo": "quantidade_de_maestrias_excedida", "limite": quantidade}
    return {"resultado": "resolvido", "caracteristica": "maestria_em_arma", "limite": quantidade, "armas": escolhidas}


def resolver_furia(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    acao = str(fatos.get("acao", "ativar")).lower()
    if acao == "ativar":
        if fatos.get("armadura_pesada", False) or fatos.get("incapacitado", False):
            return {"resultado": "bloqueado", "motivo": "armadura_pesada_ou_incapacitado"}
        max_usos = 2 if nivel < 3 else 3 if nivel < 6 else 4 if nivel < 12 else 5 if nivel < 17 else 6
        dano = 2 if nivel < 9 else 3 if nivel < 16 else 4
        return {
            "resultado": "ativada",
            "caracteristica": "furia",
            "usos_maximos": max_usos,
            "dano_adicional": dano,
            "resistencias": ["contundente", "cortante", "perfurante"],
            "vantagem_forca": True,
            "concentracao": False,
        }
    if acao == "dano":
        return {
            "resultado": "resolvido",
            "dano_adicional": 2 if nivel < 9 else 3 if nivel < 16 else 4,
            "resistencias": ["contundente", "cortante", "perfurante"],
        }
    return {"resultado": "encerrada", "caracteristica": "furia"}


def dados_ataque_furtivo(nivel: int) -> int:
    if nivel < 1:
        return 0
    return (nivel + 1) // 2


def resolver_ataque_furtivo(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    elegivel = bool(fatos.get("vantagem", False)) or bool(fatos.get("aliado_adjacente", False))
    arma_valida = bool(fatos.get("acuidade_ou_distancia", False))
    if not elegivel or not arma_valida or fatos.get("ja_usou_no_turno", False):
        return {"resultado": "bloqueado", "motivo": "requisitos_ataque_furtivo"}
    return {"resultado": "resolvido", "dados": dados_ataque_furtivo(nivel), "dado": "d6"}


def resolver_recuperar_folego(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    usos_maximos = 2 if nivel < 4 else 3 if nivel < 10 else 4
    if fatos.get("acao", "usar") == "recuperar":
        return {"resultado": "recuperado", "usos": usos_maximos}
    cura = int(fatos.get("rolagem_d10", 0)) + nivel
    return {"resultado": "usado", "cura": cura, "usos_maximos": usos_maximos, "acao_extra": nivel >= 5}


def resolver_foco_monge(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    foco_maximo = nivel
    acao = str(fatos.get("acao", "")).lower()
    custo = {"defesa_paciente": 1, "passo_do_vento": 1, "torrente_de_golpes": 1}.get(acao, 0)
    if custo and int(fatos.get("foco_disponivel", 0)) < custo:
        return {"resultado": "bloqueado", "motivo": "foco_insuficiente", "custo": custo}
    efeitos = {
        "defesa_paciente": ["desengajar", "esquivar"],
        "passo_do_vento": ["desengajar", "correr", "salto_dobrado"],
        "torrente_de_golpes": ["dois_ataques_desarmados" if nivel < 10 else "tres_ataques_desarmados"],
    }
    return {"resultado": "resolvido", "foco_maximo": foco_maximo, "custo": custo, "efeitos": efeitos.get(acao, [])}


def resolver_defletir_ataques(fatos: dict) -> dict:
    nivel = int(fatos["nivel"])
    reducao = int(fatos.get("rolagem_d10", 0)) + int(fatos.get("modificador_destreza", 0)) + nivel
    dano = int(fatos.get("dano", 0))
    return {
        "resultado": "resolvido",
        "reducao": reducao,
        "dano_restante": max(0, dano - reducao),
        "pode_redirecionar": dano <= reducao and int(fatos.get("foco_disponivel", 0)) >= 1,
    }


def resolver_esquiva_sobrenatural(fatos: dict) -> dict:
    return {"resultado": "resolvido", "dano_final": int(fatos["dano"]) // 2}


def resolver_evasao(fatos: dict) -> dict:
    if fatos.get("incapacitado", False):
        return {
            "resultado": "normal",
            "dano_final": int(fatos["dano"]) if not fatos.get("sucesso", False) else int(fatos["dano"]) // 2,
        }
    return {"resultado": "resolvido", "dano_final": 0 if fatos.get("sucesso", False) else int(fatos["dano"]) // 2}
