# 🔧 Solução: Empresas no Dashboard GRV

**Data:** 10/10/2025  
**Problema Resolvido:** Apenas 3 empresas apareciam no dashboard GRV

---

## 📊 Problema Identificado

No dashboard GRV (`http://127.0.0.1:5002/grv/dashboard`), só apareciam **3 empresas**:
- Alimentos Tia Sonia
- Tech Solutions
- Consultoria ABC

**A empresa "Versus Gestão Corporativa" não estava cadastrada no banco de dados.**

---

## ✅ Solução Aplicada

### 1. Diagnóstico
O banco de dados é inicializado com apenas 3 empresas de exemplo (veja `database/sqlite_db.py`, linhas 638-643):

```python
companies = [
    ('Alimentos Tia Sonia',),
    ('Tech Solutions',),
    ('Consultoria ABC',)
]
```

### 2. Empresa Adicionada
Foi criada a empresa **"Versus Gestão Corporativa"** com:

```
ID: 4
Nome: Versus Gestão Corporativa
Razão Social: Versus Gestão Corporativa Ltda
Setor: Consultoria Empresarial
Porte: Média Empresa
Missão: Transformar organizações através de gestão estratégica
Visão: Ser referência nacional em consultoria de gestão
Valores: Excelência, Inovação, Transparência, Resultados
Plano: Planejamento Estratégico 2025 (ID: 4)
```

### 3. Resultado
Agora o sistema tem **4 empresas** cadastradas e todas aparecem no dashboard GRV.

---

## 🚀 Como Adicionar Novas Empresas

### Método 1: Script Rápido (Recomendado)

Use o script criado como base:

```bash
# Edite add_versus_company.py alterando os dados
python add_versus_company.py
```

### Método 2: Criar Script Personalizado

```python
#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('instance/pevapp22.db')
cursor = conn.cursor()

# Inserir empresa
cursor.execute("""
    INSERT INTO companies (
        name, legal_name, industry, size, description,
        mvv_mission, mvv_vision, mvv_values
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'Nome da Empresa',
    'Razão Social Ltda',
    'Setor/Indústria',
    'Porte da Empresa',
    'Descrição da empresa',
    'Missão da empresa',
    'Visão da empresa',
    'Valores da empresa'
))

company_id = cursor.lastrowid

# Criar plano para a empresa
cursor.execute("""
    INSERT INTO plans (company_id, name, year)
    VALUES (?, ?, ?)
""", (company_id, 'Nome do Plano 2025', 2025))

conn.commit()
conn.close()

print(f"Empresa adicionada! ID: {company_id}")
```

### Método 3: Interface Web (Futuro)

Criar uma página de administração para cadastro de empresas pela interface web.

---

## 📋 Estrutura da Tabela Companies

```sql
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT,                  -- Nome fantasia
    legal_name TEXT,           -- Razão social
    industry TEXT,             -- Setor/indústria
    size TEXT,                 -- Porte da empresa
    description TEXT,          -- Descrição
    client_code TEXT,          -- Código do cliente
    mvv_mission TEXT,          -- Missão
    mvv_vision TEXT,           -- Visão
    mvv_values TEXT,           -- Valores
    pev_config TEXT,           -- Config PEV (JSON)
    grv_config TEXT,           -- Config GRV (JSON)
    created_at TIMESTAMP       -- Data de criação
);
```

---

## 🔍 Verificar Empresas Cadastradas

Use o script de verificação:

```bash
python check_companies.py
```

Saída esperada:
```
============================================================
EMPRESAS NO BANCO DE DADOS
============================================================

Total de empresas encontradas: 4

1. ID: 1     | Nome: Alimentos Tia Sonia
2. ID: 3     | Nome: Consultoria ABC
3. ID: 2     | Nome: Tech Solutions
4. ID: 4     | Nome: Versus Gestão Corporativa
```

---

## 🎯 Dados de Seed Padrão

Para atualizar os dados iniciais do sistema, edite:

**SQLite:** `database/sqlite_db.py` (linhas 638-643)
**PostgreSQL:** `database/postgresql_db.py` (linhas 381-384)

Exemplo:
```python
# Insert sample companies
companies = [
    ('Alimentos Tia Sonia',),
    ('Tech Solutions',),
    ('Consultoria ABC',),
    ('Versus Gestão Corporativa',)  # ← Adicionar aqui
]
cursor.executemany('INSERT INTO companies (name) VALUES (?)', companies)
```

---

## 📝 Scripts Criados

### 1. `check_companies.py`
Verifica e lista todas as empresas no banco:
```bash
python check_companies.py
```

### 2. `add_versus_company.py`
Adiciona a Versus Gestão Corporativa (já executado):
```bash
python add_versus_company.py
```

---

## ⚙️ Como o Dashboard GRV Funciona

### Código Relevante: `modules/grv/__init__.py` (linhas 63-90)

```python
@grv_bp.route('/dashboard')
def grv_dashboard():
    db = get_db()
    companies = db.get_companies()  # ← Busca TODAS as empresas
    
    companies_context = []
    for company in companies:
        plans = db.get_plans_by_company(company['id'])
        companies_context.append({
            'id': company['id'],
            'name': company.get('name') or company.get('legal_name'),
            'industry': company.get('industry') or '',
            'plans': [{'id': plan['id'], 'name': plan['name']} for plan in plans]
        })
    
    return render_template("routine_selector.html", 
                         companies=companies_context, ...)
```

**Não há filtros** - todas as empresas do banco são exibidas.

---

## 🐛 Troubleshooting

### Empresa não aparece no dashboard?

1. **Verificar se está no banco:**
   ```bash
   python check_companies.py
   ```

2. **Verificar se tem plano associado:**
   ```bash
   python -c "from config_database import get_db; db = get_db(); plans = db.get_plans_by_company(4); print(f'Planos: {len(plans)}')"
   ```

3. **Recarregar a página:**
   - Ctrl + F5 (limpiar cache)
   - Ou fechar e abrir navegador

### Script dá erro de encoding (Windows)?

Remova emojis e caracteres especiais:
- ✅ → OK
- ❌ → ERRO
- 📊 → (remover)

---

## ✅ Checklist de Verificação

Após adicionar uma empresa, verifique:

- [ ] Empresa aparece em `check_companies.py`
- [ ] Empresa tem pelo menos 1 plano associado
- [ ] Dashboard GRV carrega sem erros
- [ ] Empresa aparece na lista do dashboard
- [ ] É possível clicar e acessar a empresa

---

## 📞 Próximos Passos

### Melhorias Recomendadas:

1. **Interface de Cadastro**
   - Criar página `/admin/companies/new`
   - Formulário web para adicionar empresas

2. **Atualizar Seed Data**
   - Incluir Versus Gestão Corporativa no seed padrão
   - Adicionar mais dados de exemplo

3. **Validações**
   - Validar campos obrigatórios
   - Evitar duplicatas

4. **API REST**
   - Endpoint POST /api/companies
   - Endpoint GET /api/companies

---

## 📚 Referências

- **Código GRV:** `modules/grv/__init__.py`
- **Banco SQLite:** `database/sqlite_db.py`
- **Configuração:** `config_database.py`
- **Scripts:** `check_companies.py`, `add_versus_company.py`

---

**Problema Resolvido! ✅**

Agora todas as 4 empresas aparecem no dashboard GRV:
- http://127.0.0.1:5002/grv/dashboard




