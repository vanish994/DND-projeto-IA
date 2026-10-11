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
        self.assertIn("roll", body["ataque"])
        bandido = next(t for t in body["mapa"]["tokens"] if t["id"] == "inimigo-bandido")
        self.assertEqual(bandido["hp"], 11 - body["dano"])

    def test_ataque_fora_de_alcance_e_rejeitado(self):
        self.save_encounter(hero_x=1, hero_y=1, enemy_x=5, enemy_y=1)
        response = self.client.post(self.url + "/atacar", headers=self.headers, json={
            "atacante_id": "heroi-vex", "alvo_id": "inimigo-bandido",
        })
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
