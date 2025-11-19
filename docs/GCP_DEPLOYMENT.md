# Deploy no Google Cloud Platform

Este documento descreve como fazer build e push das imagens Docker para o Artifact Registry do GCP.

## 📋 Pré-requisitos

1. **Google Cloud SDK (gcloud CLI)** instalado
   - Download: https://cloud.google.com/sdk/docs/install
   - Autenticação: Execute `.\scripts\setup-gcp-auth.ps1` ou veja [GCP_AUTHENTICATION.md](GCP_AUTHENTICATION.md)

2. **Docker** instalado e rodando

3. **Acesso ao projeto GCP**: `vrs-eco-478714`

## 🔐 Autenticação (IMPORTANTE!)

**Antes de executar o script de build, você precisa autenticar no GCP:**

### Opção 1: Script Auxiliar (Recomendado)
```powershell
.\scripts\setup-gcp-auth.ps1
```

Este script guiará você através do processo de autenticação.

### Opção 2: Manual
```powershell
# Autenticação interativa (abre navegador)
gcloud auth login
gcloud auth application-default login

# Configurar projeto
gcloud config set project vrs-eco-478714

# Configurar Docker
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**📚 Para mais detalhes, consulte:** [GCP_AUTHENTICATION.md](GCP_AUTHENTICATION.md)

## 🚀 Build e Push das Imagens

### Opção 1: Script Bash (Linux/Mac/WSL)

```bash
chmod +x scripts/build-and-push-gcp.sh
./scripts/build-and-push-gcp.sh [tag]
```

### Opção 2: Script PowerShell (Windows)

```powershell
.\scripts\build-and-push-gcp.ps1 [tag]
```

**Parâmetros:**
- `tag`: Tag da imagem (padrão: `latest`)

**Exemplo:**
```bash
./scripts/build-and-push-gcp.sh v1.0.0
```

## 📦 Imagens Geradas

Após executar o script, as seguintes imagens estarão disponíveis no Artifact Registry:

### Backend (Flask Application)
```
us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo/my-backend:latest
```

### Frontend (Nginx)
```
us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo/my-frontend:latest
```

## 🔧 O que o Script Faz

1. **Verifica dependências**: gcloud CLI e Docker
2. **Configura projeto GCP**: Define `vrs-eco-478714` como projeto ativo
3. **Habilita APIs necessárias**:
   - Artifact Registry API
   - Cloud Build API
   - Cloud Run API
4. **Cria repositório Artifact Registry** (se não existir):
   - Nome: `my-app-repo`
   - Região: `us-central1`
   - Formato: Docker
5. **Configura autenticação Docker** para Artifact Registry
6. **Build das imagens**:
   - Backend: Aplicação Flask completa
   - Frontend: Nginx com arquivos estáticos
7. **Push das imagens** para o Artifact Registry

## 📝 Estrutura das Imagens

### Backend (`my-backend`)
- **Base**: `python:3.9-slim`
- **Conteúdo**: Aplicação Flask completa
- **Porta**: 5002
- **Comando**: Gunicorn com 4 workers

### Frontend (`my-frontend`)
- **Base**: `nginx:1.27-alpine`
- **Conteúdo**: 
  - Configuração Nginx
  - Arquivos estáticos (`/app/static`)
  - Reverse proxy para backend Flask
- **Portas**: 80 (HTTP), 443 (HTTPS)

## 🔍 Verificar Imagens

Para listar as imagens no Artifact Registry:

```bash
gcloud artifacts docker images list \
    us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo \
    --include-tags
```

## 🎯 Usar no Cloud Run

Use os nomes completos das imagens no seu design do Cloud Run:

```yaml
# Exemplo de configuração Cloud Run
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: gestaoversus-backend
spec:
  template:
    spec:
      containers:
      - image: us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo/my-backend:latest
        ports:
        - containerPort: 5002
```

## 🔐 Autenticação

O script configura automaticamente a autenticação Docker. Se precisar fazer manualmente:

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## 🐛 Troubleshooting

### Erro: "Permission denied"
```bash
# Verificar autenticação
gcloud auth list

# Reautenticar se necessário
gcloud auth login
gcloud auth application-default login
```

### Erro: "Repository not found"
```bash
# Criar repositório manualmente
gcloud artifacts repositories create my-app-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="GestaoVersus Docker Images"
```

### Erro: "Docker build failed"
- Verificar se Docker está rodando
- Verificar espaço em disco
- Verificar logs do build: `docker build --progress=plain ...`

## 📚 Referências

- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Docker Build Documentation](https://docs.docker.com/engine/reference/commandline/build/)

