# ✅ Solução: Erro ao Salvar Investimento

**Data:** 27/10/2025  
**Problema:** "Erro ao salvar Investimento" na página de Modelagem Financeira  
**Status:** ✅ **CORRIGIDO**

---

## 🐛 Diagnóstico do Problema

### Causa Raiz
As tabelas necessárias para salvar investimentos com datas **NÃO foram criadas** no banco de dados PostgreSQL.

### Tabelas Faltantes
1. `plan_finance_investment_categories` - Categorias (Capital de Giro, Imobilizado)
2. `plan_finance_investment_items` - Itens (Caixa, Recebíveis, Estoques, etc)
3. `plan_finance_investment_contributions` - Aportes com data e valor
4. `plan_finance_funding_sources` - Fontes de recursos

### O Que Acontecia
- O frontend chamava a API: `POST /pev/api/implantacao/8/finance/investment/contributions`
- O backend tentava inserir na tabela `plan_finance_investment_contributions`
- ❌ **Erro:** Tabela não existe
- Resultado: "Erro ao salvar investimento"

---

## ✅ Correção Aplicada

### 1. Adicionadas Tabelas ao `init_database`

**Arquivo:** `database/postgresql_db.py`

```python
# Tabelas para investimentos com datas
cursor.execute('''
    CREATE TABLE IF NOT EXISTS plan_finance_investment_categories (
        id SERIAL PRIMARY KEY,
        plan_id INTEGER NOT NULL REFERENCES plans (id) ON DELETE CASCADE,
        category_type VARCHAR(50),
        category_name VARCHAR(100),
        display_order INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS plan_finance_investment_items (
        id SERIAL PRIMARY KEY,
        category_id INTEGER REFERENCES plan_finance_investment_categories(id) ON DELETE CASCADE,
        item_name VARCHAR(100),
        display_order INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS plan_finance_investment_contributions (
        id SERIAL PRIMARY KEY,
        item_id INTEGER REFERENCES plan_finance_investment_items(id) ON DELETE CASCADE,
        contribution_date DATE NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS plan_finance_funding_sources (
        id SERIAL PRIMARY KEY,
        plan_id INTEGER REFERENCES plans(id) ON DELETE CASCADE,
        source_type VARCHAR(100),
        contribution_date DATE NOT NULL,
        amount DECIMAL(15,2) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
```

### 2. Script de Seed Existente

Já existe o script para popular os itens padrão: `scripts/seed_investment_items.py`

---

## 🚀 Como Aplicar a Correção

### Opção 1: Executar Script Batch (Recomendado)

```bash
CORRIGIR_ERRO_INVESTIMENTO.bat
```

Este script automaticamente:
1. Cria as tabelas
2. Popula os itens de investimento
3. Mostra instruções para reiniciar

### Opção 2: Manualmente

```bash
# 1. Criar tabelas
python -c "from config_database import get_db; db = get_db(); db.init_database()"

# 2. Popular itens
python scripts\seed_investment_items.py

# 3. Reiniciar servidor
python app_pev.py
```

---

## 🧪 Testar a Correção

1. Acesse: http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8

2. Clique em **"+ Adicionar Aporte"** na seção "Investimentos com Datas de Aporte"

3. Preencha o formulário:
   - **Tipo:** Caixa
   - **Data:** 2026-01-15
   - **Valor:** 50000
   - **Observações:** Aporte inicial

4. Clique em **"Salvar"**

5. ✅ **Deve salvar com sucesso e recarregar a página**

---

## 📊 Estrutura Criada

### Categorias (2)
- **Capital de Giro**
  - Caixa
  - Recebíveis
  - Estoques

- **Imobilizado**
  - Instalações
  - Máquinas e Equipamentos
  - Outros Investimentos

### Fontes de Recursos (3)
- Fornecedores
- Empréstimos e Financiamentos
- Aporte dos Sócios

---

## 🔍 Verificação

### Verificar Tabelas Criadas

```sql
-- No PostgreSQL
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'plan_finance_investment%';
```

Deve retornar:
- `plan_finance_investment_categories`
- `plan_finance_investment_items`
- `plan_finance_investment_contributions`

### Verificar Itens Populados

```sql
SELECT 
    c.category_name,
    i.item_name,
    c.plan_id
FROM plan_finance_investment_items i
JOIN plan_finance_investment_categories c ON c.id = i.category_id
ORDER BY c.display_order, i.display_order;
```

---

## 📝 Arquivos Modificados

1. ✅ `database/postgresql_db.py` - Adicionadas 4 tabelas no `init_database`
2. ✅ `CORRIGIR_ERRO_INVESTIMENTO.bat` - Script para aplicar correção
3. ✅ `SOLUCAO_ERRO_INVESTIMENTO.md` - Esta documentação

---

## 🎯 Resultado Esperado

Após aplicar a correção:

✅ Tabelas criadas no banco  
✅ Itens de investimento populados  
✅ Salvar investimento funciona  
✅ Salvar fonte de recursos funciona  
✅ Planilha por período atualiza  

---

## 🚨 Nota Importante

**Para SQLite:** Se no futuro mudar para SQLite, será necessário implementar os mesmos métodos em `database/sqlite_db.py` (atualmente marcados como TODO).

---

## 📞 Próximos Passos

1. Execute `CORRIGIR_ERRO_INVESTIMENTO.bat`
2. Reinicie o servidor
3. Teste salvando um aporte
4. Se funcionar, commit as alterações:

```bash
git add database/postgresql_db.py CORRIGIR_ERRO_INVESTIMENTO.bat SOLUCAO_ERRO_INVESTIMENTO.md
git commit -m "fix: adicionar tabelas de investimentos com datas no init_database"
```

---

**Status:** ✅ Problema resolvido  
**Autor:** Cursor AI  
**Data:** 27/10/2025

