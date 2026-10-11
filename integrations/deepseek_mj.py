"""MJ conversacional baseado na API do DeepSeek.

O DeepSeek conduz a conversa, a narrativa e as decisões de apresentação.
O Rule Engine é a autoridade exclusiva para mecânicas de D&D chamadas por
ferramentas. Este módulo não envia a história inteira ao motor.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from rule_engine import PERICIAS, build_default_engine


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

REGRA PRIORITÁRIA — FICHA E INÍCIO DA CAMPANHA:
- Antes de descrever a primeira cena, leia o bloco de ESTADO AUTORITATIVO DOS PERSONAGENS fornecido no contexto.
- Se houver personagem cadastrado, use exatamente essa ficha. Nunca invente nem troque nome, espécie/raça, classe, nível, antecedente, atributos, proficiências, magias ou outros dados. Não peça novamente dados já registrados.
- Se a ficha não registrar nome, aparência, personalidade ou história pessoal, não preencha essas lacunas por conta própria como fatos estabelecidos. Faça uma pergunta curta ou deixe o detalhe em aberto.
- Se não houver personagem cadastrado, não comece uma cena atribuindo ao jogador um personagem fictício. Pergunte qual personagem existente ele quer usar ou peça que crie um.
- Diferencie fatos da ficha de detalhes narrativos novos. Você pode criar cenário e ganchos, mas não pode afirmar que o personagem conhece um lugar, tem uma profissão, possui um item ou viveu um acontecimento sem base na ficha ou confirmação do jogador.
- Se o jogador disser que já tem um personagem, consulte o estado fornecido; não peça para recriá-lo nem solicite nome/classe se esses dados já estiverem registrados.

REGRA PRIORITÁRIA — RESOLUÇÃO MECÂNICA:
- Não declare sucesso, falha, dano, cura, gasto de recurso, movimento ou efeito mecânico antes de consultar a ferramenta apropriada.
- Para testes, ataques, salvaguardas, magias e ações de classe, use apenas dados da ficha e resultados do motor. Nunca invente proficiências, bônus, CA, alcance, espaços de magia ou efeitos ausentes.
- Se a ferramenta disponível não cobrir a ação, diga que a resolução mecânica ainda não está implementada e não simule que o motor a validou. Preserve a escolha do jogador e peça como deseja proceder narrativamente, sem apresentar isso como regra oficial.

As ferramentas devolvem dados normativos. Você decide como apresentar e narrar
o resultado, sem alterar os valores oficiais. A escolha final de monstros e o
rumo da história permanecem com o MJ.
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
            "description": "Resolve fatos mecânicos usando o Rule Engine; em ability_check sem roll, o motor gera o d20 auditável.",
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
        self.uses_tokenharbor = bool(os.getenv("TOKENHARBOR_API_KEY"))
        default_model = "deepseek-v4.1-flash:free" if os.getenv("TOKENHARBOR_API_KEY") else "deepseek-flash"
        if client is None:
            from openai import OpenAI

            tokenharbor_key = os.getenv("TOKENHARBOR_API_KEY")
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")
            api_key = tokenharbor_key or deepseek_key
            if not api_key:
                raise RuntimeError("Defina TOKENHARBOR_API_KEY ou DEEPSEEK_API_KEY")
            if tokenharbor_key:
                base_url = os.getenv("TOKENHARBOR_BASE_URL", "https://tokenharbor.ai/v1")
            else:
                base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )
        self.client = client
        self.model = model or os.getenv("DEEPSEEK_MODEL", default_model)
        self.system_prompt = carregar_prompt_mj()
        self.engine = build_default_engine()

    def _tool(self, name: str, args: dict[str, Any], personagens: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        if name == "sugerir_monstros":
            facts = {"type": "bestiary", "operacao": "sugerir", **args}
        elif name == "consultar_monstro":
            facts = {"type": "bestiary", "operacao": "bloco_completo", **args}
        elif name == "resolver_regra":
            facts = dict(args["fatos"])
            if facts.get("type") == "ability_check":
                grupo = personagens or []
                personagem_id = facts.get("character_id")
                personagem = next((p for p in grupo if p.get("id") == personagem_id), None)
                if personagem is None and not personagem_id and len(grupo) == 1:
                    personagem = grupo[0]
                if personagem is None:
                    return {"resultado": "bloqueado", "motivo": "personagem_ausente_ou_nao_identificado"}
                pericia_bruta = facts.get("skill", facts.get("pericia"))
                if pericia_bruta:
                    pericia = str(pericia_bruta).strip().lower().replace(" ", "_")
                    aliases = {
                        "athletics": "atletismo", "acrobatics": "acrobacia", "animal_handling": "adestrar_animais",
                        "sleight_of_hand": "prestidigitacao", "stealth": "furtividade", "arcana": "arcanismo",
                        "history": "historia", "insight": "intuicao", "intimidation": "intimidacao",
                        "investigation": "investigacao", "medicine": "medicina", "nature": "natureza",
                        "perception": "percepcao", "performance": "atuacao", "persuasion": "persuasao",
                        "religion": "religiao", "survival": "sobrevivencia", "deception": "enganacao",
                    }
                    pericia = aliases.get(pericia, pericia)
                    if pericia not in PERICIAS:
                        return {"resultado": "bloqueado", "motivo": "pericia_desconhecida", "pericia": pericia}
                    atributo = PERICIAS[pericia]
                    atributo_informado = facts.get("ability", facts.get("atributo"))
                    if atributo_informado:
                        normalizados = {
                            "str": "forca", "strength": "forca", "for": "forca",
                            "dex": "destreza", "dexterity": "destreza", "des": "destreza",
                            "con": "constituicao", "constitution": "constituicao",
                            "int": "inteligencia", "intelligence": "inteligencia",
                            "wis": "sabedoria", "wisdom": "sabedoria", "sab": "sabedoria",
                            "cha": "carisma", "charisma": "carisma", "car": "carisma",
                        }
                        informado = normalizados.get(str(atributo_informado).strip().lower(), str(atributo_informado).strip().lower())
                        if informado != atributo:
                            return {"resultado": "bloqueado", "motivo": "atributo_incompativel_com_pericia", "pericia": pericia, "atributo_correto": atributo}
                    facts["skill"] = pericia
                    facts["ability"] = atributo
                    proficiencias = {str(p).strip().lower().replace(" ", "_") for p in (personagem.get("pericias") or [])}
                    proficiente = pericia in proficiencias
                else:
                    atributo_bruto = facts.get("ability", facts.get("atributo"))
                    aliases_atributo = {
                        "str": "forca", "strength": "forca", "for": "forca",
                        "dex": "destreza", "dexterity": "destreza", "des": "destreza",
                        "con": "constituicao", "constitution": "constituicao",
                        "int": "inteligencia", "intelligence": "inteligencia",
                        "wis": "sabedoria", "wisdom": "sabedoria", "sab": "sabedoria",
                        "cha": "carisma", "charisma": "carisma", "car": "carisma",
                    }
                    atributo = aliases_atributo.get(str(atributo_bruto).strip().lower(), str(atributo_bruto).strip().lower()) if atributo_bruto else ""
                    if atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
                        return {"resultado": "bloqueado", "motivo": "atributo_ausente_ou_invalido"}
                    facts["ability"] = atributo
                    proficiente = False
                modificadores = personagem.get("modificadores") or {}
                atributos = personagem.get("atributos") or {}
                if atributo in modificadores:
                    modificador_atributo = int(modificadores[atributo])
                elif atributo in atributos:
                    modificador_atributo = (int(atributos[atributo]) - 10) // 2
                else:
                    return {"resultado": "bloqueado", "motivo": "atributo_ausente_na_ficha", "atributo": atributo}
                bonus_proficiencia = int(personagem.get("bonus_proficiencia", 2)) if proficiente else 0
                facts["modifier"] = modificador_atributo + bonus_proficiencia
                facts["character_id"] = personagem.get("id")
                facts["proficiency_applied"] = bonus_proficiencia
                facts["modifier_source"] = "ficha_autoritativa"
        else:
            return {"resultado": "bloqueado", "motivo": "ferramenta_desconhecida"}
        resolution = self.engine.evaluate(facts)
        resultado = {"status": resolution.status, **dict(resolution.outcome)}
        for chave in ("character_id", "proficiency_applied", "modifier_source"):
            if chave in facts:
                resultado[chave] = facts[chave]
        return resultado

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

    def responder(self, texto: str, historico: list[dict[str, Any]] | None = None, personagens: list[dict[str, Any]] | None = None) -> str:
        mensagens: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]
        mensagens.extend(historico or [])
        mensagens.append({"role": "user", "content": texto})

        for _ in range(8):
            parametros = {
                "model": self.model,
                "messages": mensagens,
                "tools": TOOLS,
                "tool_choice": "auto",
                "max_tokens": 4096,
            }
            if not self.uses_tokenharbor:
                parametros["extra_body"] = {"thinking": {"type": "disabled"}}
            resposta = self.client.chat.completions.create(**parametros)
            mensagem = resposta.choices[0].message
            mensagens.append(self._message_dict(mensagem))
            chamadas = getattr(mensagem, "tool_calls", None) or []
            if not chamadas:
                return getattr(mensagem, "content", "") or ""
            for chamada in chamadas:
                funcao = chamada.function
                resultado = self._tool(funcao.name, json.loads(funcao.arguments), personagens)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })
        raise RuntimeError("O MJ excedeu o limite de chamadas de ferramentas")
