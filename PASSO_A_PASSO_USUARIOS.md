# 🎯 Passo a Passo: Como Acessar a Gestão de Usuários

## ❌ **PROBLEMA:** Página sem botões

Quando você acessa `http://127.0.0.1:5003/auth/users/page` sem estar logado, a página **REDIRECIONA PARA LOGIN** e não mostra nenhum botão.

## ✅ **SOLUÇÃO:** Fazer Login Primeiro

### **📝 Passo 1: Fazer Login**

1. **Abra o navegador** e acesse:
   ```
   http://127.0.0.1:5003/login
   ```

2. **Digite as credenciais do administrador:**
   - **Email:** `admin@versus.com.br`
   - **Senha:** `123456`

3. **Clique em "Entrar"**

### **📝 Passo 2: Acessar Gestão de Usuários**

Após o login, você tem **3 opções:**

#### **Opção A - Pelo Dashboard:**
1. Você será redirecionado para o Dashboard
2. Procure o card **"👥 Usuários"**
3. Clique nele

#### **Opção B - Pela URL Direta:**
```
http://127.0.0.1:5003/auth/users/page
```

#### **Opção C - Pelas Configurações:**
1. Acesse o menu **"⚙️ Configurações"**
2. Clique em **"👥 Usuários e Perfis"**

### **📝 Passo 3: Gerenciar Usuários**

Agora você verá a página completa com:

#### **Botões Disponíveis:**
- ✅ **"➕ Novo Usuário"** - No canto superior direito
- ✅ **"🔴 Desativar"** - Para cada usuário ativo
- ✅ **"🟢 Ativar"** - Para cada usuário inativo

## 🖼️ **Como Deve Aparecer**

### **Cabeçalho da Página:**
```
👥 Gerenciar Usuários          [➕ Novo Usuário]
─────────────────────────────────────────────────
```

### **Tabela de Usuários:**
```
Nome          | Email              | Perfil        | Status | Ações
─────────────|───────────────────|──────────────|────────|──────────
Administrador| admin@versus...   | Administrador | Ativo  | [Desativar]
João Silva   | joao@empresa...   | Consultor     | Ativo  | [Desativar]
```

## 🔐 **Se Você NÃO Consegue Fazer Login**

### **Verificar se o usuário admin existe:**

```bash
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "SELECT id, email, name, role FROM users;"
```

### **Se não existir nenhum usuário, criar o admin:**

```bash
docker exec gestaoversus_app_dev python -c "
from app_pev import app
with app.app_context():
    from services.auth_service import AuthService
    user = AuthService.create_admin_user()
    if user:
        print('✅ Admin criado com sucesso!')
    else:
        print('ℹ️ Admin já existe')
"
```

## 🐛 **Problemas Comuns**

### **1. Página redireciona para login**
- **Causa:** Você não está logado
- **Solução:** Faça login com admin@versus.com.br

### **2. "Acesso negado"**
- **Causa:** Você está logado mas não é administrador
- **Solução:** Faça login com um usuário com role='admin'

### **3. Botões não aparecem**
- **Causa:** JavaScript não carregou ou você não está logado
- **Solução:** 
  1. Pressione F12 para abrir o console do navegador
  2. Verifique se há erros
  3. Recarregue a página (Ctrl+F5)

### **4. Página em branco**
- **Causa:** Erro no template ou no servidor
- **Solução:** Verificar logs do Docker:
  ```bash
  docker logs gestaoversus_app_dev --tail 50
  ```

## 📊 **Funcionalidades Disponíveis**

### **Após Login como Admin:**

#### **1. Cadastrar Novo Usuário**
- Clique em "➕ Novo Usuário"
- Preencha:
  - Nome completo
  - Email (será o login)
  - Senha (mínimo 6 caracteres)
  - Confirmar senha
  - Perfil (Admin/Consultor/Cliente)
- Clique em "Cadastrar Usuário"

#### **2. Desativar Usuário**
- Na lista de usuários, clique em "Desativar"
- Confirme a ação
- Usuário não poderá mais fazer login

#### **3. Reativar Usuário**
- Na lista de usuários inativos, clique em "Ativar"
- Usuário poderá fazer login novamente

## 🎬 **Vídeo Tutorial (Texto)**

```
1. Abra: http://127.0.0.1:5003/login
2. Digite: admin@versus.com.br
3. Digite: 123456
4. Clique: "Entrar"
5. Aguarde redirecionamento
6. Clique: Card "👥 Usuários"
7. Veja: Página com botões e tabela
8. Clique: "➕ Novo Usuário"
9. Preencha formulário
10. Clique: "Cadastrar Usuário"
```

## 🔧 **Teste Rápido**

Execute este comando para testar se a página está funcionando:

```bash
# Teste 1: Verificar se a rota existe
docker exec gestaoversus_app_dev python -c "
from app_pev import app
with app.app_context():
    from flask import url_for
    with app.test_request_context():
        print('URL da página:', url_for('auth.list_users_page'))
        print('URL de cadastro:', url_for('auth.register'))
"

# Teste 2: Ver usuários no banco
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "SELECT email, name, role FROM users;"
```

## 🚀 **Recapitulando**

### **O que você DEVE fazer:**
1. ✅ Acessar `http://127.0.0.1:5003/login`
2. ✅ Fazer login com `admin@versus.com.br` / `123456`
3. ✅ Clicar no card "Usuários" no Dashboard
4. ✅ Agora você verá TODOS os botões

### **O que NÃO fazer:**
1. ❌ Tentar acessar `/auth/users/page` sem login
2. ❌ Usar um usuário que não é admin
3. ❌ Esquecer de fazer login primeiro

---

**Importante:** A página de gestão de usuários é protegida e **REQUER:**
- ✅ Estar logado
- ✅ Ter role='admin'

**Se não estiver logado, você verá apenas o redirecionamento para login, SEM BOTÕES.**

---

**Data:** 22/10/2024  
**Status:** ✅ Página funciona - Necessário fazer login primeiro  
**Próximo Passo:** Fazer login e testar


