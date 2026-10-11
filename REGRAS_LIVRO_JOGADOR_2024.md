# Cobertura do Livro do Jogador 2024

Este documento é o inventário de implementação do **Rule Engine**. Os livros continuam no repositório apenas como referência; nenhuma regra é considerada concluída sem código e testes.

## Situação geral

O motor está **funcional, mas incompleto**. A suíte atual possui **36 testes aprovados**.

## Bloco 1 — núcleo de sobrevivência

O núcleo de sobrevivência foi implementado: Estado Vital, Pontos de Vida, Pontos de Vida Temporários, cura, tipos e origem de dano, Resistência, Vulnerabilidade, Imunidade, dano em 0 PV, inconsciência, estabilidade, Salvaguardas contra a Morte, estabilização, Exaustão, Dados de Vida e descansos com duração, interrupção, intervalo e recursos recuperáveis declarados.

O **Bloco 1 está encerrado no nível do núcleo**. A recuperação de uma característica específica de classe só será aplicada quando o módulo de classes fornecer seu contrato de recursos; o descanso já retorna os recursos declarados para essa integração futura.

## O que já está implementado

- Modificador de atributo para valores de 1 a 30.
- Bônus de Proficiência por nível/ND.
- Rolagem de d20 com Vantagem, Desvantagem e cancelamento entre ambas.
- Testes básicos de atributo.
- Jogadas de ataque básicas, 20 natural e 1 natural.
- Dano normal e dano crítico.
- Salvaguardas básicas.
- Conjuração básica por espaço de magia e nível do espaço.
- Concentração básica e substituição da concentração anterior.
- Aplicação, remoção e imunidade de condições em nível básico.
- Ordenação de iniciativa e desempate.
- Rodadas e turnos.
- Uma ação, uma ação bônus e uma reação por turno.
- Movimento, Correr e terreno difícil.
- Ações Ajudar, Atacar, Analisar, Desengajar, Esconder, Esquivar, Influenciar, Preparar, Procurar, Usar Magia e Usar Objeto em nível estrutural.
- Ataques de oportunidade.
- Agarrar, escape do agarramento e condição Imobilizado.
- Empurrar, empurrão de 1,5 metro e efeito Caído.

## Regras que ainda faltam

### 1. Fundamentos e testes

- Pipeline completo de Teste de D20 usando automaticamente atributo, perícia, proficiência e modificadores circunstanciais.
- As 18 perícias com seus atributos padrão.
- Perícia usando atributo alternativo autorizado pelo Mestre.
- CDs padrão 5, 10, 15, 20, 25 e 30.
- Não acumulação do Bônus de Proficiência.
- Multiplicação e divisão do Bônus de Proficiência no máximo uma vez.
- Testes passivos.
- Testes resistidos.
- Testes em grupo.
- Regra para decidir quando não pedir um teste.
- Proficiência em salvaguardas integrada ao cálculo.
- Proficiência em ferramentas.
- Vantagem por proficiência simultânea em ferramenta e perícia.
- Rerrolagem/substituição de um único dado sob Vantagem ou Desvantagem.
- Inspiração Heroica.
- Interação social estruturada com atitude, objetivo, medo, desejo, simpatia e reação de NPC.

### 2. Combate e ações

- Iniciativa com modificador de Destreza integrado.
- Surpresa conforme percepção e estado Incapacitado.
- Grid, quadrados, diagonais, cantos e distância.
- Tamanho e espaço ocupado por criaturas.
- Alcance normal e máximo.
- Ataques à distância além do alcance normal.
- Inimigo adjacente impondo Desvantagem em ataque à distância.
- Alvo invisível e atacante invisível.
- Linha de visão e linha de efeito.
- Cobertura parcial, três quartos e total.
- Cobertura não cumulativa.
- Movimento dividido antes/depois da ação.
- Escalar, nadar, rastejar e saltar.
- Atravessar espaço de outra criatura.
- Levantar-se da condição Caído.
- Movimento com Deslocamento 0.
- Reação que interrompe outro turno e continuidade do turno.
- Ação bônus concedida por característica ou magia.
- Reação concedida por gatilho.
- Ataque de oportunidade considerando alcance, invisibilidade e alvo válido.
- Agarrar com mão livre, arrasto, distância e encerramento por incapacitação do imobilizador.
- Escape do agarramento por Atletismo ou Acrobacia com estado persistente.
- Ataque Desarmado com dano, Empurrar ou Agarrar como opções distintas.
- Combate montado: montar, desmontar, montaria controlada e independente.
- Queda do cavaleiro e salvaguarda de Destreza CD 10.
- Combate subaquático.
- Ataques com duas armas.
- Ataques múltiplos e divisão de movimento entre ataques.
- Objetos usados durante o combate.

### 3. Vida, dano e descanso

- Pontos de Vida atuais e máximos.
- Pontos de Vida Temporários.
- Cura limitada aos Pontos de Vida máximos.
- Cura que remove inconsciência.
- Tipos de dano.
- Resistência.
- Vulnerabilidade.
- Imunidade a dano.
- Ordem entre ajustes, Resistência e Vulnerabilidade.
- Dano com Pontos de Vida iguais a zero.
- Morte instantânea.
- Inconsciência.
- Estado Estável.
- Salvaguardas contra a Morte.
- 1 natural e 20 natural em Salvaguardas contra a Morte.
- Dano crítico contra criatura com 0 Pontos de Vida.
- Estabilização por Medicina CD 10.
- Recuperação após 1d4 horas estável.
- Exaustão por níveis.
- Penalidade de Exaustão em Testes de D20.
- Redução de Deslocamento por Exaustão.
- Morte no nível 6 de Exaustão.
- Descanso Curto.
- Gasto de Dados de Vida.
- Recuperação de recursos em Descanso Curto.
- Interrupção de Descanso Curto.
- Descanso Longo.
- Recuperação completa no Descanso Longo.
- Intervalo de 16 horas entre Descansos Longos.
- Interrupções e reinício do Descanso Longo.
- Recuperação de características por tipo de descanso.

### 4. Condições e efeitos

O motor atual apenas aplica/remove condições e resolve alguns efeitos de vantagem/desvantagem. Ainda faltam os efeitos completos de:

- Amedrontado.
- Atordoado.
- Caído.
- Cego.
- Contido.
- Enfeitiçado.
- Envenenado.
- Exaustão.
- Imobilizado.
- Incapacitado.
- Inconsciente.
- Invisível.
- Paralisado.
- Petrificado.
- Surdo.

Também faltam:

- Condições derivadas, como Incapacitado causado por Atordoado, Paralisado ou Inconsciente.
- Falha automática em salvaguardas de Força e Destreza.
- Crítico automático contra alvos Paralisados ou Inconscientes a curta distância.
- Deslocamento 0 e impossibilidade de aumento.
- Efeitos sensoriais de Cego, Surdo e Invisível.
- Efeitos sociais de Enfeitiçado.
- Linha de visão para Amedrontado.
- Encerramento de Concentração por Incapacitado.
- Não acumulação de condições iguais com durações independentes.
- Recuperação contextual de Caído e Inconsciente.

### 5. Magias e conjuração

O motor atual cobre somente espaço de magia e concentração básica. Ainda faltam:

- Magias preparadas por classe.
- Magias sempre preparadas.
- Alteração da lista preparada por classe.
- Truques sem gasto de espaço.
- Conjuração em espaço de nível superior.
- Limite de uma magia com espaço por turno.
- Magias rituais.
- Tempo adicional de 10 minutos para Ritual.
- Componentes Verbais, Somáticos e Materiais.
- Mãos livres.
- Bolsa de Componentes.
- Foco de Conjuração.
- Custos e consumo de componentes materiais.
- Treinamento em armadura para conjurar.
- Tempo de conjuração de Ação, Ação Bônus e Reação.
- Conjuração com duração de 1 minuto ou mais.
- Falha de conjuração longa e reinício.
- Alcance Pessoal, Toque e distância em metros.
- Linha de efeito e Cobertura Total.
- Áreas de efeito: Cilindro, Cone, Cubo, Emanação, Esfera e Linha.
- Validação de alvo e alvo inválido.
- Duração Instantânea, intervalo e Concentração.
- Encerramento voluntário.
- CD de salvaguarda de magia.
- Modificador de ataque mágico.
- Metade do dano em sucesso quando a magia determinar.
- Combinação e precedência de efeitos mágicos.
- Identificação de magia por Analisar e Arcanismo CD 15.
- Catálogo estruturado das magias do Livro do Jogador 2024.

### 6. Equipamento, armas e fabricação

- Catálogo completo de armas.
- Proficiência com armas.
- Propriedades Acuidade, Alcance, Arremesso, Duas Mãos, Extensão, Leve, Munição, Pesada, Recarga e Versátil.
- Maestrias Afligir, Ágil, Derrubar, Drenar, Empurrar, Garantido, Lentidão e Trespassar.
- Ataque adicional de armas Leves.
- Munição, recuperação e mão livre.
- Armaduras Leves, Médias e Pesadas.
- Limite de Destreza em armadura Média.
- Força mínima de armadura Pesada.
- Redução de Deslocamento por armadura.
- Desvantagem em Furtividade.
- Falta de treinamento em armadura.
- Armadura bloqueando conjuração sem treinamento.
- Escudo e limite de um escudo.
- Tempo para vestir e despir armaduras.
- Ferramentas e CDs de Usar Objeto.
- Ferramenta + perícia concedendo Vantagem.
- Inventário, peso e Capacidade de Carga.
- Moedas e conversão monetária.
- Contêineres, munição e objetos consumíveis.
- Montarias, selas e apetrechos.
- Veículos, tripulação, passageiros, carga e reparos.
- Estilo de vida, hospedagem, comida e serviços.
- Fabricação não mágica.
- Poção de Cura.
- Pergaminho Mágico.
- Ajudantes e divisão do tempo de fabricação.

### 7. Criação e progressão de personagens

- Matriz padrão de atributos.
- Compra por pontos.
- Rolagem de 4d6 descartando o menor.
- Criação de personagem completa.
- As dez espécies e seus traços.
- Tipo, tamanho e Deslocamento de cada espécie.
- Antecedentes.
- Aumentos de atributo de origem.
- Talento de Origem.
- Perícias, ferramentas e equipamentos de origem.
- As 12 classes.
- Dados de Vida por classe.
- Proficiências por classe.
- Equipamento inicial.
- Progressão de níveis 1 a 20.
- Características de classe.
- Subclasses.
- Ataque Extra e não acumulação entre classes.
- Aumento no Valor de Atributo.
- Talentos Gerais.
- Estilos de Luta.
- Dádivas Épicas.
- Pré-requisitos de talentos.
- Limite de atributo 20.
- Multiclasse.
- Pré-requisito 13 para multiclasse.
- Proficiências concedidas pela segunda classe.
- Níveis individuais e nível total.
- Dados de Vida em multiclasse.
- Conjuração em multiclasse.
- Pacto Mágico em multiclasse.
- Migração de antecedentes e espécies legadas.
- Persistência e não duplicação das escolhas.

### 8. Exploração, ambiente e interação social

- Ritmos de viagem Rápido, Normal e Lento.
- Distância por minuto, hora e dia.
- Penalidades e benefícios de cada ritmo.
- Necessidade de descanso após ritmo Rápido.
- Percepção passiva.
- Ação Procurar com Percepção ou Investigação.
- Ocultar com Furtividade CD 15.
- Gatilhos de revelação da condição Invisível.
- Luz Plena, Escuridão e obscurecimento.
- Visão no Escuro.
- Visão às Cegas.
- Escalada, natação, rastejamento e salto fora do combate.
- Interação gratuita com objetos.
- Segunda interação exigindo Usar Objeto.
- Objetos frágeis e resistentes.
- CA, Pontos de Vida, imunidades e Limiar de Dano de objetos.
- Capacidade de Carga.
- Queda e dano de queda.
- Asfixia.
- Combustão.
- Desidratação.
- Desnutrição.
- Riscos ambientais e Exaustão.
- Influência, Persuasão, Intimidação, Enganação e Intuição.
- Atitudes Amigável, Indiferente e Hostil.
- Consequências narrativas de NPC sem automatizar decisões.
- Ordem de resolução de efeitos simultâneos.
- Glossário normativo da edição 2024.

## Próxima prioridade

A ordem recomendada permanece:

1. Pontos de Vida, dano, morte e descanso.
2. Condições completas e efeitos derivados.
3. Alcance, cobertura, sentidos e alvos em combate.
4. Componentes, preparação e áreas de efeito de magias.
5. Equipamento, armas, armaduras e maestria.
6. Criação e progressão de personagens.
7. Exploração, riscos ambientais e interação social.
8. Catálogo detalhado das magias e características de classe.

A lista acima é a referência atual para determinar quando o Rule Engine estará realmente completo.
