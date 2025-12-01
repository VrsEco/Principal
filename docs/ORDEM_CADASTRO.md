# 📋 Ordem Correta de Cadastro - Sistema User-Employee-Company

**Data:** 26/11/2025  
**Versão:** 1.0

---

## 🎯 Cenários de Cadastro

Existem **3 cenários principais** de cadastro no sistema. Veja qual se aplica ao seu caso:

---

## 📌 Cenário 1: Novo Cliente se Cadastrando (Mais Comum)

**Situação:** Pessoa física ou empresa se cadastrando pela primeira vez no sistema.

### Ordem de Cadastro (AUTOMÁTICA)

```
1. USER (Credenciais)
   ↓
2. COMPANY (Empresa)
   ↓
3. EMPLOYEE (Vínculo automático)
```

### Como Fazer

**Opção A: Via API (Recomendado)**
```python
from services.user_employee_service import UserEmployeeService

result = UserEmployeeService.create_user_with_company(
    user_data={
        'name': 'João Silva',
        'email': 'joao@empresa.com',
        'password': 'senha123',
        'role': 'client'  # Opcional, padrão é 'client'
    },
    company_data={
        'name': 'Tech Solutions Ltda',
        'legal_name': 'Tech Solutions Tecnologia Ltda',
        'cnpj': '12.345.678/0001-90',
        'segment': 'Tecnologia',
        'city': 'São Paulo',
        'state': 'SP'
    },
    employee_data={  # Opcional
        'phone': '(11) 98765-4321',
        'department': 'Diretoria'
    }
)

# Resultado:
# {
#   'success': True,
#   'user': {...},      # User criado
#   'company': {...},   # Company criada
#   'employee': {...}   # Employee criado automaticamente
# }
```

**Opção B: Via Endpoint REST**
```bash
POST /api/user-employee/register
Content-Type: application/json

{
  "user": {
    "name": "João Silva",
    "email": "joao@empresa.com",
    "password": "senha123"
  },
  "company": {
    "name": "Tech Solutions Ltda",
    "cnpj": "12.345.678/0001-90"
  }
}
```

### ✅ Vantagens
- **Tudo em uma transação** (se falhar, nada é criado)
- **Vínculo automático** (não precisa criar Employee manualmente)
- **Seguro** (rollback automático em caso de erro)

---

## 📌 Cenário 2: Adicionar Usuário Existente em Nova Empresa

**Situação:** Consultor que já tem cadastro e vai atender uma nova empresa.

### Ordem de Cadastro

```
1. COMPANY (Se ainda não existe)
   ↓
2. EMPLOYEE (Vincular User existente à Company)
```

### Como Fazer

**Passo 1: Verificar se a empresa existe**
```python
from models.company import Company

company = Company.query.filter_by(cnpj='98.765.432/0001-10').first()

if not company:
    # Criar empresa
    company = Company(
        name='Consultoria ABC',
        cnpj='98.765.432/0001-10'
    )
    db.session.add(company)
    db.session.commit()
```

**Passo 2: Adicionar usuário como colaborador**
```python
from services.user_employee_service import UserEmployeeService

result = UserEmployeeService.add_employee_to_company(
    user_id=5,              # ID do usuário existente
    company_id=company.id,  # ID da empresa
    role_id=3,              # Opcional: ID do cargo
    employee_data={         # Opcional
        'department': 'Consultoria',
        'weekly_hours': 20
    }
)
```

**Ou via API:**
```bash
POST /api/user-employee/add-to-company
Content-Type: application/json
Authorization: Bearer <token>

{
  "user_id": 5,
  "company_id": 10,
  "role_id": 3
}
```

### ✅ Vantagens
- **Reutiliza credenciais** (mesmo login para múltiplas empresas)
- **Permissões independentes** (pode ser admin em uma e viewer em outra)

---

## 📌 Cenário 3: Funcionário Sem Acesso ao Sistema

**Situação:** Cadastrar funcionário que aparece no organograma mas não faz login.

### Ordem de Cadastro

```
1. COMPANY (Deve existir)
   ↓
2. EMPLOYEE (Sem user_id)
```

### Como Fazer

```python
from services.user_employee_service import UserEmployeeService

result = UserEmployeeService.create_employee_without_user(
    company_id=10,
    employee_data={
        'name': 'Maria Santos',
        'email': 'maria@empresa.com',  # Opcional
        'phone': '(11) 91234-5678',
        'department': 'Operações',
        'role_id': 5  # Opcional
    }
)

# Resultado:
# {
#   'success': True,
#   'employee': {
#       'id': 20,
#       'user_id': None,  # ← Sem vínculo com User
#       'company_id': 10,
#       'name': 'Maria Santos'
#   }
# }
```

### ✅ Vantagens
- **Organograma completo** (todos os funcionários cadastrados)
- **Sem credenciais** (não ocupa licença de usuário)
- **Pode virar usuário depois** (adicionar user_id posteriormente)

---

## 🔄 Fluxograma de Decisão

```
┌─────────────────────────────────────┐
│ Pessoa precisa fazer login?         │
└─────────────┬───────────────────────┘
              │
        ┌─────┴─────┐
        │           │
       SIM         NÃO
        │           │
        ▼           ▼
┌───────────────┐  ┌──────────────────────┐
│ Já tem User?  │  │ Cenário 3:           │
└───┬───────────┘  │ create_employee_     │
    │              │ without_user()       │
┌───┴────┐         └──────────────────────┘
│        │
NÃO     SIM
│        │
▼        ▼
┌────────────────┐  ┌──────────────────────┐
│ Cenário 1:     │  │ Cenário 2:           │
│ create_user_   │  │ add_employee_        │
│ with_company() │  │ to_company()         │
└────────────────┘  └──────────────────────┘
```

---

## ⚠️ Erros Comuns e Como Evitar

### ❌ Erro 1: Criar User sem Company
```python
# ERRADO - User sem vínculo
user = User(name='João', email='joao@email.com')
db.session.add(user)
db.session.commit()
# ❌ User existe mas não pode acessar nenhuma empresa!
```

**✅ CORRETO:**
```python
# Use o serviço que cria tudo junto
UserEmployeeService.create_user_with_company(...)
```

---

### ❌ Erro 2: Criar Employee sem verificar duplicação
```python
# ERRADO - Pode criar duplicado
employee = Employee(user_id=5, company_id=10)
db.session.add(employee)
# ❌ Se já existir, vai dar erro de constraint!
```

**✅ CORRETO:**
```python
# Use o serviço que verifica duplicação
UserEmployeeService.add_employee_to_company(user_id=5, company_id=10)
```

---

### ❌ Erro 3: Não usar transação
```python
# ERRADO - Se falhar no meio, fica inconsistente
user = User(...)
db.session.add(user)
db.session.commit()  # ← Se falhar aqui, User foi criado

company = Company(...)
db.session.add(company)
db.session.commit()  # ← Mas Company não!
```

**✅ CORRETO:**
```python
# Use o serviço que faz tudo em uma transação
UserEmployeeService.create_user_with_company(...)
# Se falhar, NADA é criado (rollback automático)
```

---

## 📊 Tabela Resumo

| Cenário | User? | Company? | Employee? | Método |
|---------|-------|----------|-----------|--------|
| Novo cliente | Criar | Criar | Auto | `create_user_with_company()` |
| Consultor em nova empresa | Existe | Criar/Existe | Criar | `add_employee_to_company()` |
| Funcionário sem login | - | Existe | Criar | `create_employee_without_user()` |

---

## 🎯 Ordem de Dependências (Técnica)

Para quem precisa entender as dependências do banco:

```
1. COMPANY (não depende de nada)
   ↓
2. ROLE (depende de COMPANY)
   ↓
3. USER (não depende de nada)
   ↓
4. EMPLOYEE (depende de USER + COMPANY + ROLE)
   ↓
5. PROJECT_TASK (depende de EMPLOYEE)
```

**Mas você NÃO precisa seguir essa ordem manualmente!**  
Use os serviços que fazem isso automaticamente.

---

## 💡 Boas Práticas

### ✅ SEMPRE Use os Serviços
```python
# BOM
UserEmployeeService.create_user_with_company(...)

# RUIM
user = User(...)
company = Company(...)
employee = Employee(...)
# Muita coisa pode dar errado!
```

### ✅ SEMPRE Valide Email Único
```python
existing = User.query.filter_by(email=email).first()
if existing:
    return {'error': 'Email já cadastrado'}
```

### ✅ SEMPRE Use Transações
```python
try:
    # Operações
    db.session.commit()
except:
    db.session.rollback()
    raise
```

---

## 🚀 Exemplos Práticos

### Exemplo 1: Cadastro de Cliente no Frontend
```javascript
async function cadastrarCliente(formData) {
  const response = await fetch('/api/user-employee/register', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user: {
        name: formData.name,
        email: formData.email,
        password: formData.password
      },
      company: {
        name: formData.companyName,
        cnpj: formData.cnpj
      }
    })
  });
  
  const result = await response.json();
  
  if (result.success) {
    // Redirecionar para login
    window.location.href = '/login';
  }
}
```

### Exemplo 2: Admin Adicionando Consultor
```python
@app.route('/admin/add-consultant', methods=['POST'])
@login_required
def add_consultant():
    if current_user.role != 'admin':
        abort(403)
    
    data = request.json
    
    result = UserEmployeeService.add_employee_to_company(
        user_id=data['consultant_id'],
        company_id=data['company_id'],
        role_id=data['role_id']
    )
    
    return jsonify(result)
```

---

## 📚 Referências

- **Serviço:** `services/user_employee_service.py`
- **API:** `docs/API_USER_EMPLOYEE.md`
- **Exemplos:** `exemplos_user_employee.py`
- **Arquitetura:** `docs/governance/ARCHITECTURE.md`

---

**Resumo:** Use sempre os serviços! Eles garantem a ordem correta automaticamente. 🎯
