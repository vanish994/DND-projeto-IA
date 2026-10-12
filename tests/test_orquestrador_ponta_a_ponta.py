"""Ponta a ponta: navegador → backend → MJ → orquestrador → motor → banco.

Este é o teste que o projeto precisava para confiar na camada intermediária. A
IA é falsa (roteirizada), mas tudo o mais é real: o MJ de produção, o
Orquestrador de Ações, o Rule Engine, a persistência e a rota HTTP.

O que ele prova:
- a rolagem que chega ao navegador foi gerada pelo motor;
- o espaço de magia gasto foi gravado no banco, não contado pela IA;
- repetir a mesma operação não gasta recurso duas vezes.
"""

import copy
import json
import logging
import unittest

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend import app as backend
    from backend.persistencia import RepositorioCampanhas

    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - dependências opcionais fora do CI
    DEPENDENCIAS = False

from integrations.deepseek_mj import DeepSeekMJ

FICHA = {
    "nome": "Tessa",
    "classe": "feiticeiro",
    "especie": "humano",
    "nivel": 3,
    "pv_maximo": 18,
    "atributos": {"carisma": 16, "constituicao": 14, "destreza": 14},
    "conjuracao": {
        "truques": ["Raio de Fogo"],
        "magias_preparadas": ["Bola de Fogo"],
        "espacos_totais": {"3": 2},
        "espacos_restantes": {"3": 2},
    },
}


class _Ferramenta:
    def __init__(self, nome, argumentos, identificador="call-1"):
        self.id = identificador
        self.function = type("Funcao", (), {"name": nome, "arguments": json.dumps(argumentos, ensure_ascii=False)})()


class _Mensagem:
    def __init__(self, content=None, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls or []


class _Resposta:
    def __init__(self, mensagem):
        self.choices = [type("Escolha", (), {"message": mensagem})()]


class _ClienteRoteirizado:
    """Cliente de LLM falso: uma mensagem roteirizada por chamada."""

    def __init__(self, mensagens):
        self.pendentes = list(mensagens)
        self.requisicoes = []
        self.chat = type("Chat", (), {"completions": self})()

    def create(self, **parametros):
        self.requisicoes.append(parametros)
        return _Resposta(self.pendentes.pop(0))


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class FluxoCompletoTests(unittest.TestCase):
    def setUp(self):
        self.db = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=self.db)
        self.jogador = "jogador-ponta-a-ponta"
        self.cid = self.repo.criar(self.jogador, "Forja")["id"]
        self.personagem = self.repo.criar_personagem(self.jogador, self.cid, {}, copy.deepcopy(FICHA))
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        backend.app.dependency_overrides.clear()
        logging.disable(logging.NOTSET)
        self.db.dispose()

    def _mj(self, mensagens):
        cliente = _ClienteRoteirizado(mensagens)
        mj = DeepSeekMJ(client=cliente, model="teste")
        mj.base_url = "https://api.groq.com/openai/v1"
        mj.uses_deepseek_api = False
        backend.app.dependency_overrides[backend.obter_repositorio] = lambda: self.repo
        backend.app.dependency_overrides[backend.obter_mj] = lambda: mj
        self.addCleanup(backend.app.dependency_overrides.clear)
        return cliente

    def _enviar(self, texto, operacao_id):
        return TestClient(backend.app).post(
            f"/v1/campanhas/{self.cid}/mensagens",
            headers={"X-Jogador-Id": self.jogador},
            json={"mensagem": texto, "operacao_id": operacao_id},
        )

    @staticmethod
    def _resultado_da_ferramenta(requisicao):
        """Última resposta de ferramenta enviada ao modelo."""
        for mensagem in reversed(requisicao["messages"]):
            if mensagem.get("role") == "tool":
                return json.loads(mensagem["content"])
        raise AssertionError("a requisição não levou resposta de ferramenta")

    def _espacos(self):
        ficha = self.repo.obter_personagem(self.jogador, self.cid, self.personagem["id"])
        return ficha["conjuracao"]["espacos_restantes"]["3"]

    def test_conjuracao_atravessa_todas_as_camadas_e_persiste_o_gasto(self):
        cliente = self._mj(
            [
                _Mensagem(
                    tool_calls=[
                        _Ferramenta(
                            "resolver_regra",
                            {
                                "fatos": {
                                    "type": "spell",
                                    "character_id": self.personagem["id"],
                                    "magia": "Bola de Fogo",
                                }
                            },
                        )
                    ]
                ),
                _Mensagem(content="A Bola de Fogo explode sobre os inimigos."),
            ]
        )

        resposta = self._enviar("Conjuro Bola de Fogo.", "op-1")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["resposta"], "A Bola de Fogo explode sobre os inimigos.")

        # A IA recebeu de volta o resultado do motor, não um palpite próprio.
        ferramenta = self._resultado_da_ferramenta(cliente.requisicoes[1])
        self.assertEqual(ferramenta["resultado"], "conjurada")
        self.assertEqual(ferramenta["espaco_usado"], 3)
        self.assertEqual(ferramenta["espacos_restantes"], {"3": 1})

        # O estado canônico no banco é a fonte de verdade.
        self.assertEqual(self._espacos(), 1)

    def test_repetir_a_mesma_operacao_nao_gasta_o_espaco_de_novo(self):
        cliente = self._mj(
            [
                _Mensagem(
                    tool_calls=[
                        _Ferramenta(
                            "resolver_regra",
                            {
                                "fatos": {
                                    "type": "spell",
                                    "character_id": self.personagem["id"],
                                    "magia": "Bola de Fogo",
                                }
                            },
                        )
                    ]
                ),
                _Mensagem(content="A Bola de Fogo explode sobre os inimigos."),
            ]
        )
        primeira = self._enviar("Conjuro Bola de Fogo.", "op-repetida")
        self.assertEqual(primeira.status_code, 200, primeira.text)
        self.assertEqual(self._espacos(), 1)

        # Replay da mesma operação: mesma resposta, sem nova chamada à IA e sem novo gasto.
        repetida = self._enviar("Conjuro Bola de Fogo.", "op-repetida")
        self.assertEqual(repetida.status_code, 200, repetida.text)
        self.assertEqual(repetida.json()["resposta"], primeira.json()["resposta"])
        self.assertEqual(repetida.json()["rolagens"], primeira.json()["rolagens"])
        # Duas idas ao modelo na primeira mensagem (ferramenta + narração);
        # o replay não acrescenta nenhuma.
        self.assertEqual(len(cliente.requisicoes), 2, "a IA foi chamada de novo no replay")
        self.assertEqual(self._espacos(), 1)

    def test_magia_de_area_composta_em_unica_rodada_de_ferramenta(self):
        # "Bola de Fogo em dois alvos" em UMA rodada de ferramenta: o fluxo
        # manual equivalente (spell, damage, 2 salvaguardas, narração) seriam
        # 5 chamadas ao modelo — cada uma reenviando o contexto inteiro.
        cliente = self._mj(
            [
                _Mensagem(
                    tool_calls=[
                        _Ferramenta(
                            "resolver_regra",
                            {
                                "fatos": {
                                    "type": "area_spell",
                                    "character_id": self.personagem["id"],
                                    "magia": "Bola de Fogo",
                                    "alvos": ["Goblin", "Zombie"],
                                }
                            },
                        )
                    ]
                ),
                _Mensagem(content="A Bola de Fogo varre a sala; o goblin é engolido pelas chamas."),
            ]
        )

        resposta = self._enviar("Lanço Bola de Fogo no goblin e no zumbi.", "op-area")
        self.assertEqual(resposta.status_code, 200, resposta.text)

        # Duas idas ao modelo (ferramenta + narração), não cinco.
        self.assertEqual(len(cliente.requisicoes), 2, "a operação composta não deveria reenviar o contexto por alvo")

        ferramenta = self._resultado_da_ferramenta(cliente.requisicoes[1])
        self.assertEqual(ferramenta["resultado"], "conjurada")
        self.assertEqual(ferramenta["tipo_resolucao"], "magia_de_area")
        self.assertEqual(ferramenta["espaco_usado"], 3)
        self.assertEqual(len(ferramenta["alvos"]), 2)
        nomes = {alvo["nome"]: alvo for alvo in ferramenta["alvos"]}
        self.assertEqual(nomes["Goblin"]["salvaguarda"]["modificador"], 2)
        self.assertEqual(nomes["Zombie"]["salvaguarda"]["modificador"], -2)
        self.assertIn("dano_aplicado", nomes["Goblin"])

        # O espaço foi gasto uma única vez, com dois alvos.
        self.assertEqual(self._espacos(), 1)

        # Três rolagens do motor chegaram à interface: dano + duas salvaguardas.
        rolagens = resposta.json()["rolagens"]
        self.assertEqual([r["tipo"] for r in rolagens], ["dano", "salvaguarda", "salvaguarda"])
        self.assertTrue(all(r["origem"] == "rule_engine" for r in rolagens))

    def test_teste_de_habilidade_devolve_a_rolagem_do_motor_para_a_interface(self):
        self._mj(
            [
                _Mensagem(
                    tool_calls=[
                        _Ferramenta(
                            "resolver_regra",
                            {
                                "fatos": {
                                    "type": "ability_check",
                                    "character_id": self.personagem["id"],
                                    "skill": "persuasao",
                                    "dc": 12,
                                }
                            },
                        )
                    ]
                ),
                _Mensagem(content="Você empurra a pedra."),
            ]
        )
        resposta = self._enviar("Empurro a pedra.", "op-teste")
        self.assertEqual(resposta.status_code, 200, resposta.text)
        rolagens = resposta.json()["rolagens"]
        self.assertEqual(len(rolagens), 1)
        self.assertEqual(rolagens[0]["tipo"], "teste")
        self.assertEqual(rolagens[0]["dificuldade"], 12)
        self.assertEqual(rolagens[0]["origem"], "rule_engine")

        # Reabrir a campanha devolve a mesma rolagem, sem rolar de novo.
        reaberta = (
            TestClient(backend.app).get(f"/v1/campanhas/{self.cid}", headers={"X-Jogador-Id": self.jogador}).json()
        )
        self.assertEqual(reaberta["mensagens"][-1]["rolagens"], rolagens)


if __name__ == "__main__":
    unittest.main()
