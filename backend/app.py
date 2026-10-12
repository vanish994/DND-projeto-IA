"""Backend HTTP do MJ DeepSeek.

A chave do provedor permanece no servidor. O cliente envia apenas mensagens;
o DeepSeek conduz a conversa e usa o Rule Engine por ferramentas. Campanhas e
mensagens ficam persistidas em banco (SQLite local ou Postgres via DATABASE_URL).
"""
from __future__ import annotations

from copy import deepcopy
import inspect
import logging
import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.limite_taxa import limitador_padrao
from backend.persistencia import RepositorioCampanhas, ConflitoEstadoCampanha, OperacaoIncompativel
from rule_engine import (
    build_default_engine,
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
from rule_engine.spells import listar_magias, obter_magia, suporte_magia
from rule_engine.character import FERRAMENTAS_ARTESAO, PERICIAS_CLASSE_OPCOES, QUANTIDADE_PERICIAS_CLASSE, CATEGORIAS_FERRAMENTA_ANTECEDENTE, escolha_ferramenta_do_antecedente
from rule_engine.spellcasters import CASTING_ABILITY, resolver_progressao_conjuracao
from rule_engine.species import ESCOLHAS_ESPECIE, HERANCA_DRACONICA, escolha_de_especie
from rule_engine.spellcasting import listar_magias_artifice, progresso_artifice, validar_escolhas_artifice
from rule_engine.catalog import CATALOGO_ARMAS, CATALOGO_ARMADURAS, INSTRUMENTOS_MUSICAIS, KITS_DE_JOGOS
from rule_engine.ability_checks import PERICIAS
from rule_engine.conditions import EstadoCondicoes, normalizar_condicao, resolver_efeitos_condicao

logger = logging.getLogger(__name__)

app = FastAPI(
    title="D&D Projeto IA — MJ",
    version="1.1.0",
    description="MJ DeepSeek com Rule Engine determinístico para mecânicas oficiais.",
)

_frontend = Path(__file__).resolve().parents[1] / "frontend"

JOGADOR_ANONIMO = "anonimo"
HISTORICO_MAX = int(os.getenv("MJ_HISTORICO_MAX", "12"))
PADRAO_ID = r"^[A-Za-z0-9_-]{1,128}$"

_mj: DeepSeekMJ | None = None
_repositorio: RepositorioCampanhas | None = None


class MensagemMJ(BaseModel):
    sessao_id: str = Field(min_length=1, max_length=64, pattern=PADRAO_ID)
    mensagem: str = Field(min_length=1, max_length=20000)


class RespostaMJ(BaseModel):
    sessao_id: str
    resposta: str
    rolagens: list[Rolagem] = Field(default_factory=list)
    narrativa_fora_do_motor: bool = True


class NovaCampanha(BaseModel):
    titulo: str | None = Field(default=None, max_length=120)


class AtualizarCampanha(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)


class MensagemCampanha(BaseModel):
    mensagem: str = Field(min_length=1, max_length=20000)
    # Opcional para preservar compatibilidade com clientes antigos.
    operacao_id: str | None = Field(default=None, min_length=1, max_length=64, pattern=PADRAO_ID)


class Campanha(BaseModel):
    id: str
    titulo: str
    criada_em: str
    atualizada_em: str
    ultima_mensagem: str | None = None
    total_mensagens: int = 0


class Rolagem(BaseModel):
    """Rolagem gerada pelo Rule Engine, pronta para a interface animar o dado."""

    tipo: str
    dado: str = "d20"
    lados: int = 20
    valor: int | None = None
    rolagens: list[int] = Field(default_factory=list)
    modificador: int = 0
    total: int | None = None
    expressao: str | None = None
    dificuldade: int | None = None
    dificuldade_tipo: str | None = None
    resultado: str = "rolado"
    sucesso: bool | None = None
    critico: bool = False
    natural_1: bool = False
    vantagem: bool = False
    desvantagem: bool = False
    motivo: str | None = None
    rotulo: str | None = None
    personagem: str | None = None
    alvo: str | None = None
    seed: str | None = None
    dano: dict | None = None
    origem: str = "rule_engine"


class Mensagem(BaseModel):
    id: int
    papel: str
    conteudo: str
    criada_em: str
    rolagens: list[Rolagem] = Field(default_factory=list)


class CampanhaDetalhe(Campanha):
    mensagens: list[Mensagem]


class RespostaCampanha(BaseModel):
    campanha: Campanha
    resposta: str
    rolagens: list[Rolagem] = Field(default_factory=list)
    narrativa_fora_do_motor: bool = True


class AtualizarMagiasPersonagem(BaseModel):
    truques: list[str] = Field(default_factory=list, max_length=20)
    magias_preparadas: list[str] = Field(default_factory=list, max_length=50)
    espacos_totais: dict[str, int] = Field(default_factory=dict)



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
    heranca_draconica: str | None = Field(default=None, max_length=40)
    ferramenta_antecedente: str | None = Field(default=None, max_length=80)
    equipamento_antecedente: str | None = Field(default=None, pattern="^[AaBb]$")
    magias_iniciais: AtualizarMagiasPersonagem | None = None


class AtualizarPersonagem(BaseModel):
    ajuste_pv: int = Field(ge=-100, le=100)


class AtualizarProficienciasPersonagem(BaseModel):
    pericias_classe: list[str] = Field(min_length=1, max_length=10)
    ferramenta_artesao: str | None = Field(default=None, max_length=80)
    heranca_draconica: str | None = Field(default=None, max_length=40)
    ferramenta_antecedente: str | None = Field(default=None, max_length=80)
    equipamento_antecedente: str | None = Field(default=None, pattern="^[AaBb]$")


class AtualizarEquipamentoPersonagem(BaseModel):
    arma: str | None = Field(default=None, max_length=80)
    armadura: str | None = Field(default=None, max_length=80)
    escudo: bool = False


class SalvaguardaCondicaoFimTurno(BaseModel):
    cd: int = Field(ge=1, le=50)
    atributo: str = Field(pattern="^(forca|destreza|constituicao|inteligencia|sabedoria|carisma)$")


class AtualizarCondicaoPersonagem(BaseModel):
    operacao: str = Field(pattern="^(apply|remove|tick|query)$")
    condicao: str | None = Field(default=None, max_length=40)
    duracao: int | str | None = None
    unidades: int = Field(default=1, ge=1, le=100)
    salvaguarda_fim_turno: SalvaguardaCondicaoFimTurno | None = None

class SalvaguardaFimTurno(BaseModel):
    condicao: str = Field(min_length=1, max_length=40)
    modificador: int = Field(ge=-30, le=30)
    cd: int = Field(ge=1, le=50)


class AcaoAvancarTurno(BaseModel):
    token_id: str | None = Field(default=None, max_length=80)
    salvaguardas: list[SalvaguardaFimTurno] = Field(default_factory=list, max_length=15)


def _exigir_escolhas_de_criacao(dados: NovoPersonagem) -> None:
    """A criação só termina quando a ficha não depende de escolhas pendentes."""
    escolha = escolha_de_especie(dados.especie)
    if escolha and not dados.heranca_draconica:
        raise HTTPException(status_code=422, detail=f"Escolha a {escolha['rotulo']} do {dados.especie}.")
    ferramenta = escolha_ferramenta_do_antecedente(dados.antecedente)
    if ferramenta and not dados.ferramenta_antecedente:
        raise HTTPException(status_code=422, detail=f"Escolha o tipo de {ferramenta['rotulo']} do antecedente {dados.antecedente}.")
    if dados.antecedente in ANTECEDENTES and not dados.equipamento_antecedente:
        raise HTTPException(status_code=422, detail="Escolha o equipamento de antecedente A ou B.")


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
            **({"heranca_draconica": dados.heranca_draconica} if dados.heranca_draconica is not None else {}),
            **({"ferramenta_antecedente": dados.ferramenta_antecedente} if dados.ferramenta_antecedente is not None else {}),
            **({"equipamento_antecedente": dados.equipamento_antecedente} if dados.equipamento_antecedente is not None else {}),
        })
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc).strip("'\"")) from exc
    if personagem.antecedente not in ANTECEDENTES:
        raise HTTPException(status_code=422, detail="Antecedente inválido")
    return dados.model_dump(), ficha_personagem(personagem)


def _texto_equipamento_antecedente(personagem: dict) -> str:
    """Mostra o pacote escolhido; sem escolha, deixa claro que está pendente."""
    equipamento = personagem.get("equipamento_antecedente") or {}
    if not isinstance(equipamento, dict) or not equipamento.get("A"):
        return "não registrado"
    escolha = str(equipamento.get("escolha") or "").strip().upper()
    pacote_a = equipamento.get("A")
    pacote_b = equipamento.get("B") or "50 PO"
    if escolha in ("A", "B"):
        itens = equipamento.get(escolha) or pacote_b
        return f"pacote {escolha} ({itens})"
    return f"pendente - escolher entre pacote A ({pacote_a}) ou pacote B ({pacote_b})"


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
            f"equipamento de antecedente={_texto_equipamento_antecedente(p)}."
        )
        heranca = p.get("heranca_draconica")
        if heranca:
            sopro = heranca.get("sopro") or {}
            linhas.append(
                f"  Herança Dracônica: linhagem={heranca.get('linhagem')}; "
                f"tipo de dano={heranca.get('tipo_dano')}; resistência={heranca.get('resistencia')}; "
                f"Arma de Sopro={sopro.get('dado')} de dano {sopro.get('tipo_dano')} "
                f"(formas: {', '.join(sopro.get('formas') or [])}; salvaguarda de "
                f"{sopro.get('salvaguarda')} CD {sopro.get('cd')}; {sopro.get('usos')} usos, "
                f"recarga em {sopro.get('recarga')})."
            )
        pendencias = [str(item) for item in (p.get("escolhas_pendentes") or [])]
        if p.get("proficiencias_pendentes"):
            pendencias = ["Perícias ou ferramenta de classe", *pendencias]
        if pendencias:
            linhas.append(
                "  PENDÊNCIAS DE CRIAÇÃO (pergunte ao jogador, nunca invente): "
                + "; ".join(dict.fromkeys(pendencias))
                + "."
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


# Limite de taxa das rotas que chamam o MJ (cada chamada custa uma requisição ao provedor).
_limitador_mj = limitador_padrao()


def limitar_chamadas_mj(jogador: str = Depends(obter_jogador)) -> None:
    _limitador_mj.verificar(jogador)


def _campanha_ou_404(repo: RepositorioCampanhas, jogador: str, campanha_id: str) -> dict:
    campanha = repo.obter(jogador, campanha_id)
    if campanha is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


def _diagnostico_erro_provedor(exc: Exception) -> tuple[str, int | None]:
    """Converte falhas comuns do provedor em instruções seguras para o jogador."""
    tipo = type(exc).__name__
    status = getattr(exc, "status_code", None)

    if tipo in {"AuthenticationError", "InvalidAPIKeyError"} or status == 401:
        return ("O provedor recusou a chave de API. Confira TOKENHARBOR_API_KEY no Render.", status or 401)
    if tipo == "PermissionDeniedError" or status == 403:
        return ("O provedor negou acesso ao modelo. Confira a conta, permissões e modelo configurado.", status or 403)
    if status == 402:
        return ("O saldo de créditos do TokenHarbor parece insuficiente ou expirou. Abra o painel Billing para conferir a carteira e, se necessário, adicione créditos; depois tente novamente.", 402)
    if tipo == "RateLimitError" or status == 429:
        return ("O provedor atingiu um limite ou não tem cota disponível. Aguarde e confira os créditos/limites da conta.", status or 429)
    if tipo == "NotFoundError" or status == 404:
        return ("O modelo ou endpoint configurado não foi encontrado. Confira DEEPSEEK_MODEL e TOKENHARBOR_BASE_URL no Render.", status or 404)
    if tipo in {"APITimeoutError", "TimeoutError"}:
        return ("O provedor demorou demais para responder. Tente novamente em instantes.", status)
    if tipo in {"APIConnectionError", "ConnectionError"}:
        return ("Não foi possível conectar ao provedor. Verifique o serviço e tente novamente.", status)
    if status is not None:
        return (f"O provedor respondeu com erro HTTP {status}. Consulte os logs do serviço no Render.", status)
    return ("Falha temporária ao consultar o provedor. Consulte os logs do serviço no Render e tente novamente.", None)


def _chamar_mj(mj: DeepSeekMJ, texto: str, historico: list[dict], **extras) -> str:
    """Chama o MJ passando apenas os ganchos que a implementação declara aceitar."""
    try:
        parametros = inspect.signature(mj.responder).parameters
    except (TypeError, ValueError):
        parametros = {}
    aceita_extras = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parametros.values())
    aceitos = {nome: valor for nome, valor in extras.items() if aceita_extras or nome in parametros}
    return mj.responder(texto, historico, **aceitos)


def _responder(
    mj: DeepSeekMJ, repo: RepositorioCampanhas, jogador: str, campanha_id: str, texto: str,
    operacao_id: str | None = None,
) -> tuple[str, list[dict]]:
    """Repete o resultado confirmado sem executar ferramentas novamente."""
    def resultado_confirmado():
        if not operacao_id:
            return None
        try:
            return repo.obter_operacao(jogador, campanha_id, operacao_id, texto)
        except OperacaoIncompativel as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    anterior = resultado_confirmado()
    if anterior is not None:
        return anterior["resposta"], anterior["rolagens"]
    historico = repo.historico_llm(jogador, campanha_id, HISTORICO_MAX)
    # Evita que respostas narrativas excepcionalmente longas façam a requisição
    # crescer sem limite e provoquem HTTP 413 no provedor.
    historico = [
        {
            **mensagem,
            "content": (
                mensagem.get("content", "")[-3000:]
                if isinstance(mensagem.get("content", ""), str)
                else mensagem.get("content", "")
            ),
        }
        for mensagem in historico
    ]
    contexto_personagem = _resumo_grupo(repo, jogador, campanha_id)
    # Contexto autoritativo sempre presente, inclusive quando a campanha ainda não tem ficha.
    historico = [{"role": "system", "content": contexto_personagem}, *historico]
    rolagens: list[dict] = []
    atualizacoes_pendentes: dict[str, dict] = {}

    def registrar_rolagem(rolagem: dict) -> None:
        rolagens.append(rolagem)

    def salvar_estado_personagem(personagem: dict) -> None:
        ficha = {
            k: v for k, v in personagem.items()
            if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}
        }
        # As ferramentas podem continuar trabalhando com a ficha em memória,
        # mas uma falha posterior do provedor não pode deixar gastos no banco.
        atualizacoes_pendentes[personagem["id"]] = deepcopy(ficha)

    try:
        personagens = repo.listar_personagens(jogador, campanha_id) or []
        fichas_esperadas = {p["id"]: deepcopy(p) for p in personagens}
        # Só envia o que o MJ em uso aceita: adaptadores antigos e dublês de teste
        # continuam funcionando com a assinatura reduzida.
        resposta = _chamar_mj(
            mj, texto, historico,
            personagens=personagens, on_character_update=salvar_estado_personagem,
            on_roll=registrar_rolagem,
        )
    except Exception as exc:
        # Outro pedido com a mesma chave pode ter confirmado enquanto a IA
        # deste pedido falhava. Nesse caso, devolvemos o resultado vencedor.
        anterior = resultado_confirmado()
        if anterior is not None:
            return anterior["resposta"], anterior["rolagens"]
        detalhe, status_provedor = _diagnostico_erro_provedor(exc)
        logger.exception(
            "Falha na chamada do provedor do MJ: tipo=%s status_provedor=%s",
            type(exc).__name__, status_provedor,
        )
        raise HTTPException(status_code=502, detail=detalhe) from exc
    try:
        confirmado = repo.registrar_troca(
            jogador, campanha_id, texto, resposta, rolagens,
            atualizacoes_ficha=atualizacoes_pendentes, fichas_esperadas=fichas_esperadas,
            operacao_id=operacao_id,
        )
    except OperacaoIncompativel as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ConflitoEstadoCampanha as exc:
        raise HTTPException(status_code=409, detail="A ficha mudou enquanto o MJ respondia. Esta resposta não foi aplicada; tente novamente com o estado atualizado.") from exc
    return confirmado["resposta"], confirmado["rolagens"]


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


@app.post("/v1/campanhas/{campanha_id}/mensagens", response_model=RespostaCampanha, dependencies=[Depends(limitar_chamadas_mj)])
def enviar_mensagem_campanha(
    campanha_id: str,
    pedido: MensagemCampanha,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
    mj: DeepSeekMJ = Depends(obter_mj),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    resposta, rolagens = _responder(mj, repo, jogador, campanha_id, pedido.mensagem, pedido.operacao_id)
    return {"campanha": repo.obter(jogador, campanha_id), "resposta": resposta, "rolagens": rolagens}


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
        "escolhas_especie": {
            especie: {"rotulo": escolha["rotulo"], "nota": escolha["nota"], "opcoes": [
                {"chave": chave, "nome": dados["nome"], "dano": dados["dano"]}
                for chave, dados in escolha["opcoes"].items()
            ]}
            for especie, escolha in ESCOLHAS_ESPECIE.items()
        },
        "heranca_draconica": HERANCA_DRACONICA,
        "ferramentas_antecedente": {
            antecedente: escolha_ferramenta_do_antecedente(antecedente)
            for antecedente in ANTECEDENTES
            if escolha_ferramenta_do_antecedente(antecedente)
        },
        "instrumentos_musicais": INSTRUMENTOS_MUSICAIS,
        "kits_de_jogos": KITS_DE_JOGOS,
        "atributo_conjuracao": {"artifice": "inteligencia", **CASTING_ABILITY},
        "matriz_padrao": sorted(gerar_atributos_matriz_padrao().values(), reverse=True),
        "compra_pontos": {"total": 27, "custos": {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}},
    }


@app.get("/v1/catalogo/equipamento")
def catalogo_equipamento() -> dict:
    """Catálogo oficial de armas e armaduras para a ficha não manter listas próprias."""
    return {
        "armas": {nome: dict(dados) for nome, dados in CATALOGO_ARMAS.items()},
        "armaduras": {nome: dict(dados) for nome, dados in CATALOGO_ARMADURAS.items()},
        "pericias_atributo": dict(PERICIAS),
        "arma_simples": sorted(ARMAS_SIMPLES),
        "alias_proficiencia_arma": dict(ALIAS_PROFICIENCIA_ARMA),
        "fonte": "Livro do Jogador 2024 — catálogos do Rule Engine",
    }


@app.get("/v1/catalogo/magias")
def catalogo_magias(
    classe: str | None = Query(default=None, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
) -> list[dict]:
    classe_normalizada = (classe or "").strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada in {"artifice", "artífice"}:
        magias = listar_magias_artifice(nivel)
    else:
        magias = listar_magias()
    return [{**m, "suporte": suporte_magia(m["nome"])} for m in magias]


@app.get("/v1/catalogo/conjuracao")
def catalogo_conjuracao(
    classe: str = Query(min_length=1, max_length=40),
    nivel: int = Query(default=1, ge=1, le=20),
    inteligencia: int = Query(default=10, ge=1, le=30),
    sabedoria: int = Query(default=10, ge=1, le=30),
    carisma: int = Query(default=10, ge=1, le=30),
) -> dict:
    """Progressão de conjuração calculada pelo motor; nada é estimado no cliente."""
    classe_normalizada = classe.strip().lower().replace("í", "i").replace(" ", "")
    if classe_normalizada in {"artifice", "artífice"}:
        try:
            progresso = progresso_artifice(nivel, inteligencia)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {**progresso, "validacao_escolhas": True}
    progresso = resolver_progressao_conjuracao({
        "classe": classe_normalizada,
        "nivel": nivel,
        "inteligencia": inteligencia,
        "sabedoria": sabedoria,
        "carisma": carisma,
    })
    if progresso.get("resultado") != "resolvido":
        return {"resultado": "nao_implementado", "motivo": progresso.get("motivo") or "progressao_de_conjuracao_ainda_nao_validada_para_esta_classe"}
    espacos = {str(indice + 1): total for indice, total in enumerate(progresso["espacos"]) if total}
    return {
        "resultado": "resolvido",
        "classe": classe_normalizada,
        "nivel": nivel,
        "atributo_conjuracao": progresso["atributo_conjuracao"],
        "truques": progresso["truques"],
        "magias_preparadas": progresso["magias_preparadas"],
        "circulo_maximo": max((int(circulo) for circulo in espacos), default=0),
        "espacos_totais": espacos,
        "validacao_escolhas": False,
    }


@app.get("/v1/campanhas/{campanha_id}/personagens")
def listar_personagens(
    campanha_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> list[dict]:
    grupo = repo.listar_personagens(jogador, campanha_id)
    if grupo is None:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return [_com_bloco(p) for p in grupo]


@app.post("/v1/campanhas/{campanha_id}/personagens", status_code=201)
def criar_personagem_campanha(
    campanha_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _campanha_ou_404(repo, jogador, campanha_id)
    _exigir_escolhas_de_criacao(dados)
    entrada, ficha = _resolver_ficha(dados)
    escolhas = None
    if dados.magias_iniciais:
        truques = list(dict.fromkeys(dados.magias_iniciais.truques))
        preparadas = list(dict.fromkeys(dados.magias_iniciais.magias_preparadas))
        if len(truques) != len(dados.magias_iniciais.truques) or len(preparadas) != len(dados.magias_iniciais.magias_preparadas):
            raise HTTPException(status_code=422, detail="Não repita magias na ficha")
        _validar_conjuracao(ficha, truques, preparadas, dados.magias_iniciais.espacos_totais)
        escolhas = (truques, preparadas, dados.magias_iniciais.espacos_totais)
    personagem = repo.criar_personagem(jogador, campanha_id, entrada, ficha)
    if escolhas:
        personagem = _aplicar_conjuracao(repo, jogador, campanha_id, personagem, *escolhas)
    return _com_bloco(personagem)


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
    return _com_bloco(_personagem_ou_404(repo, jogador, campanha_id, personagem_id))


@app.put("/v1/campanhas/{campanha_id}/personagens/{personagem_id}")
def substituir_personagem(
    campanha_id: str,
    personagem_id: str,
    dados: NovoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    _exigir_escolhas_de_criacao(dados)
    entrada, ficha = _resolver_ficha(dados)
    return _com_bloco(repo.atualizar_personagem(jogador, campanha_id, personagem_id, entrada=entrada, ficha=ficha))


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
    return _com_bloco(atualizado)


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
    for campo in ("heranca_draconica", "ferramenta_antecedente", "equipamento_antecedente"):
        valor = getattr(dados, campo)
        if valor is not None:
            entrada[campo] = valor
    try:
        novo = NovoPersonagem.model_validate(entrada)
        nova_entrada, nova_ficha = _resolver_ficha(novo)
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for chave in ("conjuracao", "equipamento"):
        if personagem.get(chave):
            nova_ficha[chave] = personagem[chave]
    atualizado = repo.atualizar_personagem(
        jogador, campanha_id, personagem_id, entrada=nova_entrada, ficha=nova_ficha
    )
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return _com_bloco(atualizado)


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
    return _com_bloco(atualizado)


def _validar_conjuracao(personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> None:
    """Nomes, círculos e progressão validada são conferidos pelo motor, nunca pelo cliente."""
    for nome_magia in truques:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") != 0:
            raise HTTPException(status_code=422, detail=f"Truque inválido: {nome_magia}")
    for nome_magia in preparadas:
        magia = obter_magia(nome_magia)
        if not magia or magia.get("circulo") is None or magia.get("circulo") == 0:
            raise HTTPException(status_code=422, detail=f"Magia preparada inválida: {nome_magia}")
    if any(not isinstance(n, int) or n < 0 or n > 20 for n in espacos_totais.values()):
        raise HTTPException(status_code=422, detail="Quantidade de espaços inválida")
    if personagem.get("classe") == "artifice":
        try:
            validar_escolhas_artifice(
                int(personagem.get("nivel", 1)),
                int((personagem.get("atributos") or {}).get("inteligencia", 10)),
                truques, preparadas, espacos_totais,
                subclasse=personagem.get("subclasse") or personagem.get("subclass"),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def _aplicar_conjuracao(repo, jogador: str, campanha_id: str, personagem: dict, truques: list[str], preparadas: list[str], espacos_totais: dict) -> dict:
    """Grava magias e espaços sem zerar os espaços já gastos se a progressão não mudou."""
    espacos = {str(circulo): int(total) for circulo, total in espacos_totais.items()}
    ficha = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    anterior = personagem.get("conjuracao") or {}
    restantes_anteriores = anterior.get("espacos_restantes") or {}
    if anterior.get("espacos_totais") == espacos and restantes_anteriores:
        restantes = {c: max(0, min(total, int(restantes_anteriores.get(c, total)))) for c, total in espacos.items() if total > 0}
    else:
        restantes = {c: total for c, total in espacos.items() if total > 0}
    ficha["conjuracao"] = {"truques": truques, "magias_preparadas": preparadas,
                           "espacos_totais": espacos, "espacos_restantes": restantes}
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], ficha)
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
    _validar_conjuracao(personagem, truques, preparadas, dados.espacos_totais)
    return _com_bloco(_aplicar_conjuracao(repo, jogador, campanha_id, personagem, truques, preparadas, dados.espacos_totais))


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
    return _com_bloco(atualizado)


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


@app.post("/v1/mj/mensagem", response_model=RespostaMJ, dependencies=[Depends(limitar_chamadas_mj)])
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
    resposta, rolagens = _responder(mj, repo, jogador, pedido.sessao_id, pedido.mensagem)
    return RespostaMJ(sessao_id=pedido.sessao_id, resposta=resposta, rolagens=rolagens)


def _validar_turno_ativo(estado: dict, token_id: str) -> None:
    if estado.get("combate_ativo") and estado.get("token_ativo") != token_id:
        raise HTTPException(status_code=409, detail={
            "motivo": "turno_de_outra_criatura",
            "token_ativo": estado.get("token_ativo"),
            "token_solicitado": token_id,
        })


def _condicoes_da_ficha(ficha: dict) -> EstadoCondicoes:
    return EstadoCondicoes(
        ativas=set(ficha.get("condicoes_ativas") or []),
        imunidades=set(ficha.get("imunidades_condicoes") or []),
        duracoes=dict(ficha.get("duracoes_condicoes") or {}),
        exaustao=int(ficha.get("exaustao_nivel", 0)),
    )


def _duracao_textual_expira(duracao: Any, momento: str) -> bool:
    if not isinstance(duracao, str):
        return False
    texto = duracao.casefold()
    if momento == "fim":
        return "até o fim do próximo turno" in texto or "until the end of its next turn" in texto
    return "até o início do próximo turno" in texto or "until the start of its next turn" in texto


def _expirar_duracoes_textuais_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, ficha: dict, momento: str) -> list[str]:
    estado = _condicoes_da_ficha(ficha)
    encerradas = []
    for condicao, duracao in list(estado.duracoes.items()):
        if _duracao_textual_expira(duracao, momento):
            estado.remover(condicao)
            encerradas.append(normalizar_condicao(condicao))
    if encerradas:
        _salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
    return encerradas


def _reduzir_duracoes_numericas_token(token: dict) -> list[str]:
    """Reduz no fim do turno as durações numéricas das condições de um monstro."""
    duracoes = token.get("condition_durations") or {}
    condicoes = token.get("conditions") or []
    encerradas = []
    for condicao, duracao in list(duracoes.items()):
        if not isinstance(duracao, int) or isinstance(duracao, bool):
            continue
        restante = duracao - 1
        chave = normalizar_condicao(condicao)
        if restante <= 0:
            token["conditions"] = [c for c in condicoes if normalizar_condicao(c) != chave]
            condicoes = token["conditions"]
            duracoes.pop(condicao, None)
            encerradas.append(chave)
        else:
            duracoes[condicao] = restante
    token["condition_durations"] = duracoes
    return encerradas


def _expirar_duracoes_textuais_token(token: dict, momento: str) -> list[str]:
    duracoes = token.get("condition_durations") or {}
    condicoes = token.get("conditions") or []
    encerradas = []
    for condicao, duracao in list(duracoes.items()):
        if _duracao_textual_expira(duracao, momento):
            chave = normalizar_condicao(condicao)
            token["conditions"] = [c for c in condicoes if normalizar_condicao(c) != chave]
            condicoes = token["conditions"]
            duracoes.pop(condicao, None)
            encerradas.append(chave)
    token["condition_durations"] = duracoes
    return encerradas


def _salvar_condicoes_ficha(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem: dict, estado: EstadoCondicoes) -> dict:
    dados = {k: v for k, v in personagem.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
    dados["condicoes_ativas"] = sorted(estado.ativas)
    dados["imunidades_condicoes"] = sorted(estado.imunidades)
    dados["duracoes_condicoes"] = dict(estado.duracoes)
    dados["exaustao_nivel"] = estado.exaustao
    atualizado = repo.atualizar_dados_ficha(jogador, campanha_id, personagem["id"], dados)
    if atualizado is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return atualizado


def _resolver_concentracao_apos_dano(repo: RepositorioCampanhas, jogador: str, campanha_id: str, personagem_id: str, dano: int) -> dict | None:
    """Aplica a salvaguarda de concentração ao dano real recebido pelo personagem."""
    ficha = repo.obter_personagem(jogador, campanha_id, personagem_id)
    if not ficha:
        return None
    magia = ficha.get("concentrando")
    if not magia:
        return {"resultado": "não_concentrando", "concentracao_mantida": False}
    estado = _condicoes_da_ficha(ficha)
    efeitos = resolver_efeitos_condicao({"action": "move", "target_conditions": list(estado.ativas)})
    if ficha.get("pv_atual", 1) <= 0 or efeitos.get("encerra_concentracao"):
        ficha_atualizada = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        ficha_atualizada["concentrando"] = None
        repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, ficha_atualizada)
        return {"resultado": "concentracao_encerrada", "concentracao_mantida": False, "motivo": "incapacitado_ou_inconsciente", "magia": magia}
    modificadores = ficha.get("modificadores") or {}
    profs = ficha.get("proficiencias_salvaguarda") or ficha.get("proficiencias_salvacao") or []
    if isinstance(profs, str):
        profs = [profs]
    bonus = int(modificadores.get("constituicao", 0))
    if "constituicao" in {str(p).casefold() for p in profs}:
        bonus += int(ficha.get("bonus_proficiencia", 2))
    rolagem = secrets.randbelow(20) + 1
    resolucao = build_default_engine().evaluate({
        "type": "concentration_check", "concentrating": True,
        "damage": int(dano), "roll": rolagem, "constitution_modifier": bonus,
    }).outcome
    resolucao["magia"] = magia
    resolucao["rolagem"] = rolagem
    resolucao["bonus_constituicao"] = bonus
    if not resolucao.get("concentracao_mantida"):
        dados = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados["concentrando"] = None
        repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, dados)
    return resolucao


@app.post("/v1/campanhas/{campanha_id}/personagens/{personagem_id}/condicoes")
def atualizar_condicoes_personagem(
    campanha_id: str,
    personagem_id: str,
    pedido: AtualizarCondicaoPersonagem,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> dict:
    ficha = _personagem_ou_404(repo, jogador, campanha_id, personagem_id)
    estado = _condicoes_da_ficha(ficha)
    fatos = {"estado": estado, "operation": pedido.operacao, "units": pedido.unidades}
    if pedido.operacao != "tick":
        if not pedido.condicao:
            raise HTTPException(status_code=422, detail="Informe a condição para aplicar, remover ou consultar")
        fatos["condition"] = pedido.condicao
    if pedido.operacao == "apply":
        fatos["duration"] = pedido.duracao
    try:
        resultado = build_default_engine().evaluate({"type": "condition_state", **fatos}).outcome
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if pedido.operacao in {"apply", "remove", "tick"}:
        ficha = _salvar_condicoes_ficha(repo, jogador, campanha_id, ficha, estado)
        metadados = dict(ficha.get("salvaguardas_fim_condicoes") or {})
        if pedido.operacao == "apply" and pedido.condicao:
            chave_condicao = normalizar_condicao(pedido.condicao)
            if pedido.salvaguarda_fim_turno:
                metadados[chave_condicao] = pedido.salvaguarda_fim_turno.model_dump()
            else:
                metadados.pop(chave_condicao, None)
        elif pedido.operacao == "remove" and pedido.condicao:
            metadados.pop(normalizar_condicao(pedido.condicao), None)
        elif pedido.operacao == "tick":
            metadados = {k: v for k, v in metadados.items() if normalizar_condicao(k) in estado.ativas}
        dados_ficha = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados_ficha["salvaguardas_fim_condicoes"] = metadados
        ficha = repo.atualizar_dados_ficha(jogador, campanha_id, personagem_id, dados_ficha) or ficha
    return {"personagem_id": personagem_id, "condicoes_ativas": sorted(estado.ativas), "duracoes": dict(estado.duracoes), "salvaguardas_fim_condicoes": ficha.get("salvaguardas_fim_condicoes", {}), "exaustao_nivel": estado.exaustao, "resolucao": resultado}


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


# Atributo de conjuração por classe, conforme declarado pelo próprio motor:
# rule_engine/spellcasters.py (mago, clérigo, druida, bardo),
# rule_engine/advanced_casters.py (bruxo, feiticeiro, guardião, paladino) e
# rule_engine/class_features.py (artífice). Classes sem conjuração ficam fora do mapa.
ATRIBUTO_CONJURACAO_CLASSE = {
    "mago": "inteligencia",
    "artifice": "inteligencia",
    "clerigo": "sabedoria",
    "druida": "sabedoria",
    "guardiao": "sabedoria",
    "bardo": "carisma",
    "bruxo": "carisma",
    "feiticeiro": "carisma",
    "paladino": "carisma",
}

# Armas simples do catálogo; as demais do CATALOGO_ARMAS são marciais.
ARMAS_SIMPLES = {
    "Clava", "Clava Grande", "Adaga", "Dardo", "Machadinha", "Martelo Leve", "Maça",
    "Cajado", "Funda", "Azagaia", "Arco Curto", "Besta Leve",
}

# Proficiências específicas concedidas por classe que não usam o nome da arma.
ALIAS_PROFICIENCIA_ARMA = {
    "Besta de Mão": "bestas_de_mao", "Espada Longa": "espadas_longas",
    "Rapieira": "rapieiras", "Espada Curta": "espadas_curtas",
    "Adaga": "adagas", "Dardo": "dardos", "Funda": "fundas",
    "Cajado": "cajados", "Besta Leve": "bestas_leves", "Clava": "clavas",
    "Clava Grande": "clavas_grandes", "Machadinha": "machadinhas",
    "Azagaia": "azagaias", "Martelo Leve": "martelos_leves", "Maça": "macas",
    "Cimitarra": "cimitarras", "Foice": "foices", "Lança": "lancas",
}

ALCANCE_CORPO_A_CORPO_PES = 5
ALCANCE_EXTENSAO_PES = 10


def _pes(metros: float) -> int:
    """Converte o alcance do catálogo (metros) para pés, como o mapa tático usa."""
    return max(ALCANCE_CORPO_A_CORPO_PES, round(float(metros) * 3.28084))


def _proficiente_com_arma(personagem: dict, nome_arma: str) -> bool:
    profs = personagem.get("proficiencias_classe") or {}
    if not isinstance(profs, dict):
        return False
    conhecidas = set(profs.get("armas", []))
    categoria = "simples" if nome_arma in ARMAS_SIMPLES else "marciais"
    return categoria in conhecidas or ALIAS_PROFICIENCIA_ARMA.get(nome_arma) in conhecidas


def _resolver_arma_ficha(personagem: dict, nome_arma: str | None) -> dict:
    """Bônus de ataque e dano a partir do catálogo oficial e dos modificadores da ficha.

    Armas de munição usam Destreza; as demais usam Força, ou Destreza quando a
    arma tem Acuidade e o modificador de Destreza é maior.
    """
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    forca = int(mods.get("forca", 0))
    destreza = int(mods.get("destreza", 0))
    if not nome_arma:
        sinal_negativo = "\u2212"
        return {
            "nome": None, "desarmado": True, "catalogo": False, "proficiente": True,
            "atributo": "forca", "modificador": forca, "ataque": proficiencia + forca,
            "dado": None, "modificador_dano": forca,
            "expressao_dano": "1 {} {}".format("+" if forca >= 0 else sinal_negativo, abs(forca)),
            "dano_medio": max(0, 1 + forca), "tipo": "contundente",
            "alcance_pes": ALCANCE_CORPO_A_CORPO_PES, "propriedades": [],
            "a_distancia": False, "arremesso": False,
        }
    arma = CATALOGO_ARMAS.get(nome_arma)
    if arma is None:
        return {"nome": nome_arma, "catalogo": False, "proficiente": False, "erro": "arma_fora_do_catalogo"}
    propriedades = list(arma.get("propriedades") or [])
    conjunto = set(propriedades)
    atributo = "destreza" if "municao" in conjunto or ("acuidade" in conjunto and destreza > forca) else "forca"
    modificador = destreza if atributo == "destreza" else forca
    a_distancia = "municao" in conjunto
    alcance_pes = _pes(arma.get("alcance", 0)) if a_distancia or "arremesso" in conjunto else (
        ALCANCE_EXTENSAO_PES if "extensao" in conjunto else ALCANCE_CORPO_A_CORPO_PES
    )
    quantidade, lados = (int(parte) for parte in str(arma["dano"]).lower().split("d"))
    dano_medio = int(quantidade * (lados + 1) / 2) + modificador
    sinal = "+" if modificador >= 0 else "−"
    return {
        "nome": nome_arma, "desarmado": False, "catalogo": True,
        "proficiente": _proficiente_com_arma(personagem, nome_arma),
        "atributo": atributo, "modificador": modificador,
        "ataque": proficiencia + modificador,
        "dado": arma["dano"], "modificador_dano": modificador,
        "expressao_dano": f"{arma['dano']} {sinal} {abs(modificador)}",
        "dano_medio": max(0, dano_medio), "tipo": arma["tipo"],
        "alcance_pes": alcance_pes, "propriedades": propriedades,
        "a_distancia": a_distancia, "arremesso": "arremesso" in conjunto,
    }


def _bloco_salvaguardas(personagem: dict) -> list[dict]:
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    proficientes = set(personagem.get("proficiencias_salvaguarda") or [])
    linhas = []
    for atributo in ("forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"):
        base = int(mods.get(atributo, 0))
        proficiente = atributo in proficientes
        linhas.append({
            "atributo": atributo, "proficiente": proficiente,
            "modificador": base, "total": base + (proficiencia if proficiente else 0),
        })
    return linhas


def _bloco_pericias(personagem: dict) -> list[dict]:
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    proficientes = set(personagem.get("pericias") or [])
    linhas = []
    for pericia, atributo in PERICIAS.items():
        base = int(mods.get(atributo, 0))
        proficiente = pericia in proficientes
        linhas.append({
            "pericia": pericia, "atributo": atributo, "proficiente": proficiente,
            "modificador": base, "total": base + (proficiencia if proficiente else 0),
        })
    linhas.sort(key=lambda linha: (-int(linha["proficiente"]), linha["pericia"]))
    return linhas


def _bloco_conjuracao(personagem: dict) -> dict | None:
    atributo = ATRIBUTO_CONJURACAO_CLASSE.get(str(personagem.get("classe") or "").lower())
    if not atributo:
        return None
    mods = personagem.get("modificadores") or {}
    proficiencia = int(personagem.get("bonus_proficiencia") or 2)
    modificador = int(mods.get(atributo, 0))
    return {
        "atributo": atributo, "modificador": modificador,
        "cd": 8 + proficiencia + modificador, "ataque": proficiencia + modificador,
    }


def _bloco_ficha(personagem: dict) -> dict:
    """Valores derivados calculados pelo servidor para exibição da ficha.

    Nada aqui é inventado pelo cliente: CA, ataque, dano, salvaguardas e perícias
    saem do catálogo oficial somados aos modificadores já validados pelo motor.
    """
    equipamento = personagem.get("equipamento") or {}
    armadura = CATALOGO_ARMADURAS.get(equipamento.get("armadura") or "")
    return {
        "fonte": "rule_engine",
        "ca": _calcular_ca_ficha(personagem),
        "iniciativa": int((personagem.get("modificadores") or {}).get("destreza", 0)),
        "bonus_proficiencia": int(personagem.get("bonus_proficiencia") or 2),
        "arma": _resolver_arma_ficha(personagem, equipamento.get("arma")),
        "armadura": {
            "nome": equipamento.get("armadura"), "escudo": bool(equipamento.get("escudo")),
            "categoria": armadura["categoria"] if armadura else None,
            "ca_base": armadura["ca"] if armadura else None,
        },
        "conjuracao": _bloco_conjuracao(personagem),
        "salvaguardas": _bloco_salvaguardas(personagem),
        "pericias": _bloco_pericias(personagem),
    }


def _com_bloco(personagem: dict) -> dict:
    """Anexa o bloco derivado à ficha devolvida pelas rotas de personagem."""
    if not isinstance(personagem, dict):
        return personagem
    return {**personagem, "bloco": _bloco_ficha(personagem)}


@app.delete("/v1/mj/sessoes/{sessao_id}", status_code=204)
def apagar_sessao(
    sessao_id: str,
    jogador: str = Depends(obter_jogador),
    repo: RepositorioCampanhas = Depends(obter_repositorio),
) -> Response:
    repo.apagar(jogador, sessao_id)
    return Response(status_code=204)


app.mount("/", StaticFiles(directory=_frontend, html=True), name="interface")
