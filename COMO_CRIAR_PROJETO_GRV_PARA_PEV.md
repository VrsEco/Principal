# Como Criar Projeto GRV para Planejamento PEV

**Data:** 24/10/2025  
**Status:** ✅ Documentado

---

## 📋 Contexto

Quando um planejamento PEV é criado, idealmente um projeto GRV deve ser criado automaticamente e vinculado a ele. No entanto, para planejamentos antigos ou casos onde a criação automática falhou, é possível criar manualmente.

---

## 🔄 Processo Automático (Ideal)

Ao criar um planejamento PEV via interface, o sistema automaticamente:

1. Cria o planejamento na tabela `plans`
2. Cria um projeto GRV na tabela `company_projects` vinculado ao planejamento
3. Define `plan_type = 'PEV'` e `plan_id = [id do planejamento]`

**Código:** `app_pev.py` - função `api_create_plan()`

---

## 🛠️ Criação Manual (quando necessário)

### Método 1: Via Interface Web

1. Acesse a lista de projetos GRV:
   ```
   http://127.0.0.1:5003/grv/company/[COMPANY_ID]/projects/projects
   ```

2. Clique em "➕ Novo Projeto"

3. Preencha o formulário:
   - **Título:** Nome do projeto
   - **Portfólio/Planejamento:** Selecione o planejamento PEV desejado
   - **Responsável:** Selecione um colaborador
   - **Datas:** Início e término
   - Outros campos opcionais

4. Clique em "Salvar Projeto"

### Método 2: Via Script Python

```python
from database.postgres_helper import connect as pg_connect
from datetime import datetime

def create_project_for_plan(plan_id: int):
    conn = pg_connect()
    cursor = conn.cursor()
    
    # 1. Buscar dados do planejamento
    cursor.execute("""
        SELECT p.id, p.company_id, p.name, p.start_date, p.end_date,
               c.client_code
        FROM plans p
        JOIN companies c ON c.id = p.company_id
        WHERE p.id = %s
    """, (plan_id,))
    
    plan = dict(cursor.fetchone())
    company_id = plan['company_id']
    
    # 2. Gerar código do projeto
    cursor.execute(
        'SELECT MAX(code_sequence) as max_seq FROM company_projects WHERE company_id = %s',
        (company_id,)
    )
    result = cursor.fetchone()
    next_sequence = (result['max_seq'] or 0) + 1
    project_code = f"{plan['client_code']}.J.{next_sequence}"
    
    # 3. Criar projeto
    cursor.execute("""
        INSERT INTO company_projects (
            company_id, plan_id, plan_type, title, description,
            priority, start_date, end_date, code, code_sequence,
            activities, notes, created_at, updated_at
        ) VALUES (%s, %s, 'PEV', %s, %s, 'medium', %s, %s, %s, %s, '[]', %s, %s, %s)
        RETURNING id
    """, (
        company_id,
        plan_id,
        f"{plan['name']} - Projeto de Implantacao",
        f"Projeto vinculado ao planejamento {plan['name']}",
        plan['start_date'],
        plan['end_date'],
        project_code,
        next_sequence,
        f"Projeto criado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        datetime.now(),
        datetime.now()
    ))
    
    project_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    
    return project_id
```

### Método 3: Via SQL Direto

```sql
-- 1. Verificar se planejamento existe
SELECT id, name, company_id FROM plans WHERE id = 8;

-- 2. Verificar se já tem projeto vinculado
SELECT id, title, code 
FROM company_projects 
WHERE plan_id = 8 AND plan_type = 'PEV';

-- 3. Buscar próxima sequência de código
SELECT MAX(code_sequence) as max_seq 
FROM company_projects 
WHERE company_id = [COMPANY_ID];

-- 4. Criar projeto
INSERT INTO company_projects (
    company_id, plan_id, plan_type, title, description,
    priority, start_date, end_date, code, code_sequence,
    activities, notes, created_at, updated_at
) VALUES (
    [COMPANY_ID],
    8,
    'PEV',
    'Nome do Projeto - Projeto de Implantacao',
    'Descricao do projeto',
    'medium',
    '2025-10-20',
    '2026-03-31',
    'XX.J.1',  -- Código gerado
    1,         -- Sequência
    '[]',      -- Activities (JSON vazio)
    'Projeto criado manualmente',
    NOW(),
    NOW()
) RETURNING id;
```

---

## 🔍 Como Verificar Planejamentos Existentes

### Via SQL:

```sql
SELECT 
    p.id,
    p.name,
    p.company_id,
    c.name as company_name,
    c.client_code,
    p.start_date,
    p.end_date,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM company_projects cp 
            WHERE cp.plan_id = p.id AND cp.plan_type = 'PEV'
        ) THEN 'Com projeto'
        ELSE 'Sem projeto'
    END as status_projeto
FROM plans p
LEFT JOIN companies c ON c.id = p.company_id
ORDER BY p.id DESC;
```

### Via Interface:

1. **Lista de Planejamentos:** http://127.0.0.1:5003/plans
2. **Planejamento específico:** http://127.0.0.1:5003/pev/implantacao?plan_id=[ID]

---

## 📊 Estrutura do Projeto GRV

### Campos Principais:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `id` | ID único do projeto | 44 |
| `company_id` | ID da empresa | 25 |
| `plan_id` | ID do planejamento vinculado | 6 |
| `plan_type` | Tipo do planejamento | 'PEV' ou 'GRV' |
| `title` | Título do projeto | "Concepção Empresa - Projeto" |
| `code` | Código automático | "AS.J.1" |
| `code_sequence` | Sequência numérica | 1 |
| `start_date` | Data de início | 2025-10-20 |
| `end_date` | Data de término | 2026-03-31 |
| `priority` | Prioridade | 'high', 'medium', 'low' |
| `responsible_id` | ID do responsável | NULL ou ID do colaborador |
| `activities` | Lista de atividades (JSON) | '[]' |

---

## 🎯 Exemplo Real de Criação

**Data:** 24/10/2025

### Planejamento PEV:
- **ID:** 6
- **Nome:** Concepção Empresa de Móveis - EUA
- **Empresa:** Eua - Moveis Planejados (ID: 25, Código: AS)
- **Período:** 2025-10-20 até 2026-03-31

### Projeto GRV Criado:
- **ID:** 44
- **Código:** AS.J.1
- **Título:** Concepção Empresa de Móveis - EUA - Projeto de Implantacao
- **Link Kanban:** http://127.0.0.1:5003/grv/company/25/projects/44/manage
- **Link Lista:** http://127.0.0.1:5003/grv/company/25/projects/projects

---

## 🔗 Links Úteis

- **Documentação GRV Projetos:** `RESUMO_IMPLEMENTACAO_PROJETOS_GRV.md`
- **Guia de Uso:** `COMO_USAR_SISTEMA_PROJETOS.md`
- **API Endpoints:** `app_pev.py` - linhas 9351-9592

---

## ⚠️ Troubleshooting

### Planejamento ID não encontrado

**Problema:** "Planejamento ID X não encontrado"

**Solução:**
1. Verificar se o planejamento existe no banco
2. Verificar se está usando o banco correto (PostgreSQL vs SQLite)
3. Listar todos os planejamentos disponíveis

### Projeto já existe para o planejamento

**Problema:** "Já existe um projeto vinculado"

**Solução:**
- Verificar na lista de projetos GRV
- Decidir se quer criar um novo projeto ou usar o existente
- Se criar novo, confirmar explicitamente no script

### Código de projeto duplicado

**Problema:** Erro de constraint unique em `code`

**Solução:**
- O sistema gera código automaticamente baseado em `MAX(code_sequence)`
- Se erro persistir, verificar manualmente a sequência:
  ```sql
  SELECT MAX(code_sequence) FROM company_projects WHERE company_id = X;
  ```

---

**Última atualização:** 24/10/2025  
**Responsável:** Cursor AI Assistant

