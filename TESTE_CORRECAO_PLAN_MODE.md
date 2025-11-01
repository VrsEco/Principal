# ✅ Correção: Tipos de Planejamento (Evolução vs Implantação)

**Data:** 01/11/2025  
**Status:** ✅ Corrigido e Testado

---

## 🐛 Problema Identificado

Projetos criados com tipo **Implantação** eram exibidos como se fossem **Evolução** e vice-versa.

**Causa raiz:**
- As rotas `/plans/<id>` e `/plans/<id>/projects` não verificavam o `plan_mode` do plano
- O link "Abrir no planejamento" não considerava o `plan_mode`
- Projetos vinculados a planos de implantação eram redirecionados para interface errada

---

## ✅ Correções Implementadas

### 1. **Rota `/plans/<plan_id>` (Dashboard Principal)**

**Arquivo:** `app_pev.py` - Linha 4418

```python
@app.route("/plans/<plan_id>")
def plan_dashboard(plan_id: str):
    """Plan dashboard - main dashboard for a specific plan"""
    plan, company = _plan_for(plan_id)
    
    # Verificar se é planejamento de implantação e redirecionar
    plan_mode = (plan.get('plan_mode') or 'evolucao').lower()
    if plan_mode == 'implantacao':
        from flask import redirect, url_for
        return redirect(url_for('pev.pev_implantacao_overview', plan_id=plan_id))
    
    navigation = _navigation(plan_id, "dashboard")
    # ... resto do código
```

**Efeito:** 
- Se acessar `/plans/7` (implantação) → redireciona para `/pev/implantacao?plan_id=7`
- Se acessar `/plans/5` (evolução) → exibe interface clássica

---

### 2. **Rota `/plans/<plan_id>/projects`**

**Arquivo:** `app_pev.py` - Linha 5919

```python
@app.route("/plans/<plan_id>/projects", methods=['GET'])
def plan_projects(plan_id: str):
    """Projects page"""
    try:
        plan, company = _plan_for(plan_id)
        
        # Verificar se é planejamento de implantação e redirecionar
        plan_mode = (plan.get('plan_mode') or 'evolucao').lower()
        if plan_mode == 'implantacao':
            from flask import redirect, url_for
            return redirect(url_for('pev.pev_implantacao_overview', plan_id=plan_id))
        
        navigation = _navigation(plan_id, "projects")
        # ... resto do código
```

**Efeito:**
- Se acessar `/plans/7/projects` (implantação) → redireciona para `/pev/implantacao?plan_id=7`
- Se acessar `/plans/5/projects` (evolução) → exibe lista de projetos

---

### 3. **API de Projetos - Incluir `plan_mode`**

**Arquivo:** `app_pev.py` - Linha 9489 e 9531

**Queries SQL atualizadas para incluir `plan_mode`:**

```sql
SELECT
    p.id,
    p.company_id,
    p.plan_id,
    p.plan_type,
    pl.plan_mode,  -- ← ADICIONADO
    -- ... outros campos
FROM company_projects p
LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
```

**Função de serialização atualizada:**

```python
def _serialize_company_project(row) -> Dict[str, Any]:
    # ... código existente
    
    # Plan mode - buscar do plano se o projeto está vinculado a um plano PEV
    plan_mode = 'evolucao'  # default
    plan_id = row.get('plan_id')
    
    if plan_origin == 'PEV' and plan_id:
        try:
            plan_mode_value = row.get('plan_mode')
            
            if plan_mode_value:
                plan_mode = str(plan_mode_value).lower()
            else:
                # Fallback: buscar diretamente do banco
                db_instance = get_db()
                plan_data = db_instance.get_plan_with_company(int(plan_id))
                if plan_data:
                    plan_mode = (plan_data.get('plan_mode') or 'evolucao').lower()
        except Exception:
            plan_mode = 'evolucao'
    
    return {
        # ... outros campos
        'plan_mode': plan_mode,  # ← ADICIONADO
    }
```

---

### 4. **Link "Abrir no Planejamento" no GRV**

**Arquivo:** `templates/grv_projects_projects.html` - Linha 907

**Antes:**
```javascript
${project.plan_id && project.plan_origin === 'PEV' 
  ? `<a href="/plans/${project.plan_id}/projects">Abrir no planejamento</a>` 
  : ''}
```

**Depois:**
```javascript
${project.plan_id && project.plan_origin === 'PEV' ? (() => {
  const planMode = (project.plan_mode || 'evolucao').toLowerCase();
  const url = planMode === 'implantacao' 
    ? `/pev/implantacao?plan_id=${project.plan_id}`
    : `/plans/${project.plan_id}/projects`;
  return `<a class="project-action" href="${url}" target="_blank">Abrir no planejamento</a>`;
})() : ''}
```

**Efeito:**
- Projeto vinculado ao plano 7 (implantação) → link para `/pev/implantacao?plan_id=7`
- Projeto vinculado ao plano 5 (evolução) → link para `/plans/5/projects`

---

## 🧪 Como Testar

### Teste 1: Projeto de Implantação

1. Acesse: `http://127.0.0.1:5003/grv/company/13/projects/projects`
2. Localize o projeto **"2025.10 - Reunião de Diretoria - Mensal"** (ID 34)
3. Clique em **"Abrir no planejamento"**
4. ✅ **Esperado:** Redireciona para `/pev/implantacao?plan_id=7` (interface de implantação)

### Teste 2: Projeto de Evolução

1. Acesse: `http://127.0.0.1:5003/grv/company/5/projects/projects`
2. Localize um projeto vinculado ao plano 5 (evolução)
3. Clique em **"Abrir no planejamento"**
4. ✅ **Esperado:** Redireciona para `/plans/5/projects` (interface clássica)

### Teste 3: Acesso Direto à URL

1. Acesse diretamente: `http://127.0.0.1:5003/plans/7`
2. ✅ **Esperado:** Redireciona automaticamente para `/pev/implantacao?plan_id=7`

3. Acesse diretamente: `http://127.0.0.1:5003/plans/5`
4. ✅ **Esperado:** Exibe o dashboard clássico (não redireciona)

---

## 📊 Dados de Teste no Banco

**Planos de IMPLANTAÇÃO:**
- ID 7: Implantação Gas Evolution (plan_mode = 'implantacao')
- ID 8: Implantação Save Water (plan_mode = 'implantacao')

**Projetos vinculados:**
- ID 34: "2025.10 - Reunião de Diretoria - Mensal" → Plan 7 (implantacao)
- ID 33: "2025.10.15 - Reunião Semanal Ordinária" → Plan 8 (implantacao)

**Planos de EVOLUÇÃO:**
- ID 5: Planejamento de Crescimento (plan_mode = 'evolucao')
- ID 6: Concepção Empresa de Móveis - EUA (plan_mode = 'evolucao')
- ID 9: Revisão do Planejamento Estratégico (plan_mode = 'evolucao')

---

## 🔧 Correção de Dados

Alguns projetos estavam com `plan_type = 'GRV'` quando deveriam ser `'PEV'`.

**Corrigido automaticamente:**
```sql
UPDATE company_projects 
SET plan_type = 'PEV' 
WHERE plan_id IN (7, 8) AND plan_type = 'GRV'
```

---

## ✅ Resultado

Agora o sistema:
1. ✅ Redireciona automaticamente planos de implantação para a interface correta
2. ✅ Gera links corretos baseado no `plan_mode`
3. ✅ Mantém compatibilidade com planos antigos (default: 'evolucao')
4. ✅ Funciona tanto no GRV quanto no PEV

---

## 🎯 Fluxo Completo

```
Usuário acessa projeto no GRV
         ↓
Clica em "Abrir no planejamento"
         ↓
Sistema verifica plan_mode do plano vinculado
         ↓
    ┌─────────────┴──────────────┐
    ↓                            ↓
plan_mode = 'implantacao'    plan_mode = 'evolucao'
    ↓                            ↓
/pev/implantacao?plan_id=X   /plans/X/projects
    ↓                            ↓
Interface de Implantação     Interface Clássica
```

---

**Container reiniciado:** `gestaoversus_app_prod`  
**Arquivos modificados:** `app_pev.py`, `templates/grv_projects_projects.html`  
**Pronto para uso!** ✅


