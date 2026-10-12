"""Concorrência do compare-and-set de fichas em ``RepositorioCampanhas``.

Duas confirmações simultâneas que atualizam a mesma ficha partindo do mesmo
snapshot devem ter exatamente uma vencedora: a outra recebe
``ConflitoEstadoCampanha``, não sobrescreve o resultado e não grava mensagens.
Fichas distintas na mesma campanha não podem gerar conflito falso.
"""

import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend.persistencia import ConflitoEstadoCampanha, RepositorioCampanhas

FICHA_BASE = {
    "nome": "Tessa",
    "classe": "artifice",
    "especie": "humano",
    "nivel": 1,
    "pv_maximo": 10,
    "atributos": {"inteligencia": 16},
}

JOGADOR = "jogador-conc"


class AtualizacaoConcorrenteDeFichaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        url = "sqlite:///" + str(Path(self._tmp.name) / "campanha.db")
        self.repo = RepositorioCampanhas(url)
        self.cid = self.repo.criar(JOGADOR, "Concorrência")["id"]
        self.personagem = self.repo.criar_personagem(JOGADOR, self.cid, {}, dict(FICHA_BASE))

    def tearDown(self):
        self.repo.engine.dispose()
        self._tmp.cleanup()

    def test_duas_atualizacoes_concorrentes_da_mesma_ficha_exatamente_uma_vence(self):
        snapshot = copy.deepcopy(self.personagem)
        barreira = threading.Barrier(2)
        vitorias: list[tuple[str, dict]] = []
        conflitos: list[ConflitoEstadoCampanha] = []

        def confirmar(marcador: str) -> None:
            barreira.wait(timeout=10)
            try:
                resultado = self.repo.registrar_troca(
                    JOGADOR,
                    self.cid,
                    f"Ação {marcador}",
                    f"Resultado {marcador}",
                    atualizacoes_ficha={self.personagem["id"]: {"nome": "Tessa", "marcador": marcador}},
                    fichas_esperadas={self.personagem["id"]: snapshot},
                )
            except ConflitoEstadoCampanha as exc:
                conflitos.append(exc)
            else:
                vitorias.append((marcador, resultado))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [pool.submit(confirmar, marcador) for marcador in ("alfa", "beta")]
            for futuro in futuros:
                futuro.result(timeout=30)

        # Invariante do compare-and-set: exatamente uma confirmação vence.
        self.assertEqual(len(vitorias), 1, f"esperava 1 vencedora, houve {len(vitorias)}")
        self.assertEqual(len(conflitos), 1, f"esperava 1 conflito, houve {len(conflitos)}")

        # A resposta perdedora não sobrescreve a ficha nem grava mensagens.
        vencedor, _ = vitorias[0]
        atual = self.repo.obter_personagem(JOGADOR, self.cid, self.personagem["id"])
        self.assertEqual(atual["marcador"], vencedor)
        self.assertEqual(len(self.repo.mensagens(JOGADOR, self.cid) or []), 2)
        self.assertEqual(
            [m["conteudo"] for m in self.repo.mensagens(JOGADOR, self.cid)],
            [f"Ação {vencedor}", f"Resultado {vencedor}"],
        )

    def test_atualizacoes_concorrentes_de_fichas_diferentes_nao_conflitam(self):
        segunda = self.repo.criar_personagem(JOGADOR, self.cid, {}, dict(FICHA_BASE))
        snapshots = {
            self.personagem["id"]: copy.deepcopy(self.personagem),
            segunda["id"]: copy.deepcopy(segunda),
        }
        barreira = threading.Barrier(2)

        def confirmar(personagem_id: str, marcador: str) -> dict:
            barreira.wait(timeout=10)
            return self.repo.registrar_troca(
                JOGADOR,
                self.cid,
                f"Ação {marcador}",
                f"Resultado {marcador}",
                atualizacoes_ficha={personagem_id: {"nome": "Tessa", "marcador": marcador}},
                fichas_esperadas={personagem_id: snapshots[personagem_id]},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futuros = [
                pool.submit(confirmar, self.personagem["id"], "alfa"),
                pool.submit(confirmar, segunda["id"], "beta"),
            ]
            for futuro in futuros:
                futuro.result(timeout=30)

        # Sem conflito falso: cada ficha mantém a própria atualização.
        self.assertEqual(self.repo.obter_personagem(JOGADOR, self.cid, self.personagem["id"])["marcador"], "alfa")
        self.assertEqual(self.repo.obter_personagem(JOGADOR, self.cid, segunda["id"])["marcador"], "beta")
        self.assertEqual(len(self.repo.mensagens(JOGADOR, self.cid) or []), 4)

    def test_snapshot_antigo_de_ficha_ja_atualizada_e_rejeitado(self):
        snapshot = copy.deepcopy(self.personagem)
        self.repo.registrar_troca(
            JOGADOR,
            self.cid,
            "Ação alfa",
            "Resultado alfa",
            atualizacoes_ficha={self.personagem["id"]: {"nome": "Tessa", "marcador": "alfa"}},
            fichas_esperadas={self.personagem["id"]: snapshot},
        )
        with self.assertRaises(ConflitoEstadoCampanha):
            self.repo.registrar_troca(
                JOGADOR,
                self.cid,
                "Ação beta",
                "Resultado beta",
                atualizacoes_ficha={self.personagem["id"]: {"nome": "Tessa", "marcador": "beta"}},
                fichas_esperadas={self.personagem["id"]: snapshot},
            )
        atual = self.repo.obter_personagem(JOGADOR, self.cid, self.personagem["id"])
        self.assertEqual(atual["marcador"], "alfa")


if __name__ == "__main__":
    unittest.main()
