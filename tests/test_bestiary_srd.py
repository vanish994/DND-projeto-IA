"""Regressões da integração de blocos estruturados do SRD 5.2.1."""

import json
import unittest
from pathlib import Path

from rule_engine.bestiary import BESTIARIO, consultar_monstro


class BestiarySrdIntegrationTests(unittest.TestCase):
    def test_todos_os_registros_da_fonte_estao_no_catalogo(self):
        path = Path(__file__).resolve().parents[1] / "rule_engine" / "srd_monsters_data.json"
        fonte = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(fonte["count"], 322)
        self.assertIn("CC BY 4.0", fonte["_license"])
        nomes = {m["nome"].casefold() for m in BESTIARIO}
        ausentes = [m["name"] for m in fonte["monsters"] if m["name"].casefold() not in nomes]
        self.assertEqual(ausentes, [])

    def test_blocos_de_monstros_comuns_tem_dados_mecanicos_estruturados(self):
        for nome in ("Aboleth", "Goblin", "Wolf", "Zombie", "Tarrasque"):
            with self.subTest(monstro=nome):
                monstro = consultar_monstro(nome)
                self.assertIsNotNone(monstro)
                self.assertTrue(monstro["bloco_srd"])
                self.assertTrue(monstro["atributos"])
                self.assertTrue(monstro["acoes"])
                self.assertGreater(monstro["ca"], 0)
                self.assertGreater(monstro["pv"], 0)

    def test_multiaction_esta_preservada_no_bloco_mesmo_sem_resolucao_automatica(self):
        monstro = consultar_monstro("Aboleth")
        multiattack = next((a for a in monstro["acoes"] if a["nome"] == "Multiattack"), None)
        self.assertIsNotNone(multiattack)
        self.assertIn("three tentacle attacks", multiattack["desc"].casefold())


if __name__ == "__main__":
    unittest.main()
