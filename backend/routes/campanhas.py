"""Rotas de campanhas e da conversa com o MJ (inclui o endpoint legado /v1/mj).

As rotas apenas traduzem HTTP ↔ serviços (``campanha_service``, ``mj_service``).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.erros import NaoEncontrado
from backend.dependencies import (
    limitar_chamadas_mj,
    obter_jogador,
    obter_mj,
    obter_repositorio,
)
from backend.persistencia import RepositorioCampanhas
from backend.schemas import (
    AtualizarCampanha,
    Campanha,
    CampanhaDetalhe,
    MensagemCampanha,
    MensagemMJ,
    NovaCampanha,
    RespostaCampanha,
    RespostaMJ,
)
from backend.services import campanha_service, mj_service
from integrations.deepseek_mj import DeepSeekMJ

router = APIRouter()


@router.get("/v1/campanhas", response_model=list[Campanha])
def listar_campanhas(
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    return repo.listar(jogador)


@router.post("/v1/campanhas", response_model=Campanha, status_code=201)
def criar_campanha(
    pedido: NovaCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return repo.criar(jogador, pedido.titulo)


@router.get("/v1/campanhas/{campanha_id}", response_model=CampanhaDetalhe)
def obter_campanha(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    campanha = campanha_service.campanha_ou_404(repo, jogador, campanha_id)
    return {**campanha, "mensagens": repo.mensagens(jogador, campanha_id) or []}


@router.patch("/v1/campanhas/{campanha_id}", response_model=Campanha)
def renomear_campanha(
    campanha_id: str,
    pedido: AtualizarCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    campanha = repo.renomear(jogador, campanha_id, pedido.titulo)
    if campanha is None:
        raise NaoEncontrado("Campanha não encontrada")
    return campanha


@router.delete("/v1/campanhas/{campanha_id}", status_code=204)
def apagar_campanha(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar(jogador, campanha_id):
        raise NaoEncontrado("Campanha não encontrada")
    return Response(status_code=204)


@router.post("/v1/campanhas/{campanha_id}/mensagens", response_model=RespostaCampanha, dependencies=[Depends(limitar_chamadas_mj)])
def enviar_mensagem_campanha(
    campanha_id: str,
    pedido: MensagemCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
    mj: DeepSeekMJ = Depends(obter_mj),
) -> dict:
    campanha_service.campanha_ou_404(repo, jogador, campanha_id)
    resposta, rolagens = mj_service.responder(mj, repo, jogador, campanha_id, pedido.mensagem, pedido.operacao_id)
    return {"campanha": repo.obter(jogador, campanha_id), "resposta": resposta, "rolagens": rolagens}


@router.post("/v1/mj/mensagem", response_model=RespostaMJ, dependencies=[Depends(limitar_chamadas_mj)])
def mensagem_mj(
    pedido: MensagemMJ,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
    mj: DeepSeekMJ = Depends(obter_mj),
) -> RespostaMJ:
    """Endpoint legado: a sessao_id vira o id da campanha persistida."""
    if repo.obter(jogador, pedido.sessao_id) is None:
        if repo.existe_em_outro_jogador(jogador, pedido.sessao_id):
            raise NaoEncontrado("Campanha não encontrada")
        repo.criar(jogador, campanha_id=pedido.sessao_id)
    resposta, rolagens = mj_service.responder(mj, repo, jogador, pedido.sessao_id, pedido.mensagem)
    return RespostaMJ(sessao_id=pedido.sessao_id, resposta=resposta, rolagens=rolagens)


@router.delete("/v1/mj/sessoes/{sessao_id}", status_code=204)
def apagar_sessao(
    sessao_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    repo.apagar(jogador, sessao_id)
    return Response(status_code=204)
