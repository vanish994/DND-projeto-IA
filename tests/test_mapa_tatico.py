import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from backend import app as backend_app
    from backend.persistencia import RepositorioCampanhas
    DEPENDENCIAS = True
except ImportError:  # pragma: no cover
    DEPENDENCIAS = False


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class BackendMapaTaticoTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-mapa"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Encontro tático"}, headers=self.headers).json()["id"]
        payload = {
            "nome": "Vex", "especie": "elfo", "classe": "guerreiro", "metodo_atributos": "matriz_padrao",
            "atributos": {"forca": 15, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8},
            "antecedente": "soldado", "aumentos_antecedente": {"forca": 2, "constituicao": 1},
        }
        response = self.client.post(f"/v1/campanhas/{self.cid}/personagens", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.hero = response.json()
        self.url = f"/v1/campanhas/{self.cid}/mapa-tatico"

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def save_encounter(self, hero_x=1, hero_y=1, enemy_x=2, enemy_y=1):
        return self.client.put(self.url, headers=self.headers, json={
            "title": "Floresta", "terrain": "forest",
            "tokens": [
                {"id": "heroi-vex", "kind": "hero", "character_id": self.hero["id"], "x": hero_x, "y": hero_y},
                {"id": "inimigo-bandido", "kind": "enemy", "monster_name": "Bandit", "x": enemy_x, "y": enemy_y},
            ],
        })

    def test_tokens_vinculam_ficha_e_bestiario(self):
        response = self.save_encounter()
        self.assertEqual(response.status_code, 200, response.text)
        tokens = response.json()["mapa"]["tokens"]
        self.assertEqual(tokens[0]["name"], "Vex")
        self.assertEqual(tokens[0]["hp"], self.hero["pv_atual"])
        self.assertEqual(tokens[1]["name"], "Bandit")
        self.assertEqual(tokens[1]["ac"], 12)
        self.assertEqual(tokens[1]["hp"], 11)

    def test_motor_rejeita_movimento_acima_do_deslocamento(self):
        self.save_encounter()
        response = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": "heroi-vex", "destino_x": 8, "destino_y": 1,
        })
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["motivo"], "movimento_insuficiente")

    def test_motor_aceita_movimento_dentro_do_deslocamento(self):
        self.save_encounter()
        response = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": "heroi-vex", "destino_x": 3, "destino_y": 1,
        })
        self.assertEqual(response.status_code, 200, response.text)
        token = next(t for t in response.json()["mapa"]["tokens"] if t["id"] == "heroi-vex")
        self.assertEqual((token["x"], token["y"]), (3, 1))

    def test_ataque_aplica_motor_de_acerto_e_dano(self):
        self.save_encounter()
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn(body["ataque"]["result"], {"hit", "miss"})
        self.assertGreaterEqual(body["rolagem"], 1)
        self.assertLessEqual(body["rolagem"], 20)
        bandido = next(t for t in body["mapa"]["tokens"] if t["id"] == "inimigo-bandido")
        self.assertEqual(bandido["hp"], 11 - body["dano"])

    def test_equipamento_calcula_ca_com_armadura_e_escudo(self):
        response = self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/equipamento",
            headers=self.headers,
            json={"armadura": "Couro", "escudo": True},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.save_encounter()
        mapa = self.client.get(self.url, headers=self.headers).json()["mapa"]
        heroi = next(t for t in mapa["tokens"] if t["id"] == "heroi-vex")
        self.assertEqual(heroi["ac"], 15)  # couro 11 + DES 2 + escudo 2

    def test_ataque_usa_dano_da_arma_equipada(self):
        equip = self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/equipamento",
            headers=self.headers,
            json={"arma": "Espada Longa"},
        )
        self.assertEqual(equip.status_code, 200, equip.text)
        self.save_encounter()
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido", "arma": "Espada Longa",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["arma"], "Espada Longa")
        self.assertIn(body["ataque"]["result"], {"hit", "miss"})
        if body["ataque"]["result"] == "hit":
            self.assertGreaterEqual(body["dano"], 1)

    def test_ataque_com_arco_a_distancia_valida(self):
        equip = self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/equipamento",
            headers=self.headers, json={"arma": "Arco Curto"},
        )
        self.assertEqual(equip.status_code, 200, equip.text)
        self.save_encounter(hero_x=1, hero_y=1, enemy_x=10, enemy_y=1)
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["ataque_a_distancia"])
        self.assertEqual(body["alcance_pes"], 79)
        self.assertIn(body["ataque"]["result"], {"hit", "miss"})

    def _criar_artifice_com_magias(self):
        payload = {
            "nome": "Tessa", "especie": "humano", "classe": "artifice", "nivel": 1,
            "metodo_atributos": "matriz_padrao",
            "atributos": {"forca": 8, "destreza": 14, "constituicao": 13, "inteligencia": 15, "sabedoria": 12, "carisma": 10},
            "antecedente": "soldado", "aumentos_antecedente": {"forca": 2, "constituicao": 1},
        }
        response = self.client.post(f"/v1/campanhas/{self.cid}/personagens", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        original = self.hero
        self.hero = response.json()
        magias = self.client.patch(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/magias",
            headers=self.headers,
            json={"truques": ["Raio de Fogo", "Consertar"],
                  "magias_preparadas": ["Curar Ferimentos", "Onda Trovejante"],
                  "espacos_totais": {"1": 2}},
        )
        self.assertEqual(magias.status_code, 200, magias.text)
        return original

    def test_raio_de_fogo_conjura_e_nao_gasta_espaco(self):
        original = self._criar_artifice_com_magias()
        try:
            self.save_encounter(hero_x=1, hero_y=1, enemy_x=5, enemy_y=1)
            response = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido", "magia": "Raio de Fogo",
            })
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["resolucao_motor"]["resultado"], "conjurada")
            self.assertIn(body["ataque"]["result"], {"hit", "miss"})
            self.assertIsNone(body["espaco_usado"])
            self.assertEqual(body["espacos_restantes"].get("1"), 2)
        finally:
            self.hero = original

    def test_curar_ferimentos_gasta_espaco_de_magia(self):
        original = self._criar_artifice_com_magias()
        try:
            self.save_encounter()
            response = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "heroi-vex", "magia": "Curar Ferimentos",
            })
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertGreater(body["cura"], 0)
            self.assertEqual(body["espacos_restantes"]["1"], 1)
        finally:
            self.hero = original

    def test_magia_nao_preparada_e_rejeitada(self):
        original = self._criar_artifice_com_magias()
        try:
            self.save_encounter()
            response = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido", "magia": "Graxa",
            })
            self.assertEqual(response.status_code, 422, response.text)
        finally:
            self.hero = original

    def test_magia_de_area_resolve_salvaguarda_em_alvo_com_ficha(self):
        original = self._criar_artifice_com_magias()
        try:
            response = self.client.put(self.url, headers=self.headers, json={
                "title": "Teste de área", "terrain": "forest",
                "tokens": [
                    {"id": "heroi-vex", "kind": "hero", "character_id": self.hero["id"], "x": 1, "y": 1},
                    {"id": "inimigo-bandido", "kind": "enemy", "monster_name": "Bandit", "x": 2, "y": 1},
                ],
            })
            self.assertEqual(response.status_code, 200, response.text)
            response = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido", "magia": "Onda Trovejante",
            })
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(len(body["resultados_area"]), 1)
            self.assertIn("salvaguarda", body["resultados_area"][0])
            self.assertGreaterEqual(body["dano"], 0)
            self.assertEqual(body["espacos_restantes"]["1"], 1)
        finally:
            self.hero = original

    def test_ataque_de_monstro_usa_bloco_estruturado(self):
        self.save_encounter()
        response = self.client.post(self.url + "/ataque-monstro", headers=self.headers, json={
            "atacante_id": "inimigo-bandido", "alvo_id": "heroi-vex",
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["monstro"], "Bandit")
        self.assertEqual(body["acao"], "Scimitar")
        self.assertIn(body["ataque"]["result"], {"hit", "miss"})
        self.assertGreaterEqual(body["dano"], 0)
        self.assertEqual(body["bonus_ataque"], 3)

    def test_multiataque_resolve_cada_ataque_separadamente(self):
        response = self.client.put(self.url, headers=self.headers, json={
            "title": "Teste multiataque", "terrain": "dungeon",
            "tokens": [
                {"id": "heroi-vex", "kind": "hero", "character_id": self.hero["id"], "x": 1, "y": 1},
                {"id": "inimigo-dretch", "kind": "enemy", "monster_name": "Dretch", "x": 2, "y": 1},
            ],
        })
        self.assertEqual(response.status_code, 200, response.text)
        # Ataques atingem; dados de dano mínimos para tornar o teste determinístico.
        with patch.object(backend_app.secrets, "randbelow", side_effect=[9, 0, 9, 0, 0]):
            response = self.client.post(self.url + "/ataque-monstro", headers=self.headers, json={
                "atacante_id": "inimigo-dretch", "alvo_id": "heroi-vex", "acao": "Multiattack",
            })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["multiataque"])
        self.assertEqual(body["sequencia"], ["Bite", "Claws"])
        self.assertEqual(len(body["ataques_resolvidos"]), 2)
        self.assertEqual(body["total_dano"], sum(a["dano"] for a in body["ataques_resolvidos"]))

    def test_ataque_de_lobo_aplica_caido_apos_falha_na_salvaguarda(self):
        response = self.client.put(self.url, headers=self.headers, json={
            "title": "Teste condição", "terrain": "forest",
            "tokens": [
                {"id": "heroi-vex", "kind": "hero", "character_id": self.hero["id"], "x": 1, "y": 1},
                {"id": "inimigo-lobo", "kind": "enemy", "monster_name": "Wolf", "x": 2, "y": 1},
            ],
        })
        self.assertEqual(response.status_code, 200, response.text)
        # d20 de ataque = 10, dois dados de dano = 1, salvaguarda de Força = 1.
        with patch.object(backend_app.secrets, "randbelow", side_effect=[9, 0, 0, 0]):
            response = self.client.post(self.url + "/ataque-monstro", headers=self.headers, json={
                "atacante_id": "inimigo-lobo", "alvo_id": "heroi-vex", "acao": "Bite",
            })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["efeitos"][0]["cd"], 11)
        self.assertFalse(body["efeitos"][0]["sucesso"])
        self.assertIn("prone", body["efeitos"][0]["condicoes_aplicadas"])
        raw = self.repo.obter_mapa_tatico("jogador-mapa", self.cid)
        token = next(t for t in raw["tokens"] if t["id"] == "heroi-vex")
        self.assertIn("prone", token["conditions"])

    def test_zumbi_usa_undead_fortitude_ao_chegar_a_zero_pv(self):
        response = self.client.put(self.url, headers=self.headers, json={
            "title": "Teste de fortitude", "terrain": "dungeon",
            "tokens": [
                {"id": "heroi-vex", "kind": "hero", "character_id": self.hero["id"], "x": 1, "y": 1},
                {"id": "inimigo-zumbi", "kind": "enemy", "monster_name": "Zombie", "x": 2, "y": 1},
            ],
        })
        self.assertEqual(response.status_code, 200, response.text)
        estado = self.repo.obter_mapa_tatico("jogador-mapa", self.cid)
        for token in estado["tokens"]:
            if token["id"] == "inimigo-zumbi":
                token["hp"] = 1
        self.repo.salvar_mapa_tatico("jogador-mapa", self.cid, estado)

        # Ataque não crítico (d20=10) e salvaguarda de Constituição (d20=19).
        with patch.object(backend_app.secrets, "randbelow", side_effect=[9, 18]):
            response = self.client.post(self.url + "/atacar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "inimigo-zumbi",
            })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["fortitude"]["sucesso"])
        self.assertEqual(body["fortitude"]["cd"], 5 + body["dano"])
        zumbi = next(t for t in body["mapa"]["tokens"] if t["id"] == "inimigo-zumbi")
        self.assertEqual(zumbi["hp"], 1)

    def test_parser_ignora_acao_sem_mecanica_de_ataque(self):
        ataques = backend_app._extrair_ataques_monstro({"acoes": [
            {"nome": "Multiattack", "desc": "The creature makes two attacks."},
            {"nome": "Bite", "desc": "Melee Attack Roll: +4, reach 5 ft. Hit: 7 (2d4 + 2) Piercing damage."},
        ]})
        self.assertEqual(len(ataques), 1)
        self.assertEqual(ataques[0]["nome"], "Bite")
        self.assertEqual(ataques[0]["bonus_ataque"], 4)
        self.assertEqual(ataques[0]["dano"], "2d4+2")
        self.assertEqual(ataques[0]["alcance_corpo_a_corpo"], 5)


    def test_ataque_fora_de_alcance_e_rejeitado(self):
        self.save_encounter(hero_x=1, hero_y=1, enemy_x=5, enemy_y=1)
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 422, response.text)


    def test_condicao_persiste_na_ficha_e_bloqueia_ataque_incompativel(self):
        response = self.client.post(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/condicoes",
            headers=self.headers,
            json={"operacao": "apply", "condicao": "paralisado", "duracao": 2},
        )
        self.assertEqual(response.status_code, 200, response.text)
        ficha = self.client.get(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}", headers=self.headers
        ).json()
        self.assertIn("paralisado", ficha["condicoes_ativas"])
        self.assertEqual(ficha["duracoes_condicoes"]["paralisado"], 2)
        self.save_encounter()
        ataque = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(ataque.status_code, 422, ataque.text)
        self.assertEqual(ataque.json()["detail"]["motivo"], "atacante_incapacitado")

    def test_concentracao_e_encerrada_apos_salvaguarda_falha_por_dano(self):
        ficha = self.repo.obter_personagem("jogador-mapa", self.cid, self.hero["id"])
        dados = {k: v for k, v in ficha.items() if k not in {"id", "campanha_id", "entrada", "criado_em", "atualizado_em", "pv_atual"}}
        dados["concentrando"] = "Benção"
        self.repo.atualizar_dados_ficha("jogador-mapa", self.cid, self.hero["id"], dados)
        with patch.object(backend_app.secrets, "randbelow", return_value=0):
            resultado = backend_app._resolver_concentracao_apos_dano(
                self.repo, "jogador-mapa", self.cid, self.hero["id"], 12
            )
        self.assertEqual(resultado["resultado"], "falha")
        self.assertFalse(resultado["concentracao_mantida"])
        ficha_final = self.repo.obter_personagem("jogador-mapa", self.cid, self.hero["id"])
        self.assertIsNone(ficha_final["concentrando"])


    def test_iniciativa_persiste_e_avanco_expira_condicao_numerica(self):
        condicao = self.client.post(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/condicoes",
            headers=self.headers,
            json={"operacao": "apply", "condicao": "paralisado", "duracao": 1},
        )
        self.assertEqual(condicao.status_code, 200, condicao.text)
        self.save_encounter()
        with patch.object(backend_app.secrets, "randbelow", side_effect=[10, 10]):
            inicio = self.client.post(self.url + "/iniciativa/iniciar", headers=self.headers)
        self.assertEqual(inicio.status_code, 200, inicio.text)
        body = inicio.json()
        self.assertEqual(body["rodada"], 1)
        self.assertEqual(len(body["iniciativa"]), 2)
        ativo = body["mapa"]["token_ativo"]
        ficha = self.hero
        if ativo != "heroi-vex":
            # Forçar a ordem do herói em empate, com o modificador de Destreza da ficha.
            self.assertNotEqual(ativo, "heroi-vex")
            bruto = self.repo.obter_mapa_tatico("jogador-mapa", self.cid)
            bruto["iniciativa"].sort(key=lambda item: item["token_id"] != "heroi-vex")
            bruto["turno_indice"] = 0
            self.repo.salvar_mapa_tatico("jogador-mapa", self.cid, bruto)
        avancar = self.client.post(self.url + "/turno/avancar", headers=self.headers, json={"token_id": "heroi-vex"})
        self.assertEqual(avancar.status_code, 200, avancar.text)
        self.assertIn("paralisado", avancar.json()["duracoes_encerradas"])
        ficha_atual = self.repo.obter_personagem("jogador-mapa", self.cid, self.hero["id"])
        self.assertNotIn("paralisado", ficha_atual.get("condicoes_ativas", []))
        mapa = self.client.get(self.url, headers=self.headers).json()["mapa"]
        self.assertTrue(mapa["combate_ativo"])
        self.assertEqual(mapa["rodada"], 1)

    def test_alvo_inconsciente_adjacente_sofre_critico_automatico(self):
        self.save_encounter()
        bruto = self.repo.obter_mapa_tatico("jogador-mapa", self.cid)
        for token in bruto["tokens"]:
            if token["id"] == "inimigo-bandido":
                token["conditions"] = ["unconscious"]
        self.repo.salvar_mapa_tatico("jogador-mapa", self.cid, bruto)
        with patch.object(backend_app.secrets, "randbelow", return_value=9):
            response = self.client.post(self.url + "/atacar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["ataque"]["result"], "hit")
        self.assertTrue(response.json()["ataque"]["critical"])
        self.assertEqual(response.json()["ataque"]["reason"], "critical_due_to_condition")

    def test_condicao_do_monstro_persiste_e_da_vantagem_ao_heroi(self):
        self.save_encounter()
        bruto = self.repo.obter_mapa_tatico("jogador-mapa", self.cid)
        for token in bruto["tokens"]:
            if token["id"] == "inimigo-bandido":
                token["conditions"] = ["prone"]
        self.repo.salvar_mapa_tatico("jogador-mapa", self.cid, bruto)
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["efeitos_condicao"]["resultado"], "vantagem")
        mapa = response.json()["mapa"]
        bandido = next(t for t in mapa["tokens"] if t["id"] == "inimigo-bandido")
        self.assertIn("prone", bandido["conditions"])

    def test_iniciativa_impede_acao_fora_do_turno(self):
        self.save_encounter()
        with patch.object(backend_app.secrets, "randbelow", side_effect=[10, 10]):
            inicio = self.client.post(self.url + "/iniciativa/iniciar", headers=self.headers)
        self.assertEqual(inicio.status_code, 200, inicio.text)
        ativo = inicio.json()["mapa"]["token_ativo"]
        fora_do_turno = "inimigo-bandido" if ativo == "heroi-vex" else "heroi-vex"
        response = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": fora_do_turno, "destino_x": 4, "destino_y": 1,
        })
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["detail"]["motivo"], "turno_de_outra_criatura")

    def test_caido_custa_metade_do_movimento_para_levantar(self):
        condicao = self.client.post(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/condicoes",
            headers=self.headers,
            json={"operacao": "apply", "condicao": "caido", "duracao": 2},
        )
        self.assertEqual(condicao.status_code, 200, condicao.text)
        self.save_encounter()
        longo = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": "heroi-vex", "destino_x": 5, "destino_y": 1,
        })
        self.assertEqual(longo.status_code, 422, longo.text)
        curto = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": "heroi-vex", "destino_x": 4, "destino_y": 1,
        })
        self.assertEqual(curto.status_code, 200, curto.text)
        ficha = self.repo.obter_personagem("jogador-mapa", self.cid, self.hero["id"])
        self.assertNotIn("caido", ficha.get("condicoes_ativas", []))

    def test_condicao_que_zerou_deslocamento_impede_movimento(self):
        condicao = self.client.post(
            f"/v1/campanhas/{self.cid}/personagens/{self.hero['id']}/condicoes",
            headers=self.headers,
            json={"operacao": "apply", "condicao": "contido", "duracao": 2},
        )
        self.assertEqual(condicao.status_code, 200, condicao.text)
        self.save_encounter()
        response = self.client.post(self.url + "/mover", headers=self.headers, json={
            "token_id": "heroi-vex", "destino_x": 3, "destino_y": 1,
        })
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"]["motivo"], "movimento_impedido_por_condicao")


if __name__ == "__main__":
    unittest.main()
