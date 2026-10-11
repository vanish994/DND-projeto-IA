# DND-projeto-IA

Biblioteca de referência do projeto de IA para Dungeons & Dragons.

## Livros incluídos

- Dungeon Master's Guide 2024
- Livro do Jogador 2024
- Eberron: Forge of the Artificer
- Ravenloft
- Dragon Delves

## Bestiário SRD 5.2.1

O catálogo original mantém **232 entradas** extraídas do `SRD_CC_v5.2.1.pdf`. Além dele, o motor agora importa **322 blocos estruturados** publicados para o SRD 5.2.1 em `rule_engine/srd_monsters_data.json`. Os registros incluem atributos, ações, descrições, traços, salvaguardas, deslocamentos, sentidos, perícias, resistências/imunidades e ações bônus, reações ou lendárias quando esses campos constam da fonte. Nomes legados do catálogo são preservados; aliases só compartilham dados quando existe uma correspondência explícita.

A origem e os termos de atribuição CC BY 4.0 estão registrados no próprio JSON. O conjunto importado tem mais entradas que o catálogo original; isso não significa que todas as 322 sejam nomes distintos presentes na extração local do PDF. Dados não publicados pela fonte, como alinhamento de algumas entradas adicionais, não são inventados.

O motor converte esses registros para o formato interno e os disponibiliza em `consultar_monstro`/`bloco_completo`. O ataque tático agora reconhece descrições de ataque no formato SRD 5.2.1 (`Melee Weapon Attack: +X to hit`) além do formato anterior. Multiataques com sequência explícita são executados como ataques separados; alternativas ambíguas são recusadas. Efeitos de ataque com salvaguarda reconhecida podem aplicar condições como Caído ou Envenenado ao token. O mapa guarda as condições, mas a duração e a remoção automática ainda dependem do controle de turnos, que não está implementado.

Também estão disponíveis a tabela de XP por ND, filtros por tipo/ND, consulta por nome e cálculo do XP bruto de um encontro. A regra do motor usa entradas como:

```python
{"type": "bestiary", "operacao": "consultar", "nome": "Aboleth"}
{"type": "bestiary", "operacao": "listar", "tipo": "beast", "nd": "0"}
{"type": "bestiary", "operacao": "xp_encontro", "nomes": ["Bandit", "Wolf"]}
```

Os ataques individuais extraídos dos blocos importados podem ser apresentados ao resolvedor tático quando bônus, alcance e dano estão explícitos. As salvaguardas estruturadas também alimentam as magias de área, e o traço **Undead Fortitude** do Zombie já tem resolução específica. **Limite atual:** importar um bloco completo não significa que todos os efeitos especiais, multiataques, agarrões, engolir, conjuração de monstros, resistências e reações já estejam simulados no mapa; esses efeitos ainda precisam de resolutores mecânicos próprios e testes.

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

### Campanhas persistidas

Campanhas e mensagens ficam salvas em banco. Sem configuração, o backend usa SQLite em `data/mj.sqlite3` (ignorado pelo Git). Em produção, defina `DATABASE_URL` com um Postgres (o formato `postgres://` do Render é aceito). O disco do plano gratuito do Render é efêmero: sem `DATABASE_URL`, o SQLite é apagado a cada deploy ou reinício.

Até existir login, cada navegador gera um identificador próprio e o envia no cabeçalho `X-Jogador-Id`; cada jogador só enxerga as próprias campanhas. Somente as últimas `MJ_HISTORICO_MAX` mensagens (padrão 40) são enviadas ao MJ como contexto; o histórico completo continua salvo.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/v1/campanhas` | Lista as campanhas do jogador, da mais recente para a mais antiga |
| `POST` | `/v1/campanhas` | Cria uma campanha (`{"titulo": "..."}` opcional) |
| `GET` | `/v1/campanhas/{id}` | Retorna a campanha com o histórico de mensagens |
| `PATCH` | `/v1/campanhas/{id}` | Renomeia (`{"titulo": "..."}`) |
| `DELETE` | `/v1/campanhas/{id}` | Apaga a campanha e as mensagens |
| `POST` | `/v1/campanhas/{id}/mensagens` | Envia uma mensagem ao MJ e salva a troca |
| `GET` | `/v1/catalogo/personagens` | Espécies, classes, antecedentes (PHB 2024 + Ravenloft), talentos de origem e Dádivas Sombrias |
| `GET` | `/v1/catalogo/equipamento` | Armas, armaduras, perícias por atributo e proficiências de arma do catálogo oficial |
| `GET` | `/v1/catalogo/magias` | Magias do catálogo, com classe e nível para filtrar |
| `GET` | `/v1/campanhas/{id}/personagens` | Lista as fichas do grupo da campanha |
| `POST` | `/v1/campanhas/{id}/personagens` | Cria uma ficha validada pelo Rule Engine (atributos, antecedente e aumentos) |
| `GET` | `/v1/campanhas/{id}/personagens/{pid}` | Retorna a ficha |
| `PUT` | `/v1/campanhas/{id}/personagens/{pid}` | Refaz a ficha, revalidando pelo motor |
| `PATCH` | `/v1/campanhas/{id}/personagens/{pid}` | Atualiza os PV atuais (`{"pv_atual": n}`, limitado ao máximo) |
| `DELETE` | `/v1/campanhas/{id}/personagens/{pid}` | Apaga a ficha |

### Bloco derivado da ficha

Toda resposta de personagem traz um campo `bloco` calculado pelo servidor (`fonte: rule_engine`): CA a partir da armadura e do escudo, iniciativa, bônus de proficiência, arma equipada (atributo usado, bônus de ataque, expressão de dano, tipo, alcance e proficiência), conjuração (atributo, CD e bônus de ataque mágico), salvaguardas e perícias com os totais já somados. Armas de munição usam Destreza; as demais usam Força, ou Destreza quando a arma tem Acuidade.

O objetivo é que a interface nunca precise recalcular regra nem manter listas próprias de equipamento: o catálogo oficial é servido por `/v1/catalogo/equipamento` e a ficha apenas exibe o que o motor devolve.

O endpoint legado `/v1/mj/mensagem` continua funcionando: a `sessao_id` passa a ser o id de uma campanha persistida. Autenticação própria ainda é necessária antes de abrir o serviço ao público; a chave do TokenHarbor nunca deve chegar ao navegador.

### Deploy no Render

O arquivo `render.yaml` deixa o repositório pronto para o Render Blueprint. No Render, use **New → Blueprint**, conecte o repositório `vanish994/DND-projeto-IA` e selecione a branch `main`. O Render lerá o `render.yaml`, instalará as dependências, iniciará o FastAPI na porta `$PORT` e usará `/v1/status` como health check. Quando o painel solicitar `TOKENHARBOR_API_KEY`, cole a chave diretamente no campo secreto do Render; ela não deve ser adicionada ao GitHub.

A extração local do PDF continua identificada como um catálogo de 232 entradas. O conjunto de 322 registros estruturados é uma fonte de dados separada, com sua própria atribuição CC BY 4.0, usada para completar a camada de dados do motor sem alegar que todas as entradas adicionais constam do PDF local.

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
