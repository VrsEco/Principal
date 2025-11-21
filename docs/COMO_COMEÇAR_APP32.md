# 🚀 Como Começar com App32 (Desenvolvimento)

## 📋 Passo a Passo Simples

### 1. Criar Pasta app32

```bash
cd C:\GestaoVersus
mkdir app32
cd app32
```

### 2. Copiar Código de app31

```bash
# Criar arquivo de exclusão
echo .git > exclude.txt
echo .venv >> exclude.txt
echo __pycache__ >> exclude.txt
echo instance >> exclude.txt
echo uploads >> exclude.txt
echo temp_pdfs >> exclude.txt
echo logs >> exclude.txt
echo backups >> exclude.txt
echo *.db >> exclude.txt
echo *.log >> exclude.txt

# Copiar tudo exceto o que está em exclude.txt
xcopy /E /I /EXCLUDE:exclude.txt ..\app31\* .

# Remover arquivo temporário
del exclude.txt
```

### 3. Criar docker-compose.override.yml

Crie o arquivo `docker-compose.override.yml` em app32:

```yaml
# ============================================
# Override para DESENVOLVIMENTO
# ============================================
# Este arquivo adiciona volumes de código
# para que mudanças apareçam imediatamente
# ============================================

services:
  app:
    volumes:
      # Montar código fonte (para ver mudanças em tempo real)
      - ./modules:/app/modules
      - ./templates:/app/templates
      - ./static:/app/static
      - ./models:/app/models
      - ./middleware:/app/middleware
      - ./database:/app/database
      - ./migrations:/app/migrations
      - ./utils:/app/utils
      - ./relatorios:/app/relatorios
      - ./services:/app/services
      - ./api:/app/api
      - ./config_database.py:/app/config_database.py
      - ./app_pev.py:/app/app_pev.py
    
    # Desabilitar restart automático em dev
    restart: "no"
    
    # Modo desenvolvimento
    environment:
      FLASK_ENV: development
      FLASK_DEBUG: "1"
```

### 4. Criar .env.development

Crie o arquivo `.env.development` em app32:

```env
# ============================================
# Configuração de DESENVOLVIMENTO
# ============================================

# Flask
FLASK_APP=app_pev.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret-key-change-in-production-2024

# Banco de dados (DEV - pode ser local)
DATABASE_URL=postgresql://postgres:*Paraiso1978@localhost:5432/bd_app_versus_dev
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=*Paraiso1978
POSTGRES_DB=bd_app_versus_dev

# Redis (opcional em dev)
REDIS_PASSWORD=dev_redis_password
REDIS_URL=redis://:dev_redis_password@localhost:6379/0

# Outros (opcional)
MAIL_SERVER=
MAIL_USERNAME=
MAIL_PASSWORD=
AI_API_KEY=
```

### 5. Ajustar docker-compose.yml (se necessário)

Se quiser usar porta diferente em dev:

```yaml
ports:
  - "5004:5002"  # Porta diferente de app31 (5003)
```

### 6. Iniciar Desenvolvimento

```bash
cd C:\GestaoVersus\app32

# Iniciar Docker
docker-compose up

# Acessar
# http://localhost:5004 (ou porta configurada)
```

---

## ✅ Checklist Inicial

- [ ] Pasta app32 criada
- [ ] Código copiado de app31
- [ ] docker-compose.override.yml criado
- [ ] .env.development configurado
- [ ] Docker iniciado sem erros
- [ ] Aplicação acessível no navegador

---

## 🎯 Agora Você Pode

- ✅ Editar código à vontade
- ✅ Mudanças aparecem automaticamente (hot-reload)
- ✅ Testar sem medo
- ✅ Quebrar e corrigir
- ✅ Desenvolver novas features

---

## 📝 Lembre-se

- ❌ **NÃO** conectar app32 ao Git
- ❌ **NÃO** usar app32 para correções urgentes em produção
- ✅ Use `PROMOVER_DEV_PARA_PROD.bat` quando estiver pronto
- ✅ Sempre teste antes de promover

---

**Pronto para desenvolver!** 🚀





