# Autenticação no Google Cloud Platform

Este guia explica como autenticar no Google Cloud para fazer build e push das imagens Docker.

## 🔐 Métodos de Autenticação

### Método 1: Autenticação Interativa (Recomendado para desenvolvimento)

Este é o método mais simples e seguro para uso local:

```powershell
# 1. Fazer login interativo
gcloud auth login

# Isso abrirá seu navegador para fazer login com sua conta Google
# Após o login, você estará autenticado

# 2. Configurar credenciais para aplicações
gcloud auth application-default login

# 3. Verificar autenticação
gcloud auth list
```

**Vantagens:**
- ✅ Seguro (OAuth 2.0)
- ✅ Não precisa compartilhar credenciais
- ✅ Fácil de usar
- ✅ Renovação automática de tokens

### Método 2: Service Account (Recomendado para CI/CD)

Para ambientes automatizados ou CI/CD:

```powershell
# 1. Criar Service Account (se ainda não tiver)
gcloud iam service-accounts create gestaoversus-sa `
    --display-name="GestaoVersus Service Account" `
    --description="Service Account para deploy automatizado"

# 2. Dar permissões necessárias
gcloud projects add-iam-policy-binding vrs-eco-478714 `
    --member="serviceAccount:gestaoversus-sa@vrs-eco-478714.iam.gserviceaccount.com" `
    --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding vrs-eco-478714 `
    --member="serviceAccount:gestaoversus-sa@vrs-eco-478714.iam.gserviceaccount.com" `
    --role="roles/storage.admin"

# 3. Criar e baixar chave JSON
gcloud iam service-accounts keys create gcp-key.json `
    --iam-account=gestaoversus-sa@vrs-eco-478714.iam.gserviceaccount.com

# 4. Autenticar usando a chave
gcloud auth activate-service-account --key-file=gcp-key.json

# 5. Configurar Docker para usar a chave
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\GestaoVersus\app31\gcp-key.json"
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**⚠️ IMPORTANTE:**
- NUNCA commite o arquivo `gcp-key.json` no Git
- Adicione `gcp-key.json` ao `.gitignore`
- Mantenha a chave segura

### Método 3: Usar Credenciais Existentes

Se você já tem credenciais configuradas:

```powershell
# Verificar credenciais ativas
gcloud auth list

# Se necessário, definir credenciais padrão
gcloud config set account SEU_EMAIL@exemplo.com
```

## 🔍 Verificar Autenticação

Antes de executar o script, verifique se está autenticado:

```powershell
# Listar contas autenticadas
gcloud auth list

# Verificar projeto atual
gcloud config get-value project

# Testar acesso ao Artifact Registry
gcloud artifacts repositories list --location=us-central1
```

## 🚀 Executar o Script

Após autenticar, você pode executar o script normalmente:

```powershell
.\scripts\build-and-push-gcp.ps1
```

O script irá:
1. Verificar se você está autenticado
2. Configurar o projeto
3. Fazer build e push das imagens

## 🐛 Troubleshooting

### Erro: "You do not currently have an active account selected"

```powershell
# Fazer login novamente
gcloud auth login

# Ou selecionar conta existente
gcloud auth list
gcloud config set account SEU_EMAIL@exemplo.com
```

### Erro: "Permission denied" ou "Access denied"

Verifique se sua conta tem as permissões necessárias:

```powershell
# Verificar permissões do projeto
gcloud projects get-iam-policy vrs-eco-478714

# Se necessário, peça ao administrador para adicionar:
# - roles/artifactregistry.writer
# - roles/storage.admin
# - roles/cloudbuild.builds.editor
```

### Erro: "Docker authentication failed"

```powershell
# Reconfigurar autenticação Docker
gcloud auth configure-docker us-central1-docker.pkg.dev

# Ou usar credenciais de aplicação
gcloud auth application-default login
```

### Erro: "Project not found" ou "Project access denied"

```powershell
# Verificar se o projeto está correto
gcloud config set project vrs-eco-478714

# Verificar acesso ao projeto
gcloud projects describe vrs-eco-478714
```

## 📋 Checklist de Autenticação

Antes de executar o script, verifique:

- [ ] `gcloud` CLI está instalado
- [ ] Você está autenticado (`gcloud auth list`)
- [ ] Projeto está configurado (`gcloud config get-value project`)
- [ ] Você tem permissões no projeto
- [ ] Docker está rodando
- [ ] Autenticação Docker está configurada

## 🔒 Segurança

**NUNCA faça:**
- ❌ Compartilhe suas credenciais (senhas, chaves JSON)
- ❌ Commite arquivos de credenciais no Git
- ❌ Envie credenciais por email ou chat

**SEMPRE faça:**
- ✅ Use autenticação interativa quando possível
- ✅ Use Service Accounts para autentomação
- ✅ Adicione arquivos de credenciais ao `.gitignore`
- ✅ Revogue credenciais comprometidas imediatamente
- ✅ Use o princípio do menor privilégio (permissões mínimas necessárias)

## 📚 Referências

- [gcloud auth login](https://cloud.google.com/sdk/gcloud/reference/auth/login)
- [Service Accounts](https://cloud.google.com/iam/docs/service-accounts)
- [Artifact Registry Authentication](https://cloud.google.com/artifact-registry/docs/docker/authentication)





