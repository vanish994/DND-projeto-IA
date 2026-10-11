
### Testes de habilidade com rolagem do motor

Nos testes de habilidade, o MJ define a CD conforme a situação, mas não fornece nem inventa o d20. O Rule Engine gera a rolagem e devolve `roll`, `modifier`, `total`, `seed` e `roll_source=rule_engine`. Se a CD ainda não estiver presente, o resultado será `result=requires_dc` com `reason=cd_do_mj_ausente`. Depois que o MJ decidir a CD, a mesma `seed` reproduz o d20 e o motor compara o total com a CD.

Exemplo:

```python
pendente = engine.evaluate({
    "type": "ability_check",
    "ability": "carisma",
    "skill": "persuasao",
    "modifier": 5,
})

final = engine.evaluate({
    "type": "ability_check",
    "ability": "carisma",
    "skill": "persuasao",
    "modifier": 5,
    "dc": 15,
    "seed": pendente.outcome["seed"],
})
```
