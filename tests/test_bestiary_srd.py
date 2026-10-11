"""Regressões da integração de blocos estruturados do SRD 5.2.1."""
import json
from pathlib import Path
import unittest

from rule_engine.bestiary import BESTIARIO, consultar_monstro
from backend.app import _aplicar_defesas_monstro, _extrair_ataques_monstro


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

    def test_ataques_srd_52_sao_extraidos_sem_inventar_estatisticas(self):
        monstro = consultar_monstro("Goblin")
        ataques = _extrair_ataques_monstro(monstro)
        nomes = {a["nome"] for a in ataques}
        self.assertIn("Scimitar", nomes)
        self.assertIn("Shortbow", nomes)
        arco = next(a for a in ataques if a["nome"] == "Shortbow")
        self.assertEqual(arco["bonus_ataque"], 4)
        self.assertEqual(arco["dano"], "1d6+2")
        self.assertEqual(arco["alcance_minimo_distancia"], 80)
        self.assertEqual(arco["alcance_maximo_distancia"], 320)

    def test_resistencias_imunidades_e_vulnerabilidades_de_dano(self):
        resistente = {"resistencias_dano": ["piercing"]}
        imune = {"imunidades_dano": ["poison"]}
        vulneravel = {"vulnerabilidades_dano": ["bludgeoning"]}
        self.assertEqual(_aplicar_defesas_monstro(7, "perfurante", resistente)["dano"], 3)
        self.assertEqual(_aplicar_defesas_monstro(7, "veneno", imune)["dano"], 0)
        self.assertEqual(_aplicar_defesas_monstro(7, "contundente", vulneravel)["dano"], 14)

    def test_resistencia_e_vulnerabilidade_do_mesmo_tipo_se_cancelam(self):
        monstro = {
            "resistencias_dano": ["piercing"],
            "vulnerabilidades_dano": ["perfurante"],
        }
        resultado = _aplicar_defesas_monstro(7, "piercing", monstro)
        self.assertEqual(resultado["dano"], 7)
        self.assertEqual(resultado["aplicacao"], "resistencia_e_vulnerabilidade_canceladas")

    def test_ataque_com_dano_fixo_e_extraido_sem_inventar_dados(self):
        from backend.app import _extrair_ataques_monstro

        monstro = {
            "acoes": [{
                "nome": "Touch",
                "desc": "Melee Spell Attack: +4 to hit, reach 5 ft., one target. Hit: 5 necrotic damage."
            }]
        }
        ataques = _extrair_ataques_monstro(monstro)
        self.assertEqual(len(ataques), 1)
        self.assertEqual(ataques[0]["dano"], "5")
        self.assertTrue(ataques[0]["dano_fixo"])
        self.assertEqual(ataques[0]["dano_medio"], 5)
        self.assertEqual(ataques[0]["tipo_dano"], "necrotic")

    def test_multiataque_expande_apenas_sequencias_sem_alternativas(self):
        from backend.app import _expandir_multiataque

        dretch = consultar_monstro("Dretch")
        ataques_dretch = _extrair_ataques_monstro(dretch)
        self.assertEqual(
            _expandir_multiataque(dretch, ataques_dretch),
            ["Bite", "Claws"],
        )

        ape = consultar_monstro("Ape")
        ataques_ape = _extrair_ataques_monstro(ape)
        self.assertEqual(
            _expandir_multiataque(ape, ataques_ape),
            ["Fist", "Fist"],
        )

    def test_multiataque_com_alternativas_nao_escolhe_sem_instrucao(self):
        from backend.app import _expandir_multiataque

        centauro = consultar_monstro("Centaur")
        ataques = _extrair_ataques_monstro(centauro)
        self.assertIsNone(_expandir_multiataque(centauro, ataques))

    def test_multiaction_esta_preservada_no_bloco_mesmo_sem_resolucao_automatica(self):
        monstro = consultar_monstro("Aboleth")
        multiattack = next((a for a in monstro["acoes"] if a["nome"] == "Multiattack"), None)
        self.assertIsNotNone(multiattack)
        self.assertIn("three tentacle attacks", multiattack["desc"].casefold())


if __name__ == "__main__":
    unittest.main()
