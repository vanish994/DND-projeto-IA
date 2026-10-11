import unittest

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
                    {"id": "aliado-teste", "kind": "hero", "character_id": self.hero["id"], "x": 2, "y": 1},
                ],
            })
            self.assertEqual(response.status_code, 200, response.text)
            response = self.client.post(self.url + "/conjurar", headers=self.headers, json={
                "atacante_id": "heroi-vex", "alvo_id": "aliado-teste", "magia": "Onda Trovejante",
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

    def test_ataque_fora_de_alcance_e_rejeitado(self):
        self.save_encounter(hero_x=1, hero_y=1, enemy_x=5, enemy_y=1)
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
