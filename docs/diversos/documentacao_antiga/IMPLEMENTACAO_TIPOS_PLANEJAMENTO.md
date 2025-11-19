# 🚀 Implementação: Tipos de Planejamento (Evolução vs Implantação)

**Data:** 23/10/2025  
**Status:** ✅ Implementado e pronto para teste

---

## 📋 Contexto

O sistema agora suporta **dois tipos de planejamento estratégico**, cada um com sua interface específica:

### 1. **Planejamento de Evolução** (Clássico)
- **Interface:** `/plans/<id>`
- **Quando usar:** Empresas já operando que querem evoluir estrategicamente
- **Seções:** Dashboard, Participantes, Direcionadores, OKRs Globais, OKRs de Área, Projetos, Relatórios

### 2. **Planejamento de Implantação** (Novo Negócio)
- **Interface:** `/pev/implantacao?plan_id=<id>`
- **Quando usar:** Novos negócios, startups ou projetos de expansão que precisam estruturar do zero
- **Fases:** Alinhamento, Modelo & Mercado, Estruturas de Execução, Entrega

---

## ✅ Alterações Implementadas

### 1. **Modal de Criação Atualizado** (`templates/plan_selector.html`)

#### Campo Adicionado:
```html
<div class="form-group">
  <label for="plan-type">Tipo de Planejamento *</label>
  <select id="plan-type" name="plan_mode" required>
    <option value="">Selecione o tipo</option>
    <option value="evolucao">Planejamento de Evolução (Clássico)</option>
    <option value="implantacao">Planejamento de Implantação (Novo Negócio)</option>
  </select>
  <div id="plan-type-description">
    <!-- Descrição dinâmica baseada na seleção -->
  </div>
</div>
```

#### JavaScript Adicionado:
```javascript
// Listener para exibir descrição ao selecionar tipo
planTypeSelect.addEventListener('change', function() {
  if (selectedType === 'evolucao') {
    // Mostra descrição do Planejamento de Evolução
  } else if (selectedType === 'implantacao') {
    // Mostra descrição do Planejamento de Implantação
  }
});
```

### 2. **Redirecionamento Inteligente** (JavaScript)

Após criar o planejamento, o sistema redireciona automaticamente para a interface correta:

```javascript
if (planMode === 'implantacao') {
  // Interface nova de implantação
  window.location.href = `/pev/implantacao?plan_id=${planId}`;
} else {
  // Interface clássica de evolução
  window.location.href = `/plans/${planId}`;
}
```

### 3. **API Atualizada** (`app_pev.py`)

#### Validação e Salvamento:
```python
# Get plan mode (type of planning)
plan_mode = (payload.get('plan_mode') or '').strip() or 'evolucao'
# Validate plan_mode
if plan_mode not in ['evolucao', 'implantacao']:
    plan_mode = 'evolucao'

plan_data = {
    'company_id': company_id,
    'name': name,
    'description': description,
    'start_date': start_date.isoformat(),
    'end_date': end_date.isoformat(),
    'year': year,
    'status': 'draft',
    'plan_mode': plan_mode  # ← Novo campo
}
```

### 4. **Database Helpers Atualizados**

#### PostgreSQL (`database/postgresql_db.py`):
```python
cursor.execute('''
    INSERT INTO plans (company_id, name, description, start_date, end_date, status, plan_mode)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id
''', (..., plan_data.get('plan_mode', 'evolucao')))
```

#### SQLite (`database/sqlite_db.py`):
```python
# Auto-adiciona coluna se não existir
cursor.execute("PRAGMA table_info(plans)")
columns = {row[1] for row in cursor.fetchall()}
if 'plan_mode' not in columns:
    cursor.execute('ALTER TABLE plans ADD COLUMN plan_mode TEXT DEFAULT "evolucao"')

cursor.execute('''
    INSERT INTO plans (company_id, name, description, start_date, end_date, status, plan_mode)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (..., plan_data.get('plan_mode', 'evolucao')))
```

### 5. **Migration SQL** (`migrations/20251023_add_plan_mode_field.sql`)

```sql
-- Add plan_mode column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'plans' AND column_name = 'plan_mode'
    ) THEN
        ALTER TABLE plans ADD COLUMN plan_mode VARCHAR(32) DEFAULT 'evolucao';
    END IF;
END $$;

-- Update existing plans
UPDATE plans SET plan_mode = 'evolucao' WHERE plan_mode IS NULL;

-- Create index
CREATE INDEX IF NOT EXISTS idx_plans_plan_mode ON plans(plan_mode);
```

---

## 🧪 Como Testar

### Teste 1: Criar Planejamento de Evolução

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
2. Clique no botão **"Novo planejamento"**
3. No modal:
   - **Empresa:** Selecione uma empresa existente
   - **Tipo de Planejamento:** Selecione **"Planejamento de Evolução (Clássico)"**
   - Observe a descrição que aparece abaixo
   - **Nome:** "Teste Evolução 2025"
   - **Descrição:** "Planejamento de teste"
   - **Data de Início:** 2025-01-01
   - **Data de Fim:** 2025-12-31
4. Clique em **"Criar Planejamento"**
5. **Resultado Esperado:**
   - ✅ Mensagem: "Planejamento criado com sucesso!"
   - ✅ Redirecionamento para: `/plans/<id>`
   - ✅ Interface clássica é exibida com Dashboard, Participantes, etc.

### Teste 2: Criar Planejamento de Implantação

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
2. Clique no botão **"Novo planejamento"**
3. No modal:
   - **Empresa:** Selecione uma empresa existente
   - **Tipo de Planejamento:** Selecione **"Planejamento de Implantação (Novo Negócio)"**
   - Observe a descrição que aparece abaixo
   - **Nome:** "Teste Implantação Nova Loja"
   - **Descrição:** "Implantação de novo negócio"
   - **Data de Início:** 2025-03-01
   - **Data de Fim:** 2025-09-30
4. Clique em **"Criar Planejamento"**
5. **Resultado Esperado:**
   - ✅ Mensagem: "Planejamento criado com sucesso!"
   - ✅ Redirecionamento para: `/pev/implantacao?plan_id=<id>`
   - ✅ Interface de implantação é exibida com fases: Alinhamento, Modelo, Execução, Entrega

### Teste 3: Validação de Campos

1. Tente criar planejamento **sem selecionar o tipo**
2. **Resultado Esperado:**
   - ❌ Alerta: "Por favor, selecione o tipo de planejamento"

---

## 📊 Banco de Dados

### Campo Adicionado na Tabela `plans`:

| Campo | Tipo | Padrão | Descrição |
|-------|------|--------|-----------|
| `plan_mode` | VARCHAR(32) / TEXT | 'evolucao' | Tipo do planejamento: 'evolucao' ou 'implantacao' |

### Como Aplicar Migration (PostgreSQL):

```bash
# Desenvolvimento
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/20251023_add_plan_mode_field.sql

# Produção (fazer backup antes!)
pg_dump -h localhost -U postgres bd_app_versus > backup_before_plan_mode_$(date +%Y%m%d_%H%M%S).sql
psql -h localhost -U postgres -d bd_app_versus < migrations/20251023_add_plan_mode_field.sql
```

### Verificar se Migration foi Aplicada:

```sql
-- PostgreSQL
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'plans' AND column_name = 'plan_mode';

-- SQLite (será adicionado automaticamente na primeira criação de plano)
PRAGMA table_info(plans);
```

---

## 🔍 Verificações Importantes

### 1. Verificar Planos Existentes

```sql
-- Ver tipos de planejamentos criados
SELECT id, name, plan_mode, status, created_at
FROM plans
ORDER BY created_at DESC
LIMIT 10;
```

### 2. Testar Ambas as Interfaces

**Interface Clássica (Evolução):**
- URL: `http://127.0.0.1:5003/plans/1`
- Deve mostrar: Dashboard, Participantes, Direcionadores, OKRs, Projetos, Relatórios

**Interface Nova (Implantação):**
- URL: `http://127.0.0.1:5003/pev/implantacao?plan_id=2`
- Deve mostrar: Macro fases (Alinhamento, Modelo, Execução, Entrega)

### 3. Compatibilidade com Planos Antigos

Todos os planos existentes (criados antes desta atualização) receberão automaticamente `plan_mode = 'evolucao'`, mantendo compatibilidade com o comportamento atual.

---

## 📁 Arquivos Modificados

```
✅ templates/plan_selector.html       (+40 linhas) - Modal e JavaScript
✅ app_pev.py                         (+10 linhas) - API de criação
✅ database/postgresql_db.py          (+2 linhas)  - CREATE plan
✅ database/sqlite_db.py              (+12 linhas) - CREATE plan + auto-migration
✅ migrations/20251023_add_plan_mode_field.sql  - Migration SQL
✅ IMPLEMENTACAO_TIPOS_PLANEJAMENTO.md          - Esta documentação
```

---

## 🎯 Próximos Passos

### Após Testar:
1. ✅ Verificar que ambos os tipos criam corretamente
2. ✅ Verificar que o redirecionamento funciona
3. ✅ Aplicar migration em ambiente de desenvolvimento
4. ✅ Testar com empresas reais

### Melhorias Futuras (Opcional):
- [ ] Adicionar filtro por tipo no dashboard
- [ ] Permitir conversão entre tipos (evolução → implantação)
- [ ] Relatórios específicos por tipo de planejamento
- [ ] Templates pré-configurados por tipo

---

## 🚨 Troubleshooting

### Erro: "Coluna plan_mode não existe" (PostgreSQL)

**Solução:**
```bash
# Aplicar migration manualmente
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "ALTER TABLE plans ADD COLUMN IF NOT EXISTS plan_mode VARCHAR(32) DEFAULT 'evolucao';"
```

### Erro: Modal não abre ou campo não aparece

**Solução:**
1. Limpar cache do navegador (Ctrl+Shift+R)
2. Verificar console do navegador (F12) para erros JavaScript
3. Verificar se o template foi atualizado corretamente

### Plano criado mas não redireciona

**Solução:**
1. Verificar console do navegador para erros
2. Verificar se o `plan_id` foi retornado pela API
3. Testar redirecionamento manual:
   - Evolução: `/plans/<id>`
   - Implantação: `/pev/implantacao?plan_id=<id>`

---

## ✅ Checklist de Validação

- [ ] Modal abre corretamente
- [ ] Campo "Tipo de Planejamento" aparece
- [ ] Descrição muda ao selecionar tipo
- [ ] Validação impede criar sem selecionar tipo
- [ ] Planejamento de Evolução cria e redireciona para `/plans/<id>`
- [ ] Planejamento de Implantação cria e redireciona para `/pev/implantacao?plan_id=<id>`
- [ ] Campo `plan_mode` salvo corretamente no banco
- [ ] Migration aplicada sem erros
- [ ] Planos antigos continuam funcionando

---

**Status:** ✅ **PRONTO PARA TESTE**

**Desenvolvido por:** Cursor AI  
**Aprovado para:** Fabiano Ferreira  
**Próximo passo:** Teste pelo usuário e validação em ambiente real

---

## 📞 Suporte

Em caso de dúvidas ou problemas:
1. Verificar este documento
2. Verificar logs do servidor: `docker-compose logs -f app_dev`
3. Verificar console do navegador (F12)
4. Reportar com prints/logs para análise

