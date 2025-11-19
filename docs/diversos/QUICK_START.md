# ⚡ Quick Start - GestaoVersus

Guia rápido para colocar a aplicação no ar em **menos de 10 minutos**!

---

## 🎯 Opção 1: Desenvolvimento Local (5 minutos)

### 1. Clone e Configure

```bash
# Clone
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app31

# Configure ambiente
cp env.development.example .env
```

### 2. Inicie com Docker

```bash
# Inicie todos os serviços
docker-compose -f docker-compose.dev.yml up -d

# Aguarde 30 segundos...
```

### 3. Acesse

- **Aplicação:** http://localhost:5003
- **Admin DB:** http://localhost:8080
- **Email Test:** http://localhost:8025

**Login padrão:**
- Email: `admin@gestaoversos.com`
- Senha: `admin123` (TROCAR IMEDIATAMENTE!)

✅ **Pronto! Aplicação rodando!**

---

## 🚀 Opção 2: Produção no Google Cloud (10 minutos)

### 1. Pré-requisitos

```bash
# Instalar Google Cloud SDK
curl https://sdk.cloud.google.com | bash

# Login
gcloud auth login
```

### 2. Setup Automático

```bash
# Clone projeto
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app31

# Execute script de setup
chmod +x scripts/deploy/setup_gcp.sh
./scripts/deploy/setup_gcp.sh

# Siga as instruções interativas
```

### 3. Deploy

```bash
# Build e deploy
gcloud builds submit --tag gcr.io/SEU-PROJECT-ID/gestaoversos
gcloud run deploy gestaoversos \
  --image gcr.io/SEU-PROJECT-ID/gestaoversos \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 4. Obter URL

```bash
gcloud run services describe gestaoversos \
  --region us-central1 \
  --format='value(status.url)'
```

✅ **Pronto! Aplicação online!**

---

## 🖥️ Opção 3: Servidor VPS (Digital Ocean, AWS, etc)

### 1. Preparar Servidor

```bash
# SSH no servidor
ssh root@seu-servidor.com

# Instalar Docker
curl -fsSL https://get.docker.com | sh
```

### 2. Deploy

```bash
# Criar diretório
mkdir -p /opt/gestaoversos && cd /opt/gestaoversos

# Clone
git clone https://github.com/mff2000/GestaoVersus.git .
cd app31

# Configurar
cp env.production.example .env
nano .env  # Edite as variáveis

# Iniciar
docker-compose up -d
```

### 3. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
apt install certbot -y

# Obter certificado
certbot certonly --standalone -d congigr.com

# Copiar certificados
cp /etc/letsencrypt/live/congigr.com/*.pem nginx/ssl/

# Restart nginx
docker-compose restart nginx
```

✅ **Pronto! HTTPS configurado!**

---

## 📋 Comandos Essenciais

### Docker Compose

```bash
# Iniciar
docker-compose up -d

# Parar
docker-compose down

# Ver logs
docker-compose logs -f app

# Reiniciar
docker-compose restart app

# Rebuild
docker-compose up -d --build
```

### Backup

```bash
# Backup banco
python scripts/backup/backup_database.py

# Backup arquivos
python scripts/backup/backup_files.py

# Restaurar
python scripts/backup/restore_database.py
```

### Health Check

```bash
# Verificar saúde da aplicação
python scripts/health_check.py

# Ou via curl
curl http://localhost:5002/health
```

---

## 🔧 Configuração Mínima (.env)

```env
# Flask
SECRET_KEY=gere-chave-secreta-aqui
FLASK_ENV=production

# Database
POSTGRES_PASSWORD=senha-forte
DATABASE_URL=postgresql://postgres:senha-forte@db:5432/bd_app_versus

# Redis
REDIS_PASSWORD=senha-redis

# Email
MAIL_USERNAME=seu-email@gmail.com
MAIL_PASSWORD=senha-app-gmail
```

**Gerar SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🎯 Checklist Rápido

### Desenvolvimento
- [ ] Docker instalado
- [ ] .env configurado
- [ ] `docker-compose -f docker-compose.dev.yml up -d`
- [ ] Acesse http://localhost:5003

### Produção
- [ ] Servidor com Docker
- [ ] .env configurado (senhas fortes!)
- [ ] `docker-compose up -d`
- [ ] SSL configurado
- [ ] Domínio apontando para servidor
- [ ] Backup configurado

---

## 🆘 Problemas Comuns

### Porta em uso
```bash
# Mudar porta no docker-compose.yml
ports:
  - "5004:5002"  # Use 5004 ao invés de 5002
```

### Erro de permissão
```bash
# Dar permissão aos diretórios
chmod -R 755 uploads temp_pdfs logs backups
```

### Banco não conecta
```bash
# Verificar se PostgreSQL está rodando
docker-compose ps db

# Ver logs
docker-compose logs db
```

### Aplicação lenta
```bash
# Aumentar workers no docker-compose.yml
command: gunicorn --workers 8 ...
```

---

## 📚 Próximos Passos

1. **Segurança:**
   - [ ] Trocar senha do admin
   - [ ] Configurar firewall
   - [ ] Habilitar 2FA

2. **Monitoring:**
   - [ ] Configurar uptime monitoring
   - [ ] Configurar alertas
   - [ ] Ver logs regularmente

3. **Backup:**
   - [ ] Testar restauração de backup
   - [ ] Configurar backup automático
   - [ ] Backup para cloud (S3/GCS)

4. **Performance:**
   - [ ] Configurar CDN
   - [ ] Otimizar queries
   - [ ] Cache com Redis

---

## 🔗 Links Úteis

- **Documentação Completa:** [README_DEPLOY.md](README_DEPLOY.md)
- **Conceitos de Virtualização:** [_GUIA_CONCEITOS_VIRTUALIZACAO.md](_GUIA_CONCEITOS_VIRTUALIZACAO.md)
- **Governança:** `/docs/governance/`
- **Templates:** `/docs/templates/`

---

## 📞 Precisa de Ajuda?

- **Issues:** https://github.com/mff2000/GestaoVersus/issues
- **Documentação:** `/docs/`
- **Email:** suporte@congigr.com

---

**🎉 Boa sorte com seu deploy! 🚀**

> **Dica:** Para desenvolvimento, sempre use `docker-compose.dev.yml`!  
> Para produção, use `docker-compose.yml` (sem sufixo).

