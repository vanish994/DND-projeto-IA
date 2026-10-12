"""Equipamentos, economia e itens mágicos do Livro do Jogador 2024."""

from __future__ import annotations

from typing import Any

from .catalog import CATALOGO_ARMADURAS, CATALOGO_ARMAS, CATALOGO_EQUIPAMENTOS

MOEDAS_POR_PO = {"pc": 0.01, "pp": 0.1, "pe": 0.5, "po": 1.0, "pl": 10.0}
RARIDADES = {"comum": 0, "incomum": 1, "raro": 2, "muito_raro": 3, "lendario": 4, "artefato": 5}

ITENS_MAGICOS = {
    "pocao_de_cura": {
        "nome": "Poção de Cura",
        "raridade": "comum",
        "sintonizacao": False,
        "consumivel": True,
        "efeito": "cura_2d4_mais_2",
    },
    "pocao_de_cura_maior": {
        "nome": "Poção de Cura Maior",
        "raridade": "incomum",
        "sintonizacao": False,
        "consumivel": True,
        "efeito": "cura_4d4_mais_4",
    },
    "varinha_de_misseis": {
        "nome": "Varinha de Mísseis Mágicos",
        "raridade": "incomum",
        "sintonizacao": False,
        "cargas": 7,
        "recarga": "1d6+1_ao_amanhecer",
        "efeito": "misseis_magicos",
    },
    "anel_de_protecao": {
        "nome": "Anel de Proteção",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "mais_1_ca_e_salvaguardas",
    },
    "manto_de_protecao": {
        "nome": "Manto de Proteção",
        "raridade": "incomum",
        "sintonizacao": True,
        "efeito": "mais_1_ca_e_salvaguardas",
    },
    "botas_de_velocidade": {
        "nome": "Botas de Velocidade",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "dobro_deslocamento",
    },
    "amuleto_de_saude": {
        "nome": "Amuleto de Saúde",
        "raridade": "raro",
        "sintonizacao": True,
        "efeito": "constituicao_19",
    },
    "bolsa_de_componentes": {
        "nome": "Bolsa de Componentes",
        "raridade": "comum",
        "sintonizacao": False,
        "efeito": "componentes_materiais",
    },
}


def converter_para_po(moedas: dict[str, int | float]) -> float:
    return sum(float(quantidade) * MOEDAS_POR_PO.get(str(tipo).lower(), 0) for tipo, quantidade in moedas.items())


def converter_de_po(valor: float) -> dict[str, int]:
    total_pc = round(float(valor) * 100)
    resultado = {
        "pl": total_pc // 1000,
        "po": (total_pc % 1000) // 100,
        "pe": (total_pc % 100) // 50,
        "pp": (total_pc % 50) // 10,
        "pc": total_pc % 10,
    }
    return {tipo: quantidade for tipo, quantidade in resultado.items() if quantidade}


def consultar_item(nome: str, categoria: str | None = None) -> dict[str, Any] | None:
    chave = str(nome).lower()
    if chave in ITENS_MAGICOS:
        return dict(ITENS_MAGICOS[chave], categoria="item_magico")
    catalogos = {
        "arma": CATALOGO_ARMAS,
        "armas": CATALOGO_ARMAS,
        "armadura": CATALOGO_ARMADURAS,
        "armaduras": CATALOGO_ARMADURAS,
        "equipamento": CATALOGO_EQUIPAMENTOS,
        "equipamentos": CATALOGO_EQUIPAMENTOS,
    }
    for tipo, catalogo in catalogos.items():
        if categoria and categoria.lower() not in {tipo, tipo + "s"}:
            continue
        for item, dados in catalogo.items():
            if item.lower() == chave:
                retorno = dict(dados)
                retorno.update({"nome": item, "categoria": tipo})
                if "custo_po" not in retorno:
                    retorno["custo_po"] = retorno.get("custo", 0)
                return retorno
    return None


def comprar_item(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"], fatos.get("categoria"))
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_desconhecido"}
    quantidade = max(1, int(fatos.get("quantidade", 1)))
    preco = float(fatos.get("preco_po", item.get("custo_po", 0))) * quantidade
    saldo = converter_para_po(fatos.get("moedas", {}))
    if saldo < preco:
        return {"resultado": "bloqueado", "motivo": "saldo_insuficiente", "preco_po": preco, "saldo_po": saldo}
    return {
        "resultado": "comprado",
        "item": item["nome"],
        "quantidade": quantidade,
        "preco_po": preco,
        "troco": converter_de_po(saldo - preco),
    }


def vender_item(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"], fatos.get("categoria"))
    if not item:
        return {"resultado": "bloqueado", "motivo": "item_desconhecido"}
    quantidade = max(1, int(fatos.get("quantidade", 1)))
    preco = float(fatos.get("preco_po", item.get("custo_po", 0))) * quantidade
    percentual = float(fatos.get("percentual_venda", 50)) / 100
    valor = preco * percentual
    return {
        "resultado": "vendido",
        "item": item["nome"],
        "quantidade": quantidade,
        "recebe_po": valor,
        "moedas": converter_de_po(valor),
    }


def resolver_inventario(fatos: dict) -> dict[str, Any]:
    forca = int(fatos.get("forca", 10))
    peso = float(fatos.get("peso_atual", 0)) + float(fatos.get("peso_adicionado", 0))
    capacidade = max(0, forca) * 7.5
    itens = list(fatos.get("itens", []))
    if fatos.get("adicionar"):
        itens.append({"nome": fatos["adicionar"], "quantidade": int(fatos.get("quantidade", 1))})
    return {
        "resultado": "sobrecarregado" if peso > capacidade else "normal",
        "peso": peso,
        "capacidade": capacidade,
        "itens": itens,
    }


def resolver_sintonizacao(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"])
    if not item or item.get("categoria") != "item_magico":
        return {"resultado": "bloqueado", "motivo": "item_magico_desconhecido"}
    sintonizados = list(fatos.get("sintonizados", []))
    nome = fatos["item"].lower()
    if not item.get("sintonizacao"):
        return {"resultado": "nao_requerida", "item": item["nome"]}
    if fatos.get("acao", "sintonizar") == "encerrar":
        if nome not in {str(x).lower() for x in sintonizados}:
            return {"resultado": "bloqueado", "motivo": "item_nao_sintonizado"}
        return {
            "resultado": "encerrada",
            "item": item["nome"],
            "sintonizados": [x for x in sintonizados if str(x).lower() != nome],
        }
    if nome in {str(x).lower() for x in sintonizados}:
        return {"resultado": "bloqueado", "motivo": "item_ja_sintonizado"}
    if len(sintonizados) >= 3:
        return {"resultado": "bloqueado", "motivo": "limite_de_tres_itens"}
    sintonizados.append(nome)
    return {
        "resultado": "sintonizado",
        "item": item["nome"],
        "sintonizados": sintonizados,
        "limite": 3,
        "requer_descanso_curto": True,
    }


def usar_item_magico(fatos: dict) -> dict[str, Any]:
    item = consultar_item(fatos["item"])
    if not item or item.get("categoria") != "item_magico":
        return {"resultado": "bloqueado", "motivo": "item_magico_desconhecido"}
    if item.get("sintonizacao") and fatos["item"].lower() not in {
        str(x).lower() for x in fatos.get("sintonizados", [])
    }:
        return {"resultado": "bloqueado", "motivo": "requer_sintonizacao"}
    cargas = fatos.get("cargas")
    if cargas is not None and int(cargas) <= 0:
        return {"resultado": "bloqueado", "motivo": "sem_cargas"}
    retorno = {"resultado": "usado", "item": item["nome"], "efeito": item.get("efeito")}
    if cargas is not None:
        retorno["cargas_restantes"] = int(cargas) - 1
    return retorno
