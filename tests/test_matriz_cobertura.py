import unittest
from collections import Counter

from rule_engine.class_progression import FEATURES_BY_CLASS
from rule_engine.feats import FEATS
from rule_engine.spells import listar_magias
from scripts.gerar_matriz_cobertura import gerar_linhas, normalizar


class MatrizCoberturaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = gerar_linhas()

    def test_inventario_nao_omite_magias_talentos_ou_pares_de_classe(self):
        contagem = Counter(r["familia"] for r in self.rows)
        self.assertEqual(contagem["magia"], len(listar_magias()))
        self.assertEqual(contagem["talento"], len(FEATS))
        self.assertEqual(
            contagem["caracteristica_classe"],
            sum(len({f for fs in niveis.values() for f in fs}) for niveis in FEATURES_BY_CLASS.values()),
        )

    def test_identidades_unicas_e_campos_obrigatorios(self):
        ids = [(r["familia"], r["grupo"], r["recurso"]) for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.rows:
            for campo in ("fonte", "retorno_probe", "integracao", "lacuna", "prioridade"):
                self.assertTrue(row[campo], (row["recurso"], campo))

    def test_rotas_alternativas_nao_sao_perdidas(self):
        row = next(
            r
            for r in self.rows
            if r["familia"] == "caracteristica_classe"
            and r["grupo"] == "barbaro"
            and normalizar(r["recurso"]) == "furia"
        )
        self.assertIn("martial.py::resolver_furia", row["rotas_relacionadas"])
        self.assertEqual(row["integracao"], "nao_comprovada_por_este_inventario")

    def test_resultado_reproduzivel(self):
        self.assertEqual(self.rows, gerar_linhas())
