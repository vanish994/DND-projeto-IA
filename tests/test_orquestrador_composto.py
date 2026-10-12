"""Operação composta ``area_spell``: uma chamada, todo o fluxo no motor.

Cobertura exigida para considerar a operação concluída:

- equivalência mecânica com o fluxo manual (spell → damage → saving_throw)
  usando as mesmas sementes — mesmo dano, mesma CD, mesmos d20s, mesmo gasto;
- falhas: sem espaço, magia fora da ficha, alvo fora do bestiário, sem alvos;
- atomicidade: nada é gasto quando a mecânica de dano não existe no catálogo;
- efeito aplicado uma única vez, com qualquer número de alvos;
- a salvaguarda usa o modificador do bloco do monstro, não o do personagem.
"""

import unittest

from orchestrator import OrquestradorAcoes
from rule_engine import build_default_engine


def feiticeiro() -> dict:
    return {
        "id": "p1",
        "nome": "Tessa",
        "classe": "feiticeiro",
        "especie": "humano",
        "nivel": 5,
        "pv_atual": 24,
        "pv_maximo": 30,
        "bonus_proficiencia": 3,
        "atributos": {
            "forca": 8,
            "destreza": 14,
            "constituicao": 14,
            "inteligencia": 12,
            "sabedoria": 10,
            "carisma": 16,
        },
        "modificadores": {
            "forca": -1,
            "destreza": 2,
            "constituicao": 2,
            "inteligencia": 1,
            "sabedoria": 0,
            "carisma": 3,
        },
        "conjuracao": {
            "truques": [],
            "magias_preparadas": ["Bola de Fogo", "Enfeitiçar Pessoa"],
            "espacos_totais": {"1": 2, "3": 2},
            "espacos_restantes": {"1": 2, "3": 2},
        },
    }


def executar_area(orquestrador, ficha, alvos, magia="Bola de Fogo", seed=None):
    fatos = {"type": "area_spell", "character_id": "p1", "magia": magia, "alvos": alvos}
    if seed:
        fatos["seed"] = seed
    return orquestrador.executar_ferramenta("resolver_regra", {"fatos": fatos}, [ficha])


class EquivalenciaMecanicaTests(unittest.TestCase):
    """O composto é válido só se o resultado for o do fluxo manual."""

    def setUp(self):
        self.engine = build_default_engine()

    def test_mesmas_sementes_produzem_os_mesmos_numeros_do_fluxo_manual(self):
        # Composto: uma chamada.
        composto = OrquestradorAcoes(build_default_engine())
        ficha_composto = feiticeiro()
        area = executar_area(composto, ficha_composto, ["Goblin", "Zombie"], seed="eq-1")

        # Manual: spell → damage → salvaguardas com os modificadores dos monstros.
        manual = OrquestradorAcoes(build_default_engine())
        ficha_manual = feiticeiro()
        manual.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "spell", "character_id": "p1", "magia": "Bola de Fogo"}},
            [ficha_manual],
        )
        dano_manual = manual.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "damage", "character_id": "p1", "magia": "Bola de Fogo", "seed": "eq-1"}},
            [ficha_manual],
        )
        cd = dano_manual.dados["cd_magia"]
        goblin = manual.engine.evaluate(
            {"type": "saving_throw", "ability": "destreza", "modifier": 2, "dc": cd, "seed": "eq-1:area-0"}
        ).outcome
        zombie = manual.engine.evaluate(
            {"type": "saving_throw", "ability": "destreza", "modifier": -2, "dc": cd, "seed": "eq-1:area-1"}
        ).outcome

        self.assertEqual(area.dados["resultado"], "conjurada")
        self.assertEqual(area.dados["dano"], dano_manual.dados["dano"])
        self.assertEqual(area.dados["dados_dano"], dano_manual.dados["dados_dano"])
        self.assertEqual(area.dados["cd_magia"], cd)
        alvo_goblin, alvo_zombie = area.dados["alvos"]
        self.assertEqual(alvo_goblin["salvaguarda"]["rolagem"], goblin.get("roll"))
        self.assertEqual(alvo_zombie["salvaguarda"]["rolagem"], zombie.get("roll"))
        # Mesmo gasto de espaço, uma vez em cada fluxo.
        self.assertEqual(
            ficha_composto["conjuracao"]["espacos_restantes"],
            ficha_manual["conjuracao"]["espacos_restantes"],
        )

    def test_salvaguarda_usa_o_modificador_do_bloco_do_monstro(self):
        orquestrador = OrquestradorAcoes(build_default_engine())
        ficha = feiticeiro()
        area = executar_area(orquestrador, ficha, ["Goblin", "Zombie"], seed="mods-1")
        por_nome = {alvo["nome"]: alvo for alvo in area.dados["alvos"]}
        # Goblin tem Destreza +2; Zombie tem −2 — nada do modificador da ficha
        # do jogador (+2 de Destreza) vaza para o Zombie.
        self.assertEqual(por_nome["Goblin"]["salvaguarda"]["modificador"], 2)
        self.assertEqual(por_nome["Zombie"]["salvaguarda"]["modificador"], -2)


class FluxoCompostoTests(unittest.TestCase):
    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())
        self.ficha = feiticeiro()

    def test_dois_alvos_uma_conjuracao_um_gasto_tres_rolagens(self):
        area = executar_area(self.orquestrador, self.ficha, ["Goblin", "Goblin"], seed="dup-1")
        self.assertEqual(area.status, "resolvido")
        self.assertEqual(area.dados["resultado"], "conjurada")
        self.assertEqual(len(area.dados["alvos"]), 2)
        # Efeito único: qualquer número de alvos gasta o espaço uma única vez.
        self.assertEqual(len(area.alteracoes), 1)
        self.assertEqual(self.ficha["conjuracao"]["espacos_restantes"]["3"], 1)
        # dano + salvaguarda de cada alvo, na ordem.
        self.assertEqual([r["tipo"] for r in area.rolagens], ["dano", "salvaguarda", "salvaguarda"])

    def test_sucesso_na_salvaguarda_aplica_metade_e_falha_aplica_inteiro(self):
        # Semente fixa: Goblin rola d20 20 (sucesso), Zombie rola d20 3 (falha).
        area = executar_area(self.orquestrador, self.ficha, ["Goblin", "Zombie"], seed="area-succ-3")
        por_nome = {alvo["nome"]: alvo for alvo in area.dados["alvos"]}
        dano_base = area.dados["dano"]
        self.assertTrue(area.dados["magia_sucesso_metade"])
        self.assertTrue(por_nome["Goblin"]["salvaguarda"]["sucesso"])
        self.assertEqual(por_nome["Goblin"]["dano_aplicado"], dano_base // 2)
        self.assertFalse(por_nome["Zombie"]["salvaguarda"]["sucesso"])
        self.assertEqual(por_nome["Zombie"]["dano_aplicado"], dano_base)

    def test_alias_magia_de_area_e_aceito(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {"fatos": {"type": "magia_de_area", "character_id": "p1", "magia": "Bola de Fogo", "alvos": ["Goblin"]}},
            [self.ficha],
        )
        self.assertEqual(resultado.status, "resolvido")


class RecusaCompostaTests(unittest.TestCase):
    """Toda recusa acontece antes de gastar recurso ou rolar dado."""

    def setUp(self):
        self.orquestrador = OrquestradorAcoes(build_default_engine())
        self.ficha = feiticeiro()

    def test_sem_espaco_restante_bloqueia_sem_rolagem(self):
        self.ficha["conjuracao"]["espacos_restantes"]["3"] = 0
        area = executar_area(self.orquestrador, self.ficha, ["Goblin"])
        self.assertEqual(area.status, "bloqueado")
        self.assertEqual(area.dados["motivo"], "sem_espacos_restantes")
        self.assertEqual(area.rolagens, [])
        self.assertEqual(len(area.alteracoes), 0)

    def test_magia_fora_da_ficha_bloqueia_sem_gastar(self):
        self.ficha["conjuracao"]["magias_preparadas"] = []
        area = executar_area(self.orquestrador, self.ficha, ["Goblin"])
        self.assertEqual(area.status, "bloqueado")
        self.assertEqual(area.dados["motivo"], "magia_nao_escolhida_na_ficha")
        self.assertEqual(self.ficha["conjuracao"]["espacos_restantes"]["3"], 2)
        self.assertEqual(area.rolagens, [])

    def test_mecanica_ausente_no_catalogo_nada_gasta_nem_rola(self):
        # Enfeitiçar Pessoa existe no catálogo e na ficha, mas não tem mecânica
        # de dano estruturada: a operação atômica recusa antes do gasto.
        area = executar_area(self.orquestrador, self.ficha, ["Goblin"], magia="Enfeitiçar Pessoa")
        self.assertEqual(area.status, "bloqueado")
        self.assertEqual(area.dados["motivo"], "magia_sem_mecanica_estruturada_no_catalogo")
        self.assertEqual(self.ficha["conjuracao"]["espacos_restantes"]["1"], 2)
        self.assertEqual(self.ficha["conjuracao"]["espacos_restantes"]["3"], 2)
        self.assertEqual(area.rolagens, [])

    def test_alvo_desconhecido_bloqueia_antes_da_conjuracao(self):
        area = executar_area(self.orquestrador, self.ficha, ["Goblin", "Dragao Verde Adulto"])
        self.assertEqual(area.status, "bloqueado")
        self.assertEqual(area.dados["motivo"], "monstro_desconhecido_no_bestiario")
        self.assertEqual(area.dados.get("alvo"), "Dragao Verde Adulto")
        self.assertEqual(self.ficha["conjuracao"]["espacos_restantes"]["3"], 2)
        self.assertEqual(area.rolagens, [])

    def test_sem_lista_de_alvos_bloqueia_com_dica(self):
        area = executar_area(self.orquestrador, self.ficha, [])
        self.assertEqual(area.status, "bloqueado")
        self.assertEqual(area.dados["motivo"], "alvos_de_area_ausentes")

    def test_personagem_ausente_bloqueia(self):
        resultado = self.orquestrador.executar_ferramenta(
            "resolver_regra",
            {
                "fatos": {
                    "type": "area_spell",
                    "character_id": "inexistente",
                    "magia": "Bola de Fogo",
                    "alvos": ["Goblin"],
                }
            },
            [self.ficha],
        )
        self.assertEqual(resultado.status, "bloqueado")
        self.assertEqual(resultado.dados["motivo"], "personagem_ausente_ou_nao_identificado")


if __name__ == "__main__":
    unittest.main()
