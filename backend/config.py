"""Configuração de processo do backend HTTP do MJ.

Concentra constantes de ambiente/identidade lidas no startup, para que rotas e
serviços não espalhem leitura de variáveis de ambiente.
"""

from __future__ import annotations

import os

JOGADOR_ANONIMO = "anonimo"
HISTORICO_MAX = int(os.getenv("MJ_HISTORICO_MAX", "12"))
PADRAO_ID = r"^[A-Za-z0-9_-]{1,128}$"
