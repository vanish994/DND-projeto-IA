"""O mapa tático foi removido: a tabela legada some na inicialização e as rotas não existem mais."""
import unittest

from sqlalchemy import create_engine, inspect, text

from backend.persistencia import RepositorioCampanhas


class RemocaoMapaTaticoTests(unittest.TestCase):
    def test_tabela_legada_e_apagada_na_inicializacao_e_e_idempotente(self):
        engine = create_engine("sqlite://")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE encontros_taticos (campanha_id TEXT PRIMARY KEY, estado TEXT, atualizado_em TEXT)"))
            conn.execute(text("INSERT INTO encontros_taticos VALUES ('c1', '{}', '2026-01-01')"))
        RepositorioCampanhas(engine=engine)
        self.assertNotIn("encontros_taticos", inspect(engine).get_table_names())
        RepositorioCampanhas(engine=engine)  # segunda inicialização não falha
        self.assertNotIn("encontros_taticos", inspect(engine).get_table_names())

    def test_rotas_do_mapa_nao_existem_mais(self):
        from backend import app as app_module
        caminhos = {getattr(r, "path", "") for r in app_module.app.routes}
        self.assertFalse([c for c in caminhos if "mapa-tatico" in c])


if __name__ == "__main__":
    unittest.main()
