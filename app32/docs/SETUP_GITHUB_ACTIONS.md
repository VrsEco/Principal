# Configuração do GitHub Actions

Este documento explica como configurar os secrets necessários para os workflows de CI/CD funcionarem corretamente.

## 🔐 Secrets Necessários

### Para Build e Push de Imagens Docker

Os workflows precisam de credenciais do Docker Hub para fazer push das imagens:

1. **DOCKER_USERNAME**: Seu usuário do Docker Hub
2. **DOCKER_PASSWORD**: Sua senha ou token de acesso do Docker Hub

### Para Deploy em Produção

1. **SSH_PRIVATE_KEY**: Chave privada SSH para acesso ao servidor de produção
2. **SSH_USER**: Usuário SSH do servidor de produção
3. **SSH_HOST**: Hostname ou IP do servidor de produção

### Para Deploy em Desenvolvimento

1. **DEV_SSH_PRIVATE_KEY**: Chave privada SSH para acesso ao servidor de desenvolvimento
2. **DEV_SSH_USER**: Usuário SSH do servidor de desenvolvimento
3. **DEV_SSH_HOST**: Hostname ou IP do servidor de desenvolvimento

## 📝 Como Configurar os Secrets

### Passo 1: Acessar as Configurações do Repositório

1. Vá para o repositório no GitHub
2. Clique em **Settings** (Configurações)
3. No menu lateral, clique em **Secrets and variables** → **Actions**

### Passo 2: Adicionar os Secrets

Para cada secret necessário:

1. Clique em **New repository secret**
2. Digite o **Name** (nome do secret, exatamente como listado acima)
3. Digite o **Value** (valor do secret)
4. Clique em **Add secret**

### Passo 3: Verificar os Secrets Configurados

Você deve ter os seguintes secrets configurados:

#### Obrigatórios para Build:
- ✅ `DOCKER_USERNAME`
- ✅ `DOCKER_PASSWORD`

#### Obrigatórios para Deploy em Produção:
- ✅ `SSH_PRIVATE_KEY`
- ✅ `SSH_USER`
- ✅ `SSH_HOST`

#### Obrigatórios para Deploy em Desenvolvimento:
- ✅ `DEV_SSH_PRIVATE_KEY`
- ✅ `DEV_SSH_USER`
- ✅ `DEV_SSH_HOST`

## 🐳 Configurando Docker Hub

### Passo 1: Criar Repositório no Docker Hub

**IMPORTANTE:** Antes de configurar os secrets, você precisa criar o repositório no Docker Hub:

1. Acesse [Docker Hub](https://hub.docker.com/)
2. Faça login na sua conta
3. Clique em **Repositories** → **Create Repository**
4. Configure:
   - **Name**: `app` (ou o nome que preferir)
   - **Visibility**: Público ou Privado (conforme sua necessidade)
   - **Description**: (opcional)
5. Clique em **Create**

**Nota:** O nome completo do repositório será `seu-usuario/app`. Por exemplo, se seu usuário for `joaosilva`, o repositório será `joaosilva/app`.

### Passo 2: Ajustar Nome do Repositório nos Workflows

Se o nome do seu repositório for diferente de `gestaoversos/app`, você precisa atualizar os workflows:

1. Edite `.github/workflows/ci-cd-production.yml`
2. Altere a linha:
   ```yaml
   DOCKER_IMAGE: gestaoversos/app
   ```
   Para:
   ```yaml
   DOCKER_IMAGE: seu-usuario-docker-hub/app
   ```

3. Faça o mesmo em `.github/workflows/ci-cd-development.yml`

### Passo 3: Configurar Credenciais

#### Opção 1: Usar Username e Password

1. Use seu username do Docker Hub
2. Use sua senha do Docker Hub

**⚠️ Nota de Segurança:** É recomendado usar um Access Token ao invés da senha.

#### Opção 2: Usar Access Token (Recomendado)

1. Acesse [Docker Hub](https://hub.docker.com/)
2. Vá em **Account Settings** → **Security**
3. Clique em **New Access Token**
4. Dê um nome ao token (ex: "github-actions")
5. Copie o token gerado
6. Use o token como `DOCKER_PASSWORD` no GitHub

## 🔑 Configurando SSH

### Gerar Chave SSH (se ainda não tiver)

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

### Adicionar Chave Pública ao Servidor

```bash
# Copiar chave pública para o servidor
ssh-copy-id -i ~/.ssh/github_actions.pub usuario@servidor
```

### Adicionar Chave Privada ao GitHub

1. Copie o conteúdo da chave privada:
   ```bash
   cat ~/.ssh/github_actions
   ```

2. Cole o conteúdo completo (incluindo `-----BEGIN OPENSSH PRIVATE KEY-----` e `-----END OPENSSH PRIVATE KEY-----`) no secret `SSH_PRIVATE_KEY` ou `DEV_SSH_PRIVATE_KEY`

## ✅ Verificação

Após configurar os secrets:

1. Faça um push para a branch `main` ou `develop`
2. Verifique se o workflow executa sem erros
3. Os jobs de build devem conseguir fazer login no Docker Hub
4. Os jobs de deploy devem conseguir conectar via SSH

## 🚨 Troubleshooting

### Erro: "Username and password required"

- Verifique se `DOCKER_USERNAME` e `DOCKER_PASSWORD` estão configurados
- Verifique se os nomes dos secrets estão exatamente como especificado (case-sensitive)
- Verifique se não há espaços extras nos valores dos secrets

### Erro: "push access denied, repository does not exist or may require authorization"

Este erro indica que:
1. **O repositório não existe no Docker Hub** - Crie o repositório no Docker Hub primeiro (veja "Passo 1: Criar Repositório no Docker Hub" acima)
2. **O nome do repositório está incorreto** - Verifique se o `DOCKER_IMAGE` nos workflows corresponde ao formato `seu-usuario/nome-repositorio`
3. **Você não tem permissão** - Certifique-se de que o `DOCKER_USERNAME` configurado tem permissão para fazer push no repositório

**Solução:**
- Crie o repositório no Docker Hub com o nome exato usado no workflow
- Ou ajuste o workflow para usar o nome do repositório que você criou
- Certifique-se de que o `DOCKER_USERNAME` corresponde ao proprietário do repositório

### Erro: "Permission denied (publickey)"

- Verifique se a chave pública SSH foi adicionada ao servidor
- Verifique se o `SSH_USER` está correto
- Verifique se o `SSH_HOST` está correto
- Verifique se a chave privada foi copiada completamente (incluindo headers)

### Erro: "Cannot connect to host"

- Verifique se o `SSH_HOST` está correto
- Verifique se o servidor está acessível
- Verifique se a porta SSH (22) está aberta no firewall

## 📚 Referências

- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Docker Hub Access Tokens](https://docs.docker.com/docker-hub/access-tokens/)
- [SSH Key Generation](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)

