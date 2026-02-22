# 🚀 GestaoVersus - Guia Completo de Deploy

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração Inicial](#configuração-inicial)
3. [Deploy Local (Desenvolvimento)](#deploy-local)
4. [Deploy em Servidor (VPS)](#deploy-servidor)
5. [Deploy no Google Cloud](#deploy-google-cloud)
6. [Configuração de Domínio](#configuração-domínio)
7. [Backup e Monitoramento](#backup-monitoramento)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Pré-requisitos

### Software Necessário

- **Docker** 20.10+ e **Docker Compose** 2.0+
- **Git** 2.30+
- **Python** 3.9+ (para desenvolvimento local)
- **PostgreSQL** 15+ (ou usar Docker)

### Contas Necessárias

- [ ] Conta no GitHub (para CI/CD)
- [ ] Conta no Google Cloud ou AWS (para hospedagem)
- [ ] Domínio registrado (ex: congigr.com)

---

## ⚙️ Configuração Inicial

### 1. Clone o Repositório

```bash
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app31
```

### 2. Configure Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp env.example .env

# Editar com suas configurações
nano .env
```

**Variáveis Essenciais:**

```env
# Flask
SECRET_KEY=gere-uma-chave-segura-aqui
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://user:password@host:5432/database
POSTGRES_PASSWORD=senha-forte-aqui

# Redis
REDIS_PASSWORD=senha-redis-aqui

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=senha-app-gmail
```

**Gerar SECRET_KEY segura:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Inicializar Aplicação

```bash
# Instalar dependências
pip install -r requirements.txt

# Inicializar aplicação
python scripts/init_app.py

# Health check
python scripts/health_check.py
```

---

## 💻 Deploy Local (Desenvolvimento)

### Usando Docker Compose

```bash
# Iniciar ambiente de desenvolvimento
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f app_dev

# Parar ambiente
docker-compose -f docker-compose.dev.yml down
```

### Acessar Serviços

- **Aplicação:** http://localhost:5003
- **Adminer (DB):** http://localhost:8080
- **MailHog (Email):** http://localhost:8025

### Hot Reload

O código é montado como volume, alterações são aplicadas automaticamente!

---

## 🖥️ Deploy em Servidor (VPS)

### Opção 1: DigitalOcean, Linode, AWS EC2, etc.

#### 1. Preparar Servidor

```bash
# SSH no servidor
ssh user@seu-servidor.com

# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalação
docker --version
docker-compose --version
```

#### 2. Clonar Projeto

```bash
# Criar diretório
sudo mkdir -p /opt/gestaoversos
sudo chown $USER:$USER /opt/gestaoversos

# Clonar
cd /opt/gestaoversos
git clone https://github.com/mff2000/GestaoVersus.git .
cd app31
```

#### 3. Configurar Ambiente

```bash
# Copiar e editar .env
cp env.production.example .env
nano .env

# Configurar permissões
chmod 600 .env
```

#### 4. Iniciar Aplicação

```bash
# Build e iniciar
docker-compose up -d --build

# Ver logs
docker-compose logs -f

# Verificar status
docker-compose ps

# Health check
curl http://localhost:5002/health
```

#### 5. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado
sudo certbot certonly --standalone -d congigr.com -d www.congigr.com

# Copiar certificados para nginx
sudo cp /etc/letsencrypt/live/congigr.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/congigr.com/privkey.pem nginx/ssl/

# Reiniciar nginx
docker-compose restart nginx
```

#### 6. Configurar Renovação Automática

```bash
# Adicionar ao crontab
sudo crontab -e

# Adicionar linha:
0 3 * * * certbot renew --quiet --deploy-hook "cd /opt/gestaoversos/app31 && docker-compose restart nginx"
```

---

## ☁️ Deploy no Google Cloud

### Opção 2A: Cloud Run (Recomendado - Serverless)

#### 1. Instalar Google Cloud SDK

```bash
# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Windows
# Baixar de: https://cloud.google.com/sdk/docs/install
```

#### 2. Configurar Projeto

```bash
# Criar projeto
gcloud projects create gestaoversos-prod --name="GestaoVersus Production"

# Selecionar projeto
gcloud config set project gestaoversos-prod

# Habilitar APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com
```

#### 3. Setup Automático

```bash
# Executar script de setup
chmod +x scripts/deploy/setup_gcp.sh
./scripts/deploy/setup_gcp.sh
```

Ou manualmente:

#### 4. Criar Cloud SQL

```bash
gcloud sql instances create gestaoversos-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create bd_app_versus \
  --instance=gestaoversos-db
```

#### 5. Build e Deploy

```bash
# Build Docker image
gcloud builds submit --tag gcr.io/gestaoversos-prod/gestaoversos

# Deploy no Cloud Run
gcloud run deploy gestaoversos \
  --image gcr.io/gestaoversos-prod/gestaoversos \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances=10

# Obter URL
gcloud run services describe gestaoversos --region us-central1 --format='value(status.url)'
```

### Opção 2B: App Engine

```bash
# Deploy usando app.yaml
gcloud app deploy app.yaml

# Ver logs
gcloud app logs tail

# Abrir aplicação
gcloud app browse
```

### Configurar CI/CD Automático

```bash
# Criar trigger no Cloud Build
gcloud builds triggers create github \
  --repo-name=GestaoVersus \
  --repo-owner=mff2000 \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

---

## 🌐 Configuração de Domínio

### 1. Mapear Domínio (Cloud Run)

```bash
gcloud run domain-mappings create \
  --service gestaoversos \
  --domain congigr.com \
  --region us-central1
```

### 2. Configurar DNS

No seu provedor de domínio (GoDaddy, Namecheap, etc):

```
Type: A
Name: @
Value: [IP_DO_SERVIDOR]

Type: A
Name: www
Value: [IP_DO_SERVIDOR]

Type: CNAME (para Cloud Run)
Name: @
Value: ghs.googlehosted.com
```

### 3. Verificar Propagação

```bash
# Verificar DNS
nslookup congigr.com

# Verificar SSL
curl -I https://congigr.com
```

---

## 💾 Backup e Monitoramento

### Configurar Backup Automático

#### 1. Backup Local (Servidor)

```bash
# Adicionar ao crontab
crontab -e

# Backup diário às 3:00 AM
0 3 * * * cd /opt/gestaoversos/app31 && docker-compose exec -T app python scripts/backup/backup_database.py

# Backup de arquivos semanal
0 3 * * 0 cd /opt/gestaoversos/app31 && docker-compose exec -T app python scripts/backup/backup_files.py
```

#### 2. Backup para S3/GCS

```bash
# Configurar variáveis no .env
BACKUP_ENABLED=true
BACKUP_STORAGE=s3  # ou gcs
AWS_ACCESS_KEY_ID=sua-key
AWS_SECRET_ACCESS_KEY=sua-secret
AWS_S3_BUCKET=gestaoversos-backups
```

### Monitoramento

#### Google Cloud Monitoring

```bash
# Habilitar API
gcloud services enable monitoring.googleapis.com

# Ver logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gestaoversos" --limit 50
```

#### Uptime Monitoring

Configurar em:
- **Google Cloud:** https://console.cloud.google.com/monitoring
- **UptimeRobot:** https://uptimerobot.com (grátis)
- **Pingdom:** https://www.pingdom.com

---

## 🔧 Troubleshooting

### Aplicação não inicia

```bash
# Ver logs
docker-compose logs app

# Verificar health
docker-compose exec app python scripts/health_check.py

# Reiniciar
docker-compose restart app
```

### Erro de conexão com banco

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps db

# Ver logs do banco
docker-compose logs db

# Testar conexão
docker-compose exec db psql -U postgres -d bd_app_versus -c "SELECT 1;"
```

### Erro SSL/HTTPS

```bash
# Verificar certificados
sudo certbot certificates

# Renovar manualmente
sudo certbot renew

# Verificar configuração Nginx
docker-compose exec nginx nginx -t
```

### Performance Issues

```bash
# Ver uso de recursos
docker stats

# Escalar workers
# Editar docker-compose.yml:
# command: gunicorn --workers 8 --threads 4 ...

# Reiniciar
docker-compose up -d --no-deps --build app
```

### Restaurar Backup

```bash
# Listar backups
ls -lh backups/

# Restaurar
docker-compose exec -T app python scripts/backup/restore_database.py
```

---

## 📚 Comandos Úteis

### Docker

```bash
# Ver todos os containers
docker-compose ps

# Logs em tempo real
docker-compose logs -f

# Entrar no container
docker-compose exec app bash

# Limpar volumes
docker-compose down -v

# Rebuild completo
docker-compose up -d --build --force-recreate
```

### Banco de Dados

```bash
# Conectar no PostgreSQL
docker-compose exec db psql -U postgres -d bd_app_versus

# Backup manual
docker-compose exec -T db pg_dump -U postgres bd_app_versus > backup_manual.sql

# Restore manual
docker-compose exec -T db psql -U postgres -d bd_app_versus < backup_manual.sql
```

### Migrations

```bash
# Criar migration
docker-compose exec app flask db migrate -m "Descrição"

# Aplicar migrations
docker-compose exec app flask db upgrade

# Reverter migration
docker-compose exec app flask db downgrade
```

---

## 🎉 Checklist Final

- [ ] Aplicação funcionando em produção
- [ ] SSL configurado (HTTPS)
- [ ] Domínio configurado
- [ ] Backup automático configurado
- [ ] Monitoring/Uptime check configurado
- [ ] CI/CD configurado (GitHub Actions ou Cloud Build)
- [ ] Senhas fortes configuradas
- [ ] Email funcionando
- [ ] Health check passando
- [ ] Documentação atualizada

---

## 📞 Suporte

- **Documentação:** `/docs/`
- **Issues:** https://github.com/mff2000/GestaoVersus/issues
- **Email:** suporte@congigr.com

---

**🎉 Parabéns! Sua aplicação está no ar! 🚀**

