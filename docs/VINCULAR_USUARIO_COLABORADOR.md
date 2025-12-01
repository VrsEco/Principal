# 🔗 Como Vincular Usuário a Colaborador Existente

**Cenário:** Você já tem a **Empresa** e o **Colaborador** cadastrados, e precisa criar o **Usuário** e vincular.

---

## 🎯 Passo a Passo Manual

### Passo 1: Criar o Usuário

```python
from models.user import User
from models import db

# Criar usuário
user = User(
    name='Nome do Usuário',
    email='usuario@email.com',
    role='client'  # ou 'admin', 'consultant'
)
user.set_password('senha123')

db.session.add(user)
db.session.commit()

print(f"✅ Usuário criado: ID {user.id}")
```

---

### Passo 2: Buscar o Colaborador Existente

```python
from models.employee import Employee
from models.company import Company

# Buscar empresa
company = Company.query.filter_by(name='Empresa teste 123').first()

# Buscar colaborador sem usuário vinculado
employee = Employee.query.filter_by(
    company_id=company.id,
    user_id=None  # Colaborador sem usuário
).first()

print(f"✅ Colaborador encontrado: ID {employee.id}")
```

---

### Passo 3: Vincular Usuário ao Colaborador

```python
# Vincular
employee.user_id = user.id
employee.name = user.name  # Atualizar nome
employee.email = user.email  # Atualizar email

db.session.commit()

print(f"✅ Vínculo criado: Employee {employee.id} → User {user.id}")
```

---

### Passo 4: Criar/Atribuir Cargo (Role)

```python
from models.role import Role

# Buscar ou criar cargo
role = Role.query.filter_by(
    company_id=company.id,
    title='Administrador'
).first()

if not role:
    # Criar novo cargo
    role = Role(
        company_id=company.id,
        title='Administrador',
        permissions={
            'financial': 'admin',
            'tasks': 'edit',
            'reports': 'view',
            'users': 'admin'
        }
    )
    db.session.add(role)
    db.session.commit()

# Vincular cargo ao colaborador
employee.role_id = role.id
db.session.commit()

print(f"✅ Cargo vinculado: {role.title}")
```

---

### Passo 5: Editar Permissões

```python
# Atualizar permissões do cargo
role.permissions = {
    'financial': 'admin',    # admin, edit, view, none
    'tasks': 'edit',
    'reports': 'view',
    'users': 'admin',
    'projects': 'edit',
    'meetings': 'view'
}

db.session.commit()

print(f"✅ Permissões atualizadas: {role.permissions}")
```

---

## 🚀 Usando o Script Interativo (Recomendado)

Execute o script que criei:

```bash
python vincular_usuario_colaborador.py
```

**Menu:**
1. Vincular novo usuário a colaborador existente
2. Editar permissões de usuário

O script faz tudo automaticamente e de forma segura!

---

## 📊 Estrutura de Permissões

### Níveis de Permissão

- **`admin`** - Acesso total (criar, editar, excluir, visualizar)
- **`edit`** - Pode editar e visualizar
- **`view`** - Apenas visualizar
- **`none`** - Sem acesso

### Módulos Disponíveis

```json
{
  "financial": "admin",    // Financeiro
  "tasks": "edit",         // Tarefas/Atividades
  "reports": "view",       // Relatórios
  "users": "admin",        // Gerenciar usuários
  "projects": "edit",      // Projetos
  "meetings": "view"       // Reuniões
}
```

---

## ⚠️ Validações Importantes

### ✅ Verificar se Email Já Existe

```python
existing = User.query.filter_by(email=email).first()
if existing:
    print("❌ Email já cadastrado!")
    return
```

### ✅ Verificar se Colaborador Já Tem Usuário

```python
if employee.user_id:
    print("⚠ Este colaborador já tem usuário vinculado!")
    print(f"   User ID: {employee.user_id}")
```

### ✅ Usar Transação

```python
try:
    # Operações
    db.session.commit()
except Exception as e:
    db.session.rollback()
    print(f"❌ Erro: {e}")
```

---

## 🔄 Fluxo Completo

```
1. Empresa "Empresa teste 123" (já existe)
   ↓
2. Colaborador (já existe, user_id = NULL)
   ↓
3. Criar USER (novo)
   ↓
4. Vincular: employee.user_id = user.id
   ↓
5. Criar/Buscar ROLE (cargo)
   ↓
6. Vincular: employee.role_id = role.id
   ↓
7. Definir PERMISSIONS no role
   ↓
✅ Pronto! Usuário pode fazer login
```

---

## 💡 Exemplo Completo

```python
from app_pev import app
from models import db
from models.user import User
from models.company import Company
from models.employee import Employee
from models.role import Role

with app.app_context():
    # 1. Buscar empresa
    company = Company.query.filter_by(name='Empresa teste 123').first()
    
    # 2. Buscar colaborador
    employee = Employee.query.filter_by(
        company_id=company.id,
        user_id=None
    ).first()
    
    # 3. Criar usuário
    user = User(
        name='João Silva',
        email='joao@teste.com',
        role='client'
    )
    user.set_password('senha123')
    db.session.add(user)
    db.session.flush()  # Gera ID sem commitar
    
    # 4. Vincular
    employee.user_id = user.id
    
    # 5. Criar cargo
    role = Role(
        company_id=company.id,
        title='Administrador',
        permissions={
            'financial': 'admin',
            'tasks': 'edit',
            'reports': 'view'
        }
    )
    db.session.add(role)
    db.session.flush()
    
    # 6. Vincular cargo
    employee.role_id = role.id
    
    # 7. Commitar tudo
    db.session.commit()
    
    print("✅ Concluído!")
    print(f"   User: {user.email}")
    print(f"   Company: {company.name}")
    print(f"   Role: {role.title}")
```

---

## 🎯 Resumo

**Para o seu caso específico:**

1. ✅ Empresa "Empresa teste 123" - **JÁ EXISTE**
2. ✅ Colaborador - **JÁ EXISTE**
3. ❌ Usuário - **PRECISA CRIAR**
4. ❌ Vínculo - **PRECISA CRIAR**
5. ❌ Permissões - **PRECISA CONFIGURAR**

**Solução mais fácil:**
```bash
python vincular_usuario_colaborador.py
```

Escolha opção 1 e siga as instruções! 🚀
