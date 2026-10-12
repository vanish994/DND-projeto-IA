"""Ações de exploração e interação social do PHB 2024."""

from __future__ import annotations

from typing import Any, Mapping

from .ability_checks import resolver_teste_habilidade

_INTERACOES = {
    "deception": "enganacao",
    "enganacao": "enganacao",
    "intimidation": "intimidacao",
    "intimidacao": "intimidacao",
    "performance": "atuacao",
    "atuacao": "atuacao",
    "persuasion": "persuasao",
    "persuasao": "persuasao",
    "animal_handling": "adestrar_animais",
    "adestrar_animais": "adestrar_animais",
    "adestramento": "adestrar_animais",
}


def resolver_acao_esconder(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a ação Esconder-se: cobertura/obscurecimento, fora da linha de visão e Furtividade CD 15."""
    cobertura = str(fatos.get("cobertura", fatos.get("cover", ""))).strip().lower().replace(" ", "_")
    obscurecido = bool(fatos.get("muito_obscurecido", fatos.get("heavily_obscured", False)))
    cobertura_valida = cobertura in {"tres_quartos", "three_quarters", "total", "total_cover"}
    if not obscurecido and not cobertura_valida:
        return {"resultado": "bloqueado", "motivo": "precisa_de_obscurecimento_total_ou_cobertura_de_tres_quartos"}
    fora_da_visao = bool(fatos.get("fora_da_linha_de_visao", fatos.get("out_of_enemy_line_of_sight", False)))
    if not fora_da_visao:
        return {"resultado": "bloqueado", "motivo": "deve_estar_fora_da_linha_de_visao_dos_inimigos"}
    dados = dict(fatos)
    dados["pericia"] = "furtividade"
    dados["cd"] = 15
    teste = resolver_teste_habilidade(dados)
    if teste.get("resultado") == "bloqueado":
        return teste
    sucesso = teste["resultado"] == "sucesso"
    return {
        "resultado": "escondido" if sucesso else "falha",
        "sucesso": sucesso,
        "condicao_invisivel_enquanto_escondido": sucesso,
        "dc_para_encontrar": teste["total"] if sucesso else None,
        "encerra_se": ["som_alto", "inimigo_encontra", "rolagem_de_ataque", "magia_com_componente_verbal"],
        "teste": teste,
    }


def resolver_acao_influenciar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Influenciar: disposto/indisposto sem teste; hesitante exige o teste social apropriado."""
    disposicao_raw = str(fatos.get("disposicao", fatos.get("willingness", "hesitante"))).strip().lower()
    aliases = {"willing": "disposto", "unwilling": "indisposto", "hesitant": "hesitante"}
    disposicao = aliases.get(disposicao_raw, disposicao_raw)
    atitude_raw = (
        str(fatos.get("atitude_monstro", fatos.get("monster_attitude", fatos.get("attitude", "indiferente"))))
        .strip()
        .lower()
    )
    atitude_aliases = {
        "friendly": "amigavel",
        "friendly_attitude": "amigavel",
        "hostile": "hostil",
        "hostile_attitude": "hostil",
        "indifferent": "indiferente",
    }
    atitude_monstro = atitude_aliases.get(atitude_raw, atitude_raw)
    if (
        disposicao_raw in {"friendly", "hostile", "indifferent"}
        and "disposicao" not in fatos
        and "willingness" not in fatos
    ):
        disposicao = "hesitante"
    if disposicao == "disposto":
        return {
            "resultado": "sucesso",
            "teste_realizado": False,
            "monstro_atende": True,
            "motivo": "pedido_alinhado_aos_desejos",
        }
    if disposicao == "indisposto":
        return {
            "resultado": "falha",
            "teste_realizado": False,
            "monstro_atende": False,
            "motivo": "pedido_repugnante_ou_contrario_aos_desejos",
        }
    if disposicao != "hesitante":
        return {"resultado": "bloqueado", "motivo": "disposicao_desconhecida"}
    interacao_raw = str(fatos.get("interacao", fatos.get("interaction", ""))).strip().lower().replace(" ", "_")
    pericia = _INTERACOES.get(interacao_raw)
    if pericia is None:
        return {"resultado": "bloqueado", "motivo": "interacao_social_desconhecida"}
    entende = bool(fatos.get("monstro_entende_voce", fatos.get("monster_understands_you", True)))
    if pericia in {"enganacao", "persuasao"} and not entende:
        return {"resultado": "bloqueado", "motivo": "monstro_nao_entende_a_interacao"}
    tipo_criatura = str(fatos.get("tipo_criatura", fatos.get("creature_type", ""))).strip().lower()
    if pericia == "adestrar_animais" and tipo_criatura not in {
        "besta",
        "bestia",
        "beast",
        "monstruosidade",
        "monstrosity",
    }:
        return {"resultado": "bloqueado", "motivo": "adestrar_animais_aplica_se_a_bestias_ou_monstruosidades"}
    cd = int(fatos.get("cd", max(15, int(fatos.get("inteligencia_monstro", fatos.get("monster_intelligence", 10))))))
    dados = dict(fatos)
    dados["pericia"] = pericia
    dados["cd"] = cd
    if atitude_monstro == "amigavel":
        dados["vantagem"] = True
    elif atitude_monstro == "hostil":
        dados["desvantagem"] = True
    teste = resolver_teste_habilidade(dados)
    if teste.get("resultado") == "bloqueado":
        return teste
    sucesso = teste["resultado"] == "sucesso"
    return {
        "resultado": "sucesso" if sucesso else "falha",
        "teste_realizado": True,
        "monstro_atende": sucesso,
        "cd": cd,
        "teste": teste,
        "pode_tentar_novamente_em_horas": None if sucesso else int(fatos.get("intervalo_tentativa_horas", 24)),
    }


def resolver_fim_esconderijo(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Aplica os eventos que encerram imediatamente o estado de escondido no PHB 2024."""
    escondido = bool(fatos.get("escondido", True))
    evento = str(fatos.get("evento", fatos.get("event", ""))).strip().lower().replace(" ", "_")
    aliases = {
        "loud_sound": "som_alto",
        "enemy_finds": "inimigo_encontra",
        "attack_roll": "rolagem_de_ataque",
        "verbal_spell": "magia_com_componente_verbal",
    }
    evento = aliases.get(evento, evento)
    encerra = evento in {
        "som_alto",
        "inimigo_encontra",
        "rolagem_de_ataque",
        "ataque",
        "magia_com_componente_verbal",
        "magia_verbal",
    }
    return {
        "resultado": (
            "esconderijo_encerrado" if escondido and encerra else "continua_escondido" if escondido else "nao_escondido"
        ),
        "escondido": escondido and not encerra,
        "evento": evento,
    }


def resolver_acao_procurar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Search com os pares Sabedoria (perícia) definidos no PHB 2024."""
    tipo = str(fatos.get("tipo_busca", fatos.get("search_for", ""))).strip().lower().replace(" ", "_")
    mapa = {
        "estado_mental": "intuicao",
        "mood": "intuicao",
        "intencoes": "intuicao",
        "doenca": "medicina",
        "ferimento": "medicina",
        "causa_da_morte": "medicina",
        "ailment": "medicina",
        "criatura_ou_objeto_escondido": "percepcao",
        "escondido": "percepcao",
        "concealed": "percepcao",
        "rastros": "sobrevivencia",
        "comida": "sobrevivencia",
        "tracks": "sobrevivencia",
        "food": "sobrevivencia",
    }
    pericia = mapa.get(tipo)
    if pericia is None:
        return {"resultado": "bloqueado", "motivo": "tipo_de_busca_desconhecido"}
    dados = dict(fatos)
    dados["pericia"] = pericia
    teste = resolver_teste_habilidade(dados)
    if teste.get("resultado") == "bloqueado":
        return teste
    sucesso = teste["resultado"] == "sucesso"
    return {
        "resultado": "encontrado" if sucesso else "nao_encontrado",
        "sucesso": sucesso,
        "pericia": pericia,
        "teste": teste,
    }


def resolver_acao_ajudar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Cria o efeito de Ajuda para um teste de perícia/ferramenta ou ataque."""
    tipo = str(fatos.get("tipo_ajuda", fatos.get("help_type", "habilidade"))).strip().lower()
    aliado_proximo = bool(fatos.get("aliado_proximo", fatos.get("ally_nearby", False)))
    if not aliado_proximo:
        return {"resultado": "bloqueado", "motivo": "aliado_fora_do_alcance_de_ajuda"}
    if tipo in {"habilidade", "ability_check", "pericia", "ferramenta", "tool"}:
        proficiente = bool(fatos.get("proficiente_ajudante", fatos.get("helper_proficient", False)))
        pericia = str(fatos.get("pericia", fatos.get("skill", ""))).strip().lower().replace(" ", "_")
        ferramenta = str(fatos.get("ferramenta", fatos.get("tool", ""))).strip()
        if not proficiente or not (pericia or ferramenta):
            return {
                "resultado": "bloqueado",
                "motivo": "ajudante_deve_escolher_pericia_ou_ferramenta_em_que_e_proficiente",
            }
        return {
            "resultado": "ajuda_preparada",
            "tipo_ajuda": "teste_habilidade",
            "pericia": pericia or None,
            "ferramenta": ferramenta or None,
            "vantagem_no_proximo_teste": True,
            "expira": "inicio_do_proximo_turno_do_ajudante",
        }
    if tipo in {"ataque", "attack_roll", "ataque_de_aliado"}:
        distancia = float(fatos.get("distancia_m", fatos.get("distance_m", 99)))
        if distancia > 1.5:
            return {"resultado": "bloqueado", "motivo": "inimigo_deve_estar_a_1_5_metros"}
        return {
            "resultado": "ajuda_preparada",
            "tipo_ajuda": "ataque",
            "alvo": fatos.get("alvo", fatos.get("target")),
            "vantagem_no_proximo_ataque": True,
            "expira": "inicio_do_proximo_turno_do_ajudante",
        }
    return {"resultado": "bloqueado", "motivo": "tipo_ajuda_desconhecido"}


def resolver_acao_estudar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Study com as perícias de Inteligência sugeridas pelo PHB 2024."""
    area = str(fatos.get("area_conhecimento", fatos.get("knowledge_area", ""))).strip().lower().replace(" ", "_")
    mapa = {
        "magia": "arcanismo",
        "itens_magicos": "arcanismo",
        "simbolos_magicos": "arcanismo",
        "planos": "arcanismo",
        "arcana": "arcanismo",
        "historia": "historia",
        "eventos_historicos": "historia",
        "civilizacoes": "historia",
        "guerras": "historia",
        "armadilhas": "investigacao",
        "cifras": "investigacao",
        "enigmas": "investigacao",
        "engenhocas": "investigacao",
        "terreno": "natureza",
        "flora": "natureza",
        "clima": "natureza",
        "nature": "natureza",
        "deuses": "religiao",
        "ritos": "religiao",
        "cultos": "religiao",
        "simbolos_sagrados": "religiao",
        "religion": "religiao",
    }
    pericia = mapa.get(area)
    if pericia is None:
        return {"resultado": "bloqueado", "motivo": "area_de_conhecimento_desconhecida"}
    dados = dict(fatos)
    dados["pericia"] = pericia
    teste = resolver_teste_habilidade(dados)
    if teste.get("resultado") == "bloqueado":
        return teste
    sucesso = teste["resultado"] == "sucesso"
    return {
        "resultado": "informacao_encontrada" if sucesso else "sem_informacao_nova",
        "sucesso": sucesso,
        "pericia": pericia,
        "teste": teste,
    }


def resolver_acao_esquivar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Aplica Esquivar até o início do próximo turno, se a criatura puder agir e tiver Deslocamento."""
    incapacitado = bool(fatos.get("incapacitado", fatos.get("incapacitated", False)))
    deslocamento = float(fatos.get("deslocamento", fatos.get("speed", 1)))
    if incapacitado or deslocamento <= 0:
        return {"resultado": "bloqueado", "motivo": "incapacitado_ou_deslocamento_zero"}
    return {
        "resultado": "esquivando",
        "esquivando": True,
        "vantagem_salvaguardas_destreza": True,
        "desvantagem_ataques_contra_voce_se_o_atacante_for_visivel": True,
        "dura_ate": "inicio_do_proximo_turno",
        "perde_beneficios_se": ["incapacitado", "deslocamento_zero"],
    }


__all__ = [
    "resolver_acao_esconder",
    "resolver_acao_influenciar",
    "resolver_fim_esconderijo",
    "resolver_acao_procurar",
    "resolver_acao_ajudar",
    "resolver_acao_estudar",
    "resolver_acao_esquivar",
]
