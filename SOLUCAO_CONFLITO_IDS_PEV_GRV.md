# 🔧 Solução Definitiva - Conflito de IDs entre PEV e GRV

## 🎯 Problema Resolvido

**Situação:** Portfólios GRV e Planejamentos PEV podem ter o mesmo ID, causando confusão ao vincular projetos.

**Exemplo do Conflito:**
- Planejamento PEV: ID=5 "Planejamento de Crescimento"
- Portfólio GRV: ID=5 "Portfolio Teste 200"

Quando um projeto era vinculado ao ID 5, o sistema não sabia se era PEV ou GRV.

---

## ✅ Solução Implementada

### 1. Novo Campo na Tabela

**Campo adicionado:** `plan_type` TEXT

```sql
ALTER TABLE company_projects ADD COLUMN plan_type TEXT;
```

**Valores possíveis:**
- `'PEV'` - Planejamento do módulo PEV
- `'GRV'` - Portfólio do módulo GRV
- `NULL` - Sem vínculo

---

### 2. Frontend - Captura Automática do Tipo

**Arquivo:** `templates/grv_projects_projects.html`

**No HTML, cada option tem `data-origin`:**
```html
<option value="{{ plan.id }}" data-origin="{{ plan.origin }}">
  {% if plan.origin %}{{ plan.origin }} - {% endif %}{{ plan.name }}
</option>
```

**JavaScript captura o tipo ao coletar payload:**
```javascript
function collectPayload() {
  // Capturar o tipo de planejamento (PEV ou GRV) do option selecionado
  const selectedOption = fieldPlan.selectedOptions[0];
  const planType = selectedOption ? selectedOption.dataset.origin : null;

  return {
    title,
    plan_id: fieldPlan.value || null,
    plan_type: planType,  // ← NOVO!
    // ... outros campos
  };
}
```

---

### 3. Backend - Salva e Consulta com plan_type

**Arquivo:** `app_pev.py`

#### POST - Criar Projeto:
```python
plan_id = payload.get('plan_id')
plan_type = (payload.get('plan_type') or '').strip() or None  # 'PEV' or 'GRV'

cursor.execute("""
    INSERT INTO company_projects (
        company_id, plan_id, plan_type, title, ...
    ) VALUES (?, ?, ?, ?, ...)
""", (company_id, plan_id_value, plan_type, title, ...))
```

#### GET - Listar Projetos:
```sql
SELECT
    p.id,
    p.plan_id,
    p.plan_type,
    CASE 
        WHEN p.plan_type = 'GRV' THEN pf.name
        WHEN p.plan_type = 'PEV' THEN pl.name
        ELSE COALESCE(pf.name, pl.name)
    END AS plan_name,
    p.plan_type AS plan_origin
FROM company_projects p
LEFT JOIN portfolios pf ON pf.id = p.plan_id AND p.plan_type = 'GRV'
LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
WHERE p.company_id = ?
```

**Lógica:**
- Se `plan_type = 'GRV'`, faz JOIN apenas com `portfolios`
- Se `plan_type = 'PEV'`, faz JOIN apenas com `plans`
- `CASE` retorna o nome correto baseado no tipo

#### PUT - Atualizar Projeto:
```python
plan_type = (payload.get('plan_type') or '').strip() or None

cursor.execute("""
    UPDATE company_projects
    SET plan_id = ?, plan_type = ?, title = ?, ...
    WHERE company_id = ? AND id = ?
""", (plan_id_value, plan_type, title, ...))
```

---

## 🧪 Testes de Validação

### Cenário 1: Projeto com Portfolio GRV ID=1
```python
{
  "plan_id": 1,
  "plan_type": "GRV"
}
```
**Resultado:**
- ✅ Origin: "GRV"
- ✅ Name: "Teste Portfolio"
- ✅ Badge: "GRV - Teste Portfolio"

### Cenário 2: Projeto com Planejamento PEV ID=5
```python
{
  "plan_id": 5,
  "plan_type": "PEV"
}
```
**Resultado:**
- ✅ Origin: "PEV"
- ✅ Name: "Planejamento de Crescimento"
- ✅ Badge: "PEV - Planejamento de Crescimento"

### Cenário 3: Conflito de IDs Resolvido
```
ANTES:
- plan_id=5 → Sempre mostrava o Plan PEV (ou Portfolio GRV, dependendo da ordem do JOIN)

DEPOIS:
- plan_id=5 + plan_type='PEV' → Plan PEV "Planejamento de Crescimento"
- plan_id=5 + plan_type='GRV' → Portfolio GRV "Portfolio Teste 200"
```

---

## 📊 Fluxo Completo

### Criação de Projeto:

1. **Usuário seleciona** no dropdown:
   - "PEV - Planejamento de Crescimento" (ID=5)

2. **JavaScript captura:**
   ```javascript
   {
     plan_id: 5,
     plan_type: "PEV"  ← capturado do data-origin
   }
   ```

3. **Backend valida e salva:**
   ```python
   plan_type = 'PEV'  # do payload
   # Salva na tabela com plan_id=5 e plan_type='PEV'
   ```

4. **Query de listagem:**
   ```sql
   -- Como plan_type='PEV', faz JOIN apenas com plans
   LEFT JOIN plans pl ON pl.id = p.plan_id AND p.plan_type = 'PEV'
   -- Retorna nome do plan PEV
   ```

5. **Frontend exibe:**
   ```html
   <span class="project-plan-badge">PEV - Planejamento de Crescimento</span>
   ```

---

## 🎨 Interface Atualizada

### Select do Formulário:
```
┌─────────────────────────────────────────┐
│ Portfólio/Planejamento                  │
├─────────────────────────────────────────┤
│ Sem planejamento vinculado              │
│ PEV - Planejamento de Crescimento ←5    │
│ GRV - Teste Portfolio             ←1    │
│ GRV - Portfolio Teste             ←3    │
│ GRV - Portfolio Teste 200         ←5    │
└─────────────────────────────────────────┘
```

Agora mesmo tendo dois itens com ID=5, cada um é identificado corretamente pelo tipo.

### Card do Projeto:
```
┌─────────────────────────────────────────┐
│ Projeto PEV - Teste Final               │
│ [PEV - Planejamento de Crescimento]     │ ← Correto!
├─────────────────────────────────────────┤
│ Código: AA.J.18                         │
│ Responsável: João Silva                 │
│ Prazo cadastrado: 01/01/2025 – 31/12/2025│
│ Prazo previsto: -                       │
│ Orçamento Total: Não definido           │
└─────────────────────────────────────────┘
```

---

## 📁 Arquivos Modificados

1. ✅ **Banco de Dados**
   - Campo `plan_type` adicionado em `company_projects`

2. ✅ **app_pev.py**
   - POST: Captura e salva `plan_type`
   - PUT: Captura e atualiza `plan_type`
   - GET: JOIN condicional baseado em `plan_type`

3. ✅ **templates/grv_projects_projects.html**
   - JavaScript captura `data-origin` do option selecionado
   - Envia `plan_type` no payload

4. ✅ **modules/grv/__init__.py**
   - Marca plans PEV com `origin='PEV'`
   - Marca portfolios GRV com `origin='GRV'`

---

## ✅ Checklist de Validação

- [x] Campo `plan_type` adicionado ao banco
- [x] Frontend captura origem do option selecionado
- [x] Backend salva `plan_type` corretamente
- [x] JOIN usa `plan_type` para buscar tabela correta
- [x] Portfolio GRV ID=1 funciona corretamente
- [x] Planejamento PEV ID=5 funciona corretamente
- [x] Mesmo com IDs iguais, sistema diferencia PEV de GRV
- [x] Badge exibe origem corretamente
- [x] Link "Abrir no planejamento" só para PEV

---

## 🚀 Próximos Passos

### Migração de Dados Antigos (Opcional):
Os projetos criados antes dessa implementação têm `plan_type=NULL`. Opções:

1. **Deixar NULL:** Funciona, mas não mostra origem no badge
2. **Script de migração:** Identificar automaticamente o tipo baseado no JOIN

```sql
-- Atualizar projetos antigos
UPDATE company_projects
SET plan_type = CASE
    WHEN plan_id IN (SELECT id FROM portfolios WHERE company_id = company_projects.company_id) THEN 'GRV'
    WHEN plan_id IN (SELECT id FROM plans WHERE company_id = company_projects.company_id) THEN 'PEV'
    ELSE NULL
END
WHERE plan_type IS NULL;
```

---

**Data da Implementação:** 11/10/2025  
**Status:** ✅ Totalmente Funcional e Testado

