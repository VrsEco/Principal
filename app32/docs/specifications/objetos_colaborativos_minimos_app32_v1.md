# Objetos Colaborativos Mínimos do APP32 — Versus Gestão Corporativa

## Status
Versão inicial v1 produzida no contexto do card `AA.J.15.4`.

## Objetivo
Modelar os objetos colaborativos mínimos que o APP32 precisa sustentar para permitir colaboração institucional entre:
- humano do cliente
- agente do Squad Cliente
- consultor da Versus
- agente do Squad Versus
- Engenharia, quando aplicável

---

## 1. Princípio
O APP32 não deve servir apenas para leitura e mutação operacional.

Ele deve sustentar também **objetos de colaboração rastreáveis**, que permitam:
- análise
- parecer
- pendência
- revisão
- aprovação
- handoff
- evidência

---

## 2. Achados do estado atual
A base atual já possui peças úteis, mas ainda fragmentadas.

### 2.1 AgentAction
Arquivo:
- `C:/GestaoVersus/app32/app32/models/agent_action.py`

Uso atual:
- ação proposta por agente
- status
- agente solicitante / agente tratador
- payload técnico
- `company_id`
- `user_id`
- timestamps

### 2.2 AgentActionBacklogLink
Arquivo:
- `C:/GestaoVersus/app32/app32/models/agent_action_backlog_link.py`

Uso atual:
- vínculo entre `AgentAction` e card de backlog
- ponte entre ação agentic e execução formal

### 2.3 OperationalAuditService
Arquivo:
- `C:/GestaoVersus/app32/app32/services/operational_audit_service.py`

Uso atual:
- timeline consolidada
- eventos de runtime IA/MCP
- human review
- workflow approvals
- agent actions

### 2.4 Approvals / trilhas associadas
Existem serviços e painéis que já trabalham com:
- approvals pendentes
- workflow approvals
- human gate
- backlog automático
- auditoria operacional

### Leitura
A base atual já permite reaproveitar estruturas, mas ainda não existe um **modelo canônico explícito de objetos colaborativos mínimos**.

---

## 3. Objetos colaborativos mínimos recomendados

### 3.1 Análise
#### Finalidade
Registrar leitura estruturada de contexto, risco, desempenho ou situação operacional.

#### Papel na arquitetura
- pode ser produzida pelo `Squad Versus`, `Squad Cliente` ou humano
- serve como base para parecer, decisão ou handoff

#### Estado atual
- parcialmente implícita em payloads, auditorias e documentos
- ainda não modelada como objeto canônico dedicado

### 3.2 Parecer
#### Finalidade
Registrar posição orientativa, crítica ou recomendatória sobre um contexto analisado.

#### Papel na arquitetura
- muito importante para `Squad Versus`
- pode orientar o cliente sem executar diretamente a mudança

#### Estado atual
- aparece disperso em mensagens, notas e payloads
- ainda não modelado como objeto canônico dedicado

### 3.3 Pendência
#### Finalidade
Registrar algo que precisa de ação, retorno, correção, complemento ou decisão.

#### Papel na arquitetura
- objeto essencial para o fluxo operacional assistido
- conecta análise → ação → acompanhamento

#### Estado atual
- parcialmente coberto por `ProjectTask`, backlog e alguns fluxos de approval
- ainda sem objeto colaborativo mínimo explícito e transversal

### 3.4 Revisão
#### Finalidade
Registrar que algo foi revisto por outro ator, com resultado e observações.

#### Papel na arquitetura
- importante para coprodução humano + agente
- importante para controle de qualidade e maturidade

#### Estado atual
- parcialmente implícita em audit trail e human review
- ainda não consolidada como objeto de colaboração explícito

### 3.5 Aprovação
#### Finalidade
Registrar aceite, rejeição ou autorização formal para avançar com ação sensível.

#### Papel na arquitetura
- essencial para governança de mutações relevantes
- conecta agentic action, humano e backlog

#### Estado atual
- já possui boa base de serviços e auditoria
- é o objeto mais próximo de estar institucionalizado

### 3.6 Handoff
#### Finalidade
Registrar passagem de contexto, responsabilidade ou próxima ação entre atores/squads.

#### Papel na arquitetura
- central para despacho entre `Sapiens`, `Squad Cliente`, `Squad Versus` e humano

#### Estado atual
- fortemente necessário
- ainda pouco explícito como objeto próprio

### 3.7 Evidência
#### Finalidade
Registrar o que comprova que algo foi analisado, decidido, aprovado, executado ou revisado.

#### Papel na arquitetura
- essencial para auditoria, qualidade e rastreabilidade

#### Estado atual
- já existe de forma fragmentada em notes, audit trail, logs e backlog
- precisa normalização mínima

---

## 4. Modelo canônico mínimo recomendado
Para o MVP, não é obrigatório criar sete tabelas novas imediatamente.

A recomendação é trabalhar com um **modelo mínimo canônico** baseado em três eixos:

### Eixo A — Registro de ação/decisão
Base reaproveitável:
- `AgentAction`
- future `collaboration_record` ou equivalente, se necessário

### Eixo B — Encaminhamento/execução
Base reaproveitável:
- `ProjectTask`
- `AgentActionBacklogLink`
- backlog formal

### Eixo C — Trilha/evidência
Base reaproveitável:
- `OperationalAuditService`
- eventos MCP/IA
- human review
- approval trail

---

## 5. Proposta mínima para o MVP
### 5.1 Objetos a institucionalizar primeiro
Para o MVP operacional assistido, institucionalizar primeiro:
1. `pendência`
2. `aprovação`
3. `handoff`
4. `evidência`

### 5.2 Objetos a manter inicialmente como camada lógica
Podem ficar inicialmente como tipo lógico/semântico em payload ou registro:
- `análise`
- `parecer`
- `revisão`

### Motivo
Isso reduz custo inicial de modelagem sem abrir mão da governança do fluxo assistido.

---

## 6. Estrutura mínima recomendada por objeto
Todo objeto colaborativo mínimo deveria carregar, no mínimo:
- `company_id`
- `object_type`
- `source_actor_type`
- `source_actor_id` ou equivalente
- `target_actor_type` quando houver
- `status`
- `title`
- `summary`
- `payload`
- `linked_capability` quando aplicável
- `linked_project_task_id` quando aplicável
- `linked_agent_action_id` quando aplicável
- `created_at`
- `updated_at`

---

## 7. Relação com os squads

### Squad Cliente
Usará principalmente:
- pendência
- handoff
- evidência

### Squad Versus
Usará principalmente:
- análise
- parecer
- revisão
- aprovação
- handoff

### Sapiens
Usará principalmente:
- pendência
- handoff
- orientação baseada em análise/parecer

### Engenharia
Usará principalmente:
- evidência
- aprovação
- handoff técnico
- backlog relacionado

---

## 8. Gaps atuais
1. falta objeto canônico transversal para pendência/handoff
2. análise, parecer e revisão ainda estão mais no plano semântico do que no plano estrutural
3. evidência existe, mas fragmentada
4. approvals já têm base boa, mas ainda precisam conversa explícita com os demais objetos colaborativos

---

## 9. Decisão recomendada do passo
### Decisão
Para o MVP da Versus Gestão Corporativa, o APP32 deve adotar um modelo colaborativo mínimo baseado em:
- `AgentAction` como eixo de ação sensível/decisória
- `ProjectTask`/backlog como eixo de pendência/execução
- trilhas de auditoria e approval como eixo de evidência
- semântica explícita de `handoff`, `pendência`, `aprovação` e `evidência`

### Próximo desdobramento natural
No passo seguinte, as capabilities MVP do domínio operacional devem já prever esses objetos como parte do fluxo, mesmo que inicialmente apoiados em modelos reaproveitados.

---

## 10. Veredito final do Passo 4
O APP32 já possui base suficiente para começar a operação colaborativa mínima, desde que a Versus normalize semanticamente e operacionalmente os objetos centrais do fluxo.

O MVP não precisa nascer com modelagem perfeita, mas precisa nascer com:
- pendência clara
- handoff claro
- approval claro
- evidência clara

Esse é o fechamento mínimo para o primeiro fluxo operacional assistido.
