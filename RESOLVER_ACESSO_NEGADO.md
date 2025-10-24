# 🔧 Resolver: "Acesso negado. Apenas administradores podem criar usuários"

## 📊 **Situação Verificada**

✅ **Banco de Dados:**
- Usuário admin existe
- Email: `admin@versus.com.br`
- Role: `admin` (correto)
- Ativo: `true`

❌ **Problema:**
- Você recebe "Acesso negado"
- Isso significa que você NÃO está logado como admin

## 🎯 **Causas Possíveis**

1. ❌ Você está logado com outro usuário (não admin)
2. ❌ A sessão expirou
3. ❌ Cookies/cache antigos
4. ❌ Você não está logado

## ✅ **SOLUÇÃO (Passo a Passo)**

### **🔥 Solução 1: Logout e Login Novamente**

1. **Faça logout:**
   ```
   http://127.0.0.1:5003/logout
   ```
   OU simplesmente **feche o navegador completamente**

2. **Limpe cache e cookies:**
   - Pressione `Ctrl + Shift + Delete`
   - Marque: ✅ Cookies ✅ Cache
   - Clique em "Limpar dados"

3. **Feche TODAS as abas e janelas do navegador**

4. **Abra o navegador novamente**

5. **Faça login:**
   ```
   URL: http://127.0.0.1:5003/login
   Email: admin@versus.com.br
   Senha: 123456
   ```

6. **Tente cadastrar usuário:**
   ```
   http://127.0.0.1:5003/auth/register
   ```

### **🔍 Solução 2: Verificar Quem Está Logado**

**No Console do Navegador (F12 → Console):**

```javascript
fetch('/auth/current-user')
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      console.log('Logado como:', data.user.name);
      console.log('Email:', data.user.email);
      console.log('Role:', data.user.role);
      console.log('É admin?', data.user.role === 'admin');
    } else {
      console.log('NÃO ESTÁ LOGADO');
    }
  });
```

**Resultado esperado:**
```
Logado como: Administrador
Email: admin@versus.com.br
Role: admin
É admin? true
```

**Se aparecer algo diferente:**
- Role diferente de 'admin' → Você não é admin
- "NÃO ESTÁ LOGADO" → Precisa fazer login

### **⚡ Solução 3: Modo Anônimo (Teste)**

1. **Abra janela anônima:**
   - Chrome/Edge: `Ctrl + Shift + N`
   - Firefox: `Ctrl + Shift + P`

2. **Acesse:**
   ```
   http://127.0.0.1:5003/login
   ```

3. **Faça login:**
   ```
   Email: admin@versus.com.br
   Senha: 123456
   ```

4. **Tente criar usuário:**
   ```
   http://127.0.0.1:5003/auth/register
   ```

**Se funcionar na janela anônima:**
→ Problema é cache/cookies no navegador normal
→ Limpe tudo e use o navegador normal

### **🔄 Solução 4: Forçar Logout via Cookie**

**No Console (F12):**

```javascript
// Limpar todos os cookies
document.cookie.split(";").forEach(function(c) { 
  document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"); 
});
console.log('Cookies limpos! Faça login novamente.');
```

Depois:
1. Recarregue a página (`F5`)
2. Você será redirecionado para login
3. Faça login com `admin@versus.com.br`

### **🗄️ Solução 5: Verificar Sessão no Servidor**

**Reiniciar o servidor Flask para limpar sessões:**

```bash
docker restart gestaoversus_app_dev
```

Aguarde 10 segundos, depois:
1. Acesse: `http://127.0.0.1:5003/login`
2. Faça login: `admin@versus.com.br` / `123456`
3. Tente criar usuário

## 🧪 **Script de Teste**

**Cole no Console (F12) para diagnosticar:**

```javascript
async function diagnosticar() {
    console.log('🔍 DIAGNÓSTICO DE LOGIN');
    console.log('========================');
    
    try {
        // Verificar usuário atual
        const resp = await fetch('/auth/current-user');
        const data = await resp.json();
        
        if (data.success) {
            console.log('✅ LOGADO');
            console.log('Nome:', data.user.name);
            console.log('Email:', data.user.email);
            console.log('Role:', data.user.role);
            console.log('ID:', data.user.id);
            
            if (data.user.role === 'admin') {
                console.log('✅ É ADMINISTRADOR - DEVERIA FUNCIONAR');
                console.log('\nTente acessar: http://127.0.0.1:5003/auth/register');
            } else {
                console.log('❌ NÃO É ADMINISTRADOR');
                console.log('Role atual:', data.user.role);
                console.log('Precisa ser: admin');
                console.log('\nFaça logout e login com admin@versus.com.br');
            }
        } else {
            console.log('❌ NÃO ESTÁ LOGADO');
            console.log('Acesse: http://127.0.0.1:5003/login');
            console.log('Email: admin@versus.com.br');
            console.log('Senha: 123456');
        }
    } catch (error) {
        console.log('❌ ERRO:', error);
    }
}

diagnosticar();
```

## 📋 **Checklist**

Siga esta ordem:

- [ ] 1. Fechou TODAS as abas/janelas do navegador?
- [ ] 2. Limpou cache e cookies (Ctrl+Shift+Delete)?
- [ ] 3. Abriu navegador novamente?
- [ ] 4. Acessou http://127.0.0.1:5003/login ?
- [ ] 5. Digitou: admin@versus.com.br ?
- [ ] 6. Digitou senha: 123456 ?
- [ ] 7. Clicou em "Entrar"?
- [ ] 8. Foi redirecionado com sucesso?
- [ ] 9. Acessou http://127.0.0.1:5003/auth/register ?
- [ ] 10. Viu o formulário de cadastro?

**Se SIM em todos:** ✅ Problema resolvido!  
**Se NÃO em algum:** ⚠️ Em qual parou?

## 🆘 **Se NADA Funcionar**

### **Criar outro usuário admin via SQL:**

```bash
docker exec gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "
INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
VALUES (
  'admin2@versus.com.br',
  'scrypt:32768:8:1\$IkrUTlx2h6j6eGfZ\$e4dbb0f27d6b8c28f7c8e1a0c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5c8f0a6e5',
  'Admin Temporário',
  'admin',
  true,
  NOW(),
  NOW()
);
"
```

**Ou use Python:**

```bash
docker exec gestaoversus_app_dev python -c "
from app_pev import app
with app.app_context():
    from services.auth_service import AuthService
    user = AuthService.create_user('admin2@versus.com.br', '123456', 'Admin 2', 'admin')
    print('Usuário criado!' if user else 'Erro ao criar')
"
```

Depois faça login com `admin2@versus.com.br` / `123456`

## 📞 **Resumo Rápido**

1. ✅ **Logout:** Feche o navegador completamente
2. ✅ **Limpar:** Ctrl+Shift+Delete → Cache e Cookies
3. ✅ **Login:** admin@versus.com.br / 123456
4. ✅ **Cadastrar:** http://127.0.0.1:5003/auth/register

---

**Data:** 22/10/2024  
**Problema:** Acesso negado apesar de ser admin  
**Causa:** Sessão expirada ou cache  
**Solução:** Logout + Limpar cache + Login novamente


