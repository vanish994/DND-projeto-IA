"""Registro de rolagens: traduz a resolução do motor para a interface.

Esta camada **não sorteia nada**. Ela apenas copia ``roll``, ``modifier``,
``total``, CD/CA e o veredito que o Rule Engine já produziu, para que o
navegador possa animar o dado sem recalcular regra alguma.

Pertence ao Orquestrador de Ações, e não ao MJ: é uma preocupação de fluxo e
apresentação do resultado mecânico, não de narrativa.
"""

from __future__ import annotations

from typing import Any, Mapping

ROTULOS_ATRIBUTO = {
    "forca": "Força",
    "destreza": "Destreza",
    "constituicao": "Constituição",
    "inteligencia": "Inteligência",
    "sabedoria": "Sabedoria",
    "carisma": "Carisma",
}

ROTULOS_PERICIA = {
    "acrobacia": "Acrobacia",
    "adestrar_animais": "Adestrar Animais",
    "arcanismo": "Arcanismo",
    "atletismo": "Atletismo",
    "atuacao": "Atuação",
    "enganacao": "Enganação",
    "furtividade": "Furtividade",
    "historia": "História",
    "intuicao": "Intuição",
    "intimidacao": "Intimidação",
    "investigacao": "Investigação",
    "medicina": "Medicina",
    "natureza": "Natureza",
    "percepcao": "Percepção",
    "persuasao": "Persuasão",
    "prestidigitacao": "Prestidigitação",
    "religiao": "Religião",
    "sobrevivencia": "Sobrevivência",
}

# Tipos de rolagem que a interface sabe animar. Qualquer outro tipo cai em "rolagem".
TIPOS_ROLAGEM = {"ataque", "iniciativa", "teste", "salvaguarda", "dano", "rolagem"}

# Mesmos textos que dado.js mostra no cartão quando o motor ajusta o dano.
MOTIVOS_APLICACAO_DANO = {
    "imunidade": "imune ao tipo",
    "resistencia": "resistência: metade",
    "vulnerabilidade": "vulnerabilidade: dobro",
    "resistencia_e_vulnerabilidade_canceladas": "resistência e vulnerabilidade se cancelam",
}


def _primeiro_valor(dados: Any, *chaves: str) -> Any:
    if not isinstance(dados, Mapping):
        return None
    for chave in chaves:
        valor = dados.get(chave)
        if valor is not None and valor != "":
            return valor
    return None


def _inteiro(valor: Any) -> int | None:
    if valor is None or isinstance(valor, bool):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _lista_de_inteiros(valor: Any) -> list[int]:
    if valor is None:
        return []
    if isinstance(valor, (str, bytes)) or not isinstance(valor, (list, tuple, set)):
        valor = [valor]
    numeros: list[int] = []
    for item in valor:
        numero = _inteiro(item)
        if numero is not None:
            numeros.append(numero)
    return numeros


def _nome_do_personagem(personagens: list[dict[str, Any]] | None, identificador: Any) -> str | None:
    if identificador is None:
        return None
    for personagem in personagens or []:
        if str(personagem.get("id")) == str(identificador):
            return personagem.get("nome")
    return None


def _lados_da_expressao(expressao: Any) -> int | None:
    """Extrai o tamanho do dado de uma expressão como ``1d8`` ou ``2d6 + 3``."""
    if not isinstance(expressao, str):
        return None
    import re

    encontrado = re.search(r"\d*\s*d\s*(\d+)", expressao.lower())
    if not encontrado:
        return None
    lados = _inteiro(encontrado.group(1))
    return lados if lados and lados > 1 else None


def _expressao_de_dano(dados: list[int], modificador: int, lados: int) -> str:
    quantidade = len(dados)
    expressao = f"{quantidade}d{lados}" if quantidade else f"1d{lados}"
    if modificador:
        sinal = "+" if modificador > 0 else "−"
        expressao += f" {sinal} {abs(modificador)}"
    return expressao


def _motivo_da_rolagem_de_dano(resultado: Mapping[str, Any]) -> str | None:
    """Explica por que o total aplicado difere da soma dos dados.

    Sem ajuste de regra (defesa, metade por salvaguarda, bloqueio), o cartão
    mostra apenas a conta — nada de "· dano" repetindo o tipo da rolagem.
    """
    notas = []
    aplicacao = str((resultado.get("defesas_dano") or {}).get("aplicacao") or "")
    if aplicacao in MOTIVOS_APLICACAO_DANO:
        notas.append(MOTIVOS_APLICACAO_DANO[aplicacao])
    if resultado.get("sucesso_na_salvaguarda"):
        notas.append("metade por salvaguarda")
    if notas:
        return " · ".join(notas)
    motivo = str(resultado.get("reason") or "").strip()
    return motivo or None


def _rotulo_da_rolagem(tipo: str, fatos: Mapping[str, Any], alvo: str | None) -> str:
    pericia = fatos.get("skill", fatos.get("pericia"))
    pericia = str(pericia).strip().lower().replace(" ", "_") if pericia else None
    atributo = fatos.get("ability", fatos.get("atributo"))
    atributo = str(atributo).strip().lower() if atributo else None
    nome_pericia = ROTULOS_PERICIA.get(pericia or "")
    nome_atributo = ROTULOS_ATRIBUTO.get(atributo or "")
    magia = fatos.get("magia") or fatos.get("spell")
    if tipo == "ataque":
        if magia:
            rotulo = f"Ataque de magia: {magia}"
        else:
            arma = fatos.get("weapon") or fatos.get("arma")
            rotulo = f"Ataque com {arma}" if arma else "Jogada de ataque"
        return f"{rotulo} contra {alvo}" if alvo else rotulo
    if tipo == "iniciativa":
        return "Iniciativa"
    if tipo == "salvaguarda":
        return f"Salvaguarda de {nome_atributo}" if nome_atributo else "Salvaguarda"
    if tipo == "dano":
        if magia:
            return f"Dano de {magia}"
        fonte = fatos.get("weapon") or fatos.get("arma")
        return f"Dano de {fonte}" if fonte else "Rolagem de dano"
    if nome_pericia:
        return f"Teste de {nome_pericia} ({nome_atributo})" if nome_atributo else f"Teste de {nome_pericia}"
    if nome_atributo:
        return f"Teste de {nome_atributo}"
    return "Rolagem de d20"


def normalizar_rolagem(
    resultado: Mapping[str, Any] | None,
    fatos: Mapping[str, Any] | None = None,
    personagens: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Converte a resolução do motor em um registro de rolagem para a interface.

    O motor continua sendo a única fonte do d20: este normalizador apenas copia
    ``roll``/``dado``, ``modifier``, ``total``, CD/CA e o veredito para que o
    navegador possa animar o dado sem recalcular nenhuma regra. Devolve ``None``
    quando a resolução não contém rolagem (por exemplo, consultas de bestiário).
    """
    resultado = dict(resultado or {})
    fatos = dict(fatos or {})
    dados = {**fatos, **resultado}
    tipo_bruto = str(dados.get("type") or "").strip().lower()

    valor = _inteiro(_primeiro_valor(resultado, "roll", "dado", "rolagem", "dado_usado"))
    if valor is None:
        valor = _inteiro(_primeiro_valor(fatos, "roll", "dado"))
    rolagens = _lista_de_inteiros(
        _primeiro_valor(resultado, "rolls", "dados_rolados", "dados")
        or _primeiro_valor(fatos, "rolls", "dados_rolados", "dados")
    )
    if not rolagens and valor is not None:
        rolagens = [valor]

    lados = 20
    dado_nome = _primeiro_valor(resultado, "die") or _primeiro_valor(fatos, "die") or "d20"
    if isinstance(dado_nome, str) and "d" in dado_nome.lower():
        lados = _inteiro(dado_nome.lower().split("d")[-1]) or 20

    if tipo_bruto == "attack":
        tipo = "ataque"
    elif tipo_bruto == "initiative":
        tipo = "iniciativa"
    elif tipo_bruto in {"saving_throw", "saving_throw_check"} or dados.get("tipo_teste") == "salvaguarda":
        tipo = "salvaguarda"
    elif tipo_bruto == "damage":
        tipo = "dano"
    elif tipo_bruto == "ability_check" or (not tipo_bruto and valor is not None):
        tipo = "teste"
    else:
        tipo = "rolagem"

    if valor is None:
        # Sem d20: ainda pode haver dados de dano rolagos pelo motor.
        dados_dano = _lista_de_inteiros(
            _primeiro_valor(resultado, "damage_dice", "dados_dano") or fatos.get("damage_dice")
        )
        if not dados_dano:
            return None
        modificador_dano = (
            _inteiro(_primeiro_valor(resultado, "damage_modifier", "modifier"))
            or _inteiro(_primeiro_valor(fatos, "damage_modifier"))
            or 0
        )
        total_dano = _inteiro(_primeiro_valor(resultado, "total"))
        if total_dano is None:
            total_dano = sum(dados_dano) + modificador_dano
        lados_dano = (
            _lados_da_expressao(_primeiro_valor(resultado, "damage_expression", "expressao"))
            or _lados_da_expressao(_primeiro_valor(resultado, "damage_dice_expression"))
            or _lados_da_expressao(_primeiro_valor(fatos, "damage_expression", "weapon_damage"))
            or 6
        )
        return {
            "tipo": "dano",
            "dado": f"d{lados_dano}",
            "lados": lados_dano,
            "valor": None,
            "rolagens": dados_dano,
            "modificador": modificador_dano,
            "total": total_dano,
            "expressao": _expressao_de_dano(dados_dano, modificador_dano, lados_dano),
            "dificuldade": None,
            "dificuldade_tipo": None,
            "resultado": "dano",
            "critico": bool(resultado.get("critical")),
            "vantagem": False,
            "desvantagem": False,
            "motivo": _motivo_da_rolagem_de_dano(resultado),
            "rotulo": _rotulo_da_rolagem("dano", dados, None),
            "personagem": _nome_do_personagem(personagens, dados.get("character_id")),
            "alvo": str(dados.get("target_name") or "").strip() or None,
            "seed": str(dados["seed"]) if dados.get("seed") is not None else None,
            "origem": "rule_engine",
        }

    modificador = _inteiro(_primeiro_valor(dados, "modifier", "modificador_total", "modificador")) or 0
    total = _inteiro(_primeiro_valor(dados, "total")) or valor + modificador
    dificuldade = _inteiro(_primeiro_valor(dados, "target_ac", "dc", "cd", "ca"))
    dificuldade_tipo = None
    if dificuldade is not None:
        dificuldade_tipo = "ca" if dados.get("target_ac") is not None else "cd"

    veredito = str(_primeiro_valor(dados, "result", "resultado") or "").strip().lower()
    if tipo == "ataque":
        resultado_jogada = {"hit": "acerto", "miss": "erro"}.get(veredito, "rolado")
    elif tipo in {"teste", "salvaguarda"}:
        resultado_jogada = {
            "success": "sucesso",
            "sucesso": "sucesso",
            "failure": "falha",
            "falha": "falha",
            "requires_dc": "pendente",
            "blocked": "bloqueado",
            "bloqueado": "bloqueado",
        }.get(veredito, "rolado")
    else:
        resultado_jogada = "rolado"

    sucesso = dados.get("sucesso")
    if sucesso is None:
        if resultado_jogada == "acerto":
            sucesso = True
        elif resultado_jogada == "erro":
            sucesso = False
        elif resultado_jogada == "sucesso":
            sucesso = True
        elif resultado_jogada == "falha":
            sucesso = False
    vantagem = bool(_primeiro_valor(dados, "advantage", "vantagem"))
    desvantagem = bool(_primeiro_valor(dados, "disadvantage", "desvantagem"))
    critico = bool(dados.get("critical")) or (
        lados == 20 and valor == 20 and tipo in {"ataque", "teste", "salvaguarda"}
    )
    alvo = str(dados.get("target_name") or dados.get("alvo") or "").strip() or None

    return {
        "tipo": tipo if tipo in TIPOS_ROLAGEM else "rolagem",
        "dado": f"d{lados}",
        "lados": lados,
        "valor": valor,
        "rolagens": rolagens,
        "modificador": modificador,
        "total": total,
        "expressao": None,
        "dificuldade": dificuldade,
        "dificuldade_tipo": dificuldade_tipo,
        "resultado": resultado_jogada,
        "sucesso": sucesso,
        "critico": critico,
        "natural_1": lados == 20 and valor == 1,
        "vantagem": vantagem and not desvantagem,
        "desvantagem": desvantagem and not vantagem,
        "motivo": str(_primeiro_valor(dados, "reason", "motivo") or "") or None,
        "rotulo": _rotulo_da_rolagem(tipo, dados, alvo),
        "personagem": _nome_do_personagem(personagens, dados.get("character_id")),
        "alvo": alvo,
        "seed": str(dados["seed"]) if dados.get("seed") is not None else None,
        "dano": (
            {
                "expressao": dados.get("weapon_damage") or dados.get("expressao"),
                "modificador": _inteiro(dados.get("damage_modifier")),
                "tipo": dados.get("damage_type"),
            }
            if dados.get("weapon_damage") or dados.get("damage_modifier") is not None
            else None
        ),
        "origem": "rule_engine",
    }
