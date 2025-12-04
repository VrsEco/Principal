# 🚀 Deploy Rápido no Google Cloud

## ⚡ TL;DR - Comandos Rápidos

### **IMPORTANTE: Fazer BACKUP primeiro!**

```bash
# 1. BACKUP (Console GCP)
# https://console.cloud.google.com/sql/instances
# Selecione instância → Backups → CREATE BACKUP
```

---

## 🎯 Opção Recomendada: Cloud Shell

### 1. Abrir Cloud Shell
```
https://shell.cloud.google.com
```

### 2. Clonar/Atualizar Código
```bash
cd gestaoversus  # ou git clone se primeira vez
git pull origin main
```

### 3. Setup Rápido
```bash
# Configurar projeto
gcloud config set project SEU_PROJECT_ID

# Variáveis (AJUSTE SEUS VALORES)
export CLOUD_SQL_CONNECTION_NAME="projeto:regiao:instancia"
export DB_USER="postgres"
export DB_PASS="sua_senha"
export DB_NAME="gestaopev"

# Instalar deps
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Conectar ao Cloud SQL
cloud_sql_proxy -instances=$CLOUD_SQL_CONNECTION_NAME=tcp:5432 &
sleep 5

# Configurar DATABASE_URL
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME"
export FLASK_APP=app_pev.py
```

### 4. Aplicar Migração
```bash
# Ver versão atual
flask db current

# Aplicar
flask db upgrade

# Verificar
python3 check_migration_status.py
```

### 5. Validar
```bash
gcloud sql connect NOME_INSTANCIA --user=postgres --database=gestaopev
```

```sql
-- Verificar roles (não deve ter 'consultant')
SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role;

-- Sair
\q
```

### 6. Reiniciar App
```bash
# Cloud Run
gcloud run deploy gestaoversus --source . --region=us-central1

# OU App Engine
gcloud app deploy

# OU VM (SSH e reiniciar serviço)
```

---

## 🆘 Se der erro:

### Rollback da Migração:
```bash
export FLASK_APP=app_pev.py
flask db downgrade -1
```

### Restaurar Backup:
```bash
gcloud sql backups list --instance=INSTANCE_NAME
gcloud sql backups restore BACKUP_ID --backup-instance=INSTANCE_NAME
```

---

## ✅ Checklist Final

- [ ] Backup criado
- [ ] Migração aplicada (`flask db upgrade`)
- [ ] Verificado: 0 usuários 'consultant'
- [ ] App reiniciado
- [ ] Testado login com diferentes perfis
- [ ] MyWork funcionando

---

## 📋 Valores que você precisa:

Antes de começar, tenha em mãos:

1. **PROJECT_ID**: ID do projeto GCP
2. **INSTANCE_NAME**: Nome da instância Cloud SQL
3. **REGION**: Região (ex: us-central1)
4. **DB_USER**: Usuário do banco (geralmente 'postgres')
5. **DB_PASS**: Senha do banco
6. **DB_NAME**: Nome do banco (geralmente 'gestaopev')

**Connection String completo:**
```
PROJECT_ID:REGION:INSTANCE_NAME
```

Exemplo:
```
gestaoversus-prod:us-central1:gestaopev-db
```

---

## 🔍 Como encontrar esses valores:

```bash
# Listar projetos
gcloud projects list

# Listar instâncias Cloud SQL
gcloud sql instances list

# Ver detalhes da instância
gcloud sql instances describe INSTANCE_NAME
```

---

**Guia Completo:** `docs/DEPLOY_MIGRATION_GCP.md`  
**Dúvidas?** Consulte o guia completo para troubleshooting detalhado.



