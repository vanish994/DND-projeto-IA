"""Mapeamento centralizado: exceções de domínio viram respostas HTTP estáveis."""

import unittest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from backend.erros import (
        ConflitoDeOperacao,
        ErroDeProvedor,
        ErroDeValidacao,
        ErroDominio,
        NaoEncontrado,
        ServicoIndisponivel,
        registrar_tratadores_de_erro,
    )

    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - backend opcional fora do CI
    DEPENDENCIAS = False


@unittest.skipUnless(DEPENDENCIAS, "fastapi não instalado")
class MapeamentoErrosDominioTests(unittest.TestCase):
    """Cada exceção de domínio tem status e corpo previsíveis em um só lugar."""

    def setUp(self):
        app = FastAPI()
        registrar_tratadores_de_erro(app)

        @app.get("/erro/validacao")
        def erro_validacao():
            raise ErroDeValidacao("entrada inválida")

        @app.get("/erro/nao-encontrado")
        def erro_nao_encontrado():
            raise NaoEncontrado("recurso ausente")

        @app.get("/erro/conflito")
        def erro_conflito():
            raise ConflitoDeOperacao("estado mudou")

        @app.get("/erro/conflito-dict")
        def erro_conflito_dict():
            raise ConflitoDeOperacao({"motivo": "turno_de_outra_criatura"})

        @app.get("/erro/provedor")
        def erro_provedor():
            raise ErroDeProvedor("falha temporária")

        @app.get("/erro/indisponivel")
        def erro_indisponivel():
            raise ServicoIndisponivel("sem chave configurada")

        @app.get("/erro/desconhecido")
        def erro_desconhecido():
            raise ErroDominio("caso genérico")

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_erro_de_validacao_vira_422(self):
        resposta = self.client.get("/erro/validacao")
        self.assertEqual(resposta.status_code, 422)
        self.assertEqual(resposta.json(), {"detail": "entrada inválida"})

    def test_nao_encontrado_vira_404(self):
        resposta = self.client.get("/erro/nao-encontrado")
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json(), {"detail": "recurso ausente"})

    def test_conflito_vira_409_com_mensagem(self):
        resposta = self.client.get("/erro/conflito")
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.json(), {"detail": "estado mudou"})

    def test_conflito_preserva_detail_estruturado(self):
        resposta = self.client.get("/erro/conflito-dict")
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(resposta.json(), {"detail": {"motivo": "turno_de_outra_criatura"}})

    def test_erro_de_provedor_vira_502(self):
        resposta = self.client.get("/erro/provedor")
        self.assertEqual(resposta.status_code, 502)
        self.assertEqual(resposta.json(), {"detail": "falha temporária"})

    def test_servico_indisponivel_vira_503(self):
        resposta = self.client.get("/erro/indisponivel")
        self.assertEqual(resposta.status_code, 503)
        self.assertEqual(resposta.json(), {"detail": "sem chave configurada"})

    def test_erro_dominio_generico_vira_500(self):
        resposta = self.client.get("/erro/desconhecido")
        self.assertEqual(resposta.status_code, 500)
        self.assertEqual(resposta.json(), {"detail": "caso genérico"})


@unittest.skipUnless(DEPENDENCIAS, "fastapi não instalado")
class ContratoHttpPreservadoTests(unittest.TestCase):
    """O contrato das rotas reais continua com o formato {"detail": ...}."""

    def setUp(self):
        from backend import app as backend_app
        from backend.dependencies import obter_mj, obter_repositorio

        class RepositorioFalso:
            def obter(self, jogador, campanha_id):
                return None

            def listar_personagens(self, jogador, campanha_id):
                return []

        backend_app.app.dependency_overrides[obter_repositorio] = lambda: RepositorioFalso()
        backend_app.app.dependency_overrides[obter_mj] = lambda: None
        self.client = TestClient(backend_app.app, raise_server_exceptions=False)

    def tearDown(self):
        from backend import app as backend_app

        backend_app.app.dependency_overrides.clear()

    def test_campanha_inexistente_responde_404_com_detail(self):
        resposta = self.client.get("/v1/campanhas/nao-existe", headers={"X-Jogador-Id": "j"})
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(resposta.json(), {"detail": "Campanha não encontrada"})


if __name__ == "__main__":
    unittest.main()
