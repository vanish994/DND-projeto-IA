"""Núcleo de equipamentos, armas, armaduras e magias do Livro do Jogador 2024."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

PROPRIEDADES_ARMAS = {
    "acuidade",
    "alcance",
    "arremesso",
    "duas_maos",
    "extensao",
    "leve",
    "municao",
    "pesada",
    "recarga",
    "versatil",
}
MAESTRIAS_ARMAS = {"afligir", "agil", "derrubar", "drenar", "empurrar", "garantido", "lentidao", "trespassar"}


@dataclass
class EstadoEquipamento:
    """Equipamentos conhecidos, armas, armaduras e carga de uma criatura."""

    forca: int
    proficiencias: set[str] = field(default_factory=set)
    propriedades_armas: dict[str, set[str]] = field(default_factory=dict)
    maestrias: dict[str, str] = field(default_factory=dict)
    peso_carregado: float = 0.0

    @property
    def capacidade_carga(self) -> float:
        return max(0, self.forca) * 7.5

    @property
    def sobrecarregado(self) -> bool:
        return self.peso_carregado > self.capacidade_carga


def validar_propriedades_armas(propriedades: set[str]) -> set[str]:
    invalidas = set(propriedades) - PROPRIEDADES_ARMAS
    if invalidas:
        raise ValueError(f"Propriedades de arma inválidas: {sorted(invalidas)}")
    return set(propriedades)


def calcular_ca(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Calcula CA sem armadura, com armadura leve/média/pesada e escudo."""
    destreza = int(fatos.get("dexterity_modifier", 0))
    armadura = fatos.get("armor", "nenhuma")
    bonus = int(fatos.get("armor_bonus", 0))
    if armadura == "nenhuma":
        ca = 10 + destreza
    elif armadura == "leve":
        ca = 10 + bonus + destreza
    elif armadura == "media":
        ca = 10 + bonus + min(2, destreza)
    elif armadura == "pesada":
        if int(fatos.get("strength", 0)) < int(fatos.get("minimum_strength", 0)):
            return {"resultado": "bloqueado", "motivo": "forca_insuficiente"}
        ca = 10 + bonus
    else:
        raise ValueError("Tipo de armadura inválido")
    if bool(fatos.get("shield", False)):
        ca += int(fatos.get("shield_bonus", 2))
    if not bool(fatos.get("armor_proficient", True)):
        return {"resultado": "bloqueado", "motivo": "sem_proficiencia_em_armadura"}
    return {"resultado": "calculada", "ca": ca}


def resolver_arma(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida propriedades e proficiência de uma arma e retorna sua maestria."""
    nome = str(fatos["weapon"])
    propriedades = validar_propriedades_armas(set(fatos.get("properties", ())))
    proficiente = bool(fatos.get("proficient", True))
    if not proficiente:
        return {"resultado": "bloqueado", "motivo": "sem_proficiencia", "arma": nome}
    maestria = fatos.get("mastery")
    if maestria is not None and maestria not in MAESTRIAS_ARMAS:
        raise ValueError("Maestria de arma inválida")
    return {"resultado": "permitida", "arma": nome, "propriedades": sorted(propriedades), "maestria": maestria}


def resolver_duas_armas(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida o ataque adicional com arma Leve na outra mão."""
    if "leve" not in set(fatos.get("primary_properties", ())):
        return {"resultado": "bloqueado", "motivo": "arma_principal_nao_e_leve"}
    if "leve" not in set(fatos.get("secondary_properties", ())):
        return {"resultado": "bloqueado", "motivo": "arma_secundaria_nao_e_leve"}
    return {"resultado": "permitido", "usa_acao_bonus": True}


def resolver_carga(fatos: Mapping[str, Any]) -> dict[str, Any]:
    capacidade = max(0, int(fatos["strength"])) * 7.5
    peso = float(fatos.get("weight", 0))
    return {"resultado": "sobrecarregado" if peso > capacidade else "normal", "capacidade": capacidade, "peso": peso}


@dataclass
class EstadoMagia:
    """Preparação, espaços e concentração de um conjurador."""

    preparadas: set[str] = field(default_factory=set)
    espacos: dict[int, int] = field(default_factory=dict)
    concentrando: str | None = None

    def preparar(self, magia: str) -> dict[str, Any]:
        self.preparadas.add(magia)
        return {"resultado": "preparada", "magia": magia}

    def gastar_espaco(self, nivel: int) -> None:
        if self.espacos.get(nivel, 0) <= 0:
            raise ValueError("Não há espaço de magia disponível")
        self.espacos[nivel] -= 1


def resolver_conjuracao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida preparação, espaço, componentes, ritual e concentração."""
    magia = str(fatos["spell"])
    nivel = int(fatos.get("spell_level", 0))
    ritual = bool(fatos.get("ritual", False))
    preparada = bool(fatos.get("prepared", True))
    if nivel > 0 and not ritual and not preparada:
        return {"resultado": "bloqueado", "motivo": "magia_nao_preparada"}
    if nivel > 0 and not ritual and not bool(fatos.get("has_slot", False)):
        return {"resultado": "bloqueado", "motivo": "sem_espaco"}
    if ritual and not bool(fatos.get("ritualista", False)):
        return {"resultado": "bloqueado", "motivo": "sem_capacidade_de_ritual"}
    faltantes = set(fatos.get("required_components", ())) - set(fatos.get("available_components", ()))
    if faltantes:
        return {"resultado": "bloqueado", "motivo": "componentes_ausentes", "faltantes": sorted(faltantes)}
    anterior = fatos.get("concentrating_on")
    return {
        "resultado": "conjurada",
        "magia": magia,
        "nivel": nivel,
        "ritual": ritual,
        "tempo_extra_minutos": 10 if ritual else 0,
        "encerra_concentracao_anterior": bool(anterior),
    }


def resolver_salvaguarda_concentracao(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve a salvaguarda de Constituição para manter concentração após dano."""
    concentrando = fatos.get("concentrating", fatos.get("concentrando", False))
    incapacitado = bool(fatos.get("incapacitated", fatos.get("incapacitado", False)))
    morto = bool(fatos.get("dead", fatos.get("morto", False)))
    if not concentrando:
        return {"resultado": "não_concentrando", "concentracao_mantida": False, "requer_salvaguarda": False}
    if incapacitado or morto:
        motivo = "morto" if morto else "incapacitado"
        return {
            "resultado": "concentracao_encerrada",
            "concentracao_mantida": False,
            "requer_salvaguarda": False,
            "motivo": motivo,
        }
    dano = int(fatos.get("damage", fatos.get("dano", 0)))
    if dano <= 0:
        return {"resultado": "sem_dano", "concentracao_mantida": True, "requer_salvaguarda": False}
    cd = max(10, dano // 2)
    vantagem = bool(fatos.get("advantage", fatos.get("vantagem", False)))
    desvantagem = bool(fatos.get("disadvantage", fatos.get("desvantagem", False)))
    if vantagem and desvantagem:
        vantagem = desvantagem = False
    rolagens = fatos.get("rolls", fatos.get("rolagens"))
    if rolagens is not None:
        rolagens = [int(r) for r in rolagens]
        if not rolagens or any(r < 1 or r > 20 for r in rolagens):
            raise ValueError("As rolagens devem ser valores de d20 entre 1 e 20")
        if (vantagem or desvantagem) and len(rolagens) < 2:
            raise ValueError("Vantagem/desvantagem exige ao menos duas rolagens")
        rolagem = max(rolagens) if vantagem else min(rolagens) if desvantagem else rolagens[0]
    else:
        if "roll" not in fatos and "rolagem" not in fatos:
            raise ValueError("A salvaguarda de concentração exige rolagem auditável")
        rolagem = int(fatos.get("roll", fatos.get("rolagem")))
        if not 1 <= rolagem <= 20:
            raise ValueError("A rolagem deve ser um valor de d20 entre 1 e 20")
    modificador = int(
        fatos.get(
            "constitution_modifier",
            fatos.get("modificador_constituicao", fatos.get("modifier", fatos.get("modificador", 0))),
        )
    )
    total = rolagem + modificador
    sucesso = total >= cd
    return {
        "resultado": "sucesso" if sucesso else "falha",
        "rolagem": rolagem,
        "modificador": modificador,
        "total": total,
        "cd": cd,
        "dano_sofrido": dano,
        "concentracao_mantida": sucesso,
        "requer_salvaguarda": True,
        "motivo": "cd_atingida" if sucesso else "cd_nao_atingida",
    }


def resolver_alvo_magia(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida alcance, número de alvos e linha de efeito de uma magia."""
    if float(fatos.get("distance", 0)) > float(fatos.get("range", 0)):
        return {"resultado": "bloqueado", "motivo": "alvo_fora_do_alcance"}
    if not bool(fatos.get("line_of_effect", True)):
        return {"resultado": "bloqueado", "motivo": "sem_linha_de_efeito"}
    max_alvos = int(fatos.get("max_targets", 1))
    alvos = int(fatos.get("targets", 1))
    if alvos < 1 or alvos > max_alvos:
        return {"resultado": "bloqueado", "motivo": "numero_de_alvos_invalido"}
    return {"resultado": "alvos_validos", "alvos": alvos}


def resolver_area_magia(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida uma área de efeito e retorna sua forma e medidas."""
    formas = {"cilindro", "cone", "cubo", "emanação", "esfera", "linha"}
    forma = str(fatos.get("shape", "")).lower()
    if forma not in formas:
        raise ValueError("Forma de área de efeito inválida")
    medida = float(fatos.get("size", 0))
    if medida <= 0:
        raise ValueError("A área de efeito deve ter medida positiva")
    return {"resultado": "area_valida", "forma": forma, "medida": medida}
