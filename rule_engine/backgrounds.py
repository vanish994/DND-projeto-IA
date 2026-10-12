"""Antecedentes do Livro do Jogador 2024 e de Ravenloft: Horror Wilds."""

from __future__ import annotations

from typing import Any, Mapping

FONTE_PHB = "Livro do Jogador 2024 — Antecedentes"
FONTE_RAVENLOFT = "Ravenloft: Horror Wilds — Antecedentes"


def _bg(nome, atributos, talento, pericias, ferramenta, equipamento_a, fonte=FONTE_PHB, talentos_alternativos=()):
    return {
        "nome": nome,
        "atributos": tuple(atributos),
        "talento": talento,
        "talentos_alternativos": tuple(talentos_alternativos),
        "pericias": tuple(pericias),
        "ferramenta": ferramenta,
        "equipamento": {"A": equipamento_a, "B": "50 PO"},
        "fonte": fonte,
    }


ANTECEDENTES: dict[str, dict[str, Any]] = {
    "acolito": _bg(
        "Acólito",
        ("inteligencia", "sabedoria", "carisma"),
        "iniciado_em_magia:clerigo",
        ("intuicao", "religiao"),
        "Suprimentos de Calígrafo",
        "Suprimentos de Calígrafo, Livro (orações), Símbolo Sagrado, Pergaminho (10 folhas), Túnica, 8 PO",
    ),
    "andarilho": _bg(
        "Andarilho",
        ("destreza", "sabedoria", "carisma"),
        "sortudo",
        ("furtividade", "intuicao"),
        "Ferramentas de Ladrão",
        "2 Adagas, Ferramentas de Ladrão, Kit de Jogos (qualquer um), 2 Algibeiras, Roupas de Viagem, Saco de Dormir, 16 PO",
    ),
    "artesao": _bg(
        "Artesão",
        ("forca", "destreza", "inteligencia"),
        "artifista",
        ("investigacao", "persuasao"),
        "Escolha um tipo de Ferramentas de Artesão",
        "Ferramentas de Artesão (a mesma que acima), 2 Algibeiras, Roupas de Viagem, 32 PO",
    ),
    "artista": _bg(
        "Artista",
        ("forca", "destreza", "carisma"),
        "musico",
        ("acrobacia", "atuacao"),
        "Escolha um tipo de Instrumento Musical",
        "Instrumento Musical (o mesmo que acima), Espelho, 2 Fantasias, Perfume, Roupas de Viagem, 11 PO",
    ),
    "charlatao": _bg(
        "Charlatão",
        ("destreza", "constituicao", "carisma"),
        "habilidoso",
        ("enganacao", "prestidigitacao"),
        "Kit de Falsificação",
        "Kit de Falsificação, Fantasia, Roupas Finas, 15 PO",
    ),
    "criminoso": _bg(
        "Criminoso",
        ("destreza", "constituicao", "inteligencia"),
        "alerta",
        ("furtividade", "prestidigitacao"),
        "Ferramentas de Ladrão",
        "2 Adagas, Ferramentas de Ladrão, 2 Algibeiras, Pé de Cabra, Roupas de Viagem, 16 PO",
    ),
    "eremita": _bg(
        "Eremita",
        ("constituicao", "sabedoria", "carisma"),
        "curandeiro",
        ("medicina", "religiao"),
        "Kit de Herbalismo",
        "Cajado, Kit de Herbalismo, Lâmpada, Livro (filosofia), Óleo (3 frascos), Roupas de Viagem, Saco de Dormir, 16 PO",
    ),
    "escriba": _bg(
        "Escriba",
        ("destreza", "inteligencia", "sabedoria"),
        "habilidoso",
        ("investigacao", "percepcao"),
        "Suprimentos de Calígrafo",
        "Suprimentos de Calígrafo, Lâmpada, Óleo (3 frascos), Pergaminho (12 folhas), Roupas Finas, 23 PO",
    ),
    "fazendeiro": _bg(
        "Fazendeiro",
        ("forca", "constituicao", "sabedoria"),
        "vigoroso",
        ("lidar_com_animais", "natureza"),
        "Ferramentas de Carpinteiro",
        "Foice, Ferramentas de Carpinteiro, Kit de Curandeiro, Balde de Ferro, Pá, 30 PO",
    ),
    "guarda": _bg(
        "Guarda",
        ("forca", "inteligencia", "sabedoria"),
        "alerta",
        ("atletismo", "percepcao"),
        "Escolha um tipo de Kit de Jogos",
        "Lança, Besta Leve, 20 Virotes, Kit de Jogos (o mesmo que acima), Aljava, Grilhões, Lanterna Coberta, Roupas de Viagem, 12 PO",
    ),
    "guia": _bg(
        "Guia",
        ("destreza", "constituicao", "sabedoria"),
        "iniciado_em_magia:druida",
        ("furtividade", "sobrevivencia"),
        "Ferramentas de Cartógrafo",
        "Arco Curto, 20 Flechas, Ferramentas de Cartógrafo, Aljava, Roupas de Viagem, Saco de Dormir, Tenda, 3 PO",
    ),
    "marinheiro": _bg(
        "Marinheiro",
        ("forca", "destreza", "sabedoria"),
        "valentao_de_taverna",
        ("acrobacia", "percepcao"),
        "Ferramentas de Navegador",
        "Adaga, Ferramentas de Navegador, Corda, Roupas de Viagem, 20 PO",
    ),
    "mercador": _bg(
        "Mercador",
        ("constituicao", "inteligencia", "carisma"),
        "sortudo",
        ("lidar_com_animais", "persuasao"),
        "Ferramentas de Navegador",
        "Ferramentas de Navegador, 2 Algibeiras, Roupas de Viagem, 22 PO",
    ),
    "nobre": _bg(
        "Nobre",
        ("forca", "inteligencia", "carisma"),
        "habilidoso",
        ("historia", "persuasao"),
        "Escolha um tipo de Kit de Jogos",
        "Kit de Jogos (o mesmo que acima), Perfume, Roupas Finas, 29 PO",
    ),
    "sabio": _bg(
        "Sábio",
        ("constituicao", "inteligencia", "sabedoria"),
        "iniciado_em_magia:mago",
        ("arcanismo", "historia"),
        "Suprimentos de Calígrafo",
        "Cajado, Suprimentos de Calígrafo, Livro (história), Pergaminho (8 folhas), Túnica, 8 PO",
    ),
    "soldado": _bg(
        "Soldado",
        ("forca", "destreza", "constituicao"),
        "atacante_selvagem",
        ("atletismo", "intimidacao"),
        "Escolha um tipo de Kit de Jogos",
        "Lança, Arco Curto, 20 Flechas, Kit de Curandeiro, Kit de Jogos (o mesmo que acima), Aljava, Roupas de Viagem, 14 PO",
    ),
    "assombrado": _bg(
        "Assombrado",
        ("constituicao", "sabedoria", "carisma"),
        "sobrevivente",
        ("arcanismo", "sobrevivencia"),
        "Escolha um tipo de Kit de Jogos",
        "Kit de Jogos (o mesmo que acima), Pé de Cabra, Água Benta (1 frasco), Espelho, Óleo (2 frascos), Apito de Sinalização, Estojo de Isqueiro, Roupas de Viagem, 5 Tochas, Odre, 14 PO",
        FONTE_RAVENLOFT,
        ("dadiva_sombria",),
    ),
    "investigador": _bg(
        "Investigador",
        ("inteligencia", "sabedoria", "carisma"),
        "olho_agucado",
        ("intuicao", "investigacao"),
        "Kit de Disfarce",
        "Kit de Disfarce, Grilhões, Pá, Roupas de Viagem, 3 Frascos, 16 PO",
        FONTE_RAVENLOFT,
        ("dadiva_sombria",),
    ),
    "andarilho_da_nevoa": _bg(
        "Andarilho da Névoa",
        ("destreza", "constituicao", "sabedoria"),
        "dadiva_sombria",
        ("sobrevivencia", "furtividade"),
        "Escolha um tipo de Ferramentas de Artesão",
        "Ferramentas de Artesão (a mesma que acima), Lâmpada, Óleo (5 frascos), Algibeira, Corda, Estojo de Isqueiro, Roupas de Viagem, 30 PO",
        FONTE_RAVENLOFT,
    ),
    "medium_espiritual": _bg(
        "Médium Espiritual",
        ("constituicao", "inteligencia", "sabedoria"),
        "dadiva_sombria",
        ("intuicao", "religiao"),
        "Escolha um tipo de Kit de Jogos",
        "Adaga, Kit de Jogos (o mesmo que acima), Cesto, Sino, 8 Velas, Tinta, Caneta-tinteiro, Papel (5 folhas), Estojo de Isqueiro, Roupas de Viagem, 32 PO",
        FONTE_RAVENLOFT,
    ),
}

# Recomendações do livro para os antecedentes que concedem Dádiva Sombria.
DADIVA_RECOMENDADA = {"andarilho_da_nevoa": "andarilho_das_brumas", "medium_espiritual": "sussurros_reunidos"}


def aplicar_aumentos_antecedente(
    antecedente: str, atributos: Mapping[str, int], aumentos: Mapping[str, int]
) -> dict[str, int]:
    """Aplica +2/+1 ou +1/+1/+1 apenas nos três atributos do antecedente (máximo 20)."""
    dados = ANTECEDENTES.get(antecedente)
    if dados is None:
        raise ValueError("Antecedente inválido")
    aumentos = {nome: int(valor) for nome, valor in aumentos.items() if int(valor)}
    if not set(aumentos) <= set(dados["atributos"]):
        raise ValueError("Os aumentos só podem ir para os atributos do antecedente")
    if sorted(aumentos.values()) not in ([1, 2], [1, 1, 1]):
        raise ValueError("Aumente um atributo em 2 e outro em 1, ou três atributos em 1")
    resultado = dict(atributos)
    for nome, valor in aumentos.items():
        resultado[nome] = resultado[nome] + valor
        if resultado[nome] > 20:
            raise ValueError("Nenhum aumento de antecedente pode passar de 20")
    return resultado
