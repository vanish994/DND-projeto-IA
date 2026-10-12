"""Regressões da auditoria: ausência de efeito nunca vira sucesso silencioso."""
import copy
import unittest

from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine
from rule_engine.economy import resolver_sintonizacao
from rule_engine.spells import mecanica_de_magia, resolver_magia, suporte_magia


class MecanicasCorrigidasTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ.__new__(DeepSeekMJ)
        self.mj.engine = build_default_engine()
        self.ficha = {
            'id': 'p1', 'classe': 'mago', 'nivel': 9,
            'atributos': {'inteligencia': 16},
            'conjuracao': {'truques': ['Raio Místico', 'Rajada de Veneno', 'Trovão', 'Bolha Ácida'],
                          'magias_preparadas': ['Contramagia', 'Dissipar Magia', 'Reviver os Mortos', 'Bola de Fogo'],
                          'espacos_totais': {'3': 2, '5': 1}, 'espacos_restantes': {'3': 2, '5': 1}},
        }

    def test_sem_mecanica_nao_conjura_nem_gasta_espacos(self):
        for nome in ['Contramagia', 'Dissipar Magia', 'Reviver os Mortos', 'Raio Místico']:
            with self.subTest(magia=nome):
                original = copy.deepcopy(self.ficha)
                updates = []
                result = self.mj._tool('resolver_regra', {'fatos': {'type': 'spell', 'magia': nome}},
                                       [self.ficha], on_character_update=updates.append)
                self.assertEqual(result['resultado'], 'nao_implementado')
                self.assertEqual(self.ficha, original)
                self.assertEqual(updates, [])

    def test_truques_escalam_sem_espaco(self):
        for nome, dado in [('Rajada de Veneno', 12), ('Trovão', 6), ('Bolha Ácida', 6)]:
            for nivel, quantidade in [(1, 1), (4, 1), (5, 2), (11, 3), (17, 4)]:
                with self.subTest(magia=nome, nivel=nivel):
                    m = mecanica_de_magia(nome, nivel_personagem=nivel)
                    self.assertEqual(m['dados_dano'], f'{quantidade}d{dado}')
            self.assertEqual(resolver_magia({'magia': nome})['resultado'], 'conjurada')
            self.assertEqual(resolver_magia({'magia': nome, 'espaco': 1})['resultado'], 'bloqueado')

    def test_componentes_do_trovao(self):
        self.assertEqual(resolver_magia({'magia': 'Trovão', 'componentes_disponiveis': ['S']})['resultado'], 'conjurada')
        self.assertEqual(resolver_magia({'magia': 'Trovão', 'componentes_disponiveis': ['V']})['resultado'], 'bloqueado')

    def test_mecanicas_conferidas_com_phb_2024(self):
        veneno = mecanica_de_magia('Rajada de Veneno')
        self.assertEqual(veneno['tipo'], 'ataque_magico')
        self.assertEqual(veneno['alcance_pes'], 30)
        trovao = mecanica_de_magia('Trovão')
        self.assertEqual(trovao['salvaguarda'], 'constituicao')
        self.assertEqual(trovao['area']['forma'], 'emanacao')
        self.assertFalse(trovao['sucesso_metade'])
        bolha = mecanica_de_magia('Bolha Ácida')
        self.assertEqual(bolha['salvaguarda'], 'destreza')
        self.assertEqual(bolha['tipo'], 'dano_multialvo')
        self.assertEqual(bolha['alvos_maximos'], 2)
        self.assertNotIn('area', bolha)
        self.assertFalse(bolha['sucesso_metade'])

    def test_dano_sem_magia_registrada_bloqueado(self):
        self.ficha['conjuracao']['magias_preparadas'] = []
        r = self.mj._preparar_dano_de_magia({'magia': 'Bola de Fogo'}, self.ficha)
        self.assertEqual(r['motivo'], 'magia_nao_registrada_na_ficha')

    def test_dano_sem_ficha_bloqueado(self):
        r = self.mj._preparar_dano_de_magia({'magia': 'Bola de Fogo'}, None)
        self.assertEqual(r['motivo'], 'personagem_ausente_ou_nao_identificado')

    def test_dano_rejeita_espacos_invalidos(self):
        for espaco in [0, 2, 10, 'abc']:
            r = self.mj._preparar_dano_de_magia({'magia': 'Bola de Fogo', 'espaco': espaco}, self.ficha)
            self.assertEqual(r['resultado'], 'bloqueado')
        r = self.mj._preparar_dano_de_magia({'magia': 'Bola de Fogo', 'espaco': 4}, self.ficha)
        self.assertEqual(r['motivo'], 'circulo_indisponivel_na_ficha')
        r = self.mj._preparar_dano_de_magia({'magia': 'Bola de Fogo', 'espaco': 5, 'aumento': -1}, self.ficha)
        self.assertEqual(r['resultado'], 'bloqueado')

    def test_rolagem_nao_afirma_aplicacao_de_dano(self):
        r = self.mj._tool('resolver_regra', {'fatos': {'type': 'damage', 'magia': 'Trovão', 'seed': 'audit'}}, [self.ficha])
        self.assertEqual(r['dano_expressao'], '2d6')
        self.assertFalse(r['aplicado_ao_alvo'])

    def test_imunidade_a_veneno_no_chat_inclui_cartao_zero(self):
        from unittest.mock import patch
        monster = {'nome': 'Alvo de teste', 'ca': 1, 'imunidades_dano': ['poison']}
        with patch('integrations.deepseek_mj.consultar_monstro', return_value=monster):
            rolls = []
            r = self.mj._tool('resolver_regra', {'fatos': {'type': 'attack', 'magia': 'Rajada de Veneno', 'target_name': monster['nome'], 'roll': 20}}, [self.ficha], on_roll=rolls.append)
        self.assertEqual(r['dano'], 0)
        self.assertEqual(r['defesas_dano']['aplicacao'], 'imunidade')
        # Resultado do ataque mantém dados brutos auditáveis.
        self.assertGreater(sum(r['dados_dano']), 0)
        damage_roll = next(x for x in rolls if x['tipo'] == 'dano')
        self.assertEqual(damage_roll['total'], 0)
        self.assertIsNone(damage_roll['valor'])
        self.assertEqual(damage_roll['motivo'], 'imune ao tipo')

    def test_suporte_distingue_catalogo_e_mapa(self):
        self.assertFalse(suporte_magia('Luz')['mecanica_estruturada'])
        self.assertTrue(suporte_magia('Escudo')['mecanica_estruturada'])
        self.assertFalse(suporte_magia('Escudo')['mapa_tatico'])
        self.assertTrue(suporte_magia('Bolha Acida')['mapa_tatico'])
        self.assertTrue(suporte_magia('Onda Trovejante')['parcial'])

    def test_encerrar_sintonia_remove_item_mesmo_no_limite(self):
        itens = ['anel_de_protecao', 'manto_de_protecao', 'amuleto_de_saude']
        r = resolver_sintonizacao({'item': itens[0], 'acao': 'encerrar', 'sintonizados': itens})
        self.assertEqual(r['resultado'], 'encerrada')
        self.assertEqual(r['sintonizados'], itens[1:])
        self.assertEqual(len(itens), 3)  # não muta os fatos de entrada

    def test_encerrar_sintonia_ausente_bloqueado(self):
        r = resolver_sintonizacao({'item': 'anel_de_protecao', 'acao': 'encerrar', 'sintonizados': []})
        self.assertEqual(r['motivo'], 'item_nao_sintonizado')
