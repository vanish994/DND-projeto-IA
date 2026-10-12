"""Matriz de cobertura das características de classe do PHB 2024 e Ravenloft."""

FEATURES_BY_CLASS = {
    "barbaro": {
        1: ["Fúria", "Defesa sem Armadura", "Maestria em Arma"],
        2: ["Ataque Imprudente", "Sentido de Perigo"],
        3: ["Conhecimento Primordial", "Subclasse"],
        5: ["Ataque Extra", "Movimento Rápido"],
        7: ["Bote Instintivo", "Instintos Primitivos"],
        9: ["Golpe Brutal"],
        11: ["Fúria Implacável"],
        13: ["Golpe Brutal Fortalecido"],
        15: ["Fúria Persistente"],
        17: ["Golpe Brutal Fortalecido"],
        18: ["Força Indomável"],
        20: ["Campeão Primitivo"],
    },
    "bardo": {
        1: ["Inspiração de Bardo", "Conjuração"],
        2: ["Especialista", "Pau pra Toda Obra"],
        3: ["Subclasse"],
        5: ["Fonte de Inspiração"],
        7: ["Contra-Encantamento"],
        10: ["Segredos Mágicos"],
        18: ["Inspiração Superior"],
        20: ["Palavras de Criação"],
    },
    "clerigo": {
        1: ["Conjuração", "Ordem Divina"],
        2: ["Canalizar Divindade"],
        3: ["Subclasse"],
        5: ["Fulminar Mortos-Vivos"],
        7: ["Golpes Abençoados"],
        10: ["Intervenção Divina"],
        14: ["Golpes Abençoados Aprimorado"],
        20: ["Intervenção Divina Maior"],
    },
    "druida": {
        1: ["Conjuração", "Idioma Druídico", "Ordem Primal"],
        2: ["Forma Selvagem", "Companheiro Selvagem"],
        3: ["Subclasse"],
        5: ["Ressurgimento Selvagem"],
        7: ["Fúria Elemental"],
        15: ["Fúria Elemental Aprimorada"],
        18: ["Magias Bestiais"],
        20: ["Arquidruida"],
    },
    "guerreiro": {
        1: ["Estilo de Luta", "Maestria em Arma", "Recuperar Fôlego"],
        2: ["Mente Tática", "Surto de Ação"],
        3: ["Subclasse"],
        5: ["Ajuste Tático", "Ataque Extra"],
        9: ["Indomável", "Mestre Tático"],
        11: ["Dois Ataques Extras"],
        13: ["Ataques Estudados"],
        17: ["Indomável Aprimorado", "Surto de Ação Aprimorado"],
        20: ["Três Ataques Extras"],
    },
    "monge": {
        1: ["Artes Marciais", "Defesa sem Armadura"],
        2: ["Foco do Monge", "Movimento sem Armadura", "Metabolismo Incomum"],
        3: ["Defletir Ataques", "Subclasse"],
        4: ["Queda Lenta"],
        5: ["Ataque Extra", "Golpe Atordoante"],
        6: ["Golpes Potencializados"],
        7: ["Evasão"],
        9: ["Movimento Acrobático"],
        10: ["Foco Aprimorado", "Restauro Pessoal"],
        13: ["Defletir Energia"],
        14: ["Sobrevivente Disciplinado"],
        15: ["Foco Perfeito"],
        18: ["Defesa Superior"],
        20: ["Corpo e Mente"],
    },
    "paladino": {
        1: ["Conjuração", "Maestria em Arma", "Mãos Consagradas"],
        2: ["Destruição do Paladino", "Estilo de Luta"],
        3: ["Canalizar Divindade", "Subclasse"],
        5: ["Ataque Extra", "Montaria Fiel"],
        6: ["Aura de Proteção"],
        9: ["Repudiar Inimigos"],
        10: ["Aura de Coragem"],
        11: ["Golpes Radiantes"],
        14: ["Toque Restaurador"],
        18: ["Aura Expandida"],
    },
    "guardiao": {
        1: ["Conjuração", "Inimigo Favorito", "Maestria em Arma"],
        2: ["Estilo de Luta", "Explorador Hábil"],
        3: ["Subclasse"],
        5: ["Ataque Extra"],
        6: ["Errante"],
        9: ["Especialista"],
        10: ["Incansável"],
        13: ["Predador Implacável"],
        14: ["Véu da Natureza"],
        17: ["Caçador Preciso"],
        18: ["Sentidos Selvagens"],
        20: ["Matador de Inimigos Favoritos"],
    },
    "ladino": {
        1: ["Ataque Furtivo", "Especialização", "Gíria dos Ladrões", "Maestria em Arma"],
        2: ["Ação Ardilosa"],
        3: ["Mira Firme", "Subclasse"],
        5: ["Esquiva Sobrenatural", "Golpe Astuto"],
        7: ["Evasão", "Talento Confiável"],
        11: ["Golpe Astuto Aprimorado"],
        14: ["Golpes Sujos"],
        15: ["Mente Escorregadia"],
        18: ["Elusivo"],
        20: ["Golpe de Sorte"],
    },
    "feiticeiro": {
        1: ["Conjuração", "Feitiçaria Inata"],
        2: ["Fonte de Magia", "Metamagia"],
        3: ["Subclasse"],
        5: ["Restauração Feiticeira"],
        7: ["Feitiçaria Encarnada"],
        20: ["Apoteose Arcana"],
    },
    "bruxo": {
        1: ["Magia de Pacto", "Invocações Místicas"],
        2: ["Astúcia Mágica"],
        3: ["Subclasse"],
        9: ["Contatar Patrono"],
        11: ["Arcana Mística"],
        20: ["Mestre Místico"],
    },
    "mago": {
        1: ["Conjuração", "Livro de Magias", "Adepto de Ritual", "Recuperação Arcana"],
        2: ["Acadêmico"],
        3: ["Subclasse"],
        5: ["Memorizar Magia"],
        18: ["Maestria de Magias"],
        20: ["Assinatura Mágica"],
    },
    "artifice": {
        1: ["Conjuração", "Magia de Artífice"],
        2: ["Replicar Item Mágico"],
        3: ["Subclasse"],
        6: ["Artesão de Item Mágico"],
        7: ["Lampejo de Gênio"],
        10: ["Adepto de Item Mágico"],
        11: ["Item Armazenador de Magia"],
        14: ["Artífice Avançado"],
        18: ["Mestre de Item Mágico"],
        20: ["Alma do Artífice"],
    },
}

# Marcos de Aumento de Atributo/Talento do PHB 2024.
# Guerreiro também recebe esses marcos nos níveis 6 e 14; Ladino no nível 10.
# A Dádiva Épica é recebida no nível 19 pelas classes do PHB 2024.
_ASI_LEVELS = {classe: [4, 8, 12, 16, 19] for classe in FEATURES_BY_CLASS}
_ASI_LEVELS["guerreiro"] = [4, 6, 8, 12, 14, 16, 19]
_ASI_LEVELS["ladino"] = [4, 8, 10, 12, 16, 19]

for _classe, _niveis in _ASI_LEVELS.items():
    for _nivel in _niveis:
        nome = "Dádiva Épica" if _nivel == 19 else "Aumento de Atributo ou Talento"
        FEATURES_BY_CLASS[_classe].setdefault(_nivel, []).append(nome)

# Os marcos de subclasse são específicos por classe no PHB 2024.
# O Artífice mantém a progressão de subclasse da versão adotada pelo projeto.
_SUBCLASS_LEVELS = {
    "barbaro": (3, 6, 10, 14),
    "bardo": (3, 6, 14),
    "clerigo": (3, 6, 17),
    "druida": (3, 6, 10, 14),
    "guerreiro": (3, 7, 10, 15, 18),
    "monge": (3, 6, 11, 17),
    "paladino": (3, 7, 15, 20),
    "guardiao": (3, 7, 11, 15),
    "ladino": (3, 9, 13, 17),
    "feiticeiro": (3, 6, 14, 18),
    "bruxo": (3, 6, 10, 14),
    "mago": (3, 6, 10, 14),
    "artifice": (3, 5, 9, 15),
}
for _classe, _niveis in _SUBCLASS_LEVELS.items():
    for _nivel in _niveis:
        if _nivel != 3:  # nível 3 já é registrado como escolha de Subclasse
            FEATURES_BY_CLASS[_classe].setdefault(_nivel, []).append("Característica de Subclasse")


SUBCLASSES_BY_CLASS = {
    "barbaro": {
        "trilha_da_arvore_do_mundo",
        "trilha_do_berserker",
        "trilha_do_coracao_selvagem",
        "caminho_do_guerreiro_espiritual",
        "trilha_do_fanatico",
    },
    "bardo": {
        "colegio_da_bravura",
        "colegio_da_danca",
        "colegio_do_conhecimento",
        "colegio_do_glamour",
        "colegio_dos_espiritos",
    },
    "clerigo": {
        "dominio_da_vida",
        "dominio_da_luz",
        "dominio_da_trickery",
        "dominio_da_guerra",
        "dominio_da_sepultura",
    },
    "druida": {"circulo_da_lua", "circulo_da_terra", "circulo_das_estrelas", "circulo_do_mar"},
    "guerreiro": {"campeao", "cavaleiro_mistico", "combatente_psiquico", "mestre_da_batalha"},
    "monge": {
        "combatente_da_mao_espalmada",
        "combatente_da_misericordia",
        "combatente_das_sombras",
        "combatente_dos_elementos",
    },
    "paladino": {"juramento_da_devocao", "juramento_da_gloria", "juramento_de_vinganca", "juramento_dos_anciaos"},
    "guardiao": {"andarilho_feerico", "cacador", "senhor_das_feras", "vigilante_das_sombras", "guardiao_oculto"},
    "ladino": {"adaga_espiritual", "assassino", "ladrao", "trapaceiro_arcano", "fantasma"},
    "feiticeiro": {
        "feiticaria_aberrante",
        "feiticaria_draconica",
        "feiticaria_mecanica",
        "feiticaria_selvagem",
        "feiticaria_das_sombras",
    },
    "bruxo": {
        "patrono_arqueifada",
        "patrono_celestial",
        "patrono_grande_antigo",
        "patrono_infero",
        "patrono_morto_vivo",
    },
    "mago": {"abjurador", "adivinhador", "evocador", "ilusionista"},
    "artifice": {"reanimador"},
}


def caracteristicas_no_nivel(classe: str, nivel: int) -> list[str]:
    return list(FEATURES_BY_CLASS.get(classe, {}).get(nivel, ()))


def subclasses_da_classe(classe: str) -> set[str]:
    return set(SUBCLASSES_BY_CLASS.get(classe, set()))
