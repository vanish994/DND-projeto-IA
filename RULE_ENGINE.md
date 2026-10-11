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

## Fatos suportados

- `ability_check`: `roll`, `modifier`, `dc`;
- `attack`: `roll`, `modifier`, `target_ac`;
- `damage`: `damage_dice` (resultados individuais), `damage_modifier` e `critical`;
- `saving_throw`: `roll`, `modifier`, `dc`.
- `spell_cast`: `spell_level`, `slot_level`, `has_slot`, `concentration_required` e `concentrating`;
- `condition`: `operation` (`apply` ou `remove`), `condition`, `active_conditions` e `immunities`;
- `condition_effect`: `action`, `attacker_conditions` e `target_conditions`.

Acertos críticos duplicam os dados de dano e adicionam o modificador uma única vez. Cada resolução informa a regra e a fonte usada, permitindo que a camada de IA explique a decisão.

Magias sem espaço disponível ou com espaço de nível insuficiente são bloqueadas. Uma nova magia de concentração encerra a concentração anterior. Condições respeitam imunidades, aplicação, remoção e o cancelamento entre vantagem e desvantagem.

## Próximas extensões

- regras de condições, resistência, vulnerabilidade e descanso;
- separação por edição (`2024`) e configuração da mesa;
- carregamento de regras em JSON/YAML com versionamento e fonte;
- camada de interpretação narrativa para converter texto em fatos;
- testes de regressão para cada regra extraída dos livros.
