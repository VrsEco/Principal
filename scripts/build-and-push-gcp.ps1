# ============================================
# GestaoVersus - Build e Push para GCP (PowerShell)
# ============================================
# Script para construir e enviar imagens Docker
# para o Artifact Registry do Google Cloud
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "GestaoVersus - Build e Push GCP" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ==========================================
# Configuracoes
# ==========================================
$PROJECT_ID = "vrs-eco-478714"
$REGION = "us-central1"
$REPOSITORY = "my-app-repo"
$BACKEND_IMAGE = "my-backend"
$FRONTEND_IMAGE = "my-frontend"
$TAG = if ($args[0]) { $args[0] } else { "latest" }

# Nome completo das imagens no Artifact Registry
$ARTIFACT_REGISTRY = "$REGION-docker.pkg.dev"
$BACKEND_FULL_NAME = "$ARTIFACT_REGISTRY/$PROJECT_ID/$REPOSITORY/${BACKEND_IMAGE}:$TAG"
$FRONTEND_FULL_NAME = "$ARTIFACT_REGISTRY/$PROJECT_ID/$REPOSITORY/${FRONTEND_IMAGE}:$TAG"

Write-Host "Configuracao:" -ForegroundColor Blue
Write-Host "  PROJECT_ID: $PROJECT_ID"
Write-Host "  REGION: $REGION"
Write-Host "  REPOSITORY: $REPOSITORY"
Write-Host "  TAG: $TAG"
Write-Host ""
Write-Host "Imagens:" -ForegroundColor Blue
Write-Host "  Backend:  $BACKEND_FULL_NAME"
Write-Host "  Frontend: $FRONTEND_FULL_NAME"
Write-Host ""

# ==========================================
# Verificar gcloud CLI
# ==========================================
try {
    $null = Get-Command gcloud -ErrorAction Stop
    Write-Host "[OK] gcloud CLI encontrado" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] gcloud CLI nao encontrado" -ForegroundColor Red
    Write-Host "Instale em: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# ==========================================
# Configurar projeto
# ==========================================
Write-Host ""
Write-Host "Configurando projeto GCP..." -ForegroundColor Blue
gcloud config set project $PROJECT_ID

# ==========================================
# Habilitar APIs necessarias
# ==========================================
Write-Host ""
Write-Host "Habilitando APIs..." -ForegroundColor Blue
gcloud services enable `
    artifactregistry.googleapis.com `
    cloudbuild.googleapis.com `
    run.googleapis.com `
    --quiet

Write-Host "[OK] APIs habilitadas" -ForegroundColor Green

# ==========================================
# Criar Artifact Registry (se nao existir)
# ==========================================
Write-Host ""
Write-Host "Verificando Artifact Registry..." -ForegroundColor Blue

try {
    $null = gcloud artifacts repositories describe $REPOSITORY `
        --location=$REGION `
        --format="value(name)" 2>$null
    Write-Host "[OK] Repositorio ja existe" -ForegroundColor Green
} catch {
    Write-Host "Criando repositorio Artifact Registry..."
    gcloud artifacts repositories create $REPOSITORY `
        --repository-format=docker `
        --location=$REGION `
        --description="GestaoVersus Docker Images"
    Write-Host "[OK] Repositorio criado" -ForegroundColor Green
}

# ==========================================
# Configurar autenticacao Docker
# ==========================================
Write-Host ""
Write-Host "Configurando autenticacao Docker..." -ForegroundColor Blue
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
Write-Host "[OK] Autenticacao configurada" -ForegroundColor Green

# ==========================================
# Build Backend (Flask App)
# ==========================================
Write-Host ""
Write-Host "Construindo imagem Backend..." -ForegroundColor Blue
docker build `
    -t $BACKEND_FULL_NAME `
    -f Dockerfile `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Backend build concluido" -ForegroundColor Green
} else {
    Write-Host "[ERRO] Erro ao construir Backend" -ForegroundColor Red
    exit 1
}

# ==========================================
# Build Frontend (Nginx)
# ==========================================
Write-Host ""
Write-Host "Construindo imagem Frontend..." -ForegroundColor Blue
# Build do frontend usando o diretorio raiz como contexto
# para ter acesso aos arquivos static e nginx
docker build `
    -t $FRONTEND_FULL_NAME `
    -f nginx/Dockerfile `
    --build-arg STATIC_DIR=static `
    .

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Frontend build concluido" -ForegroundColor Green
} else {
    Write-Host "[ERRO] Erro ao construir Frontend" -ForegroundColor Red
    exit 1
}

# ==========================================
# Push Backend
# ==========================================
Write-Host ""
Write-Host "Enviando Backend para Artifact Registry..." -ForegroundColor Blue
docker push $BACKEND_FULL_NAME

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Backend enviado com sucesso" -ForegroundColor Green
} else {
    Write-Host "[ERRO] Erro ao enviar Backend" -ForegroundColor Red
    exit 1
}

# ==========================================
# Push Frontend
# ==========================================
Write-Host ""
Write-Host "Enviando Frontend para Artifact Registry..." -ForegroundColor Blue
docker push $FRONTEND_FULL_NAME

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Frontend enviado com sucesso" -ForegroundColor Green
} else {
    Write-Host "[ERRO] Erro ao enviar Frontend" -ForegroundColor Red
    exit 1
}

# ==========================================
# Resumo Final
# ==========================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "[OK] Build e Push Concluidos!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Imagens disponiveis no Artifact Registry:" -ForegroundColor Blue
Write-Host ""
Write-Host "Backend:" -ForegroundColor Green
Write-Host "  $BACKEND_FULL_NAME"
Write-Host ""
Write-Host "Frontend:" -ForegroundColor Green
Write-Host "  $FRONTEND_FULL_NAME"
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Use estes nomes completos no seu design do GCP" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
