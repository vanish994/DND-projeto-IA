import os
import unittest
from unittest import mock

try:
    from fastapi import HTTPException
    from fastapi.testclient import TestClient
    from sqlalchemy.pool import StaticPool
    from sqlalchemy import create_engine

    from backend import app as backend_app
    from backend.limite_taxa import LimitadorTaxa, limitador_padrao
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover
    DEPENDENCIAS = False


class RelogioFalso:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class LimitadorTaxaUnitTests(unittest.TestCase):
    def test_bloqueia_apos_o_maximo_e_informa_espera(self):
        relogio = RelogioFalso()
        lim = LimitadorTaxa(maximo=2, janela_segundos=60, relogio=relogio)
        lim.verificar("a")
        relogio.t += 10
        lim.verificar("a")
        relogio.t += 5
        with self.assertRaises(HTTPException) as ctx:
            lim.verificar("a")
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.headers["Retry-After"], "45")

    def test_janela_desliza_e_libera_novas_requisicoes(self):
        relogio = RelogioFalso()
        lim = LimitadorTaxa(maximo=1, janela_segundos=60, relogio=relogio)
        lim.verificar("a")
        relogio.t += 59
        with self.assertRaises(HTTPException):
            lim.verificar("a")
        relogio.t += 1
        lim.verificar("a")

    def test_chaves_sao_independentes(self):
        lim = LimitadorTaxa(maximo=1, janela_segundos=60, relogio=RelogioFalso())
        lim.verificar("a")
        lim.verificar("b")
        with self.assertRaises(HTTPException):
            lim.verificar("a")

    def test_reiniciar_limpa_contagem(self):
        lim = LimitadorTaxa(maximo=1, janela_segundos=60, relogio=RelogioFalso())
        lim.verificar("a")
        lim.reiniciar()
        lim.verificar("a")

    def test_parametros_invalidos_sao_rejeitados(self):
        with self.assertRaises(ValueError):
            LimitadorTaxa(maximo=0)
        with self.assertRaises(ValueError):
            LimitadorTaxa(janela_segundos=0)

    def test_configuracao_por_ambiente_com_padrao_seguro(self):
        with mock.patch.dict(os.environ, {"MJ_LIMITE_REQUISICOES": "5", "MJ_LIMITE_JANELA_SEGUNDOS": "120"}):
            lim = limitador_padrao()
        self.assertEqual(lim._maximo, 5)
        self.assertEqual(lim._janela, 120.0)
        with mock.patch.dict(os.environ, {"MJ_LIMITE_REQUISICOES": "abc", "MJ_LIMITE_JANELA_SEGUNDOS": "-1"}):
            lim = limitador_padrao()
        self.assertEqual(lim._maximo, 30)
        self.assertEqual(lim._janela, 60.0)


class MJFalsoTaxa:
    def responder(self, texto, historico=None):
        return f"MJ: {texto}"


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy não instalados")
class LimiteNasRotasDoMJTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        self.original = backend_app._limitador_mj
        backend_app._limitador_mj = LimitadorTaxa(maximo=2, janela_segundos=60, relogio=RelogioFalso())
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        backend_app.app.dependency_overrides[backend_app.obter_mj] = lambda: MJFalsoTaxa()
        self.client = TestClient(backend_app.app)
        self.cabecalho = {"X-Jogador-Id": "jogador-taxa"}

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()
        backend_app._limitador_mj = self.original

    def test_rota_legado_bloqueia_com_429(self):
        for _ in range(2):
            r = self.client.post("/v1/mj/mensagem", json={"sessao_id": "s1", "mensagem": "oi"}, headers=self.cabecalho)
            self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post("/v1/mj/mensagem", json={"sessao_id": "s1", "mensagem": "oi"}, headers=self.cabecalho)
        self.assertEqual(r.status_code, 429)
        self.assertIn("Retry-After", r.headers)

    def test_rota_de_campanha_bloqueia_com_429(self):
        campanha = self.repo.criar("jogador-taxa", "Campanha de teste")["id"]
        url = f"/v1/campanhas/{campanha}/mensagens"
        for _ in range(2):
            r = self.client.post(url, json={"mensagem": "oi"}, headers=self.cabecalho)
            self.assertEqual(r.status_code, 200, r.text)
        r = self.client.post(url, json={"mensagem": "oi"}, headers=self.cabecalho)
        self.assertEqual(r.status_code, 429)

    def test_limite_e_por_jogador(self):
        for _ in range(2):
            self.client.post("/v1/mj/mensagem", json={"sessao_id": "s1", "mensagem": "oi"}, headers=self.cabecalho)
        r = self.client.post("/v1/mj/mensagem", json={"sessao_id": "s2", "mensagem": "oi"},
                             headers={"X-Jogador-Id": "outro-jogador"})
        self.assertEqual(r.status_code, 200, r.text)


if __name__ == "__main__":
    unittest.main()
