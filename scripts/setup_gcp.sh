#!/bin/bash
# Script de Setup Google Cloud Platform
# GestaoVersus (APP30)

set -e

echo "🚀 Configurando Google Cloud Platform para GestaoVersus..."

# Variáveis
PROJECT_ID="your-gcp-project-id"
REGION="southamerica-east1"
SERVICE_NAME="gestaoversos-app"
DB_INSTANCE="gestaoversos-db"
DB_NAME="gestaoversos_prod"
DB_USER="gestaoversos_user"

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ===== 1. CONFIGURAR PROJETO =====
echo -e "\n${BLUE}1. Configurando projeto...${NC}"
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# ===== 2. HABILITAR APIs =====
echo -e "\n${BLUE}2. Habilitando APIs necessárias...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    vpcaccess.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    storage-api.googleapis.com

# ===== 3. CRIAR CLOUD SQL (PostgreSQL) =====
echo -e "\n${BLUE}3. Criando Cloud SQL PostgreSQL...${NC}"
gcloud sql instances create $DB_INSTANCE \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --enable-bin-log \
    || echo "Instância já existe"

# Criar banco de dados
gcloud sql databases create $DB_NAME \
    --instance=$DB_INSTANCE \
    || echo "Banco já existe"

# Criar usuário
echo -e "Digite a senha para o usuário do banco:"
read -s DB_PASSWORD
gcloud sql users create $DB_USER \
    --instance=$DB_INSTANCE \
    --password=$DB_PASSWORD \
    || echo "Usuário já existe"

# ===== 4. CRIAR VPC CONNECTOR =====
echo -e "\n${BLUE}4. Criando VPC Connector...${NC}"
gcloud compute networks vpc-access connectors create gestaoversos-connector \
    --region=$REGION \
    --range=10.8.0.0/28 \
    || echo "VPC Connector já existe"

# ===== 5. CRIAR BUCKETS =====
echo -e "\n${BLUE}5. Criando Cloud Storage Buckets...${NC}"

# Bucket para uploads
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-uploads || true
gsutil uniformbucketlevelaccess set on gs://${PROJECT_ID}-uploads

# Bucket para backups
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-backups || true
gsutil uniformbucketlevelaccess set on gs://${PROJECT_ID}-backups

# ===== 6. CRIAR SERVICE ACCOUNT =====
echo -e "\n${BLUE}6. Criando Service Account...${NC}"
gcloud iam service-accounts create gestaoversos-sa \
    --display-name="GestaoVersus Service Account" \
    || echo "Service Account já existe"

# Dar permissões
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:gestaoversos-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:gestaoversos-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# ===== 7. CRIAR SECRETS =====
echo -e "\n${BLUE}7. Criando secrets no Secret Manager...${NC}"

# SECRET_KEY
echo -e "Gerando SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
echo -n "$SECRET_KEY" | gcloud secrets create SECRET_KEY --data-file=- || true

# DATABASE_URL
echo -e "Criando DATABASE_URL..."
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@//${DB_NAME}?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL --data-file=- || true

# OPENAI_API_KEY (você precisa fornecer)
echo -e "Digite sua OPENAI_API_KEY:"
read -s OPENAI_KEY
echo -n "$OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=- || true

# ===== 8. BUILD E DEPLOY INICIAL =====
echo -e "\n${BLUE}8. Build e deploy inicial...${NC}"

# Build com Cloud Build
gcloud builds submit --config cloudbuild.yaml .

echo -e "\n${GREEN}✅ Setup do Google Cloud Platform concluído!${NC}"
echo -e "\nPróximos passos:"
echo -e "1. Configure os DNS para apontar para o Cloud Run"
echo -e "2. Configure o certificado SSL"
echo -e "3. Acesse: https://console.cloud.google.com/run"
echo -e "4. URL do serviço: https://${SERVICE_NAME}-xxxxx-uc.a.run.app"


