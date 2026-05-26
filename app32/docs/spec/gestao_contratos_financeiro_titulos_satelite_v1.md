# SPEC — Gestão de Contratos + Financeiro de Títulos Satélite

**Data:** 2026-05-26  
**Status:** decisão oficial  
**Escopo:** APP32 / Gestão Comercial / Gestão de Contratos

---

## 1. Decisões fechadas

- o **título principal** do contrato nasce no **valor bruto**;
- o faturamento nativo do contrato gera automaticamente o **título principal**;
- retenções e tributos vinculados ao contrato geram **títulos satélite** separados;
- o comportamento do satélite é definido por **política configurável**, não apenas pelo tipo;
- o default de `ISS retido` é:
  - `principal_effect_mode = partial_settlement_by_settlement`
  - `satellite_effect_mode = settle_by_settlement`
- algumas retenções podem ficar em aberto até:
  - liberação manual;
  - evento explícito.

---

## 2. Modelo oficial

### 2.1. Título principal

Fonte:

- `contract_native_billing`

Destino:

- `financial_schedule` com papel `main`

Características:

- bruto;
- one-time;
- vinculado ao contrato e à competência;
- base para baixa e compensações.

### 2.2. Títulos satélite

Destino:

- `financial_schedule` com papel `satellite`

Naturezas mínimas:

- `iss_withheld`
- `inss_withheld`
- `irrf_withheld`
- `pis_withheld`
- `cofins_withheld`
- `csll_withheld`
- `contractual_retention`
- `financial_retention`

### 2.3. Política do satélite

Tabela:

- `financial_satellite_policies`

Campos semânticos:

- natureza;
- efeito no principal;
- efeito no satélite;
- evento gatilho;
- escopo `full | proportional`;
- aplicação automática;
- contas de destino.

### 2.4. Vínculo hierárquico

Tabela:

- `financial_schedule_links`

Função:

- ligar título principal aos satélites;
- preservar árvore financeira;
- rastrear política aplicada.

### 2.5. Execução por evento

Tabela:

- `financial_satellite_executions`

Função:

- registrar a execução automática por baixa;
- manter idempotência;
- sustentar reversão futura;
- auditar compensações do principal e liquidação do satélite.

---

## 3. Regra de baixa por evento

Quando ocorre baixa no título principal:

1. o sistema identifica satélites vinculados;
2. calcula saldo aberto do principal e dos satélites;
3. avalia a política;
4. se elegível, cria:
   - compensação automática no principal, quando aplicável;
   - liquidação automática do satélite, quando aplicável;
5. grava `financial_satellite_execution`.

Regra prática do MVP:

- se o saldo aberto remanescente do principal for compatível com o total pendente dos satélites, o sistema pode inferir **recebimento líquido com retenção** e compensar o principal.

---

## 4. UX oficial

No contrato:

- aba **Financeiro**;
- card de parâmetros financeiros;
- card de regras automáticas dos satélites;
- card de títulos gerados;
- ação para gerar títulos a partir de competência sem integração financeira.

Na central financeira:

- o título continua sendo operado no módulo financeiro;
- o contrato apenas consolida a visão.

---

## 5. Guardrails

- multi-tenancy com `company_id` em tudo;
- sem lógica financeira em rota;
- geração de títulos no service;
- baixa automática com idempotência;
- contrato continua separado de fiscal e do ledger.
