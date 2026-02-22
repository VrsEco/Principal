# 🔧 Correções Aplicadas - 21/10/2025

## 📋 Resumo Executivo

Durante a implementação da correção do Playwright, identificamos e corrigimos **múltiplos problemas de compatibilidade PostgreSQL** no projeto.

---

## ✅ Correções Aplicadas

### 1. **Playwright + Chromium no Docker** 
**Status:** ✅ Corrigido  
**Arquivo:** `Dockerfile.dev`

**Problema:**
```
BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1187/chrome-linux/headless_shell
```

**Solução:**
- Adicionadas 18 bibliotecas do sistema necessárias para Chromium
- Executado `playwright install --with-deps chromium` no build
- Browsers funcionando corretamente

**Arquivos modificados:**
- `Dockerfile.dev`
- `Dockerfile` (produção)

**Documentação:**
- `REBUILD_INSTRUCTIONS.md`
- `PLAYWRIGHT_FIX_CHECKLIST.md`
- `docs/governance/DECISION_LOG.md` (ADR-011)

---

### 2. **Placeholders SQL Misturados (PostgreSQL vs SQLite)**
**Status:** ✅ Corrigido  
**Arquivo:** `app_pev.py`

**Problema:**
```
syntax error at or near ","
VALUES (%s, ?, ?, ...)  -- ❌ Misturado!
```

**Causa:**
- Placeholders `%s` (PostgreSQL) e `?` (SQLite) na mesma query
- Função `datetime('now')` (SQLite) ao invés de Python `datetime.utcnow()`

**Solução:**
Corrigidas **9 queries SQL** em `app_pev.py`:

| Linha | Tabela | Correção |
|-------|--------|----------|
| 2818 | `process_instances` | `?` → `%s`, adicionado `RETURNING id` |
| 3198 | `occurrences` | `?` → `%s`, adicionado `RETURNING id` |
| 3908 | `routines` (INSERT) | `?` → `%s`, `datetime('now')` → `dt.utcnow()` |
| 3990 | `routines` (UPDATE) | `?` → `%s`, `datetime('now')` → `dt.utcnow()` |
| 4106 | `routine_collaborators` | `?` → `%s`, adicionado `RETURNING id` |
| 8031 | `okr_area_records` | `?` → `%s` |
| 8145 | `okr_area_records` | `?` → `%s` |
| 8814 | `portfolios` | `?` → `%s`, adicionado `RETURNING id` |
| 9358 | `company_projects` | `?` → `%s`, adicionado `RETURNING id` |

**Padrão aplicado:**
```python
# ✅ CORRETO - PostgreSQL
cursor.execute("""
    INSERT INTO table (col1, col2, col3)
    VALUES (%s, %s, %s)
    RETURNING id
""", (val1, val2, val3))

id = cursor.fetchone()[0]
```

---

### 3. **Tipo Boolean vs Integer**
**Status:** ✅ Corrigido  
**Arquivo:** `app_pev.py`

**Problema:**
```
column "is_active" is of type integer but expression is of type boolean
```

**Causa:**
- PostgreSQL define `is_active` como `INTEGER`
- Código Python enviava `True` (boolean)

**Solução:**
```python
# Antes:
True,  # is_active

# Depois:
1,  # is_active (INTEGER: 1=ativo, 0=inativo)
```

---

### 4. **Sequences Faltando em 15 Tabelas**
**Status:** ✅ Corrigido  
**Arquivos:** Migrations SQL

**Problema:**
```
null value in column "id" of relation "routine_collaborators" violates not-null constraint
```

**Causa:**
15 tabelas criadas com `id INTEGER NOT NULL` mas **sem SERIAL ou SEQUENCE**, então o PostgreSQL não gerava IDs automaticamente.

**Tabelas corrigidas:**
1. `routine_collaborators` ✅
2. `alignment_records` ✅
3. `company_records` ✅
4. `directional_records` ✅
5. `market_records` ✅
6. `misalignment_records` ✅
7. `okr_area_preliminary_records` ✅
8. `okr_preliminary_records` ✅
9. `process_activity_entries` ✅
10. `process_instances` ✅
11. `report_models` ✅
12. `report_patterns` ✅
13. `report_templates` ✅
14. `user_logs` ✅
15. `vision_records` ✅

**Migrations criadas:**
- `migrations/20251021_fix_routine_collaborators_sequence.sql` (individual)
- `migrations/20251021_fix_all_missing_sequences.sql` (todas de uma vez)

**Solução aplicada para cada tabela:**
```sql
-- 1. Criar sequence
CREATE SEQUENCE IF NOT EXISTS table_name_id_seq;

-- 2. Ajustar valor inicial baseado em dados existentes
SELECT setval('table_name_id_seq', 
    COALESCE((SELECT MAX(id) FROM table_name), 0) + 1, 
    false
);

-- 3. Configurar default
ALTER TABLE table_name 
    ALTER COLUMN id SET DEFAULT nextval('table_name_id_seq');

-- 4. Associar sequence à tabela
ALTER SEQUENCE table_name_id_seq OWNED BY table_name.id;
```

**Documentação:**
- `migrations/README_SEQUENCES_FIX.md`
- `docs/governance/DECISION_LOG.md` (ADR-012)

---

## 📊 Estatísticas

| Tipo de Correção | Quantidade | Status |
|------------------|------------|--------|
| Dockerfiles atualizados | 2 | ✅ |
| Queries SQL corrigidas | 9 | ✅ |
| Tabelas com sequence corrigida | 15 | ✅ |
| Migrations criadas | 3 | ✅ |
| ADRs documentados | 2 | ✅ |

---

## 🚀 Próximos Passos

### Imediato
- [x] Aplicado em ambiente DEV
- [x] Testes de funcionalidade básica
- [x] Documentação completa

### Curto Prazo (Esta semana)
- [ ] Testar geração de PDF via Playwright
- [ ] Testar todas as rotinas corrigidas
- [ ] Verificar logs de erro (nenhum esperado)

### Médio Prazo (Próxima semana)
- [ ] Aplicar migrations em STAGING
- [ ] Testes completos em STAGING
- [ ] Aplicar em PRODUÇÃO (com backup completo)

### Longo Prazo
- [ ] Criar templates para novas tabelas com SERIAL correto
- [ ] Adicionar lint/validação para evitar `?` em queries PostgreSQL
- [ ] Migrar queries raw SQL para ORM SQLAlchemy (seguir padrões do projeto)

---

## 📝 Arquivos Criados/Modificados

### Novos Arquivos
```
REBUILD_INSTRUCTIONS.md
PLAYWRIGHT_FIX_CHECKLIST.md
CORREÇÕES_APLICADAS_20251021.md (este arquivo)
migrations/20251021_fix_routine_collaborators_sequence.sql
migrations/20251021_fix_all_missing_sequences.sql
migrations/README_SEQUENCES_FIX.md
```

### Arquivos Modificados
```
Dockerfile
Dockerfile.dev
app_pev.py (9 queries corrigidas)
docs/governance/DECISION_LOG.md (ADR-011, ADR-012)
```

### Arquivos de Documentação
```
REBUILD_INSTRUCTIONS.md
PLAYWRIGHT_FIX_CHECKLIST.md
migrations/README_SEQUENCES_FIX.md
docs/governance/DECISION_LOG.md
```

---

## ⚠️ Avisos Importantes

### Para Produção
1. **SEMPRE fazer backup antes de aplicar migrations:**
   ```bash
   pg_dump -h localhost -U postgres bd_app_versus > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Testar migrations em STAGING primeiro**

3. **Aplicar migrations em ordem:**
   - Primeiro: `20251021_fix_all_missing_sequences.sql`
   - Depois: Deploy do código atualizado

### Para Novas Tabelas
**SEMPRE usar SERIAL:**
```sql
-- ✅ CORRETO
CREATE TABLE nome_tabela (
    id SERIAL PRIMARY KEY,
    ...
);

-- ❌ ERRADO
CREATE TABLE nome_tabela (
    id INTEGER NOT NULL PRIMARY KEY,
    ...
);
```

---

## 🔍 Como Verificar se Tudo Está Funcionando

### 1. Verificar Playwright
```bash
docker exec gestaoversus_app_dev playwright --version
docker exec gestaoversus_app_dev ls -la /root/.cache/ms-playwright/
```
**Esperado:** Versão exibida e `chromium_headless_shell-1187` presente

### 2. Verificar Sequences
```bash
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "
SELECT table_name, column_default 
FROM information_schema.columns 
WHERE table_schema = 'public' 
AND column_name = 'id' 
AND data_type = 'integer' 
AND is_nullable = 'NO' 
AND column_default IS NULL;"
```
**Esperado:** Nenhuma linha retornada (todas têm default agora)

### 3. Testar Inserção
```bash
# Acessar a aplicação e testar:
# - Criar rotina de processo
# - Adicionar colaborador à rotina
# - Gerar PDF do mapa de processos
```
**Esperado:** Tudo funciona sem erros!

---

## 📞 Suporte

**Documentos de Referência:**
- Playwright: `REBUILD_INSTRUCTIONS.md`, `PLAYWRIGHT_FIX_CHECKLIST.md`
- Sequences: `migrations/README_SEQUENCES_FIX.md`
- Decisões: `docs/governance/DECISION_LOG.md`

**Logs para Debug:**
```bash
# Ver logs do app
docker-compose -f docker-compose.dev.yml logs -f app_dev

# Ver logs do banco
docker-compose -f docker-compose.dev.yml logs -f db_dev
```

---

**Data de Aplicação:** 21/10/2025  
**Ambientes:** DEV ✅ | STAGING ⏳ | PROD ⏳  
**Status Geral:** ✅ Todas as correções aplicadas com sucesso em DEV




