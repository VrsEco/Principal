# Atualização de Permissões do MyWork

**Data:** 03/12/2025  
**Versão:** 1.0

## 📋 Resumo das Mudanças

Este documento descreve as alterações implementadas no sistema de permissões do módulo MyWork, incluindo a renomeação do perfil "Consultor" para "Colaborador" e a implementação de regras de visualização baseadas em perfis de usuário.

---

## 🔄 Mudanças Implementadas

### 1. Renomeação de Perfil: Consultor → Colaborador

**Arquivos Modificados:**
- `models/user.py` - Alterado default de 'consultant' para 'collaborator'
- `services/auth_service.py` - Atualizado default e documentação
- `api/auth.py` - Atualizado default no registro
- `services/user_employee_service.py` - Atualizada documentação
- `templates/auth/register.html` - Atualizado formulário e descrições
- `templates/auth/users.html` - Atualizado CSS e mapeamento de roles
- `templates/auth/profile.html` - Atualizado formulário de perfil

**Compatibilidade com Dados Legados:**
- O sistema mantém compatibilidade com registros antigos que possuem 'consultant'
- A normalização é feita automaticamente: `consultant` → `collaborator`
- Templates e JavaScript incluem fallback para dados legados

---

### 2. Implementação de Regras de Permissão

#### **Perfil: Administrador (admin)**

**Permissões:**
- ✅ Visualiza **todas as atividades** de **todas as empresas**
- ✅ Visualiza **todos os colaboradores** de todas as empresas
- ✅ Acesso completo aos filtros (empresas, colaboradores, projetos, processos)
- ✅ Pode usar as abas: "Minhas", "Equipe" e "Empresa"

**Comportamento:**
- Quando nenhuma empresa é selecionada, o sistema busca **todas as empresas** automaticamente
- Pode filtrar por qualquer empresa, colaborador ou projeto

---

#### **Perfil: Cliente (client)**

**Permissões:**
- ✅ Visualiza atividades de **todos os usuários** das **empresas vinculadas**
- ✅ Visualiza **todos os colaboradores** das empresas vinculadas
- ✅ Acesso aos filtros das empresas vinculadas
- ✅ Pode usar as abas: "Minhas", "Equipe" e "Empresa"

**Comportamento:**
- Vê apenas empresas às quais está vinculado (via tabela `employees`)
- Pode filtrar por colaboradores dessas empresas
- Tem visão completa das atividades das empresas vinculadas

---

#### **Perfil: Colaborador (collaborator)**

**Permissões:**
- ✅ Visualiza **apenas atividades atribuídas a ele** (responsável ou executor)
- ⚠️ Nos filtros de colaboradores, vê **apenas ele mesmo**
- ⚠️ **NÃO** pode acessar a aba "Empresa"
- ⚠️ A aba "Equipe" retorna vazio (sem membros de equipe configurados)

**Comportamento:**
- O scope é **forçado para 'me'** (minhas atividades)
- Mesmo que tente acessar outras abas, sempre retorna apenas suas atividades
- Filtros de colaboradores mostram apenas o próprio usuário
- Vê empresas vinculadas, mas apenas suas próprias atividades nelas

---

### 3. Arquivos Modificados

#### **Backend - Services**

**`services/my_work_service.py`:**
```python
# Nova função para obter role do usuário
def _get_user_role_from_employee(employee_id: int) -> Optional[str]

# Função de permissão atualizada
def _can_view_company(cursor, employee_id: int) -> bool
    # Agora verifica role: admin e client podem ver, collaborator não

# Função de filtros atualizada
def get_filter_options(user_id: int) -> Dict[str, List[Dict[str, Any]]]
    # Admin: todas as empresas e colaboradores
    # Client: empresas vinculadas e seus colaboradores
    # Collaborator: empresas vinculadas, mas apenas ele nos colaboradores
```

#### **Backend - Routes**

**`modules/my_work/routes.py`:**
```python
@my_work_bp.route("/api/activities")
def get_activities():
    # Obtém role do usuário
    user_role = current_user.role
    
    # Admin sem filtro: busca TODAS as empresas
    if user_role == 'admin' and not company_ids:
        company_ids = [todas as empresas]
    
    # Collaborator: força scope='me' e filtra apenas ele
    if user_role == 'collaborator':
        scope = 'me'
        employee_ids = [apenas o próprio employee_id]
```

---

## 🗄️ Migração de Dados

**Arquivo:** `migrations/versions/20251203_1000_update_consultant_to_collaborator.py`

Esta é uma migração Alembic que atualiza automaticamente o campo `role` de 'consultant' para 'collaborator' em todos os usuários.

### Como executar a migração:

#### 1. Verificar migrações pendentes:
```bash
flask db current
```

#### 2. Aplicar a migração:
```bash
flask db upgrade
```

Ou usando alembic diretamente:
```bash
alembic upgrade head
```

#### 3. Verificar resultado:
A migração exibirá automaticamente a distribuição de roles após a execução:
```
============================================================
Resultado da migração - Distribuição de roles:
============================================================
  admin: 2 usuário(s)
  client: 5 usuário(s)
  collaborator: 10 usuário(s)
============================================================
```

### Rollback (se necessário):
```bash
flask db downgrade -1
```

Ou:
```bash
alembic downgrade -1
```

**⚠️ ATENÇÃO:** O downgrade não é recomendado em produção após a migração ter sido testada e validada.

---

## 🧪 Testes Recomendados

### Teste 1: Perfil Administrador

**Cenário:** Usuário com role='admin'

**Passos:**
1. Login como administrador
2. Acessar MyWork
3. **Sem selecionar empresa:** Verificar que aparecem atividades de TODAS as empresas
4. Selecionar uma empresa específica: Verificar que filtra corretamente
5. Verificar filtro de colaboradores: Deve mostrar TODOS os colaboradores de todas as empresas
6. Verificar abas: "Minhas", "Equipe" e "Empresa" devem funcionar

**Resultado Esperado:**
- ✅ Vê todas as atividades quando nenhuma empresa selecionada
- ✅ Filtros funcionam corretamente
- ✅ Todas as abas acessíveis

---

### Teste 2: Perfil Cliente

**Cenário:** Usuário com role='client' vinculado a 2 empresas (Empresa A e Empresa B)

**Passos:**
1. Login como cliente
2. Acessar MyWork
3. Verificar seletor de empresas: Deve mostrar apenas Empresa A e Empresa B
4. Selecionar Empresa A: Verificar que aparecem atividades de TODOS os colaboradores da Empresa A
5. Verificar filtro de colaboradores: Deve mostrar todos os colaboradores das empresas vinculadas
6. Verificar abas: "Minhas", "Equipe" e "Empresa" devem funcionar

**Resultado Esperado:**
- ✅ Vê apenas empresas vinculadas
- ✅ Vê atividades de todos os colaboradores das empresas vinculadas
- ✅ Todas as abas acessíveis

---

### Teste 3: Perfil Colaborador

**Cenário:** Usuário com role='collaborator' vinculado à Empresa A

**Passos:**
1. Login como colaborador
2. Acessar MyWork
3. Verificar seletor de empresas: Deve mostrar Empresa A
4. Selecionar Empresa A: Verificar que aparecem APENAS as atividades atribuídas a ele
5. Verificar filtro de colaboradores: Deve mostrar APENAS ele mesmo
6. Tentar acessar aba "Empresa": Deve retornar erro de permissão ou vazio
7. Verificar aba "Equipe": Deve retornar vazio (sem equipe configurada)

**Resultado Esperado:**
- ✅ Vê apenas empresas vinculadas
- ✅ Vê APENAS suas próprias atividades
- ✅ Filtro de colaboradores mostra apenas ele mesmo
- ⚠️ Aba "Empresa" não acessível ou vazia

---

### Teste 4: Compatibilidade com Dados Legados

**Cenário:** Usuário com role='consultant' (não migrado)

**Passos:**
1. Criar usuário com role='consultant' diretamente no banco (sem executar migration)
2. Login com esse usuário
3. Verificar comportamento

**Resultado Esperado:**
- ✅ Sistema trata 'consultant' como 'collaborator'
- ✅ Permissões de colaborador são aplicadas
- ✅ Interface mostra "Colaborador" mesmo com 'consultant' no banco

---

### Teste 5: Filtros Avançados

**Cenário:** Testar filtros com diferentes perfis

**Passos para cada perfil:**
1. Filtrar por colaborador específico
2. Filtrar por projeto específico
3. Filtrar por processo específico
4. Filtrar por data de vencimento
5. Combinar múltiplos filtros

**Resultado Esperado:**
- ✅ Admin: Todos os filtros funcionam sem restrições
- ✅ Client: Filtros funcionam dentro das empresas vinculadas
- ✅ Collaborator: Filtros sempre retornam apenas suas atividades

---

## 🔍 Verificações de Segurança

### Verificar que Collaborator NÃO pode:
- [ ] Ver atividades de outros colaboradores
- [ ] Acessar visão de empresa
- [ ] Filtrar por outros colaboradores
- [ ] Burlar permissões via API (testar chamadas diretas)

### Verificar que Client NÃO pode:
- [ ] Ver empresas não vinculadas
- [ ] Ver colaboradores de outras empresas
- [ ] Acessar atividades de empresas não vinculadas

### Verificar que Admin PODE:
- [ ] Ver todas as empresas
- [ ] Ver todos os colaboradores
- [ ] Acessar todas as atividades
- [ ] Usar todos os filtros sem restrições

---

## 📝 Notas Importantes

### Normalização de Role
O sistema normaliza automaticamente `consultant` → `collaborator` em:
- `services/my_work_service.py::_get_user_role_from_employee()`
- `services/my_work_service.py::get_filter_options()`
- `modules/my_work/routes.py::get_activities()`

### Compatibilidade
- Templates incluem fallback para 'consultant' nos mapeamentos JavaScript
- Formulários aceitam 'collaborator' como padrão
- Dados legados continuam funcionando até a migração

### Performance
- Admin sem filtro de empresa pode ter queries mais pesadas (busca todas as empresas)
- Considerar adicionar paginação se houver muitas empresas

---

## 🚀 Deploy

### Checklist de Deploy:

1. **Backup do Banco de Dados**
   ```bash
   # PostgreSQL
   pg_dump gestaopev > backup_pre_migration_$(date +%Y%m%d).sql
   
   # SQLite (se aplicável)
   cp instance/gestaopev.db instance/gestaopev_backup_$(date +%Y%m%d).db
   ```

2. **Verificar Estado das Migrações**
   ```bash
   flask db current
   flask db history
   ```

3. **Deploy do Código**
   - Fazer backup dos arquivos atuais
   - Fazer pull/copiar novos arquivos
   - Verificar que o arquivo de migração está presente:
     `migrations/versions/20251203_1000_update_consultant_to_collaborator.py`

4. **Executar Migration**
   ```bash
   flask db upgrade
   ```
   
   Ou usando alembic diretamente:
   ```bash
   alembic upgrade head
   ```

5. **Verificar Resultado da Migration**
   A migração exibirá automaticamente os resultados.
   
   Para verificar manualmente:
   ```bash
   flask shell
   >>> from models.user import User
   >>> User.query.with_entities(User.role, func.count()).group_by(User.role).all()
   ```

6. **Reiniciar Aplicação**
   ```bash
   # Docker
   docker-compose restart
   
   # Systemd
   systemctl restart gestaopev
   
   # Manual
   pkill -f "python app_pev.py"
   python app_pev.py
   ```

7. **Testes Pós-Deploy**
   - Executar todos os testes descritos acima
   - Verificar logs de erro: `tail -f logs/app.log`
   - Monitorar performance
   - Validar permissões com usuários de teste

---

## 📞 Suporte

Em caso de problemas:

1. Verificar logs da aplicação: `logs/app.log`
2. Verificar role do usuário: `SELECT id, email, role FROM users WHERE email = '...'`
3. Verificar vinculação de employee: `SELECT * FROM employees WHERE user_id = ...`
4. Testar API diretamente: `/my-work/api/filter-options`

---

## 📚 Referências

- **Governança:** `/docs/governance/ARCHITECTURE.md`
- **Padrões de Código:** `/docs/governance/CODING_STANDARDS.md`
- **Modelo User:** `models/user.py`
- **Service MyWork:** `services/my_work_service.py`
- **Routes MyWork:** `modules/my_work/routes.py`

---

**Última Atualização:** 03/12/2025  
**Autor:** Cursor AI  
**Revisão:** Pendente

