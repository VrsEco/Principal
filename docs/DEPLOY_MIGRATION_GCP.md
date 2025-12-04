# 🚀 Deploy da Migração no Google Cloud

**Migração:** Consultant → Collaborator  
**Data:** 03/12/2025  
**Ambiente:** Google Cloud Platform (Cloud SQL)

---

## 📋 Pré-requisitos

Antes de executar no Google Cloud:

- [x] Migração testada e validada em desenvolvimento
- [x] Backup do banco de dados de produção
- [x] Acesso ao Cloud SQL
- [x] Código atualizado no repositório
- [x] Cloud SQL Proxy instalado (se usar conexão local)

---

## 🔐 Opções de Conexão

### **Opção 1: Cloud Shell (Recomendado - Mais Seguro)**

Vantagens:
- ✅ Já tem todas as ferramentas instaladas
- ✅ Autenticação automática
- ✅ Não precisa de Cloud SQL Proxy
- ✅ Conexão segura

### **Opção 2: Cloud SQL Proxy (Local)**

Vantagens:
- ✅ Executa da sua máquina
- ✅ Mais controle
- ✅ Pode fazer troubleshooting localmente

### **Opção 3: Conexão Direta via IP Público**

⚠️ **Não recomendado** - Requer whitelist de IP

---

## 🛡️ Passo 0: BACKUP (OBRIGATÓRIO!)

### Via Console Google Cloud:

1. Acesse: https://console.cloud.google.com/sql/instances
2. Selecione sua instância Cloud SQL
3. Vá em **Backups**
4. Clique em **CREATE BACKUP**
5. Aguarde conclusão (pode demorar alguns minutos)

### Via gcloud CLI:

```bash
# Criar backup sob demanda
gcloud sql backups create --instance=NOME_DA_INSTANCIA

# Listar backups
gcloud sql backups list --instance=NOME_DA_INSTANCIA

# Descrever backup específico
gcloud sql backups describe BACKUP_ID --instance=NOME_DA_INSTANCIA
```

### Via Cloud Shell SQL:

```bash
# Conectar ao Cloud SQL
gcloud sql connect NOME_DA_INSTANCIA --user=postgres --database=gestaopev

# Dentro do psql, criar export
\! pg_dump -h /cloudsql/PROJECT_ID:REGION:INSTANCE_NAME -U postgres gestaopev > backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql
```

---

## 🚀 OPÇÃO 1: Deploy via Cloud Shell (Recomendado)

### Passo 1: Abrir Cloud Shell

```bash
# No console do Google Cloud, clique no ícone de terminal no canto superior direito
# Ou acesse: https://shell.cloud.google.com
```

### Passo 2: Clonar/Atualizar Repositório

```bash
# Se primeira vez
git clone https://github.com/SEU_USUARIO/gestaoversus.git
cd gestaoversus

# Se já existe
cd gestaoversus
git pull origin main  # ou master
```

### Passo 3: Configurar Variáveis de Ambiente

```bash
# Configurar projeto
gcloud config set project SEU_PROJECT_ID

# Definir variáveis
export CLOUD_SQL_CONNECTION_NAME="PROJECT_ID:REGION:INSTANCE_NAME"
export DB_USER="postgres"
export DB_PASS="SUA_SENHA"
export DB_NAME="gestaopev"
```

### Passo 4: Instalar Dependências

```bash
# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar requirements
pip install -r requirements.txt
```

### Passo 5: Configurar Conexão com Cloud SQL

```bash
# Criar diretório para socket do Cloud SQL
mkdir -p /tmp/cloudsql

# Conectar via Cloud SQL Proxy (em background)
cloud_sql_proxy -instances=$CLOUD_SQL_CONNECTION_NAME=tcp:5432 &

# Aguardar alguns segundos
sleep 5

# Configurar DATABASE_URL
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME"
```

### Passo 6: Verificar Conexão

```bash
# Testar conexão
python3 << EOF
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print("✅ Conexão OK:", result.fetchone()[0][:50])
EOF
```

### Passo 7: Verificar Estado Atual

```bash
# Definir app Flask
export FLASK_APP=app_pev.py

# Ver versão atual
flask db current
```

### Passo 8: Aplicar Migração

```bash
# Aplicar migração
flask db upgrade

# Ou usando script Python
python3 run_migration_role.py
```

### Passo 9: Verificar Resultado

```bash
python3 check_migration_status.py
```

### Passo 10: Validar Dados

```bash
# Conectar ao banco
gcloud sql connect NOME_DA_INSTANCIA --user=postgres --database=gestaopev

# Dentro do psql
SELECT role, COUNT(*) as total FROM users GROUP BY role ORDER BY role;

# Deve mostrar:
#  role         | total
# --------------+-------
#  admin        |     2
#  client       |     5
#  collaborator |    15
# (Sem 'consultant')

# Sair
\q
```

---

## 🚀 OPÇÃO 2: Deploy via Cloud SQL Proxy (Local)

### Passo 1: Instalar Cloud SQL Proxy

**Windows:**
```powershell
# Baixar
curl -o cloud-sql-proxy.exe https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.x64.exe

# Verificar
.\cloud-sql-proxy.exe --version
```

**macOS/Linux:**
```bash
# Baixar
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64
chmod +x cloud-sql-proxy

# Verificar
./cloud-sql-proxy --version
```

### Passo 2: Autenticar

```bash
# Fazer login no gcloud
gcloud auth login

# Configurar projeto
gcloud config set project SEU_PROJECT_ID

# Obter credenciais de aplicação
gcloud auth application-default login
```

### Passo 3: Iniciar Cloud SQL Proxy

```powershell
# PowerShell (Windows)
$env:CLOUD_SQL_CONNECTION_NAME = "PROJECT_ID:REGION:INSTANCE_NAME"

# Iniciar proxy
.\cloud-sql-proxy.exe $env:CLOUD_SQL_CONNECTION_NAME
```

**OU em terminal separado:**
```bash
cloud-sql-proxy PROJECT_ID:REGION:INSTANCE_NAME
```

### Passo 4: Configurar Ambiente Local

```powershell
# PowerShell
$env:DATABASE_URL = "postgresql://USER:PASS@127.0.0.1:5432/gestaopev"
$env:FLASK_APP = "app_pev.py"
```

### Passo 5: Aplicar Migração

```powershell
# Verificar versão atual
flask db current

# Aplicar
flask db upgrade

# Verificar
python check_migration_status.py
```

---

## 🔄 Passo Final: Reiniciar Aplicação

### Se usar Cloud Run:

```bash
# Fazer deploy da nova versão
gcloud run deploy gestaoversus \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated
```

### Se usar App Engine:

```bash
gcloud app deploy
```

### Se usar Compute Engine / VM:

```bash
# SSH na VM
gcloud compute ssh NOME_DA_VM --zone=ZONA

# Na VM
cd /path/to/app
git pull
source venv/bin/activate
pip install -r requirements.txt

# Aplicar migração
export FLASK_APP=app_pev.py
flask db upgrade

# Reiniciar serviço
sudo systemctl restart gestaoversus
# OU
sudo supervisorctl restart gestaoversus
```

---

## ✅ Checklist Pós-Deploy

Execute estes testes em produção:

### 1. Verificar Migração
```bash
gcloud sql connect INSTANCE_NAME --user=postgres --database=gestaopev
```

```sql
-- Ver versão do Alembic
SELECT version_num FROM alembic_version;

-- Verificar roles
SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role;

-- Não deve haver 'consultant'
SELECT COUNT(*) FROM users WHERE role = 'consultant';
```

### 2. Testar Login

- [ ] Login com usuário Admin
- [ ] Login com usuário Client  
- [ ] Login com usuário Collaborator

### 3. Testar MyWork

- [ ] Admin: vê todas as empresas sem filtro
- [ ] Client: vê empresas vinculadas
- [ ] Collaborator: vê apenas suas atividades

### 4. Verificar Logs

```bash
# Cloud Run
gcloud run logs read SERVICE_NAME --limit=50

# App Engine
gcloud app logs tail

# Compute Engine
gcloud compute ssh VM_NAME --command "tail -f /var/log/gestaoversus/app.log"
```

### 5. Monitorar Erros

- [ ] Verificar Cloud Logging
- [ ] Verificar Error Reporting
- [ ] Verificar métricas de performance

---

## 🆘 Rollback (Emergência)

### Se algo der errado:

#### 1. Rollback da Migração

```bash
# Via Cloud Shell
export FLASK_APP=app_pev.py
export DATABASE_URL="..."

flask db downgrade -1
```

#### 2. Restaurar Backup

```bash
# Listar backups
gcloud sql backups list --instance=INSTANCE_NAME

# Restaurar backup específico
gcloud sql backups restore BACKUP_ID \
  --backup-instance=INSTANCE_NAME \
  --backup-instance=INSTANCE_NAME
```

#### 3. Reverter Deploy

```bash
# Cloud Run - reverter para revisão anterior
gcloud run services update-traffic SERVICE_NAME \
  --to-revisions=REVISION_ANTERIOR=100

# App Engine - reverter versão
gcloud app services set-traffic default \
  --splits=VERSAO_ANTERIOR=1
```

---

## 📊 Comandos Úteis

### Verificar Logs em Tempo Real

```bash
# Cloud Run
gcloud run logs tail SERVICE_NAME

# App Engine
gcloud app logs tail -s default

# Cloud SQL
gcloud sql operations list --instance=INSTANCE_NAME
```

### Conectar ao Banco Diretamente

```bash
# Via gcloud
gcloud sql connect INSTANCE_NAME --user=postgres --database=gestaopev

# Via Cloud SQL Proxy local
psql "host=127.0.0.1 port=5432 dbname=gestaopev user=postgres"
```

### Verificar Status dos Serviços

```bash
# Cloud Run
gcloud run services list

# App Engine
gcloud app versions list

# Cloud SQL
gcloud sql instances describe INSTANCE_NAME
```

---

## 🔐 Segurança

### Verificações Importantes:

- [ ] Backup realizado com sucesso
- [ ] Credenciais não expostas nos logs
- [ ] Conexões usando SSL/TLS
- [ ] IP whitelisting configurado (se aplicável)
- [ ] Logs sensíveis mascarados

### Boas Práticas:

1. **Nunca expor senhas** em comandos ou scripts
2. **Usar Service Accounts** com permissões mínimas
3. **Habilitar Cloud SQL Auth Proxy** para conexões seguras
4. **Ativar logging de auditoria** no Cloud SQL
5. **Configurar alertas** para falhas

---

## 📞 Suporte

### Em caso de problemas:

1. **Verificar logs:**
   ```bash
   gcloud logging read "resource.type=cloud_run_revision" --limit=50
   ```

2. **Conectar ao banco e verificar:**
   ```sql
   SELECT * FROM alembic_version;
   SELECT role, COUNT(*) FROM users GROUP BY role;
   ```

3. **Fazer rollback se necessário:**
   ```bash
   flask db downgrade -1
   ```

4. **Restaurar backup:**
   ```bash
   gcloud sql backups restore BACKUP_ID --backup-instance=INSTANCE_NAME
   ```

---

## 📚 Referências

- [Cloud SQL Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy)
- [Cloud Shell](https://cloud.google.com/shell/docs)
- [Flask-Migrate](https://flask-migrate.readthedocs.io/)
- [Alembic](https://alembic.sqlalchemy.org/)
- [Guia Local](migrations/README_ROLE_MIGRATION.md)

---

## ⏱️ Tempo Estimado

| Etapa | Tempo |
|-------|-------|
| Backup | 5-10 min |
| Setup Cloud Shell | 2-3 min |
| Aplicar Migração | 1-2 min |
| Validação | 3-5 min |
| Reiniciar App | 2-5 min |
| **TOTAL** | **15-25 min** |

---

**Última atualização:** 03/12/2025  
**Testado em:** Google Cloud SQL (PostgreSQL 13+)  
**Autor:** Cursor AI



