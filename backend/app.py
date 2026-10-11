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

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
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
from rule_engine.spells import listar_magias, obter_magia, resolver_magia
from rule_engine.character import FERRAMENTAS_ARTESAO, PERICIAS_CLASSE_OPCOES, QUANTIDADE_PERICIAS_CLASSE
from rule_engine.spellcasting import listar_magias_artifice, progresso_artifice, validar_escolhas_artifice
from rule_engine.catalog import CATALOGO_ARMAS, CATALOGO_ARMADURAS
from rule_engine.ability_checks import resolver_salvaguarda

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
    pericias_classe: list[str] | None = Field(default=None, max_length=10)
    ferramenta_artesao: str | None = Field(default=None, max_length=80)


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
    arma: str | None = Field(default=None, max_length=80)


class AcaoConjurarTatico(BaseModel):
    atacante_id: str = Field(min_length=1, max_length=80)
    alvo_id: str = Field(min_length=1, max_length=80)
    magia: str = Field(min_length=1, max_length=100)
    espaco: int | None = Field(default=None, ge=0, le=9)
    cobertura: str = Field(default="nenhuma", pattern="^(nenhuma|meia|tres_quartos|total)$")

class AcaoMonstroTatico(BaseModel):
    atacante_id: str = Field(min_length=1, max_length=80)
    alvo_id: str = Field(min_length=1, max_length=80)
    acao: str | None = Field(default=None, max_length=100)
    cobertura: str = Field(default="nenhuma", pattern="^(nenhuma|meia|tres_quartos|total)$")


class AtualizarMagiasPersonagem(BaseModel):
    truques: list[str] = Field(default_factory=list, max_length=20)
    magias_preparadas: list[str] = Field(default_factory=list, max_length=50)
    espacos_totais: dict[str, int] = Field(default_factory=dict)


class AtualizarProficienciasPersonagem(BaseModel):
    pericias_classe: list[str] = Field(min_length=1, max_length=10)
    ferramenta_artesao: str | None = Field(default=None, max_length=80)


class AtualizarEquipamentoPersonagem(BaseModel):
    arma: str | None = Field(default=None, max_length=80)
    armadura: str | None = Field(default=None, max_length=80)
    escudo: bool = False


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
            **({"class_skill_proficiencies": dados.pericias_classe} if dados.pericias_classe is not None else {}),
            **({"artisan_tool_proficiency": dados.ferramenta_artesao} if dados.ferramenta_artesao is not None else {}),
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
            f"- FICHA AUTORITATIVA #{indice}: id={p.get('id', 'não registrado')}; nome={p.get('nome', 'não registrado')}; "
            f"espécie={p.get('especie', 'não registrada')}; classe={p.get('classe', 'não registrada')}; "
            f"subclasse={p.get('subclasse') or 'nenhuma registrada'}; nível={p.get('nivel', 'não registrado')}; "
            f"antecedente={p.get('antecedente') or 'não registrado'}; "
            f"PV={p.get('pv_atual', '?')}/{p.get('pv_maximo', '?')}; "
            f"bônus de proficiência=+{p.get('bonus_proficiencia', '?')}; "
            f"atributos=[{atributos}]; modificadores=[{modificadores}]."
        )
        linhas.append(
            f"  Dados de ficha: perícias={', '.join(p.get('pericias') or []) or 'nenhuma registrada'}; "
            f"perícias escolhidas de classe={', '.join(p.get('pericias_classe') or []) or 'não registradas'}; "
            f"salvaguardas proficientes={', '.join(p.get('proficiencias_salvaguarda') or []) or 'não registradas'}; "
            f"proficiências de classe={p.get('proficiencias_classe') or 'não catalogadas'}; "
            f"proficiências pendentes={p.get('proficiencias_pendentes', True)}; "
            f"ferramenta de antecedente={p.get('ferramenta') or 'nenhuma registrada'}; "
            f"talentos={', '.join(p.get('talentos') or []) or 'nenhum registrado'}; "
            f"deslocamento={p.get('deslocamento', 'não registrado')} m; "
            f"equipamento de antecedente={p.get('equipamento_antecedente') or 'não registrado'}."
        )
        conjuracao = p.get("conjuracao") or {}
        truques = conjuracao.get("truques") or []
        preparadas = conjuracao.get("magias_preparadas") or []
        espacos = conjuracao.get("espacos_totais") or {}
        restantes = conjuracao.get("espacos_restantes") or espacos
        linhas.append(
            f"  Conjuração exatamente registrada: truques={', '.join(truques) or 'nenhum registrado'}; "
            f"magias preparadas/conhecidas={', '.join(preparadas) or 'nenhuma registrada'}; "
            f"espaços totais={espacos or 'nenhum registrado'}; espaços restantes={restantes or 'nenhum registrado'}. "
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
        personagens = repo.listar_personagens(jogador, campanha_id) or []
        if isinstance(mj, DeepSeekMJ):
            def salvar_estado_personagem(personagem: dict) -> None:
                ficha = {
                    k: v for k, v in personagem.items()
                    if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}
                }
                repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], ficha)

            resposta = mj.responder(
                texto, historico, personagens=personagens,
                on_character_update=salvar_estado_personagem,
            )
        else:
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
        "pericias_classe_opcoes": {classe: sorted(opcoes) for classe, opcoes in PERICIAS_CLASSE_OPCOES.items()},
        "quantidade_pericias_classe": dict(QUANTIDADE_PERICIAS_CLASSE),
        "ferramentas_artesao": sorted(FERRAMENTAS_ARTESAO),
        "matriz_padrao": sorted(gerar_atributos_matriz_padrao().values(), reverse=True),
        "compra_pontos": {"total": 27, "custos": {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}},
    }


@app.get("/v1/catalogo/magias")
def catalogo_magias(
    classe: str | None = Query(default=None, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
) -> list[dict]:
    classe_normalizada = (classe or "").strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada in {"artifice", "artífice"}:
        return listar_magias_artifice(nivel)
    return listar_magias()


@app.get("/v1/catalogo/conjuracao")
def catalogo_conjuracao(
    classe: str = Query(min_length=1, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
    inteligencia: int = Query(default=10, ge=1, le=30),
) -> dict:
    classe_normalizada = classe.strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada not in {"artifice", "artífice"}:
        return {"resultado": "nao_implementado", "motivo": "progressao_de_conjuracao_ainda_nao_validada_para_esta_classe"}
    try:
        return progresso_artifice(nivel, inteligencia)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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


@app.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/proficiencias")
def atualizar_proficiencias_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarProficienciasPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    entrada = dict(personagem.get("entrada") or {})
    entrada["pericias_classe"] = dados.pericias_classe
    entrada["ferramenta_artesao"] = dados.ferramenta_artesao
    try:
        novo = NovoPersonagem.model_validate(entrada)
        nova_entrada, nova_ficha = _resolver_ficha(novo)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    atualizado = repo.atualizar_personagem(
        jogador, campanha_id, personagem_id, entrada=nova_entrada, ficha=nova_ficha
    )
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


@app.patch("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/equipamento")
def atualizar_equipamento_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: AtualizarEquipamentoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    if dados.arma is not None and dados.arma not in CATALOGO_ARMAS:
        raise HTTPException(status_code=422, detail="Arma não encontrada no catálogo")
    if dados.armadura is not None and dados.armadura not in CATALOGO_ARMADURAS:
        raise HTTPException(status_code=422, detail="Armadura não encontrada no catálogo")
    profs = personagem.get("proficiencias_classe") or {}
    armaduras = set(profs.get("armaduras", [])) if isinstance(profs, dict) else set()
    if dados.armadura:
        categoria = CATALOGO_ARMADURAS[dados.armadura]["categoria"]
        if categoria == "escudo":
            raise HTTPException(status_code=422, detail="Registre escudos no campo escudo, não como armadura")
        categoria_normalizada = {"media": "medias", "leve": "leves", "pesada": "pesadas"}.get(categoria, categoria)
        if categoria_normalizada not in armaduras and categoria not in armaduras:
            raise HTTPException(status_code=422, detail="A ficha não registra proficiência nesta categoria de armadura")
    if dados.escudo and "escudos" not in armaduras:
        raise HTTPException(status_code=422, detail="A ficha não registra proficiência com escudos")
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    ficha["equipamento"] = {"arma": dados.arma, "armadura": dados.armadura, "escudo": dados.escudo}
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
    if personagem.get("classe") == "artifice":
        try:
            validar_escolhas_artifice(
                int(personagem.get("nivel", 1)),
                int((personagem.get("atributos") or {}).get("inteligencia", 10)),
                truques,
                preparadas,
                dados.espacos_totais,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    espacos_totais = {str(k): int(v) for k, v in dados.espacos_totais.items()}
    conjuracao_anterior = personagem.get("conjuracao") or {}
    restantes_anteriores = conjuracao_anterior.get("espacos_restantes") or {}
    if conjuracao_anterior.get("espacos_totais") == espacos_totais and restantes_anteriores:
        espacos_restantes = {
            circulo: max(0, min(total, int(restantes_anteriores.get(circulo, total))))
            for circulo, total in espacos_totais.items() if total > 0
        }
    else:
        espacos_restantes = {circulo: total for circulo, total in espacos_totais.items() if total > 0}
    ficha["conjuracao"] = {
        "truques": truques,
        "magias_preparadas": preparadas,
        "espacos_totais": espacos_totais,
        "espacos_restantes": espacos_restantes,
    }
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


@app.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/descanso-longo")
def recuperar_espacos_descanso_longo(
    campanha_id: str,
    personagem_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    personagem = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    ficha = {
        k: v for k, v in personagem.items()
        if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}
    }
    conjuracao = dict(ficha.get("conjuracao") or {})
    totais = {str(k): int(v) for k, v in (conjuracao.get("espacos_totais") or {}).items() if int(v) > 0}
    conjuracao["espacos_restantes"] = dict(totais)
    ficha["conjuracao"] = conjuracao
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


def _calcular_ca_ficha(personagem: dict) -> int:
    mods = personagem.get("modificadores") or {}
    dex = int(mods.get("destreza", 0))
    equipamento = personagem.get("equipamento") or {}
    nome_armadura = equipamento.get("armadura")
    if nome_armadura:
        armadura = CATALOGO_ARMADURAS[nome_armadura]
        categoria = armadura["categoria"]
        if categoria == "leve":
            ca = int(armadura["ca"]) + dex
        elif categoria == "media":
            ca = int(armadura["ca"]) + min(2, dex)
        elif categoria == "pesada":
            ca = int(armadura["ca"])
        else:
            ca = 10 + dex
    else:
        ca = 10 + dex
    if equipamento.get("escudo") or (nome_armadura and CATALOGO_ARMADURAS[nome_armadura]["categoria"] == "escudo"):
        ca += 2
    return ca


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
                "ac": _calcular_ca_ficha(p),
                "speed_ft": int(round(float(p.get("deslocamento", 9)) / 0.3)),
                "str_mod": int((p.get("modificadores") or {}).get("forca", 0)),
                "dex_mod": int((p.get("modificadores") or {}).get("destreza", 0)),
                "proficiency": int(p.get("bonus_proficiencia", 2)),
                "equipment": p.get("equipamento") or {},
                "source": "character",
            })
        elif token.get("kind") == "enemy":
            m = monstros.get(token.get("monster_name"))
            if not m:
                continue
            token.update({
                "name": m["nome"], "hp": max(0, int(token.get("hp", m["pv"]))),
                "maxHp": int(token.get("maxHp", m["pv"])), "ac": int(m["ca"]),
                "speed_ft": int(m.get("deslocamento_pes", 30)),
                "str_mod": int((m.get("modificadores") or {}).get("forca", 2)),
                "dex_mod": int((m.get("modificadores") or {}).get("destreza", 0)),
                "proficiency": int(m.get("bonus_proficiencia", max(2, 2 + max(0, int(float(m["nd"])) - 1) // 4) if "/" not in str(m["nd"]) else 2)),
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
    equipamento_tatico = atacante.get("equipment") or {}
    nome_arma_tatica = pedido.arma or equipamento_tatico.get("arma")
    arma_tatica = CATALOGO_ARMAS.get(nome_arma_tatica or "")
    dx, dy = abs(int(atacante["x"]) - int(alvo["x"])), abs(int(atacante["y"]) - int(alvo["y"]))
    distancia_pes = max(dx, dy) * 5
    alcance_tatico = 5
    ataque_a_distancia = False
    if arma_tatica:
        propriedades_taticas = set(arma_tatica.get("propriedades", []))
        alcance_catalogo = int(arma_tatica.get("alcance", 0))
        ataque_a_distancia = "municao" in propriedades_taticas or ("arremesso" in propriedades_taticas and distancia_pes > 5)
        if ataque_a_distancia:
            alcance_tatico = max(5, round(alcance_catalogo * 3.28084))
        elif "extensao" in propriedades_taticas:
            alcance_tatico = 10
    geometria = resolver_ataque_tatico({
        "distancia": distancia_pes, "alcance": alcance_tatico, "alcance_maximo": alcance_tatico if ataque_a_distancia else None,
        "ataque_a_distancia": ataque_a_distancia,
        "desvantagem": bool(ataque_a_distancia and distancia_pes <= 5 and alvo["kind"] == "enemy"),
        "origem": (int(atacante["x"]), int(atacante["y"])),
        "alvo": (int(alvo["x"]), int(alvo["y"])),
        "atacante": (int(atacante["x"]), int(atacante["y"])),
        "alvo_posicao": (int(alvo["x"]), int(alvo["y"])),
        "aliados": [(int(t["x"]), int(t["y"])) for t in tokens if t["kind"] == "hero" and t["id"] != atacante["id"]],
        "cobertura": pedido.cobertura,
    })
    if geometria.get("resultado") != "permitido":
        raise HTTPException(status_code=422, detail={"motivo": geometria.get("motivo", "ataque_bloqueado"), "geometria": geometria})
    ficha_atacante = repo.obter_personagem(jogador, campanha_id, atacante["character_id"])
    if not ficha_atacante:
        raise HTTPException(status_code=404, detail="Ficha do atacante não encontrada")
    equipamento = ficha_atacante.get("equipamento") or {}
    nome_arma = pedido.arma or equipamento.get("arma")
    modificadores = int(atacante.get("str_mod", 0))
    dados_arma: list[int] = []
    if nome_arma:
        arma = CATALOGO_ARMAS.get(nome_arma)
        if not arma:
            raise HTTPException(status_code=422, detail="Arma não encontrada no catálogo")
        profs = ficha_atacante.get("proficiencias_classe") or {}
        prof_armas = set(profs.get("armas", [])) if isinstance(profs, dict) else set()
        armas_simples = {"Clava", "Clava Grande", "Adaga", "Dardo", "Machadinha", "Martelo Leve", "Maça", "Cajado", "Funda", "Azagaia", "Arco Curto", "Besta Leve"}
        categoria_arma = "simples" if nome_arma in armas_simples else "marciais"
        alias_prof = {
            "Besta de Mão": "bestas_de_mao", "Espada Longa": "espadas_longas",
            "Rapieira": "rapieiras", "Espada Curta": "espadas_curtas",
            "Adaga": "adagas", "Dardo": "dardos", "Funda": "fundas",
            "Cajado": "cajados", "Besta Leve": "bestas_leves", "Clava": "clavas",
            "Clava Grande": "clavas_grandes", "Machadinha": "machadinhas",
            "Azagaia": "azagaias", "Martelo Leve": "martelos_leves", "Maça": "macas",
            "Cimitarra": "cimitarras", "Foice": "foices", "Lança": "lancas",
        }
        proficiente = categoria_arma in prof_armas or alias_prof.get(nome_arma) in prof_armas
        if not proficiente:
            raise HTTPException(status_code=422, detail="A ficha não confirma proficiência com esta arma")
        alcance_corpo_a_corpo = 10 if "extensao" in arma.get("propriedades", []) else 5
        propriedades_arma = set(arma.get("propriedades", []))
        e_distancia = "municao" in propriedades_arma or ("arremesso" in propriedades_arma and distancia_pes > 5)
        alcance_maximo_arma = max(5, round(int(arma.get("alcance", 0)) * 3.28084)) if e_distancia else alcance_corpo_a_corpo
        if distancia_pes > alcance_maximo_arma:
            raise HTTPException(status_code=422, detail={"motivo": "fora_de_alcance", "alcance_pes": alcance_maximo_arma})
        try:
            qtd, lados = map(int, arma["dano"].lower().split("d"))
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="Dado de dano inválido no catálogo")
        dados_arma = [secrets.randbelow(lados) + 1 for _ in range(qtd)]
        if "acuidade" in arma.get("propriedades", []) and int(atacante.get("dex_mod", 0)) > modificadores:
            modificadores = int(atacante.get("dex_mod", 0))
    bonus = int(atacante.get("proficiency", 2)) + modificadores
    rolagem = secrets.randbelow(20) + 1
    rolagens_extra = []
    if geometria.get("estado_jogada") == "vantagem":
        rolagens_extra = [secrets.randbelow(20) + 1]
        rolagem = max(rolagem, *rolagens_extra)
    elif geometria.get("estado_jogada") == "desvantagem":
        rolagens_extra = [secrets.randbelow(20) + 1]
        rolagem = min(rolagem, *rolagens_extra)
    engine = build_default_engine()
    ca_efetiva = int(alvo["ac"]) + int(geometria.get("bonus_ca_por_cobertura", 0))
    ataque = engine.evaluate({"type": "attack", "roll": rolagem, "modifier": bonus, "target_ac": ca_efetiva}).outcome
    if rolagem == 1:
        ataque = {**ataque, "result": "miss", "critical": False, "reason": "natural_1"}
    dano = 0
    fortitude = None
    if ataque.get("result") == "hit":
        dados_dano = list(dados_arma)
        if ataque.get("critical") and nome_arma:
            dados_dano += list(dados_arma)
        modificador_dano = int(modificadores) if nome_arma else max(0, 1 + int(modificadores))
        dano_resolvido = engine.evaluate({
            "type": "damage", "damage_dice": dados_dano, "damage_modifier": modificador_dano,
            "critical": False,
        }).outcome
        dano = max(0, int(dano_resolvido.get("total", 0)))
        if alvo["kind"] == "enemy":
            estado_bruto = repo.obter_mapa_tatico(jogador, campanha_id) or {}
            from rule_engine.bestiary import consultar_monstro
            bloco_completo_alvo = consultar_monstro(alvo.get("monster_name") or alvo.get("name")) or {}
            fortitude = None
            hp_anterior = int(alvo["hp"])
            hp_resultante = max(0, hp_anterior - dano)
            if hp_resultante == 0 and hp_anterior > 0:
                tracos = bloco_completo_alvo.get("tracos") or []
                possui_fortitude = any(
                    isinstance(t, dict) and str(t.get("nome", "")).casefold() == "undead fortitude"
                    for t in tracos
                )
                if possui_fortitude and dano > 0 and not ataque.get("critical"):
                    tipo_dano_arma = str((CATALOGO_ARMAS.get(nome_arma or "") or {}).get("tipo_dano", "")).casefold()
                    if tipo_dano_arma != "radiant":
                        salvaguardas = bloco_completo_alvo.get("salvaguardas") or {}
                        bonus_constituicao = int(salvaguardas.get("constituicao", (bloco_completo_alvo.get("modificadores") or {}).get("constituicao", 0)))
                        rolagem_fortitude = secrets.randbelow(20) + 1
                        dc_fortitude = 5 + dano
                        sucesso_fortitude = rolagem_fortitude + bonus_constituicao >= dc_fortitude
                        if sucesso_fortitude:
                            hp_resultante = 1
                        fortitude = {
                            "traco": "Undead Fortitude",
                            "rolagem": rolagem_fortitude,
                            "bonus_salvaguarda": bonus_constituicao,
                            "cd": dc_fortitude,
                            "sucesso": sucesso_fortitude,
                            "pv_final": hp_resultante,
                        }
            for bruto in estado_bruto.get("tokens", []):
                if bruto.get("id") == alvo["id"]:
                    bruto["hp"] = hp_resultante
            repo.salvar_mapa_tatico(jogador, campanha_id, estado_bruto)
        else:
            fortitude = None
            repo.ajustar_pv_personagem(jogador, campanha_id, alvo["character_id"], -dano)
    return {
        "mapa": _estado_mapa_normalizado(repo, jogador, campanha_id),
        "ataque": ataque, "dano": dano, "rolagem": rolagem, "bonus_ataque": bonus,
        "geometria": geometria,
        "arma": nome_arma or "Ataque desarmado",
        "ca_alvo": int(alvo["ac"]),
        "rolagens": [rolagem, *rolagens_extra],
        "fortitude": fortitude,
        "alcance_pes": alcance_tatico,
        "ataque_a_distancia": ataque_a_distancia,
        "nota": "Armas corpo a corpo e à distância usam o catálogo, alcance e estado de vantagem/desvantagem do motor. Munição não é rastreada no inventário nesta versão.",
    }



def _acoes_monstro_como_lista(monstro: dict) -> list[str]:
    """Normaliza as ações do bloco SRD sem inventar ataques ausentes."""
    acoes = monstro.get("acoes", [])
    if isinstance(acoes, str):
        return [linha.strip() for linha in acoes.splitlines() if linha.strip()]
    if isinstance(acoes, dict):
        acoes = list(acoes.values())
    if isinstance(acoes, list):
        linhas = []
        for item in acoes:
            if isinstance(item, dict):
                nome = str(item.get("nome") or item.get("name") or "").strip()
                descricao = str(item.get("desc") or item.get("descricao") or item.get("description") or item.get("texto") or "").strip()
                linhas.append((nome + ". " + descricao).strip() if nome and descricao else (descricao or nome))
            else:
                linhas.append(str(item))
        return linhas
    return []


def _extrair_ataques_monstro(monstro: dict) -> list[dict]:
    """Extrai somente ataques com bônus, alcance e dano explicitamente no bloco."""
    import re
    resultado = []
    for texto in _acoes_monstro_como_lista(monstro):
        if not texto:
            continue
        nome_match = re.match(r"^([^.:\n]{2,90})[.:]", texto.strip())
        bonus_match = re.search(
            r"(?:Melee|Ranged|Melee or Ranged)(?: Weapon)? Attack(?: Roll)?:\\s*([+-]\\d+)(?:\\s+to hit)?",
            texto, re.I,
        )
        dano_match = re.search(r"Hit:\s*\d+\s*\((\d+d\d+(?:\s*[+-]\s*\d+)?)\)\s*([A-Za-z]+)?\s*damage", texto, re.I)
        alcance_match = re.search(r"reach\s+(\d+)\s*ft\.|range\s+(\d+)/(\d+)\s*ft\.|range\s+(\d+)\s*ft\.", texto, re.I)
        if not (nome_match and bonus_match and dano_match and alcance_match):
            continue
        reach = int(alcance_match.group(1)) if alcance_match.group(1) else 0
        range_ft = int(alcance_match.group(2) or alcance_match.group(4) or 0)
        max_range_ft = int(alcance_match.group(3) or range_ft)
        resultado.append({
            "nome": nome_match.group(1).strip(),
            "bonus_ataque": int(bonus_match.group(1)),
            "dano": dano_match.group(1).replace(" ", ""),
            "tipo_dano": dano_match.group(2) or "desconhecido",
            "alcance_pes": max(reach, range_ft, max_range_ft),
            "alcance_corpo_a_corpo": reach,
            "alcance_minimo_distancia": range_ft,
            "alcance_maximo_distancia": max_range_ft,
            "texto": texto,
        })
    return resultado


@app.post("/v1/campanhas/{campanha_id}/mapa-tatico/ataque-monstro")
def atacar_com_monstro_tatico(
    campanha_id: str,
    pedido: AcaoMonstroTatico,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    estado = _estado_mapa_normalizado(repo, jogador, campanha_id)
    tokens = estado["tokens"]
    atacante = next((t for t in tokens if t["id"] == pedido.atacante_id), None)
    alvo = next((t for t in tokens if t["id"] == pedido.alvo_id), None)
    if not atacante or not alvo:
        raise HTTPException(status_code=404, detail="Atacante ou alvo não encontrado")
    if atacante["kind"] != "enemy":
        raise HTTPException(status_code=422, detail="Esta rota é exclusiva para tokens de monstros")
    if alvo["kind"] != "hero":
        raise HTTPException(status_code=422, detail="Monstros só podem atacar tokens de personagens nesta rota")
    if atacante["hp"] <= 0 or alvo["hp"] <= 0:
        raise HTTPException(status_code=422, detail="Atacante e alvo precisam estar com PV acima de zero")
    from rule_engine.bestiary import consultar_monstro
    monstro = consultar_monstro(atacante.get("monster_name") or atacante["name"])
    if not monstro:
        raise HTTPException(status_code=404, detail="Bloco do monstro não encontrado no bestiário")
    ataques = _extrair_ataques_monstro(monstro)
    if not ataques:
        raise HTTPException(status_code=422, detail={
            "motivo": "ataques_do_bloco_nao_estruturados",
            "monstro": monstro.get("nome"),
            "detalhe": "O bloco não contém ataque com bônus, alcance e dano em formato reconhecido; nenhum valor foi inventado.",
        })
    if pedido.acao:
        selecionado = next((a for a in ataques if a["nome"].casefold() == pedido.acao.casefold()), None)
        if not selecionado:
            raise HTTPException(status_code=422, detail={"motivo": "acao_de_ataque_inexistente", "acoes_disponiveis": [a["nome"] for a in ataques]})
    else:
        dx, dy = abs(int(atacante["x"]) - int(alvo["x"])), abs(int(atacante["y"]) - int(alvo["y"]))
        distancia = max(dx, dy) * 5
        candidatos = [a for a in ataques if (
            (a["alcance_corpo_a_corpo"] >= distancia and a["alcance_corpo_a_corpo"] > 0)
            or (a["alcance_maximo_distancia"] >= distancia and a["alcance_maximo_distancia"] > 0)
        )]
        if not candidatos:
            raise HTTPException(status_code=422, detail={"motivo": "fora_de_alcance", "acoes_disponiveis": [a["nome"] for a in ataques]})
        selecionado = candidatos[0]
    dx, dy = abs(int(atacante["x"]) - int(alvo["x"])), abs(int(atacante["y"]) - int(alvo["y"]))
    distancia = max(dx, dy) * 5
    if selecionado["alcance_corpo_a_corpo"] > 0 and distancia > selecionado["alcance_corpo_a_corpo"]:
        raise HTTPException(status_code=422, detail={"motivo": "fora_de_alcance", "alcance_pes": selecionado["alcance_corpo_a_corpo"]})
    if selecionado["alcance_maximo_distancia"] > 0 and distancia > selecionado["alcance_maximo_distancia"]:
        raise HTTPException(status_code=422, detail={"motivo": "fora_de_alcance", "alcance_pes": selecionado["alcance_maximo_distancia"]})
    geometria = resolver_ataque_tatico({
        "distancia": distancia,
        "alcance": selecionado["alcance_corpo_a_corpo"] or selecionado["alcance_maximo_distancia"],
        "alcance_maximo": selecionado["alcance_maximo_distancia"] or None,
        "ataque_a_distancia": selecionado["alcance_maximo_distancia"] > 0,
        "desvantagem": bool(selecionado["alcance_maximo_distancia"] > 0 and (
            distancia <= 5 or distancia > selecionado["alcance_minimo_distancia"]
        )),
        "origem": (int(atacante["x"]), int(atacante["y"])),
        "alvo": (int(alvo["x"]), int(alvo["y"])),
        "atacante": (int(atacante["x"]), int(atacante["y"])),
        "alvo_posicao": (int(alvo["x"]), int(alvo["y"])),
        "aliados": [(int(t["x"]), int(t["y"])) for t in tokens if t["kind"] == "enemy" and t["id"] != atacante["id"]],
        "cobertura": pedido.cobertura,
    })
    if geometria.get("resultado") != "permitido":
        raise HTTPException(status_code=422, detail={"motivo": geometria.get("motivo", "ataque_bloqueado"), "geometria": geometria})
    rolagem = secrets.randbelow(20) + 1
    rolagens_extra = []
    if geometria.get("estado_jogada") == "desvantagem":
        rolagens_extra = [secrets.randbelow(20) + 1]
        rolagem = min(rolagem, *rolagens_extra)
    elif geometria.get("estado_jogada") == "vantagem":
        rolagens_extra = [secrets.randbelow(20) + 1]
        rolagem = max(rolagem, *rolagens_extra)
    ataque = build_default_engine().evaluate({
        "type": "attack", "roll": rolagem, "modifier": selecionado["bonus_ataque"],
        "target_ac": int(alvo["ac"]) + int(geometria.get("bonus_ca_por_cobertura", 0)),
    }).outcome
    if rolagem == 1:
        ataque = {**ataque, "result": "miss", "critical": False, "reason": "natural_1"}
    dados_expr = selecionado["dano"]
    import re
    m = re.fullmatch(r"(\d+)d(\d+)(?:([+-])(\d+))?", dados_expr)
    if not m:
        raise HTTPException(status_code=422, detail={"motivo": "expressao_de_dano_nao_suportada", "expressao": dados_expr})
    quantidade, lados = int(m.group(1)), int(m.group(2))
    modificador = int(m.group(4) or 0) * (-1 if m.group(3) == "-" else 1)
    dados_dano = [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
    if ataque.get("critical"):
        dados_dano += [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
    dano = max(0, sum(dados_dano) + modificador) if ataque.get("result") == "hit" else 0
    if dano:
        repo.ajustar_pv_personagem(jogador, campanha_id, alvo["character_id"], -dano)
    return {
        "mapa": _estado_mapa_normalizado(repo, jogador, campanha_id),
        "monstro": monstro["nome"], "acao": selecionado["nome"], "ataque": ataque,
        "rolagem": rolagem, "rolagens": [rolagem, *rolagens_extra],
        "bonus_ataque": selecionado["bonus_ataque"],
        "dados_dano": dados_dano if ataque.get("result") == "hit" else [],
        "dano": dano, "tipo_dano": selecionado["tipo_dano"], "geometria": geometria,
        "nota": "Ação extraída do bloco de estatísticas do bestiário; ações múltiplas e efeitos especiais ainda precisam de resolução própria.",
    }


@app.post("/v1/campanhas/{campanha_id}/mapa-tatico/conjurar")
def conjurar_no_mapa_tatico(
    campanha_id: str,
    pedido: AcaoConjurarTatico,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    estado = _estado_mapa_normalizado(repo, jogador, campanha_id)
    tokens = estado["tokens"]
    conjurador = next((t for t in tokens if t["id"] == pedido.atacante_id), None)
    alvo = next((t for t in tokens if t["id"] == pedido.alvo_id), None)
    if not conjurador or not alvo:
        raise HTTPException(status_code=404, detail="Conjurador ou alvo não encontrado")
    if conjurador["kind"] != "hero":
        raise HTTPException(status_code=422, detail="Somente personagens com ficha podem conjurar nesta versão")
    if alvo["hp"] <= 0:
        raise HTTPException(status_code=422, detail="O alvo está com 0 PV")
    ficha = repo.obter_personagem(jogador, campanha_id, conjurador["character_id"])
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha do conjurador não encontrada")
    if str(ficha.get("classe", "")).casefold() != "artifice":
        raise HTTPException(status_code=422, detail="A lista de magias táticas implementada nesta versão é a do Artífice; outras classes precisam de suas listas validadas")
    conjuracao = ficha.get("conjuracao") or {}
    magia = obter_magia(pedido.magia)
    if not magia:
        raise HTTPException(status_code=422, detail="Magia ausente do catálogo do motor")
    nome = magia["nome"]
    circulo = int(magia.get("circulo") or 0)
    catalogo_artifice = {str(m.get("nome", "")).casefold() for m in listar_magias_artifice(int(ficha.get("nivel", 1)))}
    if nome.casefold() not in catalogo_artifice:
        raise HTTPException(status_code=422, detail="Esta magia não pertence à lista disponível do Artífice neste nível")
    truques = {str(n).casefold() for n in conjuracao.get("truques", [])}
    preparadas = {str(n).casefold() for n in conjuracao.get("magias_preparadas", [])}
    if circulo == 0 and nome.casefold() not in truques:
        raise HTTPException(status_code=422, detail="O truque não está registrado na ficha")
    if circulo > 0 and nome.casefold() not in preparadas:
        raise HTTPException(status_code=422, detail="A magia não está preparada/registrada na ficha")
    espaco_usado = int(pedido.espaco if pedido.espaco is not None else circulo)
    if circulo == 0 and espaco_usado != 0:
        raise HTTPException(status_code=422, detail="Truques não usam espaços de magia")
    restantes = {str(k): int(v) for k, v in (conjuracao.get("espacos_restantes") or {}).items()}
    totais = {str(k): int(v) for k, v in (conjuracao.get("espacos_totais") or {}).items()}
    if circulo > 0:
        if espaco_usado < circulo or restantes.get(str(espaco_usado), 0) < 1:
            raise HTTPException(status_code=422, detail="Não há espaço disponível do círculo escolhido")
    resolucao_magia = resolver_magia({
        "magia": nome, "espaco": espaco_usado,
        "componentes_disponiveis": ["V", "S", "M"],
    })
    if resolucao_magia.get("resultado") != "conjurada":
        raise HTTPException(status_code=422, detail={
            "motivo": resolucao_magia.get("motivo", "magia_sem_resolucao_tatica"),
            "resultado_motor": resolucao_magia,
        })
    mecanica = resolucao_magia.get("mecanica") or {}
    chave_magia = nome.casefold()
    dx = abs(int(conjurador["x"]) - int(alvo["x"]))
    dy = abs(int(conjurador["y"]) - int(alvo["y"]))
    distancia_pes = max(dx, dy) * 5
    engine = build_default_engine()
    resultado_ataque = None
    dano = 0
    cura = 0
    rolagem = None
    bonus_ataque = None
    if mecanica.get("tipo") == "ataque_magico":
        alcance_pes = 120 if chave_magia == "raio de fogo" else round(float(mecanica.get("alcance_m", 0)) * 3.28084)
        geometria = resolver_ataque_tatico({
            "distancia": distancia_pes, "alcance": alcance_pes, "alcance_maximo": alcance_pes,
            "ataque_a_distancia": True,
            "desvantagem": bool(distancia_pes <= 5 and alvo["kind"] == "enemy"),
            "origem": (int(conjurador["x"]), int(conjurador["y"])),
            "alvo": (int(alvo["x"]), int(alvo["y"])),
            "atacante": (int(conjurador["x"]), int(conjurador["y"])),
            "alvo_posicao": (int(alvo["x"]), int(alvo["y"])),
            "aliados": [(int(t["x"]), int(t["y"])) for t in tokens if t["kind"] == "hero" and t["id"] != conjurador["id"]],
            "cobertura": pedido.cobertura,
        })
        if geometria.get("resultado") != "permitido":
            raise HTTPException(status_code=422, detail={"motivo": geometria.get("motivo", "magia_bloqueada"), "geometria": geometria})
        mods = ficha.get("modificadores") or {}
        bonus_ataque = int(ficha.get("bonus_proficiencia", 2)) + int(mods.get("inteligencia", 0))
        rolagem = secrets.randbelow(20) + 1
        rolagens_extra = []
        if geometria.get("estado_jogada") == "vantagem":
            rolagens_extra = [secrets.randbelow(20) + 1]
            rolagem = max(rolagem, *rolagens_extra)
        elif geometria.get("estado_jogada") == "desvantagem":
            rolagens_extra = [secrets.randbelow(20) + 1]
            rolagem = min(rolagem, *rolagens_extra)
        ca_alvo = int(alvo["ac"]) + int(geometria.get("bonus_ca_por_cobertura", 0))
        resultado_ataque = engine.evaluate({"type": "attack", "roll": rolagem, "modifier": bonus_ataque, "target_ac": ca_alvo}).outcome
        if rolagem == 1:
            resultado_ataque = {**resultado_ataque, "result": "miss", "critical": False, "reason": "natural_1"}
        if resultado_ataque.get("result") == "hit":
            nivel = int(ficha.get("nivel", 1))
            quantidade, lados = map(int, str(mecanica.get("dados_dano_base", "1d10")).lower().split("d"))
            if nivel >= 17:
                quantidade = 4
            elif nivel >= 11:
                quantidade = 3
            elif nivel >= 5:
                quantidade = 2
            dados = [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
            if resultado_ataque.get("critical"):
                dados += [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
            dano_resolvido = engine.evaluate({"type": "damage", "damage_dice": dados, "damage_modifier": 0, "critical": False}).outcome
            dano = max(0, int(dano_resolvido.get("total", 0)))
    elif mecanica.get("tipo") == "cura" and chave_magia == "curar ferimentos":
        if distancia_pes > 5:
            raise HTTPException(status_code=422, detail={"motivo": "fora_de_alcance", "alcance_pes": 5})
        dados_cura = str(mecanica.get("dados_cura") or "2d8")
        quantidade, lados = map(int, dados_cura.lower().split("d"))
        dados = [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
        mod = int((ficha.get("modificadores") or {}).get("inteligencia", 0))
        cura = max(0, sum(dados) + mod)
    elif mecanica.get("tipo") == "dano_em_area":
        # A área é centrada no alvo escolhido; resolvemos apenas quando todos
        # os tokens atingidos têm salvaguardas deriváveis de fichas completas.
        area = mecanica.get("area") or {}
        forma = str(area.get("forma", "")).lower()
        if forma == "cubo":
            lado_casas = max(1, round(float(area.get("lado_m", 0)) * 3.28084 / 5))
            vx = (int(alvo["x"]) > int(conjurador["x"])) - (int(alvo["x"]) < int(conjurador["x"]))
            vy = (int(alvo["y"]) > int(conjurador["y"])) - (int(alvo["y"]) < int(conjurador["y"]))
            if vx == 0 and vy == 0:
                raise HTTPException(status_code=422, detail="Para esta área, selecione um alvo em uma direção diferente do conjurador")
            # Cubo de 15 pés que parte do conjurador e se estende na direção do alvo.
            if vx and vy:
                perp_x, perp_y = -vy, vx
                offsets = range(-(lado_casas // 2), lado_casas - lado_casas // 2)
                area_cells = {
                    (int(conjurador["x"]) + vx * depth + perp_x * offset,
                     int(conjurador["y"]) + vy * depth + perp_y * offset)
                    for depth in range(1, lado_casas + 1)
                    for offset in offsets
                }
            elif vx:
                area_cells = {
                    (int(conjurador["x"]) + vx * depth, int(conjurador["y"]) + offset)
                    for depth in range(1, lado_casas + 1)
                    for offset in range(-(lado_casas // 2), lado_casas - lado_casas // 2)
                }
            else:
                area_cells = {
                    (int(conjurador["x"]) + offset, int(conjurador["y"]) + vy * depth)
                    for depth in range(1, lado_casas + 1)
                    for offset in range(-(lado_casas // 2), lado_casas - lado_casas // 2)
                }
            alvos_area = [t for t in tokens if t["hp"] > 0 and (int(t["x"]), int(t["y"])) in area_cells]
        elif forma == "esfera":
            raio_pes = round(float(area.get("raio_m", 0)) * 3.28084)
            if raio_pes <= 0:
                raise HTTPException(status_code=422, detail="A magia não possui dimensão de área válida")
            alvos_area = [
                t for t in tokens
                if t["hp"] > 0 and max(abs(int(t["x"]) - int(alvo["x"])), abs(int(t["y"]) - int(alvo["y"]))) * 5 <= raio_pes
            ]
        else:
            raise HTTPException(status_code=422, detail="Este formato de área exige direção/posicionamento explícito ainda não disponível no mapa")
        if not alvos_area:
            raise HTTPException(status_code=422, detail="Nenhum alvo dentro da área")
        if not alvos_area:
            raise HTTPException(status_code=422, detail="Nenhum alvo dentro da área")
        fichas_alvos = {}
        for token_area in alvos_area:
            if token_area["kind"] == "enemy":
                from rule_engine.bestiary import consultar_monstro
                ficha_monstro = consultar_monstro(token_area.get("monster_name") or token_area["name"])
                if not ficha_monstro or not ficha_monstro.get("salvaguardas") or not ficha_monstro.get("modificadores"):
                    raise HTTPException(status_code=422, detail={
                        "motivo": "salvaguarda_monstro_indisponivel",
                        "alvo": token_area["name"],
                        "detalhe": "O bloco não contém modificadores e salvaguardas estruturados. A área foi rejeitada sem gastar espaço.",
                    })
                fichas_alvos[token_area["id"]] = {
                    "modificadores": ficha_monstro["modificadores"],
                    "salvaguardas": ficha_monstro["salvaguardas"],
                    "proficiencias_salvaguarda": [
                        atributo for atributo, bonus in ficha_monstro["salvaguardas"].items()
                        if int(bonus) != int(ficha_monstro["modificadores"].get(atributo, 0))
                    ],
                    "bonus_proficiencia": int(ficha_monstro.get("bonus_proficiencia", 2)),
                }
            else:
                ficha_alvo = repo.obter_personagem(jogador, campanha_id, token_area["character_id"])
                if not ficha_alvo:
                    raise HTTPException(status_code=404, detail="Ficha de alvo da área não encontrada")
                fichas_alvos[token_area["id"]] = ficha_alvo
        expressao = str(mecanica.get("dados_dano") or mecanica.get("dados_dano_base") or "2d8")
        quantidade, lados = map(int, expressao.lower().split("d"))
        dc = 8 + int(ficha.get("bonus_proficiencia", 2)) + int((ficha.get("modificadores") or {}).get("inteligencia", 0))
        resultados_area = []
        for token_area in alvos_area:
            ficha_alvo = fichas_alvos[token_area["id"]]
            atributo = str(mecanica.get("salvaguarda", "destreza")).lower()
            mods_alvo = ficha_alvo.get("modificadores") or {}
            bonus_atributo = int(mods_alvo.get(atributo, 0))
            profs_salva = ficha_alvo.get("proficiencias_salvaguarda") if "proficiencias_salvaguarda" in ficha_alvo else ficha_alvo.get("salvaguardas", [])
            profs_norm = {str(p).casefold() for p in (profs_salva or [])} if not isinstance(profs_salva, dict) else set(profs_salva.keys())
            proficiente = atributo in profs_norm
            bonus_salva = int(ficha_alvo.get("salvaguardas", {}).get(atributo, bonus_atributo)) if isinstance(ficha_alvo.get("salvaguardas"), dict) else bonus_atributo
            rolagem_salva = secrets.randbelow(20) + 1
            salvaguarda = resolver_salvaguarda({
                "atributo": atributo, "roll": rolagem_salva, "modifier": bonus_atributo,
                "dc": dc, "proficiente": proficiente, "bonus_proficiencia": int(ficha_alvo.get("bonus_proficiencia", 2)),
            })
            if isinstance(ficha_alvo.get("salvaguardas"), dict):
                salvaguarda["bonus_oficial_bloco"] = bonus_salva
                salvaguarda["total"] = int(salvaguarda.get("dado", rolagem_salva)) + bonus_salva
                salvaguarda["sucesso"] = salvaguarda["total"] >= dc and int(salvaguarda.get("dado", rolagem_salva)) != 1 or int(salvaguarda.get("dado", rolagem_salva)) == 20
                salvaguarda["resultado"] = "sucesso" if salvaguarda["sucesso"] else "falha"
            if salvaguarda.get("resultado") == "bloqueado":
                raise HTTPException(status_code=422, detail={"motivo": "salvaguarda_nao_resolvida", "resultado": salvaguarda})
            dados_area = [secrets.randbelow(lados) + 1 for _ in range(quantidade)]
            dano_base = sum(dados_area)
            dano_alvo = (dano_base // 2) if salvaguarda.get("sucesso") and mecanica.get("sucesso_metade") else (0 if salvaguarda.get("sucesso") else dano_base)
            if token_area["kind"] == "hero" and dano_alvo:
                repo.ajustar_pv_personagem(jogador, campanha_id, token_area["character_id"], -dano_alvo)
            elif token_area["kind"] == "enemy" and dano_alvo:
                estado_bruto_area = repo.obter_mapa_tatico(jogador, campanha_id) or {}
                for bruto_area in estado_bruto_area.get("tokens", []):
                    if bruto_area.get("id") == token_area["id"]:
                        bruto_area["hp"] = max(0, int(bruto_area.get("hp", token_area["maxHp"])) - dano_alvo)
                repo.salvar_mapa_tatico(jogador, campanha_id, estado_bruto_area)
            resultados_area.append({"alvo_id": token_area["id"], "nome": token_area["name"], "salvaguarda": salvaguarda, "dados_dano": dados_area, "dano": dano_alvo})
        dano = sum(x["dano"] for x in resultados_area)
    else:
        raise HTTPException(status_code=422, detail="Esta magia ainda não tem efeito implementado no combate tático")
    if resultado_ataque and resultado_ataque.get("result") == "hit" and dano:
        if alvo["kind"] == "enemy":
            estado_bruto = repo.obter_mapa_tatico(jogador, campanha_id) or {}
            for bruto in estado_bruto.get("tokens", []):
                if bruto.get("id") == alvo["id"]:
                    bruto["hp"] = max(0, int(bruto.get("hp", alvo["maxHp"])) - dano)
            repo.salvar_mapa_tatico(jogador, campanha_id, estado_bruto)
        else:
            repo.ajustar_pv_personagem(jogador, campanha_id, alvo["character_id"], -dano)
    if cura:
        if alvo["kind"] == "enemy":
            estado_bruto = repo.obter_mapa_tatico(jogador, campanha_id) or {}
            for bruto in estado_bruto.get("tokens", []):
                if bruto.get("id") == alvo["id"]:
                    bruto["hp"] = min(int(bruto.get("maxHp", alvo["maxHp"])), int(bruto.get("hp", 0)) + cura)
            repo.salvar_mapa_tatico(jogador, campanha_id, estado_bruto)
        else:
            repo.ajustar_pv_personagem(jogador, campanha_id, alvo["character_id"], cura)
    if circulo > 0:
        restantes[str(espaco_usado)] = restantes.get(str(espaco_usado), 0) - 1
        dados_ficha = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados_ficha["conjuracao"] = {**conjuracao, "espacos_restantes": restantes, "espacos_totais": totais}
        repo.atualizar_dados_ficha(jogador, campanha_id, conjurador["character_id"], dados_ficha)
    return {
        "mapa": _estado_mapa_normalizado(repo, jogador, campanha_id),
        "magia": nome, "resolucao_motor": resolucao_magia,
        "ataque": resultado_ataque, "rolagem": rolagem, "bonus_ataque": bonus_ataque,
        "dano": dano, "cura": cura, "resultados_area": resultados_area if mecanica.get("tipo") == "dano_em_area" else [],
        "espaco_usado": espaco_usado if circulo > 0 else None,
        "espacos_restantes": restantes, "nota": "Magias sem efeito tático implementado são rejeitadas sem gastar espaço. Área, salvaguardas e condições exigem integração própria.",
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
