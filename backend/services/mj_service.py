"""Casos de uso da conversa com o MJ: chamada ao provedor e troca persistida."""
from __future__ import annotations

from copy import deepcopy
import inspect
import logging

from fastapi import HTTPException

from backend import config
from backend.persistencia import ConflitoEstadoCampanha, OperacaoIncompativel, RepositorioCampanhas
from backend.services.campanha_service import resumo_grupo
from integrations.deepseek_mj import DeepSeekMJ

logger = logging.getLogger(__name__)


def diagnostico_erro_provedor(exc: Exception) -> tuple[str, int | None]:
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


def chamar_mj(mj: DeepSeekMJ, texto: str, historico: list[dict], **extras) -> str:
    """Chama o MJ passando apenas os ganchos que a implementação declara aceitar."""
    try:
        parametros = inspect.signature(mj.responder).parameters
    except (TypeError, ValueError):
        parametros = {}
    aceita_extras = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parametros.values())
    aceitos = {nome: valor for nome, valor in extras.items() if aceita_extras or nome in parametros}
    return mj.responder(texto, historico, **aceitos)


def responder(
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
    historico = repo.historico_llm(jogador, campanha_id, config.HISTORICO_MAX)
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
    contexto_personagem = resumo_grupo(repo, jogador, campanha_id)
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
        resposta = chamar_mj(
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
        detalhe, status_provedor = diagnostico_erro_provedor(exc)
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
