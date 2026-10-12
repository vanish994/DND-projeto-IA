"""Regressões para progressão por classe e alvos de Bolha Ácida."""

import unittest

from rule_engine.class_progression import caracteristicas_no_nivel
from rule_engine.spells import MECANICAS_MAGIA, obter_magia


class ProgressionRegressionTests(unittest.TestCase):
    def test_marcos_de_subclasse_sao_especificos_por_classe(self):
        self.assertIn("Característica de Subclasse", caracteristicas_no_nivel("barbaro", 14))
        self.assertNotIn("Característica de Subclasse", caracteristicas_no_nivel("barbaro", 18))
        self.assertIn("Característica de Subclasse", caracteristicas_no_nivel("guerreiro", 7))
        self.assertNotIn("Característica de Subclasse", caracteristicas_no_nivel("guerreiro", 6))
        self.assertIn("Característica de Subclasse", caracteristicas_no_nivel("ladino", 17))

    def test_marcos_extras_de_asi_para_guerreiro_e_ladino(self):
        self.assertIn("Aumento de Atributo ou Talento", caracteristicas_no_nivel("guerreiro", 6))
        self.assertIn("Aumento de Atributo ou Talento", caracteristicas_no_nivel("guerreiro", 14))
        self.assertIn("Aumento de Atributo ou Talento", caracteristicas_no_nivel("ladino", 10))
        self.assertIn("Dádiva Épica", caracteristicas_no_nivel("ladino", 19))


class AcidSplashRegressionTests(unittest.TestCase):
    def test_bolha_acida_tem_alvos_proximos_e_nao_area_esferica(self):
        magia = obter_magia("Bolha Ácida")
        mecanica = MECANICAS_MAGIA["bolha ácida"]
        self.assertEqual(magia["circulo"], 0)
        self.assertEqual(mecanica["tipo"], "dano_multialvo")
        self.assertEqual(mecanica["alvos_maximos"], 2)
        self.assertEqual(mecanica["distancia_entre_alvos_m"], 1.5)
        self.assertNotIn("area", mecanica)
        self.assertEqual(mecanica["alcance_m"], 18)
        self.assertEqual(mecanica["salvaguarda"], "destreza")
        self.assertFalse(mecanica["sucesso_metade"])


if __name__ == "__main__":
    unittest.main()
