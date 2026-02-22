# 📚 Índice - Arquivos de Deploy e Virtualização

## 🎯 COMEÇAR POR AQUI

### Para Começar Rápido
1. **`_COMECE_AQUI_DEPLOY.md`** ⭐ - **COMECE AQUI!** Guia de início
2. **`_RESUMO_VIRTUALIZACAO_DEPLOY.md`** ⭐ - Resumo executivo completo
3. **`QUICK_START_DEPLOY.md`** ⭐ - Deploy em minutos
4. **`start.sh`** ou **`start.bat`** ⭐ - Menu interativo

### Para Entender os Conceitos
1. **`_GUIA_CONCEITOS_VIRTUALIZACAO.md`** 📚 - **O que cada coisa faz?**

### Para Entender Tudo
1. **`DEPLOY.md`** 📖 - Guia completo (500+ linhas)
2. **`VIRTUALIZACAO_COMPLETA.md`** 📖 - Detalhes técnicos

---

## 📁 ESTRUTURA POR CATEGORIA

### 🐳 Docker
```
Dockerfile                      # Imagem da aplicação
docker-compose.yml              # Produção
docker-compose.dev.yml          # Desenvolvimento
.dockerignore                   # Otimização de build
```

**Para usar:**
- Desenvolvimento: `docker-compose -f docker-compose.dev.yml up -d`
- Produção: `docker-compose up -d --build`

---

### ⚙️ Configuração
```
.env.example                    # Template de variáveis
config_prod.py                  # Configurações produção
config_dev.py                   # Configurações desenvolvimento
```

**Para usar:**
1. `cp .env.example .env.production`
2. Editar `.env.production` com seus valores
3. Nunca commitar `.env.*` no Git!

---

### 🔐 Segurança
```
.gitignore                      # Proteção de dados (ATUALIZADO)
```

**O que protege:**
- Variáveis de ambiente (.env)
- Credenciais (*.pem, *.key)
- Bancos de dados (*.db)
- Backups
- Uploads
- Logs

---

### 🚀 CI/CD (GitHub Actions)
```
.github/workflows/
├── ci-cd-production.yml       # Deploy automático produção
├── ci-cd-development.yml      # Deploy automático dev
└── backup.yml                 # Backup agendado diário
```

**Como funciona:**
- Push em `main` → Deploy produção
- Push em `develop` → Deploy dev
- Todo dia 3:00 AM → Backup automático

**Configurar:**
1. GitHub → Settings → Secrets
2. Adicionar: `GCP_SA_KEY`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`

---

### ☁️ Google Cloud Platform
```
app.yaml                        # App Engine config
cloudbuild.yaml                 # Cloud Build config
cloud-run.yaml                  # Cloud Run service
scripts/setup_gcp.sh            # Setup automático ⭐
```

**Para usar:**
```bash
chmod +x scripts/setup_gcp.sh
./scripts/setup_gcp.sh
```

Vai configurar:
- Cloud SQL (PostgreSQL)
- Cloud Storage (uploads/backups)
- Cloud Run (aplicação)
- VPC Connector
- Secret Manager
- Service Account

---

### 🌐 Nginx (Reverse Proxy)
```
nginx/nginx.conf                # Configuração com SSL
```

**Funcionalidades:**
- Reverse proxy para Flask
- SSL/HTTPS (Let's Encrypt)
- Rate limiting (anti-DDoS)
- Gzip compression
- Security headers
- Static files serving

---

### 💾 Backup
```
scripts/
├── backup_database.py         # Backup completo ⭐
├── restore_database.py        # Restauração ⭐
└── setup_cron_backup.sh       # Agendamento CRON
```

**Para usar:**
```bash
# Backup manual
python scripts/backup_database.py

# Restaurar
python scripts/restore_database.py

# Agendar (diário 3:00 AM)
./scripts/setup_cron_backup.sh
```

**Suporta:**
- PostgreSQL e SQLite
- Upload AWS S3
- Upload Google Cloud Storage
- Retenção 30 dias
- Limpeza automática

---

### 🏥 Utilitários
```
scripts/health_check.py         # Verificar aplicação
start.sh                        # Menu Linux/Mac ⭐
start.bat                       # Menu Windows ⭐
```

**Para usar:**
```bash
# Menu interativo
./start.sh  # Linux/Mac
start.bat   # Windows

# Health check
python scripts/health_check.py --url https://congigr.com
```

---

### 📦 Dependências
```
requirements.txt                # Dependências principais
requirements-deploy.txt         # Dependências deploy
```

**Inclui:**
- Flask, SQLAlchemy, PostgreSQL
- Gunicorn (servidor produção)
- Redis, Celery (tarefas assíncronas)
- boto3 (AWS S3)
- google-cloud-storage (GCS)

---

### 📖 Documentação
```
DEPLOY.md                       # Guia completo (500+ linhas) 📖
QUICK_START_DEPLOY.md           # Guia rápido ⚡
VIRTUALIZACAO_COMPLETA.md       # Detalhes técnicos 🔧
_RESUMO_VIRTUALIZACAO_DEPLOY.md # Resumo executivo ⭐
_INDICE_DEPLOY.md              # Este arquivo 📚
```

---

## 🎯 GUIA RÁPIDO POR OBJETIVO

### Quero testar localmente
1. Ler: `QUICK_START_DEPLOY.md`
2. Executar: `./start.sh` → Opção 1
3. Acessar: http://localhost:5002

### Quero colocar em produção
1. Ler: `DEPLOY.md` → "Deploy em Produção"
2. Configurar: `.env.production`
3. Executar: `docker-compose up -d --build`

### Quero usar Google Cloud
1. Ler: `DEPLOY.md` → "Deploy no Google Cloud Platform"
2. Executar: `./scripts/setup_gcp.sh`
3. Configurar DNS

### Quero CI/CD automático
1. Ler: `DEPLOY.md` → "Configuração do GitHub"
2. Configurar secrets no GitHub
3. Push para `main` = deploy automático!

### Quero fazer backup
1. Manual: `python scripts/backup_database.py`
2. Automático: `./scripts/setup_cron_backup.sh`
3. Ver backups: `ls -lh backups/`

### Quero restaurar backup
1. Executar: `python scripts/restore_database.py`
2. Escolher backup da lista
3. Confirmar restauração

---

## 📊 FLUXOGRAMA DE DECISÃO

```
Começar Deploy
     ↓
Já tem experiência com Docker?
  ├─ Não → Ler QUICK_START_DEPLOY.md
  └─ Sim → Ler DEPLOY.md (seção específica)
     ↓
Onde vai hospedar?
  ├─ Desenvolvimento Local → docker-compose.dev.yml
  ├─ Servidor Próprio → docker-compose.yml + nginx
  └─ Google Cloud → scripts/setup_gcp.sh
     ↓
Configurar .env e secrets
     ↓
Deploy!
     ↓
Configurar backup automático
     ↓
Monitorar logs e métricas
```

---

## 🔍 BUSCA RÁPIDA

### "Como fazer deploy local?"
→ `QUICK_START_DEPLOY.md` → Opção 1

### "Como configurar produção?"
→ `DEPLOY.md` → "Deploy em Produção"

### "Como configurar GCP?"
→ `DEPLOY.md` → "Deploy no Google Cloud Platform"
→ `scripts/setup_gcp.sh`

### "Como fazer backup?"
→ `scripts/backup_database.py`
→ `DEPLOY.md` → "Backup Automático"

### "Como resolver problemas?"
→ `DEPLOY.md` → "Troubleshooting"

### "Como configurar CI/CD?"
→ `DEPLOY.md` → "Configuração do GitHub"

### "Comandos úteis?"
→ `DEPLOY.md` → "Comandos Úteis"
→ `_RESUMO_VIRTUALIZACAO_DEPLOY.md` → "Comandos Úteis"

---

## ✅ CHECKLIST DE LEITURA

### Mínimo (Para começar)
- [ ] `_RESUMO_VIRTUALIZACAO_DEPLOY.md`
- [ ] `QUICK_START_DEPLOY.md`

### Recomendado (Para produção)
- [ ] `DEPLOY.md` (completo)
- [ ] `VIRTUALIZACAO_COMPLETA.md`

### Referência (Quando precisar)
- [ ] `.github/workflows/*.yml` (CI/CD)
- [ ] `scripts/backup_database.py` (backup)
- [ ] `nginx/nginx.conf` (nginx)

---

## 🚀 ATALHOS

### Desenvolvimento
```bash
./start.sh → Opção 1
# OU
docker-compose -f docker-compose.dev.yml up -d
```

### Produção
```bash
./start.sh → Opção 2
# OU
docker-compose up -d --build
```

### Google Cloud
```bash
./scripts/setup_gcp.sh
```

### Backup
```bash
./start.sh → Opção 4
# OU
python scripts/backup_database.py
```

### Health Check
```bash
./start.sh → Opção 6
# OU
python scripts/health_check.py
```

---

## 💡 DICAS

1. **Sempre comece pelo resumo**: `_RESUMO_VIRTUALIZACAO_DEPLOY.md`
2. **Use o menu interativo**: `start.sh` ou `start.bat`
3. **Leia troubleshooting**: Economiza tempo
4. **Configure backup**: Não deixe para depois
5. **Teste localmente primeiro**: Antes de produção

---

## 🆘 AJUDA POR NÍVEL

### Iniciante
1. `QUICK_START_DEPLOY.md`
2. `start.sh` (menu interativo)
3. `DEPLOY.md` → "Troubleshooting"

### Intermediário
1. `DEPLOY.md` (completo)
2. `VIRTUALIZACAO_COMPLETA.md`
3. Arquivos específicos (docker-compose, nginx, etc)

### Avançado
1. Arquivos de código diretamente
2. Customizar configs
3. Adicionar funcionalidades

---

**GestaoVersus (APP30)** - Documentação completa de deploy! 📚

**Próximo passo**: Ler `_RESUMO_VIRTUALIZACAO_DEPLOY.md` ⭐


