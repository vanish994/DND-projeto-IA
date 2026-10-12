"""Truques, magias e Ataque de Sopro resolvidos pelo motor.

Regressão do defeito em que o MJ recusava "raio de fogo" como ataque, dizendo
que o motor não tinha registro do truque. O motor precisa derivar o bônus de
conjuração da ficha, escalonar truques, rolar o dano, gastar espaços de magia e
resolver o Ataque de Sopro do Draconato por salvaguarda — sempre sem inventar
valores fora do catálogo.
"""
import unittest

from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine
from rule_engine.damage import aplicar_defesas_monstro
from rule_engine.casting import atributo_de_conjuracao as atributo_de_conjuracao_engine
from rule_engine.spells import escala_de_truque, mecanica_de_magia


def feiticeiro(**extra):
    ficha = {
        "id": "p1", "nome": "Vanish", "classe": "feiticeiro", "nivel": 3,
        "atributos": {"carisma": 16, "constituicao": 14, "destreza": 14},
        "conjuracao": {"truques": ["Raio de Fogo"], "magias_preparadas": ["Bola de Fogo"],
                       "espacos_totais": {"3": 2}, "espacos_restantes": {"3": 2}},
    }
    ficha.update(extra)
    return ficha


def draconato(**extra):
    ficha = {
        "id": "p1", "nome": "Vex", "classe": "guerreiro", "nivel": 5, "especie": "draconato",
        "heranca_draconica": "vermelho", "atributos": {"forca": 16, "constituicao": 15},
    }
    ficha.update(extra)
    return ficha


class MotorDeMagiaTests(unittest.TestCase):
    def setUp(self):
        self.engine = build_default_engine()
        self.mj = DeepSeekMJ.__new__(DeepSeekMJ)
        self.mj.engine = self.engine

    def resolver(self, fatos, personagens):
        rolagens = []
        resultado = self.mj._tool("resolver_regra", {"fatos": fatos}, personagens, on_roll=rolagens.append)
        return resultado, rolagens

    # ---------- catálogo ----------

    def test_escala_de_truque_segue_o_nivel_do_personagem(self):
        self.assertEqual([escala_de_truque(n) for n in (1, 4, 5, 10, 11, 16, 17, 20)], [1, 1, 2, 2, 3, 3, 4, 4])

    def test_mecanica_de_magia_escala_truque_e_espaco(self):
        self.assertEqual(mecanica_de_magia("Raio de Fogo", nivel_personagem=1)["dados_dano"], "1d10")
        self.assertEqual(mecanica_de_magia("Raio de Fogo", nivel_personagem=17)["dados_dano"], "4d10")
        self.assertEqual(mecanica_de_magia("Bola de Fogo", nivel_personagem=5)["dados_dano"], "8d6")
        self.assertEqual(mecanica_de_magia("Bola de Fogo", nivel_personagem=5, aumento=2)["dados_dano"], "10d6")
        self.assertIsNone(mecanica_de_magia("Magia Inexistente"))
        self.assertIsNone(mecanica_de_magia("Raio de Gelo"))

    # ---------- ataque de magia ----------

    def test_truque_de_ataque_usa_o_atributo_de_conjuracao_da_ficha(self):
        resultado, rolagens = self.resolver(
            {"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Goblin", "seed": "4"},
            [feiticeiro()],
        )
        self.assertEqual(resultado["modifier"], 3 + 2)  # Carisma 16 (+3) e proficiência +2
        self.assertEqual(resultado["spell_attack_ability"], "carisma")
        self.assertEqual([r["tipo"] for r in rolagens], ["ataque"])
        self.assertTrue(rolagens[0]["rotulo"].startswith("Ataque de magia"))

    def test_truque_escala_e_rola_o_dano_com_o_acerto(self):
        resultado, rolagens = self.resolver(
            {"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Goblin", "seed": "21"},
            [feiticeiro(nivel=5, conjuracao={"truques": ["Raio de Fogo"]})],
        )
        if resultado.get("result") == "hit":
            self.assertEqual(resultado["dano_expressao"], "2d10")
            self.assertEqual(resultado["dano"], sum(resultado["dados_dano"]) + resultado["modifier"])
            self.assertEqual(resultado["tipo_dano"], "igneo")
            self.assertEqual([r["tipo"] for r in rolagens], ["ataque", "dano"])
            self.assertEqual(rolagens[1]["rotulo"], "Dano de Raio de Fogo")

    def test_ataque_de_magia_reproduz_os_mesmos_dados_com_a_mesma_semente(self):
        fatos = {"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Goblin", "seed": "abc"}
        primeiro, _ = self.resolver(dict(fatos), [feiticeiro()])
        segundo, _ = self.resolver(dict(fatos), [feiticeiro()])
        self.assertEqual(primeiro["roll"], segundo["roll"])
        self.assertEqual(primeiro.get("dados_dano"), segundo.get("dados_dano"))

    def test_critico_de_magia_dobra_os_dados_de_dano(self):
        for semente in range(400):
            resultado, rolagens = self.resolver(
                {"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Goblin", "seed": str(semente)},
                [feiticeiro(nivel=5)],
            )
            if resultado.get("critical"):
                # O motor dobra a quantidade de dados rolados; a expressão base fica igual.
                self.assertEqual(resultado["dano_expressao"], "2d10")
                self.assertEqual(len(resultado["dados_dano"]), 4)
                self.assertEqual(resultado["dano"], sum(resultado["dados_dano"]))
                self.assertEqual([r["tipo"] for r in rolagens], ["ataque", "dano"])
                return
        self.fail("nenhum crítico encontrado com 400 sementes")

    def test_bloqueios_de_magia_com_motivo_explicito(self):
        casos = [
            ({"type": "attack", "character_id": "p1", "magia": "Magia Inventada", "target_name": "Goblin"}, "magia_desconhecida"),
            ({"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Dragão Inventado"}, "monstro_desconhecido_no_bestiario"),
            ({"type": "attack", "character_id": "p1", "magia": "Raio de Fogo"}, "nome_do_alvo_ausente"),
            ({"type": "attack", "character_id": "p1", "magia": "Bola de Fogo", "target_name": "Goblin"}, "magia_nao_resolve_por_jogada_de_ataque"),
        ]
        for fatos, motivo in casos:
            with self.subTest(motivo=motivo):
                resultado, rolagens = self.resolver(fatos, [feiticeiro(nivel=5, conjuracao={"truques": ["Raio de Fogo"], "magias_preparadas": ["Bola de Fogo"]})])
                self.assertEqual(resultado["motivo"], motivo)
                self.assertEqual(rolagens, [])

    def test_truque_precisa_estar_na_ficha(self):
        resultado, _ = self.resolver(
            {"type": "attack", "character_id": "p1", "magia": "Raio de Fogo", "target_name": "Goblin"},
            [feiticeiro(conjuracao={"truques": []})],
        )
        self.assertEqual(resultado["motivo"], "magia_nao_registrada_na_ficha")

    def test_arma_continua_usando_o_caminho_de_arma(self):
        resultado, rolagens = self.resolver(
            {"type": "attack", "character_id": "p1", "weapon": "Espada Longa", "target_name": "Goblin", "seed": "8"},
            [{"id": "p1", "nome": "Vex", "classe": "guerreiro", "nivel": 3, "atributos": {"forca": 16}}],
        )
        self.assertEqual(resultado["weapon"], "Espada Longa")
        self.assertEqual([r["tipo"] for r in rolagens], ["ataque"])
        self.assertEqual(rolagens[0]["rotulo"], "Ataque com Espada Longa contra Goblin")

    # ---------- dano de magia por salvaguarda ----------

    def test_dano_de_magia_sai_do_catalogo_com_cd_da_ficha(self):
        resultado, rolagens = self.resolver(
            {"type": "damage", "character_id": "p1", "magia": "Bola de Fogo", "seed": "11"},
            [feiticeiro()],
        )
        self.assertEqual(resultado["result"], "damage")
        self.assertEqual(resultado["dano_expressao"], "8d6")
        self.assertEqual(len(resultado["dados_dano"]), 8)
        self.assertEqual(resultado["dano"], sum(resultado["dados_dano"]))
        self.assertEqual(resultado["tipo_dano"], "igneo")
        # CD de magia: 8 + proficiência (+2) + Carisma (+3).
        self.assertEqual(resultado["cd_magia"], 13)
        self.assertEqual(resultado["magia_salvaguarda"], "destreza")
        self.assertTrue(resultado["magia_sucesso_metade"])
        self.assertEqual([r["tipo"] for r in rolagens], ["dano"])

    def test_dano_de_magia_respeita_espaco_maior(self):
        resultado, _ = self.resolver(
            {"type": "damage", "character_id": "p1", "magia": "Bola de Fogo", "espaco": 5, "seed": "11"},
            [feiticeiro(nivel=5)],
        )
        self.assertEqual(resultado["dano_expressao"], "10d6")
        self.assertEqual(resultado["aumento"], 2)

    def test_dano_de_magia_desconhecida_e_bloqueado(self):
        resultado, rolagens = self.resolver({"type": "damage", "character_id": "p1", "magia": "Magia Inventada"}, [feiticeiro()])
        self.assertEqual(resultado["motivo"], "magia_desconhecida")
        self.assertEqual(rolagens, [])

    # ---------- conjuração e espaços ----------

    def test_conjurar_gasta_espaco_e_bloqueia_quando_acaba(self):
        ficha = feiticeiro()
        primeiro = self.mj._tool("resolver_regra", {"fatos": {"type": "spell", "character_id": "p1", "magia": "Bola de Fogo"}}, [ficha])
        segundo = self.mj._tool("resolver_regra", {"fatos": {"type": "spell", "character_id": "p1", "magia": "Bola de Fogo"}}, [ficha])
        terceiro = self.mj._tool("resolver_regra", {"fatos": {"type": "cast_spell", "character_id": "p1", "magia": "Bola de Fogo"}}, [ficha])
        self.assertEqual(primeiro["resultado"], "conjurada")
        self.assertEqual(segundo["resultado"], "conjurada")
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"]["3"], 0)
        self.assertEqual(terceiro["motivo"], "sem_espacos_restantes")

    def test_truque_conjura_sem_gastar_espaco(self):
        ficha = feiticeiro()
        resultado = self.mj._tool("resolver_regra", {"fatos": {"type": "spell", "character_id": "p1", "magia": "Raio de Fogo"}}, [ficha])
        self.assertEqual(resultado["resultado"], "conjurada")
        self.assertEqual(resultado["espaco_usado"], 0)
        self.assertEqual(ficha["conjuracao"]["espacos_restantes"], {"3": 2})

    def test_conjurar_magia_de_outra_classe_e_bloqueado(self):
        resultado = self.mj._tool(
            "resolver_regra",
            {"fatos": {"type": "spell", "character_id": "p1", "magia": "Curar Ferimentos"}},
            [feiticeiro(nivel=5)],
        )
        self.assertEqual(resultado["motivo"], "magia_nao_escolhida_na_ficha")

    # ---------- Ataque de Sopro ----------

    def test_ataque_de_sopro_resolve_por_salvaguarda_de_destreza(self):
        resultado, rolagens = self.resolver(
            {"type": "attack", "character_id": "p1", "weapon": "Arma de Sopro", "target_name": "Goblin", "seed": "7"},
            [draconato()],
        )
        self.assertEqual(resultado["resultado"], "resolvido")
        self.assertEqual(resultado["tipo_resolucao"], "salvaguarda_de_area")
        self.assertEqual(resultado["dano_expressao"], "2d10")
        # O texto é o do traço no livro; a chave comparável fica em defesas_dano.
        self.assertEqual(resultado["tipo_dano"], "ígneo")
        self.assertEqual(resultado["defesas_dano"]["tipo_dano"], "fire")
        # CD do traço: 8 + proficiência (+3) + Constituição (+2).
        self.assertEqual(resultado["salvaguarda"]["cd"], 13)
        self.assertEqual(resultado["salvaguarda"]["atributo"], "destreza")
        self.assertEqual(resultado["usos_por_descanso_longo"], 3)
        self.assertEqual([r["tipo"] for r in rolagens], ["salvaguarda", "dano"])

    def test_ataque_de_sopro_metade_no_sucesso(self):
        alvo = {"id": "p1", "nome": "Vex", "nivel": 17, "especie": "draconato", "heranca_draconica": "vermelho",
                "atributos": {"constituicao": 20, "destreza": 20}}
        resultado, _ = self.resolver(
            {"type": "attack", "character_id": "p1", "weapon": "Ataque de Sopro", "target_name": "Goblin", "seed": "2"},
            [alvo],
        )
        bruto = sum(resultado["dados_dano"])
        if resultado["salvaguarda"]["sucesso"]:
            self.assertEqual(resultado["dano"], bruto // 2)
        else:
            self.assertEqual(resultado["dano"], bruto)

    def test_ataque_de_sopro_exige_heranca_draconica(self):
        resultado, rolagens = self.resolver(
            {"type": "attack", "character_id": "p1", "weapon": "Arma de Sopro", "target_name": "Goblin"},
            [draconato(heranca_draconica=None)],
        )
        self.assertEqual(resultado["motivo"], "ataque_de_sopro_exige_draconato_com_heranca_draconica_na_ficha")
        self.assertEqual(rolagens, [])

    def test_ataque_de_sopro_reproduz_a_mesma_rolagem(self):
        fatos = {"type": "attack", "character_id": "p1", "weapon": "Ataque de Sopro", "target_name": "Goblin", "seed": "5"}
        primeiro, _ = self.resolver(dict(fatos), [draconato()])
        segundo, _ = self.resolver(dict(fatos), [draconato()])
        self.assertEqual(primeiro["dano"], segundo["dano"])
        self.assertEqual(primeiro["salvaguarda"]["rolagem"], segundo["salvaguarda"]["rolagem"])

    def test_sopro_de_linhagem_aplicada_contra_defesas_do_alvo(self):
        # Goblin não tem defesa contra ígneo; a aplicação precisa ser explícita.
        resultado, _ = self.resolver(
            {"type": "attack", "character_id": "p1", "weapon": "Ataque de Sopro", "target_name": "Goblin", "seed": "3"},
            [draconato(heranca_draconica="latao")],
        )
        self.assertEqual(resultado["defesas_dano"]["aplicacao"], "normal")
        self.assertEqual(resultado["defesas_dano"]["tipo_dano"], "fire")


class DefesasDeDanoTests(unittest.TestCase):
    def test_resistencia_imunidade_e_vulnerabilidade(self):
        resistente = {"resistencias_dano": ["perfurante"]}
        imune = {"imunidades_dano": ["Veneno"]}
        vulneravel = {"vulnerabilidades_dano": ["contundente"]}
        self.assertEqual(aplicar_defesas_monstro(7, "perfurante", resistente)["dano"], 3)
        self.assertEqual(aplicar_defesas_monstro(7, "veneno", imune)["dano"], 0)
        self.assertEqual(aplicar_defesas_monstro(7, "contundente", vulneravel)["dano"], 14)

    def test_resistencia_e_vulnerabilidade_no_mesmo_tipo_se_cancelam(self):
        resultado = aplicar_defesas_monstro(9, "fogo", {"resistencias_dano": ["igneo"], "vulnerabilidades_dano": ["fogo"]})
        self.assertEqual(resultado["dano"], 9)
        self.assertEqual(resultado["aplicacao"], "resistencia_e_vulnerabilidade_canceladas")


if __name__ == "__main__":
    unittest.main()


class AtributoDeConjuracaoTests(unittest.TestCase):
    """O motor resolve o atributo por classe; a ficha sempre tem precedência."""

    def setUp(self):
        self.engine = build_default_engine()

    def test_atributo_por_classe(self):
        esperado = {
            "mago": "inteligencia", "clerigo": "sabedoria", "druida": "sabedoria", "bardo": "carisma",
            "bruxo": "carisma", "feiticeiro": "carisma", "paladino": "carisma", "guardiao": "sabedoria",
            "artifice": "inteligencia",
        }
        from rule_engine.casting import atributo_da_classe
        for classe, atributo in esperado.items():
            with self.subTest(classe=classe):
                self.assertEqual(atributo_da_classe(self.engine, classe, nivel=5), atributo)

    def test_classe_marcial_nao_tem_atributo_de_conjuracao(self):
        from rule_engine.casting import atributo_da_classe
        self.assertIsNone(atributo_da_classe(self.engine, "guerreiro", nivel=5))

    def test_ficha_declarada_tem_precedencia(self):
        ficha = {"classe": "guerreiro", "nivel": 5, "conjuracao": {"atributo_conjuracao": "carisma"}}
        self.assertEqual(atributo_de_conjuracao_engine(self.engine, ficha), "carisma")

    def test_artifice_usa_inteligencia_da_ficha(self):
        ficha = {"classe": "artifice", "nivel": 3, "atributos": {"inteligencia": 16}}
        self.assertEqual(atributo_de_conjuracao_engine(self.engine, ficha), "inteligencia")


try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool

    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover - backend opcional fora do CI
    DEPENDENCIAS = False


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class ConjurarNoMapaTaticoTests(unittest.TestCase):
    """/conjurar usa o catálogo para escalonar e devolve os dados que a interface anima."""

    def setUp(self):
        from unittest.mock import patch

        self.patch = patch
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-conjurador"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Magia"}, headers=self.headers).json()["id"]
        self.ficha = self.client.post(f"/v1/campanhas/{self.cid}/personagens", headers=self.headers, json={
            "nome": "Ferrun", "especie": "draconato", "heranca_draconica": "vermelho", "classe": "artifice",
            "metodo_atributos": "matriz_padrao",
            "atributos": {"forca": 10, "destreza": 13, "constituicao": 14, "inteligencia": 15, "sabedoria": 12, "carisma": 8},
            "antecedente": "soldado", "aumentos_antecedente": {"constituicao": 2, "destreza": 1},
            "ferramenta_antecedente": "Dados", "equipamento_antecedente": "A",
        }).json()
        self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{self.ficha['id']}/magias", headers=self.headers,
            json={"truques": ["Raio de Fogo", "Raio de Gelo"], "magias_preparadas": ["Curar Ferimentos", "Graxa"],
                  "espacos_totais": {"1": 2}},
        )
        self.url = f"/v1/campanhas/{self.cid}/mapa-tatico"
        self.client.put(self.url, headers=self.headers, json={
            "title": "Cripta", "terrain": "dungeon",
            "tokens": [
                {"id": "heroi", "kind": "hero", "character_id": self.ficha["id"], "x": 1, "y": 1},
                {"id": "inimigo", "kind": "enemy", "monster_name": "Awakened Shrub", "x": 2, "y": 1},
            ],
        })
        self.client.post(self.url + "/iniciativa/iniciar", headers=self.headers)
        for _ in range(3):
            if (self.client.get(self.url, headers=self.headers).json().get("mapa") or {}).get("token_ativo") == "heroi":
                break
            self.client.post(self.url + "/turno/avancar", headers=self.headers)
        self.mapa = self.client.get(self.url, headers=self.headers).json()["mapa"]

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def _nivel(self, nivel):
        atual = self.repo.obter_personagem("jogador-conjurador", self.cid, self.ficha["id"])
        self.repo.atualizar_dados_ficha("jogador-conjurador", self.cid, self.ficha["id"], {**atual, "nivel": nivel})

    def _conjurar(self, valores):
        """Rola com valores fixos: o mesmo número de d20 que a geometria exigir."""
        chamadas = []

        def randbelow(lados):
            # Repete o último valor se a rota pedir mais rolagens do que o previsto.
            indice = min(len(chamadas), len(valores) - 1)
            chamadas.append(valores[indice])
            return valores[indice]

        with self.patch.object(backend_app.secrets, "randbelow", side_effect=randbelow):
            resposta = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi", "alvo_id": "inimigo", "magia": "Raio de Fogo",
            })
        self.assertEqual(resposta.status_code, 200, resposta.text)
        return resposta.json()

    def test_truque_no_nivel_1_rola_um_dado(self):
        self.assertEqual(self.mapa.get("token_ativo"), "heroi", "o turno do herói precisa estar ativo")
        body = self._conjurar([9, 9, 4])  # d20 = 10 em cada dado de desvantagem; dano 5
        self.assertEqual(body["dano_expressao"], "1d10")
        self.assertEqual(len(body["dados_dano"]), 1)
        self.assertEqual(body["dano"], sum(body["dados_dano"]))
        self.assertEqual(body["ca_alvo"], 9)
        self.assertEqual(body["tipo_dano"], "igneo")
        self.assertIsNone(body["espaco_usado"], "truque não gasta espaço")

    def test_truque_no_nivel_11_escala_para_tres_dados(self):
        self._nivel(11)
        body = self._conjurar([9, 9, 4, 4, 4])
        self.assertEqual(body["dano_expressao"], "3d10")
        self.assertEqual(len(body["dados_dano"]), 3)
        self.assertEqual(body["dano"], sum(body["dados_dano"]))

    def test_critico_dobra_os_dados_do_truque(self):
        body = self._conjurar([19, 19, 4, 4])  # 20 natural nas duas rolagens
        self.assertTrue(body["ataque"]["critical"])
        self.assertEqual(len(body["dados_dano"]), 2)
        self.assertEqual(body["dano"], sum(body["dados_dano"]))
