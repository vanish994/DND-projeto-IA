# Cobertura do Livro do Jogador 2024

Este arquivo é o mapa de implementação do **Rule Engine**. A biblioteca de livros permanece apenas como referência; suas regras são convertidas em código versionado e testado.

## Módulos

| Módulo | Situação | Próxima cobertura |
|---|---|---|
| Fundamentos e testes | Em implementação | Atributos, CD, proficiência, vantagem/desvantagem, perícias e interação social |
| Combate e ações | Em implementação | Iniciativa, rodadas, turnos, ações, movimento, Correr, Desengajar, Esquivar, Preparar e terreno difícil já iniciados; faltam alcance, cobertura e agarrar |
| Vida, dano e descanso | Parcial | PV, PV temporários, resistência, vulnerabilidade, morte, exaustão e descansos |
| Condições e efeitos | Parcial | Todas as condições, efeitos derivados e término contextual |
| Conjuração e magias | Parcial | Componentes, preparação, rituais, alvos, áreas, concentração e duração |
| Equipamento e armas | Pendente | Armas, armaduras, propriedades, maestria, ferramentas, carga e fabricação |
| Criação e progressão | Pendente | Espécies, origens, classes, subclasses, talentos e multiclasse |
| Exploração e regras gerais | Pendente | Viagem, percepção, furtividade, iluminação, objetos, riscos e interação social |

## Princípios

1. A regra determinística deve ser resolvida pelo motor antes da resposta narrativa da IA.
2. Toda resolução deve retornar resultado, fatos usados, regra aplicada, fonte e trilha de auditoria.
3. Regras compartilhadas ficam em uma única implementação: dados, modificadores, proficiência, CD, vantagem/desvantagem, condições e tempo.
4. Cada módulo recebe testes de casos normais, limites, conflitos e integração.
5. Todo texto destinado ao usuário, documentação e descrição de regra deve estar em português do Brasil.
6. A edição da regra deve ser explícita para permitir versões futuras sem misturar 2014 e 2024.

## Ordem de implementação

1. Fundamentos compartilhados: teste de d20, modificadores, proficiência, vantagem/desvantagem e perícias.
2. Combate: iniciativa, ações, movimento, alcance, cobertura e ações especiais.
3. Vida e descanso: PV, cura, morte, resistência, vulnerabilidade, exaustão e recursos.
4. Condições completas e efeitos derivados.
5. Conjuração detalhada e catálogo estruturado de magias.
6. Equipamento, armas, armaduras, ferramentas e maestria.
7. Criação, progressão, classes, subclasses, talentos e multiclasse.
8. Exploração, objetos, riscos ambientais e interação social.

## Estado atual

Já existem regras iniciais para testes de atributo, ataques, dano, salvaguardas, espaços de magia, concentração e aplicação/remoção/imunidade de condições. A fundação compartilhada agora inclui:

- modificador de atributo de 1 a 30;
- Bônus de Proficiência por nível/ND;
- seleção determinística de d20 com Vantagem e Desvantagem;
- cancelamento entre Vantagem e Desvantagem;
- comparação do total com uma CD.

O módulo de combate já inclui:

- ordenação de iniciativa com desempate determinístico;
- avanço de rodadas e turnos;
- uma ação, uma ação bônus e uma reação por turno;
- movimento restante e limite de deslocamento;
- ação Correr, que concede movimento adicional igual ao deslocamento;
- estado de surpresa no primeiro turno.
- ações Ajudar, Atacar, Analisar, Desengajar, Esconder, Esquivar, Influenciar, Preparar, Procurar, Usar Magia e Usar Objeto;
- efeitos estruturados de Desengajar, Esquivar e Preparar;
- custo dobrado de movimento em terreno difícil.
