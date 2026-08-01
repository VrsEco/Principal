# Arquitetura Oficial — Motor de Eventos, BPMS e Catálogo Unificado de Automações

Status: canônico  
Classe: SPEC
Atualizado em: 2026-08-01

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

## 11. Artefatos executáveis do BPMN

Os artefatos `IA`, `IN` e `OUT` são configurações especializadas associadas à atividade BPMN. Eles tornam explícita a intenção da modelagem, mas não substituem o motor nem os executores de domínio.

- `IA` solicita uma execução Sapiens/MCP governada pelo contrato da atividade;
- `IN` registra e correlaciona dados recebidos com uma instância;
- `OUT` solicita entrega de dados a um destino configurado;
- `POP`, `FORM` e `CHECK` compõem o contexto e os gates humanos da mesma atividade.

Regra de boundary:

```text
artefato define intenção e configuração
→ BPMS materializa a execução na instância
→ motor/dispatcher executa de forma idempotente
→ executor de domínio preserva a regra de negócio
→ BPMS recebe resultado e avalia a conclusão da atividade
```

O artefato nunca deve conter lógica financeira, fiscal ou contratual que pertença ao service de domínio.

## 12. Envelope mínimo da execução de artefato

Toda execução automática deve carregar:

- `company_id`;
- `process_instance_id`;
- `activity_execution_id`;
- `artifact_execution_id`;
- `artifact_type`;
- `artifact_version`;
- `correlation_id`;
- `idempotency_key`;
- `attempt`;
- timestamps e estado;
- request/output ou referência segura para payload volumoso;
- erro normalizado e decisão de retry/fallback.

O estado deve ser persistido antes e depois da chamada externa. Retry não pode duplicar efeitos já confirmados.

## 13. Fila humana derivada de exceções

Execuções automáticas não devem aparecer como atividades pessoais comuns. O BPMS cria ou reativa assignment humano somente quando ocorrer:

- human gate configurado;
- confidence abaixo do threshold;
- falha sem retry elegível;
- dado obrigatório ausente;
- aprovação ou revisão exigida;
- exceção de negócio devolvida pelo executor.

Essa projeção deve ser consumida tanto por `Meu Trabalho` quanto pelo Portal de Processos, preservando uma única fonte operacional de assignment por atividade.
