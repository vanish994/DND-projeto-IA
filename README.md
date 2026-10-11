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

A estimativa de “mais de 300 monstros” não corresponde ao PDF SRD 5.2.1 presente na biblioteca ativa: a extração verificável dessa fonte resulta em 232 blocos completos. O catálogo não inventa entradas para preencher essa diferença.
