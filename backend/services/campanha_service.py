"""Casos de uso de campanha: acesso a campanhas e contexto autoritativo do MJ."""
from __future__ import annotations

from backend.persistencia import RepositorioCampanhas
from fastapi import HTTPException

from orchestrator import resumo_autoritativo


def campanha_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> dict:
    campanha = repo.obter(jogador, campanha_id)
    if campanha is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


def resumo_grupo(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> str:
    """Lê o estado canônico do banco e o entrega ao MJ como contexto autoritativo.

    O texto vive no Orquestrador de Ações (``orchestrator.estado``), que é o
    único ponto que lê o estado para montar o contexto do MJ. Aqui só existe a
    leitura da campanha no banco.
    """
    grupo = repo.listar_personagens(jogador, campanha_id) or []
    return resumo_autoritativo(grupo)
