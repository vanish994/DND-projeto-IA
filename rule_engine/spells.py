"""Sistema de magias do Livro do Jogador 2024.

O catálogo reaproveita as centenas de entradas extraídas do livro e adiciona
metadados executáveis, componentes, concentração, efeitos e escalonamento.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any
from .catalog import CATALOGO_MAGIAS

ESCOLAS = {"abjuração", "adivinhação", "conjuração", "encantamento", "evocação", "ilusão", "necromancia", "transmutação"}

def _nome_limpo(nome: str) -> str:
    nome = re.sub(r"\s+", " ", nome).strip(" -–")
    return nome

MAGIAS: dict[str, dict[str, Any]] = {}
for bruto, meta in CATALOGO_MAGIAS.items():
    partes = re.split(r"\s{2,}", bruto.strip())
    nome = _nome_limpo(partes[0])
    if nome and nome.lower() not in {"a opção que você escolheu para golpes abençoados", "após usar", "como uma ação usar"}:
        MAGIAS.setdefault(nome.lower(), {"nome": nome, "circulo": None, "escola": meta["escola"].lower(), "componentes": "V, S" + (", M" if meta.get("material") else ""), "concentracao": bool(meta.get("concentracao")), "ritual": bool(meta.get("ritual")), "duracao": "concentração" if meta.get("concentracao") else "instantânea"})

# Entradas de referência com círculo, componentes e efeitos precisos do PHB 2024.
_DETALHADAS = {
    # PHB 2024, pp. 249, 324 e 340 (PDF local: páginas 255, 330 e 346).
    "bolha ácida": (0, "evocação", "V, S", False, "Escolha uma ou duas criaturas a até 18 m, cujos espaços estejam a até 1,5 m entre si; salvaguarda de Destreza evita 1d6 ácido", {"dano": "escala nos níveis 5, 11 e 17"}),
    "rajada de veneno": (0, "necromancia", "V, S", False, "Ataque mágico à distância; 1d12 dano venenoso; alcance 9 m", {"dano": "escala nos níveis 5, 11 e 17"}),
    "trovão": (0, "evocação", "S", False, "Emanação de 1,5 m; Constituição evita 1d6 trovejante; som audível a 30 m", {"dano": "escala nos níveis 5, 11 e 17"}),
    "armadura de agathys": (1, "abjuração", "V, S, M (um caco de vidro azul)", False, "5 PV temporários; 5 dano gélido ao atacante", {"pv_temporarios": "+5 por círculo", "dano_retorno": "+5 por círculo"}),
    "mísseis mágicos": (1, "evocação", "V, S", False, "3 dardos de 1d4+1 dano energético", {"dardos": "+1 por círculo"}),
    "raio de fogo": (0, "evocação", "V, S", False, "Ataque mágico à distância; 1d10 dano ígneo; alcance 36 m", {"dano": "escala nos níveis 5, 11 e 17"}),
    "escudo": (1, "abjuração", "V, S", False, "+5 CA até o início do próximo turno", {}),
    "curar ferimentos": (1, "necromancia", "V, S", False, "cura 2d8", {"cura": "+2d8 por círculo"}),
    "palavra curativa": (1, "abjuração", "V", False, "cura 1d4 + modificador de conjuração; alcance 18m; ação bônus", {"cura": "+1d4 por círculo"}),
    "onda trovejante": (1, "evocação", "V, S", False, "2d8 dano trovejante; cubo de 4,5m; salvaguarda de Constituição reduz à metade; falha empurra 3m", {"dano": "+1d8 por círculo"}),
    "mãos flamejantes": (1, "evocação", "V, S", False, "3d6 dano ígneo em cone de 4,5m; salvaguarda de Destreza reduz à metade", {"dano": "+1d6 por círculo"}),
    "armadura arcana": (1, "abjuração", "V, S, M (um pedaço de couro curtido)", False, "CA base 13 + modificador de Destreza por 8 horas; alvo voluntário sem armadura", {}),
    "benção": (1, "encantamento", "V, S, M (uma gota de água benta)", True, "até três criaturas adicionam 1d4", {"alvos": "+1 por círculo"}),
    "escudo da fé": (1, "abjuração", "V, S, M (um pergaminho com texto sagrado)", True, "+2 CA para uma criatura; duração de até 10 minutos; ação bônus", {}),
    "raio místico": (0, "evocação", "V, S", False, "1d10 dano energético", {"raios": "+1 nos níveis 5, 11 e 17"}),
    "bola de fogo": (3, "evocação", "V, S, M (uma bola de guano de morcego e enxofre)", False, "8d6 dano ígneo em esfera de 6m", {"dano": "+1d6 por círculo"}),
    "relâmpago": (3, "evocação", "V, S, M (um pouco de pelo e uma haste de âmbar, cristal ou vidro)", False, "8d6 dano elétrico em linha", {"dano": "+1d6 por círculo"}),
    "contramagia": (3, "abjuração", "S", False, "interrompe magia", {}),
    "voo": (3, "transmutação", "V, S, M (uma pena de qualquer ave)", True, "deslocamento de voo 18m", {"alvos": "+1 por círculo"}),
    "invisibilidade": (2, "ilusão", "V, S, M (uma pestana envolta em goma)", True, "condição Invisível", {"alvos": "+1 por círculo"}),
    "passo nebuloso": (2, "conjuração", "V", False, "teleporta 9m", {}),
    "reviver os mortos": (5, "necromancia", "V, S, M (um diamante de 500 PO)", False, "retorna criatura morta à vida", {}),
    "dissipar magia": (3, "abjuração", "V, S", False, "encerra efeitos mágicos", {}),
    "banimento": (4, "abjuração", "V, S, M (um item desagradável ao alvo)", True, "salvaguarda ou banido", {"alvos": "+1 por círculo"}),
    "cura completa": (6, "necromancia", "V, S", False, "cura 70 PV", {"cura": "+10 por círculo"}),
}
for nome, (circulo, escola, componentes, conc, efeito, upcast) in _DETALHADAS.items():
    MAGIAS[nome] = {"nome": nome.title(), "circulo": circulo, "escola": escola, "componentes": componentes, "concentracao": conc, "ritual": False, "duracao": "concentração" if conc else "instantânea", "efeito": efeito, "upcasting": upcast}

# O catálogo extraído contém entradas incompletas sem círculo. Para as magias
# da lista de Artífice, o círculo é conhecido e validado separadamente do efeito.
from .spellcasting import ARTIFICER_SPELL_LEVELS, normalizar_nome_magia as _normalizar_nome_spellcasting

for _nome_artifice, _circulo_artifice in ARTIFICER_SPELL_LEVELS.items():
    _chave_artifice = _normalizar_nome_spellcasting(_nome_artifice)
    _existente_artifice = next(
        (m for m in MAGIAS.values() if _normalizar_nome_spellcasting(m["nome"]) == _chave_artifice),
        None,
    )
    if _existente_artifice is not None:
        _existente_artifice["circulo"] = _circulo_artifice
    else:
        MAGIAS[_chave_artifice] = {
            "nome": _nome_artifice, "circulo": _circulo_artifice,
            "escola": "transmutação", "componentes": "V, S",
            "concentracao": False, "ritual": False, "duracao": "instantânea",
        }


# Mecânicas estruturadas para integrar o resultado da magia ao combate.
# Fórmulas são devolvidas como dados; o motor de combate continua responsável
# por rolagens, salvaguardas, aplicação de dano e atualização de estado.
MECANICAS_MAGIA: dict[str, dict[str, Any]] = {
    "bolha ácida": {
        "tipo": "dano_multialvo", "dados_dano_base": "1d6", "tipo_dano": "acido",
        "salvaguarda": "destreza", "sucesso_metade": False, "acao": "acao",
        "alcance_m": 18, "alcance_pes": 60, "alvos_maximos": 2,
        "distancia_entre_alvos_m": 1.5, "escala_niveis": [5, 11, 17],
    },
    "rajada de veneno": {
        "tipo": "ataque_magico", "dados_dano_base": "1d12", "tipo_dano": "venenoso",
        "alcance_m": 9, "alcance_pes": 30, "escala_niveis": [5, 11, 17], "acao": "acao",
    },
    "trovão": {
        "tipo": "dano_em_area", "dados_dano_base": "1d6", "tipo_dano": "trovejante",
        "salvaguarda": "constituicao", "sucesso_metade": False, "acao": "acao",
        "area": {"forma": "emanacao", "raio_m": 1.5, "origem": "conjurador", "exclui_conjurador": True},
        "som_audivel_m": 30, "escala_niveis": [5, 11, 17],
    },
    "raio de fogo": {
        "tipo": "ataque_magico", "dados_dano_base": "1d10", "tipo_dano": "igneo",
        "alcance_m": 36, "escala_niveis": [5, 11, 17],
    },
    "armadura de agathys": {
        "tipo": "pv_temporarios_e_dano_retorno", "pv_temporarios_por_nivel": 5,
        "dano_retorno_por_nivel": 5, "tipo_dano": "gelido",
        "gatilho": "acertado_por_ataque_corpo_a_corpo_enquanto_tem_pv_temporarios",
    },
    "mísseis mágicos": {
        "tipo": "dano_multialvo", "dardos_base": 3, "dardos_por_nivel": 1,
        "dano_por_dardo": "1d4+1", "tipo_dano": "energetico", "jogada_ataque": False,
    },
    "escudo": {
        "tipo": "defesa", "bonus_ca": 5, "duracao": "ate_inicio_do_proximo_turno",
        "gatilhos": ["atingido_por_ataque", "alvo_de_misseis_magicos"],
        "anula_dano_misseis_magicos": True, "acao": "reacao",
    },
    "curar ferimentos": {
        "tipo": "cura", "dados_cura_base": "2d8", "dados_cura_por_nivel": "2d8",
        "soma_modificador_conjuracao": True, "alcance": "toque",
    },
    "palavra curativa": {
        "tipo": "cura", "dados_cura_base": "1d4", "dados_cura_por_nivel": "1d4",
        "soma_modificador_conjuracao": True, "alcance_m": 18, "acao": "bonus",
    },
    "onda trovejante": {
        "tipo": "dano_em_area", "dados_dano_base": "2d8", "dados_dano_por_nivel": "1d8",
        "tipo_dano": "trovejante", "salvaguarda": "constituicao", "sucesso_metade": True,
        "area": {"forma": "cubo", "lado_m": 4.5, "origem": "conjurador"},
        "empurra_m": 3, "empurra_em_falha": True,
    },
    "mãos flamejantes": {
        "tipo": "dano_em_area", "dados_dano_base": "3d6", "dados_dano_por_nivel": "1d6",
        "tipo_dano": "igneo", "salvaguarda": "destreza", "sucesso_metade": True,
        "area": {"forma": "cone", "comprimento_m": 4.5, "origem": "conjurador"},
    },
    "armadura arcana": {
        "tipo": "defesa", "ca_base": 13, "adiciona_modificador_destreza": True,
        "duracao": "ate_8_horas", "exige_alvo_sem_armadura": True,
    },
    "benção": {
        "tipo": "beneficio", "alvos_base": 3, "alvos_por_nivel": 1,
        "bonus": "1d4", "aplica_a": ["jogadas_de_ataque", "salvaguardas"],
        "concentracao": True,
    },
    "escudo da fé": {
        "tipo": "beneficio_defensivo", "bonus_ca": 2, "alcance_m": 18,
        "duracao": "ate_10_minutos", "concentracao": True, "acao": "bonus",
        "alvos_base": 1,
    },
    "bola de fogo": {
        "tipo": "dano_em_area", "dados_dano_base": "8d6", "dados_dano_por_nivel": "1d6",
        "tipo_dano": "igneo", "salvaguarda": "destreza", "sucesso_metade": True,
        "area": {"forma": "esfera", "raio_m": 6}, "alcance_m": 45,
    },
    "relâmpago": {
        "tipo": "dano_em_area", "dados_dano_base": "8d6", "dados_dano_por_nivel": "1d6",
        "tipo_dano": "eletrico", "salvaguarda": "destreza", "sucesso_metade": True,
        "area": {"forma": "linha", "comprimento_m": 30, "largura_m": 1.5}, "alcance_m": 30,
    },
    "voo": {
        "tipo": "movimento", "deslocamento_voo_m": 18, "duracao": "ate_10_minutos",
        "concentracao": True, "alvos_base": 1, "alvos_por_nivel": 1,
    },
    "invisibilidade": {
        "tipo": "condicao", "condicao": "invisivel", "duracao": "ate_1_hora",
        "concentracao": True, "alvos_base": 1, "alvos_por_nivel": 1,
    },
    "passo nebuloso": {
        "tipo": "teleporte", "distancia_m": 9, "acao": "bonus",
    },
    "cura completa": {
        "tipo": "cura", "pv_base": 70, "pv_por_nivel": 10,
        "remove_condicoes": ["cego", "surdo", "envenenado"],
    },
    "banimento": {
        "tipo": "controle", "salvaguarda": "carisma", "falha": "banido",
        "concentracao": True, "duracao": "ate_1_minuto",
        "alvos_base": 1, "alvos_por_nivel": 1,
    },
}


def _aplicar_escalonamento_mecanico(nome: str, magia: dict[str, Any], aumento: int) -> dict[str, Any] | None:
    chave_normalizada = _normalizar_nome_magia(nome)
    base = next((mecanica for chave, mecanica in MECANICAS_MAGIA.items() if _normalizar_nome_magia(chave) == chave_normalizada), None)
    if base is None:
        return None
    mecanica = dict(base)
    if "area" in base:
        mecanica["area"] = dict(base["area"])
    if "pv_temporarios_por_nivel" in base:
        mecanica["pv_temporarios"] = base["pv_temporarios_por_nivel"] * int(magia["circulo"] + aumento)
        mecanica["dano_retorno"] = base["dano_retorno_por_nivel"] * int(magia["circulo"] + aumento)
    if "dardos_base" in base:
        mecanica["dardos"] = base["dardos_base"] + base["dardos_por_nivel"] * aumento
    if "dados_dano_base" in base:
        dados_base = re.fullmatch(r"(\d+)d(\d+)", base["dados_dano_base"])
        dados_extra = re.fullmatch(r"(\d+)d(\d+)", base.get("dados_dano_por_nivel", "0d0"))
        if dados_base and dados_extra:
            quantidade = int(dados_base.group(1)) + int(dados_extra.group(1)) * aumento
            mecanica["dados_dano"] = f"{quantidade}d{dados_base.group(2)}"
    if "dados_cura_base" in base:
        dados_base = re.fullmatch(r"(\d+)d(\d+)", base["dados_cura_base"])
        dados_extra = re.fullmatch(r"(\d+)d(\d+)", base["dados_cura_por_nivel"])
        if dados_base and dados_extra:
            quantidade = int(dados_base.group(1)) + int(dados_extra.group(1)) * aumento
            mecanica["dados_cura"] = f"{quantidade}d{dados_base.group(2)}"
    if "alvos_base" in base:
        mecanica["alvos"] = base["alvos_base"] + base.get("alvos_por_nivel", 0) * aumento
    if "pv_base" in base:
        mecanica["pv_curados"] = base["pv_base"] + base["pv_por_nivel"] * aumento
    return mecanica


def escala_de_truque(nivel_personagem: int) -> int:
    """Quantos dados de dano um truque tem no nível do personagem.

    O Livro do Jogador 2024 aumenta o dano dos truques nos níveis 5, 11 e 17;
    o texto do catálogo registra os mesmos marcos ("escala nos níveis 5, 11 e
    17"). O nível é o do personagem, não o do espaço de magia: truque não gasta
    espaço.
    """
    if nivel_personagem >= 17:
        return 4
    if nivel_personagem >= 11:
        return 3
    if nivel_personagem >= 5:
        return 2
    return 1


def mecanica_de_magia(
    nome: object,
    *,
    nivel_personagem: int = 1,
    aumento: int = 0,
) -> dict[str, Any] | None:
    """Mecânica estruturada da magia, com o escalonamento já aplicado.

    Magias de círculo 1 ou superior escalam pelo espaço usado (``aumento``);
    truques escalam pelo nível do personagem (5, 11 e 17). Devolve ``None``
    quando a magia não está no catálogo ou ainda não tem mecânica estruturada —
    nesse caso o motor não deve inventar dados de dano.
    """
    magia = obter_magia(str(nome or ""))
    if not magia:
        return None
    mecanica = _aplicar_escalonamento_mecanico(magia["nome"], magia, aumento)
    if mecanica is None:
        return None
    if magia.get("circulo") == 0:
        multiplicador = escala_de_truque(nivel_personagem)
        base = str(mecanica.get("dados_dano") or mecanica.get("dados_dano_base") or "")
        casamento = re.fullmatch(r"(\d+)d(\d+)", base)
        if casamento:
            quantidade = int(casamento.group(1)) * multiplicador
            mecanica["dados_dano"] = f"{quantidade}d{casamento.group(2)}"
            mecanica["dados_dano_base"] = mecanica["dados_dano"]
            mecanica["escala_truque"] = multiplicador
    return mecanica


def listar_magias(escola: str | None = None, circulo: int | None = None) -> list[dict[str, Any]]:
    resultado = list(MAGIAS.values())
    if escola:
        resultado = [m for m in resultado if m["escola"] == escola.lower()]
    if circulo is not None:
        resultado = [m for m in resultado if m["circulo"] is not None and m["circulo"] == int(circulo)]
    return sorted(resultado, key=lambda m: (m["circulo"] is None, m["circulo"] if m["circulo"] is not None else 99, m["nome"]))


def _normalizar_nome_magia(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).replace("-", " ")


def obter_magia(nome: str) -> dict[str, Any] | None:
    direta = MAGIAS.get(str(nome).strip().lower())
    if direta is not None:
        return direta
    chave = _normalizar_nome_magia(nome)
    for magia in MAGIAS.values():
        if _normalizar_nome_magia(magia["nome"]) == chave:
            return magia
    return None


def _circulo_efetivo(base: int, usado: int) -> int:
    if not 0 <= usado <= 9:
        raise ValueError("O espaço de magia deve estar entre 0 e 9")
    if base == 0 and usado != 0:
        raise ValueError("Truques não usam espaços de magia")
    if base > 0 and usado == 0:
        raise ValueError("Magias de círculo 1 ou superior exigem espaço de magia")
    if usado < base:
        raise ValueError("O espaço usado não pode ser inferior ao círculo da magia")
    return usado - base


def resolver_magia(fatos: dict) -> dict[str, Any]:
    nome = str(fatos.get("magia", fatos.get("spell", ""))).lower()
    magia = obter_magia(nome)
    if not magia:
        return {"resultado": "bloqueado", "motivo": "magia_desconhecida", "magia": nome}
    if magia.get("circulo") is None:
        return {
            "resultado": "nao_implementado",
            "motivo": "magia_catalogada_sem_resolucao_especifica",
            "motivo_secundario": "circulo_da_magia_nao_catalogado",
            "magia": magia["nome"],
            "escola": magia["escola"],
        }
    if _normalizar_nome_magia(magia["nome"]) == _normalizar_nome_magia("armadura arcana") and fatos.get("alvo_veste_armadura") is True:
        return {"resultado": "bloqueado", "motivo": "alvo_ja_veste_armadura"}
    try:
        usado = int(fatos.get("espaco", fatos.get("spell_level", magia["circulo"])))
        aumento = _circulo_efetivo(magia["circulo"], usado)
    except (TypeError, ValueError) as erro:
        return {"resultado": "bloqueado", "motivo": "circulo_invalido", "detalhe": str(erro)}
    componentes = set(magia["componentes"].replace("(", ",").replace(")", ",").split(","))
    requeridos = {c.strip() for c in componentes if c.strip() in {"V", "S", "M"}}
    disponiveis = set(fatos.get("componentes_disponiveis", ["V", "S", "M"]))
    faltantes = requeridos - disponiveis
    if faltantes:
        return {"resultado": "bloqueado", "motivo": "componentes_ausentes", "faltantes": sorted(faltantes)}
    if magia["concentracao"] and fatos.get("concentrando") and fatos.get("nova_concentracao", True):
        encerra = fatos["concentrando"]
    else:
        encerra = None
    resultado = {
        "magia": magia["nome"], "circulo_base": magia["circulo"],
        "circulo_usado": usado, "upcasting": aumento, "escola": magia["escola"],
        "componentes": sorted(requeridos), "concentracao": magia["concentracao"],
        "duracao": magia["duracao"], "encerra_concentracao": encerra,
    }
    if "efeito" not in magia or _aplicar_escalonamento_mecanico(magia["nome"], magia, aumento) is None:
        # Metadados do catálogo não bastam para executar uma magia com fidelidade.
        # Não declarar a conjuração resolvida enquanto o efeito específico não existir.
        resultado.update({
            "resultado": "nao_implementado",
            "motivo": "magia_catalogada_sem_resolucao_especifica",
        })
        return resultado
    resultado.update({"resultado": "conjurada", "efeito": magia["efeito"]})
    mecanica = _aplicar_escalonamento_mecanico(magia["nome"], magia, aumento)
    if mecanica is not None:
        resultado["mecanica"] = mecanica
    if aumento and magia.get("upcasting"):
        resultado["escalonamento"] = magia["upcasting"]
    return resultado


def suporte_magia(nome: str) -> dict[str, Any]:
    """Capacidades reais, não uma promessa de aplicação de todo efeito catalogado."""
    mecanica = mecanica_de_magia(nome)
    chave = _normalizar_nome_magia(nome)
    tatico = chave in {"raio de fogo", "rajada de veneno", "trovao", "bolha acida", "curar ferimentos", "onda trovejante"}
    parcial = chave == "onda trovejante"  # Empurrão ainda não move os tokens.
    if not mecanica:
        rotulo = "Sem mecânica implementada"
    elif tatico:
        rotulo = "Mapa (Artífice): parcial, sem empurrão" if parcial else "Mapa (Artífice): resolução disponível"
    else:
        rotulo = "Regra estruturada; sem execução no mapa"
    return {"mecanica_estruturada": mecanica is not None, "mapa_tatico": tatico,
            "parcial": parcial, "rotulo": rotulo,
            "restricao_mapa": "Apenas Artífice; exige registro na ficha"}
