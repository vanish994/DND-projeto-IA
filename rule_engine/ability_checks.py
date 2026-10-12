"""Testes de habilidade, perícias, testes passivos, testes em grupo e Inspiração Heroica (PHB 2024)."""

from __future__ import annotations

from math import ceil
from typing import Any, Mapping

from .core import bonus_proficiencia as calcular_bonus_proficiencia
from .core import modificador_atributo, resolver_teste_d20

PERICIAS = {
    "acrobacia": "destreza",
    "adestrar_animais": "sabedoria",
    "arcanismo": "inteligencia",
    "atletismo": "forca",
    "atuacao": "carisma",
    "enganacao": "carisma",
    "furtividade": "destreza",
    "historia": "inteligencia",
    "intuicao": "sabedoria",
    "intimidacao": "carisma",
    "investigacao": "inteligencia",
    "medicina": "sabedoria",
    "natureza": "inteligencia",
    "percepcao": "sabedoria",
    "persuasao": "carisma",
    "prestidigitacao": "destreza",
    "religiao": "inteligencia",
    "sobrevivencia": "sabedoria",
}

CDS_PADRAO = {5: "muito_facil", 10: "facil", 15: "media", 20: "dificil", 25: "muito_dificil", 30: "quase_impossivel"}

_ATRIBUTOS = {
    "for": "forca",
    "strength": "forca",
    "forca": "forca",
    "des": "destreza",
    "dexterity": "destreza",
    "destreza": "destreza",
    "con": "constituicao",
    "constitution": "constituicao",
    "constituicao": "constituicao",
    "int": "inteligencia",
    "intelligence": "inteligencia",
    "inteligencia": "inteligencia",
    "sab": "sabedoria",
    "wisdom": "sabedoria",
    "sabedoria": "sabedoria",
    "car": "carisma",
    "charisma": "carisma",
    "carisma": "carisma",
}


def _normalizar_pericia(valor: Any) -> str:
    nome = str(valor).strip().lower().replace(" ", "_")
    aliases = {
        "adestramento": "adestrar_animais",
        "animal_handling": "adestrar_animais",
        "sleight_of_hand": "prestidigitacao",
        "performance": "atuacao",
        "deception": "enganacao",
        "stealth": "furtividade",
        "history": "historia",
        "insight": "intuicao",
        "intimidation": "intimidacao",
        "investigation": "investigacao",
        "medicine": "medicina",
        "nature": "natureza",
        "perception": "percepcao",
        "persuasion": "persuasao",
        "religion": "religiao",
        "survival": "sobrevivencia",
        "acrobatics": "acrobacia",
        "athletics": "atletismo",
        "arcana": "arcanismo",
    }
    return aliases.get(nome, nome)


def _int(value: Any, default: int = 0) -> int:
    return default if value is None else int(value)


def _atributo_e_modificador(fatos: Mapping[str, Any], pericia: str | None = None) -> tuple[str | None, int]:
    atributo_bruto = fatos.get("atributo") or fatos.get("ability")
    atributo = (
        _ATRIBUTOS.get(str(atributo_bruto).lower(), str(atributo_bruto).lower())
        if atributo_bruto
        else PERICIAS.get(pericia or "")
    )
    if "modificador_atributo" in fatos:
        modificador = int(fatos["modificador_atributo"])
    elif "valor_atributo" in fatos:
        modificador = modificador_atributo(int(fatos["valor_atributo"]))
    elif "ability_score" in fatos:
        modificador = modificador_atributo(int(fatos["ability_score"]))
    else:
        modificador = 0
    return atributo, modificador


def _bonus_prof(fatos: Mapping[str, Any]) -> int:
    if "bonus_proficiencia" in fatos:
        return int(fatos["bonus_proficiencia"])
    nivel = fatos.get("nivel", fatos.get("level"))
    return calcular_bonus_proficiencia(int(nivel)) if nivel is not None else 0


def _modificadores(fatos: Mapping[str, Any], pericia: str | None = None) -> dict[str, Any]:
    atributo, mod_atributo = _atributo_e_modificador(fatos, pericia)
    proficiente = bool(
        fatos.get(
            "proficiente",
            fatos.get("proficient", fatos.get("proficiente_pericia", fatos.get("skill_proficient", False))),
        )
    )
    expertise = bool(fatos.get("expertise", fatos.get("especialista", False)))
    proficiente = proficiente or expertise
    pb = _bonus_prof(fatos)
    # Proficiência de várias fontes nunca acumula; Especialização duplica o bônus uma única vez.
    mod_prof = pb * (2 if expertise else 1) if proficiente else 0
    circunstancias = fatos.get("modificadores_circunstanciais", fatos.get("situational_modifiers", [])) or []
    if not isinstance(circunstancias, (list, tuple)):
        circunstancias = [circunstancias]
    total_circunstancial = sum(
        int(x.get("valor", x.get("modifier", 0))) if isinstance(x, Mapping) else int(x) for x in circunstancias
    )
    extra = _int(fatos.get("modificador_extra", fatos.get("extra_modifier", 0)))
    ferramenta = bool(fatos.get("proficiente_ferramenta", fatos.get("tool_proficient", False)))
    pericia_prof = bool(fatos.get("proficiente_pericia", fatos.get("skill_proficient", proficiente)))
    vantagem = bool(fatos.get("vantagem", fatos.get("advantage", False)))
    desvantagem = bool(fatos.get("desvantagem", fatos.get("disadvantage", False)))
    if ferramenta and pericia_prof:
        vantagem = True
    fontes_v = fatos.get("fontes_vantagem", []) or []
    fontes_d = fatos.get("fontes_desvantagem", []) or []
    vantagem = vantagem or bool(fontes_v)
    desvantagem = desvantagem or bool(fontes_d)
    if vantagem and desvantagem:
        vantagem = False
        desvantagem = False
    return {
        "atributo": atributo,
        "modificador_atributo": mod_atributo,
        "bonus_proficiencia_aplicado": mod_prof,
        "proficiente": proficiente,
        "expertise": expertise,
        "modificador_circunstancial": total_circunstancial,
        "modificador_extra": extra,
        "modificador_total": mod_atributo + mod_prof + total_circunstancial + extra,
        "vantagem": vantagem,
        "desvantagem": desvantagem,
        "vantagem_por_pericia_e_ferramenta": ferramenta and pericia_prof,
    }


def _validar_modificadores(fatos: Mapping[str, Any]) -> str | None:
    if not any(fatos.get(k) is not None for k in ("modificador_atributo", "valor_atributo", "ability_score")):
        return "modificador_de_atributo_ausente"
    proficiente = bool(
        fatos.get(
            "proficiente",
            fatos.get("proficient", fatos.get("proficiente_pericia", fatos.get("skill_proficient", False))),
        )
    )
    expertise = bool(fatos.get("expertise", fatos.get("especialista", False)))
    if (
        (proficiente or expertise)
        and fatos.get("bonus_proficiencia") is None
        and fatos.get("nivel", fatos.get("level")) is None
    ):
        return "bonus_de_proficiencia_ausente"
    return None


def _cd(fatos: Mapping[str, Any]) -> int | None:
    valor = fatos.get("cd", fatos.get("dc"))
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip().isdigit():
        inverso = {nome: cd for cd, nome in CDS_PADRAO.items()}
        return inverso.get(valor.strip().lower().replace(" ", "_"))
    return int(valor)


def resolver_teste_habilidade(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve um teste ativo com atributo, perícia, proficiência e modificadores explícitos."""
    pericia_raw = fatos.get("pericia", fatos.get("skill"))
    pericia = _normalizar_pericia(pericia_raw) if pericia_raw else None
    if pericia and pericia not in PERICIAS:
        return {"resultado": "bloqueado", "motivo": "pericia_desconhecida", "pericia": pericia}
    if not any(k in fatos for k in ("roll", "dado", "dados", "rolls")):
        return {"resultado": "bloqueado", "motivo": "resultado_de_d20_ausente"}
    erro_mod = _validar_modificadores(fatos)
    if erro_mod:
        return {"resultado": "bloqueado", "motivo": erro_mod}
    cd = _cd(fatos)
    if cd is None:
        return {"resultado": "bloqueado", "motivo": "cd_ausente"}
    mod = _modificadores(fatos, pericia)
    dados = fatos.get("dados", fatos.get("rolls"))
    dado_unico = fatos.get("roll", fatos.get("dado"))
    if dados is None:
        dados = [int(dado_unico)]
    try:
        resolucao = resolver_teste_d20(
            dados, modificador=mod["modificador_total"], cd=cd, vantagem=mod["vantagem"], desvantagem=mod["desvantagem"]
        )
    except (TypeError, ValueError) as exc:
        return {"resultado": "bloqueado", "motivo": "rolagem_invalida", "detalhe": str(exc)}
    total = resolucao.total
    natural = resolucao.dado_selecionado
    sucesso = natural == 20 or (natural != 1 and total >= cd)
    if natural == 1:
        sucesso = False
    return {
        "resultado": "sucesso" if sucesso else "falha",
        "sucesso": sucesso,
        "pericia": pericia,
        "atributo": mod["atributo"],
        "dado": natural,
        "dados_rolados": list(resolucao.dados_rolados),
        "total": total,
        "cd": cd,
        "motivo": "20_natural" if natural == 20 else "1_natural" if natural == 1 else "total_vs_cd",
        **mod,
    }


def resolver_teste_passivo(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Calcula um teste passivo: 10 + modificadores, com +5/-5 por vantagem/desvantagem."""
    pericia_raw = fatos.get("pericia", fatos.get("skill"))
    pericia = _normalizar_pericia(pericia_raw) if pericia_raw else None
    if pericia and pericia not in PERICIAS:
        return {"resultado": "bloqueado", "motivo": "pericia_desconhecida", "pericia": pericia}
    erro_mod = _validar_modificadores(fatos)
    if erro_mod:
        return {"resultado": "bloqueado", "motivo": erro_mod}
    cd = _cd(fatos)
    mod = _modificadores(fatos, pericia)
    ajuste = (
        5 if mod["vantagem"] and not mod["desvantagem"] else -5 if mod["desvantagem"] and not mod["vantagem"] else 0
    )
    score = 10 + mod["modificador_total"] + ajuste
    return {
        "resultado": "calculado" if cd is None else "sucesso" if score >= cd else "falha",
        "pericia": pericia,
        "atributo": mod["atributo"],
        "valor_passivo": score,
        "cd": cd,
        "ajuste_vantagem_desvantagem": ajuste,
        **mod,
    }


def resolver_teste_grupo(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Um teste em grupo é bem-sucedido quando pelo menos metade do grupo obtém sucesso."""
    participantes = fatos.get("participantes", fatos.get("results", []))
    if not isinstance(participantes, (list, tuple)) or not participantes:
        return {"resultado": "bloqueado", "motivo": "participantes_ausentes"}
    sucessos = 0
    for item in participantes:
        if isinstance(item, Mapping):
            if "sucesso" in item:
                ok = bool(item["sucesso"])
            elif "success" in item:
                ok = bool(item["success"])
            elif "total" in item and ("cd" in item or "dc" in item):
                ok = int(item["total"]) >= int(item.get("cd", item.get("dc")))
            else:
                return {"resultado": "bloqueado", "motivo": "resultado_de_participante_incompleto"}
        else:
            ok = bool(item)
        sucessos += int(ok)
    necessario = ceil(len(participantes) / 2)
    return {
        "resultado": "sucesso" if sucessos >= necessario else "falha",
        "sucessos": sucessos,
        "participantes": len(participantes),
        "sucessos_necessarios": necessario,
    }


def resolver_inspiracao_heroica(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Gasta Inspiração Heroica para rerrolar um d20 e usa obrigatoriamente o novo resultado."""
    if not bool(fatos.get("tem_inspiracao_heroica", fatos.get("has_heroic_inspiration", False))):
        return {"resultado": "bloqueado", "motivo": "sem_inspiracao_heroica"}
    if "rerrolagem" not in fatos and "reroll" not in fatos:
        return {"resultado": "bloqueado", "motivo": "novo_d20_ausente"}
    if not bool(fatos.get("imediatamente_apos_rolar", fatos.get("immediate", True))):
        return {"resultado": "bloqueado", "motivo": "inspiracao_deve_ser_gasta_imediatamente"}
    original = int(fatos.get("dado_original", fatos.get("original", 0)))
    novo = int(fatos.get("rerrolagem", fatos.get("reroll", 0)))
    lados = fatos.get("lados_dado", fatos.get("die_sides"))
    if (
        original < 1
        or novo < 1
        or (lados is not None and (int(lados) < 2 or original > int(lados) or novo > int(lados)))
    ):
        return {"resultado": "bloqueado", "motivo": "resultado_fora_do_intervalo_do_dado"}
    return {
        "resultado": "resolvido",
        "dado_anterior": original,
        "dado_usado": novo,
        "lados_dado": int(lados) if lados is not None else None,
        "inspiracao_heroica_consumida": True,
    }


def resolver_salvaguarda(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve uma salvaguarda com atributo e proficiência da classe/personagem."""
    bruto = fatos.get("atributo", fatos.get("ability"))
    atributo = _ATRIBUTOS.get(str(bruto).strip().lower(), str(bruto).strip().lower()) if bruto is not None else None
    if atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
        return {"resultado": "bloqueado", "motivo": "atributo_de_salvaguarda_ausente_ou_invalido"}
    if not any(k in fatos for k in ("roll", "dado", "dados", "rolls")):
        return {"resultado": "bloqueado", "motivo": "resultado_de_d20_ausente"}
    if (
        atributo == "destreza"
        and bool(fatos.get("esquivando", fatos.get("dodging", False)))
        and not bool(fatos.get("incapacitado", fatos.get("incapacitated", False)))
        and float(fatos.get("deslocamento", fatos.get("speed", 1))) > 0
    ):
        fatos = {**fatos, "vantagem": True}
    profs = fatos.get("proficiencias_salvaguarda", fatos.get("saving_throw_proficiencies", [])) or []
    if isinstance(profs, str):
        profs = [profs]
    profs_norm = {_ATRIBUTOS.get(str(x).strip().lower(), str(x).strip().lower()) for x in profs}
    dados = dict(fatos)
    dados["atributo"] = atributo
    dados["proficiente"] = bool(fatos.get("proficiente", fatos.get("proficient", atributo in profs_norm)))
    dados["pericia"] = None
    resultado = resolver_teste_habilidade(dados)
    resultado["tipo_teste"] = "salvaguarda"
    resultado["atributo"] = atributo
    return resultado


def resolver_iniciativa(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve iniciativa como teste de Destreza ou por escore de iniciativa."""
    if not any(
        fatos.get(k) is not None
        for k in ("modificador_atributo", "valor_atributo", "ability_score", "modificador_destreza", "valor_destreza")
    ):
        return {"resultado": "bloqueado", "motivo": "modificador_de_destreza_ausente"}
    dados = dict(fatos)
    if "modificador_destreza" in dados:
        mod_destreza = int(dados["modificador_destreza"])
    elif "valor_destreza" in dados:
        mod_destreza = modificador_atributo(int(dados["valor_destreza"]))
    else:
        _, mod_destreza = _atributo_e_modificador({**dados, "atributo": "destreza"})
    condicoes = dados.get("condicoes", dados.get("conditions", [])) or []
    if isinstance(condicoes, str):
        condicoes = [condicoes]
    condicoes_norm = {str(x).strip().lower().replace(" ", "_") for x in condicoes}
    surpreendido = bool(dados.get("surpreendido", dados.get("surprised", False)))
    incapacitado = bool(dados.get("incapacitado", dados.get("incapacitated", False))) or bool(
        {"incapacitado", "incapacitated"} & condicoes_norm
    )
    invisivel = bool(dados.get("invisivel", dados.get("invisible", False))) or bool(
        {"invisivel", "invisible"} & condicoes_norm
    )
    vantagem = bool(dados.get("vantagem", dados.get("advantage", False))) or invisivel
    desvantagem = bool(dados.get("desvantagem", dados.get("disadvantage", False))) or surpreendido or incapacitado
    if vantagem and desvantagem:
        vantagem = False
        desvantagem = False
    extra_iniciativa = _int(dados.get("bonus_iniciativa", 0))
    if bool(dados.get("usar_escore", dados.get("use_score", False))):
        ajuste = 5 if vantagem else -5 if desvantagem else 0
        total = 10 + mod_destreza + extra_iniciativa + ajuste
        return {
            "resultado": "resolvido",
            "atributo": "destreza",
            "metodo": "escore",
            "iniciativa": total,
            "total": total,
            "bonus_iniciativa": extra_iniciativa,
            "ajuste_vantagem_desvantagem": ajuste,
            "vantagem": vantagem,
            "desvantagem": desvantagem,
        }
    if not any(k in fatos for k in ("roll", "dado", "dados", "rolls")):
        return {"resultado": "bloqueado", "motivo": "resultado_de_d20_ausente"}
    condicoes = dados.get("condicoes", dados.get("conditions", [])) or []
    if isinstance(condicoes, str):
        condicoes = [condicoes]
    condicoes_norm = {str(x).strip().lower().replace(" ", "_") for x in condicoes}
    surpreendido = bool(dados.get("surpreendido", dados.get("surprised", False)))
    incapacitado = bool(dados.get("incapacitado", dados.get("incapacitated", False))) or bool(
        {"incapacitado", "incapacitated"} & condicoes_norm
    )
    invisivel = bool(dados.get("invisivel", dados.get("invisible", False))) or bool(
        {"invisivel", "invisible"} & condicoes_norm
    )
    if surpreendido or incapacitado:
        dados["desvantagem"] = True
    if invisivel:
        dados["vantagem"] = True
    dados["atributo"] = "destreza"
    if "modificador_atributo" not in dados and "valor_atributo" not in dados and "ability_score" not in dados:
        dados["modificador_atributo"] = int(dados["modificador_destreza"])
    erro_mod = _validar_modificadores(dados)
    if erro_mod:
        return {"resultado": "bloqueado", "motivo": erro_mod}
    mod = _modificadores(dados)
    extra_iniciativa = _int(dados.get("bonus_iniciativa", 0))
    rolagens = dados.get("dados", dados.get("rolls"))
    if rolagens is None:
        rolagens = [int(dados.get("roll", dados.get("dado")))]
    try:
        resolucao = resolver_teste_d20(
            rolagens,
            modificador=mod["modificador_total"] + extra_iniciativa,
            vantagem=mod["vantagem"],
            desvantagem=mod["desvantagem"],
        )
    except (TypeError, ValueError) as exc:
        return {"resultado": "bloqueado", "motivo": "rolagem_invalida", "detalhe": str(exc)}
    return {
        "resultado": "resolvido",
        "atributo": "destreza",
        "dado": resolucao.dado_selecionado,
        "dados_rolados": list(resolucao.dados_rolados),
        "total": resolucao.total,
        "bonus_iniciativa": extra_iniciativa,
        **mod,
    }


__all__ = [
    "PERICIAS",
    "CDS_PADRAO",
    "resolver_teste_habilidade",
    "resolver_teste_passivo",
    "resolver_teste_grupo",
    "resolver_inspiracao_heroica",
    "resolver_salvaguarda",
    "resolver_iniciativa",
]
