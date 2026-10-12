"""Rotas de personagens da campanha: ficha, conjuração, equipamento e condições.

As rotas apenas traduzem HTTP ↔ serviços (``personagem_service``,
``condicoes_service``, ``bloco_ficha``).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.erros import NaoEncontrado
from backend.dependencies import obter_jogador, obter_repositorio
from backend.persistencia import RepositorioCampanhas
from backend.schemas import (
    AtualizarCondicaoPersonagem,
    AtualizarEquipamentoPersonagem,
    AtualizarMagiasPersonagem,
    AtualizarPersonagem,
    AtualizarProficienciasPersonagem,
    NovoPersonagem,
)
from backend.services import campanha_service, condicoes_service, personagem_service
from backend.services.bloco_ficha import com_bloco

router = APIRouter()


@router.get("/v1/campanhas/{campanha_id}/personagens")
def listar_personagens(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    grupo = repo.listar_personagens(jogador, campanha_id)
    if grupo is None:
        raise NaoEncontrado("Campanha não encontrada")
    return [com_bloco(p) for p in grupo]


@router.post("/v1/campanhas/{campanha_id}/personagens", status_code=201)
def criar_personagem_campanha(
    campanha_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    campanha_service.campanha_ou_404(repo, jogador, campanha_id)
    return personagem_service.criar_personagem(repo, jogador, campanha_id, dados)


@router.get("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def obter_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return com_bloco(personagem_service.personagem_ou_404(repo, jogador, campanha_id, personagem_id))


@router.put("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def substituir_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.substituir_personagem(repo, jogador, campanha_id, personagem_id, dados)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def atualizar_pv_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.ajustar_pv(repo, jogador, campanha_id, personagem_id, dados.ajuste_pv)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/proficiencias")
def atualizar_proficiencias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarProficienciasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.atualizar_proficiencias(repo, jogador, campanha_id, personagem_id, dados)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/equipamento")
def atualizar_equipamento_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarEquipamentoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.atualizar_equipamento(repo, jogador, campanha_id, personagem_id, dados)


@router.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/magias")
def atualizar_magias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarMagiasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.atualizar_magias(repo, jogador, campanha_id, personagem_id, dados)


@router.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/descanso-longo")
def recuperar_espacos_descanso_longo(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return personagem_service.descanso_longo(repo, jogador, campanha_id, personagem_id)


@router.delete("/v1/campanhas/{campanha_id}/personagens/{personagem_id}", status_code=204)
def apagar_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar_personagem(jogador, campanha_id, personagem_id):
        raise NaoEncontrado("Personagem não encontrado")
    return Response(status_code=204)


@router.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/condicoes")
def atualizar_condicoes_personagem(
    campanha_id: str,
    personagem_id: str,
    pedido: AtualizarCondicaoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return condicoes_service.atualizar_condicoes(repo, jogador, campanha_id, personagem_id, pedido)
