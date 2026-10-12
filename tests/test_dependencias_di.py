"""Injeção de dependências do backend: estado da app e substituição por dublês."""
import unittest

try:
    from fastapi.testclient import TestClient

    from backend import app as backend_app
    from backend.dependencies import Recursos, obter_mj, obter_repositorio
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - backend opcional fora do CI
    DEPENDENCIAS = False


class RepositorioFalso:
    def __init__(self):
        self.listagens = []

    def listar(self, jogador):
        self.listagens.append(jogador)
        return [{
            "id": "c-mock", "titulo": "Campanha mockada",
            "criada_em": "2026-01-01T00:00:00", "atualizada_em": "2026-01-01T00:00:00",
            "ultima_mensagem": None, "total_mensagens": 0,
        }]


class MJFalso:
    def responder(self, texto, historico=None):
        return f"MJ: {texto}"


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy não instalados")
class InjecaoDeDependenciasTests(unittest.TestCase):
    def setUp(self):
        self.recursos_originais = backend_app.app.state.recursos
        # Container novo por teste: o lazy init não pode vazar entre testes.
        backend_app.app.state.recursos = Recursos()
        self.client = TestClient(backend_app.app)

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()
        backend_app.app.state.recursos = self.recursos_originais

    def test_status_responde_sem_instanciar_recursos(self):
        resposta = self.client.get("/v1/status")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["status"], "online")

    def test_repositorio_vem_do_estado_da_app(self):
        repo = RepositorioFalso()
        backend_app.app.state.recursos = Recursos(repositorio=repo)
        resposta = self.client.get("/v1/campanhas", headers={"X-Jogador-Id": "jogador-di"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()[0]["titulo"], "Campanha mockada")
        self.assertEqual(repo.listagens, ["jogador-di"])

    def test_override_de_dependencia_injeta_dubles(self):
        repo = RepositorioFalso()
        backend_app.app.dependency_overrides[obter_repositorio] = lambda: repo
        backend_app.app.dependency_overrides[obter_mj] = lambda: MJFalso()
        resposta = self.client.get("/v1/campanhas", headers={"X-Jogador-Id": "outro"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(len(resposta.json()), 1)
        # O container da app não foi tocado: o override substitui o provider.
        self.assertIsNone(backend_app.app.state.recursos.repositorio)


if __name__ == "__main__":
    unittest.main()
