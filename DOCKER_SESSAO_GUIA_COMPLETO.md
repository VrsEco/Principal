# 🐳 Guia Completo: Aplicar Correções de Sessão no Docker

**Data:** 25/10/2025  
**Ambiente:** Docker Development (porta 5003)

---

## 🎯 Objetivo

Aplicar as correções de segurança de sessão no ambiente Docker:
- ✅ Redução de sessão persistente (30 → 7 dias)
- ✅ Proteções contra XSS e CSRF
- ✅ Logout via GET habilitado
- ✅ Sessão de 24h sem "lembrar-me"

---

## 📋 Pré-requisitos

### Verificar se Docker está rodando:
```bash
docker ps
```

### Containers esperados:
- `gestaoversus_app_dev` - Aplicação Flask (porta 5003)
- `gestaoversus_db_dev` - PostgreSQL
- `gestaoversus_redis_dev` - Redis
- `gestaoversus_adminer_dev` - Adminer (opcional)

---

## 🚀 Aplicar Correções

### **Opção 1: Script Automático (RECOMENDADO)**

```bash
APLICAR_CORRECOES_SESSAO_DOCKER.bat
```

Este script:
1. ✅ Verifica containers
2. ✅ Reinicia a aplicação
3. ✅ Mostra logs
4. ✅ Testa se app responde

---

### **Opção 2: Manual (Passo a Passo)**

#### **Passo 1: Verificar Containers**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

#### **Passo 2: Reiniciar Container da Aplicação**
```bash
docker-compose -f docker-compose.dev.yml restart app_dev
```

**OU** (se quiser rebuild completo):
```bash
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d --build
```

#### **Passo 3: Ver Logs em Tempo Real**
```bash
docker logs -f gestaoversus_app_dev
```

Pressione `Ctrl+C` para sair.

#### **Passo 4: Verificar se App Respondeu**
```bash
curl http://localhost:5003/
```

---

## 🧪 Testar Correções

### **Opção 1: Script de Teste Automático**

```bash
TESTAR_SESSAO_DOCKER.bat
```

---

### **Opção 2: Teste Manual no Navegador**

#### **Teste 1: Verificar Proteção de Rota**

1. **Abra navegador em Modo Anônimo** (Ctrl+Shift+N)
2. Acesse: `http://127.0.0.1:5003/main`
3. ✅ **ESPERADO:** Redirecionar para `/login`

---

#### **Teste 2: Fazer Logout**

1. Faça login:
   - Email: `admin@versus.com.br`
   - Senha: `123456`

2. Após login, acesse: `http://127.0.0.1:5003/auth/logout`
3. ✅ **ESPERADO:** 
   - Redirecionar para `/login`
   - Mostrar mensagem "Logout realizado com sucesso"

---

#### **Teste 3: Verificar Cookies de Segurança**

1. Faça login novamente
2. Pressione **F12** (DevTools)
3. Vá em **Application** → **Cookies** → `http://127.0.0.1:5003`
4. Encontre o cookie `session`
5. ✅ **ESPERADO:**
   - `HttpOnly` = ✅ (true)
   - `SameSite` = `Lax`
   - `Secure` = ❌ (false - normal em dev sem HTTPS)

---

#### **Teste 4: Verificar Expiração de Sessão**

##### **Sem "Lembrar-me":**
1. Faça login SEM marcar checkbox "Lembrar-me"
2. Verifique cookie `session`
3. ✅ **ESPERADO:** Expira em ~24 horas

##### **Com "Lembrar-me":**
1. Faça logout
2. Faça login MARCANDO checkbox "Lembrar-me"
3. Verifique cookie `session`
4. ✅ **ESPERADO:** Expira em ~7 dias

---

## 🔍 Troubleshooting

### **Problema: Container não está rodando**

```bash
docker-compose -f docker-compose.dev.yml up -d
```

---

### **Problema: Porta 5003 já em uso**

```bash
# Ver o que está usando a porta
netstat -ano | findstr :5003

# Parar containers
docker-compose -f docker-compose.dev.yml down

# Subir novamente
docker-compose -f docker-compose.dev.yml up -d
```

---

### **Problema: Mudanças não aparecem**

#### **Causa:** Docker cache

**Solução:**
```bash
# Parar tudo
docker-compose -f docker-compose.dev.yml down

# Rebuild sem cache
docker-compose -f docker-compose.dev.yml build --no-cache app_dev

# Subir novamente
docker-compose -f docker-compose.dev.yml up -d
```

---

### **Problema: Ainda logado automaticamente**

#### **Causa:** Cookie antigo no navegador

**Solução:**

1. **F12** → **Application** → **Cookies**
2. Delete cookie `session`
3. Recarregue página

**OU**

Use **Modo Anônimo** (Ctrl+Shift+N)

---

## 📂 Arquivos Modificados

### **1. `config.py`**

```python
# Antes:
REMEMBER_COOKIE_DURATION = timedelta(days=30)

# Depois:
REMEMBER_COOKIE_DURATION = timedelta(days=7)

# Adicionado:
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
```

---

### **2. `api/auth.py`**

```python
# Antes:
@auth_bp.route('/logout', methods=['POST'])

# Depois:
@auth_bp.route('/logout', methods=['GET', 'POST'])
```

Agora aceita logout via navegador!

---

## 🔧 Comandos Úteis

### **Ver todos os containers:**
```bash
docker ps -a
```

### **Ver logs da aplicação:**
```bash
docker logs gestaoversus_app_dev
```

### **Ver logs em tempo real:**
```bash
docker logs -f gestaoversus_app_dev
```

### **Entrar no container:**
```bash
docker exec -it gestaoversus_app_dev bash
```

### **Reiniciar apenas a app:**
```bash
docker-compose -f docker-compose.dev.yml restart app_dev
```

### **Parar tudo:**
```bash
docker-compose -f docker-compose.dev.yml down
```

### **Subir tudo:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### **Ver uso de recursos:**
```bash
docker stats
```

---

## 🌍 Variáveis de Ambiente

### **Desenvolvimento (docker-compose.dev.yml):**

```yaml
FLASK_ENV: development
FLASK_DEBUG: 1
SECRET_KEY: dev-secret-key-not-for-production
DATABASE_URL: postgresql://postgres:dev_password@db_dev:5432/bd_app_versus_dev
```

### **Produção (docker-compose.yml):**

```yaml
FLASK_ENV: production
SECRET_KEY: ${SECRET_KEY}  # Deve vir de .env
DATABASE_URL: postgresql://...
SESSION_COOKIE_SECURE: true  # IMPORTANTE em produção!
```

---

## 📊 Portas do Sistema

| Serviço | Dev | Prod | Descrição |
|---------|-----|------|-----------|
| **Flask App** | 5003 | 5002 | Aplicação principal |
| **PostgreSQL** | 5433 | 5432 | Banco de dados |
| **Redis** | 6380 | 6379 | Cache/Queue |
| **Adminer** | 8080 | - | Admin DB (dev only) |
| **MailHog** | 8025 | - | Email testing (dev) |
| **Nginx** | - | 80/443 | Reverse proxy (prod) |

---

## ✅ Checklist de Validação

Após aplicar correções:

- [ ] Container `gestaoversus_app_dev` está rodando
- [ ] Porta 5003 responde (HTTP 200 ou 302)
- [ ] `/main` sem login redireciona para `/login`
- [ ] Login funciona normalmente
- [ ] `/auth/logout` via GET funciona
- [ ] Cookie `session` tem `HttpOnly = true`
- [ ] Cookie `session` tem `SameSite = Lax`
- [ ] Sessão sem "lembrar-me" expira em 24h
- [ ] Sessão com "lembrar-me" expira em 7 dias

---

## 🚀 Próximos Passos

### **1. Para Produção:**

Adicione ao arquivo `.env` de produção:

```bash
# Segurança de Sessão
SESSION_COOKIE_SECURE=true  # IMPORTANTE com HTTPS
SECRET_KEY=sua_chave_forte_aqui_gerada_com_secrets
```

Gerar SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### **2. Melhorias Futuras (Opcional):**

- [ ] Implementar rotação de SECRET_KEY
- [ ] Adicionar auditoria de sessões (log de login/logout)
- [ ] Limite de sessões simultâneas por usuário
- [ ] Auto-logout por inatividade
- [ ] 2FA (Two-Factor Authentication)

---

## 📚 Documentação Relacionada

- `CORRECAO_SESSAO_PERSISTENTE.md` - Documentação técnica completa
- `GUIA_RAPIDO_LOGOUT.md` - Guia rápido de logout
- `docker-compose.dev.yml` - Configuração Docker Dev
- `docker-compose.yml` - Configuração Docker Prod

---

## 🆘 Suporte

### **Ver configuração atual:**
```bash
docker exec gestaoversus_app_dev env | grep FLASK
```

### **Verificar arquivo config.py no container:**
```bash
docker exec gestaoversus_app_dev cat config.py | grep SESSION
```

### **Testar endpoint health:**
```bash
curl http://localhost:5003/health
```

---

**✅ Correções Aplicadas com Sucesso!**

O sistema agora está mais seguro e com gerenciamento adequado de sessões.

---

**Versão:** 1.0  
**Data:** 25/10/2025  
**Ambiente:** Docker Development + Production
























