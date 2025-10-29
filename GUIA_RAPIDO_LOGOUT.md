# 🔓 Guia Rápido: Como Fazer Logout

## 🚀 Métodos para Fazer Logout

### **Método 1: Via Navegador (MAIS FÁCIL)**
Simplesmente acesse no navegador:
```
http://127.0.0.1:5003/auth/logout
```

---

### **Método 2: Limpar Cookies**

#### Chrome/Edge:
1. Pressione **F12**
2. Aba **Application** → **Cookies**
3. Delete cookie `session` de `http://127.0.0.1:5003`
4. Recarregue a página (**F5**)

#### Firefox:
1. Pressione **F12**
2. Aba **Storage** → **Cookies**
3. Delete cookie `session` de `http://127.0.0.1:5003`
4. Recarregue a página (**F5**)

---

### **Método 3: Atalho Rápido**
1. **Ctrl+Shift+Delete**
2. Marque **"Cookies e outros dados do site"**
3. Clique em **"Limpar dados"**
4. Acesse `http://127.0.0.1:5003`

---

### **Método 4: Modo Anônimo**
1. **Ctrl+Shift+N** (Chrome/Edge) ou **Ctrl+Shift+P** (Firefox)
2. Acesse `http://127.0.0.1:5003`
3. Faça login normalmente
4. A sessão será limpa ao fechar a janela anônima

---

## ⏱️ Duração das Sessões

### Sessão Normal (SEM "Lembrar-me"):
- **Duração:** 24 horas
- **Comportamento:** Expira após 24h de inatividade
- **Ao fechar navegador:** Sessão pode persistir se não expirou

### Sessão Persistente (COM "Lembrar-me"):
- **Duração:** 7 dias
- **Comportamento:** Permanece ativa mesmo após fechar navegador
- **Expiração:** Apenas após 7 dias ou logout manual

---

## 🔒 URLs Úteis

| Função | URL |
|--------|-----|
| **Login** | `http://127.0.0.1:5003/login` |
| **Logout** | `http://127.0.0.1:5003/auth/logout` |
| **Página Principal** | `http://127.0.0.1:5003/main` |
| **Dashboard PEV** | `http://127.0.0.1:5003/pev/dashboard` |
| **Logs** | `http://127.0.0.1:5003/logs/` |

---

## ❓ Perguntas Frequentes

### **Por que estou indo direto para /main sem fazer login?**
Você tem uma sessão ativa. Use um dos métodos acima para fazer logout.

### **Como testar a autenticação?**
1. Faça logout (use Método 1)
2. Acesse `http://127.0.0.1:5003/main`
3. Deve redirecionar para `/login`

### **A sessão expira automaticamente?**
- **Sem "Lembrar-me":** Sim, após 24 horas
- **Com "Lembrar-me":** Sim, após 7 dias

### **Como forçar novo login para todos os usuários?**
Reinicie o servidor Flask. Isso invalida todas as sessões ativas.

---

**Última atualização:** 25/10/2025


