"""Características de classe executáveis do PHB 2024.

Este módulo mantém os recursos sem estado mutável: a aplicação fornece usos,
atributos e resultados da jogada, e recebe uma resolução determinística.
"""

from __future__ import annotations

import unicodedata

from .class_progression import FEATURES_BY_CLASS


def _normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.replace(" ", "_").replace("-", "_")


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def resolver_caracteristica(f: dict) -> dict:
    classe = _normalizar(f.get("classe", f.get("class", "")))
    recurso = _normalizar(f.get("recurso", f.get("feature", "")))
    try:
        nivel = int(f.get("nivel", f.get("level", 1)))
    except (TypeError, ValueError):
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    if not classe:
        return {"resultado": "bloqueado", "motivo": "classe_ausente"}
    if not 1 <= nivel <= 20:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}
    if not recurso:
        return {"resultado": "requer_caracteristica", "classe": classe, "nivel": nivel}

    if classe not in FEATURES_BY_CLASS:
        return {"resultado": "bloqueado", "motivo": "classe_desconhecida", "classe": classe}
    aliases = {
        "asi": "aumento_de_atributo_ou_talento",
        "aumento_de_atributo": "aumento_de_atributo_ou_talento",
        "tinkers_magic": "magia_de_artifice",
        "replicate_magic_item": "replicar_item_magico",
        "flash_of_genius": "lampejo_de_genio",
        "spell_storing_item": "item_armazenador_de_magia",
        "advanced_artifice": "artifice_avancado",
        "soul_of_artifice": "alma_do_artifice",
    }
    chave = aliases.get(recurso, recurso)
    marcos = [n for n, nomes in FEATURES_BY_CLASS[classe].items() if chave in {_normalizar(nome) for nome in nomes}]
    if marcos and nivel < min(marcos):
        return {
            "resultado": "bloqueado",
            "motivo": "nivel_insuficiente",
            "classe": classe,
            "caracteristica": chave,
            "nivel_minimo": min(marcos),
        }

    if recurso in {"asi", "aumento_de_atributo", "aumento_de_atributo_ou_talento"}:
        atributo = f.get("atributo")
        talento = f.get("talento")
        if atributo and atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
            return {"resultado": "bloqueado", "motivo": "atributo_invalido"}
        if not atributo and not talento:
            return {"resultado": "bloqueado", "motivo": "escolha_obrigatoria"}
        if atributo and int(f.get("aumento", 1)) not in {1, 2}:
            return {"resultado": "bloqueado", "motivo": "aumento_deve_ser_um_ou_dois"}
        return {
            "resultado": "aplicado",
            "atributo": atributo,
            "aumento": int(f.get("aumento", 1)) if atributo else 0,
            "talento": talento,
        }

    if classe == "barbaro":
        if recurso == "defesa_sem_armadura":
            return {
                "resultado": "resolvido",
                "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("constituicao", 10)),
                "usa_escudo": True,
            }
        if recurso == "sentido_de_perigo":
            return {
                "resultado": "resolvido",
                "vantagem_salvaguarda_destreza": not f.get("cego", False)
                and not f.get("surdo", False)
                and not f.get("incapacitado", False),
            }
        if recurso == "conhecimento_primordial":
            return {
                "resultado": "resolvido",
                "pericias_forca_durante_furia": [
                    "acrobacia",
                    "intimidacao",
                    "percepcao",
                    "furtividade",
                    "sobrevivencia",
                ],
                "prof_expertise": f.get("pericia"),
            }
        if recurso == "movimento_rapido":
            return {"resultado": "resolvido", "bonus_deslocamento_m": 3 if not f.get("armadura_pesada", False) else 0}
        if recurso == "furia_implacavel":
            cd = int(f.get("cd", 10))
            if int(f.get("salvaguarda_constituicao", -1)) < cd:
                return {
                    "resultado": "bloqueado",
                    "motivo": "falha_nao_salva_furia",
                    "cd": cd,
                    "cura": 2 * nivel,
                    "recarga": "descanso_longo",
                }
            return {"resultado": "salvo", "cd": cd, "furia_continua": True, "aumentar_cd": 5}
        if recurso == "forca_indomavel":
            valor = int(f.get("resultado_forca", 0))
            forca = int(f.get("forca", 10))
            return {"resultado": "resolvido", "total": max(valor, forca), "substitui_se_inferior": True}
        if recurso == "campeao_primitivo":
            return {"resultado": "resolvido", "bonus_forca": 4, "bonus_constituicao": 4, "maximo_atributo": 25}

    if classe == "guerreiro":
        if recurso in {"surto_de_acao", "surto_de_acao_aprimorado"}:
            return {
                "resultado": "resolvido",
                "acao_adicional": True,
                "pode_acao_magica": False,
                "usos": 2 if nivel >= 17 else 1,
                "limite_por_turno": 1,
            }
        if recurso == "mente_tatica":
            return {
                "resultado": "resolvido",
                "bonus_teste": int(f.get("rolagem_d10", 0)) + _mod(f.get("constituicao", 10)),
                "gasta_recuperar_folego": True,
            }
        if recurso in {"indomavel", "indomavel_aprimorado"}:
            usos = 3 if nivel >= 17 else 2 if nivel >= 13 else 1
            if f.get("sucesso", False):
                return {"resultado": "sucesso", "usos": usos}
            return {"resultado": "nova_rolagem", "bonus": nivel, "usos": usos}
        if recurso == "ajuste_tatico":
            return {"resultado": "resolvido", "movimento": "metade_do_deslocamento", "sem_ataque_de_oportunidade": True}
        if recurso == "ataques_estudados":
            return {
                "resultado": "resolvido",
                "vantagem_proximo_ataque": not f.get("acertou", True),
                "alvo": f.get("alvo"),
            }

    if classe == "monge":
        if recurso == "defesa_sem_armadura":
            return {
                "resultado": "resolvido",
                "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("sabedoria", 10)),
                "usa_armadura": False,
                "usa_escudo": False,
            }
        if recurso == "artes_marciais":
            dado = "d6" if nivel < 5 else "d8" if nivel < 11 else "d10" if nivel < 17 else "d12"
            return {"resultado": "resolvido", "dado": dado, "ataque_desarmado_bonus": True, "usa_destreza": True}
        if recurso == "queda_lenta":
            return {"resultado": "resolvido", "reducao": 5 * nivel, "usa_reacao": True}
        if recurso == "golpe_atordoante":
            cd = 8 + int(f.get("bonus_proficiencia", 2)) + _mod(f.get("sabedoria", 10))
            return {
                "resultado": "atordoado" if int(f.get("salvaguarda_constituicao", 0)) < cd else "resistiu",
                "custo_foco": 1,
                "cd": cd,
            }
        if recurso == "sobrevivente_disciplinado":
            return {
                "resultado": "sucesso" if f.get("gastou_foco", False) else "resistencia",
                "todos_testes_resistencia": True,
                "custo_foco": 1,
            }
        if recurso == "foco_perfeito":
            return {
                "resultado": "resolvido",
                "recuperar_foco_na_iniciativa": 4 if not f.get("foco_disponivel", 0) else 0,
            }
        if recurso == "defesa_superior":
            return {
                "resultado": "ativada",
                "custo_foco": 3,
                "resistencia_todos_danos_exceto_forca": True,
                "duracao": "ate_inicio_proximo_turno",
            }
        if recurso == "corpo_e_mente":
            return {"resultado": "resolvido", "bonus_destreza": 4, "bonus_sabedoria": 4, "maximo_atributo": 25}

    if classe == "ladino":
        if recurso == "acao_ardilosa":
            acao = f.get("acao", "")
            return {
                "resultado": "permitido" if acao in {"correr", "desengajar", "esconder"} else "bloqueado",
                "acao_bonus": acao,
            }
        if recurso == "mira_firme":
            return {
                "resultado": "resolvido",
                "vantagem_proximo_ataque": True,
                "deslocamento_zero": True,
                "limite": "um_ataque_neste_turno",
            }
        if recurso == "talento_confiavel":
            return {
                "resultado": "resolvido",
                "total": max(10, int(f.get("rolagem_d20", 0))) + int(f.get("bonus", 0)),
                "aplica": f.get("proficiente", False),
            }
        if recurso == "mente_escorregadia":
            return {"resultado": "resolvido", "prof_sabedoria": True, "prof_carisma": True}
        if recurso == "elusivo":
            return {"resultado": "resolvido", "inimigo_nao_tem_vantagem": not f.get("incapacitado", False)}
        if recurso == "golpe_de_sorte":
            return {"resultado": "20_natural", "transforma_falha": True, "recarga": "descanso_curto_ou_longo"}

    if classe == "bardo":
        if recurso == "inspiracao_de_bardo":
            dado = "d6" if nivel < 5 else "d8" if nivel < 10 else "d10" if nivel < 15 else "d12"
            return {
                "resultado": "concedida",
                "dado": dado,
                "usos": max(1, _mod(f.get("carisma", 10))),
                "alcance_m": 18,
                "duracao_min": 10,
            }
        if recurso == "pau_pra_toda_obra":
            return {"resultado": "resolvido", "bonus": _mod(f.get("carisma", 10)), "testes": "não_proficientes"}
        if recurso == "especialista":
            return {
                "resultado": "resolvido",
                "pericias_escolhidas": int(f.get("quantidade", 2)),
                "multiplicador_proficiencia": 2,
            }
        if recurso == "fonte_de_inspiracao":
            return {"resultado": "resolvido", "recupera_em": "descanso_curto_ou_longo", "dado": "inspiracao_de_bardo"}
        if recurso == "contra_encantamento":
            return {
                "resultado": "ativado",
                "vantagem": True,
                "aliados_alcance_m": 9,
                "efeito": "amedrontado_ou_enfeiticado",
            }
        if recurso == "inspiracao_superior":
            return {"resultado": "resolvido", "recupera_uso_ao_iniciativa": True}
        if recurso == "palavras_de_criacao":
            return {
                "resultado": "resolvido",
                "cd_aumentada": 2,
                "efeitos": ["incapacitado", "amedrontado", "enfeitiçado"],
            }

    if classe == "clerigo":
        if recurso == "ordem_divina":
            return {"resultado": "escolha", "opcoes": ["dominio_de_vida", "potencializar_cura"], "quantidade": 1}
        if recurso == "canalizar_divindade":
            return {
                "resultado": "resolvido",
                "usos": 2 if nivel < 6 else 3 if nivel < 18 else 4,
                "recupera_em": "descanso_curto_ou_longo",
            }
        if recurso == "fulminar_mortos_vivos":
            cd = 8 + int(f.get("bonus_proficiencia", 2)) + _mod(f.get("sabedoria", 10))
            return {
                "resultado": "destruido" if f.get("falhou_salvaguarda", False) and nivel >= 5 else "repelido",
                "cd": cd,
                "tipo": "morto_vivo",
            }
        if recurso == "golpes_abencoados":
            return {"resultado": "resolvido", "dano_extra": "1d8_radiante_ou_necrotico", "limite": "uma_vez_por_turno"}
        if recurso == "intervencao_divina":
            return {
                "resultado": "resolvido",
                "efeito": f.get("efeito", "milagre_divino"),
                "recarga": "descanso_longo",
                "sem_custo": nivel >= 20,
            }

    if classe == "druida":
        if recurso == "idioma_druidico":
            return {"resultado": "resolvido", "idioma": "druidico", "pode_falar_com_druidas": True}
        if recurso == "ordem_primal":
            return {"resultado": "escolha", "opcoes": ["mago", "combatente"], "beneficio": "truque_ou_armadura_leve"}
        if recurso == "companheiro_selvagem":
            return {"resultado": "conjurado", "custo": "uso_de_forma_selvagem", "duracao_horas": 1, "familiar": True}
        if recurso == "ressurgimento_selvagem":
            return {"resultado": "recuperado", "pontos_forma_selvagem": 1, "recarga": "descanso_curto_ou_longo"}
        if recurso == "furia_elemental":
            return {
                "resultado": "resolvido",
                "dano_extra": "1d8",
                "tipos": ["frio", "fogo", "eletricidade", "trovejante"],
            }
        if recurso == "magias_bestiais":
            return {"resultado": "resolvido", "pode_conjurar_em_forma_selvagem": True, "componentes_somaticos": True}
        if recurso == "arquidruida":
            return {"resultado": "resolvido", "forma_selvagem_usos": "ilimitados", "recupera_foco": True}

    if classe == "mago":
        if recurso == "recuperacao_arcana":
            return {
                "resultado": "recuperado",
                "circulos": min(5, (nivel + 1) // 2),
                "recarga": "descanso_curto_ou_longo",
                "uma_vez_por_dia": True,
            }
        if recurso == "adepto_de_ritual":
            return {"resultado": "resolvido", "pode_conjurar_rituais_do_livro": True, "sem_preparar": True}
        if recurso == "academico":
            return {
                "resultado": "resolvido",
                "especializacao": f.get("pericia", "historia"),
                "dobro_proficiencia": True,
            }
        if recurso == "memorizar_magia":
            return {"resultado": "resolvido", "troca_em_descanso_curto": True, "magias": 1}
        if recurso == "maestria_de_magias":
            return {
                "resultado": "resolvido",
                "magias_sem_espaco": int(f.get("quantidade", 2)),
                "recarga": "descanso_curto_ou_longo",
            }
        if recurso == "assinatura_magica":
            return {"resultado": "resolvido", "magias": 2, "circulo_maximo": 3, "uma_vez_sem_espaco": True}

    if classe == "feiticeiro":
        if recurso == "fonte_de_magia":
            return {"resultado": "resolvido", "pontos": nivel, "conversao": True, "recarga": "descanso_longo"}
        if recurso == "metamagia":
            return {"resultado": "resolvido", "pontos": nivel, "opcoes": 2 if nivel < 10 else 4 if nivel < 17 else 6}
        if recurso == "restauracao_feiticeira":
            return {"resultado": "recuperado", "pontos": nivel // 2, "recarga": "descanso_curto"}
        if recurso == "feiticaria_encarnada":
            return {"resultado": "ativada", "custo_pontos": 2, "duas_metamagias_na_mesma_magia": True}
        if recurso == "apoteose_arcana":
            return {"resultado": "resolvido", "metamagia_sem_custo": True, "uma_vez_por_turno": True}

    if classe == "bruxo":
        if recurso == "astucia_magica":
            return {
                "resultado": "recuperado",
                "espacos": max(1, int(f.get("espacos", 1)) // 2),
                "recarga": "descanso_longo",
                "acao": "minuto",
            }
        if recurso == "contatar_patrono":
            return {"resultado": "resolvido", "consulta": True, "telepatia": True, "recarga": "descanso_longo"}
        if recurso == "arcana_mistica":
            circulo = {11: 6, 13: 7, 15: 8, 17: 9}.get(nivel)
            return {
                "resultado": "resolvido" if circulo else "bloqueado",
                "circulo": circulo,
                "recarga": "descanso_longo",
            }
        if recurso == "mestre_mistico":
            return {"resultado": "resolvido", "invocacao_adicional": True, "recupera_espaco_pacto": True}

    if classe == "artifice":
        if recurso in {"conjuracao", "tinkers_magic"}:
            return {"resultado": "resolvido", "atributo_conjuracao": "inteligencia", "foco": "ferramentas_de_artifice"}
        if recurso in {"replicar_item_magico", "replicate_magic_item"}:
            return {
                "resultado": "infundido",
                "infusoes": 2 if nivel < 6 else 3 if nivel < 10 else 4,
                "itens": int(f.get("quantidade", 1)),
            }
        if recurso in {"flash_of_genius", "lampejo_de_genio"}:
            return {
                "resultado": "resolvido",
                "bonus": _mod(f.get("inteligencia", 10)),
                "usos": max(1, _mod(f.get("inteligencia", 10))),
                "reacao": True,
            }
        if recurso in {"spell_storing_item", "item_armazenador_de_magia"}:
            return {"resultado": "armazenado", "conjuracoes": 2 * _mod(f.get("inteligencia", 10)), "circulo_maximo": 2}
        if recurso in {"advanced_artifice", "artifice_avancado"}:
            return {"resultado": "resolvido", "itens_sintonizados_extra": 2, "bonus_todos_itens": 1}
        if recurso in {"soul_of_artifice", "alma_do_artifice"}:
            return {
                "resultado": "resolvido",
                "itens_sintonizados": 6,
                "bonus_salvaguardas_por_item": 1,
                "reacao_evitar_morte": True,
            }

    if classe == "paladino":
        if recurso == "maos_consagradas":
            pool_maximo = 5 * nivel
            pool_restante = int(f.get("pool_restante", pool_maximo))
            custo = int(f.get("custo", pool_restante))
            if pool_restante < 0 or pool_restante > pool_maximo:
                return {"resultado": "bloqueado", "motivo": "pool_de_cura_invalido", "pool_maximo": pool_maximo}
            if custo < 0 or custo > pool_restante:
                return {
                    "resultado": "bloqueado",
                    "motivo": "cura_excede_pool_disponivel",
                    "pool_restante": pool_restante,
                }
            return {
                "resultado": "cura",
                "pool_maximo": pool_maximo,
                "cura": custo,
                "pool_restante": pool_restante - custo,
                "acao": "bonus",
            }
        if recurso == "aura_de_protecao":
            return {
                "resultado": "resolvido",
                "bonus_salvaguardas": _mod(f.get("carisma", 10)),
                "alcance_m": int(f.get("alcance_m", 3)),
            }
        if recurso == "aura_de_coragem":
            return {"resultado": "resolvido", "imune_amedrontado": True, "alcance_m": int(f.get("alcance_m", 3))}
        if recurso == "golpes_radiantes":
            return {"resultado": "resolvido", "dano_extra": "1d8_radiante", "limite": "uma_vez_por_turno"}
        if recurso == "toque_restaurador":
            return {
                "resultado": "removida",
                "condicao": f.get("condicao"),
                "custo": 5,
                "condicoes": ["cego", "surdo", "paralisado", "envenenado", "amedrontado", "atordoado"],
            }

    if classe == "guardiao":
        if recurso == "errante":
            return {
                "resultado": "resolvido",
                "bonus_deslocamento_m": 3,
                "escalada_igual_deslocamento": True,
                "natacao_igual_deslocamento": True,
            }
        if recurso == "incansavel":
            return {
                "resultado": "resolvido",
                "pontos_de_vida_temporarios": max(1, _mod(f.get("sabedoria", 10))) + int(f.get("rolagem_d8", 0)),
                "reduzir_exaustao_no_descanso_curto": True,
            }
        if recurso == "sentidos_selvagens":
            return {"resultado": "resolvido", "sentido_as_cegas_m": 9}
        if recurso == "matador_de_inimigos_favoritos":
            return {"resultado": "resolvido", "dado_marca_do_predador": "d10"}

    classes_conhecidas = {
        "barbaro",
        "bardo",
        "clerigo",
        "druida",
        "guerreiro",
        "monge",
        "paladino",
        "guardiao",
        "ladino",
        "feiticeiro",
        "bruxo",
        "mago",
        "artifice",
    }
    if classe not in classes_conhecidas:
        return {"resultado": "bloqueado", "motivo": "classe_desconhecida", "classe": classe}
    return {
        "resultado": "nao_implementado",
        "caracteristica": recurso,
        "classe": classe,
        "nivel": nivel,
        "motivo": "caracteristica_catalogada_sem_resolver_especifico",
    }
