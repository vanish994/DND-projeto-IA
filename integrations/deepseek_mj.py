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
from rule_engine.catalog import CATALOGO_ARMAS
from rule_engine.character import PROFICIENCIAS_CLASSE
from rule_engine.bestiary import consultar_monstro
from rule_engine.spellcasting import ARTIFICER_SPELL_LEVELS, normalizar_nome_magia, progresso_artifice


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
            "description": "Resolve fatos mecânicos. Em attack, recebe modifier e target_ac e gera d20 auditável para hit/miss/crítico. Em initiative, gera d20 e aplica desvantagem quando surprised=true. Em ability_check sem roll, gera d20 auditável.",
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

    def _tool(
        self,
        name: str,
        args: dict[str, Any],
        personagens: list[dict[str, Any]] | None = None,
        on_character_update: Any | None = None,
    ) -> dict[str, Any]:
        personagem_magia: dict[str, Any] | None = None
        slot_a_consumir: str | None = None
        if name == "sugerir_monstros":
            facts = {"type": "bestiary", "operacao": "sugerir", **args}
        elif name == "consultar_monstro":
            facts = {"type": "bestiary", "operacao": "bloco_completo", **args}
        elif name == "resolver_regra":
            facts = dict(args["fatos"])
            if facts.get("type") in {"attack", "initiative"}:
                grupo = personagens or []
                personagem_id = facts.get("character_id")
                personagem = next((p for p in grupo if p.get("id") == personagem_id), None)
                if personagem is None and not personagem_id and len(grupo) == 1:
                    personagem = grupo[0]
                if personagem is None:
                    return {"resultado": "bloqueado", "motivo": "personagem_ausente_ou_nao_identificado"}

                atributos = personagem.get("atributos") or {}
                modificadores = personagem.get("modificadores") or {}
                if facts.get("type") == "initiative":
                    if "destreza" in modificadores:
                        modifier = int(modificadores["destreza"])
                    elif "destreza" in atributos:
                        modifier = (int(atributos["destreza"]) - 10) // 2
                    else:
                        return {"resultado": "bloqueado", "motivo": "destreza_ausente_na_ficha"}
                    facts["modifier"] = modifier
                    facts["character_id"] = personagem.get("id")
                    facts["modifier_source"] = "ficha_autoritativa"
                else:
                    nome_arma = str(facts.get("weapon", facts.get("arma", ""))).strip()
                    nome_canonico = next((k for k in CATALOGO_ARMAS if k.casefold() == nome_arma.casefold()), None)
                    arma = CATALOGO_ARMAS.get(nome_canonico) if nome_canonico else None
                    if arma is None:
                        return {"resultado": "bloqueado", "motivo": "arma_nao_encontrada_no_catalogo", "arma": nome_arma}

                    classe = str(personagem.get("classe", "")).strip().lower()
                    prof_classe = PROFICIENCIAS_CLASSE.get(classe, {}).get("armas", [])
                    # Mesma classificação usada pelo combate tático do backend.
                    simples = {
                        "clava", "clava grande", "adaga", "dardo", "machadinha", "martelo leve",
                        "maça", "cajado", "funda", "azagaia", "arco curto", "besta leve",
                    }
                    nome_normalizado = nome_canonico.casefold()
                    # Druida usa a lista específica do Livro do Jogador, não toda a categoria simples.
                    arma_proficiente = (
                        "simples" in prof_classe and classe != "druida" and nome_normalizado in simples
                    )
                    arma_proficiente = arma_proficiente or ("marciais" in prof_classe and nome_canonico not in {
                        next((k for k in CATALOGO_ARMAS if k.casefold() == x), x) for x in simples
                    })
                    if not arma_proficiente:
                        categorias = {
                            "besta de mão": "bestas_de_mao", "espada longa": "espadas_longas",
                            "rapieira": "rapieiras", "espada curta": "espadas_curtas",
                            "besta leve": "bestas_leves", "adaga": "adagas", "dardo": "dardos",
                            "funda": "fundas", "cajado": "cajados", "azagaia": "azagaias",
                            "maça": "macas", "clava": "clavas", "foice": "foices",
                            "lança": "lancas", "cimitarra": "cimitarras",
                        }
                        categoria = categorias.get(nome_normalizado)
                        arma_proficiente = bool(categoria and categoria in prof_classe)
                    if not arma_proficiente:
                        return {"resultado": "bloqueado", "motivo": "personagem_sem_proficiencia_na_arma", "arma": nome_canonico, "classe": classe}

                    propriedades = set(arma.get("propriedades", []))
                    if "acuidade" in propriedades:
                        if not all(k in atributos or k in modificadores for k in ("forca", "destreza")):
                            return {"resultado": "bloqueado", "motivo": "atributos_para_arma_ausentes_na_ficha"}
                        forca = int(modificadores["forca"]) if "forca" in modificadores else (int(atributos["forca"]) - 10) // 2
                        destreza = int(modificadores["destreza"]) if "destreza" in modificadores else (int(atributos["destreza"]) - 10) // 2
                        atributo_ataque = "forca" if forca >= destreza else "destreza"
                        modificador_atributo = max(forca, destreza)
                    elif "municao" in propriedades:
                        atributo_ataque = "destreza"
                        if atributo_ataque in modificadores:
                            modificador_atributo = int(modificadores[atributo_ataque])
                        elif atributo_ataque in atributos:
                            modificador_atributo = (int(atributos[atributo_ataque]) - 10) // 2
                        else:
                            return {"resultado": "bloqueado", "motivo": "destreza_ausente_na_ficha"}
                    else:
                        atributo_ataque = "forca"
                        if atributo_ataque in modificadores:
                            modificador_atributo = int(modificadores[atributo_ataque])
                        elif atributo_ataque in atributos:
                            modificador_atributo = (int(atributos[atributo_ataque]) - 10) // 2
                        else:
                            return {"resultado": "bloqueado", "motivo": "forca_ausente_na_ficha"}

                    nivel = max(1, int(personagem.get("nivel", 1)))
                    bonus_proficiencia = int(personagem.get("bonus_proficiencia", 2 + (nivel - 1) // 4))
                    facts["modifier"] = modificador_atributo + bonus_proficiencia
                    facts["character_id"] = personagem.get("id")
                    facts["proficiency_applied"] = bonus_proficiencia
                    facts["modifier_source"] = "ficha_autoritativa"
                    facts["weapon"] = nome_canonico
                    facts["weapon_damage"] = arma["dano"]
                    facts["damage_type"] = arma["tipo"]
                    facts["damage_modifier"] = modificador_atributo
                    facts["attack_ability"] = atributo_ataque

                    alvo_nome = str(facts.get("target_name", facts.get("alvo", ""))).strip()
                    if not alvo_nome:
                        return {"resultado": "bloqueado", "motivo": "nome_do_alvo_ausente"}
                    alvo = consultar_monstro(alvo_nome)
                    if alvo is None:
                        return {"resultado": "bloqueado", "motivo": "monstro_desconhecido_no_bestiario", "alvo": alvo_nome}
                    # A CA vem sempre do catálogo oficial; nunca confiar numa CA fornecida pelo modelo.
                    facts["target_ac"] = int(alvo["ca"])
                    facts["target_name"] = alvo["nome"]
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
                        "athletics": "atletismo", "acrobatics": "acrobacia", "animal_handling": "adestrar_animais", "lidar_com_animais": "adestrar_animais",
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
                    proficiencias = {
                        aliases.get(str(p).strip().lower().replace(" ", "_"), str(p).strip().lower().replace(" ", "_"))
                        for p in (personagem.get("pericias") or [])
                    }
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
            if facts.get("type") in {"saving_throw", "saving_throw_check"}:
                grupo = personagens or []
                personagem_id = facts.get("character_id")
                personagem_salvaguarda = next((p for p in grupo if p.get("id") == personagem_id), None)
                if personagem_salvaguarda is None and not personagem_id and len(grupo) == 1:
                    personagem_salvaguarda = grupo[0]
                if personagem_salvaguarda is None:
                    return {"resultado": "bloqueado", "motivo": "personagem_ausente_ou_nao_identificado"}
                bruto = facts.get("ability", facts.get("atributo"))
                aliases_atributo = {
                    "str": "forca", "strength": "forca", "for": "forca",
                    "dex": "destreza", "dexterity": "destreza", "des": "destreza",
                    "con": "constituicao", "constitution": "constituicao",
                    "int": "inteligencia", "intelligence": "inteligencia",
                    "wis": "sabedoria", "wisdom": "sabedoria", "sab": "sabedoria",
                    "cha": "carisma", "charisma": "carisma", "car": "carisma",
                }
                atributo = aliases_atributo.get(str(bruto).strip().lower(), str(bruto).strip().lower()) if bruto else ""
                atributos = personagem_salvaguarda.get("atributos") or {}
                modificadores = personagem_salvaguarda.get("modificadores") or {}
                if atributo not in {"forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"}:
                    return {"resultado": "bloqueado", "motivo": "atributo_de_salvaguarda_ausente_ou_invalido"}
                if atributo in modificadores:
                    modificador_atributo = int(modificadores[atributo])
                elif atributo in atributos:
                    modificador_atributo = (int(atributos[atributo]) - 10) // 2
                else:
                    return {"resultado": "bloqueado", "motivo": "atributo_ausente_na_ficha", "atributo": atributo}
                proficientes = set(personagem_salvaguarda.get("proficiencias_salvaguarda") or [])
                proficiente = atributo in proficientes
                pb = int(personagem_salvaguarda.get("bonus_proficiencia", 2))
                facts["ability"] = atributo
                facts["atributo"] = atributo
                facts["proficiencias_salvaguarda"] = sorted(proficientes)
                facts["proficiente"] = proficiente
                facts["modificador_atributo"] = modificador_atributo
                facts["bonus_proficiencia"] = pb
                facts["modifier"] = modificador_atributo + (pb if proficiente else 0)
                facts["character_id"] = personagem_salvaguarda.get("id")
                facts["proficiency_applied"] = pb if proficiente else 0
                facts["modifier_source"] = "ficha_autoritativa"
            if facts.get("type") in {"spell", "spell_cast"} and facts.get("magia"):
                grupo = personagens or []
                personagem_id = facts.get("character_id")
                personagem_magia = next((p for p in grupo if p.get("id") == personagem_id), None)
                if personagem_magia is None and not personagem_id and len(grupo) == 1:
                    personagem_magia = grupo[0]
                if personagem_magia is None:
                    return {"resultado": "bloqueado", "motivo": "personagem_ausente_ou_nao_identificado"}
                if personagem_magia.get("classe") == "artifice":
                    nome_magia = normalizar_nome_magia(facts.get("magia"))
                    circulo = next(
                        (nivel for nome, nivel in ARTIFICER_SPELL_LEVELS.items()
                         if normalizar_nome_magia(nome) == nome_magia),
                        None,
                    )
                    if circulo is None:
                        return {"resultado": "bloqueado", "motivo": "magia_nao_disponivel_para_artifice", "magia": facts.get("magia")}
                    conjuracao = personagem_magia.get("conjuracao") or {}
                    escolhidas = conjuracao.get("truques", []) if circulo == 0 else conjuracao.get("magias_preparadas", [])
                    if nome_magia not in {normalizar_nome_magia(x) for x in escolhidas}:
                        return {"resultado": "bloqueado", "motivo": "magia_nao_escolhida_na_ficha", "magia": facts.get("magia")}
                    progresso = progresso_artifice(
                        int(personagem_magia.get("nivel", 1)),
                        int((personagem_magia.get("atributos") or {}).get("inteligencia", 10)),
                    )
                    if circulo > progresso["circulo_maximo"]:
                        return {"resultado": "bloqueado", "motivo": "circulo_indisponivel_para_nivel", "circulo": circulo}
                    facts["character_id"] = personagem_magia.get("id")
                    if circulo > 0:
                        try:
                            slot = int(facts.get("espaco", facts.get("slot_level", circulo)))
                        except (TypeError, ValueError):
                            return {"resultado": "bloqueado", "motivo": "espaco_de_magia_invalido"}
                        if slot < circulo or slot > progresso["circulo_maximo"]:
                            return {"resultado": "bloqueado", "motivo": "espaco_incompativel_com_magia", "circulo_magia": circulo, "espaco_solicitado": slot}
                        totais = conjuracao.get("espacos_totais") or progresso["espacos_totais"]
                        restantes = conjuracao.get("espacos_restantes") or totais
                        if int(restantes.get(str(slot), 0)) < 1:
                            return {"resultado": "bloqueado", "motivo": "sem_espacos_restantes", "espaco": slot}
                        facts["espaco"] = slot
                        slot_a_consumir = str(slot)
        else:
            return {"resultado": "bloqueado", "motivo": "ferramenta_desconhecida"}
        resolution = self.engine.evaluate(facts)
        resultado = {"status": resolution.status, **dict(resolution.outcome)}
        if name == "resolver_regra" and personagem_magia is not None and slot_a_consumir is not None and resultado.get("resultado") == "conjurada":
            conjuracao = dict(personagem_magia.get("conjuracao") or {})
            totais = dict(conjuracao.get("espacos_totais") or {})
            restantes = dict(conjuracao.get("espacos_restantes") or totais)
            restantes[slot_a_consumir] = max(0, int(restantes.get(slot_a_consumir, 0)) - 1)
            conjuracao["espacos_restantes"] = restantes
            personagem_magia["conjuracao"] = conjuracao
            resultado["espacos_restantes"] = restantes
            if on_character_update is not None:
                on_character_update(personagem_magia)
        for chave in (
            "character_id", "proficiency_applied", "modifier_source", "weapon",
            "weapon_damage", "damage_type", "damage_modifier", "attack_ability",
            "target_name",
        ):
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

    def responder(
        self,
        texto: str,
        historico: list[dict[str, Any]] | None = None,
        personagens: list[dict[str, Any]] | None = None,
        on_character_update: Any | None = None,
    ) -> str:
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
                resultado = self._tool(funcao.name, json.loads(funcao.arguments), personagens, on_character_update)
                mensagens.append({
                    "role": "tool",
                    "tool_call_id": chamada.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })
        raise RuntimeError("O MJ excedeu o limite de chamadas de ferramentas")
