#!/bin/bash

# ============================================
# GestaoVersus - Setup Google Cloud Platform
# ============================================
# Script para configurar projeto no GCP
# ============================================

set -e  # Exit on error

echo "======================================"
echo "🚀 GestaoVersus - Setup Google Cloud"
echo "======================================"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar se gcloud está instalado
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI não encontrado${NC}"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI encontrado${NC}"

# Solicitar PROJECT_ID
read -p "Digite o PROJECT_ID do Google Cloud: " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ PROJECT_ID não pode ser vazio${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo "📋 Configuração"
echo "======================================"
echo "PROJECT_ID: $PROJECT_ID"
echo "REGION: us-central1"
echo "======================================"
echo ""

read -p "Confirma? (s/n): " CONFIRM

if [ "$CONFIRM" != "s" ]; then
    echo "❌ Cancelado"
    exit 0
fi

# Definir projeto
echo ""
echo "🔧 Configurando projeto..."
gcloud config set project $PROJECT_ID

# Habilitar APIs necessárias
echo ""
echo "🔧 Habilitando APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    sqladmin.googleapis.com \
    vpcaccess.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com

echo -e "${GREEN}✅ APIs habilitadas${NC}"

# Criar Cloud SQL Instance (PostgreSQL)
echo ""
echo "💾 Deseja criar instância Cloud SQL? (s/n)"
read -p "> " CREATE_SQL

if [ "$CREATE_SQL" = "s" ]; then
    echo "Criando Cloud SQL (PostgreSQL 15)..."
    gcloud sql instances create gestaoversos-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=us-central1 \
        --root-password=CHANGE_THIS_PASSWORD \
        --backup-start-time=03:00
    
    echo "Criando database..."
    gcloud sql databases create bd_app_versus \
        --instance=gestaoversos-db
    
    echo -e "${GREEN}✅ Cloud SQL criado${NC}"
fi

# Criar VPC Connector
echo ""
echo "🌐 Deseja criar VPC Connector? (s/n)"
read -p "> " CREATE_VPC

if [ "$CREATE_VPC" = "s" ]; then
    echo "Criando VPC Connector..."
    gcloud compute networks vpc-access connectors create gestaoversos-connector \
        --region=us-central1 \
        --range=10.8.0.0/28
    
    echo -e "${GREEN}✅ VPC Connector criado${NC}"
fi

# Criar secrets no Secret Manager
echo ""
echo "🔐 Configurando secrets..."

# SECRET_KEY
echo "Digite SECRET_KEY (ou Enter para gerar):"
read SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -hex 32)
fi
echo -n "$SECRET_KEY" | gcloud secrets create flask-secret-key --data-file=-

# DATABASE_URL
echo "Digite DATABASE_URL:"
read DATABASE_URL
echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=-

# REDIS_URL (opcional)
echo "Digite REDIS_URL (ou Enter para pular):"
read REDIS_URL
if [ ! -z "$REDIS_URL" ]; then
    echo -n "$REDIS_URL" | gcloud secrets create redis-url --data-file=-
fi

echo -e "${GREEN}✅ Secrets configurados${NC}"

# Build inicial
echo ""
echo "🏗️ Deseja fazer build inicial? (s/n)"
read -p "> " DO_BUILD

if [ "$DO_BUILD" = "s" ]; then
    echo "Building Docker image..."
    gcloud builds submit --tag gcr.io/$PROJECT_ID/gestaoversos:latest
    
    echo -e "${GREEN}✅ Build concluído${NC}"
fi

# Deploy inicial
echo ""
echo "🚀 Deseja fazer deploy inicial? (s/n)"
read -p "> " DO_DEPLOY

if [ "$DO_DEPLOY" = "s" ]; then
    echo "Deploying to Cloud Run..."
    gcloud run deploy gestaoversos \
        --image gcr.io/$PROJECT_ID/gestaoversos:latest \
        --platform managed \
        --region us-central1 \
        --allow-unauthenticated \
        --set-secrets="SECRET_KEY=flask-secret-key:latest,DATABASE_URL=database-url:latest" \
        --max-instances=10 \
        --memory=512Mi \
        --cpu=2 \
        --timeout=300
    
    echo -e "${GREEN}✅ Deploy concluído${NC}"
    
    # Obter URL
    SERVICE_URL=$(gcloud run services describe gestaoversos --region us-central1 --format 'value(status.url)')
    echo ""
    echo "======================================"
    echo -e "${GREEN}✅ Aplicação disponível em:${NC}"
    echo -e "${GREEN}$SERVICE_URL${NC}"
    echo "======================================"
fi

# Configurar domínio customizado
echo ""
echo "🌐 Deseja configurar domínio customizado? (s/n)"
read -p "> " CONFIG_DOMAIN

if [ "$CONFIG_DOMAIN" = "s" ]; then
    read -p "Digite o domínio (ex: your-domain.com): " DOMAIN
    
    echo "Mapeando domínio..."
    gcloud run domain-mappings create \
        --service gestaoversos \
        --domain $DOMAIN \
        --region us-central1
    
    echo ""
    echo "======================================"
    echo "⚠️ IMPORTANTE: Configure os seguintes DNS records:"
    echo ""
    gcloud run domain-mappings describe \
        --domain $DOMAIN \
        --region us-central1 \
        --format="table(resourceRecords:format='Type: {type}, Name: {name}, Data: {rrdata}')"
    echo "======================================"
fi

echo ""
echo "======================================"
echo -e "${GREEN}✅ Setup concluído!${NC}"
echo "======================================"
echo ""
echo "📋 Próximos passos:"
echo "1. Configure GitHub Actions secrets"
echo "2. Configure CI/CD trigger"
echo "3. Configure backup automático"
echo "4. Configure monitoramento"
echo ""
echo "======================================"

