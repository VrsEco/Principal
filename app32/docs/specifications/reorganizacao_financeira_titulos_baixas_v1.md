# Reorganização Financeira — Títulos, Baixas, Correções, Rateios e Ledger

## 1. Objetivo deste documento

Materializar a arquitetura alvo para a reorganização do Financeiro oficial, consolidando:

1. modelo de dados proposto em SQLAlchemy;
2. desenho das migrations;
3. contratos JSON de API;
4. fluxo operacional da baixa com principal e correção separados;
5. plano de implementação por commits;
6. vínculo com os cards já existentes em `AA.J.31 (Produção)`.

Este documento é a base técnica para a evolução dos conceitos:

- **Agendamentos** → **Títulos Financeiros**
- **Lançamentos** → **Baixas**

Sem perder compatibilidade gradual com a base atual.

---

## 2. Premissas obrigatórias

- Stack oficial: **Python + Flask + PostgreSQL**
- Multi-tenancy obrigatório com `company_id`
- Sem lógica de negócio em rota
- Relatórios contábeis e dashboards podem compor dados de fontes distintas
- Extrato bancário mostra o **valor total financeiro movimentado**
- Tela do Título e relatórios analíticos mostram a **decomposição por componente**
- `draft` e `cancelled` não entram nos relatórios contábeis
- `open`, `partial` e `settled` entram
- `forecast` entra apenas em relatórios projetados, nunca em relatórios contábeis oficiais

---

## 3. Relação com cards do projeto AA.J.31

Os cards já criados para esta frente continuam válidos:

- `AA.J.31.1515` — Arquitetura alvo e glossário
- `AA.J.31.1516` — Modelo de dados
- `AA.J.31.1517` — Fluxo operacional
- `AA.J.31.1518` — Motor de cálculo
- `AA.J.31.1519` — Relatórios e dashboards
- `AA.J.31.1520` — Migração e compatibilidade
- `AA.J.31.1521` — UX e nomenclatura
- `AA.J.31.1522` — QA, auditoria e deploy

### Mapeamento deste documento
- seções **4 a 8** → `1516`
- seções **9 a 11** → `1517` e `1518`
- seções **12 e 13** → `1519`
- seção **14** → `1520`
- seção **15** → `1521`
- seção **16** → `1522`

---

## 4. Visão conceitual da solução

## 4.1 Entidades principais

### Título Financeiro
Representa a obrigação/direito original.

### Baixa
Representa o evento financeiro efetivo no banco/caixa.

### Componentes da Baixa
Representam a decomposição do valor total pago/recebido:
- principal
- correção monetária
- juros
- multa
- desconto
- ajuste manual

### Ajustes do Título
Representam valores gerados sobre o título ao longo do tempo:
- correção monetária
- juros
- multa
- desconto
- writeoff

### Ledger do Título
Representa a memória oficial e auditável da evolução do título.

---

## 5. Modelo de dados alvo — SQLAlchemy

> Observação: os trechos abaixo são **contratos de modelagem**. A implementação real pode ser distribuída entre `models/financial.py` e novos módulos especializados, preservando convenções do repositório.

## 5.1 Evolução do `FinancialSchedule` para Título Financeiro

### Estratégia recomendada
Não renomear a tabela imediatamente em produção.

### Fase transitória
- manter `financial_schedules`
- manter o model `FinancialSchedule`
- adotar semanticamente o conceito **Título Financeiro**
- introduzir alias e nomenclatura de UI/API gradualmente

### Campos obrigatórios adicionais/revisados
- `status` restrito a: `draft`, `open`, `partial`, `settled`, `cancelled`, `forecast`
- `principal_amount` como alias semântico de `template_amount`
- `competence_date`
- `due_date` semântico baseado em `first_due_date` / `next_due_date`
- `correction_rule_id`
- `discount_rule_id`

### Exemplo de shape alvo

```python
class FinancialTitle(db.Model):
    __tablename__ = "financial_schedules"  # transição controlada

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)

    schedule_code = db.Column(db.String(50), nullable=False, index=True)
    entry_type = db.Column(db.String(20), nullable=False, index=True)  # payable / receivable
    movement_nature = db.Column(db.String(10), nullable=False, index=True)  # debit / credit
    status = db.Column(db.String(20), nullable=False, default="open", index=True)

    description = db.Column(db.String(255), nullable=False)
    counterparty_id = db.Column(db.Integer, db.ForeignKey("financial_counterparties.id"), index=True)

    template_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)  # principal original
    competence_date = db.Column(db.Date, nullable=False, index=True)
    first_due_date = db.Column(db.Date, nullable=False, index=True)
    next_due_date = db.Column(db.Date, index=True)

    correction_index_id = db.Column(db.Integer, db.ForeignKey("financial_correction_indexes.id"))
    discount_rule_id = db.Column(db.Integer, db.ForeignKey("financial_discount_rules.id"))

    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
```

---

## 5.2 Baixas — manter `FinancialSettlement` como base oficial

### Estratégia
Manter `financial_settlements` como tabela base da Baixa.

### Evolução obrigatória
Adicionar o valor bruto explícito e reforçar o vínculo com o título.

```python
class FinancialSettlement(db.Model):
    __tablename__ = "financial_settlements"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id"), index=True)
    financial_schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id"), index=True)

    settlement_code = db.Column(db.String(50), nullable=False, index=True)
    settlement_date = db.Column(db.Date, nullable=False, index=True)
    settlement_status = db.Column(db.String(20), nullable=False, default="posted", index=True)
    settlement_type = db.Column(db.String(30), nullable=False, default="manual", index=True)

    principal_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    interest_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    penalty_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    fee_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    other_adjustments_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    gross_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    bank_account_id = db.Column(db.Integer, db.ForeignKey("financial_bank_accounts.id"), index=True)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
```

### Regra
`gross_amount` deve representar o total movimentado no banco e deve ser consistente com a soma algébrica dos componentes da baixa.

---

## 5.3 Nova tabela `financial_settlement_components`

Representa a decomposição oficial da Baixa.

```python
SETTLEMENT_COMPONENT_TYPES = (
    "principal",
    "monetary_correction",
    "interest",
    "fine",
    "discount",
    "manual_adjustment",
)


class FinancialSettlementComponent(db.Model):
    __tablename__ = "financial_settlement_components"
    __table_args__ = (
        db.CheckConstraint(
            f"component_type IN {SETTLEMENT_COMPONENT_TYPES}",
            name="ck_financial_settlement_components_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_settlement_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_settlements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    financial_schedule_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    component_type = db.Column(db.String(30), nullable=False, index=True)
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    competence_date = db.Column(db.Date, nullable=False, index=True)
    due_date = db.Column(db.Date, index=True)
    source = db.Column(db.String(20), nullable=False, default="system", index=True)  # system / user

    origin_adjustment_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_title_adjustments.id", ondelete="SET NULL"),
        index=True,
    )
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
```

### Regra obrigatória
A soma algébrica dos componentes deve bater com `gross_amount`.

---

## 5.4 Nova tabela `financial_title_adjustments`

Representa os ajustes autônomos do título.

```python
TITLE_ADJUSTMENT_TYPES = (
    "monetary_correction",
    "interest",
    "fine",
    "discount",
    "writeoff",
)

TITLE_ADJUSTMENT_STATUSES = (
    "open",
    "partial",
    "settled",
    "cancelled",
)


class FinancialTitleAdjustment(db.Model):
    __tablename__ = "financial_title_adjustments"
    __table_args__ = (
        db.CheckConstraint(
            f"adjustment_type IN {TITLE_ADJUSTMENT_TYPES}",
            name="ck_financial_title_adjustments_type",
        ),
        db.CheckConstraint(
            f"status IN {TITLE_ADJUSTMENT_STATUSES}",
            name="ck_financial_title_adjustments_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_schedule_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_schedules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    adjustment_type = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="open", index=True)

    calculation_date = db.Column(db.Date, nullable=False, index=True)
    competence_date = db.Column(db.Date, nullable=False, index=True)
    due_date_reference = db.Column(db.Date, index=True)

    base_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    generated_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    settled_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    open_amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    rule_snapshot_json = db.Column(JSONB, nullable=False, default=dict)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)
```

### Regras
- todo ajuste nasce com `generated_amount`
- baixa parcial atualiza `settled_amount` e `open_amount`
- ajuste pode ser liquidado integralmente por uma ou mais Baixas

---

## 5.5 Nova tabela `financial_title_adjustment_allocations`

Rateio próprio dos ajustes.

```python
class FinancialTitleAdjustmentAllocation(db.Model):
    __tablename__ = "financial_title_adjustment_allocations"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_title_adjustment_id = db.Column(
        db.Integer,
        db.ForeignKey("financial_title_adjustments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chart_account_id = db.Column(db.Integer, db.ForeignKey("financial_chart_accounts.id"), index=True)
    cost_center_id = db.Column(db.Integer, db.ForeignKey("financial_cost_centers.id"), index=True)
    budget_document_id = db.Column(db.Integer, db.ForeignKey("financial_budget_documents.id"), index=True)

    percentage = db.Column(db.Numeric(9, 4))
    amount = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
```

### Regra recomendada
- ajuste herda o rateio do principal por padrão
- usuário pode sobrescrever

---

## 5.6 Evolução do ledger atual

Hoje existe `financial_title_calculation_logs`.

### Recomendação
Evoluir semanticamente para ledger estruturado:

```python
TITLE_LEDGER_EVENT_TYPES = (
    "adjustment_generated",
    "settlement_posted",
    "settlement_reversed",
    "adjustment_recalculated",
    "manual_override",
)


class FinancialTitleCalculationLedger(db.Model):
    __tablename__ = "financial_title_calculation_logs"  # transição preservando tabela atual

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    financial_schedule_id = db.Column(db.Integer, db.ForeignKey("financial_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    financial_entry_id = db.Column(db.Integer, db.ForeignKey("financial_entries.id", ondelete="SET NULL"), index=True)
    financial_settlement_id = db.Column(db.Integer, db.ForeignKey("financial_settlements.id", ondelete="SET NULL"), index=True)

    event_type = db.Column(db.String(40), nullable=False, index=True)
    calculation_date = db.Column(db.Date, nullable=False, index=True)

    principal_before = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    adjustments_open_before = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total_due_before = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    principal_settled_now = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    adjustments_settled_now = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    discount_now = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    principal_after = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    adjustments_open_after = db.Column(db.Numeric(14, 2), nullable=False, default=0)
    total_due_after = db.Column(db.Numeric(14, 2), nullable=False, default=0)

    metadata_json = db.Column(JSONB, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
```

---

## 6. Migrations recomendadas

## 6.1 Migration 1 — componentes da baixa

### Nome sugerido
`20260420_0900_create_financial_settlement_components.py`

### Entregas
- criar tabela `financial_settlement_components`
- índices:
  - `(company_id, financial_settlement_id)`
  - `(company_id, financial_schedule_id)`
  - `(company_id, component_type, competence_date)`

---

## 6.2 Migration 2 — ajustes do título

### Nome sugerido
`20260420_1000_create_financial_title_adjustments.py`

### Entregas
- criar tabela `financial_title_adjustments`
- constraints de tipo/status
- índices por data, company e title

---

## 6.3 Migration 3 — rateio dos ajustes

### Nome sugerido
`20260420_1100_create_financial_title_adjustment_allocations.py`

### Entregas
- criar tabela `financial_title_adjustment_allocations`
- índices por ajuste e `company_id`

---

## 6.4 Migration 4 — evolução de baixa

### Nome sugerido
`20260420_1200_add_gross_amount_to_financial_settlements.py`

### Entregas
- adicionar `gross_amount` em `financial_settlements`
- backfill:
  - `principal_amount + interest_amount + penalty_amount + fee_amount + other_adjustments_amount - discount_amount`

---

## 6.5 Migration 5 — evolução do ledger

### Nome sugerido
`20260420_1300_expand_financial_title_calculation_logs_to_ledger.py`

### Entregas
- adicionar colunas estruturadas de antes/agora/depois
- manter retrocompatibilidade do conteúdo já salvo

---

## 6.6 Migration 6 — backfill

### Nome sugerido
`20260420_1400_backfill_settlement_components_and_adjustments.py`

### Entregas
- criar componentes históricos a partir de `financial_settlements`
- materializar ajustes históricos mínimos quando houver snapshot suficiente
- marcar registros sem granularidade histórica como:
  - `source = "legacy_backfill"`
  - `metadata_json["backfill_precision"] = "partial"`

---

## 7. Contratos de API

## 7.1 Buscar detalhe do Título

### `GET /api/financial/titles/<id>`

### Response

```json
{
  "id": 34,
  "company_id": 7,
  "title_code": "TIT-000034",
  "entry_type": "payable",
  "status": "partial",
  "description": "Aluguel Abril/2026",
  "counterparty": {
    "id": 19,
    "name": "Fornecedor XPTO"
  },
  "principal_amount": 1000.0,
  "competence_date": "2026-04-01",
  "due_date": "2026-04-10",
  "balances": {
    "principal_open": 500.0,
    "adjustments_open": 30.0,
    "total_open": 530.0
  },
  "allocations": [],
  "adjustments": [],
  "settlements": [],
  "ledger": []
}
```

---

## 7.2 Simular composição da baixa

### `POST /api/financial/titles/<id>/settlements/simulate`

### Request

```json
{
  "company_id": 7,
  "settlement_date": "2026-04-20",
  "gross_amount": 300.0,
  "mode": "editable",
  "composition": {
    "principal": 270.0,
    "monetary_correction": 30.0,
    "interest": 0.0,
    "fine": 0.0,
    "discount": 0.0,
    "manual_adjustment": 0.0
  }
}
```

### Response

```json
{
  "title_id": 34,
  "settlement_date": "2026-04-20",
  "before": {
    "principal_open": 800.0,
    "adjustments_open": 30.0,
    "total_due": 830.0
  },
  "composition": {
    "principal": 270.0,
    "monetary_correction": 30.0,
    "interest": 0.0,
    "fine": 0.0,
    "discount": 0.0,
    "manual_adjustment": 0.0,
    "gross_amount": 300.0
  },
  "after": {
    "principal_open": 530.0,
    "adjustments_open": 0.0,
    "total_open": 530.0
  },
  "allocation_preview": {
    "principal": [],
    "adjustments": []
  }
}
```

---

## 7.3 Efetivar baixa

### `POST /api/financial/titles/<id>/settlements`

### Request

```json
{
  "company_id": 7,
  "settlement_date": "2026-04-20",
  "bank_account_id": 3,
  "gross_amount": 300.0,
  "components": [
    {
      "component_type": "principal",
      "amount": 270.0,
      "competence_date": "2026-04-01",
      "due_date": "2026-04-10",
      "source": "user"
    },
    {
      "component_type": "monetary_correction",
      "amount": 30.0,
      "competence_date": "2026-04-20",
      "due_date": "2026-04-20",
      "source": "user",
      "origin_adjustment_id": 81
    }
  ],
  "metadata_json": {
    "notes": "Baixa parcial negociada"
  }
}
```

### Response

```json
{
  "settlement": {
    "id": 905,
    "settlement_code": "LIQ-000905",
    "gross_amount": 300.0
  },
  "components": [
    {
      "component_type": "principal",
      "amount": 270.0
    },
    {
      "component_type": "monetary_correction",
      "amount": 30.0
    }
  ],
  "title_balances": {
    "principal_open": 530.0,
    "adjustments_open": 0.0,
    "total_open": 530.0
  },
  "ledger_event_id": 1201
}
```

---

## 7.4 Buscar memória de cálculo do Título

### `GET /api/financial/titles/<id>/ledger`

### Response

```json
{
  "title": {
    "id": 34,
    "title_code": "TIT-000034"
  },
  "balances": {
    "principal_open": 530.0,
    "adjustments_open": 0.0,
    "total_open": 530.0
  },
  "events": [
    {
      "id": 1201,
      "event_type": "settlement_posted",
      "calculation_date": "2026-04-20",
      "principal_before": 800.0,
      "adjustments_open_before": 30.0,
      "total_due_before": 830.0,
      "principal_settled_now": 270.0,
      "adjustments_settled_now": 30.0,
      "discount_now": 0.0,
      "principal_after": 530.0,
      "adjustments_open_after": 0.0,
      "total_due_after": 530.0
    }
  ]
}
```

---

## 8. Regras de negócio obrigatórias

## 8.1 Saldos

Todo Título deve expor sempre:
- `principal_open`
- `adjustments_open`
- `total_open`

Nunca apenas um “saldo total” solto.

## 8.2 Composição da baixa

Toda Baixa deve gravar a decomposição.

### Validações
- soma dos componentes = `gross_amount`
- principal liquidado <= principal aberto
- correção/juros/multa liquidados <= ajustes abertos elegíveis
- desconto não pode gerar saldo inconsistente

## 8.3 Competência da correção

A correção liquidada deve poder usar:
- `competence_date` da data da baixa
- `due_date` da data-base usada no cálculo

## 8.4 Rateio

### Principal
Usa rateio principal do Título.

### Ajuste
Herda o rateio principal por padrão, com possibilidade de override.

## 8.5 Extrato bancário

Mostra o total financeiro movimentado:
- `gross_amount`

## 8.6 DRE e relatórios contábeis

Mostram a decomposição:
- principal na conta principal
- correção/juros/multa em contas financeiras apropriadas
- desconto em conta própria

---

## 9. Fluxo operacional da Baixa

## 9.1 Passo 1 — carregar posição do Título

Sistema calcula:
- principal em aberto
- ajustes abertos até a data da baixa
- total exigível

## 9.2 Passo 2 — sugerir composição

Usuário informa:
- valor total pago/recebido

Sistema sugere:
- principal
- correção monetária
- juros
- multa
- desconto

## 9.3 Passo 3 — override do usuário

Usuário pode alterar os componentes ainda em aberto.

## 9.4 Passo 4 — persistência

Persistir em ordem:
1. baixa
2. componentes da baixa
3. liquidação dos ajustes afetados
4. recalcular saldo do título
5. registrar ledger

---

## 10. Serviço central recomendado

## 10.1 `FinancialTitleBalanceService`
Responsável por:
- calcular principal aberto
- calcular ajustes abertos
- consolidar saldo total

## 10.2 `FinancialTitleAdjustmentService`
Responsável por:
- gerar correção
- recalcular multa/juros
- manter ajuste aberto/parcial/liquidado

## 10.3 `FinancialSettlementCompositionService`
Responsável por:
- simular composição da baixa
- validar composição
- gerar componentes

## 10.4 `FinancialTitleLedgerService`
Responsável por:
- criar eventos do ledger
- materializar snapshots antes/depois

---

## 11. Estratégia de UI

## 11.1 Tela do Título

Exibir:
- principal original
- principal em aberto
- ajustes em aberto
- total exigível
- memória de cálculo
- baixas realizadas

## 11.2 Tela da Baixa

Exibir antes de confirmar:
- saldo principal
- saldo de correção
- total exigível
- valor informado da baixa
- grade editável de decomposição

### Exemplo
- aplicar em principal
- aplicar em correção
- aplicar em multa
- aplicar em juros
- aplicar desconto

---

## 12. Estratégia de relatórios

## 12.1 Extrato bancário

Fonte principal:
- `financial_settlements.gross_amount`

## 12.2 DRE contábil

Fontes combinadas:
- principal dos títulos/baixas
- componentes financeiros das baixas
- rateios de principal
- rateios dos ajustes

## 12.3 Memória analítica

Fonte:
- ledger do título
- componentes da baixa
- ajustes do título

---

## 13. Estratégia de migração e compatibilidade

## 13.1 Fase transitória

Durante a migração:
- manter tabelas atuais
- enriquecer com novas tabelas/colunas
- manter APIs antigas operando

## 13.2 Backfill

### Baixas históricas
Gerar componentes a partir dos campos agregados atuais:
- principal
- juros
- multa
- desconto
- ajustes diversos

### Ajustes históricos
Gerar apenas quando houver evidência suficiente.

### Precisão
Sempre marcar em `metadata_json`:
- origem do backfill
- nível de confiabilidade

---

## 14. Sequência recomendada de implementação por commit

## Commit 1 — base de persistência
**Mensagem sugerida:** `Cria componentes das baixas financeiras`

Entrega:
- model `FinancialSettlementComponent`
- migration correspondente
- testes unitários de criação e validação básica

## Commit 2 — ajustes autônomos
**Mensagem sugerida:** `Cria ajustes autonomos dos titulos financeiros`

Entrega:
- model `FinancialTitleAdjustment`
- migration
- índices e constraints

## Commit 3 — rateio dos ajustes
**Mensagem sugerida:** `Cria rateio proprio para ajustes financeiros`

Entrega:
- model `FinancialTitleAdjustmentAllocation`
- herança inicial do rateio principal

## Commit 4 — evolução da baixa
**Mensagem sugerida:** `Adiciona valor bruto e composicao das baixas`

Entrega:
- `gross_amount` em `financial_settlements`
- validação da soma dos componentes

## Commit 5 — motor de saldo
**Mensagem sugerida:** `Centraliza saldo de principal e ajustes dos titulos`

Entrega:
- `FinancialTitleBalanceService`
- cálculo oficial de saldo aberto

## Commit 6 — motor de ajustes
**Mensagem sugerida:** `Centraliza geracao de correcoes e ajustes dos titulos`

Entrega:
- `FinancialTitleAdjustmentService`
- simulação de correção/multa/juros

## Commit 7 — composição da baixa
**Mensagem sugerida:** `Permite baixa com principal e correcao separados`

Entrega:
- `FinancialSettlementCompositionService`
- endpoint de simulação
- endpoint de efetivação

## Commit 8 — ledger estruturado
**Mensagem sugerida:** `Evolui memoria de calculo para ledger estruturado`

Entrega:
- expansão da tabela atual
- snapshots antes/agora/depois

## Commit 9 — UI do título
**Mensagem sugerida:** `Exibe saldo analitico e memoria do titulo financeiro`

Entrega:
- saldo principal
- saldo ajustes
- ledger visual

## Commit 10 — UI da baixa
**Mensagem sugerida:** `Exibe composicao editavel das baixas financeiras`

Entrega:
- simulador visual
- override do usuário

## Commit 11 — relatórios
**Mensagem sugerida:** `Separa principal e ajustes nos relatorios financeiros`

Entrega:
- DRE contábil
- extrato bancário consolidado
- visões analíticas

## Commit 12 — migração histórica
**Mensagem sugerida:** `Realiza backfill financeiro para componentes e ledger`

Entrega:
- scripts/migrations de backfill
- marcadores de precisão histórica

---

## 15. Recomendação final de execução

### Ordem obrigatória
1. persistência
2. saldo oficial
3. composição da baixa
4. ledger
5. interface
6. relatórios
7. backfill

### Motivo
Sem a decomposição oficial da baixa, o restante continua sendo inferência frágil.

---

## 16. Critérios de aceite globais

- toda operação financeira respeita `company_id`
- toda Baixa tem composição explícita
- todo Título expõe saldo de principal e saldo de ajustes
- correção financeira pode ser liquidada separadamente do principal
- extrato bancário exibe o total
- DRE e relatórios contábeis usam a decomposição
- ledger permite auditoria completa do antes/agora/depois
- migração histórica preserva rastreabilidade

---

## 17. Próximo passo recomendado

Implementar o **Commit 1** e o **Commit 2** em sequência:

1. `financial_settlement_components`
2. `financial_title_adjustments`

Esses dois passos destravam a base estrutural de toda a reorganização.
