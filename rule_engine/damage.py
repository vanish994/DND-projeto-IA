"""Defesas de dano e normalização de tipos.

Transcrito do Livro do Jogador 2024 (Resistência, Vulnerabilidade e Imunidade)
e do SRD 5.2 para os blocos de monstro. O backend e o MJ compartilham esta
fonte única para que nenhum dos dois reimplemente a regra.
"""

from __future__ import annotations

import unicodedata

# Tipos do catálogo PT-BR e do SRD mapeados para uma chave comparável.
ALIASES_TIPO_DANO = {
    "contundente": "bludgeoning",
    "bludgeoning": "bludgeoning",
    "perfurante": "piercing",
    "piercing": "piercing",
    "cortante": "slashing",
    "slashing": "slashing",
    "acido": "acid",
    "acid": "acid",
    "frio": "cold",
    "cold": "cold",
    "fogo": "fire",
    "fire": "fire",
    "igneo": "fire",
    "forca": "force",
    "force": "force",
    "eletrico": "lightning",
    "raio": "lightning",
    "lightning": "lightning",
    "necrotico": "necrotic",
    "necrotic": "necrotic",
    "veneno": "poison",
    "venenoso": "poison",
    "poison": "poison",
    "psiquico": "psychic",
    "psychic": "psychic",
    "radiante": "radiant",
    "radiant": "radiant",
    "trovejante": "thunder",
    "thunder": "thunder",
}

# Palavras que o catálogo em PT-BR e a Herança Dracônica usam para o mesmo tipo.
# Sem elas, o "ígneo" do Draconato não casaria com o "fire" do bloco do monstro.
ALIASES_TIPO_DANO.update({"gelido": "cold", "gélido": "cold"})


def normalizar_tipo_dano(tipo: str) -> str:
    """Mapeia tipos do catálogo PT-BR e do SRD em uma chave comparável."""
    texto = unicodedata.normalize("NFKD", str(tipo or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).strip()
    return ALIASES_TIPO_DANO.get(texto, texto)


def aplicar_defesas_monstro(dano: int, tipo_dano: str, defesas: dict) -> dict:
    """Aplica imunidade, resistência e vulnerabilidade conforme o bloco oficial.

    Funciona tanto para blocos de monstro do bestiário quanto para fichas que
    declarem as mesmas chaves; o backend usa em ambos os casos.
    """
    tipo = normalizar_tipo_dano(tipo_dano)
    resistencias = {normalizar_tipo_dano(x) for x in (defesas.get("resistencias_dano") or [])}
    imunidades = {normalizar_tipo_dano(x) for x in (defesas.get("imunidades_dano") or [])}
    vulnerabilidades = {normalizar_tipo_dano(x) for x in (defesas.get("vulnerabilidades_dano") or [])}
    bruto = max(0, int(dano))
    if tipo in imunidades:
        return {"dano": 0, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "imunidade", "fator": 0}
    # Pela regra de D&D, resistência e vulnerabilidade ao mesmo dano se cancelam.
    if tipo in resistencias and tipo in vulnerabilidades:
        return {
            "dano": bruto,
            "dano_bruto": bruto,
            "tipo_dano": tipo,
            "aplicacao": "resistencia_e_vulnerabilidade_canceladas",
            "fator": 1,
        }
    if tipo in resistencias:
        return {"dano": bruto // 2, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "resistencia", "fator": 0.5}
    if tipo in vulnerabilidades:
        return {"dano": bruto * 2, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "vulnerabilidade", "fator": 2}
    return {"dano": bruto, "dano_bruto": bruto, "tipo_dano": tipo, "aplicacao": "normal", "fator": 1}
