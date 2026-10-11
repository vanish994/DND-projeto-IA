"""Motor determinístico de regras do projeto DND-projeto-IA."""

from .engine import Rule, RuleEngine, Resolution
from .core import ResultadoD20, bonus_proficiencia, modificador_atributo, resolver_teste_d20
from .combat_special import (
    cd_ataque_desarmado, resolver_agarrar, resolver_ataque_oportunidade,
    resolver_empurrar, resolver_escape_agarramento,
)
from .combat_geometry import (
    distancia_euclidiana, distancia_grade, espaco_por_tamanho,
    resolver_alcance, resolver_ataque_geometria, resolver_cobertura,
    resolver_linha_de_visao, resolver_queda,
)
from .combat_movement import (
    custo_movimento, resolver_ataque_subaquatico, resolver_montaria,
    resolver_movimento_especial, resolver_objeto, resolver_sentidos,
)
from .conditions import (
    CONDICOES, EstadoCondicoes, normalizar_condicao,
    resolver_efeitos_condicao, resolver_estado_condicao,
)
from .magic_equipment import (
    EstadoEquipamento, EstadoMagia, calcular_ca, resolver_alvo_magia,
    resolver_area_magia, resolver_arma, resolver_carga, resolver_conjuracao,
    resolver_duas_armas,
)
from .catalog import CATALOGO_ARMAS, CATALOGO_ARMADURAS, CATALOGO_EQUIPAMENTOS, CATALOGO_MAGIAS, buscar_catalogo, listar_catalogo
from .character import CLASSES, ESPECIES, SUBCLASSES, SUBCLASSES_RAVENLOFT, TALENTOS, Personagem, criar_personagem, gerar_atributos_compra_pontos, gerar_atributos_matriz_padrao, resolver_multiclasse, resolver_progressao
from .class_progression import FEATURES_BY_CLASS, SUBCLASSES_BY_CLASS, caracteristicas_no_nivel, subclasses_da_classe
from .martial import resolver_ataque_extra, resolver_ataque_furtivo, resolver_defletir_ataques, resolver_esquiva_sobrenatural, resolver_evasao, resolver_foco_monge, resolver_furia, resolver_maestria_arma, resolver_recuperar_folego
from .martial_subclasses import SUBCLASS_FEATURES, caracteristicas_subclasse, resolver_subclasse_marcial
from .spellcasters import resolver_canalizar_divindade, resolver_forma_selvagem, resolver_inspiracao_bardo, resolver_livro_de_magias, resolver_progressao_conjuracao
from .advanced_casters import resolver_bruxo, resolver_feiticeiro, resolver_guardiao
from .warlock_invocations import INVOCATIONS, resolver_invocacao, validar_invocacao
from .feats import EPIC_FEATS, FEATS, GENERAL_FEATS, ORIGIN_FEATS, resolver_talento, validar_talento
from .spells import ESCOLAS, MAGIAS, listar_magias, obter_magia, resolver_magia
from .economy import ITENS_MAGICOS, converter_de_po, converter_para_po, comprar_item, consultar_item, resolver_inventario, resolver_sintonizacao, usar_item_magico, vender_item
from .tactical import caminho_grade, resolver_ataque_tatico, resolver_flanco, resolver_linha_grade, resolver_terreno
from .class_features import resolver_caracteristica
from .bestiary import BESTIARIO, XP_POR_ND, consultar_bloco_completo, consultar_monstro, listar_monstros, resolver_bestiario, secao_monstro, xp_encontro, xp_por_nd
from .rules import build_default_engine
from .turns import EstadoTurno, Participante, RastreadorCombate, ordenar_iniciativa
from .survival import (
    EstadoVital, adicionar_exaustao, ajustar_dano, aplicar_dano, curar,
    descanso_curto, descanso_longo, resolver_descanso, salvaguarda_contra_morte, estabilizar,
)

__all__ = [
    "Rule", "RuleEngine", "Resolution", "ResultadoD20", "bonus_proficiencia",
    "modificador_atributo", "resolver_teste_d20", "build_default_engine",
    "Participante", "EstadoTurno", "RastreadorCombate", "ordenar_iniciativa",
    "cd_ataque_desarmado", "resolver_agarrar", "resolver_ataque_oportunidade",
    "resolver_empurrar", "resolver_escape_agarramento",
    "distancia_euclidiana", "distancia_grade", "espaco_por_tamanho",
    "resolver_alcance", "resolver_ataque_geometria", "resolver_cobertura",
    "resolver_linha_de_visao", "resolver_queda",
    "custo_movimento", "resolver_ataque_subaquatico", "resolver_montaria",
    "resolver_movimento_especial", "resolver_objeto", "resolver_sentidos",
    "CONDICOES", "EstadoCondicoes", "normalizar_condicao",
    "resolver_efeitos_condicao", "resolver_estado_condicao",
    "EstadoEquipamento", "EstadoMagia", "calcular_ca", "resolver_alvo_magia",
    "resolver_area_magia", "resolver_arma", "resolver_carga", "resolver_conjuracao",
    "resolver_duas_armas",
    "CATALOGO_ARMAS", "CATALOGO_ARMADURAS", "CATALOGO_EQUIPAMENTOS", "CATALOGO_MAGIAS",
    "buscar_catalogo", "listar_catalogo",
    "CLASSES", "ESPECIES", "SUBCLASSES", "SUBCLASSES_RAVENLOFT", "TALENTOS", "Personagem", "criar_personagem",
    "gerar_atributos_compra_pontos", "gerar_atributos_matriz_padrao", "resolver_multiclasse",
    "resolver_progressao",
    "FEATURES_BY_CLASS", "SUBCLASSES_BY_CLASS", "caracteristicas_no_nivel", "subclasses_da_classe",
    "resolver_ataque_extra", "resolver_ataque_furtivo", "resolver_defletir_ataques", "resolver_esquiva_sobrenatural", "resolver_evasao", "resolver_foco_monge", "resolver_furia", "resolver_maestria_arma", "resolver_recuperar_folego",
    "SUBCLASS_FEATURES", "caracteristicas_subclasse", "resolver_subclasse_marcial",
    "resolver_canalizar_divindade", "resolver_forma_selvagem", "resolver_inspiracao_bardo", "resolver_livro_de_magias", "resolver_progressao_conjuracao",
    "resolver_bruxo", "resolver_feiticeiro", "resolver_guardiao",
    "INVOCATIONS", "resolver_invocacao", "validar_invocacao",
    "EPIC_FEATS", "FEATS", "GENERAL_FEATS", "ORIGIN_FEATS", "resolver_talento", "validar_talento",
    "ESCOLAS", "MAGIAS", "listar_magias", "obter_magia", "resolver_magia",
    "ITENS_MAGICOS", "converter_de_po", "converter_para_po", "comprar_item", "consultar_item", "resolver_inventario", "resolver_sintonizacao", "usar_item_magico", "vender_item",
    "caminho_grade", "resolver_ataque_tatico", "resolver_flanco", "resolver_linha_grade", "resolver_terreno",
    "resolver_caracteristica",
    "BESTIARIO", "XP_POR_ND", "consultar_bloco_completo", "consultar_monstro", "listar_monstros", "resolver_bestiario", "secao_monstro", "xp_encontro", "xp_por_nd",
    "EstadoVital", "adicionar_exaustao", "ajustar_dano", "aplicar_dano", "curar",
    "descanso_curto", "descanso_longo", "salvaguarda_contra_morte", "estabilizar",
    "resolver_descanso",
]
