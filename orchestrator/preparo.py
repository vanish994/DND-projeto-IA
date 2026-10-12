"""Preparo mecânico: transforma ficha e catálogo em fatos para o motor.

Esta é a parte do Orquestrador de Ações que **deriva** o que o MJ não pode
inventar: modificador de atributo, proficiência, atributo de conjuração, CD de
magia, CA do alvo e os dados de dano do catálogo.

Regra de fronteira: aqui não se decide regra. Quando o dado oficial já existe
no Rule Engine, o preparo apenas monta os fatos e deixa o motor resolver.
Quando falta, devolve ``bloqueado`` com o motivo — nunca um palpite.
"""

from __future__ import annotations

from typing import Any, Mapping

from rule_engine import RuleEngine
from rule_engine.bestiary import consultar_monstro
from rule_engine.casting import atributo_de_conjuracao
from rule_engine.damage import aplicar_defesas_monstro
from rule_engine.species import HERANCA_DRACONICA, bloco_heranca_draconica
from rule_engine.spellcasting import normalizar_nome_magia
from rule_engine.spells import mecanica_de_magia, obter_magia

from .rolagens import normalizar_rolagem

ATAQUE_DE_SOPRO_FERRAMENTA = "Ataque de Sopro"


def modificador_do_atributo(personagem: Mapping[str, Any], atributo: str) -> int | None:
    """Modificador do atributo usando a ficha; calcula só se o valor bruto existir."""
    modificadores = personagem.get("modificadores") or {}
    if atributo in modificadores:
        return int(modificadores[atributo])
    atributos = personagem.get("atributos") or {}
    if atributo in atributos:
        return (int(atributos[atributo]) - 10) // 2
    return None


def normalizar_texto(valor: Any) -> str:
    """Compara nomes de mesa sem acento, caixa ou espaço duplicado."""
    import unicodedata

    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.replace("_", " ").split())


# Nomes com que mesa e ficha costumam chamar o traço do Draconato. O traço
# não é arma do catálogo: ele resolve por salvaguarda de Destreza em área.
NOMES_ATAQUE_DE_SOPRO = (
    "arma de sopro",
    "ataque de sopro",
    "sopro",
    "sopro de dragao",
    "sopro do dragao",
)


def preparar_ataque_de_magia(
    engine: RuleEngine,
    facts: dict[str, Any],
    personagem: Mapping[str, Any],
) -> dict[str, Any]:
    """Deriva bônus de ataque e dano de um truque/magia a partir do catálogo.

    O modelo informa apenas ``magia`` e ``target_name``: o atributo de
    conjuração vem da ficha, a proficiência vem da ficha, a CA vem do
    bestiário e o dano vem da mecânica estruturada da magia. Nada disso é
    inventado pelo MJ.
    """
    nome = str(facts.get("magia", facts.get("spell", ""))).strip()
    magia = obter_magia(nome)
    if not magia:
        return {"resultado": "bloqueado", "motivo": "magia_desconhecida", "magia": nome}
    circulo = magia.get("circulo")
    if circulo is None:
        return {
            "resultado": "bloqueado",
            "motivo": "magia_sem_circulo_confirmado_no_catalogo",
            "magia": magia["nome"],
        }

    nome_canonico = str(magia["nome"])
    conjuracao = personagem.get("conjuracao") or {}
    chave_magia = normalizar_nome_magia(nome_canonico)
    if circulo == 0:
        registradas = conjuracao.get("truques") or []
    else:
        registradas = conjuracao.get("magias_preparadas") or conjuracao.get("magias") or []
    registradas = {normalizar_nome_magia(n) for n in registradas}
    if not registradas:
        return {
            "resultado": "bloqueado",
            "motivo": "magia_nao_registrada_na_ficha",
            "magia": nome_canonico,
            "dica": "Registre o truque ou a magia na ficha antes de conjurar.",
        }
    if chave_magia not in registradas:
        return {"resultado": "bloqueado", "motivo": "magia_nao_registrada_na_ficha", "magia": nome_canonico}

    nivel = max(1, int(personagem.get("nivel", 1) or 1))
    mecanica = mecanica_de_magia(nome_canonico, nivel_personagem=nivel)
    if not mecanica:
        return {
            "resultado": "bloqueado",
            "motivo": "magia_sem_mecanica_estruturada_no_catalogo",
            "magia": nome_canonico,
            "dica": "O catálogo ainda não tem dados de dano para esta magia; não narre dano oficial.",
        }
    if str(mecanica.get("tipo")) != "ataque_magico":
        return {
            "resultado": "bloqueado",
            "motivo": "magia_nao_resolve_por_jogada_de_ataque",
            "magia": nome_canonico,
            "tipo_de_mecanica": mecanica.get("tipo"),
            "dica": "Esta magia não usa jogada de ataque; resolva pelo efeito próprio dela.",
        }

    atributo = atributo_de_conjuracao(engine, personagem)
    if not atributo:
        return {
            "resultado": "bloqueado",
            "motivo": "atributo_de_conjuracao_ausente_na_ficha",
            "classe": personagem.get("classe"),
        }
    modificador = modificador_do_atributo(personagem, atributo)
    if modificador is None:
        return {
            "resultado": "bloqueado",
            "motivo": "atributo_de_conjuracao_sem_valor_na_ficha",
            "atributo": atributo,
        }
    bonus_proficiencia = int(personagem.get("bonus_proficiencia", 2 + (nivel - 1) // 4))

    alvo_nome = str(facts.get("target_name", facts.get("alvo", ""))).strip()
    if not alvo_nome:
        return {"resultado": "bloqueado", "motivo": "nome_do_alvo_ausente"}
    alvo = consultar_monstro(alvo_nome)
    if alvo is None:
        return {"resultado": "bloqueado", "motivo": "monstro_desconhecido_no_bestiario", "alvo": alvo_nome}

    return {
        "fatos": {
            **facts,
            "modifier": modificador + bonus_proficiencia,
            "character_id": personagem.get("id"),
            "proficiency_applied": bonus_proficiencia,
            "modifier_source": "ficha_autoritativa",
            "magia": nome_canonico,
            "spell_attack": True,
            "spell_attack_ability": atributo,
            "magia_dano": mecanica.get("dados_dano"),
            "magia_tipo_dano": mecanica.get("tipo_dano"),
            "magia_alcance_m": mecanica.get("alcance_m"),
            "escala_truque": mecanica.get("escala_truque", 1),
            "target_ac": int(alvo["ca"]),
            "target_name": alvo["nome"],
        }
    }


def preparar_dano_de_magia(
    engine: RuleEngine,
    facts: dict[str, Any],
    personagem: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Deriva o dano de uma magia do catálogo, já escalonado por espaço.

    Serve para magias resolvidas por salvaguarda (Bola de Fogo, Mãos
    Flamejantes, Onda Trovejante): o modelo informa a magia e, opcionalmente,
    o espaço usado; os dados de dano e a CD saem do catálogo e da ficha.
    """
    nome = str(facts.get("magia", facts.get("spell", ""))).strip()
    magia = obter_magia(nome)
    if not magia:
        return {"resultado": "bloqueado", "motivo": "magia_desconhecida", "magia": nome}
    nome_canonico = str(magia["nome"])
    if magia.get("circulo") is None:
        return {"resultado": "bloqueado", "motivo": "magia_sem_circulo_confirmado_no_catalogo"}
    circulo = int(magia["circulo"])
    if personagem is None:
        return {"resultado": "bloqueado", "motivo": "personagem_ausente_ou_nao_identificado"}
    if personagem is not None:
        conjuracao = personagem.get("conjuracao") or {}
        registradas = (
            conjuracao.get("truques")
            if circulo == 0
            else (conjuracao.get("magias_preparadas") or conjuracao.get("magias"))
        )
        registradas = {normalizar_nome_magia(x) for x in (registradas or [])}
        if normalizar_nome_magia(nome_canonico) not in registradas:
            return {
                "resultado": "bloqueado",
                "motivo": "magia_nao_registrada_na_ficha",
                "magia": nome_canonico,
            }

    nivel = max(1, int((personagem or {}).get("nivel", 1) or 1))
    espaco = facts.get("espaco", facts.get("slot_level"))
    try:
        aumento_informado = facts.get("aumento", facts.get("upcast"))
        usado = int(espaco) if espaco is not None else circulo + int(aumento_informado or 0)
        if not circulo <= usado <= 9 or (circulo == 0 and usado != 0):
            raise ValueError("espaço incompatível")
        aumento = usado - circulo
        if aumento_informado is not None and int(aumento_informado) != aumento:
            raise ValueError("espaço e aumento divergentes")
        if (
            circulo > 0
            and int(((personagem.get("conjuracao") or {}).get("espacos_totais") or {}).get(str(usado), 0)) < 1
        ):
            return {"resultado": "bloqueado", "motivo": "circulo_indisponivel_na_ficha"}
    except (TypeError, ValueError):
        return {"resultado": "bloqueado", "motivo": "espaco_de_magia_invalido"}
    # Esta ferramenta calcula a rolagem; não aplica PV nem consome outro espaço.
    # A conjuração continua sendo a operação responsável por consumir o recurso.
    mecanica = mecanica_de_magia(nome_canonico, nivel_personagem=nivel, aumento=aumento)
    if not mecanica:
        return {
            "resultado": "bloqueado",
            "motivo": "magia_sem_mecanica_estruturada_no_catalogo",
            "magia": nome_canonico,
            "dica": "O catálogo ainda não tem dano para esta magia; não narre dano oficial.",
        }
    expressao = mecanica.get("dados_dano") or mecanica.get("dados_dano_base")
    if not expressao:
        return {
            "resultado": "bloqueado",
            "motivo": "magia_sem_dano_no_catalogo",
            "magia": nome_canonico,
            "tipo_de_mecanica": mecanica.get("tipo"),
        }

    fatos = {
        **facts,
        "magia": nome_canonico,
        "damage_expression": str(expressao),
        "aumento": max(0, int(aumento)),
        "magia_tipo_dano": mecanica.get("tipo_dano"),
        "magia_salvaguarda": mecanica.get("salvaguarda"),
        "magia_sucesso_metade": bool(mecanica.get("sucesso_metade", False)),
        "magia_area": mecanica.get("area"),
    }
    if personagem is not None:
        atributo = atributo_de_conjuracao(engine, personagem)
        modificador = modificador_do_atributo(personagem, atributo) if atributo else None
        if atributo and modificador is not None:
            proficiencia = int(personagem.get("bonus_proficiencia", 2 + (nivel - 1) // 4))
            # CD de magia = 8 + proficiência + modificador do atributo de conjuração.
            fatos["cd_magia"] = 8 + proficiencia + modificador
            fatos["magia_atributo"] = atributo
        fatos["character_id"] = personagem.get("id")
    return {"fatos": fatos}


def resolver_ataque_de_sopro(
    engine: RuleEngine,
    facts: dict[str, Any],
    personagem: Mapping[str, Any],
    personagens: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Resolve o Ataque de Sopro do Draconato pela regra do traço.

    O sopro não é uma arma do catálogo: ele pede uma salvaguarda de Destreza
    contra a CD do traço (8 + Constituição + proficiência), com dano por
    nível de personagem e metade no sucesso. O motor rola a salvaguarda do
    alvo e o dano, e aplica as defesas do bloco do monstro.
    """
    especie = str(personagem.get("especie", "")).strip().lower()
    chave = str(personagem.get("heranca_draconica") or "").strip().lower().replace("-", "_")
    if not chave or chave not in HERANCA_DRACONICA:
        return {
            "resultado": "bloqueado",
            "motivo": "ataque_de_sopro_exige_draconato_com_heranca_draconica_na_ficha",
            "especie": especie,
            "dica": "O Ataque de Sopro vem da Herança Dracônica; registre a herança na ficha.",
        }
    modificador_constituicao = modificador_do_atributo(personagem, "constituicao")
    if modificador_constituicao is None:
        return {"resultado": "bloqueado", "motivo": "constituicao_ausente_na_ficha"}

    nivel = max(1, int(personagem.get("nivel", 1) or 1))
    bonus_proficiencia = int(personagem.get("bonus_proficiencia", 2 + (nivel - 1) // 4))
    bloco = bloco_heranca_draconica(chave, nivel, modificador_constituicao, bonus_proficiencia)
    sopro = bloco["sopro"]

    alvo_nome = str(facts.get("target_name", facts.get("alvo", ""))).strip()
    if not alvo_nome:
        return {"resultado": "bloqueado", "motivo": "nome_do_alvo_ausente"}
    alvo = consultar_monstro(alvo_nome)
    if alvo is None:
        return {"resultado": "bloqueado", "motivo": "monstro_desconhecido_no_bestiario", "alvo": alvo_nome}

    # Salvaguarda do alvo: usa a proficiência do bloco quando ela existe,
    # senão o modificador de Destreza puro.
    atributo_save = "destreza"
    salvaguardas_alvo = alvo.get("salvaguardas") or {}
    if atributo_save in salvaguardas_alvo:
        modificador_alvo = int(salvaguardas_alvo[atributo_save])
    else:
        modificador_alvo = int((alvo.get("modificadores") or {}).get(atributo_save, 0))

    semente = str(facts.get("seed") or "")
    salvaguarda = engine.evaluate(
        {
            "type": "saving_throw",
            "ability": atributo_save,
            "modifier": modificador_alvo,
            "dc": int(sopro["cd"]),
            "seed": f"{semente}:sopro" if semente else None,
        }
    ).outcome
    dano_rolado = engine.evaluate(
        {
            "type": "damage",
            "damage_expression": str(sopro["dado"]),
            "damage_modifier": 0,
            "seed": f"{semente}:sopro-dano" if semente else None,
        }
    ).outcome
    dano = int(dano_rolado.get("total", 0))
    sucesso = salvaguarda.get("result") == "success"
    if sucesso:
        dano = dano // 2
    defesas = aplicar_defesas_monstro(dano, str(sopro["tipo_dano"]), alvo)

    resultado = {
        "resultado": "resolvido",
        "tipo_resolucao": "salvaguarda_de_area",
        "ataque": "Ataque de Sopro",
        "character_id": personagem.get("id"),
        "target_name": alvo["nome"],
        "heranca_draconica": bloco["nome"],
        "tipo_dano": sopro["tipo_dano"],
        "formas": list(sopro["formas"]),
        "salvaguarda": {
            "atributo": atributo_save,
            "cd": int(sopro["cd"]),
            "rolagem": salvaguarda.get("roll"),
            "total": salvaguarda.get("total"),
            "sucesso": sucesso,
            "resultado": salvaguarda.get("result"),
        },
        "dano": int(defesas["dano"]),
        "dano_bruto": int(defesas["dano_bruto"]),
        "defesas_dano": defesas,
        "dados_dano": list(dano_rolado.get("damage_dice") or []),
        "dano_expressao": dano_rolado.get("damage_expression"),
        "usos_por_descanso_longo": int(sopro["usos"]),
        "seed": semente or None,
        "fonte": "Livro do Jogador 2024 — Ataque de Sopro do Draconato",
    }
    # A rolagem anunciada mostra o dano aplicado: defesas do bloco e metade no
    # sucesso da salvaguarda, com o motivo no cartão.
    dano_anunciado = {
        **dano_rolado,
        "total": int(defesas["dano"]),
        "defesas_dano": defesas,
        "sucesso_na_salvaguarda": bool(sucesso),
        "target_name": alvo["nome"],
    }
    rolagens = [
        normalizar_rolagem(salvaguarda, {**facts, "ability": atributo_save, "target_name": alvo["nome"]}, personagens),
        normalizar_rolagem(dano_anunciado, {**facts, "magia": None, "weapon": ATAQUE_DE_SOPRO_FERRAMENTA}, personagens),
    ]
    return {"resultado": resultado, "rolagens": [r for r in rolagens if r]}
