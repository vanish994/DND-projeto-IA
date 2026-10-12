# Auditoria de mecânicas — truques, magias e itens

Data: 11/10/2026. **Retrato inicial, anterior às correções.** Os números e achados abaixo documentam a auditoria original; consulte a atualização ao final para o estado após o primeiro lote de correções.

## Método e limites

- Inventário executado sobre `listar_magias`, `resolver_magia` e `mecanica_de_magia`.
- Inspeção do caminho de seleção na ficha, ferramentas do MJ, conjuração tática e itens mágicos.
- Reprodução local de quatro problemas de validação/efeito, sem provedor externo.
- Suíte existente: `python -m unittest discover -s tests -q`: **422 testes, OK**, sem skips reportados.
- Reexecutar o inventário: `python scripts/auditar_mecanicas.py`. A saída JSON inclui todas as entradas e os motivos de indisponibilidade.
- Esta não é uma certificação de todas as classes, talentos, monstros ou de fidelidade integral ao PHB. Não houve teste com uma conversa real do provedor de IA nem conferência individual das centenas de entradas com o livro.

## Resumo medido

| Medida | Quantidade |
|---|---:|
| Entradas no catálogo de magias | 349 |
| Sem círculo confirmado | 243 |
| Com círculo confirmado | 106 |
| Com mecânica estruturada | 18 |
| Retornam `conjurada` no resolvedor isolado | 22 |
| Retornam `nao_implementado` | 327 |
| Truques identificados como círculo 0 | 21 |
| Truques com mecânica estruturada | 1 |

**As 349 entradas não significam 349 magias oficiais únicas e corretas.** O catálogo é extraído de texto e contém metadados incompletos. Os 21 truques são apenas os que o sistema identifica como círculo 0, não uma lista completa de truques do livro.

`conjurada` também não significa que dano, cura ou condição foram aplicados. Quatro magias recebem esse resultado sem mecânica estruturada: **Raio Místico, Contramagia, Dissipar Magia e Reviver os Mortos**.

## Truques: o que falta

| Situação | Truques |
|---|---|
| Mecânica de ataque e dano, com escalonamento | Raio de Fogo |
| Descrição reconhecida, sem mecânica de múltiplos raios | Raio Místico |
| Sem efeito específico no resolvedor | Acudir os Moribundos; Bolha Ácida; Chicote de Espinhos; Congelamento; Consertar; Criar Fogueira; Explosão de Espadas; Luz; Luzes Dançantes; Mensagem; Mão Mágica; Orientação; Pedra Mágica; Prestidigitação Arcana; Raio de Gelo; Rajada de Veneno; Resistência; Toque Chocante; Trovão |

Para implementar não basta inserir dados de dano. São necessários alcance, tipo de ação, alvos, ataque ou salvaguarda, escalonamento, condições, duração, concentração e efeitos secundários conforme a edição adotada. Truques utilitários precisam de limites e estado quando pertinente, não de uma rolagem de dano artificial.

O projeto declara PHB 2024 em `spells.py`, mas a lista do Artífice em `spellcasting.py` declara Tasha. A edição de cada entrada deve ser definida antes de preencher os efeitos. As fórmulas existentes, inclusive Palavra Curativa, precisam de conferência com a fonte escolhida; passar no teste atual apenas confirma a fórmula cadastrada.

## Prioridades confirmadas

### P0 — resultado de sucesso sem efeito executado

**Fonte:** `rule_engine/spells.py::resolver_magia`; `integrations/deepseek_mj.py::DeepSeekMJ._tool`.

O resolvedor considera suficiente ter o campo textual `efeito` para retornar `conjurada`. A integração gasta um espaço quando recebe esse status, mesmo sem uma resolução específica do efeito.

**Reprodução executada:** mago sintético de nível 5, Contramagia preparada, dois espaços de 3º círculo. A ferramenta retornou `conjurada`, texto `interrompe magia`, nenhum campo `mecanica`, e reduziu os espaços para um. Não houve resolução de uma conjuração adversária.

**Correção recomendada:** distinguir consulta/descrição, validação da conjuração e execução do efeito. Só confirmar sucesso e consumir recursos quando a operação suportada estiver resolvida; informar limites sem inventar consequências.

### P0 — validação incompleta no caminho de dano do chat

**Fonte:** `integrations/deepseek_mj.py::_preparar_dano_de_magia`.

A checagem usa `if registradas and ...`: uma lista vazia não bloqueia a magia. Esse caminho também calcula dano separadamente do consumo/validação de espaços.

**Reprodução executada:** ficha sintética de mago nível 1, lista de magias preparadas vazia, solicitação de Bola de Fogo. O preparador devolveu `damage_expression: 8d6` e CD 13 em vez de bloquear. Isso demonstra falha de validação, não aplicação persistida de dano.

**Correção recomendada:** validação central de ficha, classe, nível, magia conhecida/preparada e recursos, comum a ataque, dano e conjuração; distinguir uma consulta de fórmula de uma ação de jogo.

### P1 — mapa tem cobertura bem menor que o catálogo

**Fonte:** `backend/app.py::conjurar_no_mapa_tatico`; `frontend/mapa-tatico.html`, seletor `spell-choice`.

- A rota bloqueia conjuradores de outras classes: apenas Artífice é aceito.
- O seletor é fixo em **Raio de Fogo, Curar Ferimentos e Onda Trovejante**; não deriva as opções da ficha.
- Há ramos para ataque mágico, Curar Ferimentos, áreas e condições com salvaguarda de fim de turno. A lista real do catálogo não fornece uma magia de condição com esse último metadado; a infraestrutura por si só não torna essas magias utilizáveis.
- Áreas aceitam cubo/esfera; cone e linha são rejeitados. A esfera existe no código, mas isso não supera a restrição à lista de Artífice.
- Armadura Arcana, Escudo, Escudo da Fé, Bênção, Invisibilidade, Voo e Passo Nebuloso têm metadados, mas não têm ramo tático compatível para executar seus efeitos atuais.
- Não há chamada à aplicação de resistências, imunidades ou vulnerabilidades no caminho de dano de magia dessa rota, embora exista nos ataques com arma/monstros.
- Onda Trovejante declara empurrão no catálogo, mas a rota não desloca os tokens atingidos.
- Curar Ferimentos não consegue tratar um alvo com 0 PV: a rota rejeita esse alvo antes de identificar o tipo de magia.
- A rota verifica o turno ativo, mas não consome a disponibilidade de ação/ação bônus/reação. O controle de ações existe em módulo separado.
- Componentes são passados à resolução como `V, S, M` disponíveis, sem checagem de posse dos materiais nessa rota.
- O dano de área é rolado dentro do laço de alvos, não como uma única rolagem compartilhada.
- A salvaguarda de monstros nessa área força falha no 1 natural e sucesso no 20 natural. Essa regra deve ser corrigida para salvaguardas comuns, que dependem do total versus CD.

Estes pontos foram constatados por inspeção da rota; não foram todos reproduzidos em testes HTTP novos nesta auditoria.

### P1 — seleção permite prometer suporte que não existe

**Fonte:** `backend/app.py::catalogo_magias`, `_validar_conjuracao`, `catalogo_conjuracao`; `frontend/personagens.js::listaEscolhaMagias`.

- Só o Artífice tem lista filtrada e validação específica de escolhas nessa API.
- Para outras classes, a API retorna o catálogo geral e a progressão marca `validacao_escolhas: false`.
- Os cartões de escolha mostram nome/escola, não o estado de implementação.
- Entradas sem círculo não recebem uma classificação confiável de truque/magia.

**Correção recomendada:** expor separadamente `catalogada`, `regra implementada`, `executável no chat` e `executável no mapa`, além de validar listas por classe. Não remover silenciosamente as escolhas já salvas.

### P1 — itens mágicos são majoritariamente descrições de efeito

**Fonte:** `rule_engine/economy.py::ITENS_MAGICOS`, `usar_item_magico`, `resolver_sintonizacao`; integração `_tool`.

Há oito itens mágicos cadastrados: duas poções de cura, Varinha de Mísseis, Anel de Proteção, Manto de Proteção, Botas de Velocidade, Amuleto de Saúde e Bolsa de Componentes.

`usar_item_magico` retorna o identificador textual do efeito; não rola a cura, não aplica bônus de CA/salvaguardas/Constituição/deslocamento e não atualiza sozinho a ficha ou o inventário. Só decrementa cargas no retorno quando o chamador fornece `cargas`; a recarga da varinha é texto de catálogo. O callback de persistência da ferramenta revisada cobre espaços de magia, não uma transação de uso desses itens.

**Reprodução executada:** `usar_item_magico({'item': 'pocao_de_cura'})` retorna `usado` e `cura_2d4_mais_2`, sem cura numérica ou consumo persistido.

**Outro defeito reproduzido:** encerrar sintonia de um Anel de Proteção já sintonizado retorna `item_ja_sintonizado`. A verificação de duplicidade ocorre antes do ramo `acao == 'encerrar'`; esse ramo também não remove o item da lista retornada.

Isso não significa ausência total de regras de equipamentos: armas, armaduras, CA, carga e economia têm módulos próprios. O problema destacado aqui é execução e persistência dos efeitos dos itens mágicos.

### P2 — qualidade do catálogo e ciclo de vida de efeitos

**Fonte:** `rule_engine/spells.py`, construção de `MAGIAS` e `_DETALHADAS`.

- Muitas entradas têm componentes e duração preenchidos por padrões genéricos.
- Entradas detalhadas não concentradas recebem duração `instantânea`, mesmo quando a mecânica específica declara duração maior, como Armadura Arcana. A descrição e os campos estruturados podem divergir.
- É necessário ligar origem do efeito, duração, concentração, substituição, expiração e remoção dos bônus. Ter uma string de duração ou `concentrando` na ficha não comprova esse ciclo completo.

## Ordem recomendada de correção

1. Bloquear falsos sucessos e fechar as lacunas de validação sem consumir recursos indevidamente.
2. Mostrar o nível real de suporte na escolha de truques/magias e na ficha.
3. Corrigir as regras já expostas: dano mágico versus defesas, cura a 0 PV, empurrão, ações e salvaguardas/rolagem de área.
4. Implementar os truques ofensivos com testes ponta a ponta e efeitos secundários; depois os utilitários e de suporte.
5. Validar listas das demais classes e substituir o seletor fixo do mapa por capacidades reais da ficha.
6. Executar e persistir consumíveis, cargas, sintonia e bônus de itens; revisar o catálogo com as fontes oficiais adotadas.

## Critérios mínimos para considerar uma mecânica pronta

- Regra e edição explícitas; nome e aliases normalizados.
- Validação de conhecimento/preparação, classe/nível, alvo, alcance, componentes e recursos.
- Rolagens auditáveis e efeitos corretos, inclusive defesas e escalonamento.
- Persistência de PV, condições, concentração, duração, cargas e espaços quando aplicável.
- Sem alterações de estado em falha; sem gasto duplicado em chamadas relacionadas.
- Interface distingue ausência de suporte de ação proibida pelas regras.
- Testes do resolvedor e integração HTTP/ferramenta; não apenas presença no catálogo.


## Atualização — primeiro lote de correções

Implementado nesta sessão, com regras dos novos truques conferidas no PDF local:

- **Rajada de Veneno** (PHB 2024 p. 324 / PDF p. 330): ataque à distância de 9 m, 1d12 venenoso, escala 5/11/17.
- **Trovão** (PHB 2024 p. 340 / PDF p. 346): emanação de 1,5 m, Constituição evita dano, 1d6 trovejante escalonável, exclui o conjurador.
- **Bolha Ácida** (PHB 2024 p. 249 / PDF p. 255): esfera de 1,5 m a até 18 m, Destreza evita dano, 1d6 ácido escalonável. No mapa atual o centro usa o token selecionado, não um ponto livre.
- As três entradas usam **efeitos PHB 2024**, mantendo a lista de acesso do Artífice já adotada pelo projeto; não são uma implementação alternativa dos efeitos antigos de Tasha.
- As quatro magias sem mecânica estruturada deixaram de retornar sucesso e consumir espaços na ferramenta do MJ.
- Cálculo de dano exige ficha, magia registrada e círculo existente, rejeitando espaços inválidos e aumentos contraditórios. Cálculo e consumo de espaço continuam etapas separadas; a resposta indica que PV não foram aplicados. Uma transação única de conjuração/dano no chat ainda está pendente.
- Cura de aliado a 0 PV funciona no mapa; conjurador a 0 PV não pode se curar por essa rota.
- Ataques mágicos aplicam imunidade, resistência e vulnerabilidade no mapa e no cálculo de ataque do chat. Áreas no mapa também aplicam essas defesas.
- Áreas compartilham a rolagem de dano; salvaguardas da rota usam total versus CD, sem sucesso/falha automática de 20/1. Corrigido o envio do modificador de atributo, que antes bloqueava salvaguardas de personagens nessa rota.
- Encerrar sintonia remove o item da lista retornada, inclusive com três itens sintonizados. Isso não implementa a persistência geral do inventário.
- A API informa suporte e limitações. A ficha mostra os avisos; o mapa deriva as opções das magias registradas e deixa indisponíveis as sem resolução. Círculo `null` não aparece mais como truque na criação.

**Inventário atualizado:** 349 entradas, 21 com mecânica estruturada, 4 truques estruturados; 21 respostas `conjurada` e 328 `nao_implementado` no resolvedor isolado. O aumento de `nao_implementado` é intencional: quatro falsos sucessos foram removidos e três truques ganharam regra.

**Ainda pendente:** Raio Místico e demais truques, classes além de Artífice no mapa, empurrão de Onda Trovejante (sinalizado como parcial), consumo de ações/reação, ciclo completo de duração/concentração, aplicação de diversos efeitos estruturados, consumíveis/cargas e persistência de itens. As correções não tornam todas as entradas executáveis.

**Validação:** suíte Python ampliada para 441 testes aprovados; inclui ferramenta do MJ, escalonamento, suporte no catálogo, HTTP do mapa, cura a 0 PV, alcance, área compartilhada e defesas. JavaScript alterado validado sintaticamente. Sem chamada a provedor real de IA.
