# Paper — Instruction Registry Bootstrap Remoto do Squad Cliente v1

Status: oficial para evolução  
Escopo: bootstrap remoto, bundle instrucional mínimo, escalabilidade e governança do `Sapiens Cliente`

## 1. Problema

Hoje o `Sapiens Cliente` já possui bootstrap operacional via MCP, mas a camada instrucional ainda depende mais de artefatos locais, runtime acoplado e documentação espalhada do que de um registry remoto versionado.

Isso gera quatro riscos:
- drift entre docs, harnesses e runtime
- rollout lento de mudança instrucional
- bootstrap inflado quando tentamos resolver tudo por prompt
- baixa governabilidade por tenant, canal e versão

## 2. Tese

O bootstrap do `Squad Cliente` deve evoluir de:

- descoberta operacional via MCP

para:

- descoberta operacional via MCP
- mais resolução de bundle instrucional mínimo via MCP

## 3. Princípio central

O agente não deve carregar a documentação completa no início da sessão.  
Ele deve carregar apenas um **bundle mínimo**, curto, cacheável e versionado, contendo:

- identidade operacional
- startup sequence
- regras obrigatórias
- handoffs
- ações proibidas
- referências canônicas

## 4. Hipótese de eficiência

O bundle mínimo aumenta levemente o custo do bootstrap, mas tende a reduzir o custo total do fluxo quando:

- reduz ambiguidade do agente
- reduz retrabalho
- reduz drift
- melhora previsibilidade
- evita reexplicar regras a cada sessão

## 5. Camadas propostas

### 5.1 Global
- multi-tenancy
- `company_id`
- MCP First
- boundaries
- safety

### 5.2 Runtime/Squad
- missão do `Squad Cliente`
- surface `user`
- ordem de startup
- política de escalonamento

### 5.3 Agente/Harness
- `SC-COORD`, `SC-COM`, `SC-OPS`, `SC-ADM`
- especialização curta
- handoffs
- proibições

### 5.4 Tenant override
- customização mínima e auditável
- sem poder violar camada global

## 6. Critérios de sucesso

- bundle remoto carregado com baixo custo de tokens
- versionamento explícito
- cache por versão/canal
- redução de drift
- capacidade de rollout incremental por tenant

## 7. Decisão derivada

Esta tese evolui para a SPEC:

- `C:\GestaoVersus\app32\app32\docs\spec\squad_cliente\arquitetura_instruction_registry_squad_cliente_v1.md`
