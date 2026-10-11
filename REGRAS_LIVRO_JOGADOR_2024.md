# Cobertura do Livro do Jogador 2024

Este documento é o inventário de implementação do **Rule Engine**. Os livros continuam no repositório apenas como referência; nenhuma regra é considerada concluída sem código e testes.

## Situação geral

O motor está **funcional, mas incompleto**. A suíte automatizada está configurada para rodar nos branches do repositório. Uma regra só será considerada concluída quando houver implementação determinística e testes executados; a execução dos testes mais recentes ainda precisa ser confirmada.

## Bloco 1 — núcleo de sobrevivência

O núcleo de sobrevivência foi implementado: Estado Vital, Pontos de Vida, Pontos de Vida Temporários, cura, tipos e origem de dano, Resistência, Vulnerabilidade, Imunidade, dano em 0 PV, inconsciência, estabilidade, Salvaguardas contra a Morte, estabilização, Exaustão, Dados de Vida e descansos com duração, interrupção, intervalo e recursos recuperáveis declarados.

O **Bloco 1 está encerrado no nível do núcleo**. A recuperação de uma característica específica de classe só será aplicada quando o módulo de classes fornecer seu contrato de recursos; o descanso já retorna os recursos declarados para essa integração futura.

## Bloco 2 — geometria de combate

O núcleo geométrico foi concluído com distância em grade, espaço por tamanho, alcance normal e máximo, Desvantagem por alcance estendido, cobertura, linha de visão, combinação de validações antes do ataque, sentidos especiais, movimento especial, queda com dano de 1d6 por 3 metros, montaria, combate subaquático e resolução básica de objetos.

O **Bloco 2 está encerrado no nível do núcleo**. A integração com o catálogo de criaturas, mapas, obstáculos e características de classe será feita pelos módulos que consumirem essas resoluções.

## Bloco 3 — condições e efeitos

O Bloco 3 foi iniciado com as 15 condições oficiais do Livro do Jogador 2024: Cego, Enfeitiçado, Surdo, Exaustão, Amedrontado, Agarrado, Incapacitado, Invisível, Paralisado, Petrificado, Envenenado, Caído, Contido, Atordoado e Inconsciente. O núcleo inclui estado persistente, imunidade, duração, remoção e efeitos sobre ações, movimento, fala, sentidos, salvaguardas e ataques. A cobertura de interações com concentração, magias específicas e características de classe será refinada nos blocos de Magias e Personagens.

## Bloco 4 — magias, equipamentos e armas

O núcleo do Bloco 4 foi iniciado com cálculo de CA, armaduras, escudos, proficiência, propriedades de armas, maestria, duas armas Leves, Capacidade de Carga, preparação de magias, componentes, rituais, concentração anterior, alcance de alvos e áreas de efeito. O catálogo estruturado agora contém 34 armas, 13 armaduras, 45 equipamentos de aventura e 390 entradas de magias com escola, Concentração, Ritual e componente Material. A consulta dos catálogos está integrada ao motor.

Ainda faltam descrições completas dos efeitos individuais das 390 magias, fabricação detalhada por ferramenta, veículos, listas de equipamentos iniciais por classe/origem, progressão de espaços por classe e todas as regras de maestria em resolução de ataque.

## Bloco 5 — criação de personagens, classes e subclasses

O núcleo foi iniciado com nove espécies, doze classes, subclasses a partir do nível 3, matriz padrão, compra por pontos, validação de atributos, criação de ficha, Bônus de Proficiência, Dados de Vida, progressão de nível, escolhas de Aumento de Atributo/Talento e pré-requisitos de multiclasse. Ainda faltam os traços completos de cada espécie, antecedentes, características individuais das doze classes, subclasses, talentos completos, progressão detalhada de espaços e equipamento inicial.

Correção de cobertura: Artífice foi adicionado como décima terceira classe, com Dado de Vida d8, Inteligência como atributo principal e requisito de Inteligência 13 para multiclasse. Também foram catalogadas as sete subclasses apresentadas em *Ravenloft*: Reanimador (Artífice), Colégio dos Espíritos (Bardo), Domínio da Sepultura (Clérigo), Guardião Oculto (Guardião), Fantasma (Ladino), Feitiçaria das Sombras (Feiticeiro) e Patrono Morto-Vivo (Bruxo), todas disponíveis a partir do nível 3.

## Auditoria para 100% de cobertura

Foi concluída uma auditoria modular das 13 classes contra os livros locais. A matriz `class_progression.py` agora registra as características por nível e todas as subclasses principais do Livro do Jogador 2024, além das opções de Ravenloft e Artífice. A progressão passou a expor as características do nível, e os níveis adicionais de Aumento de Atributo do Guerreiro e do Ladino foram corrigidos. Essa matriz é o inventário executável da próxima fase: cada característica ainda precisa receber sua resolução de efeitos, recursos, recargas, testes e integração com combate/conjuração.

## Bloco marcial — lote 1

Implementados no `martial.py` e registrados no motor: Ataque Extra (incluindo os quatro ataques do Guerreiro no nível 20), Maestria em Arma, Fúria do Bárbaro, Recuperar Fôlego, Ataque Furtivo, Foco do Monge, Defletir Ataques, Esquiva Sobrenatural e Evasão. O lote inclui validação de usos, resistências, bônus de dano, progressão de dados, redução de dano e recuperação básica. As características marciais restantes — subclasses, Golpe Astuto, Surto de Ação, Indomável, Golpe Atordoante, recursos avançados de Fúria e demais efeitos por nível — permanecem no próximo lote.

## Subclasses marciais — lote 1

Foi criado o catálogo executável das subclasses de Guerreiro (Campeão, Cavaleiro Místico, Combatente Psíquico e Mestre da Batalha), Bárbaro (Árvore do Mundo, Berserker, Coração Selvagem/Caminho do Guerreiro Espiritual e Fanático), Monge (Mão Espalmada, Misericórdia, Sombras e Elementos) e Ladino (Adaga Espiritual, Assassino, Ladrão e Trapaceiro Arcano). O resolvedor já aplica efeitos centrais como Crítico Aprimorado, Frenesi, Fúria Irracional, Fúria Divina, Passo da Sombra, Mão de Cura/Dolo, Assassinar, Poder Psiônico e Maestrias da Árvore do Mundo. As características restantes de cada subclasse serão detalhadas em lotes seguintes.

## Bloco conjurador — lote 1

Iniciado o núcleo de Mago, Clérigo, Druida e Bardo. O motor agora resolve a progressão de espaços de magia, atributo de conjuração, magias preparadas e foco; Inspiração de Bardo com progressão do dado e recuperação; Canalizar Divindade com Centelha Divina e Expulsar Mortos-Vivos; Forma Selvagem com usos, duração, PV temporários e conjuração em níveis altos; e Livro de Magias com adição de magias, Recuperação Arcana e Memorizar Magia. Ainda faltam as características de subclasses, listas completas de magias por classe e os recursos avançados de cada classe.

## Segundo lote conjurador

Implementados Bruxo, Feiticeiro e Guardião. O Bruxo agora possui progressão de Magia de Pacto, quantidade de Invocações Místicas, Astúcia Mágica e Arcana Mística. O Feiticeiro possui Pontos de Feitiçaria, Metamagia, Feitiçaria Inata, Restauração Feiticeira, Feitiçaria Encarnada e Apoteose Arcana. O Guardião possui progressão de espaços, Inimigo Favorito, Explorador Hábil, Incansável, Predador Implacável e Véu da Natureza. Permanecem para lotes posteriores os efeitos individuais de invocações, opções de Metamagia, subclasses e listas detalhadas de magias.

## Invocações Místicas do Bruxo

O catálogo do PHB 2024 foi integrado em `warlock_invocations.py`, com 27 opções, níveis mínimos, requisitos de Pacto da Lâmina/Corrente/Tomo, requisitos de truques, invocações repetíveis e bloqueio de duplicatas. O motor resolve os efeitos detalhados de Explosão Agonizante/Repulsiva, Lança Mística, Lâmina Sedenta/Devoradora, Punição Mística, Sorvedouro de Vida, Investimento do Mestre da Corrente, Presentes, Pactos, visões, conjurações sem espaço, Mente Mística e demais opções catalogadas.

## Bloco 6 — Talentos

Implementado o catálogo do Livro do Jogador 2024 em `feats.py`, separado em Talentos de Origem, Talentos Gerais e Dádivas Épicas. O motor valida nível mínimo, necessidade de conjuração, atributos mínimos e categoria, além de resolver efeitos como proficiência em Iniciativa, Sorte, Vigoroso, Conjurador Bélico, Mestre em Escudos, Sentinela, Telecinético, Tocado pelas Fadas/Sombras e as Dádivas Épicas de Velocidade, Visão Verdadeira, Recuperação, Resistência à Energia, Destino e outras. A criação de personagens passou a aceitar o catálogo completo em vez da lista reduzida anterior.

## Sistema completo de magias

Criado `spells.py` com consulta por escola e círculo, componentes Verbais/Somáticos/Materiais, duração, Ritual, Concentração, troca da concentração anterior e uso de espaços de círculo superior. O sistema reaproveita o catálogo extraído do Livro do Jogador e acrescenta resolução detalhada para magias representativas de dano, cura, proteção, teleporte, invocação e controle, incluindo upcasting de Bola de Fogo, Relâmpago, Mísseis Mágicos, Cura, Benção e Armadura de Agathys. A API oferece listagem, consulta e conjuração; as regras legadas continuam compatíveis quando a entrada antiga é usada sem o campo `magia`.

## Equipamentos, economia e itens mágicos

Implementado `economy.py` com conversão entre PC, PP, PE, PO e PL; compra e venda; consulta unificada de armas, armaduras, equipamentos e itens mágicos; inventário com capacidade de carga; consumíveis; cargas; e sintonização. O sistema aplica o limite de três itens mágicos sintonizados, exige sintonização quando necessário, permite encerrar a sintonização após descanso curto e bloqueia o uso de itens com cargas esgotadas. Foram adicionados itens mágicos representativos com efeitos, raridade, cargas e requisitos de sintonização.

## Condições e estados alterados

Completo o módulo `conditions.py` com as 15 condições do Livro do Jogador 2024, normalização de nomes em português/inglês, imunidades, duração, aplicação repetida, remoção, redução por turnos e níveis de Exaustão. Os efeitos derivados agora abrangem vantagem/desvantagem, acertos críticos automáticos, deslocamento 0, ações e reações bloqueadas, falhas automáticas de salvaguardas de Força/Destreza, concentração, fala, sentidos, ataques contra Caído, efeitos de Cego/Invisível, Petrificado, Contido, Atordoado, Inconsciente, Envenenado, Amedrontado, Enfeitiçado, Agarrado e Exaustão.

## Combate tático avançado

Criado `tactical.py` para resolver deslocamento em grade, casulas bloqueadas, terreno difícil, rastejar, linha de efeito, cobertura, flanqueamento e ataques táticos. O ataque tático combina alcance normal/máximo, desvantagem por distância, cobertura parcial ou de três quartos, cobertura total, bloqueadores na linha, vantagem de flanqueamento e movimento restante. O módulo mantém a compatibilidade com as regras geométricas e de movimento existentes.

## Características restantes das 13 classes — lote transversal

Criado `class_features.py` com resolução executável para o primeiro lote de lacunas auditadas: Defesa sem Armadura, Sentido de Perigo, Conhecimento Primordial, Movimento Rápido, Fúria Implacável, Força Indomável, Campeão Primitivo, Surto de Ação, Mente Tática, Indomável, Ajuste Tático, Ataques Estudados, Artes Marciais, Queda Lenta, Golpe Atordoante, Sobrevivente Disciplinado, Foco Perfeito, Defesa Superior, Corpo e Mente, Ação Ardilosa, Mira Firme, Talento Confiável, Mente Escorregadia, Elusivo, Golpe de Sorte, Mãos Consagradas, Auras do Paladino, Golpes Radiantes, Toque Restaurador, Errante, Incansável, Sentidos Selvagens e Matador de Inimigos Favoritos.

Também foram corrigidos os marcos transversais de progressão: aumentos de atributo/talento nos níveis 4, 8, 12 e 16, Dádiva Épica no nível 19, marcos explícitos de subclasse, posição da subclasse do Mago no nível 3, espaço inicial do meio-conjurador e tabela completa de espaços de Magia de Pacto. Maestria em Arma agora contempla Paladino e Guardião, sem concedê-la indevidamente ao Monge; a progressão de usos de Fúria foi corrigida para os marcos de 2024.

## Características restantes das 13 classes — segundo lote

O segundo lote expandiu `class_features.py` com resoluções determinísticas para os recursos de Bardo (Inspiração, Pau pra Toda Obra, Especialista, Fonte de Inspiração, Contra-Encantamento, Inspiração Superior e Palavras de Criação), Clérigo (Ordem Divina, Canalizar Divindade, Fulminar Mortos-Vivos, Golpes Abençoados e Intervenção Divina), Druida (Idioma Druídico, Ordem Primal, Companheiro Selvagem, Ressurgimento Selvagem, Fúria Elemental, Magias Bestiais e Arquidruida), Mago (Adepto de Ritual, Recuperação Arcana, Acadêmico, Memorizar Magia, Maestria de Magias e Assinatura Mágica), Feiticeiro (Fonte de Magia, Metamagia, Restauração Feiticeira, Feitiçaria Encarnada e Apoteose Arcana), Bruxo (Astúcia Mágica, Contatar Patrono, Arcana Mística e Mestre Místico) e Artífice (Magia de Artífice, Replicar Item Mágico, Lampejo de Gênio, Item Armazenador de Magia, Artífice Avançado e Alma do Artífice).

Cada recurso aceita fatos estruturados em português, retorna um resultado auditável e possui testes de comportamento. A nomenclatura da progressão do Artífice também foi traduzida para português do Brasil.

## O que já está implementado

- Modificador de atributo para valores de 1 a 30.
- Bônus de Proficiência por nível/ND.
- Rolagem de d20 com Vantagem, Desvantagem e cancelamento entre ambas.
- Testes básicos de atributo.
- Jogadas de ataque básicas, 20 natural e 1 natural.
- Dano normal e dano crítico.
- Salvaguardas básicas.
- Conjuração básica por espaço de magia e nível do espaço.
- Concentração básica e substituição da concentração anterior.
- Aplicação, remoção e imunidade de condições em nível básico.
- Ordenação de iniciativa e desempate.
- Rodadas e turnos.
- Uma ação, uma ação bônus e uma reação por turno.
- Movimento, Correr e terreno difícil.
- Ações Ajudar, Atacar, Analisar, Desengajar, Esconder, Esquivar, Influenciar, Preparar, Procurar, Usar Magia e Usar Objeto em nível estrutural.
- Ataques de oportunidade.
- Agarrar, escape do agarramento e condição Imobilizado.
- Empurrar, empurrão de 1,5 metro e efeito Caído.

## Lote de fundamentos — testes de habilidade e Inspiração Heroica

Adicionado `ability_checks.py` e integração ao `build_default_engine()` para:

- As 18 perícias padrão e seus atributos associados.
- Testes ativos com modificador de atributo, proficiência, Especialização, modificadores circunstanciais e vantagem/desvantagem.
- Bônus de Proficiência aplicado uma única vez; Especialização duplica esse bônus.
- CDs padrão de 5, 10, 15, 20, 25 e 30, aceitas também por rótulo.
- Testes passivos, aplicando +5 por vantagem ou -5 por desvantagem.
- Testes em grupo, exigindo sucesso de pelo menos metade dos participantes.
- Vantagem quando a mesma tarefa combina proficiência relevante em perícia e ferramenta.
- Inspiração Heroica com validação do recurso, rerrolagem imediata de qualquer dado e uso obrigatório do novo resultado.
- Bloqueio explícito quando faltam modificadores do personagem, Bônus de Proficiência necessário ou resultados de dados.

Os testes foram adicionados em `tests/test_ability_checks.py`. **Ainda não há confirmação de execução da suíte pelo GitHub Actions**, portanto este lote está implementado, mas não marcado como validado.

## Lote de fundamentos — salvaguardas e iniciativa

Ampliado o módulo `ability_checks.py` com `saving_throw_check` e `initiative_check`. Salvaguardas agora podem calcular o modificador do atributo e aplicar a proficiência declarada para aquele atributo; iniciativa usa Destreza e aceita bônus explícitos de características. Ambos validam a presença dos fatos necessários e aceitam vantagem/desvantagem com os mesmos controles de rolagem.

Testes de integração foram adicionados. A execução automatizada continua sem confirmação; o lote não é considerado validado até que a suíte seja executada.

## Correção de condições — sem efeitos inferidos incorretamente

Ajustado `conditions.py` para não conceder vantagem a um atacante Cego, bloquear ataques de criaturas Incapacitadas, exigir distância em metros para declarar crítico automático contra Paralisado/Inconsciente e não aplicar desvantagem genérica a salvaguardas por Amedrontado/Envenenado. Incapacitado, por si só, não impede a fala; Paralisado, Petrificado e Inconsciente impedem. Foram adicionados testes de regressão para esses casos.

Os testes foram adicionados, mas a suíte ainda não foi executada/confirmada por CI.

## Auditoria oficial das condições

A lista oficial do PHB 2024 contém **15 condições**, não 16. `Lento/Slowed` não faz parte da lista normativa e foi removida do conjunto de condições do motor; efeitos de lentidão devem ser modelados como efeitos específicos de magias ou características, não como condição geral. A fonte oficial D&D Beyond lista as 15 condições no glossário.

## Correção de Surpresa no combate de 2024

Atualizado o rastreador de turnos: Surpresa não remove ação, ação bônus, reação nem movimento no primeiro turno. A condição de surpreendido agora é aplicada à rolagem de iniciativa como desvantagem, conforme o PHB 2024.

## Correção de descanso e estabilização

`EstadoVital` agora pode rastrear Dados de Vida máximos e disponíveis: o Descanso Curto consome os dados usados, e o Descanso Longo recupera todos os dados gastos, além dos PV e da redução de um nível de Exaustão. Estabilizar não é mais sucesso automático: exige teste de Sabedoria (Medicina) CD 10 ou uso de kit médico.

Testes de regressão adicionados. A validação final depende da execução da suíte no branch.

## Correção de interrupções de descanso e Salvaguardas contra a Morte

Descanso Longo interrompido após pelo menos uma hora agora concede os benefícios de Descanso Curto; descansos longos completos validam sono mínimo de seis horas e até duas horas de atividade leve. Salvaguardas contra a Morte rejeitam valores fora de 1–20 e não podem ser roladas por uma criatura já estável.

## Ações de exploração e interação social

Adicionado `exploration_actions.py` para Esconder-se (requisitos de obscurecimento/cobertura, fora da linha de visão, Furtividade CD 15 e DC para encontrar) e Influenciar (disposto/indisposto sem teste; hesitante com a perícia aplicável e CD padrão max(15, Inteligência do monstro)).

Testes de integração adicionados; aguardando execução da suíte.

## Ações Search e Help

Adicionadas regras para Search (Sabedoria com Intuição, Medicina, Percepção ou Sobrevivência conforme o alvo da busca) e Help (vantagem no próximo teste de perícia/ferramenta, exigindo proficiência do ajudante, ou no próximo ataque contra inimigo a até 1,5 m).

## Ação Study

Adicionada a ação Study com associação das áreas de conhecimento às perícias de Inteligência (Arcanismo, História, Investigação, Natureza e Religião).

## Regras que ainda faltam

### 1. Fundamentos e testes

- Pipeline completo de Teste de D20 usando automaticamente atributo, perícia, proficiência e modificadores circunstanciais.
- Perícia usando atributo alternativo autorizado pelo Mestre.
- Não acumulação do Bônus de Proficiência.
- Multiplicação e divisão do Bônus de Proficiência no máximo uma vez.
- Testes resistidos.
- Regra para decidir quando não pedir um teste.
- Proficiência em ferramentas.
- Rerrolagem/substituição de um único dado sob Vantagem ou Desvantagem.
- Interação social estruturada com atitude, objetivo, medo, desejo, simpatia e reação de NPC.

### 2. Combate e ações

- Surpresa conforme percepção e estado Incapacitado.
- Grid, quadrados, diagonais, cantos e distância.
- Tamanho e espaço ocupado por criaturas.
- Alcance normal e máximo.
- Ataques à distância além do alcance normal.
- Inimigo adjacente impondo Desvantagem em ataque à distância.
- Alvo invisível e atacante invisível.
- Linha de visão e linha de efeito.
- Cobertura parcial, três quartos e total.
- Cobertura não cumulativa.
- Movimento dividido antes/depois da ação.
- Escalar, nadar, rastejar e saltar.
- Atravessar espaço de outra criatura.
- Levantar-se da condição Caído.
- Movimento com Deslocamento 0.
- Reação que interrompe outro turno e continuidade do turno.
- Ação bônus concedida por característica ou magia.
- Reação concedida por gatilho.
- Ataque de oportunidade considerando alcance, invisibilidade e alvo válido.
- Agarrar com mão livre, arrasto, distância e encerramento por incapacitação do imobilizador.
- Escape do agarramento por Atletismo ou Acrobacia com estado persistente.
- Ataque Desarmado com dano, Empurrar ou Agarrar como opções distintas.
- Combate montado: montar, desmontar, montaria controlada e independente.
- Queda do cavaleiro e salvaguarda de Destreza CD 10.
- Combate subaquático.
- Ataques com duas armas.
- Ataques múltiplos e divisão de movimento entre ataques.
- Objetos usados durante o combate.

### 3. Vida, dano e descanso

- Pontos de Vida atuais e máximos.
- Pontos de Vida Temporários.
- Cura limitada aos Pontos de Vida máximos.
- Cura que remove inconsciência.
- Tipos de dano.
- Resistência.
- Vulnerabilidade.
- Imunidade a dano.
- Ordem entre ajustes, Resistência e Vulnerabilidade.
- Dano com Pontos de Vida iguais a zero.
- Morte instantânea.
- Inconsciência.
- Estado Estável.
- Salvaguardas contra a Morte.
- 1 natural e 20 natural em Salvaguardas contra a Morte.
- Dano crítico contra criatura com 0 Pontos de Vida.
- Estabilização por Medicina CD 10.
- Recuperação após 1d4 horas estável.
- Exaustão por níveis.
- Penalidade de Exaustão em Testes de D20.
- Redução de Deslocamento por Exaustão.
- Morte no nível 6 de Exaustão.
- Descanso Curto.
- Gasto de Dados de Vida.
- Recuperação de recursos em Descanso Curto.
- Interrupção de Descanso Curto.
- Descanso Longo.
- Recuperação completa no Descanso Longo.
- Intervalo de 16 horas entre Descansos Longos.
- Interrupções e reinício do Descanso Longo.
- Recuperação de características por tipo de descanso.

### 4. Condições e efeitos

O motor atual apenas aplica/remove condições e resolve alguns efeitos de vantagem/desvantagem. Ainda faltam os efeitos completos de:

- Amedrontado.
- Atordoado.
- Caído.
- Cego.
- Contido.
- Enfeitiçado.
- Envenenado.
- Exaustão.
- Imobilizado.
- Incapacitado.
- Inconsciente.
- Invisível.
- Paralisado.
- Petrificado.
- Surdo.

Também faltam:

- Condições derivadas, como Incapacitado causado por Atordoado, Paralisado ou Inconsciente.
- Falha automática em salvaguardas de Força e Destreza.
- Crítico automático contra alvos Paralisados ou Inconscientes a curta distância.
- Deslocamento 0 e impossibilidade de aumento.
- Efeitos sensoriais de Cego, Surdo e Invisível.
- Efeitos sociais de Enfeitiçado.
- Linha de visão para Amedrontado.
- Encerramento de Concentração por Incapacitado.
- Não acumulação de condições iguais com durações independentes.
- Recuperação contextual de Caído e Inconsciente.

### 5. Magias e conjuração

O motor atual cobre somente espaço de magia e concentração básica. Ainda faltam:

- Magias preparadas por classe.
- Magias sempre preparadas.
- Alteração da lista preparada por classe.
- Truques sem gasto de espaço.
- Conjuração em espaço de nível superior.
- Limite de uma magia com espaço por turno.
- Magias rituais.
- Tempo adicional de 10 minutos para Ritual.
- Componentes Verbais, Somáticos e Materiais.
- Mãos livres.
- Bolsa de Componentes.
- Foco de Conjuração.
- Custos e consumo de componentes materiais.
- Treinamento em armadura para conjurar.
- Tempo de conjuração de Ação, Ação Bônus e Reação.
- Conjuração com duração de 1 minuto ou mais.
- Falha de conjuração longa e reinício.
- Alcance Pessoal, Toque e distância em metros.
- Linha de efeito e Cobertura Total.
- Áreas de efeito: Cilindro, Cone, Cubo, Emanação, Esfera e Linha.
- Validação de alvo e alvo inválido.
- Duração Instantânea, intervalo e Concentração.
- Encerramento voluntário.
- CD de salvaguarda de magia.
- Modificador de ataque mágico.
- Metade do dano em sucesso quando a magia determinar.
- Combinação e precedência de efeitos mágicos.
- Identificação de magia por Analisar e Arcanismo CD 15.
- Catálogo estruturado das magias do Livro do Jogador 2024.

### 6. Equipamento, armas e fabricação

- Catálogo completo de armas.
- Proficiência com armas.
- Propriedades Acuidade, Alcance, Arremesso, Duas Mãos, Extensão, Leve, Munição, Pesada, Recarga e Versátil.
- Maestrias Afligir, Ágil, Derrubar, Drenar, Empurrar, Garantido, Lentidão e Trespassar.
- Ataque adicional de armas Leves.
- Munição, recuperação e mão livre.
- Armaduras Leves, Médias e Pesadas.
- Limite de Destreza em armadura Média.
- Força mínima de armadura Pesada.
- Redução de Deslocamento por armadura.
- Desvantagem em Furtividade.
- Falta de treinamento em armadura.
- Armadura bloqueando conjuração sem treinamento.
- Escudo e limite de um escudo.
- Tempo para vestir e despir armaduras.
- Ferramentas e CDs de Usar Objeto.
- Ferramenta + perícia concedendo Vantagem.
- Inventário, peso e Capacidade de Carga.
- Moedas e conversão monetária.
- Contêineres, munição e objetos consumíveis.
- Montarias, selas e apetrechos.
- Veículos, tripulação, passageiros, carga e reparos.
- Estilo de vida, hospedagem, comida e serviços.
- Fabricação não mágica.
- Poção de Cura.
- Pergaminho Mágico.
- Ajudantes e divisão do tempo de fabricação.

### 7. Criação e progressão de personagens

- Matriz padrão de atributos.
- Compra por pontos.
- Rolagem de 4d6 descartando o menor.
- Criação de personagem completa.
- As dez espécies e seus traços.
- Tipo, tamanho e Deslocamento de cada espécie.
- Antecedentes.
- Aumentos de atributo de origem.
- Talento de Origem.
- Perícias, ferramentas e equipamentos de origem.
- As 12 classes.
- Dados de Vida por classe.
- Proficiências por classe.
- Equipamento inicial.
- Progressão de níveis 1 a 20.
- Características de classe.
- Subclasses.
- Ataque Extra e não acumulação entre classes.
- Aumento no Valor de Atributo.
- Talentos Gerais.
- Estilos de Luta.
- Dádivas Épicas.
- Pré-requisitos de talentos.
- Limite de atributo 20.
- Multiclasse.
- Pré-requisito 13 para multiclasse.
- Proficiências concedidas pela segunda classe.
- Níveis individuais e nível total.
- Dados de Vida em multiclasse.
- Conjuração em multiclasse.
- Pacto Mágico em multiclasse.
- Migração de antecedentes e espécies legadas.
- Persistência e não duplicação das escolhas.

### 8. Exploração, ambiente e interação social

- Ritmos de viagem Rápido, Normal e Lento.
- Distância por minuto, hora e dia.
- Penalidades e benefícios de cada ritmo.
- Necessidade de descanso após ritmo Rápido.
- Percepção passiva.
- Ação Procurar com Percepção ou Investigação.
- Ocultar com Furtividade CD 15.
- Gatilhos de revelação da condição Invisível.
- Luz Plena, Escuridão e obscurecimento.
- Visão no Escuro.
- Visão às Cegas.
- Escalada, natação, rastejamento e salto fora do combate.
- Interação gratuita com objetos.
- Segunda interação exigindo Usar Objeto.
- Objetos frágeis e resistentes.
- CA, Pontos de Vida, imunidades e Limiar de Dano de objetos.
- Capacidade de Carga.
- Queda e dano de queda.
- Asfixia.
- Combustão.
- Desidratação.
- Desnutrição.
- Riscos ambientais e Exaustão.
- Influência, Persuasão, Intimidação, Enganação e Intuição.
- Atitudes Amigável, Indiferente e Hostil.
- Consequências narrativas de NPC sem automatizar decisões.
- Ordem de resolução de efeitos simultâneos.
- Glossário normativo da edição 2024.

## Próxima prioridade

A ordem recomendada permanece:

1. Pontos de Vida, dano, morte e descanso.
2. Condições completas e efeitos derivados.
3. Alcance, cobertura, sentidos e alvos em combate.
4. Componentes, preparação e áreas de efeito de magias.
5. Equipamento, armas, armaduras e maestria.
6. Criação e progressão de personagens.
7. Exploração, riscos ambientais e interação social.
8. Catálogo detalhado das magias e características de classe.

A lista acima é a referência atual para determinar quando o Rule Engine estará realmente completo.
