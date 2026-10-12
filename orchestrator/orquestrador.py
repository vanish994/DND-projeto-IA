"""Orquestrador de Ações: o fluxo determinístico entre MJ, motor e estado.

Camada intermediária entre o MJ conversacional e o Rule Engine. Ela **não é um
terceiro cérebro**: não narra, não decide regra e não inventa mecânica. As seis
responsabilidades são:

1. interpretar o pedido estruturado do MJ (:class:`~orchestrator.contratos.Acao`);
2. despachar a ação ao subsistema correto do Rule Engine;
3. controlar pré-condições (personagem, alvo, magia, espaço, proficiência);
4. executar e registrar a alteração no estado canônico sem duplicar efeito;
5. devolver resultado estruturado com motivo explícito de recusa;
6. manter MJ, ficha e combate lendo o mesmo estado.

Regra de fronteira: este módulo **não resolve mecânica**. Ele prepara fatos,
chama ``engine.evaluate`` e relata o que o motor decidiu. Toda decisão
mecânica continua em ``rule_engine``; se algo não está implementado, o
resultado é ``bloqueado`` com motivo — nunca um palpite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from rule_engine import PERICIAS, RuleEngine, build_default_engine
from rule_engine.bestiary import consultar_monstro
from rule_engine.catalog import CATALOGO_ARMAS
from rule_engine.character import PROFICIENCIAS_CLASSE
from rule_engine.damage import aplicar_defesas_monstro
from rule_engine.spellcasting import (
    ARTIFICER_SPELL_LEVELS,
    circulo_magia_subclasse,
    magia_sempre_preparada_do_artifice,
    normalizar_nome_magia,
    progresso_artifice,
)
from rule_engine.spells import obter_magia

from .contratos import Acao, ResultadoAcao
from .estado import consumir_espaco
from .preparo import (
    NOMES_ATAQUE_DE_SOPRO,
    normalizar_texto,
    preparar_ataque_de_magia,
    preparar_dano_de_magia,
    resolver_ataque_de_sopro,
)
from .rolagens import normalizar_rolagem

ATRIBUTOS = ("forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma")

# Aliases que o modelo costuma usar para atributos e perícias.
ALIASES_ATRIBUTO = {
    "str": "forca",
    "strength": "forca",
    "for": "forca",
    "dex": "destreza",
    "dexterity": "destreza",
    "des": "destreza",
    "con": "constituicao",
    "constitution": "constituicao",
    "int": "inteligencia",
    "intelligence": "inteligencia",
    "wis": "sabedoria",
    "wisdom": "sabedoria",
    "sab": "sabedoria",
    "cha": "carisma",
    "charisma": "carisma",
    "car": "carisma",
}

ALIASES_PERICIA = {
    "athletics": "atletismo",
    "acrobatics": "acrobacia",
    "animal_handling": "adestrar_animais",
    "lidar_com_animais": "adestrar_animais",
    "sleight_of_hand": "prestidigitacao",
    "stealth": "furtividade",
    "arcana": "arcanismo",
    "history": "historia",
    "insight": "intuicao",
    "intimidation": "intimidacao",
    "investigation": "investigacao",
    "medicine": "medicina",
    "nature": "natureza",
    "perception": "percepcao",
    "performance": "atuacao",
    "persuasion": "persuasao",
    "religion": "religiao",
    "survival": "sobrevivencia",
    "deception": "enganacao",
}

# Chaves que o preparo derivou da ficha/catálogo e que o MJ deve receber de
# volta junto do resultado para narrar exatamente o que foi usado.
CHAVES_DERIVADAS = (
    "character_id",
    "proficiency_applied",
    "modifier_source",
    "weapon",
    "weapon_damage",
    "damage_type",
    "damage_modifier",
    "attack_ability",
    "target_name",
    "magia",
    "spell_attack",
    "spell_attack_ability",
    "magia_tipo_dano",
    "magia_alcance_m",
    "escala_truque",
    "aumento",
    "magia_salvaguarda",
    "magia_sucesso_metade",
    "magia_area",
    "cd_magia",
    "magia_atributo",
)


@dataclass
class _Preparo:
    """Fatos prontos para o motor + o que o orquestrador precisa aplicar depois."""

    fatos: dict[str, Any]
    personagem_magia: dict[str, Any] | None = None
    slot_a_consumir: str | None = None


# Operação composta: conjuração + dano + salvaguardas de área em uma única
# chamada de ferramenta. Aliases aceitos; o canônico é "area_spell".
TIPOS_MAGIA_DE_AREA = {"area_spell", "spell_area", "magia_de_area"}


class OrquestradorAcoes:
    """Coordena MJ, Rule Engine e estado canônico."""

    def __init__(self, engine: RuleEngine | None = None) -> None:
        self.engine = engine or build_default_engine()
        # Rolagens da última ação, em ordem de resolução.
        self.rolagens: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------
    def executar(
        self,
        acao: Acao,
        personagens: list[dict[str, Any]] | None = None,
        on_alteracao: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
        on_rolagem: Callable[[dict[str, Any]], None] | None = None,
    ) -> ResultadoAcao:
        """Executa a ação: pré-condições, motor, estado e rolagens."""
        if acao.ferramenta not in {"sugerir_monstros", "consultar_monstro", "resolver_regra"}:
            return ResultadoAcao.bloqueado("ferramenta_desconhecida")

        fatos = acao.para_fatos()
        preparo = _Preparo(fatos)
        personagem_magia: dict[str, Any] | None = None
        slot_a_consumir: str | None = None

        if acao.ferramenta == "resolver_regra":
            if str(fatos.get("type", "")).strip().lower() in TIPOS_MAGIA_DE_AREA:
                return self._executar_magia_de_area(fatos, personagens, on_alteracao, on_rolagem)
            pronto = self._preparar(fatos, personagens)
            if isinstance(pronto, ResultadoAcao):
                # Recusa ou resolução direta (ex.: Ataque de Sopro): as rolagens
                # que já existirem também são anunciadas.
                self._registrar(pronto.rolagens, on_rolagem)
                return pronto
            preparo = pronto
            fatos = preparo.fatos
            personagem_magia = preparo.personagem_magia
            slot_a_consumir = preparo.slot_a_consumir

        resolucao = self.engine.evaluate(fatos)
        resultado: dict[str, Any] = {"status": resolucao.status, **dict(resolucao.outcome)}

        self._pos_processar_resolucao(fatos, resultado)

        alteracoes = self._aplicar_estado(fatos, resultado, personagem_magia, slot_a_consumir, on_alteracao)
        rolagens = self._coletar_rolagens(fatos, resultado, personagens, on_rolagem)
        return ResultadoAcao(resolucao.status, resultado, alteracoes, rolagens)

    def executar_ferramenta(
        self,
        nome: str,
        argumentos: Mapping[str, Any] | None = None,
        personagens: list[dict[str, Any]] | None = None,
        on_alteracao: Callable[[dict[str, Any], dict[str, Any]], None] | None = None,
        on_rolagem: Callable[[dict[str, Any]], None] | None = None,
    ) -> ResultadoAcao:
        """Conveniência para o adaptador do MJ: ferramenta + argumentos → ação."""
        return self.executar(Acao.de_ferramenta(nome, argumentos), personagens, on_alteracao, on_rolagem)

    # ------------------------------------------------------------------
    # Pré-condições e preparo (responsabilidades 1 e 3)
    # ------------------------------------------------------------------
    @staticmethod
    def _personagem(personagem_id: Any, personagens: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        """Localiza a ficha; sem id e com um único personagem, usa essa ficha."""
        grupo = personagens or []
        ficha = next((p for p in grupo if p.get("id") == personagem_id), None)
        if ficha is None and not personagem_id and len(grupo) == 1:
            ficha = grupo[0]
        return ficha

    def _preparar(self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None) -> _Preparo | ResultadoAcao:
        """Encaminha a ação ao subsistema correto e monta os fatos do motor."""
        tipo = fatos.get("type")
        if tipo == "class_feature":
            return self._preparar_caracteristica(fatos, personagens)
        if tipo in {"attack", "initiative"}:
            return self._preparar_ataque(fatos, personagens)
        if tipo == "damage" and str(fatos.get("magia", fatos.get("spell", ""))).strip():
            return self._preparar_dano(fatos, personagens)
        if tipo == "ability_check":
            return self._preparar_teste_habilidade(fatos, personagens)
        if tipo in {"saving_throw", "saving_throw_check"}:
            return self._preparar_salvaguarda(fatos, personagens)
        if tipo in {"spell", "spell_cast", "cast_spell", "conjurar"} and fatos.get("magia"):
            return self._preparar_conjuracao(fatos, personagens)
        # Bestiário e demais operações não exigem preparo: vão direto ao motor.
        return _Preparo(fatos)

    def _preparar_caracteristica(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Característica de classe: classe e nível vêm da ficha, nunca do modelo."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")
        nivel = int(ficha.get("nivel", 1) or 1)
        fatos.update(
            {
                "classe": ficha.get("classe", ""),
                "nivel": ficha.get("nivel", 1),
                "character_id": ficha["id"],
                "modifier_source": "ficha_autoritativa",
            }
        )
        for atributo in ATRIBUTOS:
            fatos.pop(atributo, None)
            if atributo in (ficha.get("atributos") or {}):
                fatos[atributo] = ficha["atributos"][atributo]
        fatos["bonus_proficiencia"] = ficha.get("bonus_proficiencia", 2 + (nivel - 1) // 4)
        return _Preparo(fatos)

    def _preparar_ataque(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Ataque com arma, ataque de magia, ataque de sopro ou iniciativa."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")

        if fatos.get("type") == "initiative":
            modificador = self._modificador(ficha, "destreza")
            if modificador is None:
                return ResultadoAcao.bloqueado("destreza_ausente_na_ficha")
            fatos["modifier"] = modificador
            fatos["character_id"] = ficha.get("id")
            fatos["modifier_source"] = "ficha_autoritativa"
            return _Preparo(fatos)

        if str(fatos.get("magia", fatos.get("spell", ""))).strip():
            # Truques e magias com jogada de ataque: o motor deriva o bônus de
            # conjuração da ficha e a CA do bestiário, como faz com armas.
            preparo = preparar_ataque_de_magia(self.engine, fatos, ficha)
            if "fatos" not in preparo:
                return ResultadoAcao(preparo.get("resultado", "bloqueado"), dict(preparo))
            return _Preparo(preparo["fatos"])

        return self._preparar_ataque_com_arma(fatos, ficha, personagens)

    def _preparar_ataque_com_arma(
        self,
        fatos: dict[str, Any],
        ficha: dict[str, Any],
        personagens: list[dict[str, Any]] | None,
    ) -> _Preparo | ResultadoAcao:
        """Ataque com arma do catálogo, ou o Ataque de Sopro do Draconato."""
        nome_arma = str(fatos.get("weapon", fatos.get("arma", ""))).strip()
        # O Ataque de Sopro do Draconato é um traço de espécie, não uma arma:
        # resolve por salvaguarda de Destreza, com CD e dano do traço.
        arma_normalizada = normalizar_texto(nome_arma)
        if arma_normalizada in {normalizar_texto(x) for x in NOMES_ATAQUE_DE_SOPRO} or (
            "sopro" in arma_normalizada and any(palavra in arma_normalizada for palavra in ("arma", "ataque"))
        ):
            sopro = resolver_ataque_de_sopro(self.engine, fatos, ficha, personagens)
            resultado_sopro = sopro.get("resultado")
            if isinstance(resultado_sopro, str):
                # O preparo recusou (herança ausente, alvo desconhecido...).
                return ResultadoAcao("bloqueado", dict(sopro))
            return ResultadoAcao("resolvido", dict(resultado_sopro), [], list(sopro.get("rolagens") or []))

        nome_canonico = next((k for k in CATALOGO_ARMAS if k.casefold() == nome_arma.casefold()), None)
        arma = CATALOGO_ARMAS.get(nome_canonico) if nome_canonico else None
        if arma is None:
            return ResultadoAcao.bloqueado("arma_nao_encontrada_no_catalogo", arma=nome_arma)

        recusa = self._verificar_proficiencia_na_arma(ficha, nome_canonico)
        if recusa is not None:
            return recusa

        atributos = ficha.get("atributos") or {}
        propriedades = set(arma.get("propriedades", []))
        if "acuidade" in propriedades:
            if not all(k in atributos or k in (ficha.get("modificadores") or {}) for k in ("forca", "destreza")):
                return ResultadoAcao.bloqueado("atributos_para_arma_ausentes_na_ficha")
            forca = self._modificador(ficha, "forca")
            destreza = self._modificador(ficha, "destreza")
            atributo_ataque = "forca" if forca >= destreza else "destreza"
            modificador_atributo = max(forca, destreza)
        elif "municao" in propriedades:
            atributo_ataque = "destreza"
            modificador_atributo = self._modificador(ficha, "destreza")
            if modificador_atributo is None:
                return ResultadoAcao.bloqueado("destreza_ausente_na_ficha")
        else:
            atributo_ataque = "forca"
            modificador_atributo = self._modificador(ficha, "forca")
            if modificador_atributo is None:
                return ResultadoAcao.bloqueado("forca_ausente_na_ficha")

        nivel = max(1, int(ficha.get("nivel", 1) or 1))
        bonus_proficiencia = int(ficha.get("bonus_proficiencia", 2 + (nivel - 1) // 4))
        fatos.update(
            {
                "modifier": modificador_atributo + bonus_proficiencia,
                "character_id": ficha.get("id"),
                "proficiency_applied": bonus_proficiencia,
                "modifier_source": "ficha_autoritativa",
                "weapon": nome_canonico,
                "weapon_damage": arma["dano"],
                "damage_type": arma["tipo"],
                "damage_modifier": modificador_atributo,
                "attack_ability": atributo_ataque,
            }
        )

        alvo_nome = str(fatos.get("target_name", fatos.get("alvo", ""))).strip()
        if not alvo_nome:
            return ResultadoAcao.bloqueado("nome_do_alvo_ausente")
        alvo = consultar_monstro(alvo_nome)
        if alvo is None:
            return ResultadoAcao.bloqueado("monstro_desconhecido_no_bestiario", alvo=alvo_nome)
        # A CA vem sempre do catálogo oficial; nunca de uma CA fornecida pelo modelo.
        fatos["target_ac"] = int(alvo["ca"])
        fatos["target_name"] = alvo["nome"]
        return _Preparo(fatos)

    @staticmethod
    def _modificador(ficha: Mapping[str, Any], atributo: str) -> int | None:
        """Modificador do atributo a partir da ficha (explícito ou calculado)."""
        if atributo in (ficha.get("modificadores") or {}):
            return int(ficha["modificadores"][atributo])
        if atributo in (ficha.get("atributos") or {}):
            return (int(ficha["atributos"][atributo]) - 10) // 2
        return None

    @staticmethod
    def _verificar_proficiencia_na_arma(ficha: Mapping[str, Any], nome_canonico: str) -> ResultadoAcao | None:
        """Confere a proficiência de arma da classe; devolve recusa ou ``None``."""
        classe = str(ficha.get("classe", "")).strip().lower()
        prof_classe = PROFICIENCIAS_CLASSE.get(classe, {}).get("armas", [])
        # Mesma classificação usada pelo combate tático do backend.
        simples = {
            "clava",
            "clava grande",
            "adaga",
            "dardo",
            "machadinha",
            "martelo leve",
            "maça",
            "cajado",
            "funda",
            "azagaia",
            "arco curto",
            "besta leve",
        }
        nome_normalizado = nome_canonico.casefold()
        # Druida usa a lista específica do Livro do Jogador, não toda a categoria simples.
        proficiente = "simples" in prof_classe and classe != "druida" and nome_normalizado in simples
        proficiente = proficiente or (
            "marciais" in prof_classe
            and nome_canonico not in {next((k for k in CATALOGO_ARMAS if k.casefold() == x), x) for x in simples}
        )
        if not proficiente:
            categorias = {
                "besta de mão": "bestas_de_mao",
                "espada longa": "espadas_longas",
                "rapieira": "rapieiras",
                "espada curta": "espadas_curtas",
                "besta leve": "bestas_leves",
                "adaga": "adagas",
                "dardo": "dardos",
                "funda": "fundas",
                "cajado": "cajados",
                "azagaia": "azagaias",
                "maça": "macas",
                "clava": "clavas",
                "foice": "foices",
                "lança": "lancas",
                "cimitarra": "cimitarras",
            }
            categoria = categorias.get(nome_normalizado)
            proficiente = bool(categoria and categoria in prof_classe)
        if not proficiente:
            return ResultadoAcao.bloqueado("personagem_sem_proficiencia_na_arma", arma=nome_canonico, classe=classe)
        return None

    def _preparar_dano(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Dano de magia: os dados saem do catálogo, já escalonados pelo espaço."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        preparo = preparar_dano_de_magia(self.engine, fatos, ficha)
        if "fatos" not in preparo:
            return ResultadoAcao(preparo.get("resultado", "bloqueado"), dict(preparo))
        return _Preparo(preparo["fatos"])

    def _preparar_teste_habilidade(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Teste de habilidade: atributo e proficiência vêm da ficha."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")

        pericia_bruta = fatos.get("skill", fatos.get("pericia"))
        if pericia_bruta:
            pericia = str(pericia_bruta).strip().lower().replace(" ", "_")
            pericia = ALIASES_PERICIA.get(pericia, pericia)
            if pericia not in PERICIAS:
                return ResultadoAcao.bloqueado("pericia_desconhecida", pericia=pericia)
            atributo = PERICIAS[pericia]
            atributo_informado = fatos.get("ability", fatos.get("atributo"))
            if atributo_informado:
                informado = ALIASES_ATRIBUTO.get(
                    str(atributo_informado).strip().lower(), str(atributo_informado).strip().lower()
                )
                if informado != atributo:
                    return ResultadoAcao.bloqueado(
                        "atributo_incompativel_com_pericia",
                        pericia=pericia,
                        atributo_correto=atributo,
                    )
            fatos["skill"] = pericia
            fatos["ability"] = atributo
            profs = {
                ALIASES_PERICIA.get(str(p).strip().lower().replace(" ", "_"), str(p).strip().lower().replace(" ", "_"))
                for p in (ficha.get("pericias") or [])
            }
            proficiente = pericia in profs
        else:
            bruto = fatos.get("ability", fatos.get("atributo"))
            atributo = ALIASES_ATRIBUTO.get(str(bruto).strip().lower(), str(bruto).strip().lower()) if bruto else ""
            if atributo not in set(ATRIBUTOS):
                return ResultadoAcao.bloqueado("atributo_ausente_ou_invalido")
            fatos["ability"] = atributo
            proficiente = False

        modificador_atributo = self._modificador(ficha, atributo)
        if modificador_atributo is None:
            return ResultadoAcao.bloqueado("atributo_ausente_na_ficha", atributo=atributo)
        bonus_proficiencia = int(ficha.get("bonus_proficiencia", 2)) if proficiente else 0
        fatos.update(
            {
                "modifier": modificador_atributo + bonus_proficiencia,
                "character_id": ficha.get("id"),
                "proficiency_applied": bonus_proficiencia,
                "modifier_source": "ficha_autoritativa",
            }
        )
        return _Preparo(fatos)

    def _preparar_salvaguarda(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Salvaguarda do personagem: proficiência da ficha, d20 do motor."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")

        bruto = fatos.get("ability", fatos.get("atributo"))
        atributo = ALIASES_ATRIBUTO.get(str(bruto).strip().lower(), str(bruto).strip().lower()) if bruto else ""
        if atributo not in set(ATRIBUTOS):
            return ResultadoAcao.bloqueado("atributo_de_salvaguarda_ausente_ou_invalido")
        modificador_atributo = self._modificador(ficha, atributo)
        if modificador_atributo is None:
            return ResultadoAcao.bloqueado("atributo_ausente_na_ficha", atributo=atributo)

        proficientes = set(ficha.get("proficiencias_salvaguarda") or [])
        proficiente = atributo in proficientes
        bonus_proficiencia = int(ficha.get("bonus_proficiencia", 2))
        fatos.update(
            {
                "ability": atributo,
                "atributo": atributo,
                "proficiencias_salvaguarda": sorted(proficientes),
                "proficiente": proficiente,
                "modificador_atributo": modificador_atributo,
                "bonus_proficiencia": bonus_proficiencia,
                "modifier": modificador_atributo + (bonus_proficiencia if proficiente else 0),
                "character_id": ficha.get("id"),
                "proficiency_applied": bonus_proficiencia if proficiente else 0,
                "modifier_source": "ficha_autoritativa",
            }
        )
        # Com o d20 já informado, o motor usa o resolvedor completo de salvaguarda.
        # Sem ele, o tipo "saving_throw" faz o próprio motor rolar o d20 auditável.
        tem_rolagem = any(chave in fatos for chave in ("roll", "dado", "dados", "rolls"))
        fatos["type"] = "saving_throw_check" if tem_rolagem else "saving_throw"
        if fatos.get("dc") is None and fatos.get("cd") is not None:
            fatos["dc"] = int(fatos["cd"])
        return _Preparo(fatos)

    def _preparar_conjuracao(
        self, fatos: dict[str, Any], personagens: list[dict[str, Any]] | None
    ) -> _Preparo | ResultadoAcao:
        """Conjuração: confere ficha, magia preparada, círculo e espaço disponível."""
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")

        magia = obter_magia(fatos.get("magia"))
        if not magia:
            return ResultadoAcao.bloqueado("magia_desconhecida", magia=fatos.get("magia"))
        nome_canonico = str(magia["nome"])
        nome_magia = normalizar_nome_magia(nome_canonico)
        classe = str(ficha.get("classe", "")).strip().lower()
        nivel = int(ficha.get("nivel", 1) or 1)
        sempre_preparada = False

        if classe == "artifice":
            progresso = progresso_artifice(nivel, int((ficha.get("atributos") or {}).get("inteligencia", 10)))
            circulo_maximo = int(progresso["circulo_maximo"])
            circulo = next(
                (n for nome, n in ARTIFICER_SPELL_LEVELS.items() if normalizar_nome_magia(nome) == nome_magia),
                None,
            )
            if circulo is None:
                subclasse = ficha.get("subclasse") or ficha.get("subclass")
                if magia_sempre_preparada_do_artifice(subclasse, nivel, nome_canonico):
                    # Magia de subclasse já liberada: sempre preparada, fora da escolha da ficha.
                    sempre_preparada = True
                    circulo = circulo_magia_subclasse(nome_canonico)
                else:
                    return ResultadoAcao.bloqueado("magia_nao_disponivel_para_artifice", magia=fatos.get("magia"))
        else:
            # Qualquer classe conjuradora usa o círculo do catálogo; a lista de
            # magias preparadas da própria ficha é a autoridade.
            circulo = int(magia.get("circulo") or 0)
            circulo_maximo = max(
                [int(k) for k in ((ficha.get("conjuracao") or {}).get("espacos_totais") or {}) if str(k).isdigit()]
                or [max(1, (nivel + 1) // 2)]
            )

        conjuracao = ficha.get("conjuracao") or {}
        if not conjuracao:
            return ResultadoAcao.bloqueado("ficha_sem_dados_de_conjuracao", classe=classe)
        escolhidas = conjuracao.get("truques", []) if circulo == 0 else conjuracao.get("magias_preparadas", [])
        if not sempre_preparada and nome_magia not in {normalizar_nome_magia(x) for x in escolhidas}:
            return ResultadoAcao.bloqueado("magia_nao_escolhida_na_ficha", magia=fatos.get("magia"))
        if circulo > circulo_maximo:
            return ResultadoAcao.bloqueado("circulo_indisponivel_para_nivel", circulo=circulo)

        fatos.update(
            {
                "character_id": ficha.get("id"),
                "magia": nome_canonico,
                "spell_level": circulo,
                "concentration_required": bool(
                    (magia.get("concentracao") if isinstance(magia, dict) else None)
                    or (ficha.get("concentracao") or {}).get("magia")
                ),
                "concentrating": bool((ficha.get("concentracao") or {}).get("magia")),
            }
        )

        if circulo == 0:
            # Truques não gastam espaço: o motor valida como conjuração sem espaço.
            fatos["slot_level"] = 0
            fatos["has_slot"] = True
            fatos["type"] = "spell_cast"
            return _Preparo(fatos, personagem_magia=ficha, slot_a_consumir=None)

        try:
            slot = int(fatos.get("espaco", fatos.get("slot_level", circulo)))
        except (TypeError, ValueError):
            return ResultadoAcao.bloqueado("espaco_de_magia_invalido")
        if slot < circulo or slot > circulo_maximo:
            return ResultadoAcao.bloqueado(
                "espaco_incompativel_com_magia", circulo_magia=circulo, espaco_solicitado=slot
            )
        totais = conjuracao.get("espacos_totais") or {}
        restantes = conjuracao.get("espacos_restantes") or totais
        if int(restantes.get(str(slot), 0)) < 1:
            return ResultadoAcao.bloqueado("sem_espacos_restantes", espaco=slot)

        fatos.update({"espaco": slot, "slot_level": slot, "has_slot": True, "type": "spell_cast"})
        return _Preparo(fatos, personagem_magia=ficha, slot_a_consumir=str(slot))

    # ------------------------------------------------------------------
    # Operação composta (responsabilidade 2 sem rodadas extras do modelo)
    # ------------------------------------------------------------------
    def _executar_magia_de_area(
        self,
        fatos: dict[str, Any],
        personagens: list[dict[str, Any]] | None,
        on_alteracao: Callable[[dict[str, Any], dict[str, Any]], None] | None,
        on_rolagem: Callable[[dict[str, Any]], None] | None,
    ) -> ResultadoAcao:
        """Conjura a magia, rola o dano uma vez e a salvaguarda de cada alvo.

        Uma única chamada de ferramenta substitui a sequência ``spell`` →
        ``damage`` → ``saving_throw`` por alvo que o MJ teria de orquestrar
        rodada a rodada (cada rodada reenvia o contexto inteiro ao modelo).

        Autoridade mecânica continua toda no motor: a conjuração usa o mesmo
        preparo do fluxo simples; o dano e a CD saem do catálogo; a salvaguarda
        usa o **modificador do bloco do monstro** (não há ficha de jogador no
        meio). A operação é atômica: se o catálogo não tiver a mecânica de
        dano, ou se algum alvo não existir no bestiário, nada é gasto — nem
        espaço, nem rolagem.
        """
        ficha = self._personagem(fatos.get("character_id"), personagens)
        if ficha is None:
            return ResultadoAcao.bloqueado("personagem_ausente_ou_nao_identificado")

        brutos = (
            fatos.get("alvos")
            or fatos.get("target_names")
            or ([fatos["target_name"]] if fatos.get("target_name") else [])
        )
        nomes_alvos = (
            [str(alvo).strip() for alvo in brutos if str(alvo).strip()] if isinstance(brutos, (list, tuple)) else []
        )
        if not nomes_alvos:
            return ResultadoAcao.bloqueado("alvos_de_area_ausentes", dica="Informe alvos=[nomes dos monstros na área].")
        monstros = []
        for nome in nomes_alvos:
            alvo = consultar_monstro(nome)
            if alvo is None:
                return ResultadoAcao.bloqueado("monstro_desconhecido_no_bestiario", alvo=nome)
            monstros.append(alvo)

        # 1. Conjuração: mesmo preparo do fluxo simples, sem efeito colateral.
        pronto = self._preparar_conjuracao({**fatos, "type": "spell"}, personagens)
        if isinstance(pronto, ResultadoAcao):
            return pronto
        slot_a_consumir = pronto.slot_a_consumir
        personagem_magia = pronto.personagem_magia

        # 2. A mecânica de dano precisa existir ANTES de gastar o espaço.
        seco = preparar_dano_de_magia(
            self.engine,
            {
                "type": "damage",
                "character_id": ficha.get("id"),
                "magia": pronto.fatos.get("magia"),
                "espaco": slot_a_consumir or 0,
                "seed": fatos.get("seed"),
            },
            ficha,
        )
        if "fatos" not in seco:
            return ResultadoAcao(
                str(seco.get("resultado", "bloqueado")),
                {chave: valor for chave, valor in seco.items()},
            )
        fatos_dano = dict(seco["fatos"])

        # 3. Conjuração confirmada pelo motor; só então o espaço é gasto — uma
        #    única vez, independente do número de alvos.
        resolucao = self.engine.evaluate(pronto.fatos)
        resultado_conjuracao = {"status": resolucao.status, **dict(resolucao.outcome)}
        self._pos_processar_resolucao(pronto.fatos, resultado_conjuracao)
        if resultado_conjuracao.get("resultado") != "conjurada":
            return ResultadoAcao(resolucao.status, resultado_conjuracao, [], [])
        alteracoes = self._aplicar_estado(
            pronto.fatos,
            resultado_conjuracao,
            personagem_magia,
            slot_a_consumir,
            on_alteracao,
        )

        # 4. Dano: mesmo caminho do fluxo manual (catálogo → motor), rolado
        #    uma vez para toda a área.
        saida_dano = self.engine.evaluate(fatos_dano)
        resultado_dano = {"status": saida_dano.status, **dict(saida_dano.outcome)}
        self._pos_processar_resolucao(fatos_dano, resultado_dano)
        dano_base = int(resultado_dano.get("dano") or resultado_dano.get("total") or 0)
        cd = int(resultado_dano.get("cd_magia") or 0)
        atributo_save = str(fatos_dano.get("magia_salvaguarda") or "destreza")
        metade_no_sucesso = bool(fatos_dano.get("magia_sucesso_metade"))

        # 5. Salvaguarda de cada alvo com o modificador do próprio bloco.
        semente = str(fatos.get("seed") or "")
        resultado_alvos = []
        rolagens = [registro for registro in (normalizar_rolagem(resultado_dano, fatos_dano, personagens),) if registro]
        for indice, (nome_alvo, alvo) in enumerate(zip(nomes_alvos, monstros)):
            blocos_salva = alvo.get("salvaguardas") or {}
            modificador_alvo = int(
                blocos_salva.get(atributo_save, (alvo.get("modificadores") or {}).get(atributo_save, 0))
            )
            fatos_salva = {
                "type": "saving_throw",
                "ability": atributo_save,
                "modifier": modificador_alvo,
                "dc": cd,
                "target_name": alvo.get("nome", nome_alvo),
                "seed": f"{semente}:area-{indice}" if semente else None,
            }
            saida_salva = self.engine.evaluate(fatos_salva)
            desfecho = dict(saida_salva.outcome)
            sucesso = desfecho.get("result") == "success"
            dano_alvo = dano_base // 2 if (sucesso and metade_no_sucesso) else dano_base
            defesas = aplicar_defesas_monstro(dano_alvo, str(fatos_dano.get("magia_tipo_dano", "")), alvo)
            resultado_alvos.append(
                {
                    "nome": alvo.get("nome", nome_alvo),
                    "salvaguarda": {
                        "atributo": atributo_save,
                        "cd": cd,
                        "modificador": modificador_alvo,
                        "rolagem": desfecho.get("roll"),
                        "total": desfecho.get("total"),
                        "sucesso": sucesso,
                    },
                    "dano_aplicado": int(defesas["dano"]),
                    "dano_antes_das_defesas": dano_alvo,
                    "defesas_dano": defesas,
                }
            )
            registro = normalizar_rolagem(desfecho, fatos_salva, personagens)
            if registro:
                rolagens.append(registro)

        self._registrar(rolagens, on_rolagem)
        payload = {
            "resultado": "conjurada",
            "tipo_resolucao": "magia_de_area",
            "magia": resultado_conjuracao.get("magia"),
            "circulo": resultado_conjuracao.get("circulo"),
            "espaco_usado": resultado_conjuracao.get("espaco_usado"),
            "espacos_restantes": resultado_conjuracao.get("espacos_restantes"),
            "dano": dano_base,
            "dano_bruto": int(resultado_dano.get("dano_bruto") or dano_base),
            "dados_dano": resultado_dano.get("dados_dano"),
            "dano_expressao": resultado_dano.get("dano_expressao"),
            "tipo_dano": resultado_dano.get("tipo_dano"),
            "cd_magia": cd,
            "magia_salvaguarda": atributo_save,
            "magia_sucesso_metade": metade_no_sucesso,
            "magia_area": fatos_dano.get("magia_area"),
            "alvos": resultado_alvos,
            "nota": (
                "Operação composta: conjuração, dano (rolado uma vez) e "
                "salvaguardas resolvidos pelo motor nesta única chamada. "
                "Narre os valores por alvo exatamente como devolvidos."
            ),
            "fonte": str(fatos_dano.get("fonte") or "catálogo de magias do Rule Engine"),
        }
        return ResultadoAcao("resolvido", payload, alteracoes, rolagens)

    # ------------------------------------------------------------------
    # Pós-processamento (responsabilidade 5)
    # ------------------------------------------------------------------
    @staticmethod
    def _pos_processar_resolucao(fatos: Mapping[str, Any], resultado: dict[str, Any]) -> None:
        """Ajusta o payload para o MJ sem alterar a decisão do motor."""
        if fatos.get("type") == "spell_cast":
            resultado["magia"] = fatos.get("magia")
            resultado["circulo"] = int(fatos.get("spell_level", 0))
            resultado["espaco_usado"] = int(fatos.get("slot_level", 0))
            if resultado.get("result") == "cast":
                resultado["resultado"] = "conjurada"
            elif resultado.get("result") == "blocked":
                resultado["resultado"] = "bloqueado"
                resultado["motivo"] = resultado.get("reason")
        for chave in CHAVES_DERIVADAS:
            if chave in fatos:
                resultado[chave] = fatos[chave]
        # Dano de magia resolvido pelo motor: total e dados explícitos para o MJ
        # narrar exatamente o que a engine rolou.
        if fatos.get("type") == "damage" and resultado.get("result") == "damage" and fatos.get("magia"):
            resultado.update(
                {
                    "dano": int(resultado.get("total", 0)),
                    "dano_bruto": int(resultado.get("total", 0)),
                    "dados_dano": list(resultado.get("damage_dice") or []),
                    "dano_expressao": resultado.get("damage_expression"),
                    "tipo_dano": fatos.get("magia_tipo_dano"),
                    "aplicado_ao_alvo": False,
                    "nota": "Rolagem de dano apenas; requer conjuração válida e aplicação ao alvo.",
                }
            )

    @staticmethod
    def _calcular_dano_de_ataque_magico(
        engine: RuleEngine, fatos: Mapping[str, Any], resultado: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Com o acerto confirmado, o dano da magia sai da semente do ataque.

        O acerto crítico dobra os dados dentro do motor; nenhuma aritmética de
        dano acontece fora dele.
        """
        if not fatos.get("spell_attack") or resultado.get("result") != "hit" or not fatos.get("magia_dano"):
            return None
        dano = engine.evaluate(
            {
                "type": "damage",
                "damage_expression": str(fatos["magia_dano"]),
                "damage_modifier": 0,
                "critical": bool(resultado.get("critical")),
                "seed": resultado.get("seed"),
            }
        ).outcome
        if dano.get("result") != "damage":
            return None
        alvo = consultar_monstro(str(fatos.get("target_name", ""))) or {}
        defesas = aplicar_defesas_monstro(int(dano["total"]), str(fatos.get("magia_tipo_dano", "")), alvo)
        resultado.update(
            {
                "dano": defesas["dano"],
                "defesas_dano": defesas,
                "dano_bruto": int(dano["total"]),
                "dados_dano": list(dano["damage_dice"]),
                "dano_expressao": dano.get("damage_expression"),
                "tipo_dano": fatos.get("magia_tipo_dano"),
            }
        )
        fatos_dano = {k: v for k, v in fatos.items() if k not in {"roll", "rolls", "dado", "dados", "dados_rolados"}}
        return normalizar_rolagem({**dano, "total": defesas["dano"], "defesas_dano": defesas}, fatos_dano, None)

    # ------------------------------------------------------------------
    # Estado (responsabilidade 4) e rolagens (responsabilidade 6)
    # ------------------------------------------------------------------
    def _aplicar_estado(
        self,
        fatos: Mapping[str, Any],
        resultado: dict[str, Any],
        personagem_magia: dict[str, Any] | None,
        slot_a_consumir: str | None,
        on_alteracao: Callable[[dict[str, Any], dict[str, Any]], None] | None,
    ) -> list[dict[str, Any]]:
        """Aplica ao estado canônico apenas o que o motor confirmou.

        Uma conjuração bloqueada não consome espaço; uma rolagem de dano não
        altera PV. Só a operação confirmada gera alteração — nunca duplicada,
        porque a alteração nasce da ficha recebida, não de um contador paralelo.
        """
        if slot_a_consumir is None or personagem_magia is None:
            return []
        if resultado.get("resultado") != "conjurada":
            return []
        alteracao = consumir_espaco(personagem_magia, slot_a_consumir)
        resultado["espacos_restantes"] = alteracao["espacos_restantes"]
        if on_alteracao is not None:
            on_alteracao(personagem_magia, alteracao)
        return [alteracao]

    def _coletar_rolagens(
        self,
        fatos: Mapping[str, Any],
        resultado: dict[str, Any],
        personagens: list[dict[str, Any]] | None,
        on_rolagem: Callable[[dict[str, Any]], None] | None,
    ) -> list[dict[str, Any]]:
        """Normaliza e anuncia toda rolagem que o motor gerou nesta ação."""
        registros: list[dict[str, Any]] = []
        rolagem_dano = self._calcular_dano_de_ataque_magico(self.engine, fatos, resultado)
        for registro in (normalizar_rolagem(resultado, fatos, personagens), rolagem_dano):
            if registro:
                registros.append(registro)
        self._registrar(registros, on_rolagem)
        return registros

    def _registrar(
        self,
        rolagens: list[dict[str, Any]],
        on_rolagem: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        for rolagem in rolagens:
            if not rolagem:
                continue
            self.rolagens.append(rolagem)
            if on_rolagem is not None:
                on_rolagem(rolagem)
