# Repetição segura de mensagens do MJ

Implementado em 12/10/2026 para `POST /v1/campanhas/{campanha_id}/mensagens`.

## Contrato

```json
{"mensagem": "Conjuro Curar Ferimentos.", "operacao_id": "identificador-unico-do-envio"}
```

- `operacao_id`: string de 1–64 caracteres conforme `PADRAO_ID`; o frontend usa UUID.
- Mesmo identificador, campanha, jogador e texto: devolve resposta e rolagens originais.
- Identificador já confirmado com outro texto: HTTP 409; nenhuma nova chamada ao provedor.
- Texto igual com identificador novo: nova ação legítima, não uma repetição.
- A campanha pertence ao jogador: conhecer a chave não permite consultar a resposta de outro jogador.
- Campo opcional para clientes antigos. **Sem identificador não há deduplicação de replay.** O endpoint legado de sessões e os endpoints diretos de combate não ganharam essa garantia neste lote.

## Banco e confirmação

A tabela `operacoes_mj` é criada automaticamente pelo `metadata.create_all` ao inicializar o repositório, inclusive em bancos existentes. Não altera dados das campanhas existentes. Sua chave primária composta é `(campanha_id, operacao_id)`.

O registro da operação, a resposta, as rolagens, as alterações de ficha e as duas mensagens são confirmados **na mesma transação**. Uma falha anterior ao commit não deixa chave registrada nem gasto de espaço. O identificador pode ser usado novamente nessa situação.

Replays já confirmados são consultados antes de chamar o MJ. Para duas requisições simultâneas que chegaram antes da confirmação, a restrição única decide o vencedor: a transação perdedora é revertida e recebe o resultado persistido pelo vencedor. Essa proteção evita dupla gravação e duplo gasto. Ela não evita necessariamente duas chamadas ao provedor quando ambas começaram antes do commit.

A comparação de snapshot de ficha da correção anterior continua ativa para operações diferentes concorrentes. Um conflito não confirma a operação descartada.

A garantia depende da durabilidade do próprio banco. SQLite efêmero em deploy continua sujeito à perda de dados; usar banco persistente em produção.

## Frontend

`frontend/envios-pendentes.js` guarda identificador e texto em localStorage antes do POST. O registro permanece em caso de timeout/erro e é recuperado ao recarregar a página. Reenviar o texto pendente sem edição conserva a chave; editar cria uma nova operação. Após confirmação, enviar novamente o mesmo texto cria uma ação nova.

O erro deixou de afirmar que “a mensagem não foi salva”: sem resposta HTTP, o navegador não sabe se houve commit. Agora orienta a repetir sem edição para recuperar o resultado. Em replay, o histórico é recarregado para não duplicar bolhas já presentes na tela. O envio permanece bloqueado enquanto termina esse fluxo.

Limites: apagar dados do navegador ou usar outro cliente sem a chave perde o vínculo de repetição. A deduplicação é por identificador, não por comparação heurística de mensagens iguais. Em caso de disputa ainda em andamento, a IA pode ser chamada mais de uma vez, embora apenas um resultado mecânico seja confirmado.

## Testes executados

- 13 testes novos em `tests/test_idempotencia_mj.py`: replay após perda de resposta; mesmas rolagens; nenhuma segunda chamada de IA no replay confirmado; falha antes de commit; conflito de texto; operação nova; isolamento por campanha/jogador; compatibilidade antiga; validação de ID; rollback de ficha e chave; exclusão; reabertura; tabela em banco existente; duas confirmações simultâneas em SQLite de arquivo.
- 5 testes novos em `tests/test_envios_pendentes.cjs`: chave após recarga, confirmação, edição/campanha, erro de armazenamento e dados inválidos.
- Suíte completa: **470 testes Python e 9 testes JavaScript aprovados**.
- Não houve teste em Postgres remoto nem chamada a provedor real; os testes de falha e resposta perdida usam dublês locais.
