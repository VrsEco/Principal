# Migração: Atualização de Role Consultant → Collaborator

## 📋 Informações da Migração

**Arquivo:** `versions/20251203_1000_update_consultant_to_collaborator.py`  
**Data:** 03/12/2025  
**Revisão:** 20251203_1000  
**Revisão Anterior:** 20251201_2200

## 🎯 Objetivo

Atualizar o perfil de acesso `consultant` (Consultor) para `collaborator` (Colaborador) em todos os usuários do sistema, como parte da reestruturação de permissões do módulo MyWork.

## ⚠️ IMPORTANTE - Leia antes de executar

### Pré-requisitos:
- ✅ Backup do banco de dados realizado
- ✅ Código atualizado com as mudanças de permissões
- ✅ Ambiente de teste validado
- ✅ Alembic configurado corretamente

### O que a migração faz:
1. Atualiza `role='consultant'` para `role='collaborator'` na tabela `users`
2. Atualiza o campo `updated_at` com timestamp atual
3. Exibe relatório de distribuição de roles após execução

### O que a migração NÃO afeta:
- ❌ Não altera usuários com role `admin`
- ❌ Não altera usuários com role `client`
- ❌ Não cria ou remove usuários
- ❌ Não afeta outras tabelas

---

## 🚀 Como Executar

### Opção 1: Usando Flask-Migrate (Recomendado)

```bash
# 1. Verificar status atual
flask db current

# 2. Ver histórico de migrações
flask db history

# 3. Aplicar a migração
flask db upgrade

# 4. Verificar que foi aplicada
flask db current
```

### Opção 2: Usando Alembic Direto

```bash
# 1. Verificar versão atual
alembic current

# 2. Ver histórico
alembic history

# 3. Aplicar migração
alembic upgrade head

# 4. Verificar
alembic current
```

---

## 🔍 Verificação Pós-Migração

### 1. Verificar via SQL:

**PostgreSQL:**
```sql
SELECT role, COUNT(*) as total_users
FROM users 
GROUP BY role
ORDER BY role;
```

**SQLite:**
```bash
sqlite3 instance/gestaopev.db "SELECT role, COUNT(*) as total_users FROM users GROUP BY role ORDER BY role;"
```

### 2. Verificar via Flask Shell:

```bash
flask shell
```

```python
from models.user import User
from sqlalchemy import func

# Verificar distribuição de roles
result = User.query.with_entities(
    User.role, 
    func.count(User.id).label('total')
).group_by(User.role).all()

for role, total in result:
    print(f"{role}: {total} usuário(s)")

# Verificar se ainda existem 'consultant'
consultant_count = User.query.filter_by(role='consultant').count()
print(f"\nUsuários 'consultant' restantes: {consultant_count}")

# Se quiser ver detalhes dos usuários 'collaborator'
collaborators = User.query.filter_by(role='collaborator').all()
for user in collaborators:
    print(f"- {user.email} ({user.name})")
```

### 3. Verificar via API:

```bash
# Testar endpoint de listagem de usuários (se disponível)
curl -X GET http://localhost:5000/api/auth/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  | jq '.data[] | {email, role}'
```

---

## 🔄 Rollback (Se Necessário)

⚠️ **ATENÇÃO:** Execute rollback apenas se houver problemas imediatos após a migração.

### Opção 1: Flask-Migrate
```bash
flask db downgrade -1
```

### Opção 2: Alembic
```bash
alembic downgrade -1
```

### O que o Rollback faz:
- Reverte `role='collaborator'` para `role='consultant'`
- ⚠️ Pode afetar usuários criados APÓS a migração
- ⚠️ Não recomendado em produção após validação

---

## 📊 Resultado Esperado

Após executar a migração com sucesso, você verá:

```
============================================================
Resultado da migração - Distribuição de roles:
============================================================
  admin: 2 usuário(s)
  client: 5 usuário(s)
  collaborator: 15 usuário(s)
============================================================
```

**Notas:**
- Não deve haver mais nenhum usuário com `role='consultant'`
- O total de usuários deve permanecer o mesmo
- Apenas usuários que tinham `consultant` foram alterados

---

## 🐛 Troubleshooting

### Erro: "Can't locate revision identified by '20251201_2200'"

**Causa:** Migração anterior não foi aplicada.

**Solução:**
```bash
# Ver quais migrações estão pendentes
flask db history

# Aplicar todas as migrações pendentes
flask db upgrade
```

### Erro: "UNIQUE constraint failed"

**Causa:** Possível problema de concorrência ou dados corrompidos.

**Solução:**
```bash
# 1. Verificar integridade dos dados
flask shell
>>> from models.user import User
>>> users = User.query.all()
>>> print(f"Total de usuários: {len(users)}")

# 2. Verificar duplicatas
>>> from sqlalchemy import func
>>> duplicates = User.query.with_entities(
...     User.email, func.count()
... ).group_by(User.email).having(func.count() > 1).all()
>>> print(f"Emails duplicados: {duplicates}")
```

### Erro: "database is locked" (SQLite)

**Causa:** Banco de dados SQLite está em uso.

**Solução:**
```bash
# 1. Parar a aplicação
pkill -f "python app_pev.py"

# 2. Aplicar migração
flask db upgrade

# 3. Reiniciar aplicação
python app_pev.py
```

---

## 📞 Suporte

Se encontrar problemas:

1. **Verificar logs:**
   ```bash
   tail -f logs/app.log
   ```

2. **Consultar documentação completa:**
   - `docs/MYWORK_PERMISSIONS_UPDATE.md`

3. **Verificar estado do banco:**
   ```bash
   flask db current
   flask db history
   ```

4. **Em caso de emergência:**
   - Fazer rollback: `flask db downgrade -1`
   - Restaurar backup: `psql gestaopev < backup_file.sql`

---

## ✅ Checklist Pós-Migração

- [ ] Migração executada sem erros
- [ ] Não há mais usuários com `role='consultant'`
- [ ] Total de usuários permanece o mesmo
- [ ] Aplicação reiniciada com sucesso
- [ ] Testes de login funcionando
- [ ] Permissões do MyWork funcionando corretamente
- [ ] Logs não apresentam erros relacionados a roles
- [ ] Testes com diferentes perfis validados

---

**Última atualização:** 03/12/2025  
**Testado em:** PostgreSQL 13+ e SQLite 3.35+




