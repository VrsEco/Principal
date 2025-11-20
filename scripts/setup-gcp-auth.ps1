# ============================================
# GestaoVersus - Setup Autenticação GCP
# ============================================
# Script auxiliar para configurar autenticação
# no Google Cloud Platform
# ============================================

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "GestaoVersus - Setup Autenticacao GCP" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Verificar se gcloud está instalado
try {
    $null = Get-Command gcloud -ErrorAction Stop
    Write-Host "[OK] gcloud CLI encontrado" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] gcloud CLI nao encontrado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Instale o Google Cloud SDK em:" -ForegroundColor Yellow
    Write-Host "https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Escolha o metodo de autenticacao:" -ForegroundColor Blue
Write-Host "1. Autenticacao interativa (recomendado)" -ForegroundColor White
Write-Host "2. Service Account (para CI/CD)" -ForegroundColor White
Write-Host "3. Verificar autenticacao atual" -ForegroundColor White
Write-Host "4. Sair" -ForegroundColor White
Write-Host ""

$opcao = Read-Host "Digite o numero da opcao"

switch ($opcao) {
    "1" {
        Write-Host ""
        Write-Host "=== Autenticacao Interativa ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Isso abrira seu navegador para fazer login..." -ForegroundColor Yellow
        Write-Host ""
        
        # Login interativo
        gcloud auth login
        
        # Configurar credenciais de aplicação
        Write-Host ""
        Write-Host "Configurando credenciais de aplicacao..." -ForegroundColor Blue
        gcloud auth application-default login
        
        # Configurar projeto
        Write-Host ""
        $PROJECT_ID = Read-Host "Digite o PROJECT_ID (ou Enter para usar vrs-eco-478714)"
        if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
            $PROJECT_ID = "vrs-eco-478714"
        }
        gcloud config set project $PROJECT_ID
        
        # Configurar Docker
        Write-Host ""
        Write-Host "Configurando autenticacao Docker..." -ForegroundColor Blue
        gcloud auth configure-docker us-central1-docker.pkg.dev
        
        Write-Host ""
        Write-Host "[OK] Autenticacao configurada com sucesso!" -ForegroundColor Green
    }
    
    "2" {
        Write-Host ""
        Write-Host "=== Service Account ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Este metodo cria uma Service Account para autenticacao automatizada." -ForegroundColor Yellow
        Write-Host ""
        
        $PROJECT_ID = Read-Host "Digite o PROJECT_ID (ou Enter para usar vrs-eco-478714)"
        if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
            $PROJECT_ID = "vrs-eco-478714"
        }
        
        $SA_NAME = Read-Host "Digite o nome da Service Account (ou Enter para usar gestaoversus-sa)"
        if ([string]::IsNullOrWhiteSpace($SA_NAME)) {
            $SA_NAME = "gestaoversus-sa"
        }
        
        $SA_EMAIL = "${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
        
        Write-Host ""
        Write-Host "Criando Service Account..." -ForegroundColor Blue
        try {
            gcloud iam service-accounts create $SA_NAME `
                --display-name="GestaoVersus Service Account" `
                --description="Service Account para deploy automatizado" `
                2>$null
            Write-Host "[OK] Service Account criada" -ForegroundColor Green
        } catch {
            Write-Host "[INFO] Service Account ja existe" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "Configurando permissoes..." -ForegroundColor Blue
        
        # Artifact Registry Writer
        gcloud projects add-iam-policy-binding $PROJECT_ID `
            --member="serviceAccount:${SA_EMAIL}" `
            --role="roles/artifactregistry.writer" `
            --quiet
        
        # Storage Admin (para buckets)
        gcloud projects add-iam-policy-binding $PROJECT_ID `
            --member="serviceAccount:${SA_EMAIL}" `
            --role="roles/storage.admin" `
            --quiet
        
        # Cloud Build Editor
        gcloud projects add-iam-policy-binding $PROJECT_ID `
            --member="serviceAccount:${SA_EMAIL}" `
            --role="roles/cloudbuild.builds.editor" `
            --quiet
        
        Write-Host "[OK] Permissoes configuradas" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Criando chave JSON..." -ForegroundColor Blue
        $KEY_FILE = "gcp-key.json"
        
        if (Test-Path $KEY_FILE) {
            $sobrescrever = Read-Host "Arquivo $KEY_FILE ja existe. Sobrescrever? (s/n)"
            if ($sobrescrever -ne "s") {
                Write-Host "Operacao cancelada." -ForegroundColor Yellow
                exit 0
            }
        }
        
        gcloud iam service-accounts keys create $KEY_FILE `
            --iam-account=$SA_EMAIL
        
        Write-Host "[OK] Chave criada: $KEY_FILE" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Configurando variavel de ambiente..." -ForegroundColor Blue
        $KEY_PATH = (Resolve-Path $KEY_FILE).Path
        $env:GOOGLE_APPLICATION_CREDENTIALS = $KEY_PATH
        
        Write-Host "[OK] GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Autenticando com Service Account..." -ForegroundColor Blue
        gcloud auth activate-service-account --key-file=$KEY_FILE
        
        Write-Host ""
        Write-Host "Configurando autenticacao Docker..." -ForegroundColor Blue
        gcloud auth configure-docker us-central1-docker.pkg.dev
        
        Write-Host ""
        Write-Host "[OK] Service Account configurada com sucesso!" -ForegroundColor Green
        Write-Host ""
        Write-Host "IMPORTANTE:" -ForegroundColor Yellow
        Write-Host "- O arquivo $KEY_FILE esta no .gitignore" -ForegroundColor White
        Write-Host "- NUNCA commite este arquivo no Git" -ForegroundColor White
        Write-Host "- Mantenha este arquivo seguro" -ForegroundColor White
    }
    
    "3" {
        Write-Host ""
        Write-Host "=== Status da Autenticacao ===" -ForegroundColor Cyan
        Write-Host ""
        
        Write-Host "Contas autenticadas:" -ForegroundColor Blue
        gcloud auth list
        
        Write-Host ""
        Write-Host "Projeto atual:" -ForegroundColor Blue
        $project = gcloud config get-value project
        Write-Host "  $project" -ForegroundColor White
        
        Write-Host ""
        Write-Host "Testando acesso ao Artifact Registry..." -ForegroundColor Blue
        try {
            gcloud artifacts repositories list --location=us-central1 2>$null | Out-Null
            Write-Host "[OK] Acesso ao Artifact Registry OK" -ForegroundColor Green
        } catch {
            Write-Host "[ERRO] Nao foi possivel acessar o Artifact Registry" -ForegroundColor Red
            Write-Host "Verifique suas permissoes ou faca login novamente" -ForegroundColor Yellow
        }
    }
    
    "4" {
        Write-Host "Saindo..." -ForegroundColor Yellow
        exit 0
    }
    
    default {
        Write-Host "[ERRO] Opcao invalida" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Configuracao concluida!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Agora voce pode executar:" -ForegroundColor Blue
Write-Host "  .\scripts\build-and-push-gcp.ps1" -ForegroundColor White
Write-Host ""




