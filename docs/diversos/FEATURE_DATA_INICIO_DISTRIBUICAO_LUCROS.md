# Data de Início da Distribuição de Lucros

## 📋 Descrição da Feature

Adicionada funcionalidade para registrar a **data de início do pagamento da distribuição de lucros** no cadastro de distribuição de lucros da Modelagem Financeira do PEV.

Esta data será utilizada no cálculo do **Fluxo de Caixa do Investidor** para determinar quando os pagamentos de distribuição de lucros começarão a ser contabilizados.

---

## 🎯 Objetivo

Permitir que o usuário defina quando a distribuição de lucros começará a ser paga aos investidores/sócios, proporcionando maior precisão no cálculo do fluxo de caixa e das métricas financeiras (TIR, Payback, etc).

---

## 🔧 Implementação Técnica

### 1. **Banco de Dados (PostgreSQL)**

**Arquivo:** `database/postgresql_db.py`

#### Migração de Schema

Adicionada coluna `start_date` (tipo DATE) na tabela `plan_finance_profit_distribution`:

```sql
ALTER TABLE plan_finance_profit_distribution 
ADD COLUMN IF NOT EXISTS start_date DATE
```

#### Métodos Atualizados

**`get_plan_profit_distribution(plan_id)`**
- Retorna também o campo `start_date` formatado como string 'YYYY-MM-DD'
- Retorna string vazia se a data não estiver definida

```python
return {
    'percentage': row['percentage'] or '',
    'start_date': row['start_date'].strftime('%Y-%m-%d') if row['start_date'] else '',
    'notes': row['notes'] or ''
}
```

**`update_plan_profit_distribution(plan_id, data)`**
- Salva o campo `start_date` tanto no INSERT quanto no UPDATE
- Converte string vazia para NULL no banco

```python
start_date = data.get('start_date', '')
start_date = start_date if start_date else None
```

---

### 2. **Backend (Módulo PEV)**

**Arquivo:** `modules/pev/implantation_data.py`

Função `load_financial_model()` atualizada para incluir o campo `start_date` no payload de `distribuicao_lucros`:

```python
"distribuicao_lucros": {
    "percentual": profit_distribution.get("percentage", ""),
    "start_date": profit_distribution.get("start_date", ""),
    "observacoes": profit_distribution.get("notes", ""),
}
```

---

### 3. **Frontend (Template)**

**Arquivo:** `templates/implantacao/modelo_modelagem_financeira.html`

#### Modal de Edição

Adicionado campo de data no formulário de distribuição de lucros:

```html
<div class="form-group">
  <label for="profitDistributionStartDate">Data de início do pagamento *</label>
  <input type="date" id="profitDistributionStartDate" required>
  <small>Data a partir da qual a distribuição de lucros começará a ser paga</small>
</div>
```

#### Card de Visualização

Adicionada exibição da data de início no card (quando configurada):

```html
{% if fluxo_negocio.distribuicao_lucros.start_date %}
  <div>
    <div>📅 Início do pagamento:</div>
    <div>{{ fluxo_negocio.distribuicao_lucros.start_date | format_date_br }}</div>
  </div>
{% endif %}
```

#### JavaScript

**Função `openProfitDistributionModal()`**
- Carrega o valor de `start_date` do objeto `profitDistributionData`

```javascript
document.getElementById('profitDistributionStartDate').value = 
  profitDistributionData.start_date || '';
```

**Submit do formulário**
- Envia o campo `start_date` na requisição PUT para a API

```javascript
const data = {
  percentage: document.getElementById('profitDistributionPercentage').value,
  start_date: document.getElementById('profitDistributionStartDate').value,
  notes: document.getElementById('profitDistributionNotes').value
};
```

---

## 📸 Interface do Usuário

### Modal de Edição

O modal de "Editar Distribuição de Lucros" agora possui 3 campos:

1. **% sobre resultado operacional** (obrigatório)
2. **Data de início do pagamento** (obrigatório) ⭐ NOVO
3. **Observações** (opcional)

### Card de Visualização

O card "💰 Distribuição de Lucros" exibe:

- % sobre resultado operacional
- Valor estimado (calculado dinamicamente)
- **📅 Início do pagamento** (quando configurado) ⭐ NOVO
- Observações (quando preenchidas)

---

## 🔄 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Usuário preenche data no modal                               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. JavaScript envia data via PUT /api/.../profit_distribution   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. API Flask chama update_plan_profit_distribution()            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. PostgreSQL salva start_date na tabela                        │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. load_financial_model() carrega data e passa para template    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Template exibe data formatada no card                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Como Testar

### 1. Aplicar Migração

Execute o script de migração:

```bash
APLICAR_DATA_INICIO_DISTRIBUICAO.bat
```

### 2. Reiniciar Servidor

```bash
python app_pev.py
```

### 3. Acessar Interface

1. Navegue até: `http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=X`
2. Na seção "Distribuição de Lucros e Outras Destinações de Resultados"
3. Clique no ícone de edição (✏️) no card "💰 Distribuição de Lucros"

### 4. Preencher Formulário

- Configure o percentual (ex: "30%")
- **Escolha uma data de início** (ex: "01/06/2025")
- Adicione observações se desejar
- Clique em "Salvar"

### 5. Verificar Resultado

- O card deve exibir a data escolhida em "📅 Início do pagamento"
- A data deve ser formatada no padrão brasileiro (DD/MM/AAAA)
- A página deve recarregar automaticamente

---

## 📊 Uso no Fluxo de Caixa do Investidor

A data de início será utilizada para determinar:

1. **Quando começar a contabilizar** a distribuição de lucros no fluxo de caixa
2. **Cálculo da TIR (Taxa Interna de Retorno)** - impacta os fluxos futuros
3. **Cálculo do Payback** - quando os investidores começam a receber retorno
4. **Projeção de resultados** - distribuições só aparecem após a data de início

### Exemplo

Se o resultado operacional mensal é R$ 100.000 e a distribuição é 30%:

- **Antes da data de início:** R$ 0 de distribuição
- **Após a data de início:** R$ 30.000/mês de distribuição

---

## ✅ Checklist de Implementação

- [x] Adicionar coluna `start_date` no PostgreSQL
- [x] Atualizar `get_plan_profit_distribution()` para retornar start_date
- [x] Atualizar `update_plan_profit_distribution()` para salvar start_date
- [x] Adicionar campo de data no modal HTML
- [x] Atualizar JavaScript para carregar/enviar start_date
- [x] Exibir data de início no card visual
- [x] Adicionar campo no payload de `load_financial_model()`
- [x] Criar script de migração (APLICAR_DATA_INICIO_DISTRIBUICAO.bat)
- [x] Criar documentação da feature
- [ ] **PRÓXIMO:** Implementar uso da data no cálculo do Fluxo de Caixa do Investidor

---

## 🚀 Próximos Passos (TODO)

### Implementação do Uso no Fluxo de Caixa

1. **Atualizar `load_financial_model()`** em `implantation_data.py`
   - Ler `start_date` da distribuição de lucros
   - Filtrar períodos do fluxo de caixa do investidor
   - Só incluir distribuições após a `start_date`

2. **Lógica de Cálculo**
   - Comparar data de cada período com `start_date`
   - Se período < `start_date`: distribuição = 0
   - Se período >= `start_date`: aplicar percentual normal

3. **Teste de Integração**
   - Criar cenário com data de início futura
   - Verificar que distribuições não aparecem antes
   - Verificar TIR e Payback recalculados corretamente

---

## 📝 Padrões Seguidos

✅ **Seguiu as regras do projeto:**
- Código funciona em PostgreSQL
- Usa soft delete (campo não deletado, apenas nullable)
- Campos de auditoria mantidos (created_at, updated_at)
- Type hints e docstrings em Python
- Validação de input no frontend
- Formatação com padrão brasileiro (DD/MM/AAAA)
- API REST seguindo padrão do projeto

✅ **Boas práticas:**
- Campo opcional (não quebra dados existentes)
- Migração idempotente (IF NOT EXISTS)
- Script de migração documentado
- Tratamento de erros adequado
- Interface intuitiva para o usuário

---

## 📅 Histórico

| Data | Versão | Autor | Descrição |
|------|--------|-------|-----------|
| 28/10/2025 | 1.0 | Cursor AI | Implementação inicial da data de início |

---

## 🔗 Arquivos Relacionados

- `database/postgresql_db.py` - Métodos de banco de dados
- `modules/pev/implantation_data.py` - Carregamento de dados financeiros
- `templates/implantacao/modelo_modelagem_financeira.html` - Interface do usuário
- `APLICAR_DATA_INICIO_DISTRIBUICAO.bat` - Script de migração
- `/docs/governance/DATABASE_STANDARDS.md` - Padrões de banco de dados
- `/docs/governance/API_STANDARDS.md` - Padrões de API

---

**Versão:** 1.0  
**Data:** 28/10/2025  
**Status:** ✅ Implementado (pendente uso no fluxo de caixa)

