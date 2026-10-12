# Auditoria geral — outubro de 2026

Escopo: testes, qualidade estática do Python e do JavaScript, tokens e CSS, interface no celular (390 px), acessibilidade automatizada básica, segurança e configuração.

## Resultado resumido

- **Testes:** 422 testes Python e 2 suítes Node passam.
- **Sintaxe JavaScript:** todos os arquivos em `frontend/` e `tests/*.cjs` são válidos.
- **IDs:** todo ID referenciado pelo JavaScript existe no HTML.
- **Tokens CSS:** nenhum `var(--token)` indefinido restante (`--app-height` é definido pelo JavaScript em tempo de execução).
- **Alvos de toque no celular:** nenhum botão, campo ou escolha menor que 44 px nas telas medidas (início, conversa, ajuda, opções, grupo e criação de personagem).
- **Erros de página no console:** nenhum nas telas percorridas.

## Corrigido nesta auditoria

| Severidade | Achado | Correção |
|---|---|---|
| Média | `backend/app.py` usava `Any` sem importar. Funcionava só por causa de `from __future__ import annotations`. | Import explícito de `typing.Any`. |
| Baixa | Variável `conhecida` atribuída e nunca usada em `rule_engine/character.py`. | Removida. A validação de subclasse não mudou. |
| Baixa | F-string sem campos em `rule_engine/spellcasters.py`. | Convertida em string comum. |
| Baixa | Cor `#f7d3a6` escrita diretamente em `styles.css`, contra a regra do guia de design. | Virou token `--color-accent-glow` em `design-tokens.css`. |
| Média (já anterior) | Estado do mapa tático e o token `--space-5` ausente. | Corrigidos nas rodadas anteriores. |

## Riscos que dependem de decisão

1. **Identidade do jogador sem autenticação (alta).** O backend lê `X-Jogador-Id`, um cabeçalho enviado pelo próprio navegador. Quem souber o ID de uma campanha e puder enviar o cabeçalho acessa o histórico. Requisições sem o cabeçalho caem no grupo compartilhado `anonimo`. Os IDs de campanha são aleatórios (12 caracteres hexadecimais), o que limita o risco na prática, mas não há controle de acesso real. Corrigir exige contas ou tokens de sessão, o que o próprio guia descarta por enquanto.
2. **Limite de taxa nos endpoints do MJ (resolvido).** `POST /v1/campanhas/{id}/mensagens` e `/v1/mj/mensagem` têm janela deslizante por jogador (`X-Jogador-Id`): 30 mensagens por 60 s, configurável por `MJ_LIMITE_REQUISICOES` e `MJ_LIMITE_JANELA_SEGUNDOS`. Excedido, responde 429 com `Retry-After`. Limitações: o contador vive na memória de cada processo (com mais de um processo, o limite é por processo), e requisições sem cabeçalho compartilham o grupo `anonimo`. Um limite por IP no proxy continua recomendado.
3. **Chave de API:** nenhuma chave real está no repositório. `.env.example` documenta `TOKENHARBOR_*` e `DEEPSEEK_*`, mas o código aceita também `LLM_*` (usado no `render.yaml`). Funciona, mas vale unificar a documentação.
4. **`docs/CRIADOR_MAPAS_TATICOS.md`:** plano de um criador de mapas em Android, separado do projeto web. Mantido até você decidir.
5. **`docs/matriz_cobertura.csv`:** a regeneração pelo script muda dados não relacionados (níveis de subclasse do artífice). Precisa de revisão antes de ser atualizada.

## Pendências técnicas menores

- 14 imports não utilizados em `backend/` e `rule_engine/` (principalmente em `rules.py` e `app.py`). São inofensivos, mas poluem a leitura.
- Módulos `combat_special.py`, `combat_geometry.py` e `combat_movement.py` seguem no motor (regras gerais de combate, não só do mapa).
- A página inicial não tem testes automatizados de interface. As verificações de tela foram feitas manualmente com Chromium headless.

## Como foi feita a verificação

- `pytest` na suíte completa; `node` nas suítes `.cjs`.
- `pyflakes` em `backend`, `integrations`, `rule_engine` e `scripts`.
- Análise estática de IDs e de `var(--...)` em JavaScript e CSS.
- Capturas de tela em 390×844 com `isMobile` e `deviceScaleFactor` 2, com medição de alvos de toque no DOM.
- Não foi testado em aparelho real nem com leitor de tela.
