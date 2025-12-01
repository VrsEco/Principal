# Guia de Uso da API de Usuários e Colaboradores

## Endpoints Disponíveis

### 1. Cadastro de Novo Usuário com Empresa
**POST** `/api/user-employee/register`

Cria um novo usuário, empresa e o vínculo de colaborador em uma única transação.

**Request Body:**
```json
{
  "user": {
    "name": "João Silva",
    "email": "joao@empresa.com",
    "password": "senha123"
  },
  "company": {
    "name": "Tech Solutions Ltda",
    "cnpj": "00.000.000/0001-00",
    "segment": "Tecnologia",
    "city": "São Paulo",
    "state": "SP"
  }
}
```

**Response (201):**
```json
{
  "success": true,
  "user": {
    "id": 5,
    "name": "João Silva",
    "email": "joao@empresa.com",
    "role": "client"
  },
  "company": {
    "id": 10,
    "name": "Tech Solutions Ltda",
    "cnpj": "00.000.000/0001-00"
  },
  "employee": {
    "id": 15,
    "user_id": 5,
    "company_id": 10,
    "name": "João Silva",
    "status": "active"
  }
}
```

---

### 2. Adicionar Usuário a Outra Empresa
**POST** `/api/user-employee/add-to-company`

Adiciona um usuário existente como colaborador de outra empresa. Requer autenticação de admin.

**Request Body:**
```json
{
  "user_id": 5,
  "company_id": 12,
  "role_id": 3
}
```

**Response (201):**
```json
{
  "success": true,
  "employee": {
    "id": 20,
    "user_id": 5,
    "company_id": 12,
    "role_id": 3,
    "status": "active"
  }
}
```

---

### 3. Listar Minhas Empresas
**GET** `/api/user-employee/my-companies`

Retorna todas as empresas que o usuário logado tem acesso.

**Response (200):**
```json
{
  "success": true,
  "count": 2,
  "companies": [
    {
      "employee_id": 15,
      "company": {
        "id": 10,
        "name": "Tech Solutions Ltda",
        "cnpj": "00.000.000/0001-00"
      },
      "role_id": null,
      "status": "active"
    },
    {
      "employee_id": 20,
      "company": {
        "id": 12,
        "name": "Consultoria ABC",
        "cnpj": "11.222.333/0001-44"
      },
      "role_id": 3,
      "status": "active"
    }
  ]
}
```

---

### 4. Listar Minhas Atividades (AGREGADAS)
**GET** `/api/user-employee/my-activities`

Retorna todas as atividades do usuário em TODAS as empresas que ele é colaborador.

**Response (200):**
```json
{
  "success": true,
  "count": 5,
  "activities": [
    {
      "task": {
        "id": 100,
        "what": "Implementar novo módulo",
        "due_date": "2025-12-01",
        "status": "in_progress"
      },
      "company_id": 10,
      "employee_name": "João Silva"
    },
    {
      "task": {
        "id": 105,
        "what": "Revisar documentação",
        "due_date": "2025-11-30",
        "status": "planned"
      },
      "company_id": 12,
      "employee_name": "João Silva"
    }
  ]
}
```

---

### 5. Listar Colaboradores de uma Empresa
**GET** `/api/user-employee/employees/{company_id}`

Lista todos os colaboradores de uma empresa específica.

**Response (200):**
```json
{
  "success": true,
  "count": 3,
  "employees": [
    {
      "id": 15,
      "user_id": 5,
      "company_id": 10,
      "name": "João Silva",
      "email": "joao@empresa.com",
      "status": "active"
    },
    {
      "id": 16,
      "user_id": null,
      "company_id": 10,
      "name": "Maria Santos",
      "email": "maria@empresa.com",
      "status": "active"
    }
  ]
}
```

---

### 6. Atualizar Colaborador
**PUT** `/api/user-employee/employee/{employee_id}`

Atualiza dados de um colaborador.

**Request Body:**
```json
{
  "phone": "(11) 98765-4321",
  "department": "TI",
  "status": "active",
  "weekly_hours": 40
}
```

**Response (200):**
```json
{
  "success": true,
  "employee": {
    "id": 15,
    "phone": "(11) 98765-4321",
    "department": "TI",
    "status": "active",
    "weekly_hours": 40
  }
}
```

---

## Exemplos de Uso com cURL

### Cadastrar Novo Usuário
```bash
curl -X POST http://localhost:5003/api/user-employee/register \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "name": "João Silva",
      "email": "joao@empresa.com",
      "password": "senha123"
    },
    "company": {
      "name": "Tech Solutions Ltda",
      "cnpj": "00.000.000/0001-00"
    }
  }'
```

### Listar Minhas Atividades
```bash
curl -X GET http://localhost:5003/api/user-employee/my-activities \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

---

## Integração com Frontend

### Exemplo em JavaScript (Fetch API)

```javascript
// Cadastrar novo usuário
async function registerUser(userData, companyData) {
  const response = await fetch('/api/user-employee/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      user: userData,
      company: companyData
    })
  });
  
  return await response.json();
}

// Buscar minhas atividades
async function getMyActivities() {
  const response = await fetch('/api/user-employee/my-activities');
  const data = await response.json();
  
  if (data.success) {
    console.log(`Você tem ${data.count} atividades pendentes`);
    data.activities.forEach(activity => {
      console.log(`- ${activity.task.what} (Empresa: ${activity.company_id})`);
    });
  }
}
```

---

## Fluxo Completo de Uso

### Cenário: Novo Cliente se Cadastrando

1. **Frontend:** Formulário de cadastro
2. **Backend:** `POST /api/user-employee/register`
3. **Sistema cria:**
   - User (credenciais)
   - Company (organização)
   - Employee (vínculo)
4. **Resultado:** Usuário pode fazer login e acessar sua empresa

### Cenário: Consultor Atendendo Múltiplas Empresas

1. **Admin adiciona consultor:** `POST /api/user-employee/add-to-company`
2. **Consultor faz login:** Sistema detecta múltiplas empresas
3. **Consultor seleciona empresa:** Interface mostra seletor
4. **Consultor acessa atividades:** `GET /api/user-employee/my-activities`
5. **Sistema retorna:** Atividades de TODAS as empresas agregadas

---

## Segurança

- ✅ Endpoints protegidos com `@login_required`
- ✅ Verificação de permissões (admin vs client)
- ✅ Validação de dados de entrada
- ✅ Transações atômicas (rollback em caso de erro)
- ✅ Senhas hasheadas com Werkzeug
