# 🔧 Correção - Portfólios GRV

## 🐛 Problemas Identificados

### 1. Erro ao Listar Portfólios
- **Erro:** `405 Method Not Allowed` na rota GET `/api/companies/<id>/portfolios`
- **Causa:** Rota GET não estava definida, apenas POST
- **Sintoma:** Página não carregava portfólios existentes

### 2. Erro ao Criar Portfólio
- **Erro:** `JSON.parse: unexpected character at line 1 column 1`
- **Causa:** Função `_serialize_portfolio()` não existia
- **Sintoma:** Após criar portfólio, retornava erro Python em vez de JSON

### 3. Portfólios GRV não Apareciam em Projetos
- **Problema:** Select de "Portfólio/Planejamento" só mostrava planejamentos PEV
- **Sintoma:** Portfólios criados no GRV não eram opções ao criar projeto

---

## ✅ Correções Aplicadas

### 1. API GET de Portfólios Criada

**Arquivo:** `app_pev.py`

```python
@app.route("/api/companies/<int:company_id>/portfolios", methods=['GET', 'POST'])
def api_company_portfolios(company_id: int):
    """List or create portfolios for a company."""
    if request.method == 'GET':
        # Lista todos os portfólios da empresa
        # JOIN com employees para nome do responsável
        # JOIN com company_projects para contar projetos
        return jsonify({'success': True, 'portfolios': portfolios})
    
    # POST - Create portfolio (já existia)
```

**Retorno do GET:**
```json
{
  "success": true,
  "portfolios": [
    {
      "id": 1,
      "company_id": 5,
      "code": "01",
      "name": "Teste Portfolio",
      "responsible_id": 5,
      "responsible_name": "Fabiano Diretor",
      "notes": "Teste",
      "project_count": 3,
      "created_at": "2025-10-11 04:06:21",
      "updated_at": "2025-10-11 04:06:21"
    }
  ]
}
```

### 2. Função de Serialização Criada

**Arquivo:** `app_pev.py`

```python
def _serialize_portfolio(row: sqlite3.Row) -> Dict[str, Any]:
    """Serialize a portfolio row to a dictionary."""
    return {
        'id': row['id'],
        'company_id': row['company_id'],
        'code': row['code'],
        'name': row['name'],
        'responsible_id': row['responsible_id'],
        'responsible_name': row['responsible_name'],
        'notes': row['notes'],
        'project_count': row['project_count'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }
```

### 3. Integração PEV + GRV em Projetos

**Arquivo:** `modules/grv/__init__.py`

Atualizada a rota `/grv/company/<id>/projects/projects` para:

1. **Buscar planejamentos PEV** (já existia)
2. **Buscar portfólios GRV** (novo)
3. **Marcar cada um com origem:**
   - PEV plans: `{'origin': 'PEV', ...}`
   - GRV portfolios: `{'origin': 'GRV', ...}`
4. **Combinar ambas as listas**

**Código:**
```python
# Get PEV plans
pev_plans = db.get_plans_by_company(company_id) or []

# Get GRV portfolios
conn = sqlite3.connect('instance/pevapp22.db')
cursor.execute("SELECT id, code, name FROM portfolios WHERE company_id = ?", (company_id,))
grv_portfolios = [{'id': r['id'], 'name': r['name'], 'origin': 'GRV'} for r in cursor.fetchall()]

# Mark origins
for plan in pev_plans:
    plan['origin'] = 'PEV'

# Combine
all_plans = pev_plans + grv_portfolios
```

### 4. Select com Origem no Template

**Arquivo:** `templates/grv_projects_projects.html`

**HTML:**
```html
<select id="projectPlan">
  <option value="">Sem planejamento vinculado</option>
  {% for plan in plans %}
  <option value="{{ plan.id }}" data-origin="{{ plan.origin }}">
    {% if plan.origin %}{{ plan.origin }} - {% endif %}{{ plan.name }}
  </option>
  {% endfor %}
</select>
```

**JavaScript:**
```javascript
function populatePlanSelect() {
  plansData.forEach((plan) => {
    const option = document.createElement('option');
    option.value = plan.id;
    option.dataset.origin = plan.origin || '';
    const prefix = plan.origin ? `${plan.origin} - ` : '';
    option.textContent = `${prefix}${plan.name}`;
    fieldPlan.appendChild(option);
  });
}
```

**Resultado no select:**
```
Sem planejamento vinculado
PEV - Planejamento Estratégico 2024
PEV - Planejamento de Crescimento
GRV - Melhoria dos Processos de Manutenção
GRV - Portfolio Teste 200
```

---

## 🎨 Interface Atualizada

### Página de Portfólios
**URL:** `http://127.0.0.1:5002/grv/company/5/projects/portfolios`

✅ **Funcionalidades:**
- Lista todos os portfólios
- Mostra responsável vinculado
- Mostra quantidade de projetos
- Criar/Editar/Excluir portfólios
- JSON válido em todas as operações

### Página de Projetos
**URL:** `http://127.0.0.1:5002/grv/company/5/projects/projects`

✅ **Select "Portfólio/Planejamento" agora mostra:**
- Planejamentos do PEV com prefixo "PEV -"
- Portfólios do GRV com prefixo "GRV -"
- Diferenciação visual clara

---

## 📊 Estrutura de Dados

### Tabela `portfolios`
```sql
CREATE TABLE portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    responsible_id INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (responsible_id) REFERENCES employees(id)
)
```

### Relacionamento com Projetos
- Projetos podem ser vinculados a:
  - **Planejamentos PEV** (via `plan_id`)
  - **Portfólios GRV** (também via `plan_id`, mesma coluna)
- O campo `origin` ajuda a diferenciar na interface

---

## 🔄 Fluxo Completo

### Criar Portfólio GRV:
1. Acesse `/grv/company/5/projects/portfolios`
2. Clique "➕ Novo Portfólio"
3. Preencha código, nome, responsável
4. Salve
5. ✅ Portfólio aparece na lista

### Criar Projeto Vinculado:
1. Acesse `/grv/company/5/projects/projects`
2. Clique "➕ Novo Projeto"
3. No select "Portfólio/Planejamento", veja:
   - `PEV - Nome do Planejamento` (se houver)
   - `GRV - Nome do Portfólio` (portfólios criados)
4. Selecione a origem desejada
5. Salve
6. ✅ Projeto vinculado corretamente

---

## 🧪 Testes Realizados

### GET Portfólios
```bash
curl http://127.0.0.1:5002/api/companies/5/portfolios
```
✅ **Status:** 200 OK
✅ **Retorno:** JSON válido com lista de portfólios

### POST Portfólio
```bash
curl -X POST http://127.0.0.1:5002/api/companies/5/portfolios \
  -H "Content-Type: application/json" \
  -d '{"code":"TEST","name":"Portfolio Teste","responsible_id":5}'
```
✅ **Status:** 201 Created
✅ **Retorno:** JSON com portfólio criado

### Página de Portfólios
✅ Lista carrega sem erros
✅ Cards exibem informações corretas
✅ Modal de criação funciona

### Página de Projetos
✅ Select mostra PEV + GRV
✅ Prefixos corretos (PEV - / GRV -)
✅ Criação de projeto vincula corretamente

---

## 📝 Arquivos Modificados

1. ✅ `app_pev.py`
   - Função `_serialize_portfolio()` criada
   - Rota GET adicionada em `api_company_portfolios()`

2. ✅ `modules/grv/__init__.py`
   - Rota `grv_projects_projects()` atualizada
   - Busca e combina PEV + GRV

3. ✅ `templates/grv_projects_projects.html`
   - HTML do select atualizado
   - JavaScript `populatePlanSelect()` atualizado

---

## ✅ Checklist de Validação

- [x] API GET `/api/companies/<id>/portfolios` funciona
- [x] API POST `/api/companies/<id>/portfolios` retorna JSON válido
- [x] Página de portfólios carrega sem erros
- [x] Portfólios aparecem na lista após criação
- [x] Select em projetos mostra PEV + GRV
- [x] Prefixos "PEV -" e "GRV -" aparecem
- [x] Projetos podem ser vinculados a ambos
- [x] Sem erros no console do navegador

---

**Data da Correção:** 11/10/2025
**Status:** ✅ Totalmente Funcional

