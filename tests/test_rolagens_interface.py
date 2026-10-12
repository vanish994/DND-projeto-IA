"""Rolagens do motor expostas para a animação de dado da interface.

O motor continua sendo a única fonte do d20: estes testes garantem que a
normalização copia valor, modificador, total, CD/CA e veredito sem recalcular
nada e que a resposta da API inclui a lista de rolagens.
"""
import unittest

from integrations.deepseek_mj import DeepSeekMJ, normalizar_rolagem
from rule_engine import build_default_engine

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - backend opcional fora do CI
    DEPENDENCIAS = False


class NormalizacaoDeRolagemTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_default_engine()
        self.personagens = [{"id": "p1", "nome": "Vex"}]

    def test_teste_de_habilidade_leva_d20_cd_e_veredito(self):
        fatos = {"type": "ability_check", "ability": "carisma", "skill": "persuasao", "modifier": 5, "dc": 15}
        resultado = self.engine.evaluate({**fatos, "character_id": "p1"}).outcome
        rolagem = normalizar_rolagem(resultado, {**fatos, "character_id": "p1"}, self.personagens)
        self.assertEqual(rolagem["tipo"], "teste")
        self.assertEqual(rolagem["dado"], "d20")
        self.assertEqual(rolagem["valor"], resultado["roll"])
        self.assertEqual(rolagem["total"], resultado["roll"] + 5)
        self.assertEqual(rolagem["dificuldade"], 15)
        self.assertEqual(rolagem["dificuldade_tipo"], "cd")
        self.assertEqual(rolagem["rotulo"], "Teste de Persuasão (Carisma)")
        self.assertEqual(rolagem["personagem"], "Vex")
        self.assertEqual(rolagem["origem"], "rule_engine")
        self.assertIn(rolagem["resultado"], {"sucesso", "falha"})

    def test_ataque_marca_ca_critico_e_dano_previsto(self):
        fatos = {
            "type": "attack", "modifier": 6, "target_ac": 15, "character_id": "p1",
            "weapon": "Espada Longa", "target_name": "Goblin",
            "weapon_damage": "1d8", "damage_modifier": 4, "damage_type": "cortante",
        }
        resultado = self.engine.evaluate(fatos).outcome
        rolagem = normalizar_rolagem(resultado, fatos, self.personagens)
        self.assertEqual(rolagem["tipo"], "ataque")
        self.assertEqual(rolagem["dificuldade"], 15)
        self.assertEqual(rolagem["dificuldade_tipo"], "ca")
        self.assertEqual(rolagem["alvo"], "Goblin")
        self.assertEqual(rolagem["rotulo"], "Ataque com Espada Longa contra Goblin")
        self.assertEqual(rolagem["resultado"], "acerto" if resultado["result"] == "hit" else "erro")
        self.assertEqual(rolagem["sucesso"], resultado["result"] == "hit")
        self.assertEqual(rolagem["dano"]["expressao"], "1d8")
        self.assertEqual(rolagem["dano"]["modificador"], 4)

    def test_vantagem_reproduz_todos_os_d20_rolados(self):
        fatos = {"type": "initiative", "modifier": 3, "advantage": True, "character_id": "p1"}
        resultado = self.engine.evaluate(fatos).outcome
        rolagem = normalizar_rolagem(resultado, fatos, self.personagens)
        self.assertEqual(rolagem["tipo"], "iniciativa")
        self.assertEqual(len(rolagem["rolagens"]), 2)
        self.assertEqual(rolagem["valor"], max(rolagem["rolagens"]))
        self.assertTrue(rolagem["vantagem"])
        self.assertFalse(rolagem["desvantagem"])

    def test_sem_rolagem_nao_gera_registro(self):
        self.assertIsNone(normalizar_rolagem({"type": "bestiary", "resultado": "ok"}, {"operacao": "sugerir"}))

    def test_dados_de_dano_tambem_sao_animaveis(self):
        fatos = {"type": "damage", "damage_dice": [5, 3], "damage_modifier": 4, "critical": False}
        resultado = self.engine.evaluate(fatos).outcome
        rolagem = normalizar_rolagem(resultado, {**fatos, "weapon": "Espada Longa"})
        self.assertEqual(rolagem["tipo"], "dano")
        self.assertEqual(rolagem["rolagens"], [5, 3])
        self.assertEqual(rolagem["total"], 12)
        self.assertEqual(rolagem["expressao"], "2d6 + 4")


class _MJFalsoRolagens:
    """MJ de teste que rola pelo motor e aciona o callback da interface."""

    def __init__(self, rolagens):
        self.rolagens = rolagens

    def responder(self, texto, historico=None, personagens=None, on_character_update=None, on_roll=None):
        for rolagem in self.rolagens:
            if on_roll is not None:
                on_roll(rolagem)
        return "O dado foi rolado pelo motor."


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class BackendRolagensTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        self.rolagem = {
            "tipo": "teste", "dado": "d20", "lados": 20, "valor": 14, "rolagens": [14],
            "modificador": 5, "total": 19, "dificuldade": 15, "dificuldade_tipo": "cd",
            "resultado": "sucesso", "sucesso": True, "rotulo": "Teste de Persuasão (Carisma)",
        }
        self.mj = _MJFalsoRolagens([self.rolagem])
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        backend_app.app.dependency_overrides[backend_app.obter_mj] = lambda: self.mj
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-rolagens"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Dados"}, headers=self.headers).json()["id"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def _conferir_rolagem(self, rolagem: dict) -> None:
        for chave, valor in self.rolagem.items():
            self.assertEqual(rolagem[chave], valor, chave)
        self.assertEqual(rolagem["origem"], "rule_engine")

    def test_mensagem_devolve_e_persiste_rolagens(self):
        resposta = self.client.post(f"/v1/campanhas/{self.cid}/mensagens", json={"mensagem": "Tento convencer."}, headers=self.headers)
        self.assertEqual(resposta.status_code, 200)
        corpo = resposta.json()
        self.assertEqual(len(corpo["rolagens"]), 1)
        self._conferir_rolagem(corpo["rolagens"][0])
        detalhe = self.client.get(f"/v1/campanhas/{self.cid}", headers=self.headers).json()
        self._conferir_rolagem(detalhe["mensagens"][-1]["rolagens"][0])
        self.assertEqual(detalhe["mensagens"][0]["rolagens"], [])

    def test_rota_legada_tambem_entrega_rolagens(self):
        resposta = self.client.post("/v1/mj/mensagem", json={"sessao_id": self.cid, "mensagem": "Tento de novo."}, headers=self.headers)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()["rolagens"]), 1)
        self._conferir_rolagem(resposta.json()["rolagens"][0])

    def test_coluna_nova_e_criada_em_banco_antigo(self):
        from sqlalchemy import text

        with self.repo.engine.begin() as conn:
            conn.execute(text("ALTER TABLE mensagens RENAME TO mensagens_antigas"))
            conn.execute(text("CREATE TABLE mensagens (id INTEGER PRIMARY KEY, campanha_id VARCHAR(64), papel VARCHAR(16), conteudo TEXT, criada_em DATETIME)"))
        RepositorioCampanhas(engine=self.repo.engine)
        resposta = self.client.post(f"/v1/campanhas/{self.cid}/mensagens", json={"mensagem": "Depois da migração."}, headers=self.headers)
        self.assertEqual(resposta.status_code, 200)


class ToolRegistraRolagemTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ.__new__(DeepSeekMJ)
        self.mj.engine = build_default_engine()
        self.personagem = {
            "id": "hero-1", "nome": "Heroi", "classe": "guerreiro", "nivel": 1,
            "atributos": {"forca": 16, "destreza": 12, "constituicao": 14, "inteligencia": 10, "sabedoria": 10, "carisma": 10},
            "bonus_proficiencia": 2, "pericias": ["atletismo"],
            "equipamento": {"arma": "Espada Longa", "armadura": None, "escudo": False},
        }

    def test_tool_entrega_a_rolagem_ao_callback(self):
        coletadas = []
        resultado = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "ability_check", "skill": "atletismo", "dc": 12}},
            [self.personagem], None, lambda rolagem: coletadas.append(rolagem),
        )
        self.assertEqual(len(coletadas), 1)
        rolagem = coletadas[0]
        self.assertEqual(rolagem["tipo"], "teste")
        self.assertEqual(rolagem["valor"], resultado["roll"])
        self.assertEqual(rolagem["dificuldade"], 12)
        self.assertEqual(self.mj.ultimas_rolagens, coletadas)

    def test_bestiario_nao_registra_rolagem(self):
        coletadas = []
        self.mj._tool("consultar_monstro", {"nome": "Goblin"}, [self.personagem], None, coletadas.append)
        self.assertEqual(coletadas, [])

    def test_salvaguarda_sem_d20_e_rolada_pelo_motor(self):
        coletadas = []
        resultado = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "saving_throw", "ability": "constituicao", "dc": 13}},
            [self.personagem], None, coletadas.append,
        )
        self.assertEqual(resultado["status"], "resolved")
        self.assertEqual(resultado["type"], "saving_throw")
        self.assertEqual(len(coletadas), 1)
        self.assertEqual(coletadas[0]["tipo"], "salvaguarda")
        self.assertEqual(coletadas[0]["seed"], resultado["seed"])
        self.assertEqual(coletadas[0]["dificuldade"], 13)

    def test_salvaguarda_com_d20_informado_mantem_resolvedor_completo(self):
        coletadas = []
        resultado = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "saving_throw_check", "ability": "constituicao", "roll": 12, "dc": 13, "modifier": 99}},
            [self.personagem], None, coletadas.append,
        )
        self.assertEqual(resultado["resultado"], "sucesso")
        self.assertEqual(resultado["modifier_source"], "ficha_autoritativa")
        self.assertEqual(coletadas[0]["valor"], 12)
        self.assertEqual(coletadas[0]["total"], resultado["total"])


if __name__ == "__main__":
    unittest.main()
