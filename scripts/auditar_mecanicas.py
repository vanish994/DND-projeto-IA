"""Inventário diagnóstico, sem modificar fichas nem chamar o provedor de IA.

Execute: python scripts/auditar_mecanicas.py
Os números medem entradas do catálogo, NÃO magias oficiais únicas nem cobertura
fim a fim. Uma mecânica estruturada ainda depende de integração e testes.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rule_engine.economy import ITENS_MAGICOS
from rule_engine.spells import listar_magias, mecanica_de_magia, resolver_magia


def auditar() -> dict:
    entradas = []
    for magia in listar_magias():
        resolucao = resolver_magia({"magia": magia["nome"]})
        mecanica = mecanica_de_magia(magia["nome"])
        entradas.append(
            {
                "nome": magia["nome"],
                "circulo": magia["circulo"],
                "resultado_resolvedor": resolucao["resultado"],
                "motivo": resolucao.get("motivo"),
                "tipo_mecanica": mecanica.get("tipo") if mecanica else None,
            }
        )
    truques = [m for m in entradas if m["circulo"] == 0]
    return {
        "escopo": "Catálogo e resolvedor isolado; não comprova execução tática ou persistência.",
        "resumo": {
            "entradas_catalogadas": len(entradas),
            "sem_circulo_confirmado": sum(m["circulo"] is None for m in entradas),
            "com_mecanica_estruturada": sum(m["tipo_mecanica"] is not None for m in entradas),
            "resultados_resolvedor": dict(Counter(m["resultado_resolvedor"] for m in entradas)),
            "truques_identificados": len(truques),
            "truques_com_mecanica": sum(m["tipo_mecanica"] is not None for m in truques),
        },
        "conjuradas_sem_mecanica": [
            m["nome"] for m in entradas if m["resultado_resolvedor"] == "conjurada" and m["tipo_mecanica"] is None
        ],
        "truques": truques,
        "itens_magicos_catalogados": [{"id": chave, **item} for chave, item in ITENS_MAGICOS.items()],
        "magias": entradas,
    }


if __name__ == "__main__":
    print(json.dumps(auditar(), ensure_ascii=False, indent=2))
