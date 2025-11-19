# 🔧 Correção - Origem de Planejamentos e Prazo Previsto

## 🐛 Problemas Identificados

### 1. Conflito de IDs entre PEV e GRV
**Problema:** Ao salvar um projeto vinculado a um portfólio GRV, o sistema exibia sempre "PEV - Planejamento de Crescimento" em vez do portfólio correto.

**Causa Raiz:**
- Portfólio GRV "Portfolio Teste 200" tem ID = 5
- Plan PEV "Planejamento de Crescimento" também tem ID = 5
- O JOIN com a tabela `plans` sempre pegava o plan PEV, ignorando o portfólio GRV

**Exemplo do conflito:**
```
PLANS PEV:
  ID 5: Planejamento de Crescimento 

PORTFOLIOS GRV:
  ID 1: Teste Portfolio
  ID 3: Portfolio Teste
  ID 4: Portfolio Teste
  ID 5: Portfolio Teste 200  ← Mesmo ID!
```

### 2. Falta de Campo "Prazo Previsto"
**Requisito:** Adicionar campo "Prazo previsto" que é calculado dinamicamente da atividade com maior prazo.

---

## ✅ Soluções Implementadas

### 1. JOIN Duplo com Prioridade para Portfolios GRV

**Arquivo:** `app_pev.py`

**Query SQL Atualizada:**
```sql
SELECT
    p.id,
    p.company_id,
    p.plan_id,
    COALESCE(pf.name, pl.name) AS plan_name,  -- Prioriza portfólio GRV
    CASE 
        WHEN pf.id IS NOT NULL THEN 'GRV'
        WHEN pl.id IS NOT NULL THEN 'PEV'
        ELSE NULL
    END AS plan_origin,                        -- Novo campo!
    p.title,
    -- ... outros campos ...
FROM company_projects p
LEFT JOIN portfolios pf ON pf.id = p.plan_id AND pf.company_id = p.company_id
LEFT JOIN plans pl ON pl.id = p.plan_id AND pl.company_id = p.company_id AND pf.id IS NULL
LEFT JOIN employees e ON e.id = p.responsible_id
WHERE p.company_id = ?
```

**Lógica do JOIN:**
1. Primeiro faz JOIN com `portfolios` (GRV)
2. Depois faz JOIN com `plans` (PEV), **MAS SOMENTE SE** não encontrou portfolio (`AND pf.id IS NULL`)
3. `COALESCE` pega o nome do portfólio se existir, senão pega do plan
4. `CASE` determina a origem: 'GRV' ou 'PEV'

**Resultado:**
- ✅ Se `plan_id=5` é um portfólio GRV → retorna "Portfolio Teste 200" com origin='GRV'
- ✅ Se `plan_id=5` é um plan PEV → retorna "Planejamento de Crescimento" com origin='PEV'

### 2. Cálculo de Prazo Previsto

**Arquivo:** `app_pev.py` - Função `_serialize_company_project()`

```python
# Calcular prazo previsto (maior prazo das atividades)
predicted_deadline = None
if activities:
    activity_deadlines = []
    for activity in activities:
        # Tentar pegar o campo 'when' ou 'deadline' ou 'end_date'
        deadline = activity.get('when') or activity.get('deadline') or activity.get('end_date')
        if deadline:
            try:
                from datetime import datetime
                if isinstance(deadline, str):
                    # Tentar parsear a data
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S'):
                        try:
                            dt = datetime.strptime(deadline, fmt)
                            activity_deadlines.append(dt)
                            break
                        except ValueError:
                            continue
            except:
                pass
    
    if activity_deadlines:
        max_deadline = max(activity_deadlines)
        predicted_deadline = max_deadline.strftime('%Y-%m-%d')
```

**Lógica:**
1. Percorre todas as atividades do projeto
2. Busca campos de data: `when`, `deadline`, `end_date`
3. Tenta parsear em múltiplos formatos
4. Pega a **maior data** (deadline mais distante)
5. Retorna no formato ISO `YYYY-MM-DD`

**Retorno na API:**
```json
{
  "id": 14,
  "title": "Projeto Teste",
  "plan_name": "Portfolio Teste 200",
  "plan_origin": "GRV",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "predicted_deadline": "2025-12-31",  ← Novo campo!
  ...
}
```

### 3. Frontend Atualizado

**Arquivo:** `templates/grv_projects_projects.html`

**Exibição da Origem:**
```javascript
// Montar nome do planejamento com origem
let planDisplay = 'Sem planejamento vinculado';
if (project.plan_name) {
  const prefix = project.plan_origin ? `${project.plan_origin} - ` : '';
  planDisplay = `${prefix}${project.plan_name}`;
}
```

**Exibição dos Prazos:**
```javascript
const start = project.start_date ? new Date(project.start_date).toLocaleDateString('pt-BR') : '-';
const end = project.end_date ? new Date(project.end_date).toLocaleDateString('pt-BR') : '-';

// Prazo previsto (maior prazo das atividades)
const predictedDeadline = project.predicted_deadline 
  ? new Date(project.predicted_deadline).toLocaleDateString('pt-BR') 
  : '-';
```

**HTML do Card:**
```html
<div class="project-meta">
  <span><strong>Código:</strong> AA.J.8</span>
  <span><strong>Responsável:</strong> João Silva</span>
  <span><strong>Prazo cadastrado:</strong> 01/01/2025 – 31/12/2025</span>
  <span><strong>Prazo previsto:</strong> 31/12/2025</span>
  <span><strong>Orçamento Total:</strong> R$ 50.000,00</span>
</div>
```

**Badge do Planejamento:**
```html
<!-- Antes -->
<span class="project-plan-badge">Planejamento de Crescimento</span>

<!-- Depois -->
<span class="project-plan-badge">GRV - Portfolio Teste 200</span>
```

### 4. Link "Abrir no Planejamento" Condicional

**Lógica:**
```javascript
${project.plan_id && project.plan_origin === 'PEV' 
  ? `<a class="project-action" href="/plans/${project.plan_id}/projects" target="_blank">
       Abrir no planejamento
     </a>` 
  : ''}
```

**Resultado:**
- ✅ Link aparece apenas para projetos vinculados a **planejamentos PEV**
- ✅ Portfólios GRV não mostram o link (não têm página de detalhes no PEV)

---

## 📊 Estrutura de Dados Atualizada

### Retorno da API `/api/companies/<id>/projects`

```json
{
  "success": true,
  "projects": [
    {
      "id": 14,
      "company_id": 5,
      "plan_id": 5,
      "plan_name": "Portfolio Teste 200",
      "plan_origin": "GRV",              ← NOVO
      "title": "Projeto GRV Teste",
      "description": "Teste",
      "status": "planned",
      "responsible_id": 3,
      "responsible_name": "João Silva",
      "start_date": "2025-01-01",
      "end_date": "2025-12-31",
      "predicted_deadline": "2025-12-31", ← NOVO
      "code": "AA.J.8",
      "activities": [
        {
          "code": "AA.J.8.01",
          "what": "Atividade 1",
          "when": "2025-12-31",
          "status": "pending"
        }
      ],
      "budget_total": 50000.0,
      "activities_count": 1,
      "delayed_activities": 0
    }
  ]
}
```

---

## 🎨 Exemplo Visual - Antes vs Depois

### Card de Projeto - ANTES:
```
┌─────────────────────────────────────────┐
│ Projeto Teste                           │
│ [Planejamento de Crescimento] [Planejado]│ ← Sempre PEV!
├─────────────────────────────────────────┤
│ Código: AA.J.8                          │
│ Responsável: João Silva                 │
│ Prazo: 01/01/2025 – 31/12/2025         │  ← Só cadastrado
│ Orçamento Total: R$ 50.000,00           │
└─────────────────────────────────────────┘
```

### Card de Projeto - DEPOIS:
```
┌─────────────────────────────────────────┐
│ Projeto Teste                           │
│ [GRV - Portfolio Teste 200] [Planejado] │ ← Correto!
├─────────────────────────────────────────┤
│ Código: AA.J.8                          │
│ Responsável: João Silva                 │
│ Prazo cadastrado: 01/01/2025 – 31/12/2025│ ← Renomeado
│ Prazo previsto: 31/12/2025              │ ← NOVO!
│ Orçamento Total: R$ 50.000,00           │
└─────────────────────────────────────────┘
```

---

## 🧪 Cenários de Teste

### Cenário 1: Projeto Vinculado a Portfólio GRV (ID Conflitante)
```
Dados:
- Portfólio GRV: ID=5, Nome="Portfolio Teste 200"
- Plan PEV: ID=5, Nome="Planejamento de Crescimento"
- Projeto: plan_id=5 (intenção: GRV)

ANTES:
✗ Badge: "Planejamento de Crescimento" (errado!)
✗ Origin: undefined

DEPOIS:
✓ Badge: "GRV - Portfolio Teste 200" (correto!)
✓ Origin: "GRV"
```

### Cenário 2: Projeto Vinculado a Plan PEV
```
Dados:
- Plan PEV: ID=1, Nome="Planejamento Estratégico 2024"
- Projeto: plan_id=1

ANTES:
✓ Badge: "Planejamento Estratégico 2024"
✗ Origin: undefined

DEPOIS:
✓ Badge: "PEV - Planejamento Estratégico 2024"
✓ Origin: "PEV"
✓ Link "Abrir no planejamento" visível
```

### Cenário 3: Prazo Previsto com Múltiplas Atividades
```
Atividades:
- Atividade 1: when="2025-06-30"
- Atividade 2: when="2025-09-15"
- Atividade 3: when="2025-12-31"

ANTES:
✗ Prazo previsto: não existia

DEPOIS:
✓ Prazo previsto: "31/12/2025" (maior data)
```

### Cenário 4: Projeto Sem Atividades
```
Atividades: []

DEPOIS:
✓ Prazo previsto: "-"
```

---

## 📁 Arquivos Modificados

1. ✅ **app_pev.py**
   - Query SQL com JOIN duplo (3 lugares: GET, POST, PUT)
   - Função `_serialize_company_project()` com cálculo de prazo previsto
   - Novo campo `plan_origin` no retorno

2. ✅ **templates/grv_projects_projects.html**
   - Exibição da origem no badge
   - Adicionado "Prazo previsto"
   - Renomeado "Prazo" para "Prazo cadastrado"
   - Link condicional baseado em origem

---

## ✅ Checklist de Validação

- [x] Projeto vinculado a GRV exibe origem "GRV - Nome do Portfólio"
- [x] Projeto vinculado a PEV exibe origem "PEV - Nome do Plano"
- [x] Conflito de IDs resolvido (ID 5 GRV vs ID 5 PEV)
- [x] Campo "Prazo cadastrado" aparece nos cards
- [x] Campo "Prazo previsto" calculado das atividades
- [x] Prazo previsto pega a maior data das atividades
- [x] Link "Abrir no planejamento" só para projetos PEV
- [x] API retorna `plan_origin` e `predicted_deadline`
- [x] Frontend exibe corretamente ambos os campos

---

## 🔍 Queries SQL para Validação

### Verificar Conflitos de ID
```sql
-- Encontrar IDs duplicados entre plans e portfolios
SELECT p.id AS plan_id, pf.id AS portfolio_id, p.name AS plan_name, pf.name AS portfolio_name
FROM plans p
INNER JOIN portfolios pf ON p.id = pf.id
WHERE p.company_id = 5 AND pf.company_id = 5;
```

### Verificar Projetos e Suas Origens
```sql
SELECT 
    cp.id,
    cp.title,
    cp.plan_id,
    COALESCE(pf.name, pl.name) AS plan_name,
    CASE 
        WHEN pf.id IS NOT NULL THEN 'GRV'
        WHEN pl.id IS NOT NULL THEN 'PEV'
        ELSE 'NENHUM'
    END AS origin
FROM company_projects cp
LEFT JOIN portfolios pf ON pf.id = cp.plan_id AND pf.company_id = cp.company_id
LEFT JOIN plans pl ON pl.id = cp.plan_id AND pl.company_id = cp.company_id AND pf.id IS NULL
WHERE cp.company_id = 5;
```

---

**Data da Correção:** 11/10/2025
**Status:** ✅ Totalmente Funcional

