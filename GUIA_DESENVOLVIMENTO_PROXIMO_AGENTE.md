# Guia de desenvolvimento do próximo agente

## 1. Objetivo do projeto

Este projeto é um **Mestre de Jogo de Dungeons & Dragons em português do Brasil**, com duas camadas separadas:

```text
Interface + DeepSeek
  = narrativa, criatividade, condução da sessão e decisões do MJ

Rule Engine
  = autoridade determinística para mecânicas e regras oficiais
```

O objetivo não é criar uma aventura pré-fabricada. O MJ deve manter liberdade total para criar mundo, história, cenas, NPCs, conflitos, mistérios, diálogos e consequências narrativas.

A restrição do Rule Engine aplica-se somente às mecânicas apresentadas como regras oficiais de D&D. O MJ não deve inventar um monstro, magia, item, condição, estatística, habilidade, CD calculada ou regra caseira e apresentá-la como oficial.

## 2. Regra principal de continuidade

> **Antes de implementar qualquer coisa, ler este guia, o README, o inventário de regras e os arquivos envolvidos. Não refazer módulos que já existem. Não substituir a arquitetura atual sem necessidade.**

O próximo agente deve:

1. Inspecionar o estado atual do Git.
2. Ler este guia e o README.
3. Localizar a função ou regra existente antes de criar outra.
4. Reutilizar o `RuleEngine`, os catálogos, o backend e a interface atuais.
5. Adicionar testes antes ou junto de cada alteração.
6. Executar a suíte completa antes de publicar.
7. Fazer commits pequenos e descritivos.
8. Publicar no GitHub somente depois de validar localmente.
9. Atualizar este guia quando uma etapa importante for concluída.

Não apagar, reextrair ou recriar o bestiário, os catálogos ou o prompt do MJ sem evidência de corrupção.

## 3. Estado atual confirmado

### Repositório

- GitHub: `https://github.com/vanish994/DND-projeto-IA`
- Branch principal: `main`
- Deploy automático: GitHub `main` → Render
- Último estado validado: 235 testes aprovados no workflow [38156565465](https://github.com/vanish994/DND-projeto-IA/actions/runs/38156565465), após correções de progressão de conjuração e validação de magias

### Serviço online

- URL: `https://dnd-projeto-ia-mj.onrender.com/`
- API de status: `GET /v1/status`
- API do MJ: `POST /v1/mj/mensagem`
- Encerrar sessão: `DELETE /v1/mj/sessoes/{sessao_id}`
- Interface web: mesma URL do serviço Render

A chave `TOKENHARBOR_API_KEY` fica somente nas variáveis do Render. Nunca inserir chave no GitHub, no prompt, no frontend ou em logs.

### Interface já existente

Arquivos:

- `frontend/index.html`
- `frontend/styles.css`
- `frontend/app.js`

A interface segue `docs/DESIGN_SYSTEM.md` e `frontend/design-tokens.css` e já possui:

- Tela inicial com campanhas recentes (Retomar campanha) e Nova campanha.
- Celular: uma tela por vez (lista ou conversa), app-shell 100dvh sem rolagem da página; só o histórico rola.
- Desktop (≥ 900 px): lista lateral + conversa.
- Histórico carregado de `/v1/campanhas/{id}`; trocar de campanha não apaga histórico nem rascunho.
- Rascunho por campanha salvo no `localStorage`; se o MJ falhar, a mensagem volta para o campo.
- Opções da campanha: renomear e apagar.
- Diálogo Ajuda com a explicação MJ × motor (fora da tela inicial).
- `X-Jogador-Id` gerado no navegador (`localStorage`) enviado em toda chamada.

O backend serve a interface em `GET /` por meio de `StaticFiles`.

### Backend já existente

Arquivos:

- `backend/app.py`
- `backend/__init__.py`
- `requirements.txt`
- `render.yaml`

O backend já possui:

- FastAPI.
- Endpoint de status.
- Endpoint de conversa do MJ.
- Campanhas e mensagens persistidas (`backend/persistencia.py`, SQLAlchemy Core): SQLite local ou Postgres via `DATABASE_URL`.
- Endpoints REST de campanhas em `/v1/campanhas`, isoladas por `X-Jogador-Id` até existir login.
- Histórico enviado ao MJ limitado por `MJ_HISTORICO_MAX` (padrão 40).
- Tratamento básico de erro.
- Serviço Render configurado para Python.
- Deploy automático pela branch `main`.

Limitação conhecida: no Render gratuito o disco é efêmero; sem `DATABASE_URL` apontando para um Postgres, o SQLite é perdido a cada deploy ou reinício. Ainda não há login: `X-Jogador-Id` separa campanhas por navegador, mas não é autenticação.

### MJ DeepSeek

Arquivo principal:

- `integrations/deepseek_mj.py`

O adaptador já possui:

- DeepSeek como MJ conversacional.
- Compatibilidade com TokenHarbor.
- Ferramenta de sugestão de monstros.
- Ferramenta de consulta de monstro.
- Ferramenta genérica `resolver_regra`.
- Prompt normativo protegido.
- Histórico de mensagens.
- Limite de chamadas de ferramentas.
- Compatibilidade sem `extra_body` no TokenHarbor.

A personalidade editável está em:

- `config/mj_personalidade.txt`

O prompt permite narrativa e decisões livres do MJ, mas exige que afirmações mecânicas passem pelo motor.

## 4. Rolagens: contrato atual e obrigatório

A CD pertence à decisão do MJ. O resultado do d20 pertence ao Rule Engine.

O fluxo correto é:

```text
MJ decide a CD
  ↓
Rule Engine gera o d20
  ↓
Rule Engine devolve seed auditável
  ↓
MJ confirma ou define a CD
  ↓
Rule Engine reutiliza a seed
  ↓
Rule Engine calcula total e sucesso/falha
  ↓
MJ narra
```

O módulo já existente é:

- `rule_engine/dice.py`

A regra já registrada é:

- `ability-check.engine-roll`

Exemplo sem CD:

```python
pendente = engine.evaluate({
    "type": "ability_check",
    "ability": "carisma",
    "skill": "persuasao",
    "modifier": 5,
})
```

O resultado contém `roll`, `seed`, `modifier`, `total`, `roll_source` e `result=requires_dc`.

Depois:

```python
final = engine.evaluate({
    "type": "ability_check",
    "ability": "carisma",
    "skill": "persuasao",
    "modifier": 5,
    "dc": 15,
    "seed": pendente.outcome["seed"],
})
```

Não permitir que o DeepSeek invente `roll`. Não remover a seed. Não trocar a fonte da rolagem para o frontend sem uma decisão arquitetural explícita.

## 5. Rule Engine já implementado

O motor está funcional, mas não é 100% completo. Não afirmar ao usuário que o PHB 2024 está integralmente implementado.

Módulos principais existentes:

- `rule_engine/engine.py`: classes `Rule`, `Resolution` e `RuleEngine`.
- `rule_engine/rules.py`: registro central e prioridades.
- `rule_engine/core.py`: modificadores, proficiência e d20.
- `rule_engine/dice.py`: d20 auditável gerado pelo motor e rolagem auditável de dano (`rolar_dano_auditavel`).
- `rule_engine/damage.py`: normalização de tipos de dano e aplicação de resistência, vulnerabilidade e imunidade (fonte única do backend e do MJ).
- `rule_engine/ability_checks.py`: contratos e resoluções estruturadas de testes de habilidade.
- `rule_engine/survival.py`: PV, dano, cura, resistência, morte e exaustão.
- `rule_engine/combat_geometry.py`: alcance, distância, cobertura, queda e linha de visão.
- `rule_engine/combat_movement.py`: movimento, montaria e subaquático.
- `rule_engine/combat_special.py`: agarrar, empurrar e ataques de oportunidade.
- `rule_engine/conditions.py`: condições e efeitos derivados.
- `rule_engine/magic_equipment.py`: CA, armas, armaduras, conjuração e componentes.
- `rule_engine/spells.py`: catálogo e resolução de magias representativas; `mecanica_de_magia` devolve a mecânica já escalonada (truque pelo nível, círculo pelo espaço).
- `rule_engine/casting.py`: atributo de conjuração por classe, com a ficha tendo precedência.
- `rule_engine/economy.py`: inventário, economia, itens mágicos e sintonização.
- `rule_engine/tactical.py`: grade, flanqueamento, terreno e combate tático.
- `rule_engine/exploration_actions.py`: ações de exploração e interações fora do combate.
- `rule_engine/character.py`: criação, progressão e multiclasse.
- `rule_engine/class_progression.py`: matriz de características por classe e nível.
- `rule_engine/class_features.py`: características transversais e lotes de classes.
- `rule_engine/martial.py`: recursos marciais.
- `rule_engine/martial_subclasses.py`: catálogo/resolução parcial de subclasses marciais.
- `rule_engine/spellcasters.py`: conjuradores principais.
- `rule_engine/advanced_casters.py`: Bruxo, Feiticeiro e Guardião.
- `rule_engine/warlock_invocations.py`: invocações do Bruxo.
- `rule_engine/feats.py`: talentos de origem, gerais e épicos.
- `rule_engine/bestiary.py`: consulta, filtros, XP e operações do bestiário.
- `rule_engine/bestiary_blocks.py`: blocos completos preservados.

## 6. Bestiário: não refazer

O bestiário atual contém **232 blocos completos identificados no SRD 5.2.1 disponível no projeto**. Cada bloco preserva cabeçalho, traços, ações, ações bônus, reações e ações lendárias quando presentes.

Arquivos/documentos relacionados:

- `rule_engine/bestiary.py`
- `rule_engine/bestiary_blocks.py`
- `BESTIARIO_SRD_5_2_1.md`

Operações já existentes:

- Consulta por nome.
- Listagem.
- Filtro por tipo e ND.
- XP por ND.
- XP bruto de encontro.
- Sugestão determinística de candidatos para o MJ.
- Consulta do bloco completo.
- Consulta de seção.
- Validação contra alterações silenciosas.

O motor retorna candidatos; o MJ escolhe. Não inventar monstros para atingir uma quantidade maior. A fonte ativa contém 232 blocos, não “mais de 300”.

## 7. Lacunas reais prioritárias

### Prioridade 1 — Persistência de campanha

Campanhas e mensagens já são persistidas. Falta armazenar:

- Usuários e permissões.
- Estado de personagens.
- Grupo.
- PV, condições e recursos.
- Combates e iniciativa.
- Monstros ativos.
- Inventário e progresso.

Não transformar a conversa inteira em substituto do estado estruturado. O MJ deve consultar e atualizar estado explícito.

### Prioridade 2 — Estado estruturado da sessão

Criar contratos de dados versionados para:

- Campanha.
- Personagem.
- Grupo.
- Encontro.
- Turno.
- Recursos.
- Decisões narrativas relevantes.

O estado narrativo pode continuar livre; o estado mecânico precisa ser estruturado e auditável.

### Prioridade 3 — Interface de campanha

Expandir a interface sem quebrar o chat atual:

- Criar campanha.
- Criar/importar ficha.
- Lista de personagens.
- Ficha visual.
- Recursos e condições.
- Iniciar encontro.
- Ordem de iniciativa.
- Turno atual.
- Monstros sugeridos.
- Escolha manual do MJ.
- Blocos oficiais.
- Dados e resultados mecânicos separados da narrativa.

### Prioridade 4 — Concluir regras

Usar `REGRAS_LIVRO_JOGADOR_2024.md` como inventário, mas verificar o código antes de declarar uma lacuna. As áreas reconhecidamente incompletas incluem:

- Efeitos individuais de todas as 390 magias.
- Traços completos das espécies.
- Antecedentes.
- Características restantes das 13 classes.
- Efeitos completos das subclasses.
- Talentos completos.
- Listas de magias por classe.
- Progressões detalhadas de espaços por classe.
- Maestrias de armas em todos os contextos.
- Equipamentos iniciais.
- Veículos.
- Fabricação detalhada.
- Integrações entre classes, condições, magias e itens.
- Orçamento e dificuldade formal de encontros, caso a regra seja implementada.

Implementar por lotes pequenos, com uma regra, um teste e uma atualização do inventário por vez.

### Prioridade 5 — Segurança e produção

Antes de abrir para outras pessoas:

- Login.
- Permissões de MJ/jogador.
- Rate limit.
- Validação de entrada.
- Limite de tamanho de histórico.
- Logs sem segredos.
- Backups.
- Controle de sessões simultâneas.
- Tratamento de erro do provedor.
- Migrações de banco.

## 8. O que não fazer

Não fazer nenhuma destas ações sem necessidade comprovada:

- Recriar o bestiário.
- Reextrair o SRD.
- Criar um novo Rule Engine paralelo.
- Criar uma segunda API de regras.
- Mover a chave para o frontend.
- Fazer o DeepSeek calcular ou inventar d20.
- Fazer o motor narrar a campanha.
- Fazer o motor escolher monstros pelo MJ.
- Transformar toda decisão narrativa em regra.
- Apresentar regra caseira como PHB oficial.
- Trocar TokenHarbor/Render sem solicitação.
- Reescrever a interface inteira para adicionar um campo simples.
- Remover testes antigos porque estão “atrapalhando”.
- Declarar 100% de cobertura apenas porque a matriz de classes existe.

## 9. Validação obrigatória

Antes de cada commit:

```bash
python3 -m unittest discover -s tests -q
python3 -m compileall -q rule_engine integrations backend tests
node --check frontend/app.js
git diff --check
git status --short
```

A suíte deve permanecer verde. O último número validado é 235; se diminuir, investigar antes de continuar.

Para verificar o serviço online:

```bash
curl -sS https://dnd-projeto-ia-mj.onrender.com/v1/status
curl -sS -I https://dnd-projeto-ia-mj.onrender.com/
```

Para testar o MJ:

```bash
curl -X POST https://dnd-projeto-ia-mj.onrender.com/v1/mj/mensagem \
  -H 'Content-Type: application/json' \
  -d '{"sessao_id":"playtest-1","mensagem":"Descreva uma cena inicial sem fechar a história."}'
```

## 10. Política de commits

Usar commits pequenos, por exemplo:

```text
Adicionar persistência de campanhas
Adicionar teste para condição X
Implementar característica Y do Guerreiro
Adicionar painel de iniciativa
Corrigir rolagem auditável de Persuasão
```

Não juntar uma grande reescrita com mudanças não relacionadas. Após o commit:

```bash
git pull --rebase origin main
git push origin main
```

O Render faz deploy automático da branch `main`. Não publicar segredos.

## 11. Definição de pronto

Uma funcionalidade só deve ser marcada como concluída quando:

1. Está implementada no módulo correto.
2. Está registrada no `rules.py` se for uma regra do motor.
3. Possui teste determinístico.
4. Possui saída auditável.
5. Não quebra a suíte existente.
6. Está documentada no inventário.
7. Está publicada no GitHub.
8. Foi verificada no Render quando for funcionalidade online.

O próximo grande marco de produto é:

> **Uma campanha persistente com personagens, estado mecânico, combate e interface visual, mantendo o MJ livre para narrar e o Rule Engine como árbitro das regras.**


## Atualização — magias e Ataque de Sopro resolvidos pelo motor (2026-10-11)

Defeito relatado em mesa real: com o personagem conjurador, o MJ recusava truques
como ataque ("raio de fogo", "arma de sopro", "bola de fogo"), dizendo que o motor
não tinha registro da magia. Causas corrigidas:

- `resolver_regra` com `type=attack` e `magia` agora deriva o bônus de ataque do
  atributo de conjuração da ficha (`rule_engine/casting.py`), confere a CA no
  bestiário, aplica o escalonamento de truque e rola o dano da magia pelo motor.
- `resolver_regra` com `type=damage` e `magia` deriva os dados de dano do catálogo
  (com `espaco`/`aumento` para upcast) e devolve `cd_magia`, `magia_salvaguarda` e
  `magia_sucesso_metade` para o MJ resolver a área como manda a regra.
- O Ataque de Sopro do Draconato deixou de ser tratado como arma: resolve por
  salvaguarda de Destreza do alvo, com CD do traço (8 + Constituição + proficiência),
  dano por nível (1d10/2d10/3d10/4d10), metade no sucesso, defesas do bloco e usos
  por descanso longo.
- `cast_spell`/`spell` deixou de ser exclusivo do Artífice: qualquer classe
  conjuradora tem a magia validada contra a ficha, gasta o espaço e recebe
  `resultado=conjurada`; sem espaço, o motor bloqueia com motivo explícito.
- `/conjurar` usa o catálogo para escalonar o truque e o atributo de conjuração da
  ficha, e devolve `dados_dano`, `dano_expressao`, `tipo_dano` e `ca_alvo` para a
  interface animar sem recalcular nada.
- Tipos de dano do catálogo PT-BR ("ígneo", "gélido", "venenoso") passaram a casar
  com os tipos do SRD ("fire", "cold", "poison") na aplicação das defesas.
- Validação: 419 testes aprovados (`python -m unittest discover -s tests`).

## Atualização de cobertura — motor de regras (2026-10-11)

- Corrigida a progressão de espaços de magia do conjurador completo no nível 17.
- Corrigida a quantidade de magias preparadas do Mago para nível + modificador de Inteligência; a progressão de magias do Bardo usa tabela própria.
- Corrigidos truques por classe nos marcos de nível 1, 4 e 10 e normalização de nomes de classe com acentos.
- Adicionada progressão de conjuração do Paladino ao registro do Rule Engine; incluídos espaços do Feiticeiro e validação de níveis 1–20 para conjuradores avançados.
- Ações de conjurador ainda não implementadas agora são bloqueadas em vez de retornarem falsamente como resolvidas.
- Mãos Consagradas valida gastos negativos e valores acima do pool restante.
- Magias sem círculo identificado deixaram de ser classificadas como truques. Truques não podem gastar espaços, e espaços acima do 9º são bloqueados. Busca de magia normaliza acentos e espaços.
- Validação: 235 testes aprovados no workflow indicado acima.

Estas correções aumentam a precisão, mas o motor continua incompleto. Permanecem pendentes efeitos mecânicos das magias catalogadas, características e subclasses sem resolução específica, traços completos de espécies, integração de estado de recursos/combate e validação sistemática de todas as regras do PHB 2024.
