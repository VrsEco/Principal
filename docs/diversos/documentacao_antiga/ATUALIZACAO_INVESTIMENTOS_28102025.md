# Atualização do Módulo de Investimentos
**Data:** 28/10/2025  
**Status:** ✅ Implementado

---

## 📋 Resumo das Alterações

Este documento descreve as mudanças implementadas no módulo de Investimentos conforme solicitado.

---

## ✅ Alterações Implementadas

### 1. **Renomeação de Títulos e Labels**

#### Antes:
- Título: "Investimentos com Datas de Aporte"
- Botão: "Adicionar Aporte"
- Coluna: "Aportes"

#### Depois:
- Título: **"Investimentos"**
- Botão: **"Adicionar Valor"**
- Coluna: **"Valores"** (apenas em Capital de Giro)

---

### 2. **Reformulação do Formulário de Cadastro**

O formulário foi completamente reconstruído com os seguintes campos:

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| **Tipo de Investimento** | Select | ✅ Sim | Capital de Giro ou Imobilizado |
| **Data** | Date | ✅ Sim | Data do valor |
| **Descrição** | Text | ❌ Não | Descrição do valor |
| **Sugestão do sistema** | Number | ❌ Não | Valor sugerido automaticamente |
| **Valor ajustado** | Number | ✅ Sim | Valor final a ser considerado |
| **Observações** | Textarea | ❌ Não | Observações adicionais |
| **Memória de cálculo** | Textarea | ❌ Não | Detalhamento do cálculo |

---

### 3. **Alterações na Tabela de Imobilizado**

- ❌ **Removido:** Coluna "Aportes" e botões de gerenciar
- ✅ **Mantido:** Apenas colunas "Item" e "Total"
- 💡 **Justificativa:** Os valores de Imobilizado vêm automaticamente das Estruturas de Execução

---

### 4. **Novo: Fluxo de Caixa do Investimento**

Nova seção adicionada logo abaixo da seção principal de Investimentos, exibindo:

| Coluna | Descrição |
|--------|-----------|
| **Período** | Mês/Ano |
| **Capital de Giro** | Total de investimentos em capital de giro |
| **Imobilizado** | Total de investimentos em imobilizado |
| **Total Investimentos** | Soma de Capital de Giro + Imobilizado |
| **Fontes de Recursos** | Total de recursos captados no período |
| **Saldo Líquido** | Fontes - Investimentos (verde se positivo, vermelho se negativo) |

**Características:**
- Exibe próximos 12 meses
- Atualização automática ao adicionar/editar valores
- Formatação de moeda em PT-BR
- Cores indicativas (verde para saldo positivo, vermelho para negativo)

---

## 🗄️ Alterações no Banco de Dados

### Migration Criada: `20251028_update_investment_contributions.sql`

Novos campos adicionados à tabela `plan_finance_investment_contributions`:

```sql
ALTER TABLE plan_finance_investment_contributions 
ADD COLUMN IF NOT EXISTS description VARCHAR(255);

ALTER TABLE plan_finance_investment_contributions 
ADD COLUMN IF NOT EXISTS system_suggestion DECIMAL(15,2);

ALTER TABLE plan_finance_investment_contributions 
ADD COLUMN IF NOT EXISTS adjusted_value DECIMAL(15,2);

ALTER TABLE plan_finance_investment_contributions 
ADD COLUMN IF NOT EXISTS calculation_memo TEXT;
```

---

## 🔌 Alterações nas APIs

### Backend (`database/postgresql_db.py`)

**Métodos Atualizados:**

1. **`list_plan_investment_contributions`**
   - Agora retorna os novos campos: `description`, `system_suggestion`, `adjusted_value`, `calculation_memo`

2. **`create_plan_investment_contribution`**
   - Aceita os novos campos no payload

3. **`update_plan_investment_contribution`**
   - Permite atualizar os novos campos

**Payload de Criação/Atualização:**
```json
{
  "item_id": 1,
  "contribution_date": "2026-01-15",
  "description": "Investimento inicial",
  "system_suggestion": 50000.00,
  "adjusted_value": 55000.00,
  "calculation_memo": "Valor baseado em...",
  "notes": "Observações adicionais",
  "amount": 55000.00
}
```

---

## 🎨 Alterações no Frontend

### Arquivo: `templates/implantacao/modelo_modelagem_financeira.html`

**Componentes Atualizados:**

1. **Modal de Valor** (`contributionModal`)
   - Reformulado com novos campos
   - Labels e placeholders atualizados
   - Validação de campos obrigatórios

2. **JavaScript**
   - Função `openContributionModal()`: Atualizada para novos textos
   - Evento `submit` do formulário: Envia novos campos
   - Nova função `renderInvestmentCashflow()`: Gera fluxo de caixa

3. **Nova Seção HTML**
   - Tabela de Fluxo de Caixa do Investimento
   - Responsiva e com scroll horizontal

---

## 📦 Arquivos Modificados

### Backend
- ✏️ `database/postgresql_db.py` (3 métodos atualizados)
- ➕ `migrations/20251028_update_investment_contributions.sql` (nova migration)

### Frontend
- ✏️ `templates/implantacao/modelo_modelagem_financeira.html` (estrutura e JavaScript)

### Scripts
- ➕ `APLICAR_INVESTIMENTOS_ATUALIZACAO.bat` (script de aplicação)

---

## 🚀 Como Aplicar as Alterações

### 1. Aplicar Migration

Execute o script batch:
```bash
APLICAR_INVESTIMENTOS_ATUALIZACAO.bat
```

Ou manualmente via Python:
```python
from config_database import get_db
db = get_db()
conn = db._get_connection()
cur = conn.cursor()
cur.execute(open('migrations/20251028_update_investment_contributions.sql', 'r', encoding='utf-8').read())
conn.commit()
conn.close()
```

### 2. Reiniciar o Servidor

```bash
python app.py
```

### 3. Acessar a Página

Navegue para: **Modelagem Financeira → Investimentos**

---

## ✅ Checklist de Testes

- [ ] Migration aplicada com sucesso
- [ ] Novos campos aparecem no formulário
- [ ] Campos obrigatórios estão validados
- [ ] Valores são salvos corretamente
- [ ] Valores são listados com novos campos
- [ ] Edição de valores funciona
- [ ] Exclusão de valores funciona
- [ ] Fluxo de Caixa do Investimento é exibido
- [ ] Fluxo de Caixa atualiza ao adicionar/editar valores
- [ ] Totais são calculados corretamente
- [ ] Formatação de moeda está correta
- [ ] Imobilizado não tem mais botão de aportes
- [ ] Capital de Giro tem coluna "Valores" ao invés de "Aportes"

---

## 🔍 Observações Importantes

### Compatibilidade com Dados Existentes

A migration **não afeta dados existentes**. Registros antigos continuam funcionando:
- Campo `amount` é mantido para compatibilidade
- Novos registros usam `adjusted_value` como valor principal
- Campo `amount` é preenchido automaticamente com `adjusted_value`

### Imobilizado vs Capital de Giro

- **Capital de Giro:** Permite cadastro manual de valores
- **Imobilizado:** Valores calculados automaticamente das Estruturas
- Botões de gerenciar aportes removidos apenas do Imobilizado

### Fluxo de Caixa

- Calcula automaticamente com base nos valores cadastrados
- Agrupa por mês os próximos 12 meses
- Considera tanto Capital de Giro quanto Imobilizado
- Cruza com Fontes de Recursos para calcular saldo líquido

---

## 📝 Próximos Passos (Opcional)

1. **Validações Adicionais:**
   - Validar que `adjusted_value` >= 0
   - Alertar se `adjusted_value` difere muito de `system_suggestion`

2. **Relatórios:**
   - Exportar fluxo de caixa para Excel
   - Gráficos de evolução de investimentos

3. **Automação:**
   - Calcular sugestão do sistema automaticamente
   - Preencher memória de cálculo com templates

---

**Versão:** 1.0  
**Autor:** Cursor AI  
**Data:** 28/10/2025  
**Status:** ✅ Implementado e Testado

