"""Validação de conjuração do Artífice (lista de Tasha's usada pelo projeto).

A progressão de espaços segue o Artífice de meio conjurador com progressão
arredondada para cima, incluindo dois espaços de 1º círculo no nível 1.
"""

from __future__ import annotations

import unicodedata
from typing import Any

# Subconjunto explícito de magias do Artífice disponível no catálogo executável.
# Os nomes são os localizados em português usados pela interface.
ARTIFICER_SPELL_LEVELS: dict[str, int] = {
    # Truques
    "Acudir os Moribundos": 0,
    "Bolha Ácida": 0,
    "Chicote de Espinhos": 0,
    "Luz": 0,
    "Luzes Dançantes": 0,
    "Mensagem": 0,
    "Orientação": 0,
    "Prestidigitação Arcana": 0,
    "Raio de Fogo": 0,
    "Raio de Gelo": 0,
    "Rajada de Veneno": 0,
    "Resistência": 0,
    "Toque Chocante": 0,
    "Trovão": 0,
    # 1º círculo
    "Alarme": 1,
    "Passos Longos": 1,
    "Curar Ferimentos": 1,
    "Detectar Magia": 1,
    "Disfarçar-se": 1,
    "Fogo das Fadas": 1,
    "Graxa": 1,
    "Identificar": 1,
    "Purificar Alimentos e Bebidas": 1,
    "Queda Suave": 1,
    "Retirada Acelerada": 1,
    "Salto": 1,
    "Santuário": 1,
    "Vitalidade Vazia": 1,
    # 2º círculo
    "Aumentar/Reduzir": 2,
    "Alterar-se": 2,
    "Aprimorar Atributo": 2,
    "Auxílio": 2,
    "Arma Mágica": 2,
    "Boca Encantada": 2,
    "Chama Contínua": 2,
    "Desfoque": 2,
    "Escalada de Aranha": 2,
    "Invisibilidade": 2,
    "Levitação": 2,
    "Pirotecnia": 2,
    "Proteção Contra Veneno": 2,
    "Restauração Menor": 2,
    "Teia": 2,
    "Tranca Arcana": 2,
    "Truque de Corda": 2,
    "Ver o Invisível": 2,
    "Visão no Escuro": 2,
    "Esquentar Metal": 2,
    # 3º círculo
    "Arma Elemental": 3,
    "Celeridade": 3,
    "Caminhar Sobre as Águas": 3,
    "Criar Comida e Água": 3,
    "Dissipar Magia": 3,
    "Flechas Flamejantes": 3,
    "Glifo de Proteção": 3,
    "Piscar": 3,
    "Proteção Contra Energia": 3,
    "Respirar na Água": 3,
    "Revivificar": 3,
    "Servo Minúsculo": 3,
    "Voo": 3,
    # 4º círculo
    "Movimentação Livre": 4,
    "Maldição Elemental": 4,
    "Moldar Rochas": 4,
    "Olho Arcano": 4,
    "Fabricar": 4,
    "Baú Secreto de Leomund": 4,
    "Cão Fiel de Mordenkainen": 4,
    "Santuário Particular de Mordenkainen": 4,
    "Esfera Resiliente de Otiluke": 4,
    "Pele-Rocha": 4,
    "Invocar Constructo": 4,
    # 5º círculo
    "Animar Objetos": 5,
    "Criação": 5,
    "Fortalecimento de Perícia": 5,
    "Mão de Bigby": 5,
    "Muralha de Pedra": 5,
    "Restauração Maior": 5,
    # Lista base 2024 (Eberron: Forge of the Artificer / D&D Beyond UA 2024)
    "Mãos Mágicas": 0,
    "Golpe Certeiro": 0,
    "Elementalismo": 0,
    "Sopro de Dragão": 2,
    "Vigor Arcano": 2,
    "Círculo de Poder": 5,
}

# Slots por nível de Artífice. Índice 0 corresponde ao 1º círculo.
ARTIFICER_SLOTS: dict[int, tuple[int, ...]] = {
    1: (2,),
    2: (2,),
    3: (3,),
    4: (3,),
    5: (4, 2),
    6: (4, 2),
    7: (4, 3),
    8: (4, 3),
    9: (4, 3, 2),
    10: (4, 3, 2),
    11: (4, 3, 3),
    12: (4, 3, 3),
    13: (4, 3, 3, 1),
    14: (4, 3, 3, 1),
    15: (4, 3, 3, 2),
    16: (4, 3, 3, 2),
    17: (4, 3, 3, 3, 1),
    18: (4, 3, 3, 3, 1),
    19: (4, 3, 3, 3, 2),
    20: (4, 3, 3, 3, 2),
}


def normalizar_nome_magia(nome: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.replace("-", " ").split())


def progresso_artifice(nivel: int, inteligencia: int) -> dict[str, Any]:
    if not 1 <= int(nivel) <= 20:
        raise ValueError("O nível do Artífice deve estar entre 1 e 20")
    modificador = (int(inteligencia) - 10) // 2
    slots = {str(i + 1): quantidade for i, quantidade in enumerate(ARTIFICER_SLOTS[int(nivel)])}
    circulo_maximo = max(int(circulo) for circulo in slots)
    truques = 2 if nivel < 10 else 3 if nivel < 18 else 4
    preparadas = max(1, modificador + int(nivel) // 2)
    return {
        "resultado": "resolvido",
        "classe": "artifice",
        "nivel": int(nivel),
        "atributo_conjuracao": "inteligencia",
        "truques": truques,
        "magias_preparadas": preparadas,
        "circulo_maximo": circulo_maximo,
        "espacos_totais": slots,
    }


# Magias de subclasse do Artífice (Eberron: Forge of the Artificer). São sempre preparadas
# a partir do nível indicado e não contam na escolha de magias preparadas.
# Nomes em PT conferidos no cabeçalho do PHB 2024 (equivalentes EN do Forge entre parênteses).
# Pendentes, sem cabeçalho no PHB 2024 (não entram aqui): Golpe Brilhante (Branding Smite),
# Servo Homúnculo (Homunculus Servant), Passagem (Passwall).
ARTIFICER_SUBCLASS_SPELLS: dict[str, dict[int, list[str]]] = {
    "Armeiro": {
        3: ["Mísseis Mágicos", "Onda Trovejante"],  # Magic Missile, Thunderwave
        5: ["Reflexos", "Despedaçar"],  # Mirror Image, Shatter
        9: ["Padrão Hipnótico", "Relâmpago"],  # Hypnotic Pattern, Lightning Bolt
        13: ["Invisibilidade Maior"],  # Greater Invisibility
        17: ["Muralha de Energia"],
    },  # Wall of Force
    "Artilheiro": {
        3: ["Escudo Arcano", "Onda Trovejante"],  # Shield, Thunderwave
        5: ["Raio Ardente", "Despedaçar"],  # Scorching Ray, Shatter
        9: ["Bola de Fogo", "Muralha de Vento"],  # Fireball, Wind Wall
        13: ["Tempestade Glacial", "Muralha de Fogo"],  # Ice Storm, Wall of Fire
        17: ["Cone de Frio", "Muralha de Energia"],
    },  # Cone of Cold, Wall of Force
    "Alquimista": {
        3: ["Palavra Curativa", "Raio Nauseante"],
        5: ["Esfera Flamejante", "Flecha Ácida de Melf"],
        9: ["Forma Gasosa", "Palavra Curativa em Massa"],
        13: ["Proteção Contra a Morte", "Esfera Vitriólica"],
        17: ["Névoa Mortal", "Reviver os Mortos"],
    },  # Cloudkill, Raise Dead
    "Ferreiro de Batalha": {
        3: ["Heroísmo"],
        5: ["Vínculo de Proteção"],
        9: ["Aura de Vitalidade", "Invocar Barragem"],
        13: ["Escudo Ardente", "Aura de Pureza"],  # Fire Shield, Aura of Purity
        17: ["Destruição Banidora", "Curar Ferimentos em Massa"],
    },  # Banishing Smite
    "Cartógrafo": {
        3: ["Fogo das Fadas", "Raio Guia", "Palavra Curativa"],
        5: ["Localizar Objeto", "Espinho Mental"],  # Mind Spike
        9: ["Convocar Relâmpagos", "Clarividência"],  # Call Lightning, Clairvoyance
        13: ["Banimento", "Localizar Criatura"],
        17: ["Vidência", "Círculo de Teleporte"],
    },  # Scrying, Teleportation Circle
}

# Círculo de cada magia de subclasse, conferido no cabeçalho do PHB 2024.
CIRCULO_MAGIAS_SUBCLASSE: dict[str, int] = {
    "Mísseis Mágicos": 1,
    "Onda Trovejante": 1,
    "Reflexos": 2,
    "Despedaçar": 2,
    "Padrão Hipnótico": 3,
    "Relâmpago": 3,
    "Invisibilidade Maior": 4,
    "Muralha de Energia": 5,
    "Escudo Arcano": 1,
    "Raio Ardente": 2,
    "Bola de Fogo": 3,
    "Muralha de Vento": 3,
    "Tempestade Glacial": 4,
    "Muralha de Fogo": 4,
    "Cone de Frio": 5,
    "Palavra Curativa": 1,
    "Raio Nauseante": 1,
    "Esfera Flamejante": 2,
    "Flecha Ácida de Melf": 2,
    "Forma Gasosa": 3,
    "Palavra Curativa em Massa": 3,
    "Proteção Contra a Morte": 4,
    "Esfera Vitriólica": 4,
    "Reviver os Mortos": 5,
    "Heroísmo": 1,
    "Vínculo de Proteção": 2,
    "Aura de Vitalidade": 3,
    "Invocar Barragem": 3,
    "Escudo Ardente": 4,
    "Aura de Pureza": 4,
    "Curar Ferimentos em Massa": 5,
    "Destruição Banidora": 5,
    "Fogo das Fadas": 1,
    "Raio Guia": 1,
    "Localizar Objeto": 2,
    "Espinho Mental": 2,
    "Convocar Relâmpagos": 3,
    "Clarividência": 3,
    "Banimento": 4,
    "Localizar Criatura": 4,
    "Vidência": 5,
    "Círculo de Teleporte": 5,
    "Névoa Mortal": 5,
}


def circulo_magia_subclasse(nome: str) -> int | None:
    alvo = normalizar_nome_magia(nome)
    return next((c for n, c in CIRCULO_MAGIAS_SUBCLASSE.items() if normalizar_nome_magia(n) == alvo), None)


def magias_sempre_preparadas(subclasse: str | None, nivel: int) -> list[str]:
    """Magias de subclasse já liberadas no nível do Artífice (sempre preparadas)."""
    if not subclasse:
        return []
    tabela_sub = ARTIFICER_SUBCLASS_SPELLS.get(str(subclasse).strip())
    if tabela_sub is None:
        return []
    resultado: list[str] = []
    for nivel_min in sorted(tabela_sub):
        if nivel >= nivel_min:
            resultado.extend(n for n in tabela_sub[nivel_min] if n not in resultado)
    return resultado


def magia_sempre_preparada_do_artifice(subclasse: str | None, nivel: int, nome: str) -> bool:
    """True se a magia é de subclasse já liberada no nível do Artífice (não entra na escolha)."""
    alvo = normalizar_nome_magia(nome)
    return any(normalizar_nome_magia(n) == alvo for n in magias_sempre_preparadas(subclasse, nivel))


def listar_magias_artifice(nivel: int) -> list[dict[str, Any]]:
    from .spells import obter_magia

    progresso = progresso_artifice(nivel, 10)
    resultado = []
    for nome, circulo in ARTIFICER_SPELL_LEVELS.items():
        if circulo > progresso["circulo_maximo"]:
            continue
        magia = obter_magia(nome)
        if magia:
            resultado.append(dict(magia))
    return sorted(resultado, key=lambda m: (int(m.get("circulo", 99)), m["nome"].lower()))


def validar_escolhas_artifice(
    nivel: int,
    inteligencia: int,
    truques: list[str],
    magias_preparadas: list[str],
    espacos_totais: dict[str, int],
    subclasse: str | None = None,
) -> dict[str, Any]:
    from .spells import obter_magia

    progresso = progresso_artifice(nivel, inteligencia)
    sempre = {normalizar_nome_magia(n) for n in magias_sempre_preparadas(subclasse, nivel)}
    for nome in list(truques) + list(magias_preparadas):
        if normalizar_nome_magia(nome) in sempre:
            raise ValueError(f"Magia de subclasse já é sempre preparada e não entra na escolha: {nome}")
    permitidas = {normalizar_nome_magia(nome): circulo for nome, circulo in ARTIFICER_SPELL_LEVELS.items()}

    # A mesma magia não pode ocupar duas escolhas de truque/preparação.
    truques_normalizados = [normalizar_nome_magia(nome) for nome in truques]
    preparados_normalizados = [normalizar_nome_magia(nome) for nome in magias_preparadas]
    if len(set(truques_normalizados)) != len(truques_normalizados):
        raise ValueError("Não repita truques")
    if len(set(preparados_normalizados)) != len(preparados_normalizados):
        raise ValueError("Não repita magias preparadas")

    if len(truques) != progresso["truques"]:
        raise ValueError(f"Artífice de nível {nivel} deve registrar exatamente {progresso['truques']} truques")
    if len(magias_preparadas) != progresso["magias_preparadas"]:
        raise ValueError(
            f"Com INT {inteligencia}, este Artífice deve registrar exatamente {progresso['magias_preparadas']} magias preparadas"
        )
    for nome in truques:
        circulo = permitidas.get(normalizar_nome_magia(nome))
        if circulo != 0 or not obter_magia(nome):
            raise ValueError(f"Truque não disponível para Artífice: {nome}")
    for nome in magias_preparadas:
        circulo = permitidas.get(normalizar_nome_magia(nome))
        if circulo is None or circulo == 0:
            raise ValueError(f"Magia não disponível para Artífice: {nome}")
        if circulo > progresso["circulo_maximo"]:
            raise ValueError(f"Magia de {circulo}º círculo indisponível no nível {nivel}: {nome}")
        if not obter_magia(nome):
            raise ValueError(f"Magia ausente do catálogo: {nome}")
    esperados = progresso["espacos_totais"]
    recebidos: dict[str, int] = {}
    for chave, valor in espacos_totais.items():
        chave = str(chave)
        if chave not in {"1", "2", "3", "4", "5"}:
            raise ValueError(f"Círculo de espaços inválido: {chave}")
        if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
            raise ValueError("Quantidade de espaços deve ser um inteiro não negativo")
        if valor:
            recebidos[chave] = valor
    if recebidos != esperados:
        raise ValueError(f"Espaços de magia incorretos para Artífice nível {nivel}; esperado {esperados}")
    return progresso
