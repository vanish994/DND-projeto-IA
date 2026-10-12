# Matriz de cobertura funcional e plano de correção

**Data:** 11/10/2026. **Base:** árvore de trabalho desta sessão, incluindo as correções recentes de magias, não o conteúdo remoto de `main`.

## Entregáveis

- [Planilha detalhada — 802 entradas](matriz_cobertura.csv): abra como CSV UTF-8 em uma planilha e filtre por família, recurso ou prioridade.
- Gerador: `scripts/gerar_matriz_cobertura.py`.
- Reprodução dos riscos críticos: `scripts/reproduzir_riscos_playtest.py` (SQLite em memória, sem campanha real nem provedor).
- [Auditoria inicial das magias e atualização das correções](AUDITORIA_MECANICAS.md).

## Como interpretar a matriz

Cada linha informa **nome do recurso, grupo, níveis, arquivo/resolvedor, fatos usados no probe, retorno observado, rotas alternativas a revisar, integração conhecida, lacuna, referências a testes e prioridade**.

As camadas são independentes:

1. **Catálogo:** nome/metadados registrados.
2. **Resolvedor:** existe código que responde a uma entrada. Um retorno `resolvido` não comprova fidelidade ao livro.
3. **Integração:** ficha, chat ou mapa usa e persiste o resultado. Texto de efeito e quantidade máxima de usos não significam consumo de recurso.
4. **Teste:** cenário verificável. Um teste de consulta ou de bloqueio não certifica execução completa.

**Limites do levantamento automático:**

- Probes de classes são chamadas ao resolvedor genérico `resolver_caracteristica`, no primeiro nível catalogado, com parâmetros mínimos; a saída completa fica na coluna `evidencia`. Não cobrem todas as opções nem situações de combate.
- Também é consultado um nível abaixo, quando possível. P0 nessas linhas significa comportamento suspeito frente à própria matriz, não que a matriz já tenha sido conferida integralmente com o livro.
- `rotas_relacionadas` é um mapa manual de caminhos já existentes, para evitar criar uma segunda implementação. Essas rotas não são consideradas aprovadas automaticamente.
- As referências de testes vêm de **literais encontrados por AST**, com arquivo, linha e método. São pistas para revisão, não medição de cobertura. Ausência de referência não prova ausência de teste parametrizado.
- A planilha não inventaria cada ação de cada monstro, cada invocação nem cada traço de espécie. Espécies e antecedentes têm uma linha por entrada. Os fluxos operacionais são tratados na tabela abaixo.
- Não foi calculado “percentual do D&D implementado”. Sem conferir a fonte e o ciclo completo, esse percentual seria enganoso.

## Inventário confirmado

| Família | Quantidade | O que a medida significa |
|---|---:|---|
| Classes | 13 | Classes na matriz de progressão |
| Características de classe | 202 | Pares únicos classe/característica; 281 ocorrências por nível |
| Subclasses na progressão geral | 56 | Entradas de `SUBCLASSES_BY_CLASS`, não 56 implementações |
| Subclasses no módulo marcial | 17 | Inclui um alias; são 16 nomes canônicos distintos |
| Características de subclasses marciais | 81 | Pares subclasse/característica, incluindo o alias |
| Talentos | 76 | 12 origem, 43 gerais, 12 épicos e 9 dádivas sombrias |
| Espécies | 10 | Entradas básicas de criação, não todos os traços |
| Antecedentes | 20 | 16 PHB e 4 Ravenloft |
| Magias | 349 | Entradas extraídas/cadastradas; não quantidade de magias oficiais validadas |
| Itens mágicos | 8 | Entradas em `ITENS_MAGICOS` |

Resultados dos probes isolados:

- **Classes:** 112 dos 202 pares retornam `nao_implementado` no resolvedor genérico. Isso **não significa 112 efeitos ausentes de todo o motor**: Fúria, Ataque Extra e outros possuem rotas separadas em `martial.py`, por exemplo.
- **Subclasses marciais:** 14 pares retornam `resolvido`; 67 retornam `nao_implementado`. Os 14 ainda precisam de verificação de aplicação, recursos e fidelidade.
- **Talentos:** apenas Vigoroso tem resolução específica em `resolver_talento`; os outros 75 retornam `nao_implementado` com pré-requisitos básicos habilitados. Há integração concreta de Vigoroso nos PV máximos em `ficha_personagem`.
- **Magias após nossas correções:** 21 mecânicas estruturadas; 4 truques estruturados. Rajada de Veneno, Trovão e Bolha Ácida se somaram a Raio de Fogo. Outros efeitos e classes no mapa continuam limitados.

## P0 — reprodução inicial (correções na atualização ao final)

### 1. Recurso usado antes do nível de desbloqueio

**Caminho:** `build_default_engine()` → regra `class.feature` → `resolver_caracteristica`.

| Entrada | Marco na própria matriz | Retorno observado |
|---|---:|---|
| Guerreiro, nível 1, `surto_de_acao` | 2 | `resolvido`, ação adicional |
| Monge, nível 1, `corpo_e_mente` | 20 | `resolvido`, +4 Destreza e +4 Sabedoria |

O resolvedor verifica se o nível está entre 1 e 20, mas não aplica uma guarda comum de desbloqueio para cada recurso. Há outro risco: dados da classe/nível precisam vir da ficha, não de um argumento livre do modelo.

**Próximo lote:** validar requisito pela ficha autoritativa, conferir os marcos com as fontes adotadas e aplicar a mesma guarda às rotas especializadas. Não corrigir apenas o botão da interface.

**Aceite:** abaixo do nível bloqueia; no nível correto permite; classe incompatível bloqueia; nenhum recurso ou estado muda em falha; testes passam pela ferramenta do MJ, não só pela função isolada.

### 2. Falha do provedor pode deixar gasto sem mensagem

**Caminho:** `backend/app.py::_responder` → callback `salvar_estado_personagem` → ferramenta de conjuração → falha posterior do provedor → HTTP 502.

Reprodução local com erro **429 simulado**, depois da ferramenta, e dois espaços iniciais:

| Tentativa | HTTP da aplicação | Espaços restantes | Mensagens salvas |
|---|---:|---:|---:|
| Antes | — | 2 | 0 |
| Primeira falha | 502 | 1 | 0 |
| Repetição da mensagem | 502 | 0 | 0 |

O callback grava a ficha antes de a resposta inteira terminar. `registrar_troca` só grava as mensagens depois do sucesso. O teste existente de falha do provedor cobre falha **antes** de qualquer alteração; ele não garante rollback ou repetição segura após ferramenta.

**Próximo lote:** definir operação com identificador estável e resultado persistido, incluindo rolagens, consumo e estado da resposta; repetir a mesma operação não deve executar a ação novamente. Alternativamente, staging transacional com commit explícito — sem manter transação de banco aberta durante chamadas lentas de rede. Concorrência entre ações precisa ser tratada junto.

**Aceite:** falhas antes/depois da ferramenta, timeout após commit, duplo clique e repetição do mesmo identificador; verificar espaços, PV, rolagens e mensagens, inclusive após reiniciar o repositório.

**Importante:** o 429 acima é simulado. Não consultei logs remotos nem confirmei o incidente de produção descrito no texto enviado.

## Matriz dos fluxos de integração

| Fluxo | Responsáveis | O que existe | Falta / limite atual | Evidência de teste existente | Prioridade |
|---|---|---|---|---|---|
| Características de classe | `class_features.py`, `martial.py`, `spellcasters.py`, `advanced_casters.py`, `rules.py` | Resolvedores específicos e progressões | Guarda comum de nível/classe; aplicação e consumo persistidos; reconciliar rotas duplicadas | `test_class_features.py`; cenários em `test_rule_engine.py` | P0 |
| Subclasses | `class_progression.py`, `martial_subclasses.py` | Tabela parcial e 14 respostas específicas nos probes | Efeitos ausentes; requisitos situacionais, recursos e integração; conferir marcos genéricos de subclasse | `test_subclass_coverage.py` testa inclusive bloqueios honestos | P1 |
| Talentos | `feats.py`, `character.py` | Validação de parte dos requisitos; Vigoroso soma PV | Demais efeitos, escolhas e recursos; conferir pré-requisitos com livro | `test_feat_coverage.py`, `test_personagens.py` | P1 |
| Espécies e antecedentes | `character.py`, `species.py`, `backgrounds.py` | Criação, escolhas, atributos/perícias; herança e cálculo de sopro | Catálogo completo de traços e integração de usos/recarga; antecedentes dependem dos talentos | `test_character_coverage.py`, `test_escolhas_criacao.py`, `test_personagens.py`, sopro em `test_magias_como_ataque.py` | P1/P2 |
| Ataque de arma | `backend/app.py::atacar_token_tatico`, integração MJ | Ataque, CA, dano, efeitos de condições, defesas | Validar sequência completa de ações extras/recursos e interações por classe | `test_combat_integration.py`, `test_mapa_tatico.py` | P1 |
| Magias no mapa | `conjurar_no_mapa_tatico`, `spells.py` | Ataque, cura, áreas e defesas; três novos truques | Só Artífice; ação/reação; empurrão; demais efeitos; centro de área usa token | `test_mapa_tatico.py`, `test_mecanicas_corrigidas.py`, `test_magias_como_ataque.py` | P1 |
| Monstros | `bestiary.py`, `bestiary_blocks.py`, `backend/app.py` | Blocos, ataques, alguns efeitos e Fortitude de Morto-Vivo | Reações, conjuração, agarrar/engolir e demais capacidades por bloco | `test_bestiary_srd.py`; ataque de monstro/zumbi em `test_mapa_tatico.py` | P1 |
| Condições e turnos | `conditions.py`, `turns.py`, `backend/app.py` | Iniciativa persistida, expiração numérica e alguns textos, salvaguardas de término | Cobertura não universal; efeitos por origem, concentração e ações precisam de cenários adicionais | `test_mapa_tatico.py`, `test_condition_saving_throws.py`; `test_turn_saving_throw_integration.py` contém principalmente validação de payload | P1 |
| Retomada de campanha | `persistencia.py`, `app.py` | Campanhas, mensagens, personagens, mapa e dados de iniciativa | Teste completo com reabertura de banco e estado mecânico; transação única por ação | `test_backend_campanhas.py`, `test_personagens.py`, `test_mapa_tatico.py` | P0/P1 |
| Provedor indisponível | `_diagnostico_erro_provedor`, `_responder`, `frontend/app.js` | Mensagem de erro e rascunho restaurado no frontend; tratamento de 429 | Repetição segura após ferramenta, identificação da operação, concorrência | `test_backend_campanhas.py::test_falha_do_provedor_nao_grava_mensagem` não cobre alteração prévia | P0 |
| Teste pendente de CD | `dice.py`, `rules.py`, `deepseek_mj.py` | Seed auditável; repetir a mesma seed conserva o d20 | Identificar teste pendente no servidor; não depender de a IA reenviar a seed | `test_rule_engine.py` verifica seed preservada quando informada | P0/P1 |
| Banco em produção | `persistencia.py`, `render.yaml` | SQLite local e suporte a `DATABASE_URL`; variável declarada no deploy | Confirmar configuração real, backup e persistência após deploy; declaração não comprova banco provisionado | Teste de normalização da URL em `test_backend_campanhas.py` | P0 operacional |
| Android | `docs/CRIADOR_MAPAS_TATICOS.md` | Especificação, backend e mapa web | Módulo Gradle/Kotlin, app nativo e testes de integração Android | Não encontrado módulo nativo neste checkout | P2, se exigido no lançamento |

## Ajustes ao diagnóstico enviado

- **17 subclasses** é o tamanho do módulo marcial, não o total do catálogo de progressão, que tem 56 entradas.
- **Expiração de condições não está totalmente ausente.** Há testes de durações numéricas e de alguns textos. Não estender essa conclusão a toda condição/efeito.
- **Sopro do Draconato** já calcula ataque por salvaguarda, dano escalonado e defesas no chat; retornar `usos_por_descanso_longo` não comprova desconto de uso persistido.
- **Repetição de d20** tem base determinística e teste de mesma seed. O relato “19 virou 7” não foi reproduzido como incidente histórico; o vínculo obrigatório entre operação e seed ainda precisa ser garantido no servidor.
- **429 é distinguido na mensagem de erro**, mas o HTTP da aplicação permanece 502. O problema prioritário não é só a mensagem: é o estado que já pode ter sido gravado.
- **Magias corrigidas nesta sessão** e avisos de suporte já fazem parte desta matriz; não precisam ser reimplementados.

## Ordem sugerida dos próximos lotes

1. **Integridade de operação:** persistência/idempotência e rolagens pendentes; reprodução de falha após ferramenta deve deixar de gastar novamente na repetição.
2. **Autoridade de ficha e requisitos:** centralizar nível, classe, escolha, usos disponíveis e alvo para recursos; conferir matriz com o livro antes de torná-la regra de bloqueio universal.
3. **Fatia vertical de classes:** uma característica por vez, começando por Surto de Ação, Recuperar Fôlego e Fúria; ativar → resolver → persistir → retomar → recuperar no descanso.
4. **Combate completo:** integrar condições, concentração, consumo de ações e efeitos secundários; cenários com jogador e monstro, acerto/falha/imunidade.
5. **Expandir subclasses, talentos, traços e magias** usando os mesmos serviços de recursos e efeitos, sem tabelas executáveis concorrentes.
6. **Deploy/playtest e Android:** comprovar banco persistente, falhas recuperáveis e limites do provedor; app nativo é entrega separada.

## Reprodução e validação

```bash
.venv/bin/python scripts/gerar_matriz_cobertura.py
.venv/bin/python scripts/reproduzir_riscos_playtest.py
.venv/bin/python -m unittest discover -s tests -q
```

Na entrega inicial de auditoria foram adicionados inventário, documentação, reproduções e testes do gerador, sem alterar regras. As correções posteriores estão descritas abaixo. Não houve chamada a provedor real, acesso ao Render ou uso de campanha do jogador para os probes.

**Validação da auditoria inicial:** 445 testes Python aprovados (441 existentes + 4 testes do inventário). A reprodução local de falha após ferramenta continua expondo o gasto duplicado descrito acima; aprovação da suíte não significa que esse risco esteja corrigido.


## Atualização — correções aplicadas em 12/10/2026

**Já corrigido no código, não apenas documentado:**

1. **Falha do provedor após ferramenta:** alterações de ficha ficam em memória durante a chamada. Só depois da resposta bem-sucedida, fichas, mensagens e rolagens são confirmadas na mesma transação. Erro posterior da IA descarta o lote; falha na gravação das mensagens desfaz também as alterações de ficha.
2. **Resposta atrasada:** confirmação usa snapshot e compare-and-swap das fichas alteradas. Uma edição concorrente causa HTTP 409, sem sobrescrever a edição nem salvar a resposta obsoleta. Não se mantém transação aberta durante a chamada ao provedor.
3. **Nível de característica:** `resolver_caracteristica` verifica o primeiro marco de desbloqueio registrado na matriz da classe, incluindo os aliases existentes do Artífice e ASI. Surto de Ação a nível 1 e Corpo e Mente a nível 1 agora retornam `bloqueado`.
4. **Autoridade da ficha:** na ferramenta `class_feature`, classe, nível, atributos e bônus de proficiência vêm da ficha identificada, não de valores inventados pelo modelo. Falta de ficha impede a operação.

**Reprodução após a correção:** duas falhas simuladas depois da ferramenta retornam 502, mantendo **2 espaços restantes nas duas tentativas**, e nenhuma mensagem salva. Uma tentativa posterior bem-sucedida consome o espaço e salva a troca.

**Validação:** 457 testes Python passaram, incluindo 12 novos testes em `tests/test_correcao_riscos_p0.py`: falha após uma/duas ferramentas, sucesso, conflito de ficha, rollback ao falhar INSERT de mensagens, snapshot obsoleto, reabertura do banco, níveis e autoridade de ficha. Três fixtures antigas passaram a informar o nível mínimo correto em vez de implicitamente usar nível 1.

**Limites que permanecem:** não há ainda identificador idempotente de operação para repetir um pedido cujo commit já ocorreu mas cuja resposta HTTP se perdeu. A guarda de característica cobre o resolvedor `class_feature`; rotas especializadas de outros tipos ainda precisam de revisão equivalente. A matriz de níveis não foi integralmente recertificada contra todas as fontes oficiais. Consumo/recuperação de todos os recursos de classe e vínculo persistido da seed a testes pendentes continuam no backlog.


## Atualização — repetição após commit implementada

A pendência do lote anterior foi tratada para mensagens de campanha com `operacao_id`: replay confirmado devolve a resposta/rolagens persistidas sem novo gasto, inclusive após reiniciar o repositório. O frontend guarda a chave entre tentativas e recargas. Duas confirmações simultâneas com a mesma chave são deduplicadas pela chave única no banco.

Detalhes, limites e testes em [IDEMPOTENCIA_MJ.md](IDEMPOTENCIA_MJ.md). Suíte atual: **470 testes Python e 9 testes JavaScript aprovados**. Não estender esta garantia ao endpoint legado, a clientes sem identificador nem às ações diretas do mapa.
