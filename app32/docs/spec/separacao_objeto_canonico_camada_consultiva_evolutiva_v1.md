# SPEC — Separação entre Objeto Canônico e Camada Consultiva/Evolutiva

**Classe documental:** SPEC  
**Status:** Decisão oficial v1  
**Data:** 2026-06-29  
**Origem:** `app32/docs/papers/paper_metodo_versus_estruturacao_evolutiva_v1.md`  
**Escopo:** APP32, Método Versus, Squads, Agentes, MCP e Orquestrador  

---

## 1. Objetivo

Esta SPEC transforma em regra implementável a separação oficial entre:

1. **Objeto Canônico** — aquilo que representa a realidade operacional, estrutural ou gerencial da empresa cliente.
2. **Camada Consultiva/Evolutiva** — aquilo que representa a leitura, condução, priorização, maturação e evolução metodológica feita pela Versus sobre essa realidade.

O APP32 deve servir simultaneamente:

- à empresa cliente, como sistema de gestão para seu uso diário;
- à Versus, como plataforma de condução metodológica, consultiva e evolutiva.

Essas duas finalidades não devem gerar dois mundos paralelos. A regra é: **a empresa opera sobre objetos canônicos; a Versus evolui esses objetos por meio da camada consultiva/evolutiva**.

---

## 2. Regra-mãe

Toda evolução funcional, técnica ou metodológica do APP32 deve partir da seguinte pergunta:

> **Isso existe primeiro para a empresa operar sua gestão ou para a Versus conduzir a evolução dessa gestão?**

Se existe primeiro para a empresa operar, é **Objeto Canônico**.

Se existe para interpretar, classificar, priorizar, amadurecer, auditar, conduzir gates ou conectar a metodologia Versus, é **Camada Consultiva/Evolutiva**.

A Camada Consultiva/Evolutiva deve preferencialmente se apoiar em objetos canônicos existentes por meio de:

- vínculos;
- classificações;
- enriquecimentos;
- overlays;
- leituras derivadas;
- trilhas de maturação;
- evidências;
- gates;
- análises de Business Review.

---

## 3. Definições oficiais

### 3.1. Objeto Canônico

Objeto Canônico é qualquer entidade, registro, estrutura ou relação que representa a realidade da empresa cliente e que pode ser usada no seu dia a dia de gestão.

Exemplos:

- empresa;
- área;
- cargo;
- colaborador;
- usuário;
- organograma;
- identidade organizacional;
- macroprocesso;
- processo;
- POP;
- rotina;
- jornada operacional;
- tarefa;
- projeto;
- responsável;
- indicador;
- meta;
- medição;
- reunião;
- decisão;
- evidência;
- bloqueio;
- dependência;
- documento operacional.

O Objeto Canônico deve ser compreensível e utilizável pelo cliente sem exigir domínio do vocabulário interno do Método Versus.

### 3.2. Camada Consultiva/Evolutiva

Camada Consultiva/Evolutiva é qualquer leitura, estrutura ou mecanismo que ajude a Versus, os squads, os agentes e o consultor a conduzir o amadurecimento da gestão da empresa.

Exemplos:

- fase metodológica;
- trilho metodológico;
- gate;
- leitura de maturidade;
- diagnóstico;
- classificação de urgência;
- Necessidade Urgente;
- jornada de estruturação;
- jornada de maturação;
- backlog de amadurecimento;
- priorização consultiva;
- Business Review;
- análise de investimento, custo, ganho, risco e retorno;
- readiness;
- escalonamento;
- overlay metodológico;
- recomendação de squad ou agente;
- benchmark;
- boas práticas pesquisadas externamente.

A Camada Consultiva/Evolutiva não deve substituir a realidade operacional. Ela deve explicá-la, organizá-la, amadurecê-la e orientar sua evolução.

---

## 4. Princípios de separação

### 4.1. O cliente não deve ser obrigado a pensar como a Versus

A interface operacional do cliente deve falar a linguagem da empresa:

- projeto;
- tarefa;
- processo;
- responsável;
- prazo;
- indicador;
- reunião;
- decisão;
- risco;
- custo;
- evidência.

A linguagem metodológica deve aparecer quando ela gerar valor claro:

- para o consultor;
- para o squad;
- para o cockpit evolutivo;
- para a priorização;
- para a governança;
- para a análise estratégica.

### 4.2. A Versus não deve operar fora do APP32

A separação entre as camadas não autoriza planilhas paralelas, controles soltos ou gestão metodológica fora do sistema.

A condução da Versus deve estar rastreada no APP32, vinculada aos objetos canônicos corretos.

### 4.3. Não criar duplicidade quando um vínculo resolve

Antes de criar uma nova tabela, entidade ou módulo consultivo, a arquitetura deve verificar se o caso pode ser resolvido por:

- tag;
- status;
- classificação;
- relacionamento;
- tabela de overlay;
- read model;
- comentário estruturado;
- evidência;
- evento;
- associação com projeto, processo, indicador ou reunião.

### 4.4. Pesquisa externa alimenta a leitura consultiva

Agentes, squads e consultores podem e devem realizar pesquisas profundas e vastas na internet quando o tema exigir:

- boas práticas;
- benchmarks;
- referências de mercado;
- legislação;
- padrões técnicos;
- comparações;
- riscos;
- alternativas de solução.

Essas pesquisas alimentam a Camada Consultiva/Evolutiva, mas não substituem:

- dados reais do APP32;
- MCP;
- evidências operacionais;
- decisões registradas;
- contexto específico da empresa.

---

## 5. Regras por domínio

### 5.1. Onboarding e setup

São Objetos Canônicos:

- identidade organizacional;
- contexto econômico;
- áreas;
- cargos;
- colaboradores;
- usuários;
- papéis;
- permissões;
- vínculos organizacionais.

São Camada Consultiva/Evolutiva:

- readiness de implantação;
- validação de maturidade inicial;
- setup assistido;
- checklist consultivo;
- integração com MCP;
- integração com Sapiens;
- canais de atendimento;
- testes controlados de entrada;
- análise de lacunas do onboarding.

### 5.2. Processos, rotinas e jornadas

São Objetos Canônicos:

- área;
- macroprocesso;
- processo;
- subprocesso;
- POP;
- rotina operacional;
- executor;
- responsável;
- jornada operacional;
- blocos de execução;
- agenda recorrente;
- regras recorrentes;
- vínculo operacional entre rotina e jornada.

São Camada Consultiva/Evolutiva:

- diagnóstico de processo;
- criticidade;
- fase metodológica;
- maturidade;
- estabilidade;
- evidência de gate;
- backlog de amadurecimento;
- jornada de estruturação;
- jornada de maturação;
- recomendação de redesenho;
- análise de aderência a boas práticas.

### 5.3. Painel estratégico, indicadores e maturação

São Objetos Canônicos:

- indicador;
- meta;
- medição;
- linha de visada;
- projeto;
- processo;
- reunião;
- decisão;
- evidência;
- plano de ação.

São Camada Consultiva/Evolutiva:

- painel como cockpit de maturação;
- leitura de alinhamento estratégico;
- itens de evolução S1-S2 e S2-S3;
- análise de readiness;
- priorização consultiva;
- recomendação de ajuste de indicador;
- Business Review;
- avaliação de investimento, custo, ganho, risco e retorno.

### 5.4. Projetos, urgências e Business Review

São Objetos Canônicos:

- projeto;
- atividade;
- responsável do projeto;
- executor;
- prazo;
- custo;
- esforço;
- evidência;
- bloqueio;
- dependência;
- aprovação operacional;
- transferência de responsabilidade.

São Camada Consultiva/Evolutiva:

- Necessidade Urgente;
- leitura de criticidade;
- leitura de fase;
- trilho metodológico;
- análise de valor;
- Business Review;
- análise de investimento;
- análise de custo;
- análise de ganho;
- análise de risco;
- análise de retorno;
- ponte consultiva para estruturação de processo.

Regra específica:

> Toda Necessidade Urgente deve alimentar o Business Review, pois sempre haverá impacto de investimento, custo, ganho, risco, retorno ou decisão de alocação.

Isso não exige criar um sistema paralelo de controle. A necessidade urgente pode aparecer para o cliente como um projeto ou atividade, enquanto para a Versus recebe uma leitura consultiva que conecta o fato ao Business Review e à eventual reestruturação de processos.

### 5.5. Squads, agentes e orquestrador

Squad Cliente, Squad Versus, Squad de Engenharia, agentes e orquestrador **não formam uma terceira camada**.

Eles são atores transversais que atuam sobre as duas camadas:

- no Objeto Canônico, ajudam a registrar, executar, auditar e manter a realidade operacional;
- na Camada Consultiva/Evolutiva, ajudam a interpretar, priorizar, pesquisar, recomendar, amadurecer e conduzir a metodologia.

Essa distinção é obrigatória para evitar que agentes ou squads criem uma realidade própria desconectada da gestão da empresa.

---

## 6. Regras de implementação no APP32

### 6.1. Modelagem de dados

Novos modelos devem indicar explicitamente se representam:

- Objeto Canônico;
- Camada Consultiva/Evolutiva;
- relacionamento entre ambos.

Quando houver dúvida, a preferência arquitetural é:

1. preservar o Objeto Canônico;
2. criar vínculo ou overlay;
3. criar read model se necessário;
4. criar nova entidade consultiva somente quando o vínculo não for suficiente.

Todo dado operacional ou consultivo vinculado a uma empresa deve respeitar multi-tenancy por `company_id`.

### 6.2. Serviços

Regras de classificação, priorização, maturidade, Business Review e gates devem ficar em services ou camada equivalente de domínio.

Rotas Flask não devem conter lógica de negócio.

### 6.3. APIs, MCP e superfícies

APIs, MCP surfaces e ferramentas de agentes devem deixar claro:

- qual Objeto Canônico está sendo lido ou alterado;
- qual leitura consultiva está sendo aplicada;
- qual empresa (`company_id`) está no escopo;
- qual permissão/capability autoriza a operação.

Nenhuma ferramenta deve permitir que uma camada consultiva altere diretamente dados operacionais críticos sem rastreabilidade e autorização.

### 6.4. Frontend

O frontend deve separar a experiência em dois tipos de superfície:

1. **Superfície operacional do cliente** — simples, direta, orientada ao uso diário.
2. **Cockpit consultivo/evolutivo** — orientado a diagnóstico, priorização, maturação, gates, Business Review e atuação dos squads.

O mesmo Objeto Canônico pode aparecer nas duas superfícies, mas com leituras diferentes.

---

## 7. Anti-padrões proibidos

São proibidos como decisão arquitetural:

1. Duplicar projeto, processo, indicador ou rotina apenas para representar uma leitura metodológica.
2. Transformar fase, gate ou trilho em cadastro obrigatório para o cliente operar.
3. Criar uma gestão paralela da Versus fora do APP32.
4. Misturar linguagem consultiva em telas operacionais sem necessidade.
5. Permitir que agentes atuem sem vínculo com Objeto Canônico ou evidência.
6. Criar automações que ignorem `company_id`.
7. Tratar benchmark externo como verdade superior ao contexto real da empresa.
8. Criar decisão consultiva sem rastrear origem, evidência ou responsável.

---

## 8. Critérios de aceite para novas evoluções

Toda nova funcionalidade, ajuste de arquitetura ou ampliação metodológica deve responder:

1. Qual é o Objeto Canônico envolvido?
2. Existe Camada Consultiva/Evolutiva? Qual?
3. O cliente consegue usar a funcionalidade sem entender jargão interno da Versus?
4. O consultor consegue conduzir a metodologia sem controle paralelo?
5. Há rastreabilidade entre objeto, leitura, decisão e evidência?
6. O dado está corretamente escopado por `company_id`?
7. A regra de negócio está fora da rota?
8. APIs, MCP e agentes respeitam permissões e menor privilégio?
9. A pesquisa externa, quando usada, aparece como subsídio e não como substituição da realidade operacional?
10. A solução evita duplicidade entre operação e metodologia?

---

## 9. Impactos esperados

Esta SPEC deve orientar:

- evolução do modelo de dados;
- desenho de APIs;
- desenho de MCP surfaces;
- comportamento dos agentes;
- cockpit consultivo;
- experiência do cliente;
- backlog da Fase 02;
- separação entre gestão operacional e método;
- próximos documentos oficiais de arquitetura.

Ela também deve ser usada como filtro para revisar funcionalidades existentes que possam estar misturando:

- projeto operacional com Necessidade Urgente;
- processo operacional com jornada de estruturação;
- indicador real com leitura de maturidade;
- reunião gerencial com gate metodológico;
- squad/agente com camada própria de dados.

---

## 10. Próximos documentos derivados

Esta SPEC é a matriz de separação. A partir dela, devem ser derivados:

1. SPEC — Onboarding e setup canônico/evolutivo.
2. SPEC — Processos, rotinas e jornadas.
3. SPEC — Painel estratégico, indicadores e maturação.
4. SPEC — Projetos, Necessidades Urgentes e Business Review.
5. SPEC — Squads, agentes, orquestrador e pesquisas externas.
6. Playbook — Tratamento de Necessidades Urgentes.
7. Runbook — Operação segura APP32/Squads/MCP.
8. Harness — Validação de aderência entre Objeto Canônico e Camada Consultiva/Evolutiva.

---

## 11. Decisão final

O APP32 não terá três camadas.

A arquitetura oficial passa a ser:

1. **Objeto Canônico** — a empresa como ela é e opera.
2. **Camada Consultiva/Evolutiva** — a Versus interpretando, conduzindo, amadurecendo e acelerando essa empresa.

Squads, agentes, MCP e orquestrador atuam transversalmente sobre ambas, sempre com rastreabilidade, multi-tenancy, governança e vínculo com a realidade operacional.

