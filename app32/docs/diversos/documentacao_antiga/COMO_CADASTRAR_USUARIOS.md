# 🎯 Como Cadastrar Usuários - GUIA RÁPIDO

## 📍 Onde Encontrar

### ✅ OPÇÃO 1 - Pelo Dashboard
1. Faça login no sistema
2. No **Dashboard principal**, clique no card **"👥 Usuários"**
3. Você será direcionado para a página de gestão de usuários

### ✅ OPÇÃO 2 - Pelas Configurações  
1. Faça login no sistema
2. Acesse o menu **"⚙️ Configurações"**
3. Clique no card **"👥 Usuários e Perfis"**
4. Você será direcionado para a página de gestão de usuários

### ✅ OPÇÃO 3 - URL Direta
```
http://localhost:5000/auth/users/page
```

## 🔐 Requisito

**IMPORTANTE:** Apenas usuários com perfil **Administrador** podem gerenciar usuários!

### Usuário Admin Padrão
```
Email: admin@versus.com.br
Senha: 123456
```

## ➕ Como Cadastrar um Novo Usuário

### Passo 1: Acesse a Gestão de Usuários
- Siga uma das opções acima

### Passo 2: Clique em "Novo Usuário"
- No topo da página, clique no botão **"+ Novo Usuário"**

### Passo 3: Preencha o Formulário
```
📝 Nome Completo: [Digite o nome completo]
📧 Email: [Digite o email - será usado para login]
🔒 Senha: [Mínimo 6 caracteres]
🔒 Confirmar Senha: [Digite a senha novamente]
👤 Perfil: [Selecione: Administrador / Consultor / Cliente]
```

### Passo 4: Clique em "Cadastrar Usuário"
- ✅ Se tudo estiver correto, o usuário será criado
- ✅ Você será redirecionado para a lista de usuários

## 👥 Tipos de Perfil

### 🔴 Administrador
- Acesso total ao sistema
- Pode gerenciar usuários
- Pode acessar configurações e auditoria

### 🔵 Consultor
- Acesso completo aos módulos GRV
- Pode criar/editar empresas, processos, indicadores
- Não pode gerenciar usuários

### ⚪ Cliente
- Acesso limitado às empresas vinculadas
- Pode visualizar processos e indicadores
- Não pode editar configurações

## ⚙️ Outras Operações

### Desativar um Usuário
1. Na lista de usuários, encontre o usuário desejado
2. Clique no botão **"🚫 Desativar"**
3. Confirme a ação
4. O usuário não poderá mais fazer login

### Reativar um Usuário
1. Na lista de usuários, encontre o usuário desativado
2. Clique no botão **"✅ Ativar"**
3. Confirme a ação
4. O usuário poderá fazer login novamente

## ❓ Problemas Comuns

### "Acesso negado"
- **Causa:** Você não está logado como administrador
- **Solução:** Faça login com usuário admin

### "Email já está em uso"
- **Causa:** Já existe um usuário com esse email
- **Solução:** Use outro email ou edite o usuário existente

### "As senhas não coincidem"
- **Causa:** A senha e confirmação estão diferentes
- **Solução:** Digite a mesma senha nos dois campos

### Não encontro o botão "Novo Usuário"
- **Causa:** Você não está na página de usuários
- **Solução:** Acesse `/auth/users/page`

## 📱 Telas do Sistema

```
Login → Dashboard → Card "Usuários" → Lista de Usuários → Novo Usuário → Formulário
```

---

**💡 DICA:** Após cadastrar, peça ao novo usuário para fazer login com o email e senha cadastrados!

**⚠️ SEGURANÇA:** Em produção, altere a senha do usuário admin padrão!


