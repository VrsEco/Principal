# 🚀 Guia Completo de Deploy - GestaoVersus (APP30)

Documentação completa para virtualizar e hospedar o projeto online.

## 📋 Índice

- [Pré-requisitos](#pré-requisitos)
- [Ambientes](#ambientes)
- [Deploy Local com Docker](#deploy-local-com-docker)
- [Deploy em Produção](#deploy-em-produção)
- [Deploy no Google Cloud Platform](#deploy-no-google-cloud-platform)
- [Configuração do GitHub](#configuração-do-github)
- [Backup Automático](#backup-automático)
- [Monitoramento](#monitoramento)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Pré-requisitos

### Software Necessário

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **Git** 2.30+
- **Python** 3.9+ (para desenvolvimento local)
- **PostgreSQL Client** 15+ (para backups)

### Contas Necessárias

1. **GitHub** - Para versionamento e CI/CD
2. **Google Cloud Platform** (ou AWS) - Para hospedagem
3. **Domínio** - congigr.com (já configurado)

---

## 🌍 Ambientes

O projeto possui 3 ambientes:

### 1. **Desenvolvimento (Local)**
- SQLite ou PostgreSQL local
- Hot-reload habilitado
- Debug mode ativo
- Sem SSL

### 2. **Staging/Testes**
- PostgreSQL em container
- Ambiente de teste pré-produção
- Branch: `develop`

### 3. **Produção**
- PostgreSQL Cloud (Cloud SQL)
- SSL obrigatório
- Backup automático
- Monitoramento ativo
- Branch: `main`

---

## 🐳 Deploy Local com Docker

### 1. Clonar o Repositório

```bash
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app30
```

### 2. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env.development

# Editar com seus valores
nano .env.development
```

### 3. Iniciar Ambiente de Desenvolvimento

```bash
# Usar docker-compose para desenvolvimento
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f app_dev

# Acessar
http://localhost:5002
```

### 4. Parar Ambiente

```bash
docker-compose -f docker-compose.dev.yml down
```

---

## 🚀 Deploy em Produção

### Opção 1: Docker Compose (Servidor Próprio)

#### 1. Preparar Servidor

```bash
# Conectar ao servidor
ssh user@seu-servidor.com

# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Clonar e Configurar

```bash
# Clonar repositório
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app30

# Configurar ambiente
cp .env.example .env.production
nano .env.production  # IMPORTANTE: Configure TODAS as variáveis!
```

#### 3. Configurar Secrets

```bash
# Gerar SECRET_KEY segura
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Editar .env.production e adicionar:
# - SECRET_KEY (gerada acima)
# - DATABASE_URL (PostgreSQL)
# - OPENAI_API_KEY
# - EMAIL e WHATSAPP configs
# - AWS S3 credentials (para backup)
```

#### 4. Iniciar Produção

```bash
# Build e start
docker-compose up -d --build

# Verificar status
docker-compose ps

# Ver logs
docker-compose logs -f

# Rodar migrações
docker-compose exec app flask db upgrade
```

#### 5. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt-get update
sudo apt-get install certbot

# Obter certificado
sudo certbot certonly --standalone -d congigr.com -d www.congigr.com

# Copiar certificados
sudo cp /etc/letsencrypt/live/congigr.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/congigr.com/privkey.pem nginx/ssl/

# Reiniciar nginx
docker-compose restart nginx
```

#### 6. Auto-renovação SSL

```bash
# Adicionar ao crontab
sudo crontab -e

# Adicionar linha:
0 3 * * * certbot renew --quiet && docker-compose restart nginx
```

---

## ☁️ Deploy no Google Cloud Platform

### 1. Preparar Projeto GCP

```bash
# Instalar gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login
gcloud auth login

# Criar projeto (se não existe)
gcloud projects create gestaoversos-prod --name="GestaoVersus"

# Configurar projeto
gcloud config set project gestaoversos-prod
```

### 2. Executar Setup Automático

```bash
# Tornar script executável
chmod +x scripts/setup_gcp.sh

# Executar (vai pedir algumas informações)
./scripts/setup_gcp.sh
```

O script vai:
- ✅ Habilitar APIs necessárias
- ✅ Criar Cloud SQL (PostgreSQL)
- ✅ Criar VPC Connector
- ✅ Criar Cloud Storage buckets
- ✅ Configurar Service Account
- ✅ Criar secrets
- ✅ Fazer deploy inicial

### 3. Configurar Domínio

```bash
# Mapear domínio customizado
gcloud run domain-mappings create \
  --service gestaoversos-app \
  --domain congigr.com \
  --region us-central1

# Adicionar registros DNS (no seu provedor de domínio)
# O comando acima mostrará os registros necessários
```

### 4. Configurar CI/CD Automático

Os arquivos GitHub Actions já estão configurados. Basta:

1. **Configurar Secrets no GitHub:**

```bash
# Ir para: https://github.com/mff2000/GestaoVersus/settings/secrets/actions
```

Adicionar:
- `GCP_SA_KEY` - JSON da service account
- `DOCKER_USERNAME` - Usuário Docker Hub
- `DOCKER_PASSWORD` - Senha Docker Hub

2. **Obter Service Account Key:**

```bash
gcloud iam service-accounts keys create gcp-key.json \
  --iam-account=gestaoversos-sa@gestaoversos-prod.iam.gserviceaccount.com

# Copiar conteúdo e adicionar como secret GCP_SA_KEY
cat gcp-key.json

# IMPORTANTE: Deletar arquivo após copiar
rm gcp-key.json
```

3. **Agora todo push em `main` fará deploy automático!**

---

## 🔧 Configuração do GitHub

### 1. Criar Repositório

```bash
# Se ainda não criou
git init
git remote add origin https://github.com/mff2000/GestaoVersus.git
```

### 2. Estrutura de Branches

```
main (produção)
  ├── develop (desenvolvimento)
  └── feature/* (features específicas)
```

### 3. Proteger Branch Main

```
GitHub → Settings → Branches → Add rule

Branch name pattern: main

✅ Require pull request reviews before merging
✅ Require status checks to pass before merging
✅ Require branches to be up to date before merging
```

### 4. Configurar Secrets

```
GitHub → Settings → Secrets and variables → Actions → New repository secret
```

Adicionar:
- `GCP_SA_KEY`
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `SECRET_KEY` (produção)

### 5. Primeiro Deploy

```bash
# Commit inicial
git add .
git commit -m "feat: initial project setup with deploy configuration"
git push origin main

# GitHub Actions vai rodar automaticamente
# Ver em: https://github.com/mff2000/GestaoVersus/actions
```

---

## 💾 Backup Automático

### 1. Backup Local (Docker)

O container `backup` já está configurado no `docker-compose.yml`.

```bash
# Executar backup manual
docker-compose exec backup python backup_database.py

# Ver backups
ls -lh backups/

# Restaurar backup
docker-compose exec backup python scripts/restore_database.py
```

### 2. Backup Agendado (CRON)

```bash
# Configurar CRON
chmod +x scripts/setup_cron_backup.sh
./scripts/setup_cron_backup.sh

# Backup será executado todo dia às 3:00 AM
```

### 3. Backup Cloud (GCP)

```bash
# Já configurado no GitHub Actions (.github/workflows/backup.yml)
# Executa todo dia às 3:00 AM UTC

# Executar manualmente
gh workflow run backup.yml
```

### 4. Verificar Backups

```bash
# No GCS
gsutil ls gs://gestaoversos-prod-backups/

# No S3
aws s3 ls s3://gestaoversos-backups/
```

### 5. Restaurar Backup

```bash
# Download do GCS
gsutil cp gs://gestaoversos-prod-backups/database/backup_YYYYMMDD_HHMMSS.sql ./

# Restaurar PostgreSQL
docker-compose exec db psql -U gestaoversos_user -d gestaoversos_prod < backup_YYYYMMDD_HHMMSS.sql
```

---

## 📊 Monitoramento

### 1. Health Check

```bash
# Verificar saúde da aplicação
curl https://congigr.com/health

# Resposta esperada:
{"status": "healthy", "timestamp": "2025-10-19T..."}
```

### 2. Logs

#### Docker Local
```bash
# Ver logs em tempo real
docker-compose logs -f app

# Ver logs de todas as services
docker-compose logs -f
```

#### Google Cloud
```bash
# Logs do Cloud Run
gcloud run services logs read gestaoversos-app --region us-central1

# Logs em tempo real
gcloud run services logs tail gestaoversos-app --region us-central1
```

### 3. Métricas (GCP)

```bash
# Abrir Cloud Console
https://console.cloud.google.com/run/detail/us-central1/gestaoversos-app/metrics
```

Métricas disponíveis:
- Request count
- Request latency
- Container instance count
- CPU utilization
- Memory utilization

### 4. Alertas (Opcional)

```bash
# Criar alerta de error rate alto
gcloud alpha monitoring policies create \
  --notification-channels=EMAIL_CHANNEL_ID \
  --display-name="Error Rate Alert" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

---

## 🔍 Troubleshooting

### Problema: Container não inicia

```bash
# Ver logs detalhados
docker-compose logs app

# Verificar configuração
docker-compose config

# Recriar container
docker-compose up -d --force-recreate app
```

### Problema: Banco de dados não conecta

```bash
# Verificar se PostgreSQL está rodando
docker-compose ps db

# Ver logs do banco
docker-compose logs db

# Testar conexão manual
docker-compose exec app python -c "from models import db; db.create_all(); print('OK')"
```

### Problema: Erro 502 Bad Gateway (Nginx)

```bash
# Verificar se app está rodando
docker-compose ps app

# Verificar logs do nginx
docker-compose logs nginx

# Verificar configuração nginx
docker-compose exec nginx nginx -t
```

### Problema: Migrações não rodam

```bash
# Rodar manualmente
docker-compose exec app flask db upgrade

# Ver status das migrações
docker-compose exec app flask db current

# Criar nova migração (se necessário)
docker-compose exec app flask db migrate -m "descrição"
```

### Problema: Deploy GCP falha

```bash
# Ver logs do Cloud Build
gcloud builds list --limit=5
gcloud builds log BUILD_ID

# Ver logs do Cloud Run
gcloud run services logs read gestaoversos-app --region us-central1 --limit=50

# Verificar secrets
gcloud secrets list
```

### Problema: Backup falha

```bash
# Verificar configuração
cat .env.production | grep BACKUP

# Testar backup manual
python scripts/backup_database.py

# Verificar permissões
ls -la backups/
```

---

## 📞 Comandos Úteis

### Docker

```bash
# Ver todos os containers
docker ps -a

# Ver uso de recursos
docker stats

# Limpar sistema
docker system prune -a --volumes

# Build sem cache
docker-compose build --no-cache
```

### PostgreSQL

```bash
# Conectar ao banco
docker-compose exec db psql -U gestaoversos_user -d gestaoversos_prod

# Dump do banco
docker-compose exec db pg_dump -U gestaoversos_user gestaoversos_prod > dump.sql

# Verificar tamanho do banco
docker-compose exec db psql -U gestaoversos_user -d gestaoversos_prod -c "SELECT pg_size_pretty(pg_database_size('gestaoversos_prod'));"
```

### Flask

```bash
# Shell interativo
docker-compose exec app flask shell

# Criar admin
docker-compose exec app python -c "from models import User, db; user = User(email='admin@congigr.com', is_admin=True); user.set_password('senha123'); db.session.add(user); db.session.commit()"

# Listar rotas
docker-compose exec app flask routes
```

---

## 🎯 Checklist de Deploy

### Pré-Deploy
- [ ] Código no GitHub
- [ ] Testes passando
- [ ] Variáveis de ambiente configuradas
- [ ] Secrets configurados
- [ ] Backup do banco atual

### Deploy
- [ ] Build Docker bem-sucedido
- [ ] Containers iniciaram
- [ ] Migrações executadas
- [ ] Health check OK
- [ ] SSL configurado (se aplicável)

### Pós-Deploy
- [ ] Testar login
- [ ] Testar funcionalidades principais
- [ ] Verificar logs
- [ ] Configurar monitoramento
- [ ] Documentar versão deployed

---

## 🔐 Segurança

### Checklist de Segurança

- [ ] `SECRET_KEY` é única e segura (32+ caracteres)
- [ ] Senhas de banco não estão hardcoded
- [ ] `.env` files estão no `.gitignore`
- [ ] SSL/HTTPS configurado
- [ ] Firewall configurado (apenas portas 80, 443)
- [ ] Backup automático ativo
- [ ] Logs não contêm senhas/tokens
- [ ] Rate limiting ativo
- [ ] CSRF protection habilitada

### Atualizar Secrets

```bash
# Gerar nova SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Atualizar no GCP
echo -n "nova-secret-key" | gcloud secrets versions add SECRET_KEY --data-file=-

# Redeploy
gcloud run services update gestaoversos-app --region us-central1
```

---

## 📚 Recursos Adicionais

- [Docker Documentation](https://docs.docker.com/)
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Flask Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Configuration](https://nginx.org/en/docs/)

---

## 🆘 Suporte

Para problemas ou dúvidas:

1. **Verificar logs** primeiro
2. **Consultar este documento**
3. **Verificar GitHub Issues**
4. **Contatar equipe de desenvolvimento**

---

**GestaoVersus (APP30)** - Sistema de Gestão Empresarial  
**Versão:** 30  
**Última atualização:** 19/10/2025


