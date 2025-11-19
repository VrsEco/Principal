# 🔧 CORREÇÃO: Projetos não Aparecem em GRV

**Data:** 24/10/2025  
**Status:** ✅ Corrigido

---

## 🚨 **PROBLEMA:**

A página `/grv/company/5/projects/projects` não mostrava os projetos criados (company_projects).

**Causa:** A função só listava:
- PEV Plans
- GRV Portfolios

**Faltava:** Listar company_projects (os projetos reais)

---

## ✅ **SOLUÇÃO APLICADA:**

**Arquivo:** `modules/grv/__init__.py` (função `grv_projects_projects`)

Adicionei busca de `company_projects`:

```python
# Get company projects (projetos criados)
company_projects = []
try:
    conn = pg_connect()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.title, p.code, p.plan_id, p.plan_type,
               CASE 
                   WHEN p.plan_type = 'PEV' THEN pl.name
                   ELSE NULL
               END as plan_name
        FROM company_projects p
        LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
        WHERE p.company_id = %s
        ORDER BY p.created_at DESC
    """, (company_id,))
    
    for row in cursor.fetchall():
        company_projects.append({
            'id': row['id'],
            'name': row['title'],
            'origin': 'Projeto',
            'plan_name': row['plan_name']
        })
    conn.close()
except Exception as e:
    print(f"Erro ao buscar company_projects: {e}")

# Combine all lists
all_plans = pev_plans + grv_portfolios + company_projects
```

---

## 🚀 **AÇÃO NECESSÁRIA:**

Execute:
```bash
docker restart gestaoversus_app_dev
```

**Aguarde 10 segundos** e teste novamente!

---

**🎯 AGORA OS PROJETOS DEVEM APARECER!**

