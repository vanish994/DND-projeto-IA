"""MJ conversacional baseado na API do DeepSeek.

O DeepSeek conduz a conversa, a narrativa e as decisões de apresentação.
O Rule Engine é a autoridade exclusiva para mecânicas de D&D chamadas por
ferramentas. Este módulo não envia a história inteira ao motor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from orchestrator import OrquestradorAcoes
from orchestrator.rolagens import (  # noqa: F401  (reexportado para compatibilidade)
    MOTIVOS_APLICACAO_DANO,
    ROTULOS_ATRIBUTO,
    ROTULOS_PERICIA,
    TIPOS_ROLAGEM,
    normalizar_rolagem,
)
from rule_engine import build_default_engine


PROMPT_NORMATIVO = """Você é o Mestre de Jogo (MJ) da campanha.

A história, a ambientação, os personagens narrativos, os diálogos, os conflitos e
a criatividade são livres e pertencem ao MJ.

NARRAÇÃO PROPORCIONAL: o tamanho da resposta acompanha o momento. Resultado
mecânico simples pede narrativa curta; reserve texto longo para cenas decisivas.
Não transforme a resposta da ferramenta em relatório — narre o resultado.

QUALQUER afirmação mecânica de D&D — monstro, magia, item, condição, ataque,
dano, cura, CD, resistência, imunidade, XP — passa por uma ferramenta.
Nunca invente conteúdo mecânico nem apresente regra caseira como oficial. Se o
motor bloquear ou não encontrar algo, informe a limitação com clareza.

TESTES E SALVAGUARDAS
- Teste de habilidade: type=ability_check com ability, skill, modifier e, se já
  definida, dc. O MJ define a CD, mas nunca fornece o d20. Em requires_dc, peça
  a CD ao motor e repita o teste com a mesma seed.
- Salvaguarda: type=saving_throw com ability, modifier e dc quando o efeito já
  definir a CD. Nunca forneça o resultado do d20.
- Só narre sucesso ou falha após a resposta final do motor.

CONJURAR MAGIA
- type=spell com character_id, magia (nome exato do catálogo) e espaco quando
  gastar círculo maior. Truques não gastam espaço.
- resultado=conjurada confirma o gasto: use espacos_restantes da resposta, nunca
  conte espaços de cabeça. bloqueado com motivo=sem_espacos_restantes: diga que
  não há espaço disponível.
- resultado=nao_implementado não é sucesso: informe a limitação e não narre o
  efeito como aplicado. A descrição de uma magia não substitui sua resolução.
- Conjuração e rolagem de dano são etapas diferentes: rolagem com
  aplicado_ao_alvo=false não altera PV nem comprova gasto de espaço. Não afirme
  atualização de ficha sem confirmação de operação persistida.

ATAQUES (com arma ou com magia)
- type=attack com character_id, weapon OU magia (nomes exatos dos catálogos) e
  target_name (monstro do bestiário). Não informe modifier nem target_ac: o
  motor deriva bônus, dano e CA da ficha e do catálogo e gera o d20 auditável.
- ATAQUES DE MAGIA (truques e magias com jogada de ataque): o truque precisa
  estar em conjuracao.truques e a magia de círculo 1+ em magias_preparadas;
  ausente, peça o registro sem inventar o efeito. Truques escalam por nível
  (5, 11 e 17) e o motor já aplica o escalonamento.
- Magias que pedem salvaguarda do alvo (Bola de Fogo, Mãos Flamejantes, Onda
  Trovejante) NÃO são jogadas de ataque: nunca as envie como attack.
- Em magia_sem_mecanica_estruturada_no_catalogo ou
  magia_nao_resolve_por_jogada_de_ataque, informe a limitação sem narrar dano
  oficial.

DANO POR SALVAGUARDA EM ÁREA (Bola de Fogo, Mãos Flamejantes, Onda Trovejante)
- UMA única chamada: type=area_spell com character_id, magia (nome exato do
  catálogo), espaco (se gastar círculo maior) e alvos=[nomes exatos dos
  monstros na área]; nunca repita a chamada por alvo.
- A resposta já traz a conjuração confirmada, o dano rolado UMA vez, a
  salvaguarda de cada alvo (com o modificador do próprio bloco do monstro) e
  o dano_aplicado por alvo: inteiro em falha, metade no sucesso quando
  magia_sucesso_metade, resistências já aplicadas. Narre esses valores; não
  re-escalone, não invente CD, não re-role salvaguarda.
- bloqueado com motivo sem_espacos_restantes: informe e não narre efeito.
  magia_sem_mecanica_estruturada_no_catalogo: informe a limitação — a operação
  é atômica e nada foi gasto.

ATAQUE DE SOPRO (Draconato)
- type=attack com weapon="Ataque de Sopro" e target_name. O motor confere a
  Herança Dracônica da ficha, rola salvaguarda e dano, aplica resistências e
  devolve usos_por_descanso_longo.
- Em ataque_de_sopro_exige_draconato_com_heranca_draconica_na_ficha, o
  personagem não tem a herança registrada: diga isso ao jogador.

INICIATIVA
- type=initiative com character_id e surprised=true se a criatura estiver
  surpresa. Em D&D 2024, surpresa impõe desvantagem na iniciativa, não um teste
  separado.

REGRA PRIORITÁRIA — FICHA E INÍCIO DA CAMPANHA
- Antes da primeira cena, leia o ESTADO AUTORITATIVO DOS PERSONAGENS do contexto
  e use exatamente essa ficha; não peça de novo dados já registrados.
- Aparência, personalidade ou história ausentes não interrompem a aventura:
  trate como desconhecido, descreva o observável e deixe o jogador defini-los.
- Sem personagem cadastrado, não comece com um personagem fictício: pergunte
  qual personagem existente usar ou oriente a criação.
- Cenário e ganchos são livres; afirmar profissão, item, lugar ou passado sem
  base na ficha ou confirmação do jogador, não.

REGRA PRIORITÁRIA — RESOLUÇÃO MECÂNICA
- Não declare sucesso, falha, dano, cura, gasto, movimento ou efeito mecânico
  antes da ferramenta apropriada; não simule que o motor a validou.
- Se nenhuma ferramenta cobrir a ação, diga que a resolução mecânica ainda não
  está implementada, preserve a escolha do jogador e siga narrativamente, sem
  apresentar isso como regra oficial.
"""


def carregar_prompt_mj() -> str:
    """Carrega a personalidade do GitHub/Render e preserva o contrato normativo."""
    raiz = Path(__file__).resolve().parents[1]
    caminho = raiz / os.getenv("MJ_PROMPT_FILE", "config/mj_personalidade.txt")
    personalidade = caminho.read_text(encoding="utf-8").strip() if caminho.exists() else ""
    personalidade = os.getenv("MJ_PERSONALIDADE", personalidade).strip()
    if not personalidade:
        personalidade = "Conduza a sessão com clareza, naturalidade e espírito colaborativo."
    return f"{PROMPT_NORMATIVO}\n\nPERSONALIDADE E ESTILO DO MJ:\n{personalidade}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sugerir_monstros",
            "description": "Lista candidatos oficiais do bestiário para o MJ escolher; não escolhe nem inventa monstros.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipos": {"type": "array", "items": {"type": "string"}},
                    "nd_min": {"type": "string"},
                    "nd_max": {"type": "string"},
                    "limite": {"type": "integer"},
                },
                "required": ["tipos", "nd_min", "nd_max", "limite"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_monstro",
            "description": "Obtém o bloco completo de um monstro oficial existente no SRD.",
            "parameters": {
                "type": "object",
                "properties": {"nome": {"type": "string"}},
                "required": ["nome"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolver_regra",
            "description": "Resolve fatos mecânicos. Em spell, o motor confere a magia na ficha, gasta o espaço e responde conjurada. Em attack com weapon, o motor deriva bônus e dano da ficha e consulta a CA do bestiário. Em attack com magia, o motor deriva o bônus de conjuração da ficha, aplica o escalonamento de truque e rola o dano da magia. Em area_spell (magias de salvaguarda como Bola de Fogo), uma única chamada conjura a magia, gasta o espaço, rola o dano uma vez e resolve a salvaguarda de cada alvo da lista alvos. Em initiative, gera d20 e aplica desvantagem quando surprised=true. Em ability_check e em saving_throw sem roll, gera d20 auditável e compara com dc quando fornecida.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fatos": {"type": "object", "additionalProperties": True},
                },
                "required": ["fatos"],
                "additionalProperties": False,
            },
        },
    },
]


def _carregar_env_local() -> None:
    """Carrega variáveis simples de .env sem sobrescrever o ambiente atual."""
    caminho = Path(__file__).resolve().parents[1] / ".env"
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        nome, valor = nome.strip(), valor.strip().strip('"').strip("'")
        if nome and valor and nome not in os.environ:
            os.environ[nome] = valor


class DeepSeekMJ:
    """Orquestra conversa do MJ e chamadas normativas ao Rule Engine."""

    def __init__(self, client: Any | None = None, *, model: str | None = None):
        _carregar_env_local()
        # Provedor OpenAI-compatible configurável; Groq é o padrão econômico/gratuito.
        generic_key = os.getenv("LLM_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        tokenharbor_key = os.getenv("TOKENHARBOR_API_KEY")
        self.base_url = (
            os.getenv("LLM_BASE_URL")
            or (os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com") if deepseek_key else "")
            or (os.getenv("TOKENHARBOR_BASE_URL", "https://tokenharbor.ai/v1") if tokenharbor_key else "")
            or "https://api.groq.com/openai/v1"
        )
        self.uses_tokenharbor = bool(not generic_key and not deepseek_key and tokenharbor_key)
        self.uses_deepseek_api = "api.deepseek.com" in self.base_url
        default_model = (
            os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            if self.uses_deepseek_api
            else ("deepseek-v4.1-flash:free" if self.uses_tokenharbor else "llama-3.3-70b-versatile")
        )
        if client is None:
            from openai import OpenAI

            api_key = generic_key or deepseek_key or tokenharbor_key
            if not api_key:
                raise RuntimeError("Defina LLM_API_KEY (provedor configurado), DEEPSEEK_API_KEY ou TOKENHARBOR_API_KEY")
            client = OpenAI(api_key=api_key, base_url=self.base_url)
        self.client = client
        self.model = model or os.getenv("LLM_MODEL") or os.getenv("DEEPSEEK_MODEL", default_model)
        self.system_prompt = carregar_prompt_mj()
        self.engine = build_default_engine()
        # Rolagens do motor registradas na última resposta, em ordem de resolução.
        self.ultimas_rolagens: list[dict[str, Any]] = []

    def _registrar_rolagens(self, on_roll: Any, rolagens: list[dict[str, Any]]) -> None:
        """Anuncia ao MJ/à interface todas as rolagens que o motor acabou de gerar."""
        for rolagem in rolagens:
            if not rolagem:
                continue
            registro = getattr(self, "ultimas_rolagens", None)
            if registro is None:
                registro = self.ultimas_rolagens = []
            registro.append(rolagem)
            if on_roll is not None:
                on_roll(rolagem)


    def _tool(
        self,
        name: str,
        args: dict[str, Any],
        personagens: list[dict[str, Any]] | None = None,
        on_character_update: Any | None = None,
        on_roll: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Repassa a chamada de ferramenta ao Orquestrador de Ações.

        O MJ não decide mecânica: ele declara a intenção, e o orquestrador
        valida pré-condições, chama o motor, aplica a alteração na ficha e
        devolve o que aconteceu. Aqui só sobra a tradução de formato.
        """
        resultado = self._orquestrador().executar_ferramenta(
            name,
            args,
            personagens,
            on_alteracao=(
                (lambda ficha, alteracao: on_character_update(ficha))
                if on_character_update is not None else None
            ),
            # A instância sempre guarda as rolagens da última resposta; o
            # callback, quando existe, é quem as leva à interface.
            on_rolagem=lambda rolagem: self._registrar_rolagens(on_roll, [rolagem]),
        )
        return resultado.para_ferramenta()

    def _orquestrador(self) -> OrquestradorAcoes:
        """Orquestrador da instância, criado sob demanda com o motor do MJ."""
        if getattr(self, "_orquestrador_acoes", None) is None:
            self._orquestrador_acoes = OrquestradorAcoes(getattr(self, "engine", None))
        return self._orquestrador_acoes

    @staticmethod
    def _message_dict(message: Any) -> dict[str, Any]:
        if hasattr(message, "model_dump"):
            return message.model_dump(exclude_none=True)
        if isinstance(message, dict):
            return message
        return {
            "role": getattr(message, "role", "assistant"),
            "content": getattr(message, "content", None),
            "reasoning_content": getattr(message, "reasoning_content", None),
            "tool_calls": getattr(message, "tool_calls", None),
        }

    def responder(
        self,
        texto: str,
        historico: list[dict[str, Any]] | None = None,
        personagens: list[dict[str, Any]] | None = None,
        on_character_update: Any | None = None,
        on_roll: Callable[[dict[str, Any]], None] | None = None,
    ) -> str:
        self.ultimas_rolagens = []
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        mensagens.extend(historico or [])
        mensagens.append({"role": "user", "content": texto})

        for _ in range(5):
            parametros = {
                "model": self.model,
                "messages": mensagens,
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_tokens": 2048,
            }
            if self.uses_deepseek_api:
                parametros["extra_body"] = {"thinking": {"type": "disabled"}}
            resposta = self.client.chat.completions.create(**parametros)
            mensagem = resposta.choices[0].message
            mensagens.append(self._message_dict(mensagem))
            chamadas = getattr(mensagem, "tool_calls", None) or []
            if not chamadas:
                return getattr(mensagem, "content", "") or ""
            for chamada in chamadas:
                funcao = chamada.function
                resultado = self._tool(
                    funcao.name, json.loads(funcao.arguments), personagens,
                    on_character_update, on_roll,
                )
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })
        raise RuntimeError("O MJ excedeu o limite de chamadas de ferramentas")
