# APP32 — Desenho Arquitetural do Processo "Novo Contrato"

**Data:** 2026-04-30  
**Projeto estruturante:** `AA.J.54`  
**Atividade-base:** `AA.J.54.1936` — Avaliar aplicação do padrão de abas ao fluxo/cadastro de Novo Contrato  
**Escopo:** fluxo guiado de criação de contrato com BPMN, capabilities e UI modular por abas

---

## 1. Objetivo

Definir um modelo executável para o processo **Novo Contrato** no APP32, usando:

- **BPMN como orquestrador** da jornada
- **capabilities** como blocos funcionais reutilizáveis
- **shell padrão de processo** para experiência guiada
- **composição por abas** para tela/cadastro modular
- **instância de processo** com persistência, retomada e multi-tenancy

---

## 2. Tese arquitetural

O processo **Novo Contrato** deve ser implementado como uma **instância BPMN orientada a capability**, onde:

1. o usuário inicia uma instância do processo
2. o runtime identifica o step atual
3. cada step resolve:
   - capability necessária
   - modo de interação
   - abas/blocos relevantes
4. o shell da jornada apresenta a UI guiada
5. os dados são persistidos por etapa, com retomada posterior

### Regra central

O BPMN **não chama uma tela hardcoded**.  
Ele chama uma **capability** e o runtime resolve:

- se será execução automática ou humana
- qual componente UI abrir
- quais abas aparecem
- quais dados precisam ser carregados/preenchidos

---

## 3. Entidades principais do domínio

### 3.1. Entidade raiz
- `contract`

### 3.2. Entidades relacionadas
- `customer`
- `service_catalog_item`
- `contract_service`
- `contract_service_schedule`
- `contract_fiscal_profile`
- `contract_billing_contact`
- `contract_note`
- `contract_attachment` (opcional)
- `process_instance`
- `process_step_execution`

### 3.3. Escopo tenant-safe
Todas as entidades devem nascer e operar com:
- `company_id`
- `created_by`
- `updated_by`
- trilha de auditoria

---

## 4. Processo BPMN de alto nível

## Fluxo: Novo Contrato

1. iniciar processo
2. identificar cliente
3. definir serviços contratados
4. definir periodicidade, vencimento e competência
5. definir dados fiscais e retenções
6. incluir observações adicionais
7. definir faturamento e cobrança
8. revisar e confirmar
9. gerar contrato / registrar artefatos iniciais
10. concluir instância

### Possíveis gatilhos de start
- manual por usuário
- rotina interna
- conversão de proposta aprovada
- evento externo/integrado

---

## 5. Shell padrão da experiência

O processo deve rodar dentro de uma **tela-shell padrão** com:

- cabeçalho da instância
- status do processo
- barra de progresso por step
- step atual em destaque
- painel de contexto do contrato
- área de conteúdo do step
- abertura contextual de modal/drawer quando necessário
- ações de:
  - salvar e continuar depois
  - avançar
  - voltar
  - cancelar
  - concluir

### Dados visíveis no cabeçalho
- código da instância
- tenant/empresa
- versão do processo
- cliente selecionado
- status do contrato
- step atual

---

## 6. Modelo de abas recomendado

## 6.1. Abas core
Estas abas devem compor a tela principal do cadastro/edição de contrato.

1. **Resumo**
2. **Cliente**
3. **Serviços**
4. **Periodicidade**
5. **Fiscal**
6. **Cobrança**
7. **Observações**
8. **Revisão**

## 6.2. Abas capability
Podem ser habilitadas conforme tenant/produto/contexto.

Exemplos:
- **Documentos**
- **Anexos**
- **Aprovações**
- **Histórico do Processo**
- **Integrações**
- **Financeiro Derivado**

## 6.3. Abas de extensão
Usadas apenas quando houver necessidade específica controlada.

Exemplos:
- regras específicas de retenção
- campos regulatórios setoriais
- observações estruturadas por cliente
- composição complementar de faturamento

### Regra de governança
- aba core = estável e transversal
- aba capability = vinculada a recurso compartilhável
- aba extensão = controlada, tenant-safe e não pode contaminar o core

---

## 7. Metadados por aba

Cada aba deve possuir no mínimo:

- `tab_key`
- `label`
- `scope` = `core | capability | extension`
- `entity_type`
- `capability_key` quando aplicável
- `visible_when`
- `required_when`
- `order`
- `interaction_mode`
- `save_strategy` = `step` | `draft` | `finalize`

Exemplo conceitual:

```json
{
  "tab_key": "contract_services",
  "label": "Serviços",
  "scope": "core",
  "entity_type": "contract",
  "capability_key": "contract.service_items.manage",
  "visible_when": ["contract_started"],
  "required_when": ["before_review"],
  "order": 30,
  "interaction_mode": "form_inline",
  "save_strategy": "step"
}
```

---

## 8. Capabilities do processo Novo Contrato

### 8.1. Mapa principal

| Etapa | Capability | Tipo | Ação esperada |
|---|---|---|---|
| Identificar cliente | `customer.select_or_create` | humana | selecionar, editar ou criar cliente |
| Serviços contratados | `contract.service_items.manage` | humana | incluir serviços e valores |
| Periodicidade | `contract.schedule.configure` | humana | definir recorrência, vencimento e competência |
| Fiscal | `contract.tax.configure` | humana | configurar retenções e dados fiscais |
| Observações | `contract.notes.capture` | humana/opcional | incluir observações adicionais |
| Cobrança | `contract.billing_contacts.configure` | humana | definir responsáveis e canais |
| Revisão | `contract.review.summary` | humana | revisar consistência |
| Geração final | `contract.create_or_publish` | automática/humana | persistir contrato e disparos iniciais |

### 8.2. Capabilities auxiliares
- `service_catalog.select_or_create`
- `fiscal_profile.resolve_defaults`
- `billing_channel.resolve_defaults`
- `proposal.import_approved_items`
- `process.audit.log_step`

---

## 9. Detalhamento step a step

## Step 1 — Identificar cliente

### Pergunta operacional
- cliente existente ou cliente novo?

### Capability principal
- `customer.select_or_create`

### Modos de interação possíveis
- `form_inline` para busca/seleção
- `modal` para criar cliente
- `drawer` para editar cliente existente

### Aba principal
- `Cliente`

### Comportamento recomendado
- se cliente existente: buscar e selecionar
- se editar: abrir edição contextual sem sair da instância
- se novo: abrir cadastro já com tipo `cliente` pré-marcado

### Persistência
- salva vínculo `contract.customer_id`
- registra no contexto da instância

---

## Step 2 — Serviços contratados

### Capability principal
- `contract.service_items.manage`

### Capability auxiliar
- `service_catalog.select_or_create`

### Aba principal
- `Serviços`

### Modos de interação
- `form_inline` para grid/lista dos serviços do contrato
- `modal` para cadastrar novo serviço
- `drawer` para editar serviço de catálogo

### Regras
- permitir importar serviços da proposta aprovada, se houver
- permitir incluir valor por serviço
- permitir quantidade/unidade quando fizer sentido

### Persistência
- cria/atualiza `contract_service`

---

## Step 3 — Periodicidade, vencimento e competência

### Capability principal
- `contract.schedule.configure`

### Aba principal
- `Periodicidade`

### Modo de interação
- `form_inline`

### Regras
- configurar por serviço ou por bloco de serviços
- permitir recorrência mensal, bimestral, trimestral, avulsa etc.
- permitir competência e regra de vencimento

### Persistência
- cria/atualiza `contract_service_schedule`

---

## Step 4 — Dados fiscais e retenções

### Capability principal
- `contract.tax.configure`

### Aba principal
- `Fiscal`

### Modo de interação
- `form_inline`
- `modal` para regras fiscais avançadas, se necessário

### Regras
- retenções por serviço ou contrato
- defaults por tenant
- campos específicos por natureza do serviço

### Persistência
- cria/atualiza `contract_fiscal_profile`

---

## Step 5 — Observações adicionais

### Capability principal
- `contract.notes.capture`

### Aba principal
- `Observações`

### Modo de interação
- pergunta inicial inline: há observações?
- se sim, abre bloco expandido ou aba habilitada

### Persistência
- cria/atualiza `contract_note`

---

## Step 6 — Faturamento e cobrança

### Capability principal
- `contract.billing_contacts.configure`

### Aba principal
- `Cobrança`

### Modo de interação
- `form_inline`
- `modal` para adicionar contato/responsável

### Regras
- responsáveis por recebimento de nota
- responsáveis por recibo
- responsáveis por boleto/cobrança
- contatos por e-mail, WhatsApp e outros canais

### Persistência
- cria/atualiza `contract_billing_contact`

---

## Step 7 — Revisão e confirmação

### Capability principal
- `contract.review.summary`

### Aba principal
- `Revisão`

### Modo de interação
- `review_screen`

### Regras
- validar pendências por step
- exibir checklist de consistência
- permitir navegar de volta para abas pendentes

---

## Step 8 — Geração final

### Capability principal
- `contract.create_or_publish`

### Modo de interação
- `background_service` com confirmação humana final

### Ações esperadas
- consolidar rascunho em contrato
- gerar identificador final
- registrar trilha de auditoria
- disparar eventos derivados
- preparar integrações futuras (financeiro/fiscal/documental)

---

## 10. Interaction modes recomendados

| Interaction mode | Uso no Novo Contrato |
|---|---|
| `form_inline` | preenchimento principal do step |
| `modal` | criação rápida de cliente/serviço/contato |
| `drawer` | edição contextual sem perder a jornada |
| `review_screen` | etapa final de conferência |
| `background_service` | consolidação automática |

### Recomendação forte
O **padrão principal** deve ser:
- shell central
- step em destaque
- aba correspondente ativa
- modal/drawer só para ações satélite

Ou seja, evitar que o processo vire navegação solta pelo sistema.

---

## 11. Runtime e persistência

A instância deve gravar:

- `process_instance_id`
- `process_definition_key = contract.new`
- `process_version`
- `company_id`
- `user_id`
- `entity_type = contract`
- `entity_id` quando já existir
- `current_step_key`
- `status`
- `payload_draft`
- `started_at`
- `updated_at`

Cada execução de step deve gravar:
- `step_execution_id`
- `process_instance_id`
- `step_key`
- `capability_key`
- `interaction_mode`
- `started_at`
- `completed_at`
- `result_snapshot`
- `performed_by`

---

## 12. Multi-tenancy e customização controlada

### Regras obrigatórias
- toda instância nasce com `company_id`
- toda capability valida enablement do tenant
- toda aba adicional depende de regra explícita
- nenhuma aba de extensão pode substituir silenciosamente uma aba core sem governança

### O que pode variar por tenant
- labels
- campos opcionais
- ordem de certas abas
- defaults fiscais
- defaults de cobrança
- ativação de abas capability
- ativação de abas de extensão

### O que não deve variar sem decisão arquitetural
- contrato entre step e capability
- segurança multi-tenant
- persistência base do contrato
- trilha de auditoria

---

## 13. Decisão A/B/C para o processo Novo Contrato

### A) usar como está
Quando houver capability pronta e aderente

Exemplos potenciais:
- seleção/cadastro básico de cliente
- captura de observações
- histórico de processo

### B) customizar/estender
Quando a capability existir, mas faltar:
- default fiscal
- modelagem por serviço
- composição de cobrança
- importação da proposta aprovada
- regras por tenant

### C) criar nova capability
Quando não houver aderência suficiente

Exemplos prováveis:
- `contract.schedule.configure`
- `contract.billing_contacts.configure`
- `contract.create_or_publish`
- registry de abas do contrato

---

## 14. Backlog derivado imediato

Este desenho sugere como próximos itens estruturantes:

1. modelar a entidade `contract` e agregados
2. modelar `process_instance` e `step_execution` para runtime BPMN
3. criar registry de tabs do contrato
4. definir capabilities do domínio de contrato
5. desenhar shell UI do processo Novo Contrato
6. decidir o que reaproveita do cadastro de favorecidos/clientes
7. decidir o que reaproveita do cadastro de serviços

---

## 15. Conclusão

O fluxo **Novo Contrato** é um excelente piloto para a nova arquitetura do APP32 porque combina:

- BPMN como runtime real
- capability-first
- composição por abas
- multi-tenancy
- extensibilidade controlada
- reuso de módulos existentes
- possibilidade de automação futura

A recomendação é implementar esse caso como **referência canônica** do padrão:

**processo guiado + shell única + capabilities reutilizáveis + abas core/capability/extensão + persistência por instância**.
