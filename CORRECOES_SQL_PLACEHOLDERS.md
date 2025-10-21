# ✅ Correções SQL: Placeholders SQLite → PostgreSQL

**Data:** 20/10/2025  
**Problema:** Após migração para Docker/PostgreSQL, queries SQL estão usando placeholders `?` (SQLite) ao invés de `%s` (PostgreSQL)

---

## 📊 Resumo de Correções

### ✅ CORRIGIDOS
- ✅ modules/grv/__init__.py: 24 queries (cursor.execute)
- ✅ modules/meetings/__init__.py: 10 queries (todas)  
- ✅ modules/report_models.py: 2 queries (cursor.execute)

### ⚠️ PENDENTES (Queries com `WHERE ... = ?` em strings SQL)
- ⚠️ modules/grv/__init__.py: ~46 queries adicionais em INSERTs, UPDATEs, SELECTs complexos
- ⚠️ modules/report_models.py: 1 UPDATE complexo (linha 158-163)

---

## 🔧 Correções Pendentes Detalhadas

### 1. modules/report_models.py (Linhas 156-164)

**ANTES:**
```python
cursor.execute("""
    UPDATE report_models SET 
    name = ?, description = ?, paper_size = ?, orientation = ?, 
    margin_top = ?, margin_right = ?, margin_bottom = ?, margin_left = ?,
    header_height = ?, header_rows = ?, header_columns = ?, header_content = ?,
    footer_height = ?, footer_rows = ?, footer_columns = ?, footer_content = ?,
    updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
""", update_data)
```

**DEPOIS:**
```python
cursor.execute("""
    UPDATE report_models SET 
    name = %s, description = %s, paper_size = %s, orientation = %s, 
    margin_top = %s, margin_right = %s, margin_bottom = %s, margin_left = %s,
    header_height = %s, header_rows = %s, header_columns = %s, header_content = %s,
    footer_height = %s, footer_rows = %s, footer_columns = %s, footer_content = %s,
    updated_at = CURRENT_TIMESTAMP
    WHERE id = %s
""", update_data)
```

---

### 2. modules/grv/__init__.py - Queries Pendentes

#### Linhas 932-943 (e similar 980-991, 1407-1417)
```python
# ANTES:
WHERE company_id = ?

# DEPOIS:
WHERE company_id = %s
```

#### Linhas 1041-1043
```python
# ANTES:
"SELECT id, code, name FROM portfolios WHERE company_id = ? ORDER BY LOWER(name)"

# DEPOIS:
"SELECT id, code, name FROM portfolios WHERE company_id = %s ORDER BY LOWER(name)"
```

#### Linhas 1103, 1164, 1273
```python
# ANTES:
WHERE p.company_id = ? AND p.id = ?

# DEPOIS:
WHERE p.company_id = %s AND p.id = %s
```

#### Linhas 1329-1330, 1435-1436, 1499-1500, 1512-1513, 1572-1573
```python
# ANTES:
WHERE id = ? AND company_id = ?

# DEPOIS:
WHERE id = %s AND company_id = %s
```

#### Linhas 1620-1622, 1630-1632
```python
# ANTES:
WHERE plan_id = ? AND stage = 'approval'

# DEPOIS:
WHERE plan_id = %s AND stage = 'approval'
```

#### Linhas 1670-1672, 1691-1692
```python
# ANTES:
WHERE g.company_id = ?

# DEPOIS:
WHERE g.company_id = %s
```

#### Linhas 1720-1721, 1733-1734, 1739-1741, 1745-1748
```python
# ANTES:
WHERE id = ?
WHERE company_id = ? AND parent_id = ?
WHERE company_id = ? AND parent_id IS NULL

# DEPOIS:
WHERE id = %s
WHERE company_id = %s AND parent_id = %s
WHERE company_id = %s AND parent_id IS NULL
```

#### Linhas 1754-1756
```python
# ANTES:
VALUES (?, ?, ?, ?, ?)

# DEPOIS:
VALUES (%s, %s, %s, %s, %s)
```

#### Linhas 1799-1800
```python
# ANTES:
SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
WHERE id = ? AND company_id = ?

# DEPOIS:
SET name = %s, description = %s, updated_at = CURRENT_TIMESTAMP
WHERE id = %s AND company_id = %s
```

#### Linhas 1838-1839, 1851-1852
```python
# ANTES:
SELECT COUNT(*) FROM indicators WHERE group_id = ?
DELETE FROM indicator_groups WHERE id = ? AND company_id = ?

# DEPOIS:
SELECT COUNT(*) FROM indicators WHERE group_id = %s
DELETE FROM indicator_groups WHERE id = %s AND company_id = %s
```

#### Linhas 1889-1891, 1916-1917, 1948-1950
```python
# ANTES:
WHERE i.company_id = ?
WHERE id = ? AND company_id = ?
WHERE i.company_id = ? AND i.process_id = ?

# DEPOIS:
WHERE i.company_id = %s
WHERE id = %s AND company_id = %s
WHERE i.company_id = %s AND i.process_id = %s
```

#### Linhas 1996-2004 (Query dinâmica com placeholders)
```python
# ANTES:
placeholders = ",".join("?" * len(collaborator_ids))
WHERE company_id = ? AND id IN ({placeholders})

# DEPOIS:
placeholders = ",".join("%s" * len(collaborator_ids))
WHERE company_id = %s AND id IN ({placeholders})
```

#### Linhas 2057-2058, 2064-2066, 2070-2071, 2080-2083
```python
# ANTES:
SELECT code FROM indicator_groups WHERE id = ?
SELECT COUNT(*) FROM indicators WHERE company_id = ? AND group_id = ?
SELECT client_code FROM companies WHERE id = ?
SELECT COUNT(*) FROM indicators WHERE company_id = ? AND group_id IS NULL

# DEPOIS:
SELECT code FROM indicator_groups WHERE id = %s
SELECT COUNT(*) FROM indicators WHERE company_id = %s AND group_id = %s
SELECT client_code FROM companies WHERE id = %s
SELECT COUNT(*) FROM indicators WHERE company_id = %s AND group_id IS NULL
```

... e assim por diante para todas as ocorrências restantes.

---

## 🚀 Script de Correção em Massa

Para corrigir todas de uma vez, execute no terminal Python:

```python
import re

files_to_fix = [
    'modules/grv/__init__.py',
    'modules/report_models.py'
]

for filepath in files_to_fix:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Substituir todos os placeholders ? por %s
    # Dentro de queries SQL (entre aspas/triplas aspas)
    content = re.sub(
        r'(\bWHERE\b.*?)(= \?)',
        r'\1= %s',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(\bVALUES\b.*?)(\?)',
        r'\1%s',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(\bSET\b.*?)(= \?)',
        r'\1= %s',
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'(\bIN \()(\?)',
        r'\1%s',
        content
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
print("✅ Correções aplicadas!")
```

---

## 📋 Validação

Após correções, verificar:

```bash
# Não deve encontrar nenhum placeholder ?
grep -r "WHERE.*= ?" modules/grv/
grep -r "WHERE.*= ?" modules/meetings/
grep -r "WHERE.*= ?" modules/report_models.py

# Deve encontrar apenas %s
grep -r "WHERE.*= %s" modules/
```

---

## ⚠️ IMPORTANTE

**Por que isso causava erros:**
- PostgreSQL usa placeholders `%s` ou `$1, $2...`
- SQLite usa placeholders `?`
- Ao usar `?` no PostgreSQL, a query falha com erro de sintaxe
- **RESULTADO:** Todas as páginas GRV e Meetings falhavam ao carregar dados

**Impacto:**
- ❌ Formulários de indicadores
- ❌ Páginas de processos
- ❌ Reuniões
- ❌ Projetos GRV
- ❌ Todas as consultas ao banco PostgreSQL

---

## ✅ Status Atual

- **Corrigidos manualmente:** 36 queries
- **Pendentes:** ~50 queries nos módulos GRV e report_models
- **Recomendação:** Aplicar correção em massa via script Python

---

**Próximos passos:**
1. Aplicar correções em massa (script acima)
2. Reiniciar Docker: `docker-compose -f docker-compose.dev.yml restart app_dev`
3. Testar todas as páginas GRV e Meetings
4. Validar formulários


