"""Dados de combate estruturados do SRD 5.2.1.

Cada bloco contém apenas campos transcritos de uma fonte identificada. O catálogo
resumido em bestiary.py continua sendo a fonte de CA/PV/ND; estes metadados
acrescentam atributos, salvaguardas e ações executáveis no combate tático.
"""
BLOCOS_COMPLETOS = {
    "Bandit": {
        "atributos": {
            "forca": 11, "destreza": 12, "constituicao": 12,
            "inteligencia": 10, "sabedoria": 10, "carisma": 10,
        },
        "modificadores": {
            "forca": 0, "destreza": 1, "constituicao": 1,
            "inteligencia": 0, "sabedoria": 0, "carisma": 0,
        },
        "salvaguardas": {
            "forca": 0, "destreza": 1, "constituicao": 1,
            "inteligencia": 0, "sabedoria": 0, "carisma": 0,
        },
        "bonus_proficiencia": 2,
        "deslocamento_pes": 30,
        "acoes": [
            {
                "nome": "Scimitar",
                "desc": "Melee Attack Roll: +3, reach 5 ft. Hit: 4 (1d6 + 1) Slashing damage.",
                "tipo": "ataque",
                "bonus_ataque": 3,
                "alcance_corpo_a_corpo": 5,
                "dano_dados": "1d6",
                "dano_modificador": 1,
                "tipo_dano": "Slashing",
            },
            {
                "nome": "Light Crossbow",
                "desc": "Ranged Attack Roll: +3, range 80/320 ft. Hit: 5 (1d8 + 1) Piercing damage.",
                "tipo": "ataque",
                "bonus_ataque": 3,
                "alcance_normal": 80,
                "alcance_maximo": 320,
                "dano_dados": "1d8",
                "dano_modificador": 1,
                "tipo_dano": "Piercing",
            },
        ],
        "reacoes": [],
        "acoes_bonus": [],
        "acoes_lendarias": [],
        "origem": "SRD 5.2.1 — Bandit",
    },
}
