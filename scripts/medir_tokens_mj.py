"""Mede o consumo real de contexto do MJ, sem chamar a rede.

O orquestrador só economiza tokens se o que o MJ envia ao provedor for menor.
Este script mede isso de verdade no repositório: usa o ``DeepSeekMJ`` de
produção com um cliente de LLM roteirizado (mesmo harness dos testes), captura
**todas** as requisições enviadas e mostra onde o contexto é gasto.

Não é estimativa de marketing: são os caracteres reais de cada requisição, com
contagem de tokens por tokenizador quando disponível.

Uso:

    python scripts/medir_tokens_mj.py
    python scripts/medir_tokens_mj.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from integrations.deepseek_mj import DeepSeekMJ  # noqa: E402


def _tokenizador():
    """Contagem de tokens: usa tiktoken quando existir, senão estima."""
    try:
        import tiktoken  # type: ignore

        codificador = tiktoken.get_encoding("cl100k_base")
        return lambda texto: len(codificador.encode(texto)), "tiktoken/cl100k_base"
    except Exception:
        # Heurística conservadora: português costuma ficar perto de 3,5 chars/token.
        return lambda texto: round(len(texto) / 3.5), "estimativa (3.5 chars/token)"


def _serializar(objeto):
    """Serializa objetos do cliente falso como o SDK real faria."""
    funcao = getattr(objeto, "function", None)
    if funcao is not None:
        return {"function": {"name": funcao.name, "arguments": funcao.arguments}}
    raise TypeError(f"tipo não serializável: {type(objeto).__name__}")


class _Ferramenta:
    def __init__(self, nome, argumentos, identificador="call-1"):
        self.id = identificador
        self.function = type(
            "Funcao", (), {"name": nome, "arguments": json.dumps(argumentos, ensure_ascii=False)}
        )()


class _Mensagem:
    def __init__(self, content=None, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []


class _Resposta:
    def __init__(self, mensagem):
        self.choices = [type("Escolha", (), {"message": mensagem})()]


class ClienteMedidor:
    """Cliente roteirizado que registra o custo de cada requisição."""

    def __init__(self, mensagens):
        self.pendentes = list(mensagens)
        self.requisicoes: list[dict] = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **parametros):
        self.requisicoes.append(parametros)
        return _Resposta(self.pendentes.pop(0))


FICHA = {
    "id": "p1", "nome": "Tessa", "classe": "feiticeiro", "especie": "draconato",
    "antecedente": "sabio", "nivel": 5, "pv_atual": 24, "pv_maximo": 30,
    "bonus_proficiencia": 3,
    "atributos": {"forca": 8, "destreza": 14, "constituicao": 14,
                  "inteligencia": 12, "sabedoria": 10, "carisma": 16},
    "modificadores": {"forca": -1, "destreza": 2, "constituicao": 2,
                      "inteligencia": 1, "sabedoria": 0, "carisma": 3},
    "pericias": ["arcanismo", "enganacao", "persuasao"],
    "pericias_classe": ["arcanismo", "persuasao"],
    "proficiencias_salvaguarda": ["constituicao", "carisma"],
    "talentos": ["Sortudo"], "deslocamento": 9,
    "heranca_draconica": None,
    "conjuracao": {"truques": ["Raio de Fogo", "Ilusao Menor"],
                   "magias_preparadas": ["Bola de Fogo", "Escudo", "Misseis Magicos"],
                   "espacos_totais": {"1": 3, "2": 2, "3": 2},
                   "espacos_restantes": {"1": 3, "2": 2, "3": 2}},
}

HISTORICO_TIPICO = 20  # mensagens anteriores na campanha


def _ficha_com_heranca():
    from rule_engine.species import bloco_heranca_draconica

    ficha = dict(FICHA)
    ficha["heranca_draconica"] = bloco_heranca_draconica("vermelho", 5, 2, 3)
    return ficha


def historico_simulado(mensagens: int = HISTORICO_TIPICO) -> list[dict]:
    """Histórico plausível de campanha: MJ narrando e jogador agindo."""
    narrativa = (
        "A taverna range com o vento da costa. Você percebe que o homem de capa cinza "
        "observa a porta há três canecas, e que o selo no papel que ele carrega traz o "
        "mesmo dragão alado gravado no medalhão da sua mãe. Ele não notou você ainda."
    )
    acao = "Observo o homem de capa cinza e tento ler o selo no papel que ele carrega."
    historico: list[dict] = []
    for _ in range(max(1, mensagens // 2)):
        historico.append({"role": "assistant", "content": narrativa})
        historico.append({"role": "user", "content": acao})
    return historico[-mensagens:]


CENARIOS = {
    "narrativo simples (sem ferramenta)": [
        _Mensagem(content="Você descreve a taverna e o homem de capa cinza."),
    ],
    "ataque com arma (1 ferramenta)": [
        _Mensagem(tool_calls=[_Ferramenta("resolver_regra", {"fatos": {
            "type": "attack", "character_id": "p1", "weapon": "Adaga", "target_name": "Goblin",
        }})]),
        _Mensagem(content="Sua adaga encontra o flanco do goblin."),
    ],
    "conjuração + dano de área (2 ferramentas)": [
        _Mensagem(tool_calls=[_Ferramenta("resolver_regra", {"fatos": {
            "type": "spell", "character_id": "p1", "magia": "Bola de Fogo",
        }}, "call-1")]),
        _Mensagem(tool_calls=[_Ferramenta("resolver_regra", {"fatos": {
            "type": "damage", "character_id": "p1", "magia": "Bola de Fogo",
        }}, "call-2")]),
        _Mensagem(content="A Bola de Fogo varre a sala e o goblin cai."),
    ],
    "consulta de monstro (1 ferramenta de bestiário)": [
        _Mensagem(tool_calls=[_Ferramenta("consultar_monstro", {"nome": "Goblin"})]),
        _Mensagem(content="O goblin avança com a lâmina torta."),
    ],
}


def medir(nome: str, mensagens, contar_tokens) -> dict:
    cliente = ClienteMedidor(mensagens)
    mj = DeepSeekMJ(client=cliente, model="teste")
    personagens = [_ficha_com_heranca()]
    historico = historico_simulado()
    contexto = __import__("orchestrator").resumo_autoritativo(personagens)

    mj.responder("Ataco o goblin.", [{**m, "role": m["role"]} for m in [{"role": "system", "content": contexto}, *historico]],
                 personagens=personagens)

    entrada = 0
    saida = 0
    por_requisicao = []
    for requisicao in cliente.requisicoes:
        texto = json.dumps(requisicao.get("messages", []), ensure_ascii=False, default=_serializar)
        ferramentas = json.dumps(requisicao.get("tools", []), ensure_ascii=False, default=_serializar)
        tokens = contar_tokens(texto) + contar_tokens(ferramentas)
        por_requisicao.append({"chars": len(texto) + len(ferramentas), "tokens": tokens})
        entrada += tokens
        for mensagem in requisicao.get("messages", []):
            if mensagem.get("role") == "assistant" and mensagem.get("content"):
                saida += contar_tokens(mensagem["content"])

    return {
        "cenario": nome,
        "chamadas_ao_modelo": len(cliente.requisicoes),
        "tokens_entrada": entrada,
        "tokens_saida": saida,
        "tokens_total": entrada + saida,
        "chars_entrada": sum(r["chars"] for r in por_requisicao),
        "por_requisicao": por_requisicao,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="imprime o resultado bruto em JSON")
    argumentos = parser.parse_args()

    contar_tokens, metodo = _tokenizador()
    resultados = [medir(nome, mensagens, contar_tokens) for nome, mensagens in CENARIOS.items()]

    if argumentos.json:
        print(json.dumps({"metodo": metodo, "resultados": resultados, "historico_mensagens": HISTORICO_TIPICO},
                         ensure_ascii=False, indent=2))
        return

    print(f"Contagem de tokens: {metodo} | histórico simulado: {HISTORICO_TIPICO} mensagens")
    print(f"{'cenário':<48}{'chamadas':>9}{'entrada':>10}{'saída':>8}{'total':>9}")
    print("-" * 84)
    for resultado in resultados:
        print(f"{resultado['cenario']:<48}{resultado['chamadas_ao_modelo']:>9}"
              f"{resultado['tokens_entrada']:>10}{resultado['tokens_saida']:>8}{resultado['tokens_total']:>9}")
    total = sum(r["tokens_total"] for r in resultados)
    print("-" * 84)
    print(f"{'total dos quatro cenários':<48}{'':>9}{'':>10}{'':>8}{total:>9}")
    print()
    print("O que pesa em cada requisição (tokens de entrada por chamada):")
    for resultado in resultados:
        print(f"  {resultado['cenario']}: {[r['tokens'] for r in resultado['por_requisicao']]}")


if __name__ == "__main__":
    main()
