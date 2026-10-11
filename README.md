# DND-projeto-IA

Biblioteca de referência do projeto de IA para Dungeons & Dragons.

## Livros incluídos

- Dungeon Master's Guide 2024
- Livro do Jogador 2024
- Eberron: Forge of the Artificer
- Ravenloft
- Dragon Delves

## Bestiário SRD 5.2.1

O projeto agora inclui um catálogo determinístico com **232 blocos estatísticos completos** identificados no `SRD_CC_v5.2.1.pdf` compartilhado. Cada registro contém nome, tamanho, tipo, alinhamento, CA, PV, dados de vida, ND e XP.

Também estão disponíveis a tabela de XP por ND, filtros por tipo/ND, consulta por nome e cálculo do XP bruto de um encontro. A regra do motor usa entradas como:

```python
{"type": "bestiary", "operacao": "consultar", "nome": "Aboleth"}
{"type": "bestiary", "operacao": "listar", "tipo": "beast", "nd": "0"}
{"type": "bestiary", "operacao": "xp_encontro", "nomes": ["Bandit", "Wolf"]}
```

O bestiário também preserva o bloco integral de cada monstro, com cabeçalho, traços, ações, ações bônus, reações e ações lendárias quando existirem. As operações `bloco_completo` e `secao` permitem consultar esses dados de forma auditável.

### Fluxo de seleção para o MJ

O MJ é um bloco separado do motor. Ele envia apenas os critérios do momento da campanha, e o motor retorna uma lista de candidatos oficiais para escolha. O motor não escolhe o monstro, não cria variantes e não inventa uma entrada ausente:

```python
{
    "type": "bestiary",
    "operacao": "sugerir",
    "tipos": ["beast"],
    "nd_min": "1/4",
    "nd_max": "1",
    "limite": 5
}
```

O resultado contém apenas resumos dos candidatos, a origem `SRD 5.2.1` e `escolha: "MJ"`. Depois que o MJ escolhe um nome, o bloco pode ser recuperado com `bloco_completo`. Critérios não presentes no catálogo, como ambiente narrativo, não são inferidos silenciosamente: devem ser convertidos pelo bloco do MJ em filtros explícitos de tipo, tamanho, alinhamento ou ND.

### Limite de responsabilidade do motor

O motor é **somente normativo**. Ele confere a existência do monstro, os dados oficiais, as ações e as consequências mecânicas. O MJ mantém liberdade total para criar história, lugares, conflitos, personagens, diálogos, mistérios, objetivos, cenas e interpretações próprias. O motor não narra, não cria uma história pré-fabricada, não escolhe o rumo da campanha e não avalia a qualidade da ideia do MJ.

Isso também vale para a condução de encontros: o MJ pode decidir a dificuldade desejada, a quantidade de criaturas, a composição do grupo e o ritmo da cena. O motor não escolhe por ele; quando houver um cálculo mecânico oficial disponível, o motor apenas calcula ou valida o resultado. Uma recomendação de condução do MJ pode existir mesmo quando ainda não houver uma ferramenta específica para aquele cálculo, desde que não seja apresentada como regra oficial calculada pelo motor.

A restrição se aplica somente ao conteúdo mecânico apresentado como regra de D&D: o MJ não pode inventar um monstro, uma magia, uma condição, um item, uma habilidade, uma estatística ou uma regra e tratá-los como oficiais. Para isso, o conteúdo deve existir no catálogo ou nas regras implementadas. A operação `validar_uso` bloqueia alterações silenciosas em dados oficiais como CA, PV, ND, tipo ou bloco de regras; decisões narrativas continuam fora do motor.

## DeepSeek como MJ

O adaptador `integrations/deepseek_mj.py` transforma a API do DeepSeek no MJ conversacional. Ele mantém a conversa, conduz a narração e apresenta os resultados. Quando precisa de mecânica, chama as ferramentas `sugerir_monstros`, `consultar_monstro` ou `resolver_regra`; essas ferramentas executam o Rule Engine e devolvem a resolução oficial. O DeepSeek não recebe permissão para alterar CA, PV, ND, XP, ações ou efeitos.

Configuração mínima:

```bash
export DEEPSEEK_API_KEY="sua-chave"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-flash"
```

Para usar o modelo indicado no TokenHarbor:

```bash
export TOKENHARBOR_API_KEY="sua-chave-do-tokenharbor"
export TOKENHARBOR_BASE_URL="https://tokenharbor.ai/v1"
export DEEPSEEK_MODEL="deepseek-v4.1-flash:free"
```

Quando `TOKENHARBOR_API_KEY` estiver definida, o adaptador seleciona automaticamente `https://tokenharbor.ai/v1` e `deepseek-v4.1-flash:free`. A chave deve ser criada na conta do TokenHarbor e nunca deve ser publicada no repositório.

### Prompt e personalidade do MJ

A personalidade editável fica em `config/mj_personalidade.txt`. Para alterá-la no deploy do Render, edite esse arquivo no GitHub, faça commit na branch `main` e o Render fará o redeploy automático. O adaptador sempre acrescenta o contrato normativo protegido: narrativa livre, mas toda mecânica de D&D passa pelo Rule Engine.

Para uma configuração exclusiva do ambiente Render, use a variável `MJ_PERSONALIDADE` no painel do serviço. Ela substitui o conteúdo do arquivo sem alterar o GitHub. Para trocar o caminho do arquivo, use `MJ_PROMPT_FILE`.

Uso:

```python
from integrations.deepseek_mj import DeepSeekMJ

mestre = DeepSeekMJ()
resposta = mestre.responder("Quero opções oficiais de monstros para o próximo encontro.")
print(resposta)
```

Também existe o inicializador interativo `run_mj.py`. Basta colar a chave em `.env` na variável `TOKENHARBOR_API_KEY` e executar:

```bash
python3 run_mj.py
```

O `.env` é carregado automaticamente, está excluído pelo `.gitignore` e não é publicado no GitHub.

### Backend recomendado

Para uso real, o cliente não deve falar diretamente com o TokenHarbor. O backend FastAPI mantém `TOKENHARBOR_API_KEY` no servidor, recebe mensagens do MJ e expõe o Rule Engine por trás do adaptador DeepSeek. O `run_mj.py` continua útil apenas para testes locais no terminal.

Instalação e execução:

```bash
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Endpoint da sessão:

```bash
curl -X POST http://localhost:8000/v1/mj/mensagem \
  -H 'Content-Type: application/json' \
  -d '{"sessao_id":"campanha-1","mensagem":"Os aventureiros entram nas ruínas."}'
```

O backend atual mantém sessões em memória para desenvolvimento. Para produção, a sessão deve ser transferida para Redis ou banco de dados e o endpoint deve receber autenticação própria; a chave do TokenHarbor nunca deve chegar ao navegador.

### Deploy no Render

O arquivo `render.yaml` deixa o repositório pronto para o Render Blueprint. No Render, use **New → Blueprint**, conecte o repositório `vanish994/DND-projeto-IA` e selecione a branch `main`. O Render lerá o `render.yaml`, instalará as dependências, iniciará o FastAPI na porta `$PORT` e usará `/v1/status` como health check. Quando o painel solicitar `TOKENHARBOR_API_KEY`, cole a chave diretamente no campo secreto do Render; ela não deve ser adicionada ao GitHub.

A estimativa de “mais de 300 monstros” não corresponde ao PDF SRD 5.2.1 presente na biblioteca ativa: a extração verificável dessa fonte resulta em 232 blocos completos. O catálogo não inventa entradas para preencher essa diferença.

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
