# 🚀 Deploy no Google Cloud Platform - Guia Rápido

## ⚡ Início Rápido

### 1. Autenticar no GCP

```powershell
.\scripts\setup-gcp-auth.ps1
```

Escolha a opção 1 (Autenticação interativa) e siga as instruções.

### 2. Build e Push das Imagens

```powershell
.\scripts\build-and-push-gcp.ps1
```

### 3. Nomes das Imagens Geradas

Após o build, você terá estas imagens no Artifact Registry:

**Backend:**
```
us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo/my-backend:latest
```

**Frontend:**
```
us-central1-docker.pkg.dev/vrs-eco-478714/my-app-repo/my-frontend:latest
```

Use estes nomes no seu design do Cloud Run!

## 📚 Documentação Completa

- **[GCP_DEPLOYMENT.md](docs/GCP_DEPLOYMENT.md)** - Guia completo de deploy
- **[GCP_AUTHENTICATION.md](docs/GCP_AUTHENTICATION.md)** - Guia de autenticação
- **[GCP_IMAGES.txt](GCP_IMAGES.txt)** - Referência rápida dos nomes das imagens

## 🔐 Segurança

**NUNCA compartilhe suas credenciais!**

- ✅ Use autenticação interativa (`gcloud auth login`)
- ✅ Use Service Accounts para autentomação
- ✅ Arquivos de credenciais estão no `.gitignore`
- ❌ NUNCA commite `gcp-key.json` no Git

## 🆘 Problemas?

Consulte a seção de Troubleshooting em:
- [GCP_AUTHENTICATION.md](docs/GCP_AUTHENTICATION.md)
- [GCP_DEPLOYMENT.md](docs/GCP_DEPLOYMENT.md)




