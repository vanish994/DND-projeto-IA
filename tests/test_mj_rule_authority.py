import unittest

from integrations.deepseek_mj import DeepSeekMJ


class MJRuleAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.mj = DeepSeekMJ(client=object(), model="test")
        self.personagem = {
            "id": "char-1",
            "nome": "Vex",
            "atributos": {
                "forca": 16, "destreza": 14, "constituicao": 13,
                "inteligencia": 12, "sabedoria": 10, "carisma": 8,
            },
            "modificadores": {
                "forca": 3, "destreza": 2, "constituicao": 1,
                "inteligencia": 1, "sabedoria": 0, "carisma": -1,
            },
            "bonus_proficiencia": 2,
            "pericias": ["investigacao"],
        }

    def test_atletismo_usa_forca_e_ignora_modificador_inventado(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "atletismo",
            "modifier": 999,
            "proficiente": True,
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["ability"], "forca")
        self.assertEqual(resultado["skill"], "atletismo")
        self.assertEqual(resultado["modifier"], 3)
        self.assertEqual(resultado["modifier_source"], "ficha_autoritativa")

    def test_pericia_registrada_recebe_bonus_de_proficiencia_da_ficha(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "investigacao",
            "modifier": -999,
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["ability"], "inteligencia")
        self.assertEqual(resultado["modifier"], 3)
        self.assertEqual(resultado["proficiency_applied"], 2)

    def test_motor_rejeita_atributo_incompativel_com_pericia(self):
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "ability_check",
            "skill": "atletismo",
            "ability": "destreza",
            "dc": 10,
        }}, [self.personagem])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "atributo_incompativel_com_pericia")
        self.assertEqual(resultado["atributo_correto"], "forca")

    def test_salvaguarda_usa_proficiência_da_ficha_e_ignora_bonus_inventado(self):
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 1,
            "atributos": {"inteligencia": 16, "constituicao": 10},
            "modificadores": {"inteligencia": 3, "constituicao": 0},
            "bonus_proficiencia": 2,
            "proficiencias_salvaguarda": ["constituicao", "inteligencia"],
        }
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "saving_throw_check", "ability": "inteligencia",
            "roll": 10, "dc": 15, "modifier": 999, "proficiente": False,
        }}, [artifice])
        self.assertEqual(resultado["resultado"], "sucesso")
        self.assertEqual(resultado["total"], 15)
        self.assertEqual(resultado["modifier_source"], "ficha_autoritativa")
        self.assertEqual(resultado["proficiency_applied"], 2)

    def test_artifice_nao_conjura_magia_que_nao_esta_preparada(self):
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 1,
            "atributos": {"inteligencia": 16},
            "conjuracao": {
                "truques": ["Luz", "Raio de Gelo"],
                "magias_preparadas": ["Curar Ferimentos"],
                "espacos_totais": {"1": 2}, "espacos_restantes": {"1": 2},
            },
        }
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "spell", "magia": "Alarme", "character_id": "artifice-1",
        }}, [artifice])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "magia_nao_escolhida_na_ficha")

    def test_artifice_conjura_magia_preparada_e_gasta_espaco(self):
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 1,
            "atributos": {"inteligencia": 16},
            "conjuracao": {
                "truques": ["Luz", "Raio de Gelo"],
                "magias_preparadas": ["Curar Ferimentos", "Alarme", "Vitalidade Vazia"],
                "espacos_totais": {"1": 2}, "espacos_restantes": {"1": 2},
            },
        }
        atualizacoes = []
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "spell", "magia": "Curar Ferimentos", "character_id": "artifice-1",
        }}, [artifice], on_character_update=lambda p: atualizacoes.append(dict(p["conjuracao"]["espacos_restantes"])))
        self.assertEqual(resultado["resultado"], "conjurada")
        self.assertEqual(resultado["espacos_restantes"], {"1": 1})
        self.assertEqual(atualizacoes, [{"1": 1}])

    def test_artifice_conjura_magia_de_subclasse_liberada_sem_estar_na_ficha(self):
        # Armeiro nível 3 tem Onda Trovejante como sempre preparada (fora da escolha).
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 3, "subclasse": "Armeiro",
            "atributos": {"inteligencia": 16},
            "conjuracao": {
                "truques": ["Luz", "Raio de Gelo"],
                "magias_preparadas": ["Curar Ferimentos", "Alarme"],
                "espacos_totais": {"1": 4, "2": 2}, "espacos_restantes": {"1": 4, "2": 2},
            },
        }
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "spell", "magia": "Onda Trovejante", "character_id": "artifice-1",
        }}, [artifice])
        self.assertNotEqual(resultado.get("motivo"), "magia_nao_disponivel_para_artifice")
        self.assertEqual(resultado["resultado"], "conjurada")

    def test_artifice_nao_conjura_magia_de_subclasse_ainda_nao_liberada(self):
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 3, "subclasse": "Armeiro",
            "atributos": {"inteligencia": 16},
            "conjuracao": {
                "truques": ["Luz", "Raio de Gelo"],
                "magias_preparadas": ["Curar Ferimentos", "Alarme"],
                "espacos_totais": {"1": 4, "2": 2}, "espacos_restantes": {"1": 4, "2": 2},
            },
        }
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "spell", "magia": "Relâmpago", "character_id": "artifice-1",
        }}, [artifice])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "magia_nao_disponivel_para_artifice")

    def test_artifice_nao_conjura_sem_espacos_restantes(self):
        artifice = {
            "id": "artifice-1", "classe": "artifice", "nivel": 1,
            "atributos": {"inteligencia": 16},
            "conjuracao": {
                "truques": ["Luz", "Raio de Gelo"],
                "magias_preparadas": ["Curar Ferimentos"],
                "espacos_totais": {"1": 2}, "espacos_restantes": {"1": 0},
            },
        }
        resultado = self.mj._tool("resolver_regra", {"fatos": {
            "type": "spell", "magia": "Curar Ferimentos", "character_id": "artifice-1",
        }}, [artifice])
        self.assertEqual(resultado["resultado"], "bloqueado")
        self.assertEqual(resultado["motivo"], "sem_espacos_restantes")


if __name__ == "__main__":
    unittest.main()
