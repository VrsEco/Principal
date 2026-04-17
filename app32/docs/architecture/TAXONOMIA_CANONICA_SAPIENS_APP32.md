# Taxonomia Canônica Sapiens / APP32

## Objetivo

Estabelecer a taxonomia canônica que deve ser usada de forma consistente por:

- catálogo de capabilities
- contracts MCP
- RBAC / policy engine
- playbooks de domínio
- runtime guard
- testes de drift
- fluxos conversacionais do Sapiens

Este documento existe para eliminar deriva semântica entre nomes de domínio publicados e nomes de domínio realmente autorizáveis no runtime.

---

## Problema observado

Hoje existem tools publicadas com domínios que não são reconhecidos de forma canônica em toda a stack, por exemplo:

- `work`
- `tasks`
- `worklog`
- `processes`

Na prática isso produz:

- `unknown_domain_rejected` na policy engine
- bloqueio indevido de ferramentas válidas
- divergência entre playbook, catálogo e RBAC
- comportamento inconsistente entre menu operacional e agente livre

---

## Princípios da taxonomia

1. **Poucos domínios canônicos**
   - o domínio deve representar uma fronteira real de negócio

2. **Aliases explícitos**
   - aliases podem existir para linguagem natural e compatibilidade
   - aliases nunca devem ser tratados como domínio primário na policy

3. **Fonte única de verdade**
   - catálogo, contracts, RBAC e playbooks devem usar o mesmo nome canônico

4. **Autorização derivável**
   - toda tool publicada deve apontar para um domínio que exista em:
     - contrato de perfil
     - matriz RBAC
     - playbook de domínio

5. **Drift falha em teste**
   - se uma tool for publicada com domínio fora da taxonomia, a suíte deve falhar

---

## Domínios canônicos oficiais propostos

### 1. `routine`

**Escopo:** trabalho operacional do dia a dia.

Inclui:

- tarefas pessoais
- tarefas da equipe
- tarefas da empresa
- pendências
- itens atrasados
- worklog operacional
- consultas operacionais rápidas

**Aliases oficiais**

- `work`
- `tasks`
- `worklog`

**Exemplos de tools**

- `get_my_work`
- `get_tasks_today`
- `complete_task`
- `log_work_hours`

**Perfis esperados**

- `colaborador`
- `cliente` (somente leitura)
- `administrador`
- `admin_tecnico` apenas quando o fluxo realmente exigir intervenção técnica

---

### 2. `projects`

**Escopo:** projetos e atividades vinculadas a projeto.

Inclui:

- projetos
- atividades de projeto
- responsáveis
- prazos
- risco de execução
- extensão de prazo

**Exemplos de tools**

- `create_project_task`
- `request_deadline_extension`
- `get_projects_execution_risk_read_model`

---

### 3. `processes`

**Escopo:** processos estruturados e instâncias de workflow.

Inclui:

- áreas de processo
- macroprocessos
- processos
- hierarquia de processo
- instâncias e andamento de workflow

**Exemplos de tools**

- `create_process_area`
- `create_macro_process`
- `create_process`
- `list_process_hierarchy`

**Decisão arquitetural**

`processes` deve continuar como domínio canônico próprio.  
Ele não deve ser absorvido por `routine`, porque possui semântica de workflow estruturado e ciclo de vida próprio.

---

### 4. `meetings`

**Escopo:** reuniões e seus desdobramentos.

Inclui:

- agendamento
- início
- registro
- encerramento
- envio de resumo / ata

---

### 5. `strategy`

**Escopo:** estratégia, planos, diagnósticos e indicadores.

Inclui:

- planos
- seções de plano
- diagnósticos estratégicos
- indicadores e análises de leitura executiva

---

### 6. `finance`

**Escopo:** dados e operações financeiras sensíveis.

Inclui:

- resultados financeiros
- análises financeiras
- mutações financeiras auditáveis

**Regra adicional**

- sempre exigir disciplina reforçada de tenant
- quando aplicável, exigir `company_id` explícito

---

### 7. `analytics`

**Escopo:** leitura analítica consolidada.

Inclui:

- read models
- diagnósticos
- envelopes analíticos
- consultas whitelisted

**Regra adicional**

- nunca mutar dados operacionais por `analytics`

---

### 8. `workload`

**Escopo:** capacidade e carga de equipe.

Inclui:

- workload
- capacidade
- sobrecarga
- distribuição de carga

**Regra de fronteira**

- `routine` = operação
- `workload` = análise de capacidade

---

### 9. `identity_self_service`

**Escopo:** dados do próprio usuário.

Inclui:

- minhas empresas
- meus contatos
- meus dados próprios

---

### 10. `identity_admin`

**Escopo:** administração de usuários e acessos.

Inclui:

- usuários do sistema
- perfis
- permissões
- gestão administrativa de acesso

---

### 11. `governance`

**Escopo:** políticas, contratos e regras de governança.

Inclui:

- políticas MCP
- contratos de perfil/surface
- regras de auditoria e segurança

---

### 12. `operations`

**Escopo:** suporte técnico e intervenção operacional técnica.

Inclui:

- troubleshooting
- incidentes
- intervenção auditável
- suporte técnico controlado

**Restrição**

- domínio restrito a `admin_tecnico`

---

## Domínios que não devem existir como canônicos

Os nomes abaixo podem existir como alias semântico ou legado, mas não devem permanecer como domínio principal no catálogo:

- `work`
- `tasks`
- `worklog`

Esses nomes devem ser normalizados para `routine` antes da avaliação da policy.

---

## Mapa alias -> canônico

| Alias | Domínio canônico |
|---|---|
| `work` | `routine` |
| `tasks` | `routine` |
| `worklog` | `routine` |
| `process` | `processes` |
| `workflow` | `processes` |
| `identity` | `identity_self_service` |
| `my_profile` | `identity_self_service` |
| `my_companies` | `identity_self_service` |
| `my_contacts` | `identity_self_service` |

---

## Matriz de perfil sugerida

### `colaborador`

Pode acessar:

- `routine`
- `projects`
- `processes`
- `meetings`
- `strategy`
- `identity_self_service`

Não deve acessar:

- `finance`
- `analytics`
- `workload`
- `identity_admin`
- `governance`
- `operations`

### `cliente`

Pode acessar:

- `routine` em leitura
- `projects` em leitura
- `processes` em leitura, quando fizer sentido de negócio
- `meetings` em leitura
- `strategy` em leitura/análise
- `identity_self_service`

Não deve acessar:

- `analytics`
- `workload`
- `identity_admin`
- `operations`

### `administrador`

Pode acessar:

- `routine`
- `projects`
- `processes`
- `meetings`
- `strategy`
- `finance`
- `analytics`
- `workload`
- `identity_self_service`
- `identity_admin`
- `governance`

Não deve acessar:

- `operations` técnico como domínio principal

### `admin_tecnico`

Pode acessar:

- `operations`
- `analytics`
- `workload`
- demais domínios conforme contrato técnico e superfície permitida

---

## Regras normativas de implementação

### Regra 1 — publicação de tool

Toda tool nova ou alterada deve usar um `domain` que pertença à lista canônica.

### Regra 2 — normalização obrigatória

Antes da avaliação de RBAC/policy, o domínio deve passar por normalização:

- alias -> domínio canônico

### Regra 3 — alinhamento em quatro camadas

Qualquer domínio publicado deve existir em:

1. `tooling/capabilities.py`
2. `security/tenant_rbac.py`
3. `mcp_contracts/profiles.py`
4. `mcp_contracts/domain_playbooks.py`

### Regra 4 — testes de drift

A suíte de drift deve falhar se:

- houver tool publicada com domínio fora da taxonomia canônica
- houver domínio no catálogo ausente do RBAC
- houver domínio no catálogo ausente dos contratos de perfil
- houver domínio no catálogo ausente dos playbooks

### Regra 5 — menu conversacional e taxonomia

O `menu_engine` deve apontar intenções operacionais para a taxonomia canônica.

Exemplo:

- “tarefas atrasadas”
- “atividades em aberto”
- “me traga minhas tarefas”

Tudo isso deve convergir para o domínio `routine`.

---

## Ordem de correção recomendada

### Fase 1 — normalização da taxonomia

1. criar normalizador `alias -> canônico`
2. migrar `work`, `tasks`, `worklog` para `routine`
3. validar `processes` como domínio canônico em toda a stack

### Fase 2 — enforcement

1. atualizar `tenant_rbac.py`
2. atualizar `profiles.py`
3. atualizar `permission_matrix.py`
4. atualizar `domain_playbooks.py`

### Fase 3 — catálogo

1. revisar `tooling/capabilities.py`
2. garantir que nenhuma tool publicada use domínio fora da lista canônica

### Fase 4 — conversação

1. ampliar detecção do `menu_engine`
2. cobrir linguagem natural operacional como:
   - `me traga`
   - `traga`
   - `preciso que você me traga`
   - `quero ver`

### Fase 5 — proteção por testes

1. expandir testes de drift
2. incluir testes de policy para:
   - `routine`
   - `processes`
   - aliases normalizados
3. incluir smoke do runtime oficial com frases reais de WhatsApp

---

## Casos que esta taxonomia deve resolver

### Caso 1 — consulta operacional

> “Preciso que você me traga as tarefas atrasadas de Marcio da empresa Ventana”

Classificação esperada:

- domínio: `routine`
- ação: `read`
- tenant: `Ventana`
- recorte: colaborador `Márcio`
- surface: `user`

### Caso 2 — consulta pessoal

> “Quais tarefas eu tenho para hoje?”

Classificação esperada:

- domínio: `routine`
- ação: `read`
- escopo: próprio usuário

### Caso 3 — carga de equipe

> “Como está a capacidade da equipe esta semana?”

Classificação esperada:

- domínio: `workload`
- ação: `analyze`

### Caso 4 — criação de processo

> “Crie um novo processo de onboarding”

Classificação esperada:

- domínio: `processes`
- ação: `create`

---

## Arquivos-alvo da implementação

- `C:\GestaoVersus\app32\app32\src\intelligence\tooling\capabilities.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\security\tenant_rbac.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\security\tool_policy.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\work_agents\tool_runtime_guard.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\profiles.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\permission_matrix.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\mcp_contracts\domain_playbooks.py`
- `C:\GestaoVersus\app32\app32\src\intelligence\menu_engine.py`
- `C:\GestaoVersus\app32\app32\tests\test_ai_mcp_contract_drift_suite.py`
- `C:\GestaoVersus\app32\app32\tests\test_intelligence_security_tool_policy.py`
- `C:\GestaoVersus\app32\app32\tests\test_intelligence_security_tenant_rbac.py`

---

## Critério de aceite arquitetural

Considera-se a taxonomia corrigida quando:

1. nenhuma tool publicada usar domínio fora da lista canônica
2. aliases forem normalizados antes da policy
3. catálogo, profile contracts, RBAC e playbooks compartilharem o mesmo vocabulário
4. frases operacionais reais de WhatsApp resolverem corretamente para a tool autorizada
5. a suíte de drift impedir regressão
