# Plano de Implantação Real dos Squads v1

## Objetivo
Levar a Estruturação Versus Gestão Corporativa da fase de base técnica publicada para a fase de **rollout assistido controlado**, com uso humano real, aprendizado operacional e critério claro para expansão.

## Premissa
Nesta etapa, o objetivo não é abrir geral para toda a base. O objetivo é implantar com controle, medir fricção, consolidar rotina e só então ampliar.

## Status de partida
Em 10/05/2026, já estão prontos:
- arquitetura formal
- perfis publicados: `sapiens_default`, `squad_versus`, `squad_cliente`
- superfície MCP protegida
- uso assistido e maturidade assistida como contrato inicial
- telemetria mínima de governança por runtime, papel e surface

## Resultado esperado desta implantação
Ao final desta fase, a Versus deve conseguir provar em operação real que:
1. o consultor da Versus usa o Squad Versus com governança adequada
2. o usuário do cliente usa o Squad Cliente com menor privilégio e condução assistida
3. o APP32 funciona como hub operacional entre humanos, squads e evidências
4. existe um fluxo operacional assistido real validado ponta a ponta
5. existe backlog consolidado para rollout ampliado

## Estratégia de implantação
### Fase 1 — Preparação do piloto
Objetivo: selecionar o recorte e montar a operação mínima controlada.

#### Entregas
- cliente piloto definido
- consultor piloto definido
- fluxo piloto definido
- critérios de sucesso do piloto definidos
- responsáveis definidos

#### Recomendação de recorte
- 1 cliente
- 1 consultor Versus
- 1 ou 2 usuários do cliente
- 1 fluxo operacional real

#### Fluxos recomendados para começar
- rotina operacional
- acompanhamento de tarefas
- cobrança/follow-up
- leitura assistida de execução

#### Não começar por
- financeiro sensível amplo
- múltiplos times em paralelo
- rollout multiempresa
- uso totalmente autônomo sem assistência

## Fase 2 — Preparação de acesso e contexto
Objetivo: garantir que o piloto entre com identidade, permissões e material de uso corretos.

#### Entregas
- tokens/contextos MCP configurados
- perfil do consultor no Squad Versus validado
- perfil do usuário no Squad Cliente validado
- surfaces corretas validadas
- snippets de conexão revisados
- trilha de auditoria validada antes da operação

#### Critério de saída
- consultor consegue acessar o runtime do Squad Versus
- usuário do cliente consegue acessar o runtime do Squad Cliente
- APP32 registra contexto mínimo por ator/runtime

## Fase 3 — Onboarding assistido
Objetivo: formar comportamento correto de uso antes de medir desempenho pleno.

#### Entregas
- onboarding do consultor Versus
- onboarding do usuário cliente
- apresentação do Sapiens como front door
- explicação do modo assistido
- explicação do que cada squad faz e não faz

#### Critério de saída
- consultor sabe iniciar pelo discovery
- cliente sabe operar no modo assistido sem tentar contornar guardrails
- ambos entendem o papel do APP32 e do MCP

## Fase 4 — Execução do piloto assistido
Objetivo: operar o fluxo real com suporte e coleta de fricção.

#### Entregas
- execução real do fluxo escolhido
- registro de dificuldades
- registro de dúvidas recorrentes
- evidência de uso dos perfis externos
- observação de pontos de atrito no APP32, no squad e na condução humana

#### O que observar
- clareza de entrada
- qualidade da resposta do squad
- necessidade de condução humana
- erros de escopo/surface/tenant
- excesso ou falta de assistência

## Fase 5 — Consolidação e prontidão para expansão
Objetivo: transformar o piloto em decisão executiva.

#### Entregas
- análise do piloto
- backlog pós-piloto consolidado
- ajustes obrigatórios identificados
- critérios de expansão definidos
- decisão entre:
  - expandir
  - manter controlado
  - corrigir antes de ampliar

## Papéis e responsabilidades
### Consultor Versus
- usar o Squad Versus
- conduzir o método
- observar fricção
- apoiar o cliente no uso correto
- registrar aprendizados

### Usuário do cliente
- usar o Squad Cliente no fluxo combinado
- reportar dúvidas e fricções
- seguir o modo assistido
- validar utilidade prática

### APP32
- centralizar contexto
- expor capabilities MCP
- registrar trilhas
- dar suporte ao uso assistido

### Squad de Engenharia
- corrigir fricções críticas
- ajustar contratos, telemetria e experiência
- preparar rollout seguinte

## Critérios de sucesso da fase
A fase pode ser considerada implantada com sucesso se:
1. o fluxo piloto rodar com usuários reais
2. os dois squads forem usados com o papel correto
3. não houver quebra crítica de tenant/surface/governança
4. a experiência assistida for compreensível
5. o backlog pós-piloto ficar claro e acionável

## Critérios de não avanço
Não ampliar rollout se houver:
- confusão forte de papéis entre Squad Versus e Squad Cliente
- fricção excessiva de acesso/contexto
- uso fora do menor privilégio esperado
- trilha insuficiente de auditoria
- dependência excessiva do consultor para cada passo básico

## Recomendação prática imediata
A próxima trilha de execução deve seguir esta ordem:
1. selecionar piloto
2. configurar acessos do piloto
3. executar onboarding assistido
4. rodar fluxo real
5. consolidar backlog pós-piloto

## Veredito
A arquitetura já está pronta para implantação assistida controlada.
O que falta agora não é desenho; é operação real com disciplina de rollout.
