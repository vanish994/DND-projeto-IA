"""Contrato HTTP das condições de personagem (apply/remove/tick/query).

Cobre o caso de uso extraído para ``backend.services.condicoes_service``:
ativação com duração numérica ou textual, salvaguarda de fim de turno,
redução por tick, remoção com limpeza de metadados e validação de entrada.
"""

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

GUERREIRO = {
    "nome": "Vex",
    "especie": "humano",
    "classe": "guerreiro",
    "nivel": 1,
    "metodo_atributos": "matriz_padrao",
    "atributos": {"forca": 15, "destreza": 14, "constituicao": 13, "inteligencia": 12, "sabedoria": 10, "carisma": 8},
    "antecedente": "soldado",
    "aumentos_antecedente": {"forca": 2, "constituicao": 1},
    "ferramenta_antecedente": "Dados",
    "equipamento_antecedente": "A",
}


@unittest.skipUnless(DEPENDENCIAS, "fastapi/sqlalchemy/httpx não instalados")
class CondicoesPersonagemTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.repo = RepositorioCampanhas(engine=engine)
        backend_app.app.dependency_overrides[backend_app.obter_repositorio] = lambda: self.repo
        self.client = TestClient(backend_app.app)
        self.headers = {"X-Jogador-Id": "jogador-condicoes"}
        self.cid = self.client.post("/v1/campanhas", json={"titulo": "Condições"}, headers=self.headers).json()["id"]
        criado = self.client.post(f"/v1/campanhas/{self.cid}/personagens", json=GUERREIRO, headers=self.headers)
        assert criado.status_code == 201, criado.text
        self.pid = criado.json()["id"]
        self.url = f"/v1/campanhas/{self.cid}/personagens/{self.pid}/condicoes"

    def tearDown(self):
        backend_app.app.dependency_overrides.clear()

    def aplicar(self, **campos):
        return self.client.post(self.url, json={"operacao": "apply", **campos}, headers=self.headers)

    def test_aplicar_condicao_com_duracao_numerica(self):
        resposta = self.aplicar(condicao="enfeiticado", duracao=3)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["condicoes_ativas"], ["enfeiticado"])
        self.assertEqual(corpo["duracoes"], {"enfeiticado": 3})
        self.assertEqual(corpo["resolucao"]["resultado"], "aplicada")

    def test_aplicar_com_salvaguarda_fim_turno_registra_metadados(self):
        resposta = self.aplicar(
            condicao="paralisado",
            duracao="até o fim do próximo turno",
            salvaguarda_fim_turno={"cd": 14, "atributo": "sabedoria"},
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["salvaguardas_fim_condicoes"], {"paralisado": {"cd": 14, "atributo": "sabedoria"}})
        self.assertEqual(corpo["duracoes"]["paralisado"], "até o fim do próximo turno")

    def test_query_consulta_sem_alterar_estado(self):
        self.aplicar(condicao="enfeiticado", duracao=3)
        resposta = self.client.post(
            self.url, json={"operacao": "query", "condicao": "enfeiticado"}, headers=self.headers
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        self.assertEqual(resposta.json()["resolucao"]["resultado"], "ativa")

    def test_tick_reduz_duracao_numerica_e_preserva_textual(self):
        self.aplicar(condicao="enfeiticado", duracao=3)
        self.aplicar(condicao="paralisado", duracao="até o fim do próximo turno")
        resposta = self.client.post(self.url, json={"operacao": "tick"}, headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["duracoes"]["enfeiticado"], 2)
        self.assertEqual(corpo["duracoes"]["paralisado"], "até o fim do próximo turno")
        self.assertEqual(corpo["resolucao"]["resultado"], "durações_reduzidas")

    def test_tick_com_duracao_zerada_encerra_a_condicao(self):
        self.aplicar(condicao="enfeiticado", duracao=1)
        resposta = self.client.post(self.url, json={"operacao": "tick"}, headers=self.headers)
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["condicoes_ativas"], [])
        self.assertIn("enfeiticado", corpo["resolucao"]["encerradas"])

    def test_remove_limpa_condicao_duracao_e_metadados(self):
        self.aplicar(condicao="paralisado", duracao=2, salvaguarda_fim_turno={"cd": 14, "atributo": "sabedoria"})
        resposta = self.client.post(
            self.url, json={"operacao": "remove", "condicao": "paralisado"}, headers=self.headers
        )
        self.assertEqual(resposta.status_code, 200, resposta.text)
        corpo = resposta.json()
        self.assertEqual(corpo["condicoes_ativas"], [])
        self.assertEqual(corpo["duracoes"], {})
        self.assertEqual(corpo["salvaguardas_fim_condicoes"], {})
        self.assertEqual(corpo["resolucao"]["resultado"], "removida")

    def test_estado_fica_persistido_na_ficha(self):
        self.aplicar(condicao="enfeiticado", duracao=3)
        ficha = self.client.get(f"/v1/campanhas/{self.cid}/personagens/{self.pid}", headers=self.headers).json()
        self.assertEqual(ficha["condicoes_ativas"], ["enfeiticado"])
        self.assertEqual(ficha["duracoes_condicoes"], {"enfeiticado": 3})

    def test_aplicar_sem_condicao_e_invalido(self):
        resposta = self.aplicar()
        self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertEqual(resposta.json()["detail"], "Informe a condição para aplicar, remover ou consultar")

    def test_condicao_desconhecida_e_invalida(self):
        resposta = self.aplicar(condicao="condicao_inventada")
        self.assertEqual(resposta.status_code, 422, resposta.text)
        self.assertIn("Condição inválida", resposta.json()["detail"])


if __name__ == "__main__":
    unittest.main()
