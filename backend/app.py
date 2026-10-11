"""Backend HTTP do MJ DeepSeek.

A chave do provedor permanece no servidor. O cliente envia apenas mensagens;
o DeepSeek conduz a conversa e usa o Rule Engine por ferramentas. Campanhas e
mensagens ficam persistidas em banco (SQLite local ou Postgres via DATABASE_URL).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.persistencia import RepositorioCampanhas
from rule_engine import (
    ANTECEDENTES,
    CLASSES,
    ESPECIES,
    criar_personagem,
    ficha_personagem,
    gerar_atributos_compra_pontos,
    gerar_atributos_matriz_padrao,
)
from rule_engine.feats import DARK_GIFT_FEATS, ORIGIN_FEATS
from integrations.deepseek_mj import DeepSeekMJ
from rule_engine.spells import listar_magias, obter_magia
from rule_engine.spells import listar_magias, obter_magia

logger = logging.getLogger(__name__)

app = FastAPI(
    title="D&D Projeto IA — MJ",
    version="1.1.0",
    description="MJ DeepSeek com Rule Engine determinístico para mecânicas oficiais.",
)

_frontend = Path(__file__).resolve().parents[1] / "frontend"

JOGADOR_ANONIMO = "anonimo"
HISTORICO_MAX = int(os.getenv("MJ_HISTORICO_MAX", "40"))
PADRAO_ID = r"^[A-Za-z0-9_-]{1,128}$"

_mj: DeepSeekMJ | None = None
_repositorio: RepositorioCampanhas | None = None


class MensagemMJ(BaseModel):
    sessao_id: str = Field(min_length=1, max_length=64, pattern=PADRAO_ID)
    mensagem: str = Field(min_length=1, max_length=20000)


class RespostaMJ(BaseModel):
    sessao_id: str
    resposta: str
    narrativa_fora_do_motor: bool = True


class NovaCampanha(BaseModel):
    titulo: str | None = Field(default=None, max_length=120)


class AtualizarCampanha(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)


class MensagemCampanha(BaseModel):
    mensagem: str = Field(min_length=1, max_length=20000)


class Campanha(BaseModel):
    id: str
    titulo: str
    criada_em: str
    atualizada_em: str
    ultima_mensagem: str | None = None
    total_mensagens: int = 0


class Mensagem(BaseModel):
    id: int
    papel: str
    conteudo: str
    criada_em: str


class CampanhaDetalhe(Campanha):
    mensagens: list[Mensagem]


class RespostaCampanha(BaseModel):
    campanha: Campanha
    resposta: str
    narrativa_fora_do_motor: bool = True


class NovoPersonagem(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    especie: str
    classe: str
    nivel: int = Field(default=1, ge=1, le=20)
    subclasse: str | None = None
    metodo_atributos: str = Field(default="matriz_padrao", pattern="^(matriz_padrao|compra_pontos)$")
    atributos: dict[str, int]
    antecedente: str
    aumentos_antecedente: dict[str, int]
    talento_antecedente: str | None = None


class AtualizarPersonagem(BaseModel):
    ajuste_pv: int = Field(ge=-100, le=100)


class AtualizarMagiasPersonagem(BaseModel):
    truques: list[str] = Field(default_factory=list, max_length=20)
    magias_preparadas: list[str] = Field(default_factory=list, max_length=50)
    espacos_totais: dict[str, int] = Field(default_factory=dict)


class AtualizarMagiasPersonagem(BaseModel):
    truques: list[str] = Field(default_factory=list, max_length=20)
    magias_preparadas: list[str] = Field(default_factory=list, max_length=50)
    espacos_totais: dict[str, int] = Field(default_factory=dict)


def _resolver_ficha(dados: NovoPersonagem) -> tuple[dict, dict]:
    """Toda ficha passa pelo Rule Engine; nada é calculado no cliente."""
    try:
        if dados.metodo_atributos == "compra_pontos":
            base = gerar_atributos_compra_pontos(dados.atributos)
        else:
            base = dict(dados.atributos)
            if sorted(base.values()) != sorted(gerar_atributos_matriz_padrao().values()):
                raise ValueError("A matriz padrão usa exatamente 15, 14, 13, 12, 10 e 8")
        personagem = criar_personagem({
            "name": dados.nome,
            "species": dados.especie,
            "class": dados.classe,
            "level": dados.nivel,
            "subclass": dados.subclasse,
            "ability_scores": base,
            "background": dados.antecedente,
            "background_increases": dados.aumentos_antecedente,
            "background_feat": dados.talento_antecedente,
        })
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc).strip("'\"")) from exc
    if personagem.antecedente not in ANTECEDENTES:
        raise HTTPException(status_code=422, detail="Antecedente inválido")
    return dados.model_dump(), ficha_personagem(personagem)


def _resumo_grupo(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> str | None:
    grupo = repo.listar_personagens(jogador, campanha_id) or []
    if not grupo:
        return None
    linhas = []
    for indice, p in enumerate(grupo, start=1):
        atributos = ", ".join(f"{nome[:3].upper()} {valor}" for nome, valor in p["atributos"].items())
        linhas.append(
            f"- Personagem {indice}: {p['especie']} {p['classe']} nível {p['nivel']}, antecedente {p['antecedente']}, "
            f"PV {p['pv_atual']}/{p['pv_maximo']}, BP +{p['bonus_proficiencia']}, {atributos}"
        )
    return (
        "Fichas do grupo registradas pelo Rule Engine (estado autoritativo; não altere valores "
        "sem resolução mecânica):\n" + "\n".join(linhas)
    )


def obter_mj() -> DeepSeekMJ:
    global _mj
    if _mj is None:
        try:
            _mj = DeepSeekMJ()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _mj


def obter_repositorio() -> RepositorioCampanhas:
    global _repositorio
    if _repositorio is None:
        _repositorio = RepositorioCampanhas()
    return _repositorio


def obter_jogador(
    x_jogador_id: str | None = Header(default=None, pattern=PADRAO_ID),
) -> str:
    return x_jogador_id or JOGADOR_ANONIMO


def _campanha_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> dict:
    campanha = repo.obter(jogador, campanha_id)
    if campanha is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


def _responder(mj: DeepSeekMJ, repo: RepositorioCampanhas, jogador: str, campanha_id: str, texto: str) -> str:
    historico = repo.historico_llm(jogador, campanha_id, HISTORICO_MAX)
    grupo = _resumo_grupo(repo, jogador, campanha_id)
    if grupo:
        historico = [{"role": "system", "content": grupo}, *historico]
    try:
        resposta = mj.responder(texto, historico)
    except Exception as exc:
        logger.exception("Falha na chamada do provedor do MJ: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Falha ao consultar o MJ configurado") from exc
    repo.registrar_troca(jogador, campanha_id, texto, resposta)
    return resposta


@app.get("/v1/status")
def status() -> dict[str, str]:
    return {
        "status": "online",
        "servico": "mj-deepseek",
        "motor_regras": "deterministico",
    }


@app.get("/v1/campanhas", response_model=list[Campanha])
def listar_campanhas(
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    return repo.listar(jogador)


@app.post("/v1/campanhas", response_model=Campanha, status_code=201)
def criar_campanha(
    pedido: NovaCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return repo.criar(jogador, pedido.titulo)


@app.get("/v1/campanhas/{campanha_id}", response_model=CampanhaDetalhe)
def obter_campanha(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    campanha = _campanha_ou_404(repo, jogador, campanha_id)
    return {**campanha, "mensagens": repo.mensagens(jogador, campanha_id) or []}


@app.patch("/v1/campanhas/{campanha_id}", response_model=Campanha)
def renomear_campanha(
    campanha_id: str,
    pedido: AtualizarCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    campanha = repo.renomear(jogador, campanha_id, pedido.titulo)
    if campanha is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


@app.delete("/v1/campanhas/{campanha_id}", status_code=204)
def apagar_campanha(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar(jogador, campanha_id):
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return Response(status_code=204)


@app.post("/v1/campanhas/{campanha_id}/mensagens", response_model=RespostaCampanha)
def enviar_mensagem_campanha(
    campanha_id: str,
    pedido: MensagemCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
    mj: DeepSeekMJ = Depends(obter_mj),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    resposta = _responder(mj, repo, jogador, campanha_id, pedido.mensagem)
    return {"campanha": repo.obter(jogador, campanha_id), "resposta": resposta}


@app.get("/v1/catalogo/personagens")
def catalogo_personagens() -> dict:
    return {
        "especies": ESPECIES,
        "classes": CLASSES,
        "antecedentes": ANTECEDENTES,
        "talentos_origem": sorted(ORIGIN_FEATS),
        "dadivas_sombrias": sorted(DARK_GIFT_FEATS),
        "matriz_padrao": sorted(gerar_atributos_matriz_padrao().values(), reverse=True),
        "compra_pontos": {"total": 27, "custos": {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}},
    }


@app.get("/v1/catalogo/magias")
def catalogo_magias() -> list[dict]:
    return listar_magias()


@app.get("/v1/catalogo/magias")
def catalogo_magias() -> list[dict]:
    return listar_magias()


@app.get("/v1/campanhas/{campanha_id}/personagens")
def listar_personagens(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    grupo = repo.listar_personagens(jogador, campanha_id)
    if grupo is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return grupo


@app.post("/v1/campanhas/{campanha_id}/personagens", status_code=201)
def criar_personagem_campanha(
    campanha_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    entrada, ficha = _resolver_ficha(dados)
    return repo.criar_personagem(jogador, campanha_id, entrada, ficha)


def _personagem_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str) -> dict:
    personagem = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return personagem


@app.get("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def obter_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    return _personagem_ou_404(repo, jogador, campanha_id, personagem_id)


@app.put("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def substituir_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    entrada, ficha = _resolver_ficha(dados)
    return repo.atualizar_personagem(jogador, campanha_id, personagem_id, entrada=entrada, ficha=ficha)


@app.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def atualizar_pv_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    atualizado = repo.ajustar_pv_personagem(jogador, campanha_id, personagem_id, dados.ajuste_pv)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


@app.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/magias")
def atualizar_magias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarMagiasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    truques = list(dict.fromkeys(dados.truques))
    preparadas = list(dict.fromkeys(dados.magias_preparadas))
    if len(truques) != len(dados.truques) or len(preparadas) != len(dados.magias_preparadas):
        raise HTTPException(status_code=422, detail="Não repita magias na ficha")
    for nome_magia in truques:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") != 0:
            raise HTTPException(status_code=422, detail=f"Truque inválido: {nome_magia}")
    for nome_magia in preparadas:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") is None or magia.get("circulo") == 0:
            raise HTTPException(status_code=422, detail=f"Magia preparada inválida: {nome_magia}")
    if any(not isinstance(n, int) or n < 0 or n > 20 for n in dados.espacos_totais.values()):
        raise HTTPException(status_code=422, detail="Quantidade de espaços inválida")
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    ficha["conjuracao"] = {
        "truques": truques,
        "magias_preparadas": preparadas,
        "espacos_totais": dados.espacos_totais,
    }
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


@app.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/magias")
def atualizar_magias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarMagiasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    truques = list(dict.fromkeys(dados.truques))
    preparadas = list(dict.fromkeys(dados.magias_preparadas))
    if len(truques) != len(dados.truques) or len(preparadas) != len(dados.magias_preparadas):
        raise HTTPException(status_code=422, detail="Não repita magias na ficha")
    for nome_magia in truques:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") != 0:
            raise HTTPException(status_code=422, detail=f"Truque inválido: {nome_magia}")
    for nome_magia in preparadas:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") is None or magia.get("circulo") == 0:
            raise HTTPException(status_code=422, detail=f"Magia preparada inválida: {nome_magia}")
    if any(not isinstance(n, int) or n < 0 or n > 20 for n in dados.espacos_totais.values()):
        raise HTTPException(status_code=422, detail="Quantidade de espaços inválida")
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    ficha["conjuracao"] = {"truques": truques, "magias_preparadas": preparadas, "espacos_totais": dados.espacos_totais}
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


@app.delete("/v1/campanhas/{campanha_id}/personagens/{personagem_id}", status_code=204)
def apagar_personagem(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    if not repo.apagar_personagem(jogador, campanha_id, personagem_id):
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return Response(status_code=204)


@app.post("/v1/mj/mensagem", response_model=RespostaMJ)
def mensagem_mj(
    pedido: MensagemMJ,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
    mj: DeepSeekMJ = Depends(obter_mj),
) -> RespostaMJ:
    """Endpoint legado: a sessao_id vira o id da campanha persistida."""
    if repo.obter(jogador, pedido.sessao_id) is None:
        if repo.existe_em_outro_jogador(jogador, pedido.sessao_id):
            raise HTTPException(status_code=404, detail="Campanha não encontrada")
        repo.criar(jogador, campanha_id=pedido.sessao_id)
    resposta = _responder(mj, repo, jogador, pedido.sessao_id, pedido.mensagem)
    return RespostaMJ(sessao_id=pedido.sessao_id, resposta=resposta)


@app.delete("/v1/mj/sessoes/{sessao_id}", status_code=204)
def apagar_sessao(
    sessao_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    repo.apagar(jogador, sessao_id)
    return Response(status_code=204)


app.mount("/", StaticFiles(directory=_frontend, html=True), name="interface")
