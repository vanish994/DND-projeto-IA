# Criador de mapas táticos — D&D 2024 para Android

## Decisão de arquitetura

O criador de mapas será um módulo Android nativo em Kotlin. A interface e a renderização tática ficam no aplicativo; o Rule Engine existente continua sendo a autoridade normativa do combate. O aplicativo não calcula resultados oficiais por conta própria e não aceita que o MJ/LLM sobrescreva uma resolução do motor.

O repositório atual tem backend FastAPI e Rule Engine em Python, mas não contém ainda um módulo Android/Kotlin. Portanto, esta especificação define a integração sem fingir que um APK ou módulo Android já existe.

## Experiência desejada

- Mapas ilustrados vistos de cima, com leitura clara de espaços e obstáculos.
- Grade quadrada de 5 pés (1,5 m) sempre visível durante o combate.
- Mapas gerados automaticamente a partir do local e do encontro descritos pela aventura.
- Tokens de personagens, aliados e monstros separados da arte do cenário.
- Terreno difícil, bloqueios, áreas de magia, alcance e caminho de movimento representados por camadas visuais.
- Interface priorizando toque e telas pequenas.
- Estado tático salvo junto à campanha, permitindo retomar o combate.

## Stack

### Aplicativo Android
- Kotlin.
- Jetpack Compose para telas e controles.
- Canvas do Compose (ou uma camada customizada equivalente) para desenhar o mapa, grade, destaques, caminhos, áreas e tokens.
- ViewModel + StateFlow para estado de tela.
- Kotlinx Serialization para os modelos JSON.
- Cliente HTTP Retrofit/Ktor para falar com o backend existente.

Não introduzir engine 3D nem Godot nesta fase: a vista é de cima e o mapa é 2D. A grade, os tokens e as regras de movimentação precisam ser determinísticos, fáceis de testar e baratos para rodar em Android.

### Backend
- Manter o FastAPI e o Rule Engine em Python como fonte autoritativa das regras.
- Adicionar endpoints táticos apenas quando houver uma resolução correspondente no motor.
- Guardar mapa e estado de encontro no armazenamento da campanha. Não mandar chaves de provedores de IA ao aplicativo.
- O gerador narrativo pode sugerir um cenário; o servidor converte a sugestão em um plano estruturado e valida os dados antes de persistir.

### Arte
- Usar uma imagem de cenário ilustrada sem personagens, grade embutida, números, texto ou símbolos de interface.
- Sobrepor a grade e todos os elementos de jogo em Kotlin. Isso mantém a grade perfeitamente alinhada e permite mover tokens.
- A arte pode ser gerada por IA ou escolhida de uma biblioteca de fundos. Para o protótipo, usar fundos locais incluídos no app; geração remota de arte é uma etapa posterior.
- A arte não é fonte de verdade mecânica. Obstáculos, terreno e células devem existir também como dados estruturados.

## Modelo de dados

Um mapa é um documento estruturado e versionável, não apenas um PNG.

```json
{
  "schema_version": 1,
  "map_id": "encounter-forest-001",
  "title": "Ruínas na floresta",
  "environment": "forest_ruins",
  "grid": {
    "width": 20,
    "height": 16,
    "feet_per_cell": 5,
    "visible": true
  },
  "background_asset": "maps/forest_ruins_01.webp",
  "cells": [
    {"x": 4, "y": 3, "terrain": "difficult", "blocked": false},
    {"x": 5, "y": 3, "terrain": "normal", "blocked": true}
  ],
  "tokens": [
    {"id": "hero-1", "kind": "character", "entity_id": "character-123", "x": 2, "y": 4},
    {"id": "enemy-1", "kind": "monster", "entity_id": "goblin", "x": 12, "y": 6}
  ],
  "encounter_id": "encounter-001"
}
```

Esse exemplo é um contrato proposto, não um endpoint já disponível. Os identificadores de monstros devem referenciar registros reais do catálogo; estatísticas não podem ser inventadas pelo mapa.

### Entidades Kotlin

- `TacticalMap`: identidade, cenário, tamanho, versão e fundo.
- `GridSpec`: largura, altura, pés por célula e visibilidade da grade.
- `MapCell`: coordenadas, terreno e bloqueio.
- `MapToken`: ID estável, tipo de entidade e coordenadas.
- `EncounterState`: turno atual, participantes e estado tático persistido.
- `MapActionRequest`: ação pretendida pelo jogador; não é resultado validado.
- `RuleResolution`: resposta autoritativa devolvida pelo backend.

Coordenadas usam origem no canto superior esquerdo: x cresce para a direita e y para baixo. Os dados guardam células inteiras; pixels só são calculados na camada de desenho.

## Geração a partir da aventura

1. O MJ descreve a cena e o encontro.
2. O backend extrai apenas metadados estruturados: ambiente, dimensões sugeridas, entradas/saídas, terreno e entidades participantes.
3. O gerador escolhe um layout conhecido para o ambiente e coloca os obstáculos em células explícitas.
4. O validador garante que o mapa cabe nos limites, que os tokens estão dentro da grade e que nenhum token começa em célula bloqueada.
5. A colocação inicial de monstros só usa entidades válidas do bestiário; a composição final do encontro continua sendo decisão do MJ/jogo, não da imagem.
6. O cliente carrega o fundo ilustrado e desenha a grade, obstáculos, tokens e indicadores.
7. O mapa e o estado inicial são salvos na campanha.

O LLM pode propor o tema ou um layout, mas sua resposta precisa ser convertida para o esquema, validada e limitada. Texto livre nunca é executado como regra.

## Regras de grade e movimento

- Uma célula equivale a 5 pés.
- A distância em quadrados, a diagonal, o alcance, a área de efeito, o terreno difícil e a linha de visão devem seguir a regra implementada pelo Rule Engine e suas convenções explícitas.
- Não presumir que todas as diagonais, coberturas ou geometrias funcionam de uma maneira sem validar a regra aplicável.
- O cliente pode mostrar uma prévia do caminho, mas o backend/motor decide se a ação é legal.
- Em ação rejeitada, o token volta à posição confirmada e a interface mostra a razão retornada pelo motor.
- Não usar colisão visual aproximada como substituto de validação mecânica.

## Contrato de integração recomendado

Os caminhos abaixo são propostas para implementar; não existem ainda por causa deste documento.

- `POST /v1/campanhas/{campanha_id}/mapas`: criar e validar mapa a partir de uma definição estruturada.
- `GET /v1/campanhas/{campanha_id}/mapas`: listar mapas da campanha.
- `GET /v1/campanhas/{campanha_id}/mapas/{mapa_id}`: carregar mapa e estado tático.
- `POST /v1/campanhas/{campanha_id}/encontros/{encontro_id}/acoes`: submeter uma ação pretendida para validação pelo Rule Engine.
- `PATCH /v1/campanhas/{campanha_id}/mapas/{mapa_id}`: persistir mudanças permitidas no layout ou posições não resolvidas mecanicamente.

A resposta de uma ação deve distinguir claramente: ação aceita, ação rejeitada, dados ausentes e regra ainda não implementada. Nunca transformar ausência de implementação em sucesso presumido.

## Renderização Android

Ordem de desenho recomendada:
1. imagem de fundo;
2. camada de células especiais e obstáculos;
3. grade sempre visível, com contraste suficiente mas sem esconder a ilustração;
4. áreas de alcance, caminho e área de efeito;
5. tokens com aro de aliado/inimigo e indicador de estado;
6. marcadores de seleção e controles acessíveis.

O zoom e o pan alteram somente a transformação visual, nunca as coordenadas táticas. Os alvos de toque devem ser grandes o bastante para uso em celular. A grade precisa continuar alinhada ao fundo em qualquer zoom.

## Segurança e autoridade

- O cliente não decide CA, PV, dano, condições, alcance legal ou resultados de dados.
- O MJ não pode editar diretamente uma resposta do motor.
- O backend valida o mapa e cada ação contra os dados oficiais disponíveis.
- Regras ausentes devem retornar `not_implemented`/equivalente, não um resultado inventado.
- O estado confirmado pelo motor é persistido; animações locais são apenas apresentação.

## Plano de implementação

### Fase 1 — Protótipo visual local
- Criar o módulo Android Kotlin e tela de combate.
- Renderizar um fundo ilustrado local, grade 20×16 sempre visível, tokens móveis e obstáculos.
- Adicionar pan/zoom e salvar/carregar o documento do mapa localmente.
- Não declarar regras de combate como integradas nesta fase.

### Fase 2 — Integração do encontro
- Adicionar modelos e persistência de mapas no FastAPI.
- Carregar fichas e monstros por IDs válidos.
- Implementar geração de layout estruturado e validação.
- Exibir claramente os campos mecânicos que ainda não são suportados.

### Fase 3 — Ações validadas
- Conectar movimento, ataque e efeitos às operações existentes ou novas do Rule Engine.
- Exigir resposta autoritativa para confirmar a ação.
- Cobrir com testes as fronteiras do mapa, bloqueios, terreno difícil, distâncias e rejeições.

### Fase 4 — Arte contextual
- Ampliar biblioteca de fundos por bioma/ambiente.
- Gerar ou selecionar arte sem texto, sem grade embutida e sem tokens permanentes.
- Vincular o cenário à aventura e permitir fallback offline com arte incluída no app.

## Critérios de aceite do primeiro protótipo

- [ ] Grade quadrada sempre visível e alinhada ao cenário.
- [ ] Cada célula equivale a 5 pés.
- [ ] Tokens podem ser selecionados e arrastados por toque.
- [ ] Células bloqueadas são visualmente distintas.
- [ ] Pan e zoom não alteram coordenadas nem deslocam a grade em relação ao cenário.
- [ ] Mapa pode ser salvo e reaberto sem perder posições.
- [ ] Uma ação não é mostrada como concluída antes da validação autoritativa.
- [ ] Arte, grade e tokens são camadas separadas.
- [ ] Testes automatizados cobrem conversão célula/pixel e validação estrutural do mapa.

## Próximo passo técnico

Como ainda não há um módulo Android/Kotlin no repositório atual, o próximo passo de implementação é criar a estrutura Gradle Android e a primeira tela de combate com um mapa local de demonstração. Depois, integrar os endpoints e o Rule Engine existente. Não afirmar que a integração está concluída até que esses componentes existam e os testes passem.
