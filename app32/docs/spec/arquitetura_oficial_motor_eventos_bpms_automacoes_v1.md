# Arquitetura Oficial — Motor de Eventos, BPMS e Catálogo Unificado de Automações

Status: canônico  
Classe: SPEC

## 1. Objetivo

Definir a arquitetura oficial para:

- automações determinísticas do APP32;
- integração com BPMS;
- visibilidade unificada de automações para o usuário.

## 2. Decisão oficial

O APP32 deve operar com:

1. **motor corporativo de eventos e regras**;
2. **executores por domínio**;
3. **BPMS como orquestrador humano/exceção**;
4. **catálogo unificado de automações**.

## 3. Boundary oficial

### 3.1. Motor corporativo

Faz:

- escuta de eventos;
- avaliação de regras;
- despacho de ações;
- execução auditável;
- idempotência;
- reversão.

Não faz:

- cálculo de faturamento;
- cálculo fiscal;
- cálculo financeiro.

### 3.2. Executores por domínio

Executores oficiais:

- `ContractService`
- `BillingService`
- `FinancialService`
- `FiscalService`

## 4. Boundary oficial do BPMS

O BPMS faz:

- jornadas humanas;
- aprovações;
- pausas;
- retomadas;
- SLA;
- acompanhamento visual;
- exceções operacionais.

O BPMS não é a fonte primária de:

- recorrência contratual;
- faturamento estrutural;
- baixa financeira automática;
- cálculo fiscal.

## 5. Catálogo unificado de automações

Toda automação cadastrada deve aparecer no mesmo catálogo funcional.

Campos mínimos:

- `company_id`
- `automation_key`
- `automation_origin` = `bpms` | `event_engine`
- `domain_key`
- `entity_type`
- `entity_id`
- `trigger_event`
- `action_key`
- `execution_mode`
- `status`
- `next_execution_at`
- `last_execution_at`

## 6. Read model oficial

O front não deve ler tabelas de motor e BPMS separadamente.

Deve consumir um read model unificado, por exemplo:

- `automation_registry_view`

Fontes:

- regras/execuções do motor
- rotinas/processos do BPMS

## 7. Regras oficiais de UX

Na UI, o usuário deve ver:

- automação
- origem
- domínio
- gatilho
- próxima execução
- último resultado
- se exige aprovação

Sem exigir que ele saiba se veio do motor ou do BPMS.

## 8. Regra oficial para contratos

Para contratos:

- faturamento é **nativo do domínio**
- renovação é **nativa do domínio**
- BPMS pode apenas:
  - consumir eventos;
  - abrir exceções;
  - aprovar;
  - acompanhar

## 9. Regra oficial para financeiro

Satélites financeiros devem ser executados por política do domínio financeiro, disparada por evento.

Exemplo:

- `MAIN_TITLE_PARTIAL_SETTLEMENT`
- `MAIN_TITLE_FULL_SETTLEMENT`
- `COMPETENCE_REACHED`
- `MANUAL_RELEASE`

## 10. Ordem oficial de execução

1. evento nasce no domínio ou runtime;
2. motor avalia regras elegíveis;
3. motor chama executor do domínio;
4. se houver exceção humana, abre BPMS;
5. BPMS devolve evento de retorno;
6. motor conclui a execução.

