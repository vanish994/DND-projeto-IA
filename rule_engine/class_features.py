"""Características de classe executáveis do PHB 2024.

Este módulo mantém os recursos sem estado mutável: a aplicação fornece usos,
atributos e resultados da jogada, e recebe uma resolução determinística.
"""
from __future__ import annotations


def _mod(valor: int) -> int:
    return (int(valor) - 10) // 2


def resolver_caracteristica(f: dict) -> dict:
    classe = str(f.get("classe", f.get("class", ""))).lower()
    recurso = str(f.get("recurso", f.get("feature", ""))).lower().replace(" ", "_")
    nivel = int(f.get("nivel", f.get("level", 1)))
    if not 1 <= nivel <= 20:
        return {"resultado": "bloqueado", "motivo": "nivel_invalido"}

    if recurso in {"asi", "aumento_de_atributo", "aumento_de_atributo_ou_talento"}:
        atributo = f.get("atributo")
        talento = f.get("talento")
        if atributo and atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
            return {"resultado": "bloqueado", "motivo": "atributo_invalido"}
        if not atributo and not talento:
            return {"resultado": "bloqueado", "motivo": "escolha_obrigatoria"}
        if atributo and int(f.get("aumento", 1)) not in {1, 2}:
            return {"resultado": "bloqueado", "motivo": "aumento_deve_ser_um_ou_dois"}
        return {"resultado": "aplicado", "atributo": atributo, "aumento": int(f.get("aumento", 1)) if atributo else 0, "talento": talento}

    if classe == "barbaro":
        if recurso == "defesa_sem_armadura":
            return {"resultado": "resolvido", "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("constituicao", 10)), "usa_escudo": True}
        if recurso == "sentido_de_perigo":
            return {"resultado": "resolvido", "vantagem_salvaguarda_destreza": not f.get("cego", False) and not f.get("surdo", False) and not f.get("incapacitado", False)}
        if recurso == "conhecimento_primordial":
            return {"resultado": "resolvido", "pericias_forca_durante_furia": ["acrobacia", "intimidacao", "percepcao", "furtividade", "sobrevivencia"], "prof_expertise": f.get("pericia")}
        if recurso == "movimento_rapido":
            return {"resultado": "resolvido", "bonus_deslocamento_m": 3 if not f.get("armadura_pesada", False) else 0}
        if recurso == "furia_implacavel":
            cd = int(f.get("cd", 10))
            if int(f.get("salvaguarda_constituicao", -1)) < cd:
                return {"resultado": "bloqueado", "motivo": "falha_nao_salva_furia", "cd": cd, "cura": 2 * nivel, "recarga": "descanso_longo"}
            return {"resultado": "salvo", "cd": cd, "furia_continua": True, "aumentar_cd": 5}
        if recurso == "forca_indomavel":
            valor = int(f.get("resultado_forca", 0)); forca = int(f.get("forca", 10))
            return {"resultado": "resolvido", "total": max(valor, forca), "substitui_se_inferior": True}
        if recurso == "campeao_primitivo":
            return {"resultado": "resolvido", "bonus_forca": 4, "bonus_constituicao": 4, "maximo_atributo": 25}

    if classe == "guerreiro":
        if recurso in {"surto_de_acao", "surto_de_acao_aprimorado"}:
            return {"resultado": "resolvido", "acao_adicional": True, "pode_acao_magica": False, "usos": 2 if nivel >= 17 else 1, "limite_por_turno": 1}
        if recurso == "mente_tatica":
            return {"resultado": "resolvido", "bonus_teste": int(f.get("rolagem_d10", 0)) + _mod(f.get("constituicao", 10)), "gasta_recuperar_folego": True}
        if recurso in {"indomavel", "indomavel_aprimorado"}:
            usos = 3 if nivel >= 17 else 2 if nivel >= 13 else 1
            if f.get("sucesso", False):
                return {"resultado": "sucesso", "usos": usos}
            return {"resultado": "nova_rolagem", "bonus": nivel, "usos": usos}
        if recurso == "ajuste_tatico":
            return {"resultado": "resolvido", "movimento": "metade_do_deslocamento", "sem_ataque_de_oportunidade": True}
        if recurso == "ataques_estudados":
            return {"resultado": "resolvido", "vantagem_proximo_ataque": not f.get("acertou", True), "alvo": f.get("alvo")}

    if classe == "monge":
        if recurso == "defesa_sem_armadura":
            return {"resultado": "resolvido", "ca": 10 + _mod(f.get("destreza", 10)) + _mod(f.get("sabedoria", 10)), "usa_armadura": False, "usa_escudo": False}
        if recurso == "artes_marciais":
            dado = "d6" if nivel < 5 else "d8" if nivel < 11 else "d10" if nivel < 17 else "d12"
            return {"resultado": "resolvido", "dado": dado, "ataque_desarmado_bonus": True, "usa_destreza": True}
        if recurso == "queda_lenta":
            return {"resultado": "resolvido", "reducao": 5 * nivel, "usa_reacao": True}
        if recurso == "golpe_atordoante":
            cd = 8 + int(f.get("bonus_proficiencia", 2)) + _mod(f.get("sabedoria", 10))
            return {"resultado": "atordoado" if int(f.get("salvaguarda_constituicao", 0)) < cd else "resistiu", "custo_foco": 1, "cd": cd}
        if recurso == "sobrevivente_disciplinado":
            return {"resultado": "sucesso" if f.get("gastou_foco", False) else "resistencia", "todos_testes_resistencia": True, "custo_foco": 1}
        if recurso == "foco_perfeito":
            return {"resultado": "resolvido", "recuperar_foco_na_iniciativa": 4 if not f.get("foco_disponivel", 0) else 0}
        if recurso == "defesa_superior":
            return {"resultado": "ativada", "custo_foco": 3, "resistencia_todos_danos_exceto_forca": True, "duracao": "ate_inicio_proximo_turno"}
        if recurso == "corpo_e_mente":
            return {"resultado": "resolvido", "bonus_destreza": 4, "bonus_sabedoria": 4, "maximo_atributo": 25}

    if classe == "ladino":
        if recurso == "acao_ardilosa":
            acao = f.get("acao", "")
            return {"resultado": "permitido" if acao in {"correr", "desengajar", "esconder"} else "bloqueado", "acao_bonus": acao}
        if recurso == "mira_firme":
            return {"resultado": "resolvido", "vantagem_proximo_ataque": True, "deslocamento_zero": True, "limite": "um_ataque_neste_turno"}
        if recurso == "talento_confiavel":
            return {"resultado": "resolvido", "total": max(10, int(f.get("rolagem_d20", 0))) + int(f.get("bonus", 0)), "aplica": f.get("proficiente", False)}
        if recurso == "mente_escorregadia":
            return {"resultado": "resolvido", "prof_sabedoria": True, "prof_carisma": True}
        if recurso == "elusivo":
            return {"resultado": "resolvido", "inimigo_nao_tem_vantagem": not f.get("incapacitado", False)}
        if recurso == "golpe_de_sorte":
            return {"resultado": "20_natural", "transforma_falha": True, "recarga": "descanso_curto_ou_longo"}

    if classe == "paladino":
        if recurso == "maos_consagradas":
            pool = 5 * nivel
            return {"resultado": "cura", "pool_maximo": pool, "cura": min(int(f.get("custo", pool)), pool), "acao": "bonus"}
        if recurso == "aura_de_protecao":
            return {"resultado": "resolvido", "bonus_salvaguardas": _mod(f.get("carisma", 10)), "alcance_m": int(f.get("alcance_m", 3))}
        if recurso == "aura_de_coragem":
            return {"resultado": "resolvido", "imune_amedrontado": True, "alcance_m": int(f.get("alcance_m", 3))}
        if recurso == "golpes_radiantes":
            return {"resultado": "resolvido", "dano_extra": "1d8_radiante", "limite": "uma_vez_por_turno"}
        if recurso == "toque_restaurador":
            return {"resultado": "removida", "condicao": f.get("condicao"), "custo": 5, "condicoes": ["cego", "surdo", "paralisado", "envenenado", "amedrontado", "atordoado"]}

    if classe == "guardiao":
        if recurso == "errante":
            return {"resultado": "resolvido", "bonus_deslocamento_m": 3, "escalada_igual_deslocamento": True, "natacao_igual_deslocamento": True}
        if recurso == "incansavel":
            return {"resultado": "resolvido", "pontos_de_vida_temporarios": max(1, _mod(f.get("sabedoria", 10))) + int(f.get("rolagem_d8", 0)), "reduzir_exaustao_no_descanso_curto": True}
        if recurso == "sentidos_selvagens":
            return {"resultado": "resolvido", "sentido_as_cegas_m": 9}
        if recurso == "matador_de_inimigos_favoritos":
            return {"resultado": "resolvido", "dado_marca_do_predador": "d10"}

    return {"resultado": "resolvido", "caracteristica": recurso, "classe": classe, "nivel": nivel}
