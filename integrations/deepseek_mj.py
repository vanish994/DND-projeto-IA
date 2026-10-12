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

A história, a ambientação, os personagens narrativos, os diálogos, os conflitos,
as cenas e a criatividade são livres e pertencem ao MJ. Não gere uma aventura
pré-fabricada nem tente controlar a imaginação do usuário.

Quando houver uma afirmação mecânica de D&D — monstro, magia, item, condição,
ataque, dano, cura, CD, resistência, imunidade, XP ou outra regra — use uma das
ferramentas disponíveis. Nunca invente conteúdo mecânico e nunca apresente uma
regra caseira como oficial. Se o Rule Engine bloquear ou não encontrar algo,
informe isso claramente e peça uma decisão narrativa ao MJ.

Em testes de habilidade, o MJ pode definir a CD, mas nunca forneça ou invente o
resultado do d20. Chame resolver_regra com type=ability_check, ability, skill,
modifier e, se já definida, dc. O motor gera o d20 e devolve uma seed auditável.
Se a resposta vier com result=requires_dc, peça ao MJ a CD e repita o teste com
a mesma seed para reproduzir a rolagem. Só narre sucesso ou falha após a resposta
final do motor.

Para salvaguardas, chame resolver_regra com type=saving_throw, ability (ou
atributo), modifier derivado da ficha e dc quando o efeito já definir a CD. O
motor gera o d20 auditável; nunca forneça o resultado da salvaguarda.

CONJURAR MAGIA (registro de espaço):
- Para conjurar, chame resolver_regra com type=spell, character_id, magia (nome
  exato do catálogo) e, quando gastar um espaço maior que o círculo da magia,
  espaco. O motor confere se a magia está na ficha, gasta o espaço e responde
  resultado=conjurada; sem espaço disponível a resposta é bloqueado com
  motivo=sem_espacos_restantes. Truques não gastam espaço.
- Nunca conte espaços de magia de cabeça: use espacos_restantes da resposta.
- resultado=nao_implementado não é sucesso: informe a limitação e não narre o
  efeito como aplicado. A descrição de uma magia não substitui sua resolução.
- O registro de conjuração e a rolagem de dano são etapas diferentes. Uma
  rolagem com aplicado_ao_alvo=false não altera PV nem comprova consumo de espaço.
  Não afirme atualização de ficha sem confirmação de uma operação persistida.

ATAQUES DE MAGIA (truques e magias com jogada de ataque):
- Quando a magia do catálogo tem resolução de ataque mágico, chame
  resolver_regra com type=attack, magia (nome exato do catálogo) e target_name
  (monstro do bestiário). Não informe modifier nem target_ac.
- O motor deriva o bônus de ataque do atributo de conjuração da ficha, confere
  a CA no bestiário e rola o d20 e o dano da magia. Truques escalam pelo nível
  do personagem (5, 11 e 17) e o motor já aplica esse escalonamento.
- O truque precisa estar registrado na ficha (conjuracao.truques) e a magia de
  círculo 1+ em conjuracao.magias_preparadas. Se não estiver, o motor bloqueia;
  diga ao jogador para registrar a magia, sem inventar o efeito.
- Se o motor responder magia_sem_mecanica_estruturada_no_catalogo ou
  magia_nao_resolve_por_jogada_de_ataque, informe a limitação com clareza e não
  narre dano oficial.
- Magias que pedem salvaguarda do alvo (como Bola de Fogo, Mãos Flamejantes e
  Onda Trovejante) NÃO são jogadas de ataque: nunca as envie como attack.

MAGIAS DE DANO POR SALVAGUARDA (Bola de Fogo, Mãos Flamejantes, Onda Trovejante):
- Passo 1: chame resolver_regra com type=damage, character_id e magia (nome exato
  do catálogo); se o jogador gastar um espaço maior, informe espaco. O motor
  devolve dados_dano, dano, tipo_dano e cd_magia. NÃO invente os dados: eles vêm
  do catálogo, já escalonados.
- Passo 2: para cada alvo na área, chame resolver_regra com type=saving_throw,
  ability = magia_salvaguarda, target_name e dc = cd_magia. O motor rola a
  salvaguarda.
- Passo 3: aplique o passo 1 a quem falhou e, quando magia_sucesso_metade for
  verdadeiro, metade (arredondada para baixo) a quem passou. O dano é o mesmo
  para todos os alvos da área: role uma vez e use o mesmo total.
- Sem cd_magia na resposta (ficha ausente), não invente a CD: informe o jogador.

ATAQUE DE SOPRO (Draconato):
- Envie type=attack com weapon="Ataque de Sopro" e target_name. O motor confere a
  Herança Dracônica da ficha, rola a salvaguarda de Destreza do alvo, rola o dano
  por nível (1d10/2d10/3d10/4d10), aplica metade no sucesso e as resistências do
  bloco, e devolve usos_por_descanso_longo.
- Se a resposta for ataque_de_sopro_exige_draconato_com_heranca_draconica_na_ficha,
  o personagem não é um Draconato com herança registrada: diga isso ao jogador.

REGRA PRIORITÁRIA — FICHA E INÍCIO DA CAMPANHA:
- Antes de descrever a primeira cena, leia o bloco de ESTADO AUTORITATIVO DOS PERSONAGENS fornecido no contexto.
- Se houver personagem cadastrado, use exatamente essa ficha. Nunca invente nem troque nome, espécie/raça, classe, nível, antecedente, atributos, proficiências, magias ou outros dados. Não peça novamente dados já registrados.
- Se a ficha não registrar aparência, personalidade ou história pessoal, não interrompa a aventura para exigir esses detalhes. Trate-os como desconhecidos, descreva apenas o que é observável e deixe o jogador defini-los espontaneamente.
- Se não houver personagem cadastrado, não comece uma cena atribuindo ao jogador um personagem fictício. Pergunte qual personagem existente ele quer usar ou peça que crie um.
- Diferencie fatos da ficha de detalhes narrativos novos. Você pode criar cenário e ganchos, mas não pode afirmar que o personagem conhece um lugar, tem uma profissão, possui um item ou viveu um acontecimento sem base na ficha ou confirmação do jogador.
- Se o jogador disser que já tem um personagem, consulte o estado fornecido; não peça para recriá-lo nem solicite nome/classe se esses dados já estiverem registrados.

REGRA PRIORITÁRIA — RESOLUÇÃO MECÂNICA:
- Não declare sucesso, falha, dano, cura, gasto de recurso, movimento ou efeito mecânico antes de consultar a ferramenta apropriada.
- Para ataques, chame resolver_regra com fatos contendo type=attack, character_id (se houver mais de um personagem), weapon (nome exato de uma arma do catálogo) e target_name (nome de um monstro do bestiário). A ferramenta deriva bônus e dano da ficha/classe e da arma e consulta a CA do bestiário; não invente modifier nem target_ac. Se o alvo não for um monstro do bestiário, informe a limitação em vez de adivinhar a CA. O motor gera o d20 auditável e determina hit/miss/crítico. Para iniciativa, use type=initiative, character_id quando necessário e surprised=true quando a criatura estiver surpresa; o motor deriva Destreza da ficha. Em D&D 2024, surpresa impõe desvantagem na iniciativa, não um teste separado.
- Se a ferramenta disponível não cobrir a ação, diga que a resolução mecânica ainda não está implementada e não simule que o motor a validou. Preserve a escolha do jogador e peça como deseja proceder narrativamente, sem apresentar isso como regra oficial.

As ferramentas devolvem dados normativos. Você decide como apresentar e narrar
o resultado, sem alterar os valores oficiais. O MJ tem autonomia para conduzir a aventura. Quando o jogador pedir para começar ou disser que o MJ decide, escolha por conta própria um cenário, ganchos e encontros adequados ao nível. Não peça ao jogador para selecionar monstros, definir encontros ou decidir tarefas rotineiras do mestre. Faça perguntas apenas quando uma escolha do jogador for realmente necessária.
Mantenha a narração focada e concisa; não repita contexto nem liste opções genéricas a cada turno.
Em combate, nunca converta ataque em teste de habilidade. Use uma resolução de ataque apropriada se disponível; se o motor ainda não suportar a mecânica, informe a limitação com brevidade, sem inventar resultados nem culpar o jogador.
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
            "description": "Resolve fatos mecânicos. Em spell, o motor confere a magia na ficha, gasta o espaço e responde conjurada. Em attack com weapon, o motor deriva bônus e dano da ficha e consulta a CA do bestiário. Em attack com magia, o motor deriva o bônus de conjuração da ficha, aplica o escalonamento de truque e rola o dano da magia. Em initiative, gera d20 e aplica desvantagem quando surprised=true. Em ability_check e em saving_throw sem roll, gera d20 auditável e compara com dc quando fornecida.",
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
