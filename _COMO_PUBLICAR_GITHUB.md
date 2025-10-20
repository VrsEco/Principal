# 📦 Como Publicar no GitHub

Guia passo a passo para colocar o projeto no GitHub pela primeira vez.

---

## ⚠️ IMPORTANTE - Antes de Começar

### Verificar Segurança

**NUNCA commite:**
- ❌ Senhas
- ❌ Chaves API
- ❌ Certificados SSL
- ❌ Arquivos `.env`
- ❌ Banco de dados

✅ Já configurado no `.gitignore` - mas sempre confira!

---

## 🚀 Passo a Passo

### 1. Preparar o Repositório Local

```bash
# Navegar até o projeto
cd c:\GestaoVersus\app31

# Inicializar Git (se ainda não fez)
git init

# Adicionar todos os arquivos
git add .

# Verificar o que será commitado
git status
```

**⚠️ IMPORTANTE:** Verifique se nenhum arquivo `.env` aparece na lista!

### 2. Fazer Primeiro Commit

```bash
# Commit inicial
git commit -m "feat: Virtualização completa do sistema

- Docker com multi-stage build
- Docker Compose para dev e prod
- Nginx com SSL/TLS
- CI/CD com GitHub Actions
- Backup automático
- Scripts de deploy
- Documentação completa
- Configuração Google Cloud
- Health checks
- Logging automático

Sistema pronto para produção!"
```

### 3. Criar Repositório no GitHub

#### Opção A: Via Interface Web

1. Acesse: https://github.com/new
2. **Repository name:** `GestaoVersus` (ou o nome desejado)
3. **Description:** "Sistema de Gestão Empresarial - PEV & GRV"
4. **Visibility:** 
   - 🔒 **Private** (recomendado para projeto comercial)
   - 🌍 **Public** (se for open source)
5. ❌ **NÃO** marque "Initialize with README" (já temos)
6. Clique em **"Create repository"**

#### Opção B: Via GitHub CLI

```bash
# Instalar GitHub CLI (se não tiver)
# Windows: https://cli.github.com/

# Login
gh auth login

# Criar repositório
gh repo create GestaoVersus --private --source=. --remote=origin
```

### 4. Conectar Repositório Local ao GitHub

```bash
# Adicionar remote (substitua SEU_USUARIO pelo seu usuário GitHub)
git remote add origin https://github.com/mff2000/GestaoVersus.git

# Verificar remote
git remote -v
```

### 5. Criar Branch Main

```bash
# Renomear branch master para main (se necessário)
git branch -M main
```

### 6. Fazer Push

```bash
# Push inicial
git push -u origin main
```

Se pedir autenticação:
- **Username:** seu usuário GitHub
- **Password:** usar **Personal Access Token** (não a senha)

#### Criar Personal Access Token

1. GitHub → Settings → Developer settings
2. Personal access tokens → Tokens (classic)
3. Generate new token → Classic
4. Marcar: `repo` (Full control)
5. Generate token
6. **COPIAR O TOKEN** (não mostra novamente!)
7. Usar o token como senha no `git push`

### 7. Verificar no GitHub

Acesse: `https://github.com/mff2000/GestaoVersus`

Você deve ver:
- ✅ Todos os arquivos
- ✅ README.md renderizado
- ✅ `.github/workflows/` (Actions)
- ✅ Estrutura completa

---

## 🔐 Configurar GitHub Secrets

Para CI/CD funcionar, configure os secrets:

### 1. Acessar Secrets

No GitHub:
```
Repository → Settings → Secrets and variables → Actions → New repository secret
```

### 2. Adicionar Secrets Necessários

#### Para Deploy em Servidor (VPS)

**SSH_HOST**
```
Valor: IP ou domínio do servidor
Exemplo: 123.456.789.10 ou servidor.com
```

**SSH_USER**
```
Valor: Usuário SSH
Exemplo: root ou ubuntu
```

**SSH_PRIVATE_KEY**
```
Valor: Chave privada SSH (todo o conteúdo)
Como obter:
  cat ~/.ssh/id_rsa
```

#### Para Docker Hub (opcional)

**DOCKER_USERNAME**
```
Valor: Seu usuário Docker Hub
```

**DOCKER_PASSWORD**
```
Valor: Senha ou token Docker Hub
```

#### Para AWS S3 (backup)

**AWS_ACCESS_KEY_ID**
```
Valor: Sua access key AWS
```

**AWS_SECRET_ACCESS_KEY**
```
Valor: Sua secret key AWS
```

**AWS_S3_BUCKET**
```
Valor: Nome do bucket
Exemplo: gestaoversos-backups
```

#### Para Google Cloud (opcional)

**GCP_PROJECT_ID**
```
Valor: ID do projeto GCP
```

**GCP_SERVICE_ACCOUNT_KEY**
```
Valor: JSON da service account
```

### 3. Verificar Secrets

```
Repository → Settings → Secrets and variables → Actions
```

Você deve ver todos os secrets listados (mas não os valores).

---

## 📁 Estrutura de Branches

### Sugestão de Branches

```bash
# Branch principal (produção)
main

# Branch de desenvolvimento
develop

# Branches de features
feature/nome-da-feature

# Branches de bugfix
bugfix/nome-do-bug

# Branches de hotfix
hotfix/nome-do-hotfix
```

### Criar Branch Develop

```bash
# Criar e mudar para develop
git checkout -b develop

# Push para GitHub
git push -u origin develop
```

### Workflow Sugerido

```
feature/nova-funcionalidade
    ↓ Pull Request
develop (testes)
    ↓ Pull Request (aprovado)
main (produção)
```

---

## 🤖 Ativar GitHub Actions

### 1. Verificar Workflows

```
Repository → Actions
```

Você deve ver:
- ✅ Deploy to Production
- ✅ Deploy to Development
- ✅ Database Backup

### 2. Configurar Triggers

**Produção (main):**
- Trigger: Push em `main`
- Auto-deploy: ✅

**Desenvolvimento (develop):**
- Trigger: Push em `develop`
- Auto-deploy: ✅

**Backup:**
- Trigger: Diário 3:00 AM UTC
- Manual: ✅

### 3. Primeiro Deploy

```bash
# Fazer alteração
echo "# Test" >> test.txt

# Commit
git add test.txt
git commit -m "test: CI/CD"

# Push (vai triggar GitHub Actions)
git push origin main
```

Acompanhe em: `Repository → Actions`

---

## 📝 Template de Commit Messages

### Formato

```
tipo(escopo): descrição curta

Descrição longa (opcional)
```

### Tipos

- **feat:** Nova funcionalidade
- **fix:** Correção de bug
- **docs:** Documentação
- **style:** Formatação (sem mudança de código)
- **refactor:** Refatoração
- **test:** Adicionar testes
- **chore:** Manutenção

### Exemplos

```bash
# Feature
git commit -m "feat(pev): adiciona dashboard de OKRs"

# Bugfix
git commit -m "fix(grv): corrige erro ao salvar reunião"

# Documentação
git commit -m "docs: atualiza guia de deploy"

# Refactor
git commit -m "refactor(models): melhora queries do banco"
```

---

## 🔄 Workflow Diário

### Começar o Dia

```bash
# Atualizar branch
git checkout develop
git pull origin develop

# Criar feature branch
git checkout -b feature/minha-feature
```

### Durante o Dia

```bash
# Fazer alterações
# ...

# Stage e commit
git add .
git commit -m "feat: adiciona funcionalidade X"
```

### Fim do Dia

```bash
# Push para GitHub
git push origin feature/minha-feature

# No GitHub, criar Pull Request:
# feature/minha-feature → develop
```

---

## 🚨 Problemas Comuns

### Erro: "Permission denied"

```bash
# Verificar SSH key
ssh -T git@github.com

# Se não funcionar, usar HTTPS
git remote set-url origin https://github.com/mff2000/GestaoVersus.git
```

### Erro: "Files too large"

```bash
# Arquivo > 100MB
# Adicionar ao .gitignore e remover do staging:
git rm --cached arquivo-grande.db
echo "*.db" >> .gitignore
git commit -m "fix: remove arquivo grande"
```

### Esqueci de Adicionar .gitignore

```bash
# Se já commitou arquivo sensível:
git rm --cached .env
git commit -m "fix: remove .env do repositório"
git push origin main

# IMPORTANTE: Trocar todas as senhas que estavam no .env!
```

### Desfazer Último Commit (Local)

```bash
# Desfazer mas manter alterações
git reset --soft HEAD~1

# Desfazer e descartar alterações
git reset --hard HEAD~1
```

---

## ✅ Checklist Final

Antes de considerar concluído:

- [ ] Repositório criado no GitHub
- [ ] Push inicial feito
- [ ] README.md aparecendo corretamente
- [ ] Nenhum arquivo `.env` no repositório
- [ ] GitHub Secrets configurados
- [ ] GitHub Actions ativado
- [ ] Branch `main` protegida (opcional)
- [ ] Branch `develop` criada
- [ ] Colaboradores adicionados (se houver)
- [ ] Descrição e tags configuradas

---

## 🎓 Boas Práticas

### Commits

- ✅ Commits pequenos e frequentes
- ✅ Mensagens descritivas
- ✅ Um conceito por commit
- ❌ Commits gigantes
- ❌ Mensagens vagas ("fix", "update")

### Branches

- ✅ Usar branches para features
- ✅ Deletar branches após merge
- ✅ Pull requests para code review
- ❌ Commitar direto em `main`

### Segurança

- ✅ Sempre revisar `git status`
- ✅ Nunca commitar credenciais
- ✅ Usar `.gitignore`
- ✅ Trocar senhas se expôs acidentalmente

---

## 📚 Recursos

- **Git Docs:** https://git-scm.com/doc
- **GitHub Docs:** https://docs.github.com
- **GitHub Actions:** https://docs.github.com/actions

---

## 🎉 Pronto!

Seu projeto agora está:
- ✅ No GitHub
- ✅ Com CI/CD configurado
- ✅ Pronto para colaboração
- ✅ Protegido e versionado

**Próximo passo:** Fazer seu primeiro deploy! 🚀

Ver: [QUICK_START.md](QUICK_START.md) ou [README_DEPLOY.md](README_DEPLOY.md)

