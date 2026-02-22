# Configuração do Deploy com Cloud Build Trigger

Este documento explica como funciona o deploy automático usando o **Cloud Build Trigger** do Google Cloud Platform, que já está configurado e linkado ao seu repositório Git.

## 🔄 Como Funciona

Quando você usa o **Cloud Build Trigger** do GCP:

1. ✅ **Push no Git** → GitHub/GitLab detecta o push
2. 🔔 **Cloud Build Trigger** → GCP detecta o push automaticamente
3. 🏗️ **Build** → Executa o `cloudbuild.yaml`
4. 📤 **Push Image** → Envia para Artifact Registry
5. 🚀 **Deploy** → Faz deploy no Cloud Run automaticamente

## 📋 Arquitetura

```
┌─────────────┐
│   GitHub    │
│  (Push)     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Cloud Build     │
│ Trigger (GCP)   │ ← Já configurado e linkado
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ cloudbuild.yaml │ ← Executa este arquivo
└──────┬──────────┘
       │
       ├──► 🧪 Tests
       ├──► 🏗️ Build Docker
       ├──► 📤 Push to Artifact Registry
       ├──► 🚀 Deploy to Cloud Run
       └──► ✅ Health Check
```

## ✅ O Que Já Está Configurado

### 1. Cloud Build Trigger
- ✅ Linkado ao repositório Git
- ✅ Configurado para executar em push
- ✅ Usa o arquivo `cloudbuild.yaml`

### 2. Arquivo cloudbuild.yaml
O arquivo `cloudbuild.yaml` já contém todos os passos:
- Execução de testes
- Build da imagem Docker
- Push para Artifact Registry
- Deploy no Cloud Run
- Health check

## 🔍 Verificar Configuração do Trigger

### Via Console GCP

1. Acesse [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Procure pelo trigger do seu repositório
3. Verifique:
   - **Nome do trigger**
   - **Repositório conectado**
   - **Branch pattern** (ex: `^main$`)
   - **Arquivo de configuração** (deve ser `cloudbuild.yaml`)

### Via CLI

```bash
# Listar triggers
gcloud builds triggers list

# Ver detalhes de um trigger específico
gcloud builds triggers describe TRIGGER_NAME --region=us-central1
```

## ⚙️ Ajustar Configurações

### Alterar Branch Pattern

Se quiser que o trigger execute apenas na branch `main`:

**Via Console:**
1. Cloud Build → Triggers
2. Edite o trigger
3. Em "Configuration", ajuste o "Branch pattern"

**Via CLI:**
```bash
gcloud builds triggers update TRIGGER_NAME \
  --branch-pattern="^main$" \
  --region=us-central1
```

### Alterar Arquivo de Configuração

Se quiser usar outro arquivo (ex: `cloudbuild-prod.yaml`):

**Via Console:**
1. Edite o trigger
2. Em "Configuration", altere o "Cloud Build configuration file"

**Via CLI:**
```bash
gcloud builds triggers update TRIGGER_NAME \
  --build-config=cloudbuild-prod.yaml \
  --region=us-central1
```

## 📝 Ajustar cloudbuild.yaml

O arquivo `cloudbuild.yaml` já está configurado, mas você pode ajustar:

### Alterar Nome do Serviço

Edite a linha 59 do `cloudbuild.yaml`:
```yaml
- 'gestaoversos'  # Altere para o nome do seu serviço
```

### Alterar Região

Edite as linhas que contêm `us-central1`:
```yaml
- '--region'
- 'us-central1'  # Altere para sua região
```

### Alterar Recursos (CPU, Memória)

Edite as linhas 71-74:
```yaml
- '--memory'
- '512Mi'  # Ajuste conforme necessário
- '--cpu'
- '2'  # Ajuste conforme necessário
```

### Adicionar Variáveis de Ambiente

Adicione mais variáveis na linha 67-68:
```yaml
- '--set-env-vars'
- 'FLASK_ENV=production,OUTRA_VAR=valor,MAIS_UMA=valor2'
```

### Configurar Cloud SQL

Se usar Cloud SQL, adicione após a linha 76:
```yaml
- '--add-cloudsql-instances'
- 'PROJECT_ID:REGION:INSTANCE_NAME'
```

## 🔄 Workflow do GitHub Actions

O workflow `.github/workflows/deploy-gcp.yml` foi ajustado para:

- ✅ **Validar código** antes do deploy
- ✅ **Executar testes básicos** (validação)
- ✅ **Monitorar status** do Cloud Build (opcional)
- ❌ **NÃO fazer deploy** (o Cloud Build faz isso)

Isso evita conflitos e duplicação de deploys.

## 🚀 Fluxo Completo

1. **Você faz push no Git**
   ```bash
   git add .
   git commit -m "Minha alteração"
   git push
   ```

2. **GitHub Actions executa** (validação)
   - ✅ Valida formatação do código
   - ✅ Executa linting
   - ✅ Executa testes básicos

3. **Cloud Build Trigger executa** (deploy)
   - 🧪 Executa todos os testes
   - 🏗️ Faz build da imagem Docker
   - 📤 Faz push para Artifact Registry
   - 🚀 Faz deploy no Cloud Run
   - ✅ Executa health check

4. **Deploy concluído!**
   - Verifique o status no [Cloud Build Console](https://console.cloud.google.com/cloud-build/builds)
   - Acesse o serviço no [Cloud Run Console](https://console.cloud.google.com/run)

## 🔍 Verificar Status do Deploy

### Via Console GCP

1. **Cloud Build:**
   - [Cloud Build History](https://console.cloud.google.com/cloud-build/builds)
   - Veja logs, status e duração de cada build

2. **Cloud Run:**
   - [Cloud Run Services](https://console.cloud.google.com/run)
   - Veja o serviço, URL, tráfego e logs

### Via CLI

```bash
# Ver últimos builds
gcloud builds list --limit=5 --region=us-central1

# Ver detalhes de um build específico
gcloud builds describe BUILD_ID --region=us-central1

# Ver logs de um build
gcloud builds log BUILD_ID --region=us-central1

# Ver status do serviço Cloud Run
gcloud run services describe gestaoversos --region=us-central1

# Ver logs do Cloud Run
gcloud run services logs read gestaoversos --region=us-central1 --limit=50
```

## 🚨 Troubleshooting

### Trigger não está executando

1. **Verifique a conexão do repositório:**
   ```bash
   gcloud builds triggers describe TRIGGER_NAME --region=us-central1
   ```

2. **Verifique o branch pattern:**
   - Deve corresponder à branch que você está fazendo push

3. **Verifique permissões:**
   - O Cloud Build precisa ter acesso ao repositório Git

### Build falhando

1. **Verifique os logs:**
   ```bash
   gcloud builds log BUILD_ID --region=us-central1
   ```

2. **Verifique o arquivo cloudbuild.yaml:**
   - Sintaxe YAML correta
   - Variáveis de substituição corretas
   - Permissões da service account

### Deploy falhando

1. **Verifique se o serviço existe:**
   ```bash
   gcloud run services list --region=us-central1
   ```

2. **Verifique permissões do Cloud Build:**
   - Precisa de `roles/run.admin`
   - Precisa de `roles/iam.serviceAccountUser`

3. **Verifique logs do Cloud Run:**
   ```bash
   gcloud run services logs read gestaoversos --region=us-central1
   ```

## 📚 Referências

- [Cloud Build Triggers Documentation](https://cloud.google.com/build/docs/triggers)
- [cloudbuild.yaml Reference](https://cloud.google.com/build/docs/build-config-file-schema)
- [Cloud Run Deployment](https://cloud.google.com/run/docs/deploying)

## ✅ Checklist

- [x] Cloud Build Trigger configurado e linkado ao Git
- [x] Arquivo `cloudbuild.yaml` configurado
- [x] Workflow do GitHub Actions ajustado (apenas validação)
- [ ] Testar push e verificar deploy automático
- [ ] Verificar logs do Cloud Build
- [ ] Verificar serviço no Cloud Run

---

**Nota:** Com o Cloud Build Trigger configurado, você não precisa configurar secrets do GCP no GitHub Actions para o deploy. O Cloud Build usa a service account do projeto GCP automaticamente.

