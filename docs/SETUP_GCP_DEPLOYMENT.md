# Configuração do Deploy Automático no Google Cloud Platform

Este documento explica como configurar o deploy automático para o Google Cloud Run através do GitHub Actions.

## 📋 Pré-requisitos

1. Conta no Google Cloud Platform (GCP)
2. Projeto criado no GCP
3. APIs habilitadas no projeto
4. Service Account criado com permissões adequadas

## 🔐 Secrets Necessários no GitHub

Configure os seguintes secrets no GitHub Actions:

### 1. GCP_PROJECT_ID
- **Descrição**: ID do seu projeto no Google Cloud Platform
- **Exemplo**: `meu-projeto-gcp-123456`
- **Como obter**: 
  - Console GCP → Seletor de Projeto (topo da página)
  - Ou via CLI: `gcloud config get-value project`

### 2. GCP_SA_KEY
- **Descrição**: Chave JSON da Service Account do GCP
- **Formato**: JSON completo da service account
- **Como criar**: Veja seção "Criar Service Account" abaixo

### 3. GCP_ARTIFACT_REGISTRY (Opcional)
- **Descrição**: Nome do repositório no Artifact Registry
- **Padrão**: Se não configurado, será usado `{PROJECT_ID}-docker.pkg.dev`
- **Exemplo**: `my-app-repo`

## 🛠️ Configuração no Google Cloud Platform

### Passo 1: Habilitar APIs Necessárias

Execute no Cloud Shell ou localmente (com `gcloud` instalado):

```bash
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    vpcaccess.googleapis.com
```

### Passo 2: Criar Artifact Registry Repository

```bash
# Definir variáveis
PROJECT_ID="seu-projeto-id"
REGION="us-central1"
REPO_NAME="my-app-repo"

# Criar repositório
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Docker repository for GestaoVersus"
```

### Passo 3: Criar Service Account

```bash
# Definir variáveis
PROJECT_ID="seu-projeto-id"
SA_NAME="github-actions-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Criar service account
gcloud iam service-accounts create $SA_NAME \
    --display-name="GitHub Actions Service Account" \
    --description="Service account for GitHub Actions deployments"

# Conceder permissões necessárias
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin"

# Criar e baixar chave JSON
gcloud iam service-accounts keys create ~/github-actions-key.json \
    --iam-account=$SA_EMAIL

# Exibir a chave (copie o conteúdo completo)
cat ~/github-actions-key.json
```

### Passo 4: Configurar Secrets no GitHub

1. Acesse seu repositório no GitHub
2. Vá em **Settings** → **Secrets and variables** → **Actions**
3. Clique em **New repository secret**
4. Adicione cada secret:

#### GCP_PROJECT_ID
- **Name**: `GCP_PROJECT_ID`
- **Value**: Seu Project ID do GCP (ex: `meu-projeto-123456`)

#### GCP_SA_KEY
- **Name**: `GCP_SA_KEY`
- **Value**: Conteúdo completo do arquivo JSON da service account (copie todo o conteúdo do arquivo `github-actions-key.json`)

#### GCP_ARTIFACT_REGISTRY (Opcional)
- **Name**: `GCP_ARTIFACT_REGISTRY`
- **Value**: Nome do repositório no Artifact Registry (ex: `my-app-repo`)

## 🚀 Como Funciona

O workflow `.github/workflows/deploy-gcp.yml` executa automaticamente em **todos os commits** e:

1. ✅ Faz checkout do código
2. 🔐 Autentica no Google Cloud usando a Service Account
3. 🏗️ Faz build da imagem Docker
4. 📤 Faz push da imagem para o Artifact Registry
5. 🚀 Faz deploy no Cloud Run
6. 🔄 Executa migrations (se configurado)
7. ✅ Faz health check do serviço

## 📝 Configurações Avançadas

### Variáveis de Ambiente no Cloud Run

Para adicionar variáveis de ambiente, edite o workflow e adicione no comando `gcloud run deploy`:

```yaml
--set-env-vars FLASK_ENV=production,PORT=5002,OUTRA_VAR=valor
```

### Usar Secret Manager

Para usar secrets do Secret Manager, adicione ao comando de deploy:

```yaml
--set-secrets SECRET_KEY=SECRET_KEY:latest,DATABASE_URL=DATABASE_URL:latest
```

### Configurar Cloud SQL

Se usar Cloud SQL, adicione:

```yaml
--add-cloudsql-instances PROJECT_ID:REGION:INSTANCE_NAME \
--set-env-vars CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
```

### Configurar VPC Connector

Se usar VPC Connector:

```yaml
--vpc-connector CONNECTOR_NAME \
--vpc-egress private-ranges-only
```

## 🔍 Verificação

Após configurar os secrets e fazer um push:

1. Vá em **Actions** no GitHub
2. Verifique se o workflow `🚀 Deploy to Google Cloud Run` está executando
3. Aguarde a conclusão
4. Verifique o URL do serviço no Cloud Run Console

## 🚨 Troubleshooting

### Erro: "Permission denied"

- Verifique se a Service Account tem as permissões corretas
- Verifique se o `GCP_SA_KEY` está correto (JSON completo)

### Erro: "Repository not found" no Artifact Registry

- Verifique se o repositório foi criado no Artifact Registry
- Verifique se o nome do repositório está correto no secret `GCP_ARTIFACT_REGISTRY`

### Erro: "Service not found" no Cloud Run

- O serviço será criado automaticamente no primeiro deploy
- Verifique se o nome do serviço está correto no workflow

### Health Check falhando

- Verifique se a rota `/health` existe na aplicação
- Verifique os logs do Cloud Run: `gcloud run services logs read SERVICE_NAME --region REGION`

## 📚 Referências

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [GitHub Actions for GCP](https://github.com/google-github-actions)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)

## ✅ Checklist de Configuração

- [ ] APIs habilitadas no GCP
- [ ] Artifact Registry repository criado
- [ ] Service Account criada com permissões
- [ ] Chave JSON da Service Account baixada
- [ ] Secret `GCP_PROJECT_ID` configurado no GitHub
- [ ] Secret `GCP_SA_KEY` configurado no GitHub
- [ ] Secret `GCP_ARTIFACT_REGISTRY` configurado (opcional)
- [ ] Workflow testado com um push

---

**Nota**: Este workflow é configurado para executar em **todas as branches** e é **obrigatório**. Se precisar restringir a execução apenas para a branch `main`, edite o workflow e altere:

```yaml
on:
  push:
    branches: ['main']  # Apenas branch main
```

