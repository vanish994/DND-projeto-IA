"""Talentos do Livro do Jogador 2024: Origem, Gerais e Dádivas Épicas."""

import unicodedata


def _normalizar_nome(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    return "_".join(texto.replace("-", " ").split())


ORIGIN_FEATS = {
    "alerta": {"categoria": "origem", "efeitos": ["proficiência_iniciativa", "troca_iniciativa"]},
    "artifista": {
        "categoria": "origem",
        "efeitos": ["proficiência_3_ferramentas", "desconto_20_porcento", "fabricacao_rapida"],
    },
    "atacante_selvagem": {"categoria": "origem", "efeitos": ["rolar_dano_da_arma_duas_vezes"]},
    "curandeiro": {"categoria": "origem", "efeitos": ["medico_de_combate", "cura_garantida"]},
    "habilidoso": {"categoria": "origem", "repetivel": True, "efeitos": ["proficiência_3_pericias_ou_ferramentas"]},
    "iniciado_em_magia": {"categoria": "origem", "repetivel": True, "efeitos": ["dois_truques", "magia_1_circulo"]},
    "musico": {"categoria": "origem", "efeitos": ["proficiência_3_instrumentos", "inspiracao_heroica_aliados"]},
    "sortudo": {
        "categoria": "origem",
        "efeitos": ["pontos_de_sorte_igual_proficiencia", "vantagem_ou_desvantagem_d20"],
    },
    "valentao_de_taverna": {
        "categoria": "origem",
        "efeitos": ["ataque_desarmado_1d4", "proficiência_armas_improvisadas", "empurra_1_5m"],
    },
    "vigoroso": {"categoria": "origem", "efeitos": ["pv_maximos_mais_2_nivel"]},
}

_GENERAL_NAMES = [
    "adepto_elemental",
    "agressor",
    "analitico",
    "atirador_arcano",
    "atleta",
    "ator",
    "aumento_no_valor_de_atributo",
    "chef",
    "combatente_montado",
    "conjurador_belico",
    "conjurador_ritualista",
    "duelista_defensivo",
    "envenenador",
    "esmagador",
    "especialista_ambidestro",
    "especialista_em_armaduras_leves",
    "especialista_em_armaduras_medias",
    "especialista_em_armaduras_pesadas",
    "especialista_em_besta",
    "especialista_em_pericia",
    "exterminador_de_conjuradores",
    "imobilizador",
    "lider_inspirador",
    "mente_agucada",
    "mestre_das_armas",
    "mestre_em_armaduras_medias",
    "mestre_em_armaduras_pesadas",
    "mestre_em_armas_de_haste",
    "mestre_em_armas_grandes",
    "mestre_em_escudos",
    "mestre_atirador",
    "perfurador",
    "resiliente",
    "resistente",
    "sentinela",
    "sorrateiro",
    "talhador",
    "telecinético",
    "telepatico",
    "tocado_pela_sombra",
    "tocado_pelas_fadas",
    "treinamento_com_armas_marciais",
    "velocista",
]
GENERAL_FEATS = {
    name: {"categoria": "geral", "nivel": 4, "efeitos": ["aumento_de_atributo_1"]} for name in _GENERAL_NAMES
}
for name in {"aumento_no_valor_de_atributo"}:
    GENERAL_FEATS[name] = {
        "categoria": "geral",
        "nivel": 4,
        "repetivel": True,
        "efeitos": ["aumento_de_atributo_2_ou_dois_1"],
    }
for name in {"adepto_elemental", "atirador_arcano", "conjurador_belico", "conjurador_ritualista"}:
    GENERAL_FEATS[name]["requer_conjuracao"] = True
for name in {
    "atleta",
    "agressor",
    "especialista_ambidestro",
    "especialista_em_besta",
    "imobilizador",
    "mestre_atirador",
    "sentinela",
    "sorrateiro",
    "velocista",
    "treinamento_com_armas_marciais",
}:
    GENERAL_FEATS[name]["atributo_13"] = ["forca", "destreza"]
GENERAL_FEATS["conjurador_belico"]["efeitos"] += [
    "vantagem_concentracao",
    "magia_reativa",
    "componentes_somaticos_com_maos_ocupadas",
]
GENERAL_FEATS["adepto_elemental"]["efeitos"] += ["ignora_resistencia_elemental", "uns_no_dano_tratados_como_dois"]
GENERAL_FEATS["atirador_arcano"]["efeitos"] += ["ignora_cobertura_magica", "sem_desvantagem_a_1_5m", "alcance_mais_18m"]
GENERAL_FEATS["chef"]["efeitos"] = [
    "proficiência_utensilios_cozinheiro",
    "refeicao_mais_1d8",
    "guloseimas_pv_temporarios",
]
GENERAL_FEATS["resiliente"]["efeitos"] = ["aumento_atributo_1", "proficiência_salvaguarda"]
GENERAL_FEATS["resistente"]["efeitos"] = [
    "aumento_constituicao_1",
    "vantagem_salvaguardas_contra_morte",
    "cura_com_dado_de_vida_acao_bonus",
]
GENERAL_FEATS["mestre_em_armaduras_pesadas"]["efeitos"] += ["reduz_dano_fisico_pela_proficiencia"]
GENERAL_FEATS["mestre_em_escudos"]["efeitos"] += ["golpe_de_escudo", "interpor_escudo"]
GENERAL_FEATS["sentinela"]["efeitos"] += ["ataque_de_oportunidade_ao_desengajar", "zera_deslocamento"]
GENERAL_FEATS["sorrateiro"]["efeitos"] += ["visao_as_cegas_3m", "vantagem_furtividade_combate"]
GENERAL_FEATS["telecinético"]["efeitos"] = ["aumento_atributo_1", "maos_magicas_aprimoradas", "empurrao_telecinetico"]
GENERAL_FEATS["telepatico"]["efeitos"] = ["aumento_atributo_1", "comunicacao_telepatica_18m", "detectar_pensamentos"]
GENERAL_FEATS["tocado_pela_sombra"]["efeitos"] = ["aumento_atributo_1", "magia_sombria", "invisibilidade"]
GENERAL_FEATS["tocado_pelas_fadas"]["efeitos"] = ["aumento_atributo_1", "magia_feerica", "passo_nebuloso"]

EPIC_FEATS = {
    "dadiva_da_fortitude": ["aumento_atributo_1_ate_30", "pv_maximos_mais_40", "cura_adicional_constituicao"],
    "dadiva_da_proeza_em_combate": ["aumento_atributo_1_ate_30", "ataque_errado_acerta_uma_vez_por_turno"],
    "dadiva_da_proficiencia_em_pericia": ["aumento_atributo_1_ate_30", "proficiência_todas_pericias", "especialização"],
    "dadiva_da_recordacao_de_magia": ["aumento_atributo_1_ate_30", "espaco_1_a_4_pode_nao_ser_gasto"],
    "dadiva_da_recuperacao": ["aumento_atributo_1_ate_30", "ao_0_pv_fica_com_1_e_cura_metade", "reserva_dez_d10"],
    "dadiva_da_resistencia_a_energia": [
        "aumento_atributo_1_ate_30",
        "duas_resistencias_escolhidas",
        "redireciona_dano_2d12",
    ],
    "dadiva_da_velocidade": ["aumento_atributo_1_ate_30", "desengajar_acao_bonus", "deslocamento_mais_9m"],
    "dadiva_da_viagem_dimensional": ["aumento_atributo_1_ate_30", "teleporte_9m_apos_atacar_ou_magia"],
    "dadiva_da_visao_verdadeira": ["aumento_atributo_1_ate_30", "visao_verdadeira_18m"],
    "dadiva_do_ataque_irresistivel": [
        "aumento_atributo_1_ate_30",
        "ignora_resistencia_fisica",
        "critico_causa_dano_atributo",
    ],
    "dadiva_do_destino": ["aumento_atributo_1_ate_30", "modifica_teste_d20_2d4"],
    "dadiva_do_espirito_da_noite": [
        "aumento_atributo_1_ate_30",
        "invisibilidade_em_sombras",
        "resistencia_quase_todos_danos",
    ],
}
EPIC_FEATS = {
    name: {"categoria": "dadiva_epica", "nivel": 19, "efeitos": effects} for name, effects in EPIC_FEATS.items()
}

# Ravenloft: Horror Wilds. O texto da biblioteca lista os nomes dos talentos de
# origem, mas não traz a descrição deles; os efeitos ficam sem catalogar.
RAVENLOFT_ORIGIN_FEATS = {
    "olho_agucado": {
        "categoria": "origem",
        "fonte": "ravenloft",
        "efeitos": [
            "vantagem_em_teste_de_atributo_da_acao_procurar_ou_estudar",
            "usos_iguais_bonus_proficiencia_por_descanso_longo",
            "uso_gasto_somente_em_sucesso",
        ],
    },
    "sobrevivente": {
        "categoria": "origem",
        "fonte": "ravenloft",
        "efeitos": [
            "hipervigilancia_rerrolar_d20_iniciativa_9_ou_menos_usa_novo",
            "controlar_se_reacao_soma_bp_em_resistencia_falha_contra_enfeiticado_ou_amedrontado_1_por_descanso_longo",
        ],
    },
}
ORIGIN_FEATS.update(RAVENLOFT_ORIGIN_FEATS)

DARK_GIFT_FEATS = {
    "anatomia_aberrante": [],
    "sombra_viva": ["maos_magicas_sem_componentes", "alcance_corpo_a_corpo_mais_3m"],
    "ser_simbiotico": ["proficiencia_1_pericia_da_lista", "idioma_adicional"],
    "alma_ecoante": [
        "proficiencia_2_pericias",
        "especializacao_1_pericia_troca_no_descanso_longo",
        "idioma_adicional",
        "ecos_intrusivos_ao_rolar_1",
    ],
    "andarilho_das_brumas": ["viajante_de_dominios"],
    "toque_da_morte": [],
    "sussurros_reunidos": ["mensagem_sem_componentes_materiais", "augurio_sempre_preparado_1_por_descanso_longo"],
    "segunda_pele": ["alterar_se_sempre_preparado_1_por_descanso_longo"],
    "observadores": ["sentido_bestial_e_falar_com_animais_1_por_descanso_longo", "busca_mais_1d4"],
}
DARK_GIFT_FEATS = {
    name: {"categoria": "dadiva_sombria", "requisito": "campanha_ravenloft", "fonte": "ravenloft", "efeitos": effects}
    for name, effects in DARK_GIFT_FEATS.items()
}

FEATS = {
    _normalizar_nome(nome): dados
    for nome, dados in {**ORIGIN_FEATS, **GENERAL_FEATS, **EPIC_FEATS, **DARK_GIFT_FEATS}.items()
}


def validar_talento(fatos: dict) -> dict:
    nome = _normalizar_nome(fatos.get("talento", ""))
    dados = FEATS.get(nome)
    if not dados:
        return {"resultado": "bloqueado", "motivo": "talento_desconhecido"}
    nivel = int(fatos.get("nivel", fatos.get("nivel_personagem", 1)))
    if nivel < dados.get("nivel", 1):
        return {"resultado": "bloqueado", "motivo": "nivel_insuficiente", "nivel_minimo": dados["nivel"]}
    if dados.get("requisito") == "campanha_ravenloft" and fatos.get("campanha_ravenloft") is not True:
        return {"resultado": "bloqueado", "motivo": "requer_campanha_ravenloft"}
    if dados.get("requer_conjuracao") and not fatos.get(
        "caracteristica_conjuracao", fatos.get("magia_de_pacto", False)
    ):
        return {"resultado": "bloqueado", "motivo": "requer_conjuracao"}
    for atributo in dados.get("atributo_13", []):
        if int(fatos.get(atributo, 0)) >= 13:
            break
    else:
        if dados.get("atributo_13"):
            return {"resultado": "bloqueado", "motivo": "atributo_insuficiente", "atributos": dados["atributo_13"]}
    if dados.get("categoria") == "dadiva_epica" and nivel < 19:
        return {"resultado": "bloqueado", "motivo": "requer_nivel_19"}
    return {"resultado": "disponivel", "talento": nome, "categoria": dados["categoria"], "efeitos": dados["efeitos"]}


def resolver_talento(fatos: dict) -> dict:
    validacao = validar_talento(fatos)
    if validacao["resultado"] != "disponivel":
        return validacao
    nome = validacao["talento"]
    resultado = dict(validacao)
    # Catálogo e validação não equivalem a uma resolução mecânica completa.
    # Só declarar resolvido o talento quando existe um ramo específico abaixo.
    resultado["resultado"] = "nao_implementado"
    resultado["motivo"] = "talento_catalogado_sem_resolucao_especifica"
    if nome == "vigoroso":
        resultado["resultado"] = "resolvido"
        resultado.pop("motivo", None)
        resultado["pv_adicionais"] = 2 * int(fatos.get("nivel", 1))
    return resultado
