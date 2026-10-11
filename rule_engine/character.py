"""Criação e progressão de personagens do Livro do Jogador 2024."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .class_progression import caracteristicas_no_nivel, subclasses_da_classe


ESPECIES = {
    "aasimar": {"tamanho": "pequeno_ou_medio", "deslocamento": 9},
    "draconato": {"tamanho": "medio", "deslocamento": 9},
    "anao": {"tamanho": "medio", "deslocamento": 9},
    "elfo": {"tamanho": "medio", "deslocamento": 9},
    "gnomo": {"tamanho": "pequeno", "deslocamento": 9},
    "golias": {"tamanho": "medio", "deslocamento": 10.5},
    "halfling": {"tamanho": "pequeno", "deslocamento": 7.5},
    "humano": {"tamanho": "medio", "deslocamento": 9},
    "orc": {"tamanho": "medio", "deslocamento": 9},
}
CLASSES = {
    "barbaro": {"dado_vida": 12, "atributo_primario": "forca"},
    "bardo": {"dado_vida": 8, "atributo_primario": "carisma"},
    "clerigo": {"dado_vida": 8, "atributo_primario": "sabedoria"},
    "druida": {"dado_vida": 8, "atributo_primario": "sabedoria"},
    "guerreiro": {"dado_vida": 10, "atributo_primario": "forca_ou_destreza"},
    "monge": {"dado_vida": 8, "atributo_primario": "destreza_e_sabedoria"},
    "paladino": {"dado_vida": 10, "atributo_primario": "forca_ou_destreza_e_carisma"},
    "guardiao": {"dado_vida": 10, "atributo_primario": "destreza_e_sabedoria"},
    "ladino": {"dado_vida": 8, "atributo_primario": "destreza"},
    "feiticeiro": {"dado_vida": 6, "atributo_primario": "carisma"},
    "bruxo": {"dado_vida": 8, "atributo_primario": "carisma"},
    "mago": {"dado_vida": 6, "atributo_primario": "inteligencia"},
    "artifice": {"dado_vida": 8, "atributo_primario": "inteligencia"},
}
SUBCLASSES = {classe: {"nivel": 3, "nomes": set()} for classe in CLASSES}
SUBCLASSES["artifice"]["nomes"].update({"reanimador"})
SUBCLASSES["bardo"]["nomes"].update({"colegio_dos_espiritos"})
SUBCLASSES["clerigo"]["nomes"].update({"dominio_da_sepultura"})
SUBCLASSES["guardiao"]["nomes"].update({"guardiao_oculto"})
SUBCLASSES["ladino"]["nomes"].update({"fantasma"})
SUBCLASSES["feiticeiro"]["nomes"].update({"feiticaria_das_sombras"})
SUBCLASSES["bruxo"]["nomes"].update({"patrono_morto_vivo"})
SUBCLASSES_RAVENLOFT = {
    "reanimador": {"classe": "artifice", "nivel": 3},
    "colegio_dos_espiritos": {"classe": "bardo", "nivel": 3},
    "dominio_da_sepultura": {"classe": "clerigo", "nivel": 3},
    "guardiao_oculto": {"classe": "guardiao", "nivel": 3},
    "fantasma": {"classe": "ladino", "nivel": 3},
    "feiticaria_das_sombras": {"classe": "feiticeiro", "nivel": 3},
    "patrono_morto_vivo": {"classe": "bruxo", "nivel": 3},
}
TALENTOS = {
    "alerta", "artista", "atacante_selvagem", "curandeiro", "defensivo",
    "especialista_em_armaduras_leves", "especialista_em_armaduras_medias",
    "especialista_em_armaduras_pesadas", "sortudo", "habilidoso",
}
ATRIBUTOS = {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}


@dataclass
class Personagem:
    nome: str
    especie: str
    classe: str
    nivel: int
    atributos: dict[str, int]
    antecedente: str = ""
    subclasse: str | None = None
    talentos: set[str] = field(default_factory=set)
    classes_multiclasse: dict[str, int] = field(default_factory=dict)

    @property
    def bonus_proficiencia(self) -> int:
        return 2 + (self.nivel - 1) // 4

    @property
    def pontos_de_vida_iniciais(self) -> int:
        dado = CLASSES[self.classe]["dado_vida"]
        return dado + ((self.atributos.get("constituicao", 10) - 10) // 2)


def validar_atributos(atributos: Mapping[str, int]) -> dict[str, int]:
    if set(atributos) != ATRIBUTOS:
        raise ValueError("É necessário informar exatamente os seis atributos")
    valores = {nome: int(valor) for nome, valor in atributos.items()}
    if any(valor < 1 or valor > 20 for valor in valores.values()):
        raise ValueError("Atributos devem estar entre 1 e 20")
    return valores


def gerar_atributos_matriz_padrao() -> dict[str, int]:
    return {"forca": 15, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8}


def gerar_atributos_compra_pontos(pontos: Mapping[str, int]) -> dict[str, int]:
    valores = validar_atributos(pontos)
    custo = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
    if any(valor not in custo for valor in valores.values()) or sum(custo[valor] for valor in valores.values()) > 27:
        raise ValueError("Compra por pontos inválida: máximo de 27 pontos e valores de 8 a 15")
    return valores


def criar_personagem(fatos: Mapping[str, Any]) -> Personagem:
    especie = str(fatos["species"]).lower()
    classe = str(fatos["class"]).lower()
    nivel = int(fatos.get("level", 1))
    if especie not in ESPECIES:
        raise ValueError("Espécie inválida")
    if classe not in CLASSES:
        raise ValueError("Classe inválida")
    if not 1 <= nivel <= 20:
        raise ValueError("O nível deve estar entre 1 e 20")
    atributos = validar_atributos(fatos["ability_scores"])
    subclasse = fatos.get("subclass")
    if subclasse:
        subclasse = str(subclasse).lower()
        if nivel < SUBCLASSES[classe]["nivel"]:
            raise ValueError("A subclasse só pode ser escolhida no nível adequado")
        conhecida = subclasse in SUBCLASSES[classe]["nomes"]
        catalogadas = subclasses_da_classe(classe)
        if catalogadas and subclasse not in catalogadas:
            raise ValueError("Subclasse inválida para a classe escolhida")
        # Subclasses não detalhadas ainda permanecem aceitas para permitir a expansão
        # progressiva do catálogo das classes do Livro do Jogador.
        if subclasse in SUBCLASSES_RAVENLOFT and SUBCLASSES_RAVENLOFT[subclasse]["classe"] != classe:
            raise ValueError("A subclasse não pertence à classe escolhida")
    talentos = set(fatos.get("feats", ()))
    if not talentos <= TALENTOS:
        raise ValueError("Talento inválido")
    return Personagem(
        nome=str(fatos["name"]), especie=especie, classe=classe, nivel=nivel,
        atributos=atributos, antecedente=str(fatos.get("background", "")),
        subclasse=subclasse, talentos=talentos,
    )


def resolver_progressao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    nivel_atual = int(fatos["current_level"])
    novo_nivel = nivel_atual + 1
    classe = str(fatos["class"]).lower()
    if classe not in CLASSES or not 1 <= nivel_atual < 20:
        raise ValueError("Progressão de nível inválida")
    resultado: dict[str, Any] = {"resultado": "nivel_adquirido", "nivel": novo_nivel}
    asi_niveis = {"guerreiro": {4, 6, 8, 12, 14, 16, 19}, "ladino": {4, 8, 10, 12, 16, 19}}
    if novo_nivel in asi_niveis.get(classe, {4, 8, 12, 16, 19}):
        resultado["escolha"] = "aumento_de_atributo_ou_talento"
    if novo_nivel == 3:
        resultado["escolha_subclasse"] = True
    resultado["bonus_proficiencia"] = 2 + (novo_nivel - 1) // 4
    resultado["caracteristicas"] = caracteristicas_no_nivel(classe, novo_nivel)
    return resultado


def resolver_multiclasse(fatos: Mapping[str, Any]) -> dict[str, Any]:
    atributos = validar_atributos(fatos["ability_scores"])
    classe = str(fatos["new_class"]).lower()
    if classe not in CLASSES:
        raise ValueError("Classe inválida para multiclasse")
    requisitos = {
        "barbaro": {"forca": 13}, "guerreiro": {"forca": 13, "destreza": 13},
        "paladino": {"forca": 13, "carisma": 13}, "guardiao": {"destreza": 13, "sabedoria": 13},
        "monge": {"destreza": 13, "sabedoria": 13}, "ladino": {"destreza": 13},
        "bardo": {"carisma": 13}, "clerigo": {"sabedoria": 13}, "druida": {"sabedoria": 13},
        "feiticeiro": {"carisma": 13}, "bruxo": {"carisma": 13}, "mago": {"inteligencia": 13},
        "artifice": {"inteligencia": 13},
    }[classe]
    valido = all(atributos[nome] >= valor for nome, valor in requisitos.items())
    return {"resultado": "permitido" if valido else "bloqueado", "requisitos": requisitos}
