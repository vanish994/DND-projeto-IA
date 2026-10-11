# Rule Engine

Primeiro componente do **DND-projeto-IA**. O motor recebe fatos estruturados, encontra a regra aplicável de maior prioridade e devolve uma decisão determinística com trilha de auditoria.

## Fluxo

1. A IA transforma a situação narrada em fatos estruturados.
2. O motor avalia as regras, sem inventar uma regra nova durante a resolução.
3. O resultado retorna `status`, `outcome`, regras aplicadas e `trace`.
4. `to_ai_instruction()` produz uma instrução curta para a IA continuar a resposta sem contradizer a decisão.

## Exemplo

```python
from rule_engine import build_default_engine

engine = build_default_engine()
result = engine.evaluate({
    "type": "ability_check",
    "roll": 14,
    "modifier": 2,
    "dc": 15,
})

print(result.outcome)
print(result.to_ai_instruction())
```

## Próximas extensões

- regras de ataque, dano, salvaguardas, condições e descanso;
- separação por edição (`2024`) e configuração da mesa;
- carregamento de regras em JSON/YAML com versionamento e fonte;
- camada de interpretação narrativa para converter texto em fatos;
- testes de regressão para cada regra extraída dos livros.
