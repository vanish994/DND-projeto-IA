"""Invocações Místicas do Bruxo — Livro do Jogador 2024."""

INVOCATIONS = {
    "armadura_de_sombras": {"nivel": 1, "efeito": "armadura_arcana_sem_espaco"},
    "explosao_agonizante": {"nivel": 2, "truque_dano": True, "repetivel": True, "efeito": "adiciona_carisma_ao_dano"},
    "explosao_repulsiva": {"nivel": 2, "truque_ataque": True, "repetivel": True, "efeito": "empurra_3m"},
    "investimento_do_mestre_da_corrente": {"nivel": 5, "pacto": "pacto_da_corrente", "efeito": "familiar_aprimorado"},
    "lamento_das_sepulturas": {"nivel": 7, "efeito": "falar_com_mortos_sem_espaco"},
    "lamina_devoradora": {"nivel": 12, "requer": "lamina_sedenta", "efeito": "dois_ataques_extras"},
    "lamina_sedenta": {"nivel": 5, "pacto": "pacto_da_lamina", "efeito": "ataque_extra_arma_pacto"},
    "lanca_mistica": {"nivel": 2, "truque_dano": True, "efeito": "alcance_mais_9m_por_nivel"},
    "licoes_dos_grandes_antigos": {"nivel": 2, "repetivel": True, "efeito": "talento_de_origem"},
    "mascara_das_muitas_faces": {"nivel": 2, "efeito": "disfarcar_se_sem_espaco"},
    "mente_mistica": {"nivel": 1, "efeito": "vantagem_concentracao_constituicao"},
    "mestre_das_infindaveis_formas": {"nivel": 5, "efeito": "alterar_se_sem_espaco"},
    "olhar_de_duas_mentes": {"nivel": 5, "efeito": "perceber_sentidos_de_alvo"},
    "pacto_da_corrente": {"nivel": 1, "efeito": "convocar_familiar_sem_espaco"},
    "pacto_da_lamina": {"nivel": 1, "efeito": "arma_pacto_carisma_foco"},
    "pacto_do_tomo": {"nivel": 1, "efeito": "livro_truques_rituais_foco"},
    "passo_ascendente": {"nivel": 5, "efeito": "levitacao_sem_espaco"},
    "presente_das_profundezas": {"nivel": 5, "efeito": "respirar_agua_nadar"},
    "presente_dos_protetores": {"nivel": 9, "pacto": "pacto_do_tomo", "efeito": "salvar_aliado_em_0_pv"},
    "punicao_mistica": {"nivel": 5, "pacto": "pacto_da_lamina", "efeito": "dano_energetico_e_caido"},
    "salto_sobrenatural": {"nivel": 2, "efeito": "salto_sem_espaco"},
    "sorvedouro_de_vida": {"nivel": 9, "pacto": "pacto_da_lamina", "efeito": "dano_extra_e_cura"},
    "uno_com_as_sombras": {"nivel": 5, "efeito": "invisibilidade_em_sombra"},
    "vigor_infero": {"nivel": 2, "efeito": "vitalidade_vazia_pv_maximos"},
    "visao_da_bruxa": {"nivel": 15, "efeito": "visao_verdadeira_9m"},
    "visao_diabolica": {"nivel": 2, "efeito": "visao_escuro_36m"},
    "visoes_de_reinos_distantes": {"nivel": 9, "efeito": "olho_arcano_sem_espaco"},
    "visoes_nebulosas": {"nivel": 2, "efeito": "imagem_silenciosa_sem_espaco"},
}


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def validar_invocacao(fatos: dict) -> dict:
    nome = str(fatos["invocacao"]).lower()
    dados = INVOCATIONS.get(nome)
    nivel = int(fatos.get("nivel", 1))
    escolhidas = {str(x).lower() for x in fatos.get("invocacoes_escolhidas", [])}
    if dados is None:
        return {"resultado": "bloqueado", "motivo": "invocacao_desconhecida"}
    if nivel < dados["nivel"]:
        return {"resultado": "bloqueado", "motivo": "nivel_insuficiente", "nivel_minimo": dados["nivel"]}
    if nome in escolhidas and not dados.get("repetivel", False):
        return {"resultado": "bloqueado", "motivo": "invocacao_duplicada"}
    pacto = dados.get("pacto")
    if pacto and pacto not in escolhidas and pacto not in {str(x).lower() for x in fatos.get("pactos", [])}:
        return {"resultado": "bloqueado", "motivo": "pacto_obrigatorio", "pacto": pacto}
    if dados.get("truque_dano") and not fatos.get("truque_causa_dano", False):
        return {"resultado": "bloqueado", "motivo": "truque_de_dano_obrigatorio"}
    if dados.get("truque_ataque") and not fatos.get("truque_exige_jogada_ataque", False):
        return {"resultado": "bloqueado", "motivo": "truque_de_ataque_obrigatorio"}
    return {"resultado": "disponivel", "invocacao": nome, "efeito": dados["efeito"], "nivel_minimo": dados["nivel"]}


def resolver_invocacao(fatos: dict) -> dict:
    validacao = validar_invocacao(fatos)
    if validacao["resultado"] != "disponivel":
        return validacao
    nome = validacao["invocacao"]
    nivel = int(fatos.get("nivel", 1))
    carisma = int(fatos.get("carisma", 10))
    base = {"resultado": "resolvido", "invocacao": nome, "efeito": validacao["efeito"]}
    if nome == "explosao_agonizante":
        base.update({"bonus_dano": _mod(carisma), "truque": fatos.get("truque")})
    elif nome == "explosao_repulsiva":
        base.update({"empurra_metros": 3, "tamanho_maximo": "Grande", "truque": fatos.get("truque")})
    elif nome == "lanca_mistica":
        base.update({"alcance_adicional_m": 9 * nivel, "truque": fatos.get("truque")})
    elif nome == "lamina_sedenta":
        base.update({"ataques_com_arma_pacto": 2})
    elif nome == "lamina_devoradora":
        base.update({"ataques_adicionais": 2})
    elif nome == "punicao_mistica":
        circulo = int(fatos.get("circulo_espaco", 1))
        base.update(
            {
                "dano_energetico": 8 * (circulo + 1),
                "pode_impor_caido": fatos.get("tamanho_alvo", "Medio")
                in {"Miúdo", "Pequeno", "Médio", "Grande", "miudo", "pequeno", "medio", "grande"},
            }
        )
    elif nome == "sorvedouro_de_vida":
        base.update(
            {"dano_extra": "1d6", "tipos_dano": ["necrótico", "psíquico", "radiante"], "cura_por_dado_vida": True}
        )
    elif nome == "investimento_do_mestre_da_corrente":
        base.update(
            {
                "deslocamento_voo_ou_natacao": 12,
                "ataque_familiar_acao_bonus": True,
                "resistencia_familiar_reacao": True,
                "dano_familiar": ["necrótico", "radiante"],
            }
        )
    elif nome == "presente_dos_protetores":
        base.update({"nomes_permitidos": max(1, _mod(carisma)), "pv_ao_cair": 1, "recarga": "descanso_longo"})
    elif nome == "vigor_infero":
        base.update({"pv_temporarios": "máximo de 1d4 + 4", "rolagem": False})
    elif nome == "visao_diabolica":
        base.update({"visao_escuro_m": 36, "ignora_magica": True})
    elif nome == "visao_da_bruxa":
        base.update({"visao_verdadeira_m": 9})
    elif nome == "presente_das_profundezas":
        base.update(
            {
                "respira_agua": True,
                "deslocamento_natacao_igual_ao_deslocamento": True,
                "respirar_na_agua_sem_espaco": True,
            }
        )
    elif nome == "pacto_da_lamina":
        base.update(
            {
                "atributo_ataque_dano": "carisma",
                "foco_conjuracao": True,
                "tipos_dano_alternativos": ["necrótico", "psíquico", "radiante"],
            }
        )
    elif nome == "pacto_do_tomo":
        base.update({"truques": 3, "rituais_1_circulo": 2, "foco_conjuracao": True, "magias_de_qualquer_lista": True})
    elif nome == "olhar_de_duas_mentes":
        base.update(
            {"acao": "bonus", "alcance_m": 18, "duracao": "ate_fim_do_proximo_turno", "mantem_com_acao_bonus": True}
        )
    elif nome == "uno_com_as_sombras":
        base.update({"requer": "meia_luz_ou_escuridao", "invisivel": True})
    elif nome in {
        "armadura_de_sombras",
        "mascara_das_muitas_faces",
        "mestre_das_infindaveis_formas",
        "passo_ascendente",
        "salto_sobrenatural",
        "visoes_de_reinos_distantes",
        "visoes_nebulosas",
        "lamento_das_sepulturas",
    }:
        base["conjuracao_sem_espaco"] = True
    elif nome == "mente_mistica":
        base["vantagem_concentracao_constituicao"] = True
    elif nome == "licoes_dos_grandes_antigos":
        base["escolhe_talento_de_origem"] = True
    elif nome == "pacto_da_corrente":
        base.update(
            {
                "convocar_familiar_sem_espaco": True,
                "formas_especiais": [
                    "cobra_peconhenta",
                    "diabrete",
                    "esfinge_maravilhosa",
                    "esqueleto",
                    "pseudodragao",
                    "quasit",
                    "slaad_girino",
                    "sprite",
                ],
            }
        )
    elif nome == "presente_das_profundezas":
        base["recarga"] = "descanso_longo"
    return base
