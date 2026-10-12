"""Núcleo de sobrevivência do Livro do Jogador 2024."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


@dataclass
class EstadoVital:
    """Estado mutável de vida de uma criatura."""

    pv_maximos: int
    pv_atuais: int
    pv_temporarios: int = 0
    inconsciente: bool = False
    estavel: bool = False
    salvaguardas_sucesso: int = 0
    salvaguardas_falha: int = 0
    exaustao: int = 0
    morto: bool = False
    dados_vida_maximos: int = 0
    dados_vida_disponiveis: int | None = None

    def __post_init__(self) -> None:
        if self.pv_maximos <= 0:
            raise ValueError("PV máximos devem ser positivos")
        if not 0 <= self.pv_atuais <= self.pv_maximos:
            raise ValueError("PV atuais devem estar entre 0 e os PV máximos")
        if self.pv_temporarios < 0 or not 0 <= self.exaustao <= 6:
            raise ValueError("PV temporários e Exaustão devem ser válidos")
        self.dados_vida_maximos = max(0, int(self.dados_vida_maximos))
        if self.dados_vida_disponiveis is None:
            self.dados_vida_disponiveis = self.dados_vida_maximos
        if not 0 <= int(self.dados_vida_disponiveis) <= self.dados_vida_maximos:
            raise ValueError("Dados de Vida disponíveis devem estar entre 0 e o máximo")
        self.dados_vida_disponiveis = int(self.dados_vida_disponiveis)


def ajustar_dano(
    dano: int,
    *,
    resistente: bool = False,
    vulneravel: bool = False,
    imune: bool = False,
) -> int:
    """Aplica ajustes e depois Resistência e Vulnerabilidade, nessa ordem."""
    dano = max(0, int(dano))
    if imune:
        return 0
    if resistente:
        dano //= 2
    if vulneravel:
        dano *= 2
    return dano


def aplicar_dano(
    estado: EstadoVital,
    dano: int,
    *,
    critico: bool = False,
    dano_ajustado: bool = False,
    tipo_dano: str | None = None,
    origem: str | None = None,
    resistencias: Iterable[str] = (),
    vulnerabilidades: Iterable[str] = (),
    imunidades: Iterable[str] = (),
) -> dict[str, Any]:
    """Aplica dano, absorvendo PV temporários e tratando 0 PV."""
    if dano_ajustado:
        dano = max(0, int(dano))
    else:
        dano = ajustar_dano(
            dano,
            resistente=tipo_dano in set(resistencias),
            vulneravel=tipo_dano in set(vulnerabilidades),
            imune=tipo_dano in set(imunidades),
        )
    antes_pv = estado.pv_atuais
    absorvido = min(estado.pv_temporarios, dano)
    estado.pv_temporarios -= absorvido
    restante = dano - absorvido
    estado.pv_atuais = max(0, estado.pv_atuais - restante)
    resultado: dict[str, Any] = {
        "dano_total": dano,
        "dano_absorvido_pv_temporarios": absorvido,
        "pv_atuais": estado.pv_atuais,
        "pv_temporarios": estado.pv_temporarios,
    }
    if tipo_dano is not None:
        resultado["tipo_dano"] = tipo_dano
    if origem is not None:
        resultado["origem"] = origem
    if estado.pv_atuais > 0:
        return resultado
    if antes_pv > 0 and restante >= estado.pv_maximos:
        estado.morto = True
        resultado["estado"] = "morto"
        return resultado
    estado.inconsciente = True
    estado.estavel = False
    if critico:
        estado.salvaguardas_falha = min(3, estado.salvaguardas_falha + 2)
    elif restante > 0:
        estado.salvaguardas_falha = min(3, estado.salvaguardas_falha + 1)
    if estado.salvaguardas_falha >= 3:
        estado.morto = True
        resultado["estado"] = "morto"
    else:
        resultado["estado"] = "inconsciente"
    resultado["salvaguardas_falha"] = estado.salvaguardas_falha
    return resultado


def curar(estado: EstadoVital, quantidade: int) -> dict[str, Any]:
    """Recupera PV sem ultrapassar o máximo; cura remove inconsciência."""
    antes = estado.pv_atuais
    estado.pv_atuais = min(estado.pv_maximos, estado.pv_atuais + max(0, int(quantidade)))
    recuperado = estado.pv_atuais - antes
    if recuperado > 0:
        estado.inconsciente = False
        estado.estavel = False
        estado.salvaguardas_sucesso = 0
        estado.salvaguardas_falha = 0
    return {"pv_recuperados": recuperado, "pv_atuais": estado.pv_atuais, "consciente": not estado.inconsciente}


def salvaguarda_contra_morte(estado: EstadoVital, rolagem: int) -> dict[str, Any]:
    """Resolve uma Salvaguarda contra a Morte quando a criatura está a 0 PV."""
    if estado.morto or estado.pv_atuais > 0 or not estado.inconsciente or estado.estavel:
        raise ValueError("A criatura não pode fazer esta Salvaguarda contra a Morte")
    rolagem = int(rolagem)
    if not 1 <= rolagem <= 20:
        raise ValueError("A rolagem da Salvaguarda contra a Morte deve estar entre 1 e 20")
    if rolagem == 1:
        estado.salvaguardas_falha = min(3, estado.salvaguardas_falha + 2)
        resultado = "falha"
    elif rolagem == 20:
        curar(estado, 1)
        return {"resultado": "recuperou_1_pv", "pv_atuais": estado.pv_atuais}
    elif rolagem >= 10:
        estado.salvaguardas_sucesso += 1
        resultado = "sucesso"
    else:
        estado.salvaguardas_falha = min(3, estado.salvaguardas_falha + 1)
        resultado = "falha"
    if estado.salvaguardas_sucesso >= 3:
        estado.estavel = True
        return {"resultado": resultado, "estado": "estavel", "sucessos": estado.salvaguardas_sucesso}
    if estado.salvaguardas_falha >= 3:
        estado.morto = True
        return {"resultado": resultado, "estado": "morto", "falhas": estado.salvaguardas_falha}
    return {
        "resultado": resultado,
        "estado": "inconsciente",
        "sucessos": estado.salvaguardas_sucesso,
        "falhas": estado.salvaguardas_falha,
    }


def estabilizar(estado: EstadoVital, *, teste_medicina: int | None = None, kit_medico: bool = False) -> dict[str, Any]:
    """Estabiliza com teste de Sabedoria (Medicina) CD 10 ou uso de kit médico."""
    if estado.pv_atuais > 0 or estado.morto:
        raise ValueError("A criatura não precisa ser estabilizada")
    if teste_medicina is None and not kit_medico:
        return {"resultado": "bloqueado", "motivo": "teste_medicina_ou_kit_medico_necessario"}
    if not kit_medico and int(teste_medicina) < 10:
        return {"resultado": "falha", "estado": "inconsciente", "cd": 10}
    estado.estavel = True
    estado.salvaguardas_sucesso = 3
    return {"resultado": "sucesso", "estado": "estavel"}


def adicionar_exaustao(estado: EstadoVital, niveis: int = 1) -> dict[str, Any]:
    estado.exaustao = min(6, estado.exaustao + max(0, int(niveis)))
    if estado.exaustao >= 6:
        estado.morto = True
    return {
        "exaustao": estado.exaustao,
        "morto": estado.morto,
        "modificador_d20": -2 * estado.exaustao,
        "deslocamento_reduzido_m": 1.5 * estado.exaustao,
    }


def descanso_curto(
    estado: EstadoVital, rolagens_dados_vida: Iterable[int], modificador_constituicao: int = 0
) -> dict[str, Any]:
    """Gasta Dados de Vida durante um Descanso Curto."""
    if estado.pv_atuais <= 0 or estado.morto:
        raise ValueError("É preciso ter pelo menos 1 PV para um Descanso Curto")
    rolagens = [int(dado) for dado in rolagens_dados_vida]
    if estado.dados_vida_maximos > 0 and len(rolagens) > int(estado.dados_vida_disponiveis or 0):
        raise ValueError("Dados de Vida insuficientes")
    recuperado = 0
    for dado in rolagens:
        recuperado += max(1, dado + int(modificador_constituicao))
    if estado.dados_vida_maximos > 0:
        estado.dados_vida_disponiveis = int(estado.dados_vida_disponiveis or 0) - len(rolagens)
    resultado = curar(estado, recuperado)
    resultado.update(
        {
            "dados_de_vida_gastos": len(rolagens),
            "descanso": "curto",
            "dados_vida_disponiveis": estado.dados_vida_disponiveis,
        }
    )
    return resultado


def descanso_longo(estado: EstadoVital) -> dict[str, Any]:
    """Concede os benefícios básicos de um Descanso Longo completo."""
    if estado.pv_atuais <= 0 or estado.morto:
        raise ValueError("É preciso ter pelo menos 1 PV para um Descanso Longo")
    estado.pv_atuais = estado.pv_maximos
    estado.dados_vida_disponiveis = estado.dados_vida_maximos
    estado.exaustao = max(0, estado.exaustao - 1)
    estado.inconsciente = False
    estado.estavel = False
    estado.salvaguardas_sucesso = 0
    estado.salvaguardas_falha = 0
    return {
        "descanso": "longo",
        "pv_atuais": estado.pv_atuais,
        "pv_temporarios": estado.pv_temporarios,
        "exaustao": estado.exaustao,
        "dados_vida_disponiveis": estado.dados_vida_disponiveis,
    }


def resolver_descanso(fatos: Mapping[str, Any]) -> dict[str, Any]:
    """Valida duração, interrupções e intervalo antes de conceder um descanso."""
    estado = fatos["estado"]
    tipo = fatos.get("rest_type", "curto")
    duracao = float(fatos.get("duration_hours", 0))
    interrompido = bool(fatos.get("interrupted", False))
    if estado.morto:
        raise ValueError("Uma criatura morta não recebe benefícios de descanso")
    if estado.pv_atuais <= 0:
        raise ValueError("É preciso ter pelo menos 1 PV para iniciar um descanso")
    if tipo == "curto":
        if duracao < 1 or interrompido:
            return {"descanso": "curto", "resultado": "interrompido_ou_invalido"}
        resultado = descanso_curto(estado, fatos.get("hit_dice_rolls", []), fatos.get("constitution_modifier", 0))
    elif tipo == "longo":
        if interrompido:
            if duracao >= 1:
                resultado = descanso_curto(
                    estado, fatos.get("hit_dice_rolls", []), fatos.get("constitution_modifier", 0)
                )
                resultado.update(
                    {"descanso": "curto", "resultado": "beneficios_de_descanso_curto_antes_da_interrupcao"}
                )
                return resultado
            return {"descanso": "longo", "resultado": "interrompido_antes_de_uma_hora"}
        if duracao < 8:
            return {"descanso": "longo", "resultado": "duracao_insuficiente"}
        if float(fatos.get("hours_since_last_long_rest", 16)) < 16:
            return {"descanso": "longo", "resultado": "intervalo_insuficiente"}
        sono = float(fatos.get("sleep_hours", 6))
        atividade_leve = float(fatos.get("light_activity_hours", 2))
        if sono < 6 or atividade_leve > 2:
            return {"descanso": "longo", "resultado": "sono_ou_atividade_invalida"}
        resultado = descanso_longo(estado)
    else:
        raise ValueError("Tipo de descanso inválido")
    recuperaveis = fatos.get("recoverable_resources", {})
    if recuperaveis:
        resultado["recursos_recuperados"] = dict(recuperaveis)
    return resultado
