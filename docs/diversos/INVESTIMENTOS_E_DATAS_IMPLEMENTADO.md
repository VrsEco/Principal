# ✅ Investimentos com Datas de Aporte - Implementado

**Data:** 25/10/2025  
**Status:** ✅ **Backend Completo** | 🔄 **Frontend Pendente**

---

## 🎯 Objetivo

Implementar sistema de cadastro de investimentos com múltiplas datas de aporte e geração automática de fluxos de caixa do negócio e dos sócios.

---

## ✅ O Que Foi Implementado

### **1. Nova Estrutura de Banco de Dados**

Criadas **4 novas tabelas** para suportar investimentos com datas:

#### Tabelas Criadas:

1. **`plan_finance_investment_categories`**
   - Armazena categorias: "Capital de Giro" e "Imobilizado"
   - Campos: `id`, `plan_id`, `category_type`, `category_name`, `display_order`

2. **`plan_finance_investment_items`**
   - Armazena itens de investimento (Caixa, Recebíveis, Estoques, etc)
   - Campos: `id`, `category_id`, `item_name`, `display_order`

3. **`plan_finance_investment_contributions`**
   - Armazena aportes com data e valor
   - Campos: `id`, `item_id`, `contribution_date`, `amount`, `notes`

4. **`plan_finance_funding_sources`**
   - Armazena fontes de recursos
   - Campos: `id`, `plan_id`, `source_type`, `contribution_date`, `amount`, `notes`

#### Estrutura de Categorias:

**Capital de Giro:**
- Caixa
- Recebíveis
- Estoques

**Imobilizado:**
- Instalações
- Máquinas e Equipamentos
- Outros Investimentos

**Fontes de Recursos:**
- Fornecedores
- Empréstimos e Financiamentos
- Aporte dos Sócios

---

### **2. Métodos de Banco de Dados Implementados**

#### Interface (`database/base.py`):

```python
# Categorias e Itens
get_plan_investment_categories(plan_id) -> List[Dict]
get_plan_investment_items(category_id) -> List[Dict]

# Aportes
list_plan_investment_contributions(item_id) -> List[Dict]
create_plan_investment_contribution(item_id, data) -> int
update_plan_investment_contribution(contribution_id, data) -> bool
delete_plan_investment_contribution(contribution_id) -> bool

# Fontes de Recursos
list_plan_funding_sources(plan_id) -> List[Dict]
create_plan_funding_source(plan_id, data) -> int
update_plan_funding_source(source_id, plan_id, data) -> bool
delete_plan_funding_source(source_id, plan_id) -> bool
```

#### Implementação PostgreSQL (`database/postgresql_db.py`):

Todos os métodos implementados com tratamento de erros e conexão adequada.

---

### **3. APIs REST Criadas**

**Arquivo:** `modules/pev/__init__.py`

#### Investimentos:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/implantacao/<plan_id>/finance/investment/contributions` | Criar aporte |
| PUT | `/api/implantacao/<plan_id>/finance/investment/contributions/<id>` | Atualizar aporte |
| DELETE | `/api/implantacao/<plan_id>/finance/investment/contributions/<id>` | Deletar aporte |

#### Fontes de Recursos:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/implantacao/<plan_id>/finance/funding_sources` | Listar fontes |
| POST | `/api/implantacao/<plan_id>/finance/funding_sources` | Criar fonte |
| PUT | `/api/implantacao/<plan_id>/finance/funding_sources/<id>` | Atualizar fonte |
| DELETE | `/api/implantacao/<plan_id>/finance/funding_sources/<id>` | Deletar fonte |

#### Getters:

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/implantacao/<plan_id>/finance/investment/categories` | Listar categorias |

---

## 🔄 Próximos Passos (Frontend)

### **1. Interface HTML**

Criar seção na página de modelagem financeira para:

1. **Cadastro de Aportes por Item:**
   - Selecionar item de investimento (Caixa, Recebíveis, etc)
   - Informar data do aporte
   - Informar valor
   - Permitir múltiplos aportes por item

2. **Cadastro de Fontes de Recursos:**
   - Tipo (Fornecedores / Empréstimos / Sócios)
   - Data do aporte
   - Valor
   - Observações

3. **Visualização em Planilha:**
   - Colunas: Total | Jan/2026 | Fev/2026 | Mar/2026...
   - Linhas: Categorias de Investimento
   - Exibir valores por mês

### **2. Cálculo de Fluxos de Caixa**

#### **Fluxo de Caixa do Negócio:**

Colunas:
- Fontes de Recursos (Fornecedores, Empréstimos, Sócios)
- Montagem/Aplicação do Investimento (Caixa, Estoques, Recebíveis, Ativo Imobilizado)
- Resultado do Negócio (Receita, (-) Custos Variáveis, (-) Despesas Variáveis, (=) Margem de Contribuição, (-) Custos Fixos, (-) Despesas Fixas, (=) Resultado Operacional, (-) Destinação de Resultados, (=) Resultado do Período)

#### **Fluxo de Caixa dos Sócios:**

Linhas:
- (-) Aporte dos Sócios no Mês
- (+) Distribuição Recebida no Mês
- (=) Resultado Líquido Acumulado no Mês
- (-) Saldo Acumulado

---

## 📋 Arquivos Criados/Modificados

### Novos Arquivos:
- `migrations/create_investment_contributions.sql`
- `migrations/seed_investment_defaults.sql`

### Arquivos Modificados:
- `database/base.py` - Adicionados métodos abstratos
- `database/postgresql_db.py` - Implementados métodos CRUD
- `modules/pev/__init__.py` - Criadas APIs REST

### Arquivos a Modificar:
- `templates/implantacao/modelo_modelagem_financeira.html` - Interface HTML
- `modules/pev/implantation_data.py` - Lógica de cálculo dos fluxos

---

## 🧪 Como Testar

### 1. Aplicar Migration:

```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus < migrations\create_investment_contributions.sql
```

### 2. Inicializar Categorias e Itens:

Criar script Python para inicializar as categorias e itens padrão para todos os plans.

### 3. Testar APIs:

```bash
# Listar categorias
curl http://localhost:5000/pev/api/implantacao/1/finance/investment/categories

# Criar aporte
curl -X POST http://localhost:5000/pev/api/implantacao/1/finance/investment/contributions \
  -H "Content-Type: application/json" \
  -d '{"item_id": 1, "contribution_date": "2026-01-15", "amount": 50000.00, "notes": "Aporte inicial"}'

# Listar fontes
curl http://localhost:5000/pev/api/implantacao/1/finance/funding_sources
```

---

## 💡 Estrutura de Dados

### Aporte de Investimento:
```json
{
  "item_id": 1,
  "contribution_date": "2026-01-15",
  "amount": 50000.00,
  "notes": "Descrição do aporte"
}
```

### Fonte de Recursos:
```json
{
  "source_type": "Aporte dos Sócios",
  "contribution_date": "2026-01-10",
  "amount": 200000.00,
  "notes": "Aporte inicial dos sócios"
}
```

---

## ✨ Diferenciais da Implementação

1. **Múltiplos Aportes:** Permite cadastrar vários aportes com datas diferentes para o mesmo item
2. **Tipagem Clara:** Separação entre Capital de Giro e Imobilizado
3. **Flexível:** Estrutura permite adicionar novos tipos sem alterar código
4. **Auditável:** Cada aporte tem data e observações
5. **Compatível:** Código funciona em PostgreSQL e SQLite (interface abstrata)

---

**Próximo Passo:** Criar interface HTML para cadastro e visualização em formato planilha.

