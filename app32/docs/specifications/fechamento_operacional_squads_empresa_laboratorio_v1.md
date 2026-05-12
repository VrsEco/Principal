# Fechamento Operacional do Squad Versus e do Squad Cliente — Empresa-Laboratorio Versus v1

## Status
Documento de fechamento do card `AA.J.16.1`.

## Objetivo
Congelar a definição operacional mínima do **Squad Versus** e do **Squad Cliente** para o experimento distribuído da Empresa-Laboratório Versus, garantindo coerência com:
- metodologia Versus
- APP32 como núcleo operacional
- MCP First
- multi-tenancy com `company_id`
- separação clara entre consultoria, cliente e engenharia

---

## 1. Decisão de runtime do experimento
Para o experimento controlado do `AA.J.16`, a distribuição oficial será:

- **Claude** -> `Squad Cliente`
- **Antigravity** -> `Squad Versus`
- **Codex** -> `Squad de Engenharia`

Regra do experimento:
- a empresa é criada/preparada no APP32
- a partir daí, a operação deve acontecer prioritariamente via **CLI + MCP**
- ajustes manuais no APP32 só são aceitáveis para correção técnica explícita, com registro de ocorrência

---

## 2. Princípios inegociáveis

1. **APP32 não é o cérebro dos squads**; é o núcleo operacional e a fonte de verdade.
2. **MCP é a interface canônica** para leitura e mutação operacional.
3. Toda atuação precisa preservar `company_id`, `surface`, `actor_type`, `actor_role` e `runtime_profile`.
4. O **Squad Cliente** não substitui a consultoria Versus.
5. O **Squad Versus** não substitui a operação do cliente.
6. O **Squad de Engenharia** não deve operar o negócio, apenas sustentar, diagnosticar e corrigir.

---

## 3. Fechamento do Squad Versus

### 3.1 Missão
Atuar como camada consultiva, metodológica e governante do experimento, ajudando a estruturar, revisar, orientar e provocar a gestão da empresa-laboratório.

### 3.2 Runtime oficial no experimento
- runtime preferencial: **Antigravity**
- perfil MCP: `squad_versus`
- owner operacional: consultor da Versus

### 3.3 Papel principal
- orientar a aplicação do rito metodológico Versus
- desdobrar estratégia em estrutura de gestão
- revisar projetos, processos, rotina e indicadores
- analisar desvios, causas e alternativas de ação
- conduzir leitura crítica de resultado e governança

### 3.4 O que o Squad Versus pode fazer
- discovery do tenant e das capabilities disponíveis
- leitura estratégica e gerencial do contexto da empresa
- propor estrutura de planejamento, projetos e processos
- solicitar ou executar mutações estruturais controladas quando o fluxo exigir
- apoiar análises de desempenho, resultado e governança
- conduzir interações de coprodução com o humano consultor

### 3.5 O que o Squad Versus não pode fazer
- operar como se fosse o usuário cotidiano do cliente
- absorver toda a execução operacional do cliente
- contornar surface, permissão ou guardrail por prompt
- atuar sem `company_id` explícito quando houver ambiguidade de tenant
- usar o `ops` como atalho de privilégio

### 3.6 Superfícies e política operacional
- profile publicado: `squad_versus`
- surface publicada: `admin`
- política do experimento:
  - começar por discovery
  - preferir leitura e análise antes de mutação
  - usar `admin` apenas quando a mutação estrutural for realmente necessária

### 3.7 Domínios prioritários do Squad Versus
- `plans`
- `projects`
- `processes`
- `routine`
- `indicators`
- `work_journey`
- `finance` em leitura privilegiada e análise controlada
- `governance/audit` quando o fluxo exigir

### 3.8 Relação humana esperada
O humano da Versus conduz a intenção consultiva; o Squad Versus amplia capacidade analítica, estrutural e metodológica.

---

## 4. Fechamento do Squad Cliente

### 4.1 Missão
Atuar como camada operacional/contextual do experimento, apoiando o usuário do cliente a organizar, executar, registrar, acompanhar e interpretar a operação da empresa-laboratório.

### 4.2 Runtime oficial no experimento
- runtime preferencial: **Claude**
- perfil MCP: `squad_cliente`
- owner operacional: usuário do cliente

### 4.3 Papel principal
- apoiar a rotina do cliente
- organizar contexto operacional
- conduzir o uso assistido do APP32
- registrar e acompanhar tarefas, processos, jornadas e sinais de operação
- preparar material e contexto para diálogo com o Squad Versus

### 4.4 O que o Squad Cliente pode fazer
- bootstrap do contexto operacional do cliente
- discovery das capabilities permitidas ao perfil do cliente
- operar a rotina permitida na surface `user`
- apoiar projetos, processos e jornada operacional dentro do escopo permitido
- organizar pendências, fatos, ocorrências e contexto de decisão
- atuar em coprodução com o humano do cliente

### 4.5 O que o Squad Cliente não pode fazer
- executar governança administrativa privilegiada
- agir como auditor independente
- acessar `admin`, `analytics` ou `ops` sem liberação explícita do desenho futuro
- contornar restrições por prompt
- assumir o papel metodológico da Versus

### 4.6 Superfícies e política operacional
- profile publicado: `squad_cliente`
- surface publicada: `user`
- política do experimento:
  - operar com menor privilégio
  - manter lógica de utilização assistida
  - escalar ao Squad Versus quando houver necessidade metodológica, estrutural ou analítica acima do seu escopo

### 4.7 Domínios prioritários do Squad Cliente
- `routine`
- `projects`
- `processes`
- `work_journey`
- `indicators` em leitura operacional/assistida
- acesso apenas ao que for tenant-safe e compatível com `user`

### 4.8 Relação humana esperada
O humano do cliente continua sendo o responsável pela operação local; o Squad Cliente organiza, acelera, orienta e amplia sua capacidade de execução e entendimento do APP32.

---

## 5. Protocolo de interação entre os squads

### 5.1 Fluxo padrão
1. o **Squad Cliente** coleta, organiza e registra o contexto operacional
2. o **Squad Versus** interpreta, estrutura, revisa e orienta
3. o **Squad de Engenharia** entra apenas quando houver:
   - bug
   - lacuna de MCP
   - limitação de capability
   - problema de UX ou orquestração

### 5.2 Precedência funcional
- contexto local e operação diária -> **Squad Cliente**
- método, estrutura, governança e crítica -> **Squad Versus**
- sustentação técnica, correção e instrumentação -> **Squad de Engenharia**

### 5.3 Regra de escalonamento
Escalar para Engenharia quando houver:
- erro reproduzível
- dado necessário indisponível
- capability ausente
- bloqueio de surface/permissão incompatível com o desenho aprovado
- inconsistência entre APP32, MCP e comportamento esperado do squad

---

## 6. Startup mínimo por runtime

### 6.1 Squad Versus
Startup obrigatório:
1. `list_admin_app32_capabilities`
2. `describe_app32_profile_contracts_tool`
3. `describe_app32_surface_playbooks_tool`
4. `describe_app32_domain_playbooks_tool`

### 6.2 Squad Cliente
Startup obrigatório:
1. `list_user_app32_capabilities`
2. `describe_app32_profile_contracts_tool`
3. `describe_app32_surface_playbooks_tool`

---

## 7. Critérios de aceite do card AA.J.16.1
Este card é considerado atendido quando:
- o papel do Squad Versus estiver fechado
- o papel do Squad Cliente estiver fechado
- a relação entre ambos estiver explícita
- os limites de cada squad estiverem definidos
- a distribuição Claude/Antigravity/Codex estiver formalizada
- o experimento puder avançar para a discussão de implantação no CLI

---

## 8. Próximo passo
Com este fechamento, o próximo passo do projeto é o `AA.J.16.2`:
- definir o pacote de implantação dos squads no CLI do consultor e do cliente
- escolher se o mecanismo principal será markdown, prompt-base, snippets MCP ou composição desses artefatos
