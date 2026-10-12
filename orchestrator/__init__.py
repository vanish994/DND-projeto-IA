"""Orquestrador de Ações do DND-projeto-IA.

Camada determinística entre o MJ conversacional e o Rule Engine. Não é um
terceiro cérebro e não contém regra de D&D: interpreta a intenção estruturada
do MJ, controla pré-condições, chama o motor, aplica o resultado ao estado
canônico sem duplicar efeitos e devolve um resultado estruturado.

    from orchestrator import Acao, OrquestradorAcoes

    orquestrador = OrquestradorAcoes()
    acao = Acao.de_ferramenta("resolver_regra", {"fatos": {
        "type": "ability_check", "skill": "atletismo", "character_id": "p1",
    }})
    resultado = orquestrador.executar(acao, personagens=[ficha])
"""

from .contratos import FERRAMENTAS_CONHECIDAS, Acao, ResultadoAcao
from .estado import consumir_espaco, resumo_autoritativo, texto_equipamento_antecedente
from .orquestrador import OrquestradorAcoes
from .rolagens import normalizar_rolagem

__all__ = [
    "FERRAMENTAS_CONHECIDAS",
    "Acao",
    "ResultadoAcao",
    "OrquestradorAcoes",
    "consumir_espaco",
    "normalizar_rolagem",
    "resumo_autoritativo",
    "texto_equipamento_antecedente",
]
