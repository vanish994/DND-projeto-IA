import unittest

from rule_engine.character import criar_personagem, ficha_personagem
from rule_engine.spellcasting import (
    listar_magias_artifice,
    progresso_artifice,
    validar_escolhas_artifice,
)
from rule_engine.spells import obter_magia


class ProficienciasClasseTests(unittest.TestCase):
    def fatos(self, **extra):
        dados = {
            "name": "Vex",
            "species": "draconato",
            "class": "artifice",
            "level": 1,
            "ability_scores": {
                "forca": 8, "destreza": 13, "constituicao": 10,
                "inteligencia": 16, "sabedoria": 12, "carisma": 16,
            },
            "background": "investigador",
            "class_skill_proficiencies": ["arcanismo", "historia"],
            "artisan_tool_proficiency": "Ferramentas de Funileiro",
        }
        dados.update(extra)
        return dados

    def test_artifice_exige_quantidade_correta_de_pericias(self):
        with self.assertRaisesRegex(ValueError, "exatamente 2 perícias"):
            criar_personagem(self.fatos(class_skill_proficiencies=["arcanismo"]))

    def test_artifice_nao_aceita_pericia_fora_da_lista(self):
        with self.assertRaisesRegex(ValueError, "não disponível para esta classe"):
            criar_personagem(self.fatos(class_skill_proficiencies=["arcanismo", "atletismo"]))

    def test_ficha_combina_pericias_de_classe_e_antecedente_sem_duplicar(self):
        personagem = criar_personagem(self.fatos(
            class_skill_proficiencies=["investigacao", "arcanismo"]
        ))
        ficha = ficha_personagem(personagem)
        self.assertEqual(ficha["pericias_classe"], ["arcanismo", "investigacao"])
        self.assertEqual(ficha["pericias"].count("investigacao"), 1)
        self.assertIn("intuicao", ficha["pericias"])
        self.assertEqual(ficha["proficiencias_salvaguarda"], ["constituicao", "inteligencia"])
        self.assertFalse(ficha["proficiencias_pendentes"])


class ArtificerSpellValidationTests(unittest.TestCase):
    def test_progressao_nivel_um_com_inteligencia_16(self):
        resultado = progresso_artifice(1, 16)
        self.assertEqual(resultado["truques"], 2)
        self.assertEqual(resultado["magias_preparadas"], 3)
        self.assertEqual(resultado["espacos_totais"], {"1": 2})
        self.assertEqual(resultado["circulo_maximo"], 1)

    def test_catalogo_artifice_filtra_por_nivel(self):
        magias = listar_magias_artifice(1)
        nomes = {m["nome"].lower() for m in magias}
        self.assertIn("luz", nomes)
        self.assertIn("alarme", nomes)
        self.assertNotIn("bola de fogo", nomes)

    def test_catalogo_define_circulo_de_magias_do_artifice(self):
        self.assertEqual(obter_magia("Luz")["circulo"], 0)
        self.assertEqual(obter_magia("Alarme")["circulo"], 1)

    def test_escolhas_validas_sao_aceitas(self):
        resultado = validar_escolhas_artifice(
            1, 16,
            ["Luz", "Raio de Gelo"],
            ["Alarme", "Curar Ferimentos", "Onda Trovejante"],
            {"1": 2},
        )
        self.assertEqual(resultado["resultado"], "resolvido")

    def test_bloqueia_magia_de_classe_ou_circulo_indisponivel(self):
        with self.assertRaisesRegex(ValueError, "não disponível para Artífice"):
            validar_escolhas_artifice(
                1, 16, ["Luz", "Raio de Gelo"],
                ["Alarme", "Curar Ferimentos", "Bola de Fogo"], {"1": 2},
            )

    def test_bloqueia_quantidade_incorreta_de_truques_e_magias(self):
        with self.assertRaisesRegex(ValueError, "exatamente 2 truques"):
            validar_escolhas_artifice(1, 16, ["Luz"], ["Alarme", "Curar Ferimentos", "Onda Trovejante"], {"1": 2})
        with self.assertRaisesRegex(ValueError, "exatamente 3 magias preparadas"):
            validar_escolhas_artifice(1, 16, ["Luz", "Raio de Gelo"], ["Alarme"], {"1": 2})

    def test_bloqueia_total_de_espacos_inventado(self):
        with self.assertRaisesRegex(ValueError, "Espaços de magia incorretos"):
            validar_escolhas_artifice(
                1, 16, ["Luz", "Raio de Gelo"],
                ["Alarme", "Curar Ferimentos", "Onda Trovejante"], {"1": 9},
            )


if __name__ == "__main__":
    unittest.main()
