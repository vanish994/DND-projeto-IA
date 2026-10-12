# Changelog

Alterações estruturais e de contrato do projeto. Mudanças de regra do jogo
ficam documentadas no `README.md` e nos testes.

## 2026-10 — Refactor P0 do backend (PR #14)

Issues: #11 (split-backend), #12 (remove-globals-di), #13 (move-business-logic), #15 (QA).

### Estrutura

- `backend/app.py` deixou de ser monolítico (1.222 → ~50 linhas): virou o
  composition root, com rotas em `backend/routes/` e casos de uso em
  `backend/services/`.
- Modelos Pydantic em `backend/schemas.py`; providers de injeção em
  `backend/dependencies.py`; constantes de processo em `backend/config.py`.
- Exceções de domínio em `backend/erros.py`, com mapeamento HTTP em um único
  handler (formato `{"detail": ...}` preservado).

### Contrato público

- **Nenhuma quebra de contrato HTTP**: status codes, formatos de resposta e
  mensagens de erro idênticos aos anteriores ao refactor.
- `backend.app` reexporta os providers de injeção (`obter_mj`,
  `obter_repositorio`, `obter_jogador`, `limitar_chamadas_mj`) — é a
  superfície usada por testes em `dependency_overrides`. Reexportar é
  compatibilidade temporária (TECHDEBT): código novo deve importar de
  `backend.dependencies`.
- Símbolos internos mudaram de módulo (`_responder` → `mj_service.responder`,
  `_resumo_grupo` → `campanha_service.resumo_grupo`, `_com_bloco` →
  `bloco_ficha.com_bloco`, etc.).
- `_mj` e `_repositorio` não existem mais como globais de módulo; os recursos
  vivem em `app.state.recursos` (container `Recursos`).

### Qualidade

- black + isort + ruff configurados no `pyproject.toml` (`requirements-dev.txt`).
- CI (`.github/workflows/tests.yml`): job de lint + suíte com piso de cobertura
  (`--cov-fail-under=80`) + testes JS.
- Novos testes: DI (`tests/test_dependencias_di.py`), mapeamento de erros
  (`tests/test_erros_dominio.py`), concorrência do compare-and-set
  (`tests/test_concorrencia_campanha.py`) e contrato das condições
  (`tests/test_condicoes_service.py`).
