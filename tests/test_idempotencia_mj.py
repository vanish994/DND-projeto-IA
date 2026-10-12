"""Resposta perdida, replay e concorrência sem novo gasto de recurso."""
import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool

from backend import app as backend
from backend.persistencia import RepositorioCampanhas, operacoes_mj
from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine


FICHA = {'nome': 'Tessa', 'classe': 'artifice', 'especie': 'humano', 'nivel': 1,
         'pv_maximo': 10, 'atributos': {'inteligencia': 16},
         'conjuracao': {'truques': ['Raio de Fogo'], 'magias_preparadas': ['Curar Ferimentos'],
                       'espacos_totais': {'1': 2}, 'espacos_restantes': {'1': 2}}}


class MJContado:
    def __init__(self):
        self.chamadas = 0
        self.falhar = False

    def responder(self, texto, historico, personagens, on_character_update, on_roll):
        self.chamadas += 1
        mj = DeepSeekMJ.__new__(DeepSeekMJ)
        mj.engine = build_default_engine()
        mj._tool('resolver_regra', {'fatos': {'type': 'spell', 'magia': 'Curar Ferimentos',
                 'character_id': personagens[0]['id']}}, personagens, on_character_update, on_roll)
        on_roll({'tipo': 'teste', 'valor': 7, 'rolagens': [7], 'total': 9, 'modificador': 2,
                 'seed': f'seed-{self.chamadas}'})
        if self.falhar:
            raise RuntimeError('Provedor indisponível após ferramenta')
        return f'Resposta original {self.chamadas}'


class IdempotenciaMJTests(unittest.TestCase):
    def setUp(self):
        self.db = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=self.db)
        self.cid = self.repo.criar('jogador-idem', 'Teste')['id']
        self.p = self.repo.criar_personagem('jogador-idem', self.cid, {}, copy.deepcopy(FICHA))
        self.mj = MJContado()
        backend.app.dependency_overrides[backend.obter_repositorio] = lambda: self.repo
        backend.app.dependency_overrides[backend.obter_mj] = lambda: self.mj
        self.client = TestClient(backend.app)
        self.log_disabled = backend.logger.disabled
        backend.logger.disabled = True

    def tearDown(self):
        backend.app.dependency_overrides.clear()
        backend.logger.disabled = self.log_disabled
        self.db.dispose()

    def enviar(self, op='envio-1', texto='Conjuro.', jogador='jogador-idem', cid=None):
        payload = {'mensagem': texto}
        if op is not None:
            payload['operacao_id'] = op
        return self.client.post(f'/v1/campanhas/{cid or self.cid}/mensagens',
                                headers={'X-Jogador-Id': jogador}, json=payload)

    def restante(self):
        return self.repo.obter_personagem('jogador-idem', self.cid, self.p['id'])['conjuracao']['espacos_restantes']['1']

    def test_repetir_post_depois_de_resposta_perdida_devolve_resultado_original(self):
        original = self.enviar()
        self.assertEqual(original.status_code, 200, original.text)
        self.mj.falhar = True  # replay não deve sequer chamar a IA indisponível
        replay = self.enviar()
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()['resposta'], original.json()['resposta'])
        self.assertEqual(replay.json()['rolagens'], original.json()['rolagens'])
        self.assertEqual(self.mj.chamadas, 1)
        self.assertEqual(self.restante(), 1)
        self.assertEqual(len(self.repo.mensagens('jogador-idem', self.cid)), 2)

    def test_falha_antes_de_confirmar_permite_tentar_mesma_chave(self):
        self.mj.falhar = True
        self.assertEqual(self.enviar().status_code, 502)
        self.assertIsNone(self.repo.obter_operacao('jogador-idem', self.cid, 'envio-1', 'Conjuro.'))
        self.assertEqual(self.restante(), 2)
        self.mj.falhar = False
        self.assertEqual(self.enviar().status_code, 200)
        self.assertEqual(self.restante(), 1)
        self.assertEqual(len(self.repo.mensagens('jogador-idem', self.cid)), 2)

    def test_mesma_chave_outro_texto_rejeita_sem_chamar_ia(self):
        self.assertEqual(self.enviar().status_code, 200)
        r = self.enviar(texto='Outra ação')
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.mj.chamadas, 1)
        self.assertEqual(self.restante(), 1)

    def test_nova_chave_mesmo_texto_e_acao_nova(self):
        self.assertEqual(self.enviar(op='primeira').status_code, 200)
        self.assertEqual(self.enviar(op='segunda').status_code, 200)
        self.assertEqual(self.mj.chamadas, 2)
        self.assertEqual(self.restante(), 0)
        self.assertEqual(len(self.repo.mensagens('jogador-idem', self.cid)), 4)

    def test_chave_nao_expoe_resultado_a_outro_jogador(self):
        self.assertEqual(self.enviar().status_code, 200)
        self.assertEqual(self.enviar(jogador='outro-jogador').status_code, 404)
        self.assertEqual(self.mj.chamadas, 1)

    def test_mesma_chave_em_campanhas_distintas_nao_colide(self):
        self.assertEqual(self.enviar().status_code, 200)
        outra = self.repo.criar('jogador-idem', 'Outra')['id']
        self.repo.criar_personagem('jogador-idem', outra, {}, copy.deepcopy(FICHA))
        self.assertEqual(self.enviar(cid=outra).status_code, 200)
        self.assertEqual(self.mj.chamadas, 2)

    def test_cliente_antigo_sem_chave_continua_funcionando(self):
        self.assertEqual(self.enviar(op=None).status_code, 200)
        self.assertEqual(self.restante(), 1)

    def test_identificador_invalido_e_rejeitado(self):
        for op in ['', 'espaço não permitido', 'a' * 65]:
            self.assertEqual(self.enviar(op=op).status_code, 422)
        self.assertEqual(self.mj.chamadas, 0)

    def test_erro_de_banco_reverte_tambem_o_registro_da_operacao(self):
        def falhar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('INSERT INTO MENSAGENS'):
                raise RuntimeError('Falha no commit simulado')
        event.listen(self.db, 'before_cursor_execute', falhar)
        try:
            with self.assertRaisesRegex(RuntimeError, 'Falha no commit'):
                self.enviar()
        finally:
            event.remove(self.db, 'before_cursor_execute', falhar)
        self.assertEqual(self.restante(), 2)
        self.assertIsNone(self.repo.obter_operacao('jogador-idem', self.cid, 'envio-1', 'Conjuro.'))
        self.assertEqual(self.enviar().status_code, 200)
        self.assertEqual(self.restante(), 1)

    def test_excluir_campanha_remove_operacoes(self):
        self.enviar()
        self.assertTrue(self.repo.apagar('jogador-idem', self.cid))
        with self.db.connect() as conn:
            self.assertEqual(conn.execute(operacoes_mj.select()).all(), [])

    def test_resultado_pode_ser_repetido_apos_reabrir_banco(self):
        with tempfile.TemporaryDirectory() as path:
            url = 'sqlite:///' + str(Path(path) / 'campanha.db')
            repo = RepositorioCampanhas(url)
            cid = repo.criar('jogador-idem', 'Persistente')['id']
            p = repo.criar_personagem('jogador-idem', cid, {}, copy.deepcopy(FICHA))
            original = backend._responder(self.mj, repo, 'jogador-idem', cid, 'Conjuro.', 'op-reabrir')
            repo.engine.dispose()
            reaberto = RepositorioCampanhas(url)
            try:
                self.mj.falhar = True
                self.assertEqual(backend._responder(self.mj, reaberto, 'jogador-idem', cid, 'Conjuro.', 'op-reabrir'), original)
                self.assertEqual(self.mj.chamadas, 1)
                self.assertEqual(reaberto.obter_personagem('jogador-idem', cid, p['id'])['conjuracao']['espacos_restantes']['1'], 1)
            finally:
                reaberto.engine.dispose()

    def test_banco_existente_ganha_tabela_sem_perder_campanha(self):
        operacoes_mj.drop(self.db)
        RepositorioCampanhas(engine=self.db)
        self.assertIn('operacoes_mj', inspect(self.db).get_table_names())
        self.assertIsNotNone(self.repo.obter('jogador-idem', self.cid))

    def test_duas_confirmacoes_simultaneas_mesma_chave_gastam_uma_vez(self):
        with tempfile.TemporaryDirectory() as path:
            url = 'sqlite:///' + str(Path(path) / 'concorrencia.db')
            repo = RepositorioCampanhas(url)
            cid = repo.criar('jogador-idem', 'Concorrência')['id']
            p = repo.criar_personagem('jogador-idem', cid, {}, copy.deepcopy(FICHA))
            barreira = threading.Barrier(2)
            def antes_de_inserir(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith('INSERT INTO OPERACOES_MJ'):
                    barreira.wait(timeout=10)
            event.listen(repo.engine, 'before_cursor_execute', antes_de_inserir)
            def confirmar(numero):
                ficha = copy.deepcopy(FICHA)
                ficha['conjuracao']['espacos_restantes']['1'] = 1
                return repo.registrar_troca('jogador-idem', cid, 'Conjuro.', f'Resposta {numero}',
                    [{'tipo': 'teste', 'valor': numero}], operacao_id='unica',
                    atualizacoes_ficha={p['id']: ficha}, fichas_esperadas={p['id']: p})
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    a, b = [pool.submit(confirmar, n) for n in (1, 2)]
                    self.assertEqual(a.result(timeout=20), b.result(timeout=20))
                self.assertEqual(len(repo.mensagens('jogador-idem', cid)), 2)
                self.assertEqual(repo.obter_personagem('jogador-idem', cid, p['id'])['conjuracao']['espacos_restantes']['1'], 1)
            finally:
                event.remove(repo.engine, 'before_cursor_execute', antes_de_inserir)
                repo.engine.dispose()
