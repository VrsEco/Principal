# 🚀 Guia Rápido: Migração Role Consultant → Collaborator

## ⚡ Execução Rápida (TL;DR)

```bash
# 1. Backup
pg_dump gestaopev > backup_$(date +%Y%m%d).sql

# 2. Aplicar migração
flask db upgrade

# 3. Verificar
flask shell
>>> from models.user import User
>>> User.query.filter_by(role='consultant').count()
0  # ✅ Deve retornar 0

# 4. Reiniciar app
docker-compose restart  # ou systemctl restart gestaopev
```

---

## 📋 O que foi Alterado

### Código (Backend)

| Arquivo | Mudança |
|---------|---------|
| `models/user.py` | Default: `consultant` → `collaborator` |
| `services/my_work_service.py` | + Funções de permissão por role |
| `modules/my_work/routes.py` | + Lógica de filtros por role |
| `services/auth_service.py` | Default atualizado |
| `api/auth.py` | Default atualizado |

### Templates (Frontend)

| Arquivo | Mudança |
|---------|---------|
| `templates/auth/register.html` | Formulário e descrições |
| `templates/auth/users.html` | Mapeamento de roles |
| `templates/auth/profile.html` | Formulário de perfil |

### Migração

| Arquivo | Descrição |
|---------|-----------|
| `migrations/versions/20251203_1000_update_consultant_to_collaborator.py` | Atualiza role no banco |

---

## 🎯 Regras de Permissão (Resumo)

| Perfil | Vê Atividades | Vê Colaboradores | Abas Disponíveis |
|--------|---------------|------------------|------------------|
| **Admin** | Todas de todas as empresas | Todos | Minhas, Equipe, Empresa |
| **Client** | Todas das empresas vinculadas | Das empresas vinculadas | Minhas, Equipe, Empresa |
| **Collaborator** | Apenas as suas | Apenas ele mesmo | Minhas* |

\* *Collaborator: abas Equipe/Empresa retornam vazio ou erro de permissão*

---

## 🔧 Comandos Úteis

### Verificar Estado
```bash
flask db current                    # Ver versão atual
flask db history                    # Ver histórico completo
```

### Aplicar Migração
```bash
flask db upgrade                    # Aplicar todas pendentes
flask db upgrade 20251203_1000     # Aplicar até versão específica
```

### Rollback (Se necessário)
```bash
flask db downgrade -1              # Voltar 1 versão
flask db downgrade 20251201_2200   # Voltar para versão específica
```

### Verificar Dados
```bash
# Via Flask Shell
flask shell
>>> from models.user import User
>>> from sqlalchemy import func
>>> User.query.with_entities(User.role, func.count()).group_by(User.role).all()
[('admin', 2), ('client', 5), ('collaborator', 15)]

# Via SQL direto (PostgreSQL)
psql gestaopev -c "SELECT role, COUNT(*) FROM users GROUP BY role;"

# Via SQL direto (SQLite)
sqlite3 instance/gestaopev.db "SELECT role, COUNT(*) FROM users GROUP BY role;"
```

---

## 🐛 Problemas Comuns

### "Can't locate revision"
```bash
# Aplicar todas as migrações pendentes primeiro
flask db upgrade
```

### "Database is locked" (SQLite)
```bash
# Parar app, migrar, reiniciar
pkill -f "python app_pev.py"
flask db upgrade
python app_pev.py
```

### "Nenhum usuário collaborator aparece"
```bash
# Verificar se migração foi aplicada
flask db current  # Deve mostrar 20251203_1000

# Re-executar se necessário
flask db upgrade
```

---

## 📚 Documentação Completa

- **Migração:** `migrations/README_ROLE_MIGRATION.md`
- **Permissões:** `docs/MYWORK_PERMISSIONS_UPDATE.md`
- **Arquitetura:** `docs/governance/ARCHITECTURE.md`

---

## ✅ Checklist Final

- [ ] Backup realizado
- [ ] Migração aplicada (`flask db upgrade`)
- [ ] Verificado: 0 usuários com `role='consultant'`
- [ ] Aplicação reiniciada
- [ ] Login testado com diferentes perfis
- [ ] MyWork funcionando corretamente

---

**Dúvidas?** Consulte `migrations/README_ROLE_MIGRATION.md` para guia completo.



