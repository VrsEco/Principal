# Reorganização do Sistema de Usuários e Empresas

## Objetivo
Implementar um modelo robusto onde usuários podem estar vinculados a múltiplas empresas, com permissões específicas por empresa, e atividades agregadas de todas as empresas.

## Estrutura Implementada

### 1. Modelos Criados

#### `models/employee.py`
- **Função:** Representa o vínculo entre um Usuário e uma Empresa (Colaborador)
- **Campos principais:**
  - `user_id`: Link para a tabela `users` (pode ser NULL para funcionários sem acesso)
  - `company_id`: Link para a tabela `companies`
  - `role_id`: Link para a tabela `roles` (cargo/permissões)
  - `status`: active, inactive, vacation
  
#### `models/role.py`
- **Função:** Define cargos e permissões dentro de uma empresa
- **Novo campo:** `permissions` (JSON) - Permite definir permissões granulares
  - Exemplo: `{"financial": "view", "tasks": "edit", "reports": "admin"}`

### 2. Alterações no Banco de Dados

Arquivo: `migrations/update_db_structure.sql`

```sql
-- Adiciona campo de permissões em roles
ALTER TABLE roles ADD COLUMN IF NOT EXISTS permissions JSON;

-- Adiciona vínculo de colaborador em project_tasks
ALTER TABLE project_tasks ADD COLUMN IF NOT EXISTS employee_id INTEGER;
ALTER TABLE project_tasks ADD CONSTRAINT fk_project_tasks_employee 
    FOREIGN KEY (employee_id) REFERENCES employees (id);
```

### 3. Serviço de Gerenciamento

Arquivo: `services/user_employee_service.py`

#### Métodos principais:

1. **`create_user_with_company()`**
   - Cria User + Company + Employee em uma transação
   - Uso: Cadastro de nova conta no sistema

2. **`add_employee_to_company()`**
   - Adiciona um usuário existente como colaborador de outra empresa
   - Uso: Consultor que atende múltiplas empresas

3. **`get_user_companies()`**
   - Lista todas as empresas que o usuário tem acesso
   - Uso: Seletor de contexto de empresa

4. **`get_user_activities()`**
   - Agrega todas as atividades do usuário em todas as empresas
   - Uso: Tela "Minhas Atividades"

5. **`create_employee_without_user()`**
   - Cria colaborador sem acesso ao sistema
   - Uso: Funcionários que aparecem em organogramas mas não fazem login

## Fluxo de Uso

### Cenário 1: Novo Cliente se Cadastrando

```python
from services.user_employee_service import UserEmployeeService

result = UserEmployeeService.create_user_with_company(
    user_data={
        'name': 'João Silva',
        'email': 'joao@empresa.com',
        'password': 'senha123',
        'role': 'client'
    },
    company_data={
        'name': 'Tech Solutions Ltda',
        'cnpj': '00.000.000/0001-00',
        'segment': 'Tecnologia'
    }
)
# Retorna: user, company e employee criados
```

### Cenário 2: Consultor Atendendo Nova Empresa

```python
# Usuário ID 5 (consultor) vai atender a empresa ID 10
result = UserEmployeeService.add_employee_to_company(
    user_id=5,
    company_id=10,
    role_id=2  # Cargo de "Consultor"
)
```

### Cenário 3: Tela "Minhas Atividades"

```python
# Usuário logado quer ver todas as suas tarefas
activities = UserEmployeeService.get_user_activities(
    user_id=current_user.id
)
# Retorna tarefas de TODAS as empresas que ele é colaborador
```

## Próximos Passos

### 1. Aplicar Migração no Banco
Execute o script SQL:
```bash
psql -U postgres -d bd_app_versus -f migrations/update_db_structure.sql
```

### 2. Atualizar Rotas de Cadastro
Modificar as rotas de registro para usar `UserEmployeeService.create_user_with_company()`

### 3. Implementar Seletor de Empresa
Criar interface para usuários escolherem qual empresa estão acessando (se tiverem múltiplas)

### 4. Migrar Dados Existentes
Criar script para:
- Vincular `project_tasks.who` (texto) para `project_tasks.employee_id`
- Popular `employees` com base em `users` existentes

### 5. Implementar Sistema de Permissões
Criar middleware para verificar `employee.role.permissions` antes de permitir ações

## Benefícios da Nova Arquitetura

1. **Flexibilidade:** Um usuário pode trabalhar em múltiplas empresas
2. **Segurança:** Permissões específicas por empresa
3. **Rastreabilidade:** Atividades vinculadas a colaboradores, não a texto livre
4. **Escalabilidade:** Fácil adicionar novos tipos de permissões
5. **Auditoria:** Histórico completo de quem fez o quê em qual empresa
