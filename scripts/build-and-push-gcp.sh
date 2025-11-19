#!/bin/bash

# ============================================
# GestaoVersus - Build e Push para GCP
# ============================================
# Script para construir e enviar imagens Docker
# para o Artifact Registry do Google Cloud
# ============================================

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================"
echo "🚀 GestaoVersus - Build e Push GCP"
echo "======================================"
echo ""

# ==========================================
# Configurações
# ==========================================
PROJECT_ID="vrs-eco-478714"
REGION="us-central1"
REPOSITORY="my-app-repo"
BACKEND_IMAGE="my-backend"
FRONTEND_IMAGE="my-frontend"
TAG="${1:-latest}"

# Nome completo das imagens no Artifact Registry
ARTIFACT_REGISTRY="${REGION}-docker.pkg.dev"
BACKEND_FULL_NAME="${ARTIFACT_REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${BACKEND_IMAGE}:${TAG}"
FRONTEND_FULL_NAME="${ARTIFACT_REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${FRONTEND_IMAGE}:${TAG}"

echo -e "${BLUE}📋 Configuração:${NC}"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  REGION: $REGION"
echo "  REPOSITORY: $REPOSITORY"
echo "  TAG: $TAG"
echo ""
echo -e "${BLUE}📦 Imagens:${NC}"
echo "  Backend:  $BACKEND_FULL_NAME"
echo "  Frontend: $FRONTEND_FULL_NAME"
echo ""

# ==========================================
# Verificar gcloud CLI
# ==========================================
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI não encontrado${NC}"
    echo "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

echo -e "${GREEN}✅ gcloud CLI encontrado${NC}"

# ==========================================
# Configurar projeto
# ==========================================
echo ""
echo -e "${BLUE}🔧 Configurando projeto GCP...${NC}"
gcloud config set project $PROJECT_ID

# ==========================================
# Habilitar APIs necessárias
# ==========================================
echo ""
echo -e "${BLUE}🔧 Habilitando APIs...${NC}"
gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    --quiet

echo -e "${GREEN}✅ APIs habilitadas${NC}"

# ==========================================
# Criar Artifact Registry (se não existir)
# ==========================================
echo ""
echo -e "${BLUE}🔧 Verificando Artifact Registry...${NC}"

if ! gcloud artifacts repositories describe $REPOSITORY \
    --location=$REGION \
    --format="value(name)" &> /dev/null; then
    echo "Criando repositório Artifact Registry..."
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --description="GestaoVersus Docker Images"
    echo -e "${GREEN}✅ Repositório criado${NC}"
else
    echo -e "${GREEN}✅ Repositório já existe${NC}"
fi

# ==========================================
# Configurar autenticação Docker
# ==========================================
echo ""
echo -e "${BLUE}🔧 Configurando autenticação Docker...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
echo -e "${GREEN}✅ Autenticação configurada${NC}"

# ==========================================
# Build Backend (Flask App)
# ==========================================
echo ""
echo -e "${BLUE}🔨 Construindo imagem Backend...${NC}"
docker build \
    -t $BACKEND_FULL_NAME \
    -f Dockerfile \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend build concluído${NC}"
else
    echo -e "${RED}❌ Erro ao construir Backend${NC}"
    exit 1
fi

# ==========================================
# Build Frontend (Nginx)
# ==========================================
echo ""
echo -e "${BLUE}🔨 Construindo imagem Frontend...${NC}"
# Build do frontend usando o diretório raiz como contexto
# para ter acesso aos arquivos static e nginx
docker build \
    -t $FRONTEND_FULL_NAME \
    -f nginx/Dockerfile \
    --build-arg STATIC_DIR=static \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend build concluído${NC}"
else
    echo -e "${RED}❌ Erro ao construir Frontend${NC}"
    exit 1
fi

# ==========================================
# Push Backend
# ==========================================
echo ""
echo -e "${BLUE}📤 Enviando Backend para Artifact Registry...${NC}"
docker push $BACKEND_FULL_NAME

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend enviado com sucesso${NC}"
else
    echo -e "${RED}❌ Erro ao enviar Backend${NC}"
    exit 1
fi

# ==========================================
# Push Frontend
# ==========================================
echo ""
echo -e "${BLUE}📤 Enviando Frontend para Artifact Registry...${NC}"
docker push $FRONTEND_FULL_NAME

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Frontend enviado com sucesso${NC}"
else
    echo -e "${RED}❌ Erro ao enviar Frontend${NC}"
    exit 1
fi

# ==========================================
# Resumo Final
# ==========================================
echo ""
echo "======================================"
echo -e "${GREEN}✅ Build e Push Concluídos!${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📦 Imagens disponíveis no Artifact Registry:${NC}"
echo ""
echo -e "${GREEN}Backend:${NC}"
echo "  $BACKEND_FULL_NAME"
echo ""
echo -e "${GREEN}Frontend:${NC}"
echo "  $FRONTEND_FULL_NAME"
echo ""
echo "======================================"
echo "Use estes nomes completos no seu design do GCP!"
echo "======================================"

