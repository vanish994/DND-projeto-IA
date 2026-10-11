"""Ações de exploração e interação social do PHB 2024."""
from __future__ import annotations

from typing import Any, Mapping

from .ability_checks import resolver_teste_habilidade

_INTERACOES = {
    "deception": "enganacao", "enganacao": "enganacao",
    "intimidation": "intimidacao", "intimidacao": "intimidacao",
    "performance": "atuacao", "atuacao": "atuacao",
    "persuasion": "persuasao", "persuasao": "persuasao",
    "animal_handling": "adestrar_animais", "adestrar_animais": "adestrar_animais", "adestramento": "adestrar_animais",
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
        "resultado": "escondido" if sucesso else "falha", "sucesso": sucesso,
        "condicao_invisivel_enquanto_escondido": sucesso,
        "dc_para_encontrar": teste["total"] if sucesso else None,
        "encerra_se": ["som_alto", "inimigo_encontra", "rolagem_de_ataque", "magia_com_componente_verbal"],
        "teste": teste,
    }

def resolver_acao_influenciar(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve Influenciar: disposto/indisposto sem teste; hesitante exige o teste social apropriado."""
    atitude = str(fatos.get("disposicao", fatos.get("attitude", "hesitante"))).strip().lower()
    aliases = {"willing": "disposto", "unwilling": "indisposto", "hesitant": "hesitante", "friendly": "amigavel", "hostile": "hostil", "indifferent": "indiferente"}
    atitude = aliases.get(atitude, atitude)
    if atitude in {"disposto", "amigavel_disposto"}:
        return {"resultado": "sucesso", "teste_realizado": False, "monstro_atende": True, "motivo": "pedido_alinhado_aos_desejos"}
    if atitude in {"indisposto", "hostil_indisposto"}:
        return {"resultado": "falha", "teste_realizado": False, "monstro_atende": False, "motivo": "pedido_repugnante_ou_contrario_aos_desejos"}
    if atitude not in {"hesitante", "amigavel", "hostil", "indiferente"}:
        return {"resultado": "bloqueado", "motivo": "disposicao_desconhecida"}
    interacao_raw = str(fatos.get("interacao", fatos.get("interaction", ""))).strip().lower().replace(" ", "_")
    pericia = _INTERACOES.get(interacao_raw)
    if pericia is None:
        return {"resultado": "bloqueado", "motivo": "interacao_social_desconhecida"}
    entende = bool(fatos.get("monstro_entende_voce", fatos.get("monster_understands_you", True)))
    if pericia in {"enganacao", "persuasao"} and not entende:
        return {"resultado": "bloqueado", "motivo": "monstro_nao_entende_a_interacao"}
    tipo_criatura = str(fatos.get("tipo_criatura", fatos.get("creature_type", ""))).strip().lower()
    if pericia == "adestrar_animais" and tipo_criatura not in {"besta", "bestia", "beast", "monstruosidade", "monstrosity"}:
        return {"resultado": "bloqueado", "motivo": "adestrar_animais_aplica_se_a_bestias_ou_monstruosidades"}
    cd = int(fatos.get("cd", max(15, int(fatos.get("inteligencia_monstro", fatos.get("monster_intelligence", 10)))))
    dados = dict(fatos)
    dados["pericia"] = pericia
    dados["cd"] = cd
    teste = resolver_teste_habilidade(dados)
    if teste.get("resultado") == "bloqueado":
        return teste
    sucesso = teste["resultado"] == "sucesso"
    return {
        "resultado": "sucesso" if sucesso else "falha", "teste_realizado": True,
        "monstro_atende": sucesso, "cd": cd, "teste": teste,
        "pode_tentar_novamente_em_horas": None if sucesso else int(fatos.get("intervalo_tentativa_horas", 24)),
    }

__all__ = ["resolver_acao_esconder", "resolver_acao_influenciar"]