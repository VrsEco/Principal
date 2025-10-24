# 🔗 Guia de Aplicação: Vínculo User <-> Employee

## 📋 O que foi implementado

Criamos o relacionamento entre `users` (autenticação) e `employees` (colaboradores da empresa):

```
┌─────────────┐         ┌──────────────┐
│   User      │         │   Employee   │
├─────────────┤         ├──────────────┤
│ id          │←───────┤ user_id (FK) │
│ email       │    0..1 │ company_id   │
│ password    │         │ name         │
│ role        │         │ department   │
└─────────────┘         └──────────────┘
```

**Vantagens:**
- ✅ Colaborador pode não ter login (estagiários, terceirizados, inativos)
- ✅ Segurança: Nem todo colaborador precisa acessar o sistema
- ✅ Auditoria: Dados de RH separados de autenticação
- ✅ Flexibilidade: User pode ser colaborador em várias empresas

---

## 🚀 Passos para Aplicação

### **1. Aplicar Migration no Banco de Dados**

Execute um dos comandos abaixo (escolha o que funcionar no seu ambiente):

```bash
# Opção 1 - Python direto
python apply_user_employee_link_migration.py

# Opção 2 - Python do Anaconda
C:\Users\mff20\anaconda3\python.exe apply_user_employee_link_migration.py

# Opção 3 - Manualmente via psql
psql -U postgres -d gestao_versus -f migrations/add_user_id_to_employees.sql
```

**O que a migration faz:**
- ✅ Adiciona coluna `user_id` na tabela `employees`
- ✅ Cria Foreign Key para `users(id)`
- ✅ Cria índice para performance
- ✅ Cria índice único para garantir 1:1

---

### **2. Vincular Users Existentes aos Employees**

Execute o script de vinculação:

```bash
# Opção 1 - Python direto
python link_users_to_employees.py

# Opção 2 - Python do Anaconda
C:\Users\mff20\anaconda3\python.exe link_users_to_employees.py
```

**O que o script faz:**
- 🔍 Busca todos os users cadastrados
- 🔗 Encontra employees correspondentes por email
- ✅ Vincula automaticamente (preenche user_id)
- 📊 Mostra relatório de vinculação

**Exemplo de saída:**
```
✅ Encontrados 5 usuários no sistema

🔍 Processando: João Silva (joao@empresa.com)
   ✅ VINCULADO: Employee #3 (João Silva) -> User #1

📊 RESUMO:
   ✅ Vinculados com sucesso: 5
   ⚠️  Colaboradores não encontrados: 0
```

---

### **3. Testar o My Work Dashboard**

Acesse: **http://127.0.0.1:5003/my-work/**

**Antes (ERRO):**
```
❌ Erro ao carregar atividades
```

**Depois (FUNCIONANDO):**
```
✅ Minhas Atividades
   17 atividades carregadas
   Dashboard funcionando perfeitamente
```

---

## 🔍 Verificação Manual (SQL)

Se quiser verificar os vínculos diretamente no banco:

```sql
-- Ver colaboradores vinculados a users
SELECT 
    e.id as employee_id,
    e.name as employee_name,
    e.email as employee_email,
    e.user_id,
    u.name as user_name,
    u.email as user_email
FROM employees e
LEFT JOIN users u ON u.id = e.user_id
WHERE e.user_id IS NOT NULL
ORDER BY e.name;

-- Contar vinculações
SELECT 
    COUNT(*) FILTER (WHERE user_id IS NOT NULL) as vinculados,
    COUNT(*) FILTER (WHERE user_id IS NULL) as sem_vinculo,
    COUNT(*) as total
FROM employees;
```

---

## 🆘 Troubleshooting

### **Erro: "coluna user_id já existe"**
✅ Tudo certo! A migration já foi aplicada anteriormente.

### **Erro: "table employees não existe"**
❌ Execute primeiro o setup do banco de dados da aplicação.

### **Erro: "Colaborador não encontrado para email"**
⚠️ O employee não tem email cadastrado ou o email não corresponde ao user.

**Solução manual:**
```sql
-- Ver users sem employee
SELECT u.id, u.name, u.email
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM employees e WHERE e.user_id = u.id
);

-- Vincular manualmente (substitua os IDs)
UPDATE employees 
SET user_id = 1  -- ID do user
WHERE id = 10;   -- ID do employee
```

---

## 📝 Próximos Passos

Após aplicar a migration e vinculações:

1. ✅ **Testar login:** Entre com um user que tem employee vinculado
2. ✅ **Acessar My Work:** http://127.0.0.1:5003/my-work/
3. ✅ **Verificar dados:** As atividades devem carregar corretamente
4. ✅ **Gestão futura:** Ao cadastrar novos employees, vincule ao user se necessário

---

## 🎯 Como Vincular Novos Colaboradores no Futuro

### **Cenário 1: Cadastrar Colaborador SEM acesso ao sistema**
```python
# Apenas cria o employee (user_id = NULL)
db.create_employee(company_id, {
    'name': 'Maria Santos',
    'email': 'maria@empresa.com',
    'department': 'RH'
    # user_id não é preenchido
})
```

### **Cenário 2: Colaborador que JÁ existe precisa de acesso**
```python
# 1. Criar user
user = auth_service.create_user(
    email='maria@empresa.com',
    password='senha123',
    name='Maria Santos',
    role='consultant'
)

# 2. Vincular ao employee
cursor.execute("""
    UPDATE employees 
    SET user_id = %s 
    WHERE email = %s
""", (user.id, user.email))
```

### **Cenário 3: Cadastrar Colaborador COM acesso imediato**
```python
# 1. Criar user
user = auth_service.create_user(...)

# 2. Criar employee já vinculado
db.create_employee(company_id, {
    'name': 'Maria Santos',
    'email': 'maria@empresa.com',
    'department': 'RH',
    'user_id': user.id  # Vincular diretamente
})
```

---

## ✅ Checklist de Conclusão

- [ ] Migration aplicada (coluna user_id criada)
- [ ] Script de vinculação executado
- [ ] Verificação SQL confirmou vínculos
- [ ] Login testado com usuário vinculado
- [ ] My Work Dashboard funcionando
- [ ] Erro "Erro ao carregar atividades" resolvido

---

**Versão:** 1.0  
**Data:** 22/10/2025  
**Autor:** AI Assistant  
**Status:** ✅ Pronto para aplicação

