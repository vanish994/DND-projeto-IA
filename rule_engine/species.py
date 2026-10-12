"""Escolhas de espécie do Livro do Jogador 2024.

Fonte: Livro do Jogador 2024 (edição brasileira), capítulo 4 — traços de
Draconato (p. 188-194). Nenhuma linhagem, tipo de dano ou forma de sopro é
inventada aqui: os valores abaixo são transcritos da tabela do livro.
"""

from __future__ import annotations

from typing import Any

# Herança Dracônica — tabela do traço "Herança Dracônica" do Draconato.
# A escolha define o tipo de dano do Ataque de Sopro e da Resistência a Dano.
HERANCA_DRACONICA: dict[str, dict[str, str]] = {
    "azul": {"nome": "Azul", "dano": "elétrico"},
    "branco": {"nome": "Branco", "dano": "gélido"},
    "bronze": {"nome": "Bronze", "dano": "elétrico"},
    "cobre": {"nome": "Cobre", "dano": "ácido"},
    "latao": {"nome": "Latão", "dano": "ígneo"},
    "negro": {"nome": "Negro", "dano": "ácido"},
    "ouro": {"nome": "Ouro", "dano": "ígneo"},
    "prata": {"nome": "Prata", "dano": "gélido"},
    "verde": {"nome": "Verde", "dano": "venenoso"},
    "vermelho": {"nome": "Vermelho", "dano": "ígneo"},
}

# Dano do Ataque de Sopro por nível de personagem (1d10, 2d10, 3d10 e 4d10).
DADO_SOPRO_POR_NIVEL = ((5, "2d10"), (11, "3d10"), (17, "4d10"))
DADO_SOPRO_BASE = "1d10"

# Formas do sopro e salvaguarda, conforme o texto do traço.
FORMAS_SOPRO = ("Cone de 4,5 metros", "Linha de 9 metros por 1,5 metro")

ESCOLHAS_ESPECIE: dict[str, dict[str, Any]] = {
    "draconato": {
        "campo": "heranca_draconica",
        "rotulo": "Herança Dracônica",
        "nota": "Define o tipo de dano do Ataque de Sopro e da Resistência a Dano.",
        "opcoes": HERANCA_DRACONICA,
    },
}


def escolha_de_especie(especie: Any) -> dict[str, Any] | None:
    """Devolve a escolha obrigatória da espécie, quando ela existe."""
    return ESCOLHAS_ESPECIE.get(str(especie or "").strip().lower())


def normalizar_escolha(especie: Any, valor: Any) -> str:
    """Valida a escolha de espécie e devolve a chave normalizada."""
    escolha = escolha_de_especie(especie)
    chave = str(valor or "").strip().lower().replace("-", "_")
    if escolha is None:
        raise ValueError(f"A espécie {especie} não exige escolha adicional")
    if chave not in escolha["opcoes"]:
        raise ValueError(f"{escolha['rotulo']} inválida: {valor}")
    return chave


def dado_sopro(nivel: int) -> str:
    """Dano do Ataque de Sopro por nível, conforme a progressão do traço."""
    dado = DADO_SOPRO_BASE
    for marca, valor in DADO_SOPRO_POR_NIVEL:
        if int(nivel) >= marca:
            dado = valor
    return dado


def bloco_heranca_draconica(
    chave: str,
    nivel: int,
    modificador_constituicao: int,
    bonus_proficiencia: int,
) -> dict[str, Any]:
    """Bloco derivado do Draconato para exibição e para o contexto do MJ."""
    heranca = HERANCA_DRACONICA[chave]
    return {
        "fonte": "Livro do Jogador 2024 — Herança Dracônica",
        "chave": chave,
        "nome": heranca["nome"],
        "linhagem": f"Dragão {heranca['nome']}",
        "tipo_dano": heranca["dano"],
        "resistencia": f"dano {heranca['dano']}",
        "sopro": {
            "dado": dado_sopro(nivel),
            "tipo_dano": heranca["dano"],
            "formas": list(FORMAS_SOPRO),
            "salvaguarda": "Destreza",
            "cd": 8 + int(modificador_constituicao) + int(bonus_proficiencia),
            "usos": int(bonus_proficiencia),
            "recarga": "descanso longo",
        },
    }


def resumo_escolha(especie: Any, valor: Any) -> str:
    """Texto curto da escolha para o contexto do MJ."""
    escolha = escolha_de_especie(especie)
    if escolha is None or not valor:
        return "nenhuma"
    opcao = escolha["opcoes"].get(str(valor))
    return opcao["nome"] if opcao else str(valor)
