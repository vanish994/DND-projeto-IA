"""Estado canônico do jogo: leitura autoritativa e aplicação de alterações.

O Orquestrador de Ações é o **único** ponto que lê o estado para montar o
contexto do MJ e o único que decide quais alterações mecânicas devem ser
gravadas. O Rule Engine calcula; este módulo aplica o resultado ao estado.

Nada aqui inventa regra: ``consumir_espaco`` e ``resumo_autoritativo`` apenas
refletem o que a ficha e o motor já determinam.
"""

from __future__ import annotations

from typing import Any


def texto_equipamento_antecedente(personagem: dict) -> str:
    """Mostra o pacote escolhido; sem escolha, deixa claro que está pendente."""
    equipamento = personagem.get("equipamento_antecedente") or {}
    if not isinstance(equipamento, dict) or not equipamento.get("A"):
        return "não registrado"
    escolha = str(equipamento.get("escolha") or "").strip().upper()
    pacote_a = equipamento.get("A")
    pacote_b = equipamento.get("B") or "50 PO"
    if escolha in ("A", "B"):
        itens = equipamento.get(escolha) or pacote_b
        return f"pacote {escolha} ({itens})"
    return f"pendente - escolher entre pacote A ({pacote_a}) ou pacote B ({pacote_b})"


def resumo_autoritativo(grupo: list[dict[str, Any]]) -> str:
    """Fornece a ficha real ao MJ e bloqueia invenções quando não há personagem."""
    grupo = grupo or []
    if not grupo:
        return (
            "ESTADO DA CAMPANHA — nenhum personagem está cadastrado nesta campanha. "
            "Não invente nem presuma nome, espécie, classe, nível, antecedentes, atributos, "
            "aparência ou história do personagem do jogador. Antes de narrar uma cena que "
            "dependa do personagem, pergunte qual personagem existente ele quer usar ou "
            "oriente-o a criar um. Não afirme que consultou uma ficha."
        )

    linhas = []
    for indice, p in enumerate(grupo, start=1):
        atributos = ", ".join(f"{nome.upper()} {valor}" for nome, valor in (p.get("atributos") or {}).items())
        modificadores = ", ".join(
            f"{nome.upper()} {valor:+d}" for nome, valor in (p.get("modificadores") or {}).items()
        )
        linhas.append(
            f"- FICHA AUTORITATIVA #{indice}: id={p.get('id', 'não registrado')}; nome={p.get('nome', 'não registrado')}; "
            f"espécie={p.get('especie', 'não registrada')}; classe={p.get('classe', 'não registrada')}; "
            f"subclasse={p.get('subclasse') or 'nenhuma registrada'}; nível={p.get('nivel', 'não registrado')}; "
            f"antecedente={p.get('antecedente') or 'não registrado'}; "
            f"PV={p.get('pv_atual', '?')}/{p.get('pv_maximo', '?')}; "
            f"bônus de proficiência=+{p.get('bonus_proficiencia', '?')}; "
            f"atributos=[{atributos}]; modificadores=[{modificadores}]."
        )
        linhas.append(
            f"  Dados de ficha: perícias={', '.join(p.get('pericias') or []) or 'nenhuma registrada'}; "
            f"perícias escolhidas de classe={', '.join(p.get('pericias_classe') or []) or 'não registradas'}; "
            f"salvaguardas proficientes={', '.join(p.get('proficiencias_salvaguarda') or []) or 'não registradas'}; "
            f"proficiências de classe={p.get('proficiencias_classe') or 'não catalogadas'}; "
            f"proficiências pendentes={p.get('proficiencias_pendentes', True)}; "
            f"ferramenta de antecedente={p.get('ferramenta') or 'nenhuma registrada'}; "
            f"talentos={', '.join(p.get('talentos') or []) or 'nenhum registrado'}; "
            f"deslocamento={p.get('deslocamento', 'não registrado')} m; "
            f"equipamento de antecedente={texto_equipamento_antecedente(p)}."
        )
        heranca = p.get("heranca_draconica")
        if heranca:
            sopro = heranca.get("sopro") or {}
            linhas.append(
                f"  Herança Dracônica: linhagem={heranca.get('linhagem')}; "
                f"tipo de dano={heranca.get('tipo_dano')}; resistência={heranca.get('resistencia')}; "
                f"Arma de Sopro={sopro.get('dado')} de dano {sopro.get('tipo_dano')} "
                f"(formas: {', '.join(sopro.get('formas') or [])}; salvaguarda de "
                f"{sopro.get('salvaguarda')} CD {sopro.get('cd')}; {sopro.get('usos')} usos, "
                f"recarga em {sopro.get('recarga')})."
            )
        pendencias = [str(item) for item in (p.get("escolhas_pendentes") or [])]
        if p.get("proficiencias_pendentes"):
            pendencias = ["Perícias ou ferramenta de classe", *pendencias]
        if pendencias:
            linhas.append(
                "  PENDÊNCIAS DE CRIAÇÃO (pergunte ao jogador, nunca invente): "
                + "; ".join(dict.fromkeys(pendencias))
                + "."
            )
        conjuracao = p.get("conjuracao") or {}
        truques = conjuracao.get("truques") or []
        preparadas = conjuracao.get("magias_preparadas") or []
        espacos = conjuracao.get("espacos_totais") or {}
        restantes = conjuracao.get("espacos_restantes") or espacos
        linhas.append(
            f"  Conjuração exatamente registrada: truques={', '.join(truques) or 'nenhum registrado'}; "
            f"magias preparadas/conhecidas={', '.join(preparadas) or 'nenhuma registrada'}; "
            f"espaços totais={espacos or 'nenhum registrado'}; espaços restantes={restantes or 'nenhum registrado'}."
        )
    return (
        "ESTADO AUTORITATIVO DOS PERSONAGENS DESTA CAMPANHA, consultado do banco. "
        "Estes dados prevalecem sobre suposições narrativas e sobre mensagens antigas. "
        "Nunca altere nem contradiga a ficha; não invente nome, raça/espécie, classe, nível, "
        "antecedente, atributos, proficiências, aparência ou história pessoal. Não pergunte de novo "
        "informações que já constam aqui. Se um dado não estiver registrado, trate-o como desconhecido "
        "e pergunte ao jogador antes de fixá-lo como fato. Não invente escolhas, espaços, magias, "
        "proficiências, equipamento ou características ausentes; toda alteração mecânica exige "
        "resolução do motor antes de narrar o efeito.\n" + "\n".join(linhas)
    )


def consumir_espaco(personagem: dict[str, Any], slot: str) -> dict[str, Any]:
    """Gasta um espaço de magia na ficha e descreve a alteração aplicada.

    A aplicação é feita **no próprio objeto da ficha**, porque é esse objeto
    que a campanha continua usando dentro do mesmo turno (duas conjurações
    seguidas precisam enxergar o mesmo estado). O retorno é o registro
    auditável da alteração — quem persiste é a camada de armazenamento.

    Devolve ``alteracao`` com ``de``/``para``; a alteração é o único caminho
    pelo qual o estado muda, o que evita efeito duplicado.
    """
    conjuracao = dict(personagem.get("conjuracao") or {})
    totais = dict(conjuracao.get("espacos_totais") or {})
    restantes = dict(conjuracao.get("espacos_restantes") or totais)
    anterior = int(restantes.get(str(slot), 0))
    restantes[str(slot)] = max(0, anterior - 1)
    conjuracao["espacos_restantes"] = restantes
    personagem["conjuracao"] = conjuracao
    return {
        "personagem_id": personagem.get("id"),
        "campo": "conjuracao.espacos_restantes",
        "espaco": str(slot),
        "de": anterior,
        "para": restantes[str(slot)],
        "espacos_restantes": restantes,
    }
