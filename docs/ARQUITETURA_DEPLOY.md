# Arquitetura de Deploy - GestaoVersus

Este documento explica como funciona a arquitetura de deploy do projeto, incluindo a integração entre GitHub Actions e Google Cloud Build Trigger.

## 🏗️ Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────┐
│                    PUSH NO GIT                              │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────────┐
│  GitHub Actions  │          │  Cloud Build Trigger │
│   (Workflows)    │          │       (GCP)          │
└────────┬─────────┘          └──────────┬───────────┘
         │                               │
         │                               │
    ┌────┴────┬──────────┬──────────┐   │
    │         │          │          │   │
    ▼         ▼          ▼          ▼   ▼
┌──────┐ ┌──────┐  ┌────────┐ ┌──────────┐ ┌─────────────┐
│Testes│ │Lint  │  │Docker  │ │Deploy    │ │Deploy       │
│      │ │      │  │Hub     │ │SSH       │ │Cloud Run    │
│      │ │      │  │(mff2000│ │(Servidor │ │(GCP)        │
│      │ │      │  │/app)   │ │Próprio)  │ │             │
└──────┘ └──────┘  └────────┘ └──────────┘ └─────────────┘
```

## 📋 Workflows e Responsabilidades

### 1. ✅ Pre-Deploy Validation (`deploy-gcp.yml`)
**Responsabilidade:** Validação de código antes do deploy

**O que faz:**
- ✅ Valida formatação do código (Black)
- ✅ Executa linting (Flake8)
- ✅ Executa testes básicos
- ✅ Monitora status do Cloud Build (opcional)

**O que NÃO faz:**
- ❌ Não faz deploy (o Cloud Build faz)

**Trigger:** Push em qualquer branch

---

### 2. 🚀 Deploy to Production (`ci-cd-production.yml`)
**Responsabilidade:** Deploy para servidor próprio via SSH

**O que faz:**
- 🧪 Executa testes
- 🏗️ Faz build da imagem Docker
- 📤 Faz push para Docker Hub (`mff2000/app:latest`)
- 🚀 Faz deploy via SSH no servidor próprio (secrets configurados)

**O que NÃO faz:**
- ❌ Não faz deploy no GCP (o Cloud Build faz)

**Trigger:** Push na branch `main`

**Deploy:** Servidor próprio (via SSH) - **Opcional** (só se secrets SSH estiverem configurados)

---

### 3. 🧪 Deploy to Development (`ci-cd-development.yml`)
**Responsabilidade:** Deploy para ambiente de desenvolvimento

**O que faz:**
- 🔍 Valida formatação e linting
- 🧪 Executa testes
- 🏗️ Faz build da imagem Docker
- 📤 Faz push para Docker Hub (`mff2000/app:dev`)
- 🚀 Faz deploy via SSH no servidor de dev (secrets configurados)

**Trigger:** Push nas branches `develop` ou `dev`

**Deploy:** Servidor de desenvolvimento (via SSH) - **Opcional**

---

### 4. ☁️ Cloud Build Trigger (GCP)
**Responsabilidade:** Deploy automático no Google Cloud Run

**O que faz:**
- 🧪 Executa todos os testes
- 🏗️ Faz build da imagem Docker
- 📤 Faz push para Artifact Registry (GCP)
- 🚀 Faz deploy no Cloud Run automaticamente
- 🔄 Executa migrations (se configurado)
- ✅ Executa health check

**Trigger:** Push no Git (configurado no GCP)

**Deploy:** Google Cloud Run - **Obrigatório** (sempre executa quando há push)

**Arquivo:** `cloudbuild.yaml`

---

## 🔄 Fluxo Completo ao Fazer Push

Quando você faz `git push` na branch `main`:

### 1. GitHub Actions (Paralelo)
```
┌─────────────────────────────────────┐
│  Workflow: Deploy to Production     │
├─────────────────────────────────────┤
│ ✅ Testes                           │
│ ✅ Build Docker                     │
│ ✅ Push para Docker Hub             │
│ ⏭️ Deploy SSH (se configurado)      │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Workflow: Pre-Deploy Validation    │
├─────────────────────────────────────┤
│ ✅ Validação de código              │
│ ✅ Monitoramento Cloud Build        │
└─────────────────────────────────────┘
```

### 2. Cloud Build Trigger (GCP) - Paralelo
```
┌─────────────────────────────────────┐
│  Cloud Build (GCP)                  │
├─────────────────────────────────────┤
│ ✅ Testes                           │
│ ✅ Build Docker                     │
│ ✅ Push para Artifact Registry      │
│ ✅ Deploy no Cloud Run              │
│ ✅ Migrations                       │
│ ✅ Health Check                     │
└─────────────────────────────────────┘
```

## ⚠️ Pontos Importantes

### Não Há Conflito Entre Deploys

1. **GitHub Actions → Docker Hub + Servidor Próprio**
   - Faz push para `mff2000/app` no Docker Hub
   - Faz deploy via SSH no servidor próprio (se configurado)
   - **Não interfere** com o Cloud Build

2. **Cloud Build → Artifact Registry + Cloud Run**
   - Faz push para Artifact Registry do GCP
   - Faz deploy no Cloud Run
   - **Não interfere** com o GitHub Actions

### Ambos Executam em Paralelo

- ✅ GitHub Actions e Cloud Build executam **simultaneamente**
- ✅ Não há conflito porque usam registries diferentes:
  - GitHub Actions: Docker Hub (`mff2000/app`)
  - Cloud Build: Artifact Registry (`us-central1-docker.pkg.dev/...`)

### Deploy no GCP é Obrigatório

- ✅ O Cloud Build Trigger **sempre executa** quando há push
- ✅ É configurado no console do GCP
- ✅ Não depende de secrets do GitHub
- ✅ Usa service account do GCP automaticamente

### Deploy via SSH é Opcional

- ⏭️ Os workflows de deploy via SSH **só executam** se os secrets estiverem configurados
- ⏭️ Se não estiverem configurados, são pulados graciosamente
- ⏭️ Não quebram o workflow

## 🎯 Cenários de Uso

### Cenário 1: Deploy Apenas no GCP (Atual)
- ✅ Cloud Build faz deploy no Cloud Run automaticamente
- ⏭️ GitHub Actions valida código e faz push para Docker Hub
- ⏭️ Deploy via SSH é pulado (secrets não configurados)

### Cenário 2: Deploy no GCP + Servidor Próprio
- ✅ Cloud Build faz deploy no Cloud Run
- ✅ GitHub Actions faz deploy via SSH no servidor próprio
- ✅ Ambos executam em paralelo

### Cenário 3: Apenas Validação
- ✅ GitHub Actions valida código
- ✅ Cloud Build faz deploy no Cloud Run
- ⏭️ Sem deploy via SSH

## 📊 Resumo das Alterações Recentes

### O Que Mudou

1. **Workflow `deploy-gcp.yml`:**
   - ❌ **Antes:** Tentava fazer deploy no GCP (conflitava com Cloud Build)
   - ✅ **Agora:** Apenas valida código (não faz deploy)

2. **Workflows de Produção/Desenvolvimento:**
   - ✅ **Antes:** Falhavam se secrets SSH não estivessem configurados
   - ✅ **Agora:** Pulam graciosamente se secrets não estiverem configurados

3. **Cloud Build Trigger:**
   - ✅ **Mantido:** Continua fazendo deploy no Cloud Run automaticamente
   - ✅ **Não alterado:** Funciona independentemente do GitHub Actions

## 🔍 Verificar Status dos Deploys

### GitHub Actions
- Acesse: `https://github.com/VrsEco/Principal/actions`
- Veja status de todos os workflows

### Cloud Build (GCP)
- Acesse: `https://console.cloud.google.com/cloud-build/builds`
- Veja status do deploy no Cloud Run

### Cloud Run (GCP)
- Acesse: `https://console.cloud.google.com/run`
- Veja o serviço `gestaoversos-app` ou `gestaoversos`

## ✅ Vantagens Desta Arquitetura

1. **Separação de Responsabilidades:**
   - GitHub Actions: Validação e deploy em servidor próprio
   - Cloud Build: Deploy no GCP

2. **Sem Conflitos:**
   - Cada sistema usa seu próprio registry
   - Executam em paralelo sem interferência

3. **Flexibilidade:**
   - Deploy no GCP sempre acontece (obrigatório)
   - Deploy via SSH é opcional (secrets configurados)

4. **Resiliência:**
   - Se um falhar, o outro continua funcionando
   - Validações no GitHub Actions não bloqueiam deploy no GCP

## 🚨 Troubleshooting

### Cloud Build não está executando

1. Verifique o trigger no GCP:
   ```bash
   gcloud builds triggers list --region=us-central1
   ```

2. Verifique se o repositório está conectado:
   - Console GCP → Cloud Build → Triggers
   - Verifique a conexão com o GitHub

3. Verifique os logs:
   ```bash
   gcloud builds list --limit=5 --region=us-central1
   ```

### GitHub Actions falhando

1. Verifique os secrets configurados
2. Verifique os logs do workflow
3. Lembre-se: Falhas no GitHub Actions **não impedem** o Cloud Build de executar

### Deploy duplicado

- ✅ **Normal:** GitHub Actions e Cloud Build executam em paralelo
- ✅ **Sem problema:** Cada um faz deploy em seu destino:
  - GitHub Actions → Servidor próprio (se configurado)
  - Cloud Build → Cloud Run (sempre)

---

**Última atualização:** Com as alterações recentes, o deploy no GCP via Cloud Build Trigger continua funcionando normalmente, e os workflows do GitHub Actions não interferem mais.

