# ⚡ Quick Start - Deploy GestaoVersus

Guia rápido para colocar o projeto no ar em minutos.

## 🚀 Opção 1: Deploy Local (Desenvolvimento)

```bash
# 1. Clonar
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app30

# 2. Configurar
cp .env.example .env.development

# 3. Iniciar
docker-compose -f docker-compose.dev.yml up -d

# 4. Acessar
http://localhost:5002
```

**Pronto! Aplicação rodando em modo desenvolvimento.**

---

## ☁️ Opção 2: Deploy Google Cloud (Produção)

### Pré-requisitos
- Conta Google Cloud
- `gcloud` CLI instalado

### Passos

```bash
# 1. Login GCP
gcloud auth login
gcloud config set project seu-project-id

# 2. Clonar e configurar
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app30

# 3. Executar setup automático
chmod +x scripts/setup_gcp.sh
./scripts/setup_gcp.sh
```

**O script vai configurar tudo automaticamente!**

Depois:
1. Configure DNS para apontar para o Cloud Run
2. Adicione secrets no GitHub para CI/CD automático

---

## 🐳 Opção 3: Servidor Próprio (Docker)

```bash
# 1. No servidor, instalar Docker
curl -fsSL https://get.docker.com | sh

# 2. Clonar projeto
git clone https://github.com/mff2000/GestaoVersus.git
cd GestaoVersus/app30

# 3. Configurar ambiente
cp .env.example .env.production
nano .env.production  # Editar variáveis

# 4. Iniciar
docker-compose up -d --build

# 5. Configurar SSL (Let's Encrypt)
sudo certbot certonly --standalone -d congigr.com
sudo cp /etc/letsencrypt/live/congigr.com/*.pem nginx/ssl/
docker-compose restart nginx
```

**Aplicação rodando com SSL!**

---

## ✅ Verificar Deploy

```bash
# Health check
curl https://seu-dominio.com/health

# Ver logs
docker-compose logs -f app
```

---

## 🔄 Atualizar Aplicação

```bash
# Pull novos códigos
git pull origin main

# Rebuild e restart
docker-compose up -d --build

# Rodar migrações
docker-compose exec app flask db upgrade
```

---

## 📋 Comandos Úteis

```bash
# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f

# Parar tudo
docker-compose down

# Backup
python scripts/backup_database.py

# Restaurar
python scripts/restore_database.py
```

---

## 🆘 Problemas?

1. **Container não inicia**: `docker-compose logs app`
2. **Erro de banco**: Verificar `DATABASE_URL` no `.env`
3. **Erro 502**: `docker-compose restart nginx`

**Documentação completa:** Ver `DEPLOY.md`

---

**GestaoVersus** - Deploy em minutos! 🚀


