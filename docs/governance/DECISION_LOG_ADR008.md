# ADR-008: Reorganização do Sistema de Usuários e Empresas

**Data:** 26/11/2025  
**Status:** ✅ Implementado  
**Decisor:** Time de Desenvolvimento  

---

## Contexto

O sistema original tinha uma relação direta entre `User` (autenticação) e `Company` (organização), o que limitava a flexibilidade:

- Um usuário só podia estar vinculado a uma empresa
- Consultores que atendem múltiplas empresas precisavam de múltiplos logins
- Atividades eram atribuídas por nome (texto), não por referência
- Permissões eram globais, não específicas por empresa
- Não havia diferenciação entre "usuário do sistema" e "colaborador da empresa"

### Problema Específico

> "Ao logar no sistema, tem que trazer para a tela de minhas atividades todas as atividades que ele é executor ou responsável."

Com a estrutura antiga, isso era impossível de forma eficiente, pois:
1. Atividades usavam campo texto `who` (não relacional)
2. Não havia conceito de "colaborador" separado de "usuário"
3. Impossível agregar atividades de múltiplas empresas

---

## Decisão

Implementamos uma **arquitetura de três camadas** com a entidade intermediária `Employee` (Colaborador):

```
USER (Credenciais) ←→ EMPLOYEE (Vínculo) ←→ COMPANY (Organização)
```

### Estrutura Implementada

#### 1. **User** (Autenticação)
- Representa as credenciais de acesso ao sistema
- Campos: `id`, `email`, `password_hash`, `name`, `role`
- Um usuário pode ter múltiplos `Employee` (um por empresa)

#### 2. **Employee** (Colaborador/Vínculo)
- Representa o vínculo entre um usuário e uma empresa
- Campos: `id`, `user_id`, `company_id`, `role_id`, `name`, `email`, `status`
- Permite que um usuário trabalhe em múltiplas empresas
- Permite funcionários sem acesso ao sistema (`user_id` NULL)

#### 3. **Company** (Organização)
- Representa a empresa/organização
- Campos: `id`, `name`, `cnpj`, etc.
- Agrupa todos os dados da organização

#### 4. **Role** (Cargo/Permissões)
- Define cargos e permissões dentro de uma empresa
- Novo campo: `permissions` (JSON) para permissões granulares
- Exemplo: `{"financial": "view", "tasks": "edit", "reports": "admin"}`

---

## Implementação

### Modelos Criados

1. **`models/employee.py`**
   - Modelo do colaborador (vínculo User ↔ Company)
   - Suporta `user_id` NULL para funcionários sem acesso

2. **`models/role.py`**
   - Modelo de cargo com campo `permissions` (JSON)
   - Permite hierarquia de cargos (`parent_role_id`)

### Alterações no Banco de Dados

```sql
-- Adicionar campo de permissões em roles
ALTER TABLE roles ADD COLUMN permissions JSON;

-- Adicionar vínculo de colaborador em project_tasks
ALTER TABLE project_tasks ADD COLUMN employee_id INTEGER;
ALTER TABLE project_tasks ADD CONSTRAINT fk_project_tasks_employee 
    FOREIGN KEY (employee_id) REFERENCES employees (id);
```

### Camada de Serviço

Criado `services/user_employee_service.py` com métodos:

- `create_user_with_company()` - Cadastro completo em uma transação
- `add_employee_to_company()` - Adicionar usuário em outra empresa
- `get_user_companies()` - Listar empresas do usuário
- **`get_user_activities()`** - **Atividades agregadas de todas as empresas** ⭐
- `create_employee_without_user()` - Funcionários sem acesso ao sistema

### API REST

Criado `api/user_employee.py` com 6 endpoints:

- `POST /api/user-employee/register` - Cadastro completo
- `POST /api/user-employee/add-to-company` - Adicionar em empresa
- `GET /api/user-employee/my-companies` - Listar empresas
- `GET /api/user-employee/my-activities` - **Atividades agregadas** ⭐
- `GET /api/user-employee/employees/{company_id}` - Listar colaboradores
- `PUT /api/user-employee/employee/{employee_id}` - Atualizar colaborador

---

## Consequências

### Positivas ✅

1. **Flexibilidade Total**
   - Um usuário pode trabalhar em múltiplas empresas
   - Permissões específicas por empresa
   - Funcionários sem acesso ao sistema podem existir

2. **Atividades Agregadas**
   - Solução para "Minhas Atividades" agregadas
   - Query eficiente: busca todos `employee_id` do usuário
   - Retorna atividades de todas as empresas

3. **Rastreabilidade**
   - Atividades vinculadas a `employee_id` (não texto)
   - Histórico completo de quem fez o quê
   - Auditoria por empresa

4. **Escalabilidade**
   - Fácil adicionar novos tipos de permissões
   - Suporta crescimento do sistema
   - Arquitetura preparada para multi-tenancy

5. **Segurança**
   - Permissões granulares por empresa
   - Isolamento de dados por empresa
   - Controle de acesso robusto

### Negativas ⚠️

1. **Complexidade Adicional**
   - Mais uma tabela (`employees`) para gerenciar
   - Queries mais complexas (joins adicionais)
   - Migração de dados necessária

2. **Migração de Dados**
   - Dados existentes precisam ser migrados
   - Campo `who` (texto) → `employee_id` (relacional)
   - Possível perda de dados se nomes não corresponderem

3. **Mudança de Paradigma**
   - Desenvolvedores precisam entender a nova arquitetura
   - Código existente precisa ser atualizado
   - Telas precisam ser adaptadas

### Mitigações

1. **Scripts de Migração**
   - `scripts/apply_db_migrations.py` - Estrutura do banco
   - `scripts/migrate_data_users_employees.py` - Migração de dados
   - `scripts/verify_migrations.py` - Verificação

2. **Documentação Completa**
   - `docs/REORGANIZACAO_USUARIOS.md` - Arquitetura
   - `docs/API_USER_EMPLOYEE.md` - Guia da API
   - `exemplos_user_employee.py` - Exemplos práticos

3. **Camada de Compatibilidade**
   - Campo `who` mantido em `project_tasks` (legacy)
   - Migração gradual possível
   - Rollback facilitado

---

## Alternativas Consideradas

### Alternativa 1: Manter Estrutura Atual
**Descartada** porque:
- Não resolve o problema de múltiplas empresas
- Atividades continuariam com texto (não relacional)
- Impossível implementar "Minhas Atividades" agregadas

### Alternativa 2: Tabela de Associação Simples
Criar apenas `user_companies` (N:M):
```
users ←→ user_companies ←→ companies
```

**Descartada** porque:
- Não permite funcionários sem acesso ao sistema
- Não suporta permissões específicas por empresa
- Não resolve o vínculo de atividades

### Alternativa 3: Duplicar Usuários
Criar um `User` para cada empresa:

**Descartada** porque:
- Múltiplos logins para o mesmo usuário
- Dificulta agregação de atividades
- Má experiência do usuário

---

## Exemplo de Uso

### Cenário 1: Novo Cliente se Cadastrando
```python
from services.user_employee_service import UserEmployeeService

result = UserEmployeeService.create_user_with_company(
    user_data={'name': 'João', 'email': 'joao@tech.com', 'password': '123'},
    company_data={'name': 'Tech Solutions', 'cnpj': '12.345.678/0001-90'}
)
# Cria: User + Company + Employee em uma transação
```

### Cenário 2: Tela "Minhas Atividades"
```python
# Retorna TODAS as atividades de TODAS as empresas
activities = UserEmployeeService.get_user_activities(current_user.id)

for activity in activities:
    print(f"{activity['task']['what']} - Empresa: {activity['company_id']}")
```

### Cenário 3: Consultor em Múltiplas Empresas
```python
# Adicionar consultor em nova empresa
UserEmployeeService.add_employee_to_company(
    user_id=5,
    company_id=12,
    role_id=3  # Cargo de "Consultor"
)
```

---

## Impacto em Outras Partes do Sistema

### Módulos Afetados

1. **Autenticação** (`api/auth.py`)
   - Manter compatibilidade com login atual
   - Adicionar seletor de empresa (se múltiplas)

2. **Atividades** (`models/project.py`, etc.)
   - Atualizar para usar `employee_id`
   - Manter `who` para compatibilidade

3. **Relatórios**
   - Filtrar por empresa do colaborador
   - Agregar dados de múltiplas empresas

4. **Permissões**
   - Implementar middleware de verificação
   - Usar `employee.role.permissions`

### Próximos Passos

1. **Interface de Usuário**
   - [ ] Criar tela de cadastro usando nova API
   - [ ] Implementar seletor de empresa
   - [ ] Criar dashboard "Minhas Atividades"

2. **Sistema de Permissões**
   - [ ] Implementar middleware de verificação
   - [ ] Criar interface para gerenciar permissões
   - [ ] Adicionar logs de auditoria

3. **Migração Completa**
   - [ ] Atualizar todas as rotas de cadastro
   - [ ] Migrar outras tabelas de atividades
   - [ ] Remover campos legados após validação

---

## Métricas de Sucesso

- ✅ Migração de estrutura aplicada sem erros
- ✅ Migração de dados concluída
- ✅ API funcionando e testada
- ✅ Documentação completa criada
- [ ] Interface de usuário implementada
- [ ] Sistema de permissões funcionando
- [ ] Feedback positivo dos usuários

---

## Referências

- [docs/REORGANIZACAO_USUARIOS.md](../REORGANIZACAO_USUARIOS.md)
- [docs/API_USER_EMPLOYEE.md](../API_USER_EMPLOYEE.md)
- [services/user_employee_service.py](../../services/user_employee_service.py)
- [api/user_employee.py](../../api/user_employee.py)

---

**Implementado em:** 26/11/2025  
**Versão:** 1.0  
**Status:** ✅ Pronto para uso
