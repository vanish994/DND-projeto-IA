"""Reproduções locais de auditoria. SQLite em memória; nunca usa campanha real.

Não congela defeitos em assertions: imprime o comportamento atual para permitir
comparação após uma correção. Não chama APIs de IA nem consulta logs de produção.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend import app as backend
from backend.persistencia import RepositorioCampanhas
from integrations.deepseek_mj import DeepSeekMJ
from rule_engine import build_default_engine


class CotaSimulada(Exception):
    status_code = 429


class MJFalhaDepoisDaFerramenta:
    def responder(self, texto, historico, personagens, on_character_update, on_roll):
        mj = DeepSeekMJ.__new__(DeepSeekMJ)
        mj.engine = build_default_engine()
        mj._tool(
            "resolver_regra",
            {"fatos": {"type": "spell", "magia": "Curar Ferimentos", "character_id": personagens[0]["id"]}},
            personagens,
            on_character_update,
            on_roll,
        )
        raise CotaSimulada("Cota simulada depois de executar ferramenta")


def reproduzir():
    engine = build_default_engine()
    niveis = []
    for classe, recurso in [("guerreiro", "surto_de_acao"), ("monge", "corpo_e_mente")]:
        fatos = {"type": "class_feature", "classe": classe, "nivel": 1, "recurso": recurso}
        niveis.append({"fatos": fatos, "resultado": dict(engine.evaluate(fatos).outcome)})

    db = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    repo = RepositorioCampanhas(engine=db)
    jogador = "auditoria-local"
    campanha = repo.criar(jogador, "Auditoria efêmera")["id"]
    ficha = {
        "nome": "Auditoria",
        "classe": "mago",
        "especie": "humano",
        "nivel": 1,
        "pv_maximo": 10,
        "atributos": {"inteligencia": 16},
        "conjuracao": {
            "truques": [],
            "magias_preparadas": ["Curar Ferimentos"],
            "espacos_totais": {"1": 2},
            "espacos_restantes": {"1": 2},
        },
    }
    # Ficha sintética criada diretamente no repositório para isolar persistência.
    # Não é uma demonstração de legalidade de lista de magias dessa classe.
    personagem = repo.criar_personagem(jogador, campanha, {}, ficha)
    tentativas = []
    antes = backend.logger.disabled
    try:
        backend.logger.disabled = True
        for _ in range(2):
            status = 200
            try:
                backend._responder(MJFalhaDepoisDaFerramenta(), repo, jogador, campanha, "Conjuro e aguardo.")
            except HTTPException as error:
                status = error.status_code
            atual = repo.obter_personagem(jogador, campanha, personagem["id"])
            tentativas.append(
                {
                    "http": status,
                    "espacos_restantes": atual["conjuracao"]["espacos_restantes"],
                    "mensagens_salvas": len(repo.mensagens(jogador, campanha)),
                }
            )
    finally:
        backend.logger.disabled = antes
        db.dispose()
    return {
        "escopo": "Simulação local; não comprova incidente em produção.",
        "recursos_nivel_1": niveis,
        "falha_apos_ferramenta": {"espacos_antes": {"1": 2}, "tentativas": tentativas},
    }


if __name__ == "__main__":
    print(json.dumps(reproduzir(), ensure_ascii=False, indent=2))
