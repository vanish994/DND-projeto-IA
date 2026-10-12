"""Contratos do Orquestrador de Ações.

O orquestrador é determinístico e não contém regra de D&D: ele interpreta a
intenção do MJ, confere pré-condições, chama o Rule Engine, aplica a alteração
no estado canônico e devolve o resultado. Estes testes cobrem as seis
responsabilidades, e em especial a que o projeto não pode perder: recusar em
vez de inventar, e nunca duplicar efeito no estado.
"""

import unittest

from orchestrator import Acao, OrquestradorAcoes, resumo_autoritativo
from rule_engine import build_default_engine


def feiticeiro(**extra):
    ficha = {
        "id": "p1",
        "nome": "Vanish",
        "classe": "feiticeiro",
        "nivel": 3,
        "atributos": {"carisma": 16, "constituicao": 14, "destreza": 14},
        "conjuracao": {
            "truques": ["Raio de Fogo"],
            "magias_preparadas": ["Bola de Fogo"],
            "espacos_totais": {"3": 2},
            "espacos_restantes": {"3": 2},
        },
    }
    ficha.update(extra)
    return ficha


def guerreiro(**extra):
    ficha = {
        "id": "g1",
        "nome": "Bruno",
        "classe": "guerreiro",
        "nivel": 1,
        "atributos": {"forca": 16, "destreza": 12, "constituicao": 14},
        "bonus_proficiencia": 2,
        "pericias": ["atletismo"],
    }
    ficha.update(extra)
    return ficha


class ContratoDaAcaoTests(unittest.TestCase):
    """Responsabilidade 1: interpretar o pedido estruturado do MJ."""

    def test_traducao_das_tres_ferramentas(self):
        sugerir = Acao.de_ferramenta(
            "sugerir_monstros", {"tipos": ["beast"], "nd_min": "1/4", "nd_max": "1", "limite": 3}
        )
        self.assertEqual((sugerir.tipo, sugerir.parametros["operacao"]), ("bestiary", "sugerir"))

        consultar = Acao.de_ferramenta("consultar_monstro", {"nome": "Goblin"})
        self.assertEqual((consultar.tipo, consultar.parametros["operacao"]), ("bestiary", "bloco_completo"))

        regra = Acao.de_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "character_id": "p1",
                    "target_name": "Goblin",
                }
            },
        )
        self.assertEqual(regra.tipo, "attack")
        self.assertEqual(regra.personagem_id, "p1")
        self.assertEqual(regra.alvo, "Goblin")

    def test_para_fatos_nao_vaza_referencia_mutavel(self):
        acao = Acao.de_ferramenta("resolver_regra", {"fatos": {"type": "attack"}})
        fatos = acao.para_fatos()
        fatos["modifier"] = 99
        self.assertNotIn("modifier", acao.para_fatos())

    def test_ferramenta_desconhecida_e_bloqueada_com_motivo(self):
        resultado = OrquestradorAcoes().executar_ferramenta("inventar_regra", {})
        self.assertEqual(resultado.status, "bloqueado")
        self.assertEqual(resultado.motivo, "ferramenta_desconhecida")


class PrecondicoesTests(unittest.TestCase):
    """Responsabilidade 3: sem informação suficiente, recusa explícita."""

    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())

    def test_personagem_ausente_bloqueia_sem_rolagem(self):
        rolagens = []
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "ability_check", "skill": "atletismo", "dc": 10}},
            [],
            on_rolagem=rolagens.append,
        )
        self.assertEqual(resultado.status, "bloqueado")
        self.assertEqual(resultado.motivo, "personagem_ausente_ou_nao_identificado")
        self.assertEqual(rolagens, [])

    def test_alvo_fora_do_bestiario_bloqueia(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "weapon": "Espada Longa",
                    "target_name": "Dragão Inventado",
                }
            },
            [guerreiro()],
        )
        self.assertEqual(resultado.motivo, "monstro_desconhecido_no_bestiario")
        self.assertEqual(resultado.dados["alvo"], "Dragão Inventado")

    def test_arma_fora_do_catalogo_bloqueia(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "weapon": "Lâmina do Infinito",
                    "target_name": "Goblin",
                }
            },
            [guerreiro()],
        )
        self.assertEqual(resultado.motivo, "arma_nao_encontrada_no_catalogo")

    def test_sem_proficiencia_na_arma_bloqueia(self):
        mago = {"id": "m1", "classe": "mago", "nivel": 1, "atributos": {"forca": 10, "destreza": 10}}
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "weapon": "Espada Longa",
                    "target_name": "Goblin",
                }
            },
            [mago],
        )
        self.assertEqual(resultado.motivo, "personagem_sem_proficiencia_na_arma")

    def test_ca_do_alvo_vem_do_bestiario_e_nao_do_modelo(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "weapon": "Espada Longa",
                    "target_name": "Goblin",
                    "modifier": 99,
                    "target_ac": 999,
                    "seed": "1",
                }
            },
            [guerreiro()],
        )
        self.assertEqual(resultado.dados["target_ac"], 15)  # CA oficial do Goblin
        self.assertEqual(resultado.dados["modifier"], 3 + 2)
        self.assertEqual(resultado.dados["modifier_source"], "ficha_autoritativa")


class EstadoTests(unittest.TestCase):
    """Responsabilidade 4: aplicar ao estado só o que o motor confirmou."""

    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())
        self.aplicadas = []

    def _conjurar(self, ficha, magia="Bola de Fogo", **fatos):
        return self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "spell", "character_id": ficha.get("id"), "magia": magia, **fatos}},
            [ficha],
            on_alteracao=lambda ficha, alteracao: self.aplicadas.append(alteracao),
        )

    def test_conjuracao_confirma_e_registra_a_alteracao(self):
        ficha = feiticeiro()
        resultado = self._conjurar(ficha)
        self.assertEqual(resultado.dados["resultado"], "conjurada")
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"3": 1})
        self.assertEqual(len(resultado.alteracoes), 1)
        alteracao = resultado.alteracoes[0]
        self.assertEqual((alteracao["espaco"], alteracao["de"], alteracao["para"]), ("3", 2, 1))
        self.assertEqual(self.aplicadas, resultado.alteracoes)

    def test_truque_nao_gasta_espaco_nem_registra_alteracao(self):
        ficha = feiticeiro()
        resultado = self._conjurar(ficha, magia="Raio de Fogo")
        self.assertEqual(resultado.dados["resultado"], "conjurada")
        self.assertEqual(resultado.dados["espaco_usado"], 0)
        self.assertEqual(resultado.alteracoes, [])
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"3": 2})

    def test_conjuracao_bloqueada_nao_altera_estado(self):
        ficha = feiticeiro(
            conjuracao={
                "truques": [],
                "magias_preparadas": ["Curar Ferimentos"],
                "espacos_totais": {"1": 2},
                "espacos_restantes": {"1": 2},
            }
        )
        resultado = self._conjurar(ficha)
        self.assertEqual(resultado.motivo, "magia_nao_escolhida_na_ficha")
        self.assertEqual(resultado.alteracoes, [])
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"1": 2})

    def test_duas_conjuracoes_consomem_exatamente_dois_espacos(self):
        ficha = feiticeiro()
        self._conjurar(ficha)
        self._conjurar(ficha)
        terceira = self._conjurar(ficha)
        self.assertEqual(terceira.motivo, "sem_espacos_restantes")
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"3": 0})
        self.assertEqual(self.aplicadas[-1]["de"], 1)

    def test_espaco_maior_e_consumido_no_nivel_certo(self):
        ficha = feiticeiro(
            nivel=9,
            conjuracao={
                "truques": [],
                "magias_preparadas": ["Bola de Fogo"],
                "espacos_totais": {"3": 1, "5": 1},
                "espacos_restantes": {"3": 1, "5": 1},
            },
        )
        resultado = self._conjurar(ficha, espaco=5)
        self.assertEqual(resultado.dados["resultado"], "conjurada")
        self.assertEqual(resultado.dados["espaco_usado"], 5)
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"3": 1, "5": 0})


class RolagensTests(unittest.TestCase):
    """Responsabilidade 5: devolver resultado estruturado, com os dados do motor."""

    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())
        self.coletadas = []

    def test_bestiario_nao_registra_rolagem(self):
        resultado = self.orquestrador.executar_ferramenta(
            "consultar_monstro", {"nome": "Goblin"}, on_rolagem=self.coletadas.append
        )
        self.assertEqual(resultado.status, "resolved")
        self.assertEqual(resultado.rolagens, [])
        self.assertEqual(self.coletadas, [])

    def test_teste_de_habilidade_anuncia_a_rolagem_do_motor(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "ability_check", "skill": "atletismo", "dc": 12}},
            [guerreiro()],
            on_rolagem=self.coletadas.append,
        )
        self.assertEqual(len(resultado.rolagens), 1)
        rolagem = resultado.rolagens[0]
        self.assertEqual(rolagem["tipo"], "teste")
        self.assertEqual(rolagem["valor"], resultado.dados["roll"])
        self.assertEqual(rolagem["origem"], "rule_engine")
        self.assertEqual(self.coletadas, resultado.rolagens)

    def test_sopro_registra_salvaguarda_e_dano(self):
        draconato = {
            "id": "d1",
            "nome": "Vex",
            "classe": "guerreiro",
            "nivel": 5,
            "especie": "draconato",
            "heranca_draconica": "vermelho",
            "atributos": {"forca": 16, "constituicao": 15},
        }
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "attack",
                    "character_id": "d1",
                    "weapon": "Ataque de Sopro",
                    "target_name": "Goblin",
                    "seed": "7",
                }
            },
            [draconato],
            on_rolagem=self.coletadas.append,
        )
        self.assertEqual(resultado.dados["resultado"], "resolvido")
        self.assertEqual([r["tipo"] for r in resultado.rolagens], ["salvaguarda", "dano"])
        self.assertEqual(self.coletadas, resultado.rolagens)

    def test_sopro_sem_heranca_bloqueia_sem_rolagem(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "attack", "character_id": "d1", "weapon": "Ataque de Sopro", "target_name": "Goblin"}},
            [
                {
                    "id": "d1",
                    "classe": "guerreiro",
                    "nivel": 5,
                    "especie": "draconato",
                    "atributos": {"constituicao": 15},
                }
            ],
        )
        self.assertEqual(resultado.status, "bloqueado")
        self.assertEqual(resultado.motivo, "ataque_de_sopro_exige_draconato_com_heranca_draconica_na_ficha")
        self.assertEqual(resultado.rolagens, [])


class ResumoAutoritativoTests(unittest.TestCase):
    """Responsabilidade 6: MJ, ficha e combate lendo o mesmo estado."""

    def test_sem_personagem_instrui_a_nao_inventar(self):
        texto = resumo_autoritativo([])
        self.assertIn("nenhum personagem está cadastrado", texto)
        self.assertIn("Não invente", texto)

    def test_com_personagem_traz_os_dados_da_ficha(self):
        texto = resumo_autoritativo([feiticeiro()])
        self.assertIn("FICHA AUTORITATIVA #1", texto)
        self.assertIn("nome=Vanish", texto)
        self.assertIn("espaços restantes={'3': 2}", texto)

    def test_espacos_restantes_aparecem_apos_o_gasto(self):
        ficha = feiticeiro()
        orquestrador = OrquestradorAcoes(build_default_engine())
        orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "spell",
                    "character_id": "p1",
                    "magia": "Bola de Fogo",
                }
            },
            [ficha],
        )
        self.assertIn("espaços restantes={'3': 1}", resumo_autoritativo([ficha]))


if __name__ == "__main__":
    unittest.main()
