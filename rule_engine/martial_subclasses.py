"""Subclasses marciais do Livro do Jogador 2024.

Inclui o catálogo e as resoluções determinísticas dos efeitos centrais.
"""

SUBCLASS_FEATURES = {
    "campeao": {
        3: ["atleta_extraordinario", "critico_aprimorado"],
        7: ["estilo_de_luta_adicional"],
        10: ["combatente_heroico"],
        15: ["critico_superior"],
        18: ["sobrevivente"],
    },
    "cavaleiro_mistico": {
        3: ["conjuracao", "vinculo_com_arma"],
        7: ["magia_de_guerra"],
        10: ["golpe_mistico"],
        15: ["investida_mistica"],
        18: ["magia_de_guerra_aprimorada"],
    },
    "combatente_psiquico": {
        3: ["poder_psionico"],
        7: ["adepto_telecinetico"],
        10: ["resguardo_mental"],
        15: ["baluarte_de_energia"],
        18: ["mestre_telecinetico"],
    },
    "mestre_da_batalha": {
        3: ["estudioso_da_guerra", "superioridade_em_combate"],
        7: ["superioridade_em_combate_adicional"],
        10: ["superioridade_em_combate_adicional"],
        15: ["implacavel"],
        18: ["superioridade_em_combate_aprimorada"],
    },
    "trilha_da_arvore_do_mundo": {
        3: ["vitalidade_da_arvore"],
        6: ["ramos_da_arvore"],
        10: ["raizes_devastadoras"],
        14: ["percorrer_a_arvore"],
    },
    "trilha_do_berserker": {3: ["frenesi"], 6: ["furia_irracional"], 10: ["retaliacao"], 14: ["presenca_intimidante"]},
    "trilha_do_coracao_selvagem": {
        3: ["arauto_da_fauna", "furia_dos_selvagens"],
        6: ["aspecto_dos_selvagens"],
        10: ["arauto_da_natureza"],
        14: ["poder_dos_selvagens"],
    },
    "caminho_do_guerreiro_espiritual": {
        3: ["arauto_da_fauna", "furia_dos_selvagens"],
        6: ["aspecto_dos_selvagens"],
        10: ["arauto_da_natureza"],
        14: ["poder_dos_selvagens"],
    },
    "trilha_do_fanatico": {
        3: ["campeao_dos_deuses", "furia_divina"],
        6: ["concentracao_fanatica"],
        10: ["presenca_zelosa"],
        14: ["furia_dos_deuses"],
    },
    "combatente_da_mao_espalmada": {
        3: ["tecnica_da_mao_espalmada"],
        6: ["integridade_corporal"],
        11: ["passo_veloz"],
        17: ["palma_vibrante"],
    },
    "combatente_da_misericordia": {
        3: ["implementos_de_misericordia", "mao_de_cura", "mao_de_dolo"],
        6: ["toque_de_medico"],
        11: ["torrente_de_cura_e_dolo"],
        17: ["mao_da_misericordia_final"],
    },
    "combatente_das_sombras": {
        3: ["artes_das_sombras"],
        6: ["passo_da_sombra"],
        11: ["passo_da_sombra_aprimorado"],
        17: ["manto_da_sombra"],
    },
    "combatente_dos_elementos": {
        3: ["manipular_elementos", "sintonia_elemental"],
        6: ["golpe_elemental"],
        11: ["explosao_elemental"],
        17: ["avatar_dos_elementos"],
    },
    "adaga_espiritual": {
        3: ["poder_psiquico"],
        9: ["lamina_espiritual"],
        13: ["velocidade_psiquica"],
        17: ["morte_psiquica"],
    },
    "assassino": {
        3: ["assassinar"],
        9: ["especialista_em_infiltracao"],
        13: ["impulso_letalde"],
        17: ["golpe_de_morte"],
    },
    "ladrao": {3: ["mao_rapida"], 9: ["truques_de_magia"], 13: ["dispositivo_estranho"], 17: ["ladrao_de_alma"]},
    "trapaceiro_arcano": {
        3: ["conjuracao", "mao_mage"],
        9: ["emboscada_magica"],
        13: ["enganador_versatil"],
        17: ["ladrao_de_magia"],
    },
}

ALIASES = {
    "caminho_do_guerreiro_espiritual": "trilha_do_coracao_selvagem",
    "berserker": "trilha_do_berserker",
    "wild_heart": "trilha_do_coracao_selvagem",
    "champion": "campeao",
}


def normalizar_subclasse(nome: str) -> str:
    nome = str(nome).lower()
    return ALIASES.get(nome, nome)


def caracteristicas_subclasse(nome: str, nivel: int) -> list[str]:
    nome = normalizar_subclasse(nome)
    return list(SUBCLASS_FEATURES.get(nome, {}).get(int(nivel), ()))


def resolver_subclasse_marcial(fatos: dict) -> dict:
    subclasse = normalizar_subclasse(fatos["subclasse"])
    nivel = int(fatos["nivel"])
    if subclasse not in SUBCLASS_FEATURES:
        return {"resultado": "bloqueado", "motivo": "subclasse_marcial_desconhecida"}
    disponiveis = [f for nivel_f, fs in SUBCLASS_FEATURES[subclasse].items() if nivel_f <= nivel for f in fs]
    caracteristica = str(fatos.get("caracteristica", "")).lower()
    if caracteristica and caracteristica not in disponiveis:
        return {"resultado": "bloqueado", "motivo": "caracteristica_ainda_nao_disponivel", "disponiveis": disponiveis}

    # Efeitos centrais comuns às subclasses, com dados fornecidos pela IA.
    if caracteristica == "critico_aprimorado":
        return {"resultado": "resolvido", "critico_com": [19, 20]}
    if caracteristica == "critico_superior":
        return {"resultado": "resolvido", "critico_com": [18, 19, 20]}
    if caracteristica == "frenesi":
        dano = 2 if nivel < 10 else 3 if nivel < 14 else 4
        return {"resultado": "resolvido", "dano_adicional": dano, "dado": "d6", "requer_ataque_imprudente": True}
    if caracteristica == "furia_irracional":
        return {"resultado": "resolvido", "imunidades": ["amedrontado", "enfeiticado"], "encerra_ao_ativar": True}
    if caracteristica == "retaliacao":
        return {"resultado": "resolvido", "acao": "reacao", "alcance": 1.5, "requer_dano_recebido": True}
    if caracteristica == "furia_divina":
        return {
            "resultado": "resolvido",
            "dano_adicional": "1d6 + metade do nível de bárbaro",
            "tipo": fatos.get("tipo_dano", "radiante"),
        }
    if caracteristica == "tecnica_da_mao_espalmada":
        return {"resultado": "resolvido", "opcoes": ["caido", "empurrado", "sem_reacoes"]}
    if caracteristica == "mao_de_cura":
        return {
            "resultado": "resolvido",
            "cura": int(fatos.get("dado_artes_marciais", 0)) + int(fatos.get("modificador_sabedoria", 0)),
        }
    if caracteristica == "mao_de_dolo":
        return {
            "resultado": "resolvido",
            "dano_necrotico": int(fatos.get("dado_artes_marciais", 0)) + int(fatos.get("modificador_sabedoria", 0)),
        }
    if caracteristica == "passo_da_sombra":
        return {"resultado": "resolvido", "acao": "acao_bonus", "teleporte": 18, "vantagem_proximo_ataque": True}
    if caracteristica == "mao_rapida":
        return {"resultado": "resolvido", "acoes_bonus": ["prestidigitacao", "usar_objeto"]}
    if caracteristica == "assassinar":
        return {"resultado": "resolvido", "vantagem": True, "critico": fatos.get("alvo_surpreso", False)}
    if caracteristica == "dispositivo_estranho":
        return {"resultado": "resolvido", "itens_magicos": 3}
    if caracteristica == "poder_psionico":
        return {
            "resultado": "resolvido",
            "dados_energia": max(1, (nivel + 2) // 3),
            "dado": "d6" if nivel < 5 else "d8" if nivel < 11 else "d10" if nivel < 17 else "d12",
        }
    # Nunca declare sucesso apenas porque a característica consta do catálogo.
    # Apenas efeitos explicitamente implementados acima podem ser resolvidos.
    if not caracteristica:
        return {
            "resultado": "requer_caracteristica",
            "subclasse": subclasse,
            "caracteristicas_disponiveis": disponiveis,
        }
    return {
        "resultado": "nao_implementado",
        "subclasse": subclasse,
        "caracteristica": caracteristica,
        "motivo": "caracteristica_catalogada_sem_resolver_especifico",
    }
