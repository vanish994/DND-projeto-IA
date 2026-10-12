"""Sistema de magias do Livro do Jogador 2024.

O catálogo reaproveita as centenas de entradas extraídas do livro e adiciona
metadados executáveis, componentes, concentração, efeitos e escalonamento.
"""

from __future__ import annotations

import json
import pathlib
import re
import unicodedata
from typing import Any

from .catalog import CATALOGO_MAGIAS

ESCOLAS = {
    "abjuração",
    "adivinhação",
    "conjuração",
    "encantamento",
    "evocação",
    "ilusão",
    "necromancia",
    "transmutação",
}


def _nome_limpo(nome: str) -> str:
    nome = re.sub(r"\s+", " ", nome).strip(" -–")
    return nome


# Entradas do catálogo extraído que não são magias: fragmentos de frase, nomes de
# traços de classe, talentos ou subclasses. Não entram no catálogo de magias.
_NAO_SAO_MAGIAS = {
    "m",
    "r",
    "se",
    "use",
    "você",
    "nenhuma",
    "o mal",
    "orga",
    "magia",
    "círculo",
    "círculo ou",
    "mínimo de",
    "matar",
    "salvar",
    "mordenkainen",
    "mansão magnífica de",
    "atordoar",
    "incansável",
    "caçador preciso",
    "dádiva épica",
    "golpes abençoados aprimorados",
    "fortificar",
    "pacto da lâmina",
    "sentidos selvagens",
    "organizadas por círculo de magia e em ordem alfabéti",
    "você já tiver qualquer uma dessas opções de uma",
    "você não pode fazê-lo novamente até",
    "você pode causar ao alvo",
    "você pode causar à criatura 1d6 pontos",
    "quando você atinge uma criatura com uma jogada de",
    "e restaura todos os usos gastos ao completar",
    "de vida temporários igual a 1d8 mais seu modificador",
    "você não pode usar essa característica",
    "você pode converter usos de",
    "você tem vantagem em jogadas de ataque contra a",
    "você invoca espíritos da natureza para se esconder ma",
    "você pode conjurar salto em si sem gastar um espaço",
    "sofrer dano não quebra sua concentração da marca do",
    "ritual e m que necessita de um componente material",
}


def _normalizar_nome_magia(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nome).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).replace("-", " ")


# Nomes antigos em português (PHB 2014) e o nome do PHB 2024. O nome antigo continua no
# catálogo marcado com "alias_de"; o resolvedor usa sempre o nome do PHB 2024.
_ALIAS_PARA_2024 = (
    ("Mão Mágica", "Mãos Mágicas"),
    ("Consertar", "Reparar"),
    ("Benção", "Bênção"),
    ("Ver Invisibilidade", "Ver o Invisível"),
    ("Acelerar", "Celeridade"),
    ("Revificar", "Revivificar"),
    ("Pele de Pedra", "Pele-Rocha"),
    ("Moldar Pedra", "Moldar Rochas"),
    ("Liberdade de Movimento", "Movimentação Livre"),
    ("Respiração Aquática", "Respirar na Água"),
    ("Aquecer Metal", "Esquentar Metal"),
    ("Criar Alimentos e Água", "Criar Comida e Água"),
)


MAGIAS: dict[str, dict[str, Any]] = {}
for bruto, meta in CATALOGO_MAGIAS.items():
    partes = re.split(r"\s{2,}", bruto.strip())
    nome = _nome_limpo(partes[0])
    if (
        nome
        and nome.lower() not in {"a opção que você escolheu para golpes abençoados", "após usar", "como uma ação usar"}
        and nome.lower() not in _NAO_SAO_MAGIAS
    ):
        MAGIAS.setdefault(
            nome.lower(),
            {
                "nome": nome,
                "circulo": None,
                "escola": meta["escola"].lower(),
                "componentes": "V, S" + (", M" if meta.get("material") else ""),
                "concentracao": bool(meta.get("concentracao")),
                "ritual": bool(meta.get("ritual")),
                "duracao": "concentração" if meta.get("concentracao") else "instantânea",
            },
        )

# Entradas de referência com círculo, componentes e efeitos precisos do PHB 2024.
_DETALHADAS = {
    # PHB 2024, pp. 249, 324 e 340 (PDF local: páginas 255, 330 e 346).
    "bolha ácida": (
        0,
        "evocação",
        "V, S",
        False,
        "Escolha uma ou duas criaturas a até 18 m, cujos espaços estejam a até 1,5 m entre si; salvaguarda de Destreza evita 1d6 ácido",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "rajada de veneno": (
        0,
        "necromancia",
        "V, S",
        False,
        "Ataque mágico à distância; 1d12 dano venenoso; alcance 9 m",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "trovão": (
        0,
        "evocação",
        "S",
        False,
        "Emanação de 1,5 m; Constituição evita 1d6 trovejante; som audível a 30 m",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "armadura de agathys": (
        1,
        "abjuração",
        "V, S, M (um caco de vidro azul)",
        False,
        "5 PV temporários; 5 dano gélido ao atacante",
        {"pv_temporarios": "+5 por círculo", "dano_retorno": "+5 por círculo"},
    ),
    "mísseis mágicos": (
        1,
        "evocação",
        "V, S",
        False,
        "3 dardos de 1d4+1 dano energético",
        {"dardos": "+1 por círculo"},
    ),
    "raio de fogo": (
        0,
        "evocação",
        "V, S",
        False,
        "Ataque mágico à distância; 1d10 dano ígneo; alcance 36 m",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "escudo": (1, "abjuração", "V, S", False, "+5 CA até o início do próximo turno", {}),
    "curar ferimentos": (1, "necromancia", "V, S", False, "cura 2d8", {"cura": "+2d8 por círculo"}),
    "palavra curativa": (
        1,
        "abjuração",
        "V",
        False,
        "cura 2d4 + modificador de conjuração; alcance 18m; ação bônus",
        {"cura": "+2d4 por círculo"},
    ),
    "onda trovejante": (
        1,
        "evocação",
        "V, S",
        False,
        "2d8 dano trovejante; cubo de 4,5m; salvaguarda de Constituição reduz à metade; falha empurra 3m",
        {"dano": "+1d8 por círculo"},
    ),
    "mãos flamejantes": (
        1,
        "evocação",
        "V, S",
        False,
        "3d6 dano ígneo em cone de 4,5m; salvaguarda de Destreza reduz à metade",
        {"dano": "+1d6 por círculo"},
    ),
    "armadura arcana": (
        1,
        "abjuração",
        "V, S, M (um pedaço de couro curtido)",
        False,
        "CA base 13 + modificador de Destreza por 8 horas; alvo voluntário sem armadura",
        {},
    ),
    # PHB 2024, p. (Bênção): componentes com Símbolo Sagrado; concentração até 1 minuto.
    "bênção": (
        1,
        "encantamento",
        "V, S, M (um Símbolo Sagrado no valor de 5 PO ou mais)",
        True,
        "até três criaturas adicionam 1d4",
        {"alvos": "+1 por círculo"},
    ),
    "escudo da fé": (
        1,
        "abjuração",
        "V, S, M (um pergaminho com texto sagrado)",
        True,
        "+2 CA para uma criatura; duração de até 10 minutos; ação bônus",
        {},
    ),
    "bola de fogo": (
        3,
        "evocação",
        "V, S, M (uma bola de guano de morcego e enxofre)",
        False,
        "8d6 dano ígneo em esfera de 6m",
        {"dano": "+1d6 por círculo"},
    ),
    "relâmpago": (
        3,
        "evocação",
        "V, S, M (um pouco de pelo e uma haste de âmbar, cristal ou vidro)",
        False,
        "8d6 dano elétrico em linha",
        {"dano": "+1d6 por círculo"},
    ),
    "voo": (
        3,
        "transmutação",
        "V, S, M (uma pena de qualquer ave)",
        True,
        "deslocamento de voo 18m",
        {"alvos": "+1 por círculo"},
    ),
    "invisibilidade": (
        2,
        "ilusão",
        "V, S, M (uma pestana envolta em goma)",
        True,
        "condição Invisível",
        {"alvos": "+1 por círculo"},
    ),
    "passo nebuloso": (2, "conjuração", "V", False, "teleporta 9m", {}),
    "reviver os mortos": (
        5,
        "necromancia",
        "V, S, M (um diamante de 500 PO)",
        False,
        "retorna criatura morta à vida",
        {},
    ),
    "banimento": (
        4,
        "abjuração",
        "V, S, M (um item desagradável ao alvo)",
        True,
        "salvaguarda ou banido",
        {"alvos": "+1 por círculo"},
    ),
    "cura completa": (6, "necromancia", "V, S", False, "cura 70 PV", {"cura": "+10 por círculo"}),
    "infligir ferimentos": (
        1,
        "necromancia",
        "V, S",
        False,
        "Toque; Constituição evita 2d10 necrótico, metade em sucesso",
        {"dano": "+1d10 por círculo"},
    ),
    "comando": (
        1,
        "encantamento",
        "V",
        False,
        "Sabedoria evita; alvo segue um comando no próximo turno (Abaixar, Aproximar, Fugir, Largar, Parar)",
        {"alvos": "+1 por círculo"},
    ),
    "sono": (
        1,
        "encantamento",
        "V, S, M (uma pitada de areia ou pétalas de rosa)",
        True,
        "Esfera de 1,5 m; Sabedoria evita Incapacitado; segunda falha causa Inconsciente",
        {},
    ),
    "heroísmo": (
        1,
        "encantamento",
        "V, S",
        True,
        "Imune a Amedrontado; PV temporários igual ao modificador de conjuração a cada turno",
        {"alvos": "+1 por círculo"},
    ),
    "auxílio": (
        2,
        "abjuração",
        "V, S, M (uma tira de pano branco)",
        False,
        "até três criaturas: +5 PV máximos e atuais por 8 horas",
        {"pv": "+5 por círculo acima de 2"},
    ),
    "raio ardente": (
        2,
        "evocação",
        "V, S",
        False,
        "Até três raios; cada um exige ataque à distância e causa 2d6 Ígneo ao acertar; +1 raio por círculo acima de 2",
        {"raios": "+1 por círculo"},
    ),
    "teia": (
        2,
        "invocação",
        "V, S, M (um pouco de teia de aranha)",
        True,
        "Cubo de 6 m de teia (Terreno Difícil); Destreza evita Contido ao entrar ou começar o turno nela",
        {},
    ),
    "levitação": (
        2,
        "transmutação",
        "V, S, M (uma mola de metal)",
        True,
        "Alvo sobe até 6 m; Constituição evita se involuntário; carga de 200 kg",
        {},
    ),
    "dissipar magia": (
        3,
        "abjuração",
        "V, S",
        False,
        "Encerra automaticamente magias até o círculo do espaço usado; para magias de 4.º+, teste de atributo CD 10 + círculo",
        {},
    ),
    "contramagia": (
        3,
        "abjuração",
        "S",
        False,
        "Reação: criatura conjurando magia V/S/M faz salvaguarda de Constituição; se falhar, a magia se dissipa",
        {},
    ),
    "queda suave": (
        1,
        "transmutação",
        "V, M (uma pequena pena ou pedaço de penugem)",
        False,
        "Reação: até cinco criaturas caem a 18 m por rodada; sem dano de queda se pousarem",
        {},
    ),
    "restauração menor": (
        2,
        "abjuração",
        "V, S",
        False,
        "Bônus: remove uma condição (Cego, Envenenado, Paralisado ou Surdo)",
        {},
    ),
    "proteção contra veneno": (
        2,
        "abjuração",
        "V, S",
        False,
        "Encerra Envenenado; Vantagem em salvaguardas contra Envenenado; Resistência a dano Venenoso por 1 hora",
        {},
    ),
    "proteção contra energia": (
        3,
        "abjuração",
        "V, S",
        True,
        "Resistência a Ácido, Elétrico, Gélido, Ígneo ou Trovejante (escolha) por até 1 hora",
        {},
    ),
    "mãos mágicas": (
        0,
        "invocação",
        "V, S",
        False,
        "Mão espectral manipula objetos e move-se 9 m por uso de Usar Magia; carga de 5 kg; não ataca",
        {},
    ),
    "reparar": (
        0,
        "transmutação",
        "V, S, M (duas pedras-ímã)",
        False,
        "Repara uma ruptura de até 30 cm em um objeto; conjuração de 1 minuto",
        {},
    ),
    "acudir os moribundos": (
        0,
        "necromancia",
        "V, S",
        False,
        "Criatura com 0 PV e não morta fica Estável; alcance dobra nos níveis 5, 11 e 17",
        {"alcance": "dobra nos níveis 5, 11 e 17"},
    ),
    "chicote de espinhos": (
        0,
        "transmutação",
        "V, S, M (o caule de uma planta espinhosa)",
        False,
        "Ataque mágico corpo a corpo; 1d6 perfurante; puxa alvo Grande ou menor até 3 m",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "luz": (
        0,
        "evocação",
        "V, M (um vaga-lume ou musgo fosforescente)",
        False,
        "Objeto Grande ou menor emite Luz Plena de 6 m e Meia-luz por mais 6 m por 1 hora",
        {},
    ),
    "luzes dançantes": (
        0,
        "ilusão",
        "V, S, M (um pouco de fósforo)",
        True,
        "Até quatro luzes com Meia-luz de 3 m; mover 18 m como Ação Bônus",
        {},
    ),
    "mensagem": (
        0,
        "transmutação",
        "S, M (um fio de cobre)",
        False,
        "Sussurro a uma criatura no alcance, que pode responder; bloqueado por 30 cm de pedra, metal ou madeira",
        {},
    ),
    "orientação": (
        0,
        "adivinhação",
        "V, S",
        True,
        "Criatura voluntária adiciona 1d4 a testes de atributo com a perícia escolhida",
        {},
    ),
    "raio místico": (
        0,
        "evocação",
        "V, S",
        False,
        "Ataque mágico à distância; 1d10 energético; feixes: dois no nível 5, três no 11, quatro no 17",
        {"feixes": "+1 nos níveis 5, 11 e 17"},
    ),
    "raio de gelo": (
        0,
        "evocação",
        "V, S",
        False,
        "Ataque mágico à distância; 1d8 gélido; alvo tem deslocamento -3 m até o início do próximo turno dele",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "resistência": (
        0,
        "abjuração",
        "V, S",
        True,
        "Criatura voluntária reduz 1d4 do dano do tipo escolhido, uma vez por turno",
        {},
    ),
    "toque chocante": (
        0,
        "evocação",
        "V, S",
        False,
        "Ataque mágico corpo a corpo; 1d8 elétrico; alvo não faz Ataques de Oportunidade até o próximo turno dele",
        {"dano": "escala nos níveis 5, 11 e 17"},
    ),
    "alarme": (
        1,
        "abjuração",
        "V, S, M (um sino e um fio de prata)",
        False,
        "Alarme em porta, janela ou área de até 6 m; sonoro (18 m) ou mental (1,5 km); 8 horas; ritual",
        {},
    ),
    "detectar magia": (
        1,
        "adivinhação",
        "V, S",
        True,
        "Sente efeitos mágicos em 9 m; Usar Magia revela auras; até 10 minutos; ritual",
        {},
    ),
    "disfarçar-se": (
        1,
        "ilusão",
        "V, S",
        False,
        "Altera sua aparência (até 30 cm de altura, roupas e pertences) por 1 hora; falha em inspeção física",
        {},
    ),
    "fogo das fadas": (
        1,
        "evocação",
        "V",
        True,
        "Cubo de 6 m delineado: Destreza evita; Meia-luz de 3 m; sem Invisível; ataques com Vantagem",
        {},
    ),
    "graxa": (
        1,
        "invocação",
        "V, S, M (um pouco de banha de porco ou manteiga)",
        False,
        "Quadrado de 3 m vira Terreno Difícil por 1 minuto; Destreza evita Caído",
        {},
    ),
    "identificar": (
        1,
        "adivinhação",
        "V, S, M (uma pérola no valor de 100 ou mais PO)",
        False,
        "Revela propriedades, sintonização e cargas de item mágico, ou magias que afetam uma criatura; 1 minuto ou ritual",
        {},
    ),
    "purificar alimentos e bebidas": (
        1,
        "transmutação",
        "V, S",
        False,
        "Remove veneno e podridão de alimentos e bebidas não mágicos em Esfera de 1,5 m; ação ou ritual",
        {},
    ),
    "retirada acelerada": (1, "transmutação", "V, S", True, "Ação Bônus para executar Correr até 10 minutos", {}),
    "salto": (
        1,
        "transmutação",
        "V, S, M (perna traseira de um gafanhoto)",
        True,
        "Criatura voluntária salta 9 m gastando 3 m de movimento, uma vez por turno; 1 minuto",
        {"alvos": "+1 por círculo"},
    ),
    "vitalidade vazia": (
        1,
        "necromancia",
        "V, S, M (uma gota de álcool)",
        False,
        "2d4 + 4 PV temporários",
        {"pv": "+5 PV temporários por círculo acima de 1"},
    ),
    "santuário": (
        1,
        "abjuração",
        "V, S, M (o caco de um espelho)",
        False,
        "Atacante que mirar a criatura protegida faz salvaguarda de Sabedoria ou perde o ataque ou a magia",
        {},
    ),
}
for nome, (circulo, escola, componentes, conc, efeito, upcast) in _DETALHADAS.items():
    MAGIAS[nome] = {
        "nome": nome.title(),
        "circulo": circulo,
        "escola": escola,
        "componentes": componentes,
        "concentracao": conc,
        "ritual": False,
        "duracao": "concentração" if conc else "instantânea",
        "efeito": efeito,
        "upcasting": upcast,
    }

# Durações específicas que a regra genérica (concentração ou instantânea) não cobre.
for _nome, _duracao in {
    "auxílio": "8 horas",
    "santuário": "1 minuto",
    "sono": "concentração, até 1 minuto",
    "heroísmo": "concentração, até 1 minuto",
    "comando": "instantânea",
    "teia": "concentração, até 1 hora",
    "levitação": "concentração, até 10 minutos",
    "proteção contra energia": "concentração, até 1 hora",
    "proteção contra veneno": "1 hora",
    "queda suave": "1 minuto",
    "bênção": "concentração, até 1 minuto",
    "prestidigitação arcana": "até 1 hora",
    "mãos mágicas": "1 minuto",
    "luz": "1 hora",
    "luzes dançantes": "concentração, até 1 minuto",
    "mensagem": "1 rodada",
    "orientação": "concentração, até 1 minuto",
    "resistência": "concentração, até 1 minuto",
    "alarme": "8 horas",
    "detectar magia": "concentração, até 10 minutos",
    "disfarçar-se": "1 hora",
    "fogo das fadas": "concentração, até 1 minuto",
    "graxa": "1 minuto",
    "retirada acelerada": "concentração, até 10 minutos",
    "salto": "1 minuto",
}.items():
    MAGIAS[_nome]["duracao"] = _duracao

# O catálogo extraído contém entradas incompletas sem círculo. Para as magias
# da lista de Artífice, o círculo é conhecido e validado separadamente do efeito.
from .spellcasting import ARTIFICER_SPELL_LEVELS
from .spellcasting import normalizar_nome_magia as _normalizar_nome_spellcasting

for _nome_artifice, _circulo_artifice in ARTIFICER_SPELL_LEVELS.items():
    _chave_artifice = _normalizar_nome_spellcasting(_nome_artifice)
    _existente_artifice = next(
        (m for m in MAGIAS.values() if _normalizar_nome_spellcasting(m["nome"]) == _chave_artifice),
        None,
    )
    if _existente_artifice is not None:
        _existente_artifice["circulo"] = _circulo_artifice
    else:
        MAGIAS[_chave_artifice] = {
            "nome": _nome_artifice,
            "circulo": _circulo_artifice,
            "escola": "transmutação",
            "componentes": "V, S",
            "concentracao": False,
            "ritual": False,
            "duracao": "instantânea",
        }


from .spellcasting import CIRCULO_MAGIAS_SUBCLASSE as _CIRCULOS_SUB

for _nome_sub, _circulo_sub in _CIRCULOS_SUB.items():
    _chave_sub = _normalizar_nome_spellcasting(_nome_sub)
    _existente_sub = next((m for m in MAGIAS.values() if _normalizar_nome_spellcasting(m["nome"]) == _chave_sub), None)
    if _existente_sub is not None and _existente_sub.get("circulo") is None:
        _existente_sub["circulo"] = _circulo_sub

# Magias do PHB 2024 que faltavam no catálogo extraído (cabeçalho, componentes e duração
# conferidos no PDF). Usadas pelas listas de Artífice e de subclasse.
_PHB2024_COMPLEMENTAR = {
    # nome: (círculo, escola, componentes, concentração, duração ou None)
    "Aura de Pureza": (4, "abjuração", "V", True, None),
    "Convocar Relâmpagos": (3, "invocação", "V, S", True, None),
    "Círculo de Teleporte": (
        5,
        "invocação",
        "V, M (tintas raras no valor de 50 PO ou mais, que a magia consome)",
        False,
        "1 rodada",
    ),
    "Destruição Banidora": (5, "invocação", "V", True, None),
    "Esfera Vitriólica": (4, "evocação", "V, S, M (uma gota de bile)", False, None),
    "Invocar Barragem": (
        3,
        "invocação",
        "V, S, M (uma arma Corpo a Corpo ou à Distância que vale pelo menos 1 PP)",
        False,
        None,
    ),
    "Névoa Mortal": (5, "invocação", "V, S", True, None),
    "Palavra Curativa em Massa": (3, "abjuração", "V", False, None),
    "Proteção Contra a Morte": (4, "abjuração", "V, S", False, "8 horas"),
    "Raio Guia": (1, "evocação", "V, S", False, "1 rodada"),
}
for _m in MAGIAS.values():
    if _m["nome"] == "Prestidigitação Arcana":
        if _m.get("circulo") is None:
            _m["circulo"] = 0
        _m.setdefault("efeito", "Cria um dos oito efeitos menores; até três não instantâneos ativos ao mesmo tempo")
for _nome_c, (_circ, _esc, _comp, _conc, _dur) in _PHB2024_COMPLEMENTAR.items():
    if not any(m["nome"] == _nome_c for m in MAGIAS.values()):
        MAGIAS[_nome_c.lower()] = {
            "nome": _nome_c,
            "circulo": _circ,
            "escola": _esc,
            "componentes": _comp,
            "concentracao": _conc,
            "ritual": False,
            "duracao": _dur or ("concentração, até 10 minutos" if _conc else "instantânea"),
        }

# Círculo de magias do catálogo extraído que não tinham círculo (cabeçalhos do PHB 2024).
_CIRCULOS_PHB2024 = json.loads(
    (pathlib.Path(__file__).parent / "dados" / "circulos_phb2024.json").read_text(encoding="utf-8")
)["circulos"]
for _nome_d, _circ_d in _CIRCULOS_PHB2024.items():
    for _m in MAGIAS.values():
        if _m["nome"] == _nome_d and _m.get("circulo") is None:
            _m["circulo"] = int(_circ_d)

for _antigo, _novo in _ALIAS_PARA_2024:
    _entrada = MAGIAS.get(_antigo.lower())
    if _entrada is not None:
        _entrada["alias_de"] = _novo


# Mecânicas estruturadas para integrar o resultado da magia ao combate.
# Fórmulas são devolvidas como dados; o motor de combate continua responsável
# por rolagens, salvaguardas, aplicação de dano e atualização de estado.
MECANICAS_MAGIA: dict[str, dict[str, Any]] = {
    "bolha ácida": {
        "tipo": "dano_multialvo",
        "dados_dano_base": "1d6",
        "tipo_dano": "acido",
        "salvaguarda": "destreza",
        "sucesso_metade": False,
        "acao": "acao",
        "alcance_m": 18,
        "alcance_pes": 60,
        "alvos_maximos": 2,
        "distancia_entre_alvos_m": 1.5,
        "escala_niveis": [5, 11, 17],
    },
    "rajada de veneno": {
        "tipo": "ataque_magico",
        "dados_dano_base": "1d12",
        "tipo_dano": "venenoso",
        "alcance_m": 9,
        "alcance_pes": 30,
        "escala_niveis": [5, 11, 17],
        "acao": "acao",
    },
    "trovão": {
        "tipo": "dano_em_area",
        "dados_dano_base": "1d6",
        "tipo_dano": "trovejante",
        "salvaguarda": "constituicao",
        "sucesso_metade": False,
        "acao": "acao",
        "area": {"forma": "emanacao", "raio_m": 1.5, "origem": "conjurador", "exclui_conjurador": True},
        "som_audivel_m": 30,
        "escala_niveis": [5, 11, 17],
    },
    "raio de fogo": {
        "tipo": "ataque_magico",
        "dados_dano_base": "1d10",
        "tipo_dano": "igneo",
        "alcance_m": 36,
        "escala_niveis": [5, 11, 17],
    },
    "armadura de agathys": {
        "tipo": "pv_temporarios_e_dano_retorno",
        "pv_temporarios_por_nivel": 5,
        "dano_retorno_por_nivel": 5,
        "tipo_dano": "gelido",
        "gatilho": "acertado_por_ataque_corpo_a_corpo_enquanto_tem_pv_temporarios",
    },
    "mísseis mágicos": {
        "tipo": "dano_multialvo",
        "dardos_base": 3,
        "dardos_por_nivel": 1,
        "dano_por_dardo": "1d4+1",
        "tipo_dano": "energetico",
        "jogada_ataque": False,
    },
    "escudo": {
        "tipo": "defesa",
        "bonus_ca": 5,
        "duracao": "ate_inicio_do_proximo_turno",
        "gatilhos": ["atingido_por_ataque", "alvo_de_misseis_magicos"],
        "anula_dano_misseis_magicos": True,
        "acao": "reacao",
    },
    "curar ferimentos": {
        "tipo": "cura",
        "dados_cura_base": "2d8",
        "dados_cura_por_nivel": "2d8",
        "soma_modificador_conjuracao": True,
        "alcance": "toque",
    },
    "palavra curativa": {
        "tipo": "cura",
        "dados_cura_base": "2d4",
        "dados_cura_por_nivel": "2d4",
        "soma_modificador_conjuracao": True,
        "alcance_m": 18,
        "acao": "bonus",
    },
    "onda trovejante": {
        "tipo": "dano_em_area",
        "dados_dano_base": "2d8",
        "dados_dano_por_nivel": "1d8",
        "tipo_dano": "trovejante",
        "salvaguarda": "constituicao",
        "sucesso_metade": True,
        "area": {"forma": "cubo", "lado_m": 4.5, "origem": "conjurador"},
        "empurra_m": 3,
        "empurra_em_falha": True,
    },
    "mãos flamejantes": {
        "tipo": "dano_em_area",
        "dados_dano_base": "3d6",
        "dados_dano_por_nivel": "1d6",
        "tipo_dano": "igneo",
        "salvaguarda": "destreza",
        "sucesso_metade": True,
        "area": {"forma": "cone", "comprimento_m": 4.5, "origem": "conjurador"},
    },
    "armadura arcana": {
        "tipo": "defesa",
        "ca_base": 13,
        "adiciona_modificador_destreza": True,
        "duracao": "ate_8_horas",
        "exige_alvo_sem_armadura": True,
    },
    "bênção": {
        "tipo": "beneficio",
        "alvos_base": 3,
        "alvos_por_nivel": 1,
        "bonus": "1d4",
        "aplica_a": ["jogadas_de_ataque", "salvaguardas"],
        "concentracao": True,
    },
    "escudo da fé": {
        "tipo": "beneficio_defensivo",
        "bonus_ca": 2,
        "alcance_m": 18,
        "duracao": "ate_10_minutos",
        "concentracao": True,
        "acao": "bonus",
        "alvos_base": 1,
    },
    "bola de fogo": {
        "tipo": "dano_em_area",
        "dados_dano_base": "8d6",
        "dados_dano_por_nivel": "1d6",
        "tipo_dano": "igneo",
        "salvaguarda": "destreza",
        "sucesso_metade": True,
        "area": {"forma": "esfera", "raio_m": 6},
        "alcance_m": 45,
    },
    "relâmpago": {
        "tipo": "dano_em_area",
        "dados_dano_base": "8d6",
        "dados_dano_por_nivel": "1d6",
        "tipo_dano": "eletrico",
        "salvaguarda": "destreza",
        "sucesso_metade": True,
        "area": {"forma": "linha", "comprimento_m": 30, "largura_m": 1.5},
        "alcance_m": 30,
    },
    "voo": {
        "tipo": "movimento",
        "deslocamento_voo_m": 18,
        "duracao": "ate_10_minutos",
        "concentracao": True,
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "invisibilidade": {
        "tipo": "condicao",
        "condicao": "invisivel",
        "duracao": "ate_1_hora",
        "concentracao": True,
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "passo nebuloso": {
        "tipo": "teleporte",
        "distancia_m": 9,
        "acao": "bonus",
    },
    "cura completa": {
        "tipo": "cura",
        "pv_base": 70,
        "pv_por_nivel": 10,
        "remove_condicoes": ["cego", "surdo", "envenenado"],
    },
    "banimento": {
        "tipo": "controle",
        "salvaguarda": "carisma",
        "falha": "banido",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "infligir ferimentos": {
        "tipo": "dano_salvaguarda",
        "dados_dano_base": "2d10",
        "dados_dano_por_nivel": "1d10",
        "tipo_dano": "necrotico",
        "salvaguarda": "constituicao",
        "sucesso_metade": True,
        "alcance": "toque",
        "acao": "acao",
    },
    "comando": {
        "tipo": "controle_comando",
        "salvaguarda": "sabedoria",
        "alcance_m": 18,
        "acao": "acao",
        "comandos": ["abaixar", "aproximar", "fugir", "largar", "parar"],
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "sono": {
        "tipo": "controle_area",
        "salvaguarda": "sabedoria",
        "alcance_m": 18,
        "acao": "acao",
        "area": {"forma": "esfera", "raio_m": 1.5},
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "condicao_inicial": "incapacitado",
        "condicao_apos_segunda_falha": "inconsciente",
        "encerra_se_sofrer_dano": True,
        "imunes": ["nao_dorme", "imunidade_a_exaustao"],
    },
    "heroísmo": {
        "tipo": "beneficio",
        "alcance": "toque",
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "condicao_imune": ["amedrontado"],
        "pv_temporarios_por_turno": "modificador_de_conjuracao",
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "auxílio": {
        "tipo": "beneficio_pv_maximo",
        "alcance_m": 9,
        "acao": "acao",
        "duracao": "ate_8_horas",
        "alvos_base": 3,
        "pv_bonus_base": 5,
        "pv_bonus_por_nivel": 5,
    },
    "raio ardente": {  # alvos = número de raios (3 base, +1 por círculo acima de 2)
        "tipo": "ataque_magico",
        "dados_dano_base": "2d6",
        "tipo_dano": "igneo",
        "alcance_m": 36,
        "acao": "acao",
        "alvos_base": 3,
        "alvos_por_nivel": 1,
    },
    "teia": {
        "tipo": "area_controle",
        "salvaguarda": "destreza",
        "alcance_m": 18,
        "acao": "acao",
        "area": {"forma": "cubo", "lado_m": 6},
        "concentracao": True,
        "duracao": "ate_1_hora",
        "terreno_dificil": True,
        "obscurecido": "parcial",
        "condicao": "contido",
        "colapsa_sem_apoio": True,
    },
    "levitação": {
        "tipo": "controle_movimento",
        "salvaguarda": "constituicao",
        "alcance_m": 18,
        "acao": "acao",
        "altura_m": 6,
        "carga_kg": 200,
        "concentracao": True,
        "duracao": "ate_10_minutos",
        "alvos_base": 1,
    },
    "dissipar magia": {
        "tipo": "encerrar_magia",
        "alcance_m": 36,
        "acao": "acao",
        "circulo_base": 3,
        "dissipa_ate_espaco": True,
        "teste_atributo_cd_base": 10,
    },
    "contramagia": {
        "tipo": "interrupcao",
        "salvaguarda": "constituicao",
        "alcance_m": 18,
        "acao": "reacao",
        "gatilho": "criatura_conjurando_magia_verbal_somatica_ou_material",
    },
    "queda suave": {
        "tipo": "protecao_queda",
        "alcance_m": 18,
        "acao": "reacao",
        "alvos_base": 5,
        "taxa_queda_m_por_rodada": 18,
    },
    "restauração menor": {
        "tipo": "remover_condicao",
        "alcance": "toque",
        "acao": "bonus",
        "condicoes_removiveis": ["cego", "envenenado", "paralisado", "surdo"],
    },
    "proteção contra veneno": {
        "tipo": "protecao_condicao",
        "alcance": "toque",
        "acao": "acao",
        "duracao": "ate_1_hora",
        "condicao_removida": "envenenado",
        "vantagem_salvaguardas": ["envenenado"],
        "resistencia": ["venenoso"],
    },
    "proteção contra energia": {
        "tipo": "resistencia",
        "alcance": "toque",
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_hora",
        "tipos_escolha": ["acido", "eletrico", "gelido", "igneo", "trovejante"],
    },
    "mãos mágicas": {
        "tipo": "utilidade_mao_espectral",
        "alcance_m": 9,
        "acao": "acao",
        "duracao": "1_minuto",
        "mover_m": 9,
        "carga_max_kg": 5,
        "pode_atacar": False,
    },
    "reparar": {
        "tipo": "reparo",
        "alcance": "toque",
        "tempo_conjuracao": "1_minuto",
        "ruptura_max_cm": 30,
        "repara_item_magico_fisicamente": True,
        "restaura_magia": False,
    },
    "acudir os moribundos": {
        "tipo": "estabilizar",
        "alcance_m": 4.5,
        "escala_alcance_truque": True,
        "acao": "acao",
    },
    "chicote de espinhos": {
        "tipo": "ataque_magico",
        "ataque": "corpo_a_corpo",
        "dados_dano_base": "1d6",
        "tipo_dano": "perfurante",
        "alcance_m": 9,
        "acao": "acao",
        "puxa_m": 3,
        "puxa_tamanho_max": "grande",
    },
    "luz": {
        "tipo": "luz_objeto",
        "alcance": "toque",
        "acao": "acao",
        "objeto_tamanho_max": "grande",
        "luz_plena_m": 6,
        "meia_luz_m": 6,
    },
    "luzes dançantes": {
        "tipo": "luzes_moveis",
        "alcance_m": 36,
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "quantidade": 4,
        "meia_luz_raio_m": 3,
        "mover_m": 18,
        "acao_mover": "bonus",
    },
    "mensagem": {
        "tipo": "comunicacao",
        "alcance_m": 36,
        "acao": "acao",
        "duracao": "1_rodada",
        "bloqueio": "30 cm de pedra, metal ou madeira, ou fina folha de chumbo",
    },
    "orientação": {
        "tipo": "bonus_teste",
        "alcance": "toque",
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "dado_bonus": "1d4",
        "aplica_a": "teste_de_atributo_com_pericia",
    },
    "raio místico": {
        "tipo": "ataque_magico",
        "dados_dano_base": "1d10",
        "tipo_dano": "energetico",
        "alcance_m": 36,
        "acao": "acao",
        "alvos_base": 1,
        "escala_alvos_truque": True,
        "escala_dados_truque": False,
    },
    "raio de gelo": {
        "tipo": "ataque_magico",
        "dados_dano_base": "1d8",
        "tipo_dano": "gelido",
        "alcance_m": 18,
        "acao": "acao",
        "reduz_deslocamento_m": 3,
        "reducao_ate": "inicio_do_proximo_turno_do_alvo",
    },
    "resistência": {
        "tipo": "protecao_dano",
        "alcance": "toque",
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "reducao_dano_base": "1d4",
        "uma_vez_por_turno": True,
        "tipos_escolha": [
            "acido",
            "contundente",
            "cortante",
            "eletrico",
            "gelido",
            "igneo",
            "necrotico",
            "perfurante",
            "radiante",
            "trovejante",
            "venenoso",
        ],
    },
    "toque chocante": {
        "tipo": "ataque_magico",
        "ataque": "corpo_a_corpo",
        "dados_dano_base": "1d8",
        "tipo_dano": "eletrico",
        "alcance": "toque",
        "acao": "acao",
        "sem_ataques_oportunidade_ate": "inicio_do_proximo_turno_do_alvo",
    },
    "alarme": {
        "tipo": "protecao_area",
        "alcance_m": 9,
        "acao": "acao",
        "concentracao": False,
        "duracao": "ate_8_horas",
        "area_max_m": 6,
        "modos": ["mental", "sonoro"],
        "alcance_mental_m": 1500,
        "alcance_sonoro_m": 18,
    },
    # PHB 2024, p. 320 (Prestidigitação Arcana): um dos oito efeitos; até três não instantâneos ativos.
    "prestidigitação arcana": {
        "tipo": "utilidade",
        "alcance_m": 3,
        "acao": "acao",
        "concentracao": False,
        "duracao": "ate_1_hora",
        "max_efeitos_nao_instantaneos": 3,
        "modos": [
            "brincar_com_fogo",
            "criacao_menor",
            "efeito_sensorial",
            "limpar_ou_sujar",
            "marca_magica",
            "sensacao_ideal",
        ],
    },
    "detectar magia": {
        "tipo": "deteccao",
        "alcance": "pessoal",
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_10_minutos",
        "raio_m": 9,
    },
    "disfarçar-se": {
        "tipo": "ilusao_disfarce",
        "alcance": "pessoal",
        "acao": "acao",
        "concentracao": False,
        "duracao": "ate_1_hora",
        "altura_ajuste_cm": 30,
        "falha_em_inspecao_fisica": True,
        "teste_para_descobrir": "inteligencia_analise",
    },
    "fogo das fadas": {
        "tipo": "area_controle",
        "salvaguarda": "destreza",
        "alcance_m": 18,
        "acao": "acao",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "area": {"forma": "cubo", "lado_m": 6},
        "efeito": "delineado",
        "luz_meia_m": 3,
        "impede_invisivel": True,
        "vantagem_ataques_contra_alvo_visivel": True,
    },
    "graxa": {
        "tipo": "area_controle",
        "salvaguarda": "destreza",
        "alcance_m": 18,
        "acao": "acao",
        "concentracao": False,
        "duracao": "1_minuto",
        "area": {"forma": "quadrado", "lado_m": 3},
        "terreno_dificil": True,
        "condicao": "caido",
        "repete_ao_entrar_ou_terminar_turno": True,
    },
    "identificar": {
        "tipo": "identificacao",
        "alcance": "toque",
        "acao": "1_minuto_ou_ritual",
        "revela": ["propriedades", "sintonizacao", "cargas", "magias_ativas"],
    },
    "purificar alimentos e bebidas": {
        "tipo": "utilidade",
        "alcance_m": 3,
        "acao": "acao",
        "area": {"forma": "esfera", "raio_m": 1.5},
        "efeito": "remove_veneno_e_podridao_nao_magicos",
    },
    "retirada acelerada": {
        "tipo": "movimento",
        "acao": "bonus",
        "acao_concedida": "correr",
        "concentracao": True,
        "duracao": "ate_10_minutos",
    },
    "salto": {
        "tipo": "beneficio_movimento",
        "alcance": "toque",
        "acao": "bonus",
        "concentracao": True,
        "duracao": "ate_1_minuto",
        "salto_m": 9,
        "custo_movimento_m": 3,
        "usos_por_turno": 1,
        "alvos_base": 1,
        "alvos_por_nivel": 1,
    },
    "vitalidade vazia": {
        "tipo": "pv_temporarios",
        "alcance": "pessoal",
        "acao": "acao",
        "pv_temporarios_base": "2d4",
        "pv_temporarios_fixo": 4,
        "pv_temporarios_extra_por_nivel": 5,
    },
    "santuário": {
        "tipo": "protecao",
        "salvaguarda": "sabedoria",
        "alcance_m": 9,
        "acao": "bonus",
        "duracao": "ate_1_minuto",
        "nao_protege_contra": ["area"],
        "encerra_se": ["ataque", "magia", "dano", "conjurar_magia"],
    },
}


def _aplicar_escalonamento_mecanico(nome: str, magia: dict[str, Any], aumento: int) -> dict[str, Any] | None:
    chave_normalizada = _normalizar_nome_magia(nome)
    base = next(
        (mecanica for chave, mecanica in MECANICAS_MAGIA.items() if _normalizar_nome_magia(chave) == chave_normalizada),
        None,
    )
    if base is None:
        return None
    mecanica = dict(base)
    if "area" in base:
        mecanica["area"] = dict(base["area"])
    if "pv_temporarios_por_nivel" in base:
        mecanica["pv_temporarios"] = base["pv_temporarios_por_nivel"] * int(magia["circulo"] + aumento)
        mecanica["dano_retorno"] = base["dano_retorno_por_nivel"] * int(magia["circulo"] + aumento)
    if "dardos_base" in base:
        mecanica["dardos"] = base["dardos_base"] + base["dardos_por_nivel"] * aumento
    if "dados_dano_base" in base:
        dados_base = re.fullmatch(r"(\d+)d(\d+)", base["dados_dano_base"])
        dados_extra = re.fullmatch(r"(\d+)d(\d+)", base.get("dados_dano_por_nivel", "0d0"))
        if dados_base and dados_extra:
            quantidade = int(dados_base.group(1)) + int(dados_extra.group(1)) * aumento
            mecanica["dados_dano"] = f"{quantidade}d{dados_base.group(2)}"
    if "dados_cura_base" in base:
        dados_base = re.fullmatch(r"(\d+)d(\d+)", base["dados_cura_base"])
        dados_extra = re.fullmatch(r"(\d+)d(\d+)", base["dados_cura_por_nivel"])
        if dados_base and dados_extra:
            quantidade = int(dados_base.group(1)) + int(dados_extra.group(1)) * aumento
            mecanica["dados_cura"] = f"{quantidade}d{dados_base.group(2)}"
    if "alvos_base" in base:
        mecanica["alvos"] = base["alvos_base"] + base.get("alvos_por_nivel", 0) * aumento
    if "pv_base" in base:
        mecanica["pv_curados"] = base["pv_base"] + base["pv_por_nivel"] * aumento
    if "pv_temporarios_extra_por_nivel" in base:
        mecanica["pv_temporarios_extra"] = base["pv_temporarios_extra_por_nivel"] * aumento
    if base.get("dissipa_ate_espaco"):
        mecanica["dissipa_ate_circulo"] = base["circulo_base"] + aumento
    if "pv_bonus_base" in base:
        mecanica["pv_bonus"] = base["pv_bonus_base"] + base["pv_bonus_por_nivel"] * aumento
    return mecanica


def escala_de_truque(nivel_personagem: int) -> int:
    """Quantos dados de dano um truque tem no nível do personagem.

    O Livro do Jogador 2024 aumenta o dano dos truques nos níveis 5, 11 e 17;
    o texto do catálogo registra os mesmos marcos ("escala nos níveis 5, 11 e
    17"). O nível é o do personagem, não o do espaço de magia: truque não gasta
    espaço.
    """
    if nivel_personagem >= 17:
        return 4
    if nivel_personagem >= 11:
        return 3
    if nivel_personagem >= 5:
        return 2
    return 1


def _mecanica_base_normalizada(nome: str) -> dict[str, Any] | None:
    chave = _normalizar_nome_magia(nome)
    return next((m for k, m in MECANICAS_MAGIA.items() if _normalizar_nome_magia(k) == chave), None)


def mecanica_de_magia(
    nome: object,
    *,
    nivel_personagem: int = 1,
    aumento: int = 0,
) -> dict[str, Any] | None:
    """Mecânica estruturada da magia, com o escalonamento já aplicado.

    Magias de círculo 1 ou superior escalam pelo espaço usado (``aumento``);
    truques escalam pelo nível do personagem (5, 11 e 17). Devolve ``None``
    quando a magia não está no catálogo ou ainda não tem mecânica estruturada —
    nesse caso o motor não deve inventar dados de dano.
    """
    magia = obter_magia(str(nome or ""))
    if not magia:
        return None
    mecanica = _aplicar_escalonamento_mecanico(magia["nome"], magia, aumento)
    if mecanica is None:
        return None
    if magia.get("circulo") == 0:
        multiplicador = escala_de_truque(nivel_personagem)
        base_mec = _mecanica_base_normalizada(magia["nome"])
        if base_mec and base_mec.get("escala_alvos_truque"):
            mecanica["alvos"] = multiplicador * base_mec.get("alvos_base", 1)
        if base_mec and base_mec.get("escala_alcance_truque"):
            mecanica["alcance_m"] = base_mec["alcance_m"] * 2 ** (multiplicador - 1)
        base = str(mecanica.get("dados_dano") or mecanica.get("dados_dano_base") or "")
        casamento = re.fullmatch(r"(\d+)d(\d+)", base)
        if base_mec and base_mec.get("escala_dados_truque") is False:
            casamento = None  # ex.: Raio Místico escala feixes, não dados
        if casamento:
            quantidade = int(casamento.group(1)) * multiplicador
            mecanica["dados_dano"] = f"{quantidade}d{casamento.group(2)}"
            mecanica["dados_dano_base"] = mecanica["dados_dano"]
            mecanica["escala_truque"] = multiplicador
    return mecanica


def listar_magias(escola: str | None = None, circulo: int | None = None) -> list[dict[str, Any]]:
    resultado = list(MAGIAS.values())
    if escola:
        resultado = [m for m in resultado if m["escola"] == escola.lower()]
    if circulo is not None:
        resultado = [m for m in resultado if m["circulo"] is not None and m["circulo"] == int(circulo)]
    return sorted(
        resultado, key=lambda m: (m["circulo"] is None, m["circulo"] if m["circulo"] is not None else 99, m["nome"])
    )


def obter_magia(nome: str, _sem_alias: bool = False) -> dict[str, Any] | None:
    direta = MAGIAS.get(str(nome).strip().lower())
    if direta is not None and "alias_de" not in direta:
        return direta
    chave = _normalizar_nome_magia(nome)
    for magia in MAGIAS.values():
        if _normalizar_nome_magia(magia["nome"]) == chave and "alias_de" not in magia:
            return magia
    if not _sem_alias:
        for antigo, novo in _ALIAS_PARA_2024:
            if _normalizar_nome_magia(antigo) == chave:
                return obter_magia(novo, _sem_alias=True)
    return None


def _circulo_efetivo(base: int, usado: int) -> int:
    if not 0 <= usado <= 9:
        raise ValueError("O espaço de magia deve estar entre 0 e 9")
    if base == 0 and usado != 0:
        raise ValueError("Truques não usam espaços de magia")
    if base > 0 and usado == 0:
        raise ValueError("Magias de círculo 1 ou superior exigem espaço de magia")
    if usado < base:
        raise ValueError("O espaço usado não pode ser inferior ao círculo da magia")
    return usado - base


# Nomes do catálogo que pertencem ao PHB 2014 ou a suplementos, não ao PHB 2024.
# O projeto usa apenas regras de 2024: estes nomes são bloqueados, não resolvidos.
_FORA_DO_PHB_2024 = (
    "Absorver Elementos",
    "Armadilha",
    "Bebida Cáustica de Tasha",
    "Catapulta",
    "Congelamento",
    "Criar Fogueira",
    "Explosão de Espadas",
    "Pedra Mágica",
    "Sorvedouro de Vida",
    "Véu da Natureza",
)


def resolver_magia(fatos: dict) -> dict[str, Any]:
    nome = str(fatos.get("magia", fatos.get("spell", ""))).lower()
    for antigo, novo in _ALIAS_PARA_2024:
        if _normalizar_nome_magia(antigo) == _normalizar_nome_magia(nome):
            nome = novo.lower()
    magia = obter_magia(nome)
    if not magia:
        return {"resultado": "bloqueado", "motivo": "magia_desconhecida", "magia": nome}
    if any(_normalizar_nome_magia(n) == _normalizar_nome_magia(magia["nome"]) for n in _FORA_DO_PHB_2024):
        return {"resultado": "bloqueado", "motivo": "fora_do_phb_2024", "magia": magia["nome"]}
    if magia.get("circulo") is None:
        return {
            "resultado": "nao_implementado",
            "motivo": "magia_catalogada_sem_resolucao_especifica",
            "motivo_secundario": "circulo_da_magia_nao_catalogado",
            "magia": magia["nome"],
            "escola": magia["escola"],
        }
    if (
        _normalizar_nome_magia(magia["nome"]) == _normalizar_nome_magia("armadura arcana")
        and fatos.get("alvo_veste_armadura") is True
    ):
        return {"resultado": "bloqueado", "motivo": "alvo_ja_veste_armadura"}
    try:
        usado = int(fatos.get("espaco", fatos.get("spell_level", magia["circulo"])))
        aumento = _circulo_efetivo(magia["circulo"], usado)
    except (TypeError, ValueError) as erro:
        return {"resultado": "bloqueado", "motivo": "circulo_invalido", "detalhe": str(erro)}
    componentes = set(magia["componentes"].replace("(", ",").replace(")", ",").split(","))
    requeridos = {c.strip() for c in componentes if c.strip() in {"V", "S", "M"}}
    disponiveis = set(fatos.get("componentes_disponiveis", ["V", "S", "M"]))
    faltantes = requeridos - disponiveis
    if faltantes:
        return {"resultado": "bloqueado", "motivo": "componentes_ausentes", "faltantes": sorted(faltantes)}
    if magia["concentracao"] and fatos.get("concentrando") and fatos.get("nova_concentracao", True):
        encerra = fatos["concentrando"]
    else:
        encerra = None
    resultado = {
        "magia": magia["nome"],
        "circulo_base": magia["circulo"],
        "circulo_usado": usado,
        "upcasting": aumento,
        "escola": magia["escola"],
        "componentes": sorted(requeridos),
        "concentracao": magia["concentracao"],
        "duracao": magia["duracao"],
        "encerra_concentracao": encerra,
    }
    try:
        nivel = max(1, int(fatos.get("nivel_personagem", 1) or 1))
    except (TypeError, ValueError):
        nivel = 1
    if "efeito" not in magia or mecanica_de_magia(magia["nome"], nivel_personagem=nivel, aumento=aumento) is None:
        # Metadados do catálogo não bastam para executar uma magia com fidelidade.
        # Não declarar a conjuração resolvida enquanto o efeito específico não existir.
        resultado.update(
            {
                "resultado": "nao_implementado",
                "motivo": "magia_catalogada_sem_resolucao_especifica",
            }
        )
        return resultado
    resultado.update({"resultado": "conjurada", "efeito": magia["efeito"]})
    mecanica = mecanica_de_magia(magia["nome"], nivel_personagem=nivel, aumento=aumento)
    if mecanica is not None:
        resultado["mecanica"] = mecanica
    if aumento and magia.get("upcasting"):
        resultado["escalonamento"] = magia["upcasting"]
    return resultado


def suporte_magia(nome: str) -> dict[str, Any]:
    """Capacidades reais, não uma promessa de aplicação de todo efeito catalogado."""
    mecanica = mecanica_de_magia(nome)
    chave = _normalizar_nome_magia(nome)
    tatico = chave in {
        "raio de fogo",
        "rajada de veneno",
        "trovao",
        "bolha acida",
        "curar ferimentos",
        "onda trovejante",
    }
    parcial = chave == "onda trovejante"  # Empurrão ainda não move os tokens.
    if not mecanica:
        rotulo = "Sem mecânica implementada"
    elif parcial:
        rotulo = "Regra estruturada, parcial"
    else:
        rotulo = "Regra estruturada"
    return {
        "mecanica_estruturada": mecanica is not None,
        "mapa_tatico": tatico,
        "parcial": parcial,
        "rotulo": rotulo,
        "restricao_mapa": "Apenas Artífice; exige registro na ficha",
    }
