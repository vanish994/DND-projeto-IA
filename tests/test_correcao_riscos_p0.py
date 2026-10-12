"""Prova de correção dos riscos reproduzidos na auditoria, sem IA externa."""
import copy
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from backend import app as backend
from backend.persistencia import RepositorioCampanhas, ConflitoEstadoCampanha
from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine
from rule_engine.class_features import resolver_caracteristica
from rule_engine.class_progression import FEATURES_BY_CLASS


class MJComFerramenta:
    def __init__(self, falhar=False, repeticoes=1, concorrente=None):
        self.falhar = falhar
        self.repeticoes = repeticoes
        self.concorrente = concorrente

    def responder(self, texto, historico, personagens, on_character_update, on_roll):
        mj = DeepSeekMJ.__new__(DeepSeekMJ)
        mj.engine = build_default_engine()
        for _ in range(self.repeticoes):
            mj._tool('resolver_regra', {'fatos': {'type': 'spell', 'magia': 'Curar Ferimentos',
                     'character_id': personagens[0]['id']}}, personagens, on_character_update, on_roll)
        if self.concorrente:
            self.concorrente()
        if self.falhar:
            raise RuntimeError('Falha simulada após uso da ferramenta')
        return 'Conjuração registrada.'


class PersistenciaAtomicaTests(unittest.TestCase):
    def setUp(self):
        self.db = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=self.db)
        self.cid = self.repo.criar('auditoria-p0', 'Teste')['id']
        self.ficha = {'nome': 'Tessa', 'classe': 'artifice', 'especie': 'humano', 'nivel': 1,
                      'pv_maximo': 10, 'atributos': {'inteligencia': 16},
                      'conjuracao': {'truques': ['Raio de Fogo'], 'magias_preparadas': ['Curar Ferimentos'],
                                    'espacos_totais': {'1': 2}, 'espacos_restantes': {'1': 2}}}
        self.p = self.repo.criar_personagem('auditoria-p0', self.cid, {}, self.ficha)
        self.mj = MJComFerramenta()
        backend.app.dependency_overrides[backend.obter_repositorio] = lambda: self.repo
        backend.app.dependency_overrides[backend.obter_mj] = lambda: self.mj
        self.client = TestClient(backend.app)
        self.log_disabled = backend.logger.disabled
        backend.logger.disabled = True

    def tearDown(self):
        backend.app.dependency_overrides.clear()
        backend.logger.disabled = self.log_disabled
        self.db.dispose()

    def enviar(self):
        return self.client.post(f'/v1/campanhas/{self.cid}/mensagens',
                                headers={'X-Jogador-Id': 'auditoria-p0'}, json={'mensagem': 'Conjuro.'})

    def atual(self):
        return self.repo.obter_personagem('auditoria-p0', self.cid, self.p['id'])

    def test_falha_apos_ferramenta_e_repeticao_nao_gastam_espacos(self):
        self.mj.falhar = True
        for _ in range(2):
            self.assertEqual(self.enviar().status_code, 502)
            self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 2})
            self.assertEqual(self.repo.mensagens('auditoria-p0', self.cid), [])
        self.mj.falhar = False
        self.assertEqual(self.enviar().status_code, 200)
        self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 1})
        self.assertEqual(len(self.repo.mensagens('auditoria-p0', self.cid)), 2)

    def test_falha_apos_duas_ferramentas_descarta_lote_inteiro(self):
        self.mj.falhar, self.mj.repeticoes = True, 2
        self.assertEqual(self.enviar().status_code, 502)
        self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 2})

    def test_sucesso_confirma_ultimo_estado_das_ferramentas(self):
        self.mj.repeticoes = 2
        self.assertEqual(self.enviar().status_code, 200)
        self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 0})
        self.assertEqual(len(self.repo.mensagens('auditoria-p0', self.cid)), 2)

    def test_edicao_concorrente_nao_e_sobrescrita_por_resposta_atrasada(self):
        def editar():
            ficha = {**self.ficha, 'nota': 'edição concorrente'}
            self.repo.atualizar_dados_ficha('auditoria-p0', self.cid, self.p['id'], ficha)
        self.mj.concorrente = editar
        r = self.enviar()
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.atual()['nota'], 'edição concorrente')
        self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 2})
        self.assertEqual(self.repo.mensagens('auditoria-p0', self.cid), [])

    def test_falha_ao_gravar_mensagens_desfaz_atualizacao_de_ficha(self):
        def falhar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith('INSERT INTO MENSAGENS'):
                raise RuntimeError('Falha de banco simulada')
        event.listen(self.db, 'before_cursor_execute', falhar)
        try:
            with self.assertRaisesRegex(RuntimeError, 'Falha de banco'):
                self.enviar()
        finally:
            event.remove(self.db, 'before_cursor_execute', falhar)
        self.assertEqual(self.atual()['conjuracao']['espacos_restantes'], {'1': 2})
        self.assertEqual(self.repo.mensagens('auditoria-p0', self.cid), [])

    def test_snapshot_antigo_nao_pode_ser_confirmado_duas_vezes(self):
        nova = copy.deepcopy(self.ficha)
        nova['conjuracao']['espacos_restantes']['1'] = 1
        kwargs = dict(atualizacoes_ficha={self.p['id']: nova}, fichas_esperadas={self.p['id']: self.p})
        self.repo.registrar_troca('auditoria-p0', self.cid, 'Ação', 'Resultado', **kwargs)
        with self.assertRaises(ConflitoEstadoCampanha):
            self.repo.registrar_troca('auditoria-p0', self.cid, 'Ação antiga', 'Resultado antigo', **kwargs)
        self.assertEqual(len(self.repo.mensagens('auditoria-p0', self.cid)), 2)

    def test_commit_persiste_apos_reabrir_banco(self):
        with tempfile.TemporaryDirectory() as path:
            url = 'sqlite:///' + str(Path(path) / 'campanha.sqlite3')
            repo = RepositorioCampanhas(url)
            cid = repo.criar('auditoria-p0', 'Persistente')['id']
            p = repo.criar_personagem('auditoria-p0', cid, {}, self.ficha)
            backend._responder(MJComFerramenta(), repo, 'auditoria-p0', cid, 'Conjuro.')
            repo.engine.dispose()
            reaberto = RepositorioCampanhas(url)
            try:
                self.assertEqual(reaberto.obter_personagem('auditoria-p0', cid, p['id'])['conjuracao']['espacos_restantes'], {'1': 1})
                self.assertEqual(len(reaberto.mensagens('auditoria-p0', cid)), 2)
            finally:
                reaberto.engine.dispose()


class NivelCaracteristicaTests(unittest.TestCase):
    def test_bloqueia_surto_antes_do_nivel_e_libera_no_nivel_correto(self):
        self.assertEqual(resolver_caracteristica({'classe': 'guerreiro', 'nivel': 1, 'recurso': 'surto_de_acao'})['motivo'], 'nivel_insuficiente')
        self.assertEqual(resolver_caracteristica({'classe': 'guerreiro', 'nivel': 2, 'recurso': 'surto_de_acao'})['resultado'], 'resolvido')

    def test_bloqueia_capstone_e_alias_de_artifice(self):
        for classe, recurso, nivel in [('monge', 'corpo_e_mente', 20), ('artifice', 'flash_of_genius', 7), ('artifice', 'soul_of_artifice', 20)]:
            with self.subTest(recurso=recurso):
                r = resolver_caracteristica({'classe': classe, 'nivel': 1, 'recurso': recurso})
                self.assertEqual(r['resultado'], 'bloqueado')
                self.assertEqual(r['nivel_minimo'], nivel)
                self.assertEqual(resolver_caracteristica({'classe': classe, 'nivel': nivel, 'recurso': recurso})['resultado'], 'resolvido')

    def test_toda_caracteristica_catalogada_respeita_primeiro_marco(self):
        for classe, marcos in FEATURES_BY_CLASS.items():
            vistos = set()
            for nivel, nomes in sorted(marcos.items()):
                for recurso in nomes:
                    if recurso in vistos:
                        continue
                    vistos.add(recurso)
                    if nivel > 1:
                        r = resolver_caracteristica({'classe': classe, 'nivel': nivel - 1, 'recurso': recurso})
                        self.assertEqual(r['resultado'], 'bloqueado', (classe, recurso, nivel))

    def test_ia_nao_pode_inventar_classe_nivel_ou_atributo(self):
        mj = DeepSeekMJ.__new__(DeepSeekMJ)
        mj.engine = build_default_engine()
        p = {'id': 'p1', 'classe': 'guerreiro', 'nivel': 1, 'atributos': {'forca': 10}}
        r = mj._tool('resolver_regra', {'fatos': {'type': 'class_feature', 'classe': 'monge',
                     'nivel': 20, 'recurso': 'surto_de_acao', 'character_id': 'p1'}}, [p])
        self.assertEqual(r['motivo'], 'nivel_insuficiente')
        self.assertEqual(r['classe'], 'guerreiro')
        p.update(classe='barbaro', atributos={'destreza': 12, 'constituicao': 14})
        r = mj._tool('resolver_regra', {'fatos': {'type': 'class_feature', 'recurso': 'defesa_sem_armadura',
                     'destreza': 30, 'constituicao': 30}}, [p])
        self.assertEqual(r['ca'], 13)

    def test_sem_ficha_bloqueia_e_asi_nao_contorna_nivel(self):
        mj = DeepSeekMJ.__new__(DeepSeekMJ)
        mj.engine = build_default_engine()
        self.assertEqual(mj._tool('resolver_regra', {'fatos': {'type': 'class_feature', 'recurso': 'surto_de_acao'}}, [])['resultado'], 'bloqueado')
        self.assertEqual(resolver_caracteristica({'classe': 'guerreiro', 'nivel': 1, 'recurso': 'asi', 'atributo': 'forca'})['motivo'], 'nivel_insuficiente')
