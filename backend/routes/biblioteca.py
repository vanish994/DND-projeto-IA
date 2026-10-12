"""Rotas da biblioteca permanente de fichas de personagem."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from backend.dependencies import obter_jogador, obter_repositorio
from backend.erros import ErroDeValidacao, NaoEncontrado
from backend.persistencia import RepositorioCampanhas
from backend.schemas import NovoPersonagem
from backend.services import personagem_service
from backend.services.bloco_ficha import com_bloco

router = APIRouter()


@router.get("/v1/personagens")
def listar_fichas_salvas(
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    return [com_bloco(p) for p in repo.listar_fichas_salvas(jogador)]


@router.post("/v1/personagens", status_code=201)
def salvar_ficha(
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem_service.exigir_escolhas_de_criacao(dados)
    entrada, ficha = personagem_service.resolver_ficha(dados)
    escolhas = dados.magias_iniciais
    if escolhas:
        truques = list(dict.fromkeys(escolhas.truques))
        preparadas = list(dict.fromkeys(escolhas.magias_preparadas))
        if len(truques) != len(escolhas.truques) or len(preparadas) != len(escolhas.magias_preparadas):
            raise ErroDeValidacao("Não repita magias na ficha")
        personagem_service.validar_conjuracao(ficha, truques, preparadas, escolhas.espacos_totais)
        espacos = {str(c): int(total) for c, total in escolhas.espacos_totais.items()}
        ficha["conjuracao"] = {
            "truques": truques,
            "magias_preparadas": preparadas,
            "espacos_totais": espacos,
            "espacos_restantes": {c: total for c, total in espacos.items() if total > 0},
        }
    salvo = repo.criar_ficha_salva(jogador, entrada, ficha)
    return com_bloco(salvo)


@router.delete("/v1/personagens/{ficha_id}", status_code=204)
def apagar_ficha(
    ficha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar_ficha_salva(jogador, ficha_id):
        raise NaoEncontrado("Ficha não encontrada")
    return Response(status_code=204)


@router.post("/v1/campanhas/{campanha_id}/personagens/salvas/{ficha_id}/vincular", status_code=201)
def vincular_ficha_salva(
    campanha_id: str,
    ficha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = repo.vincular_ficha_salva(jogador, campanha_id, ficha_id)
    if personagem is None:
        raise NaoEncontrado("Campanha ou ficha não encontrada")
    return com_bloco(personagem)
