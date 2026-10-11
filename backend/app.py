"""Backend HTTP do MJ DeepSeek.

A chave do provedor permanece no servidor. O cliente envia apenas mensagens;
o DeepSeek conduz a conversa e usa o Rule Engine por ferramentas. Campanhas e
mensagens ficam persistidas em banco (SQLite local ou Postgres via DATABASE_URL).
"""
from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.persistencia import RepositorioCampanhas
from rule_engine import (
    BESTIARIO,
    build_default_engine,
    caminho_grade,
    resolver_ataque_tatico,
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


class TokenMapaTatico(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    kind: str = Field(pattern="^(hero|enemy|npc)$")
    character_id: str | None = Field(default=None, max_length=80)
    monster_name: str | None = Field(default=None, max_length=120)
    x: int = Field(ge=0, le=19)
    y: int = Field(ge=0, le=12)


class AtualizarMapaTatico(BaseModel):
    title: str = Field(default="Cena da aventura", max_length=120)
    terrain: str = Field(default="forest", pattern="^(forest|dungeon|cave|ruins|town|road)$")
    tokens: list[TokenMapaTatico] = Field(default_factory=list, max_length=60)


class AcaoMovimentoTatico(BaseModel):
    token_id: str = Field(min_length=1, max_length=80)
    destino_x: int = Field(ge=0, le=19)
    destino_y: int = Field(ge=0, le=12)


class AcaoAtaqueTatico(BaseModel):
    atacante_id: str = Field(min_length=1, max_length=80)
    alvo_id: str = Field(min_length=1, max_length=80)
    cobertura: str = Field(default="nenhuma", pattern="^(nenhuma|meia|tres_quartos|total)$")


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


def _resumo_grupo(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> str:
    """Fornece a ficha real ao MJ e bloqueia invenções quando não há personagem."""
    grupo = repo.listar_personagens(jogador, campanha_id) or []
    if not grupo:
        return (
            "ESTADO DA CAMPANHA — nenhum personagem está cadastrado nesta campanha. "
            "Não invente nem presuma nome, espécie, classe, nível, antecedentes, atributos, "
            "aparência ou história do personagem do jogador. Antes de narrar uma cena que "
            "dependa do personagem, pergunte qual personagem existente ele quer usar ou "
            "oriente-o a criar um. Não afirme que consultou uma ficha."
        )

    linhas = []
    for indice, p in enumerate(grupo, start=1):
        atributos = ", ".join(f"{nome.upper()} {valor}" for nome, valor in (p.get("atributos") or {}).items())
        modificadores = ", ".join(
            f"{nome.upper()} {valor:+d}" for nome, valor in (p.get("modificadores") or {}).items()
        )
        linhas.append(
            f"- FICHA AUTORITATIVA #{indice}: nome={p.get('nome', 'não registrado')}; "
            f"espécie={p.get('especie', 'não registrada')}; classe={p.get('classe', 'não registrada')}; "
            f"subclasse={p.get('subclasse') or 'nenhuma registrada'}; nível={p.get('nivel', 'não registrado')}; "
            f"antecedente={p.get('antecedente') or 'não registrado'}; "
            f"PV={p.get('pv_atual', '?')}/{p.get('pv_maximo', '?')}; "
            f"bônus de proficiência=+{p.get('bonus_proficiencia', '?')}; "
            f"atributos=[{atributos}]; modificadores=[{modificadores}]."
        )
        linhas.append(
            f"  Dados de ficha: perícias={', '.join(p.get('pericias') or []) or 'nenhuma registrada'}; "
            f"ferramenta de antecedente={p.get('ferramenta') or 'nenhuma registrada'}; "
            f"talentos={', '.join(p.get('talentos') or []) or 'nenhum registrado'}; "
            f"deslocamento={p.get('deslocamento', 'não registrado')} m; "
            f"equipamento de antecedente={p.get('equipamento_antecedente') or 'não registrado'}."
        )
        conjuracao = p.get("conjuracao") or {}
        truques = conjuracao.get("truques") or []
        preparadas = conjuracao.get("magias_preparadas") or []
        espacos = conjuracao.get("espacos_totais") or {}
        linhas.append(
            f"  Conjuração exatamente registrada: truques={', '.join(truques) or 'nenhum registrado'}; "
            f"magias preparadas/conhecidas={', '.join(preparadas) or 'nenhuma registrada'}; "
            f"espaços totais={espacos or 'nenhum registrado'}. "
            "Não invente escolhas, espaços, magias, proficiências, equipamento ou características ausentes. "
            "Valide classe, nível, disponibilidade e custo no Rule Engine antes de permitir conjurar."
        )
    return (
        "ESTADO AUTORITATIVO DOS PERSONAGENS DESTA CAMPANHA, consultado do banco. "
        "Estes dados prevalecem sobre suposições narrativas e sobre mensagens antigas. "
        "Nunca altere nem contradiga a ficha; não invente nome, raça/espécie, classe, nível, "
        "antecedente, atributos, proficiências, aparência ou história pessoal. Não pergunte de novo "
        "informações que já constam aqui. Se um dado não estiver registrado, trate-o como desconhecido "
        "e pergunte ao jogador antes de fixá-lo como fato. Toda alteração mecânica exige resolução do motor.\n"
        + "\n".join(linhas)
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
    contexto_personagem = _resumo_grupo(repo, jogador, campanha_id)
    # Contexto autoritativo sempre presente, inclusive quando a campanha ainda não tem ficha.
    historico = [{"role": "system", "content": contexto_personagem}, *historico]
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


def _estado_mapa_normalizado(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> dict:
    estado = repo.obter_mapa_tatico(jogador, campanha_id)
    if estado is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    personagens = repo.listar_personagens(jogador, campanha_id) or []
    por_id = {p["id"]: p for p in personagens}
    monstros = {m["nome"]: m for m in BESTIARIO}
    tokens = []
    vistos = set()
    for bruto in estado.get("tokens", []):
        token = dict(bruto)
        if token.get("kind") == "hero":
            p = por_id.get(token.get("character_id"))
            if not p:
                continue
            token.update({
                "name": p["nome"], "hp": p["pv_atual"], "maxHp": p["pv_maximo"],
                "ac": 10 + int((p.get("modificadores") or {}).get("destreza", 0)),
                "speed_ft": int(round(float(p.get("deslocamento", 9)) / 0.3)),
                "str_mod": int((p.get("modificadores") or {}).get("forca", 0)),
                "proficiency": int(p.get("bonus_proficiencia", 2)),
                "source": "character",
            })
        elif token.get("kind") == "enemy":
            m = monstros.get(token.get("monster_name"))
            if not m:
                continue
            token.update({
                "name": m["nome"], "hp": max(0, int(token.get("hp", m["pv"]))),
                "maxHp": int(token.get("maxHp", m["pv"])), "ac": int(m["ca"]),
                "speed_ft": 30, "str_mod": 2,
                "proficiency": max(2, 2 + max(0, int(float(m["nd"])) - 1) // 4) if "/" not in str(m["nd"]) else 2,
                "source": "bestiary",
            })
        else:
            continue
        if token["id"] in vistos:
            continue
        vistos.add(token["id"])
        tokens.append(token)
    return {"title": estado.get("title", "Cena da aventura"), "terrain": estado.get("terrain", "forest"), "tokens": tokens}


@app.get("/v1/campanhas/{campanha_id}/mapa-tatico")
def obter_mapa_tatico(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    estado = _estado_mapa_normalizado(repo, jogador, campanha_id)
    personagens = repo.listar_personagens(jogador, campanha_id) or []
    return {
        "mapa": estado,
        "personagens": [{"id": p["id"], "nome": p["nome"], "pv_atual": p["pv_atual"], "pv_maximo": p["pv_maximo"], "classe": p["classe"], "nivel": p["nivel"]} for p in personagens],
        "monstros": [{"nome": m["nome"], "ca": m["ca"], "pv": m["pv"], "nd": m["nd"], "tamanho": m["tamanho"]} for m in BESTIARIO],
    }


@app.put("/v1/campanhas/{campanha_id}/mapa-tatico")
def salvar_mapa_tatico(
    campanha_id: str,
    pedido: AtualizarMapaTatico,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    personagens = repo.listar_personagens(jogador, campanha_id) or []
    por_id = {p["id"]: p for p in personagens}
    monstros = {m["nome"]: m for m in BESTIARIO}
    estado_anterior = repo.obter_mapa_tatico(jogador, campanha_id) or {}
    tokens_anteriores = {t.get("id"): t for t in estado_anterior.get("tokens", [])}
    tokens, ids = [], set()
    for token in pedido.tokens:
        if token.id in ids:
            raise HTTPException(status_code=422, detail="IDs de tokens duplicados")
        ids.add(token.id)
        if token.kind == "hero":
            p = por_id.get(token.character_id)
            if not p:
                raise HTTPException(status_code=422, detail="Vincule o token a um personagem desta campanha")
            tokens.append({"id": token.id, "kind": "hero", "character_id": p["id"], "x": token.x, "y": token.y})
        elif token.kind == "enemy":
            m = monstros.get(token.monster_name or "")
            if not m:
                raise HTTPException(status_code=422, detail="Selecione um monstro do bestiário oficial disponível no projeto")
            anterior = tokens_anteriores.get(token.id, {})
            hp_maximo = int(m["pv"])
            hp_atual = max(0, min(hp_maximo, int(anterior.get("hp", hp_maximo)))) if anterior.get("monster_name") == m["nome"] else hp_maximo
            tokens.append({"id": token.id, "kind": "enemy", "monster_name": m["nome"], "x": token.x, "y": token.y, "hp": hp_atual, "maxHp": hp_maximo})
        else:
            raise HTTPException(status_code=422, detail="Use um personagem ou monstro do catálogo")
    estado = {"title": pedido.title, "terrain": pedido.terrain, "tokens": tokens, "bloqueados": [], "terreno_dificil": []}
    repo.salvar_mapa_tatico(jogador, campanha_id, estado)
    return {"mapa": _estado_mapa_normalizado(repo, jogador, campanha_id)}


@app.post("/v1/campanhas/{campanha_id}/mapa-tatico/mover")
def mover_token_tatico(
    campanha_id: str,
    pedido: AcaoMovimentoTatico,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    estado = _estado_mapa_normalizado(repo, jogador, campanha_id)
    tokens = estado["tokens"]
    token = next((t for t in tokens if t["id"] == pedido.token_id), None)
    if token is None:
        raise HTTPException(status_code=404, detail="Token não encontrado no encontro")
    destino = (pedido.destino_x, pedido.destino_y)
    if any(t["id"] != token["id"] and (t["x"], t["y"]) == destino for t in tokens):
        raise HTTPException(status_code=409, detail="A casa de destino já está ocupada")
    origem = (int(token["x"]), int(token["y"]))
    dx, dy = destino[0] - origem[0], destino[1] - origem[1]
    passos = max(abs(dx), abs(dy))
    caminho = [origem]
    if passos:
        for i in range(1, passos + 1):
            caminho.append((round(origem[0] + dx * i / passos), round(origem[1] + dy * i / passos)))
    velocidade = max(0, int(token.get("speed_ft", 30)))
    disponivel = max(0, velocidade // 5)
    resolucao = caminho_grade({
        "caminho": caminho, "movimento_disponivel": disponivel,
        "bloqueados": [], "terreno_dificil": [],
    })
    if resolucao.get("resultado") != "permitido":
        raise HTTPException(status_code=422, detail={
            "motivo": resolucao.get("motivo", "movimento_bloqueado"),
            "movimento_disponivel_quadrados": disponivel,
            "custo": resolucao.get("custo", 0),
        })
    if token["kind"] == "hero":
        atualizado = repo.obter_personagem(jogador, campanha_id, token["character_id"])
        if not atualizado:
            raise HTTPException(status_code=404, detail="Personagem não encontrado")
    token["x"], token["y"] = destino
    repo.salvar_mapa_tatico(jogador, campanha_id, {
        "title": estado["title"], "terrain": estado["terrain"],
        "tokens": [{k: t[k] for k in ("id", "kind", "character_id", "monster_name", "x", "y", "hp", "maxHp") if k in t} for t in tokens],
        "bloqueados": [], "terreno_dificil": [],
    })
    return {"mapa": _estado_mapa_normalizado(repo, jogador, campanha_id), "resolucao": resolucao}


@app.post("/v1/campanhas/{campanha_id}/mapa-tatico/atacar")
def atacar_token_tatico(
    campanha_id: str,
    pedido: AcaoAtaqueTatico,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    estado = _estado_mapa_normalizado(repo, jogador, campanha_id)
    tokens = estado["tokens"]
    atacante = next((t for t in tokens if t["id"] == pedido.atacante_id), None)
    alvo = next((t for t in tokens if t["id"] == pedido.alvo_id), None)
    if not atacante or not alvo:
        raise HTTPException(status_code=404, detail="Atacante ou alvo não encontrado")
    if atacante["id"] == alvo["id"]:
        raise HTTPException(status_code=422, detail="Um token não pode atacar a si mesmo")
    if atacante["kind"] != "hero":
        raise HTTPException(status_code=422, detail="Nesta versão, o ataque automático usa o personagem como atacante; ações específicas dos monstros ainda não foram integradas")
    if alvo["hp"] <= 0:
        raise HTTPException(status_code=422, detail="O alvo já está com 0 PV")
    dx, dy = abs(int(atacante["x"]) - int(alvo["x"])), abs(int(atacante["y"]) - int(alvo["y"]))
    distancia_pes = max(dx, dy) * 5
    geometria = resolver_ataque_tatico({
        "distancia": distancia_pes, "alcance": 5, "alcance_maximo": 5,
        "ataque_a_distancia": False,
        "origem": (int(atacante["x"]), int(atacante["y"])),
        "alvo": (int(alvo["x"]), int(alvo["y"])),
        "atacante": (int(atacante["x"]), int(atacante["y"])),
        "alvo_posicao": (int(alvo["x"]), int(alvo["y"])),
        "aliados": [(int(t["x"]), int(t["y"])) for t in tokens if t["kind"] == "hero" and t["id"] != atacante["id"]],
        "cobertura": pedido.cobertura,
    })
    if geometria.get("resultado") != "permitido":
        raise HTTPException(status_code=422, detail={"motivo": geometria.get("motivo", "ataque_bloqueado"), "geometria": geometria})
    rolagem = secrets.randbelow(20) + 1
    modificadores = atacante.get("str_mod", 0)
    bonus = int(atacante.get("proficiency", 2)) + int(modificadores)
    engine = build_default_engine()
    ataque = engine.evaluate({"type": "attack", "roll": rolagem, "modifier": bonus, "target_ac": int(alvo["ac"])}).outcome
    if rolagem == 1:
        ataque = {**ataque, "result": "miss", "critical": False, "reason": "natural_1"}
    dano = 0
    if ataque.get("result") == "hit":
        dano_resolvido = engine.evaluate({
            "type": "damage", "damage_dice": [], "damage_modifier": max(0, 1 + int(modificadores)),
            "critical": bool(ataque.get("critical", False)),
        }).outcome
        dano = max(0, int(dano_resolvido.get("total", 0)))
        if alvo["kind"] == "enemy":
            estado_bruto = repo.obter_mapa_tatico(jogador, campanha_id) or {}
            for bruto in estado_bruto.get("tokens", []):
                if bruto.get("id") == alvo["id"]:
                    bruto["hp"] = max(0, int(bruto.get("hp", alvo["maxHp"])) - dano)
            repo.salvar_mapa_tatico(jogador, campanha_id, estado_bruto)
        else:
            repo.ajustar_pv_personagem(jogador, campanha_id, alvo["character_id"], -dano)
    return {
        "mapa": _estado_mapa_normalizado(repo, jogador, campanha_id),
        "ataque": ataque, "dano": dano, "rolagem": rolagem, "bonus_ataque": bonus,
        "geometria": geometria,
        "nota": "Ataque desarmado básico; CA de personagem sem equipamento é uma referência provisória. Armas, magias, condições e ações próprias dos monstros ainda precisam ser conectadas.",
    }


@app.delete("/v1/mj/sessoes/{sessao_id}", status_code=204)
def apagar_sessao(
    sessao_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    repo.apagar(jogador, sessao_id)
    return Response(status_code=204)


app.mount("/", StaticFiles(directory=_frontend, html=True), name="interface")
