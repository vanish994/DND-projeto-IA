# Design system — Taverna editorial

## Objetivo do produto

Levar a experiência de RPG de mesa para o celular: manter a agência do jogador, a continuidade da campanha e um diálogo legível com o Mestre de Jogo (MJ). A conversa é o foco; controles de campanha ficam claros e compactos.

## Direção visual

Taverna editorial — preservar o visual já usado pelo projeto, com carvão profundo, âmbar quente e títulos serifados. O resultado deve parecer uma mesa de aventura, sem ornamentos concorrendo com a leitura. Como o refinamento da paleta não foi escolhido, esta versão mantém as cores atuais da interface.

Referências de produto: Tales RPG e AI Dungeon inspiram narrativa conduzida pelo jogador, histórias customizáveis e continuidade. A implementação deve se inspirar nesses princípios, não reproduzir suas marcas ou telas.

## Cores e contraste

| Token | HEX | OKLCH | Uso |
|---|---|---|---|
| Fundo | #0e1012 | oklch(17.2% 0.005 248.1) | Fundo principal |
| Superfície | #15171a | oklch(20.4% 0.007 258.4) | Painéis e barra de composição |
| Superfície elevada | #1c1f23 | oklch(23.8% 0.009 255.6) | Mensagens do jogador, menus |
| Texto | #f5f1e9 | oklch(95.9% 0.011 84.6) | Texto principal |
| Texto secundário | #a6a09a | oklch(70.9% 0.011 67.6) | Rótulos e metadados |
| Âmbar | #d8a06f | oklch(74.8% 0.093 61.9) | Ações, seleção, pequenos destaques |
| Âmbar claro | #f1c28d | oklch(84.3% 0.087 69.6) | Hover e foco |
| Texto sobre âmbar | #21170f | oklch(21.5% 0.022 59.9) | Texto em botão âmbar |
| Sucesso | #7ecb9d | oklch(77.9% 0.101 156.8) | Estado positivo com rótulo |
| Erro | #e37979 | oklch(69.5% 0.132 21.0) | Erro com mensagem textual |
| Fundo afundado | #0a0c0e | oklch(13.9% 0.005 258.4) | Cartões internos da ficha |
| Véu de superfície | rgba(245, 241, 233, .04) | — | Chips e etiquetas sobre painéis |
| Linha forte | rgba(216, 160, 111, .42) | — | Bordas de destaque e seleção |
| Arcano | #9fb7d4 | oklch(74.8% 0.063 254.4) | Conjuração e espaços de magia |

Pares verificados (WCAG 2.2): texto/fundo 16.92:1; texto/superfície 15.94:1; secundário/superfície 6.94:1; âmbar/fundo 8.33:1; âmbar claro/fundo 11.66:1; texto de botão/âmbar 7.69:1; texto/fundo afundado 17.4:1; secundário/fundo afundado 7.55:1; âmbar/fundo afundado 8.54:1; arcano/fundo 9.26:1. Todos excedem 4.5:1 para texto normal.

Os rampas neutral-50…900 e amber-50…900 estão em frontend/design-tokens.css. A aplicação atual é dark-first; os níveis claros são para ilustrações, badges e futuros estados, não para grandes áreas de leitura.

## Tipografia

- Exibição: Georgia, fallback Times New Roman e serif. Use em títulos curtos e nomes de campanha.
- Interface: Inter, fallback system-ui/sans-serif. Use em mensagens, controles, metadados e botões.
- Não há download de fontes externas no MVP. Corpo mínimo de 16 px; metadados preferencialmente 12–14 px e nunca abaixo de 12 px.
- Hierarquia: título de campanha 22–28 px; título de tela 40–72 px responsivo; corpo 16 px / line-height 1.6; rótulo 12 px, caixa alta com espaçamento moderado.

## Layout e componentes

- Celular primeiro e uma viewport para a tela de conversa: use 100dvh (com fallback 100vh) e impeça rolagem do body. O cabeçalho fica no topo, o histórico é o único painel rolável e o compositor fica ancorado no rodapé. Ao abrir o teclado virtual, nenhum controle pode ficar inacessível.
- Desktop pode ampliar a navegação lateral, sem reduzir a largura de leitura da conversa. Se a lista de campanhas for longa, ela rola dentro do próprio painel/overlay, não na página inteira.
- Espaçamento em múltiplos de 4 px; tokens disponíveis até 64 px. Cantos: 8 px para elementos compactos, 12 px para controles, 16 px para painéis e bolhas.
- Início do jogador: mostrar apenas o nome do produto, campanhas recentes e ações Retomar/Nova campanha. Ocultar explicações do motor, indicadores técnicos e as seções 03/04 deste guia; detalhes ficam em Ajuda/Configurações.
- Campanha: nome visível, estado de carregamento e troca explícita; criar campanha não apaga nem arquiva silenciosamente outras.
- Mensagem do MJ: alinhamento editorial simples, avatar identificável e parágrafos com boa largura. Mensagem do jogador: superfície elevada e alinhamento oposto.
- Compositor: campo de texto e botão de envio; altura de toque mínima 48 px; foco visível; mensagem pendente não some em troca de campanha.
- Ações secundárias são discretas, mas com rótulos acessíveis; não esconder funções importantes atrás de ícone sem texto alternativo.

## Ficha, grupo e criação de personagem

Três superfícies em camadas: o diálogo usa `--color-surface`, os painéis usam `--color-bg` e os cartões internos usam `--color-surface-sunken`. O resultado é uma ficha legível sem depender de cor para transmitir estado.

- **Grupo:** cartão por personagem com nome em serifada, barra de PV, chips de CA e ataque, e um selo textual de situação (Saudável, Ferido, Grave, Inconsciente). Escolhas pendentes recebem alerta escrito, não apenas cor.
- **Ficha:** abas (Resumo, Atributos, Perícias, Equipamento e Magias) com `role="tablist"` e navegação por setas. A aba de magias só aparece quando o motor confirma conjuração para a classe.
- **Bloco de combate:** cartões com rótulo curto, valor em serifada e nota de origem (CA, Iniciativa, Proficiência, Deslocamento, Dado de Vida e CD de magia).
- **Chips de dados:** `d20 +5`, `1d8 + 3` e `CD 15` aparecem como chips com ícone de dado, tanto na ficha quanto no texto da narração — o texto da mensagem não é alterado, apenas marcado visualmente.
- **Dado do motor (`frontend/dado.js` + `dado.css`):** sempre que o Rule Engine rola um d20, a camada `.dado-camada` apresenta o dado girando antes de a narração aparecer, com rótulo, fórmula (`17 + 6 = 23 contra CA 15`) e veredito (Acerto, Erro, Crítico, Sucesso, Falha). Rolagens de dano usam a bandeja `.dado-bandeja` com um dado por valor. Depois da animação, o mesmo resumo fica fixo abaixo da mensagem em `.rolagem-cartao`, com o botão “Ver o dado” para rever. Nenhum número é sorteado no navegador: valor, modificador, total, CD/CA e veredito vêm prontos do motor.
- **Camada de dado é modal:** bloqueia clique, toque e foco no resto da tela enquanto gira. `Esc`, `Espaço`, `Enter` ou um toque fecham a camada imediatamente; passar o ponteiro sobre o painel pausa o fechamento automático, para dar tempo de ler.
- **Pré-visualização:** `frontend/dados-preview.html` (rota `/dados-preview.html`) mostra os estados do dado — acerto, crítico, teste com vantagem, salvaguarda falha, magia em área e rodada completa — sem precisar de campanha ou chave de API.
- **Perícias e salvaguardas:** lista com marca de proficiência (círculo âmbar), nome da perícia, atributo entre parênteses e total. A marca nunca é o único indicador: a linha traz o valor por extenso.
- **Assistente de criação:** passos numerados com trilha de progresso, resumo das escolhas acumuladas e cartões de seleção maiores. A revisão final mostra a ficha como ela ficará antes de o motor validar.
- **Equipamento:** listas vêm do catálogo oficial do servidor; itens sem proficiência aparecem desabilitados e identificados, porque o motor recusa o que a ficha não domina.

Nenhum valor de regra é calculado no navegador: CA, bônus de ataque, dano, salvaguardas e perícias chegam prontos no bloco `bloco` devolvido pelo backend (`fonte: rule_engine`).

## Voz e microcopy

- Personalidade: imersiva, colaborativa, concisa e clara nas regras.
- Boas-vindas: “A aventura continua de onde sua mesa parou.”
- Estado vazio: “Ainda não há mensagens. Conte onde a cena começa.”
- Erro: “Não foi possível carregar esta campanha. Tente novamente; seu histórico salvo não foi alterado.”
- Ação principal: “Retomar campanha” ou “Enviar”.
- O MJ conduz a narrativa; o motor valida mecânicas. Não prometa persistência entre dispositivos sem contas/sincronização.

## Acessibilidade e movimento

- Alvos de toque com pelo menos 48×48 px; foco com contorno âmbar visível.
- Status nunca depende somente da cor; texto deve acompanhar bolinhas e badges.
- Animações decorativas são curtas e removidas com prefers-reduced-motion. Com movimento reduzido, o dado não gira: o resultado aparece direto, com uma pausa curta por rolagem.
- A camada do dado é um `role="dialog"` com `aria-modal`, foco preso no botão “Continuar” e frase única em região `aria-live` (“Vex: Ataque com Espada Longa contra Goblin. d20 17 + 6 = 23 contra CA 15. Acerto”).
- App-shell usa altura dinâmica de viewport (100dvh, fallback 100vh) e body sem scroll. Somente o histórico e listas internas rolam. O compositor fixo usa env(safe-area-inset-bottom); teclado virtual e scroll interno não podem ocultar o envio.
- Use aria-live para novas respostas e rótulos explícitos para seletor, campo e ações.

## Camadas da conversa

- **Painel de campanhas:** cartão com título em serifada, data relativa, prévia da última mensagem, contagem de mensagens e ação “Retomar campanha”. A campanha aberta recebe borda âmbar e barra lateral.
- **Conversa:** coluna de leitura de até 48 rem centralizada; mensagem do MJ em bloco editorial com filete âmbar à esquerda; mensagem do jogador em superfície elevada; indicador de digitação com três pontos pulsantes.
- **Compositor:** campo com altura dinâmica, dica “O motor de regras rola os dados; o MJ narra o resultado” e botão de envio sempre alcançável sobre `env(safe-area-inset-bottom)`.
- **Avisos:** erros de lista, renomear e apagar aparecem como avisos flutuantes (`#avisos`), sem interromper a leitura do histórico.
- **Rolagem longa:** botão flutuante “↓” volta ao fim da conversa quando o histórico fica distante do rodapé.

## Referências consultadas

- Tales RPG: https://talesrpg.app/ — histórias customizáveis e escolhas que influenciam a narrativa.
- AI Dungeon: https://aidungeon.com/ — aventura textual aberta dirigida pelo jogador.
- Roll20: https://roll20.net/ — organização de campanha e automação integrada.
- Foundry VTT: https://foundryvtt.com/ — plataforma moderna e self-hosted de RPG.
