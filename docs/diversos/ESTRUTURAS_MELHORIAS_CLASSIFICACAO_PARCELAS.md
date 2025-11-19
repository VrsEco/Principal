# ✅ Melhorias: Estruturas - Classificação e Repetição por Parcela

**Data:** 28/10/2025  
**Status:** ✅ Implementado

---

## 🎯 Objetivo

Melhorar a precisão contábil e financeira do sistema permitindo que cada parcela de uma estrutura tenha sua própria classificação contábil e periodicidade.

---

## 📊 Mudanças Implementadas

### 1. **Remoção de Campos do Formulário Principal**

#### ❌ Removidos:
- **Status** - Campo removido do formulário principal
- **Repetição** - Movido para o nível de parcela

#### ✅ Mantidos:
- Área, Bloco, Tipo, Descrição
- Valor Total (agora como referência)
- Data Aquisição, Fornecedor, Disponibilização
- Observações

---

### 2. **Novos Campos nas Parcelas**

Cada parcela agora possui:

| Campo | Tipo | Opções | Descrição |
|-------|------|--------|-----------|
| **Classificação** | Select | Investimento, Custo Fixo, Despesa Fixa | Classificação contábil da parcela |
| **Repetição** | Select | Única, Mensal, Trimestral, Semestral, Anual | Periodicidade da parcela |
| Número | Text | - | Identificação da parcela (ex: 1/12) |
| Valor | Number | - | Valor da parcela |
| Vencimento | Date | - | Data de vencimento |
| Tipo | Select | Entrada, Mensalidade, Parcela, Pagamento único | Tipo de pagamento |

---

### 3. **Benefícios da Nova Estrutura**

✅ **Maior Precisão Contábil**
- Cada parcela pode ter classificação diferente
- Permite estruturas mistas (ex: investimento inicial + despesas recorrentes)

✅ **Flexibilidade Financeira**
- Periodicidades diferentes na mesma estrutura
- Melhor controle de fluxo de caixa

✅ **Dados Mais Precisos**
- Investimentos separados de despesas operacionais
- Custos fixos vs despesas fixas diferenciados
- Integração correta com DRE e Fluxo de Caixa

---

## 🗄️ Alterações no Banco de Dados

### **Tabela: `plan_structure_installments`**

Novos campos adicionados:

```sql
ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS classification TEXT;

ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS repetition TEXT;
```

**Schema Completo:**
```sql
CREATE TABLE plan_structure_installments (
    id SERIAL PRIMARY KEY,
    structure_id INTEGER NOT NULL REFERENCES plan_structures (id) ON DELETE CASCADE,
    installment_number TEXT,
    amount TEXT,
    due_info TEXT,
    installment_type TEXT,
    classification TEXT,          -- NOVO
    repetition TEXT,              -- NOVO
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## 📁 Arquivos Modificados

### 1. **templates/implantacao/execution_estruturas.html**

**Formulário:**
- ❌ Removido campo `Status`
- ❌ Removido campo `Repetição` da estrutura principal
- ✅ Campo `Valor` agora é "Valor Total (referência)"
- ✅ Adicionados campos `Classificação` e `Repetição` nas parcelas

**Função `addInstallment()`:**
```javascript
// Grid com 7 colunas: #, Valor, Vencimento, Classificação, Repetição, Tipo, Ações
grid-template-columns: 70px 100px 110px 130px 130px 100px 50px;
```

**Coleta de dados:**
```javascript
const installments = Array.from(installmentRows).map(row => ({
    installment_number: row.querySelector('.installment-number').value,
    amount: row.querySelector('.installment-amount').value,
    due_info: row.querySelector('.installment-due').value,
    classification: row.querySelector('.installment-classification').value,  // NOVO
    repetition: row.querySelector('.installment-repetition').value,          // NOVO
    installment_type: row.querySelector('.installment-type').value
}));
```

**Exibição de Parcelas:**
- Tabela expandida com 6 colunas
- Classificação exibida com badges coloridos:
  - 🔵 Investimento (azul)
  - 🟡 Custo Fixo (amarelo)
  - 🔴 Despesa Fixa (rosa)

---

### 2. **database/postgresql_db.py**

**init_database():**
- Atualizado schema do `CREATE TABLE` para incluir os novos campos

**create_plan_structure_installment():**
```python
cursor.execute('''
    INSERT INTO plan_structure_installments (
        structure_id, installment_number, amount, due_info, installment_type, 
        classification, repetition
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
''', (
    structure_id,
    data.get('installment_number'),
    data.get('amount'),
    data.get('due_info'),
    data.get('installment_type'),
    data.get('classification'),      # NOVO
    data.get('repetition')           # NOVO
))
```

---

### 3. **modules/pev/implantation_data.py**

**load_structures():**
```python
installments_map.setdefault(structure_id, []).append({
    "numero": inst.get("installment_number"),
    "valor": inst.get("amount"),
    "vencimento": inst.get("due_info"),
    "tipo": inst.get("installment_type"),
    "classificacao": inst.get("classification"),    # NOVO
    "repeticao": inst.get("repetition"),           # NOVO
})
```

---

### 4. **database/migrations/add_installment_classification_repetition.sql**

Novo arquivo de migração para adicionar os campos no banco de dados existente.

```sql
ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS classification TEXT;

ALTER TABLE plan_structure_installments 
ADD COLUMN IF NOT EXISTS repetition TEXT;
```

---

## 🔄 Migração de Dados

### Para bancos existentes:

**PostgreSQL:**
```bash
psql -U postgres -d gestaovs -f database/migrations/add_installment_classification_repetition.sql
```

**SQLite:**
Os campos serão criados automaticamente na próxima inicialização (nullable).

### Dados Existentes:
- Parcelas antigas continuarão funcionando (campos nullable)
- Novas parcelas devem ter classificação e repetição preenchidas
- Recomendado atualizar parcelas antigas para melhor precisão

---

## 🎨 Exemplo de Uso

### Exemplo 1: Sistema ERP Parcelado

**Estrutura:**
- Descrição: "Sistema ERP Financeiro"
- Valor Total: R$ 15.000,00

**Parcelas:**
1. **Parcela 1/12**: R$ 5.000,00 | Investimento | Única | Entrada
2. **Parcela 2-12**: R$ 833,33 | Despesa Fixa | Mensal | Mensalidade

**Resultado:**
- R$ 5.000 classificado como Investimento (imobilizado)
- R$ 833,33/mês classificado como Despesa Fixa (DRE)

---

### Exemplo 2: Aluguel com Caução

**Estrutura:**
- Descrição: "Aluguel de Escritório"
- Valor Total: R$ 5.000,00

**Parcelas:**
1. **Caução**: R$ 2.000,00 | Investimento | Única | Entrada
2. **Aluguel**: R$ 1.000,00 | Custo Fixo | Mensal | Mensalidade

**Resultado:**
- R$ 2.000 classificado como Investimento (capital de giro)
- R$ 1.000/mês classificado como Custo Fixo (DRE)

---

## 📈 Impacto nas Demonstrações Financeiras

### **Investimentos → Imobilizado**
- Parcelas com `classificacao = 'Investimento'`
- Aparecem no Plano de Investimentos
- Não impactam DRE diretamente

### **Custos Fixos → DRE (Custos)**
- Parcelas com `classificacao = 'Custo Fixo'`
- Aparecem na linha de Custos Fixos da DRE
- Relacionados à operação/produção

### **Despesas Fixas → DRE (Despesas)**
- Parcelas com `classificacao = 'Despesa Fixa'`
- Aparecem na linha de Despesas Fixas da DRE
- Relacionados a comercial/administrativo

---

## ✅ Validações

### Frontend (HTML5):
- Campos obrigatórios marcados
- Tipos de input validados (number, date)

### Backend (Python):
- Validação de campos obrigatórios da estrutura
- Parcelas podem ter campos opcionais

---

## 🚀 Como Usar

### 1. **Criar Nova Estrutura**
1. Clique em "Nova Estrutura"
2. Preencha: Área, Bloco, Tipo, Descrição
3. Valor Total é opcional (referência)

### 2. **Adicionar Parcelas**
1. Clique em "+ Adicionar Parcela"
2. Preencha:
   - Número (ex: 1/12)
   - Valor da parcela
   - Vencimento
   - **Classificação** ⭐
   - **Repetição** ⭐
   - Tipo (opcional)
3. Adicione quantas parcelas necessárias

### 3. **Salvar**
- Estrutura e parcelas salvas juntas
- Classificações aplicadas automaticamente

---

## 🔧 Próximos Passos (Futuro)

1. **Cálculos Automáticos:**
   - Usar classificação para popular automaticamente:
     - DRE (Custos/Despesas Fixas)
     - Fluxo de Investimentos
     - Fluxo de Caixa

2. **Relatórios:**
   - Relatório de Investimentos por Bloco
   - Análise de Custos vs Despesas
   - Projeção de Fluxo de Caixa

3. **Dashboards:**
   - Gráficos por classificação
   - Análise de impacto financeiro
   - Alertas de vencimentos

---

## 📝 Notas Técnicas

### Compatibilidade:
- ✅ PostgreSQL (produção)
- ✅ SQLite (desenvolvimento)
- ✅ Dados existentes compatíveis (campos nullable)

### Performance:
- Sem impacto significativo (campos TEXT simples)
- Índices não necessários no momento

### Segurança:
- Validação de plan_id em todas as operações
- Soft delete mantido
- Auditoria via created_at

---

**Versão:** 1.0  
**Última atualização:** 28/10/2025  
**Implementado por:** Sistema de IA + Fabiano Ferreira

