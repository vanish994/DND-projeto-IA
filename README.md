# DND-projeto-IA

Biblioteca de referência do projeto de IA para Dungeons & Dragons.

## Livros incluídos

- Dungeon Master's Guide 2024
- Livro do Jogador 2024
- Eberron: Forge of the Artificer
- Ravenloft
- Dragon Delves

## Bestiário SRD 5.2.1

O projeto agora inclui um catálogo determinístico com **232 blocos estatísticos completos** identificados no `SRD_CC_v5.2.1.pdf` compartilhado. Cada registro contém nome, tamanho, tipo, alinhamento, CA, PV, dados de vida, ND e XP.

Também estão disponíveis a tabela de XP por ND, filtros por tipo/ND, consulta por nome e cálculo do XP bruto de um encontro. A regra do motor usa entradas como:

```python
{"type": "bestiary", "operacao": "consultar", "nome": "Aboleth"}
{"type": "bestiary", "operacao": "listar", "tipo": "beast", "nd": "0"}
{"type": "bestiary", "operacao": "xp_encontro", "nomes": ["Bandit", "Wolf"]}
```

O bestiário também preserva o bloco integral de cada monstro, com cabeçalho, traços, ações, ações bônus, reações e ações lendárias quando existirem. As operações `bloco_completo` e `secao` permitem consultar esses dados de forma auditável.

### Fluxo de seleção para o MJ

O MJ é um bloco separado do motor. Ele envia apenas os critérios do momento da campanha, e o motor retorna uma lista de candidatos oficiais para escolha. O motor não escolhe o monstro, não cria variantes e não inventa uma entrada ausente:

```python
{
    "type": "bestiary",
    "operacao": "sugerir",
    "tipos": ["beast"],
    "nd_min": "1/4",
    "nd_max": "1",
    "limite": 5
}
```

O resultado contém apenas resumos dos candidatos, a origem `SRD 5.2.1` e `escolha: "MJ"`. Depois que o MJ escolhe um nome, o bloco pode ser recuperado com `bloco_completo`. Critérios não presentes no catálogo, como ambiente narrativo, não são inferidos silenciosamente: devem ser convertidos pelo bloco do MJ em filtros explícitos de tipo, tamanho, alinhamento ou ND.

A estimativa de “mais de 300 monstros” não corresponde ao PDF SRD 5.2.1 presente na biblioteca ativa: a extração verificável dessa fonte resulta em 232 blocos completos. O catálogo não inventa entradas para preencher essa diferença.
