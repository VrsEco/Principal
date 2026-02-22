# GitHub Actions - Workflows Disponíveis

Este documento lista todos os workflows configurados no projeto e explica como eles aparecem no GitHub Actions.

## 📋 Workflows Configurados

### 1. 🚀 Deploy to Production
- **Arquivo**: `.github/workflows/ci-cd-production.yml`
- **Trigger**: Push na branch `main`
- **Execução Manual**: ✅ Sim (workflow_dispatch)
- **Descrição**: Deploy automático para produção

### 2. 🧪 Deploy to Development
- **Arquivo**: `.github/workflows/ci-cd-development.yml`
- **Trigger**: Push nas branches `develop` ou `dev`
- **Execução Manual**: ✅ Sim (workflow_dispatch)
- **Descrição**: Deploy automático para ambiente de desenvolvimento

### 3. 💾 Database Backup
- **Arquivo**: `.github/workflows/backup-database.yml`
- **Trigger**: Schedule diário às 3:00 AM UTC
- **Execução Manual**: ✅ Sim (workflow_dispatch)
- **Descrição**: Backup automático do banco de dados

### 4. Backup Automático
- **Arquivo**: `.github/workflows/backup.yml`
- **Trigger**: Schedule diário às 3:00 AM UTC
- **Execução Manual**: ✅ Sim (workflow_dispatch)
- **Descrição**: Backup automático de database e uploads

### 5. ✅ Pre-Deploy Validation
- **Arquivo**: `.github/workflows/deploy-gcp.yml`
- **Trigger**: Push em qualquer branch
- **Execução Manual**: ✅ Sim (workflow_dispatch)
- **Descrição**: Validação de código antes do deploy (Cloud Build faz o deploy)

## 🔍 Por Que Alguns Workflows Não Aparecem?

O GitHub Actions mostra workflows na sidebar baseado em:

1. **Workflows executados recentemente** - Workflows que foram executados nas últimas semanas aparecem primeiro
2. **Relevância para a branch atual** - Workflows configurados para a branch atual aparecem mais facilmente
3. **Atualização da interface** - Pode levar alguns minutos para novos workflows aparecerem

### Como Fazer Todos Aparecerem

1. **Executar manualmente cada workflow:**
   - Vá em **Actions** → Clique no workflow
   - Clique em **Run workflow**
   - Execute uma vez para que apareça na lista

2. **Fazer push em diferentes branches:**
   - Workflows de desenvolvimento aparecerão quando você fizer push na branch `develop`
   - Workflows de backup aparecerão quando executarem no schedule

3. **Aguardar atualização:**
   - O GitHub pode levar alguns minutos para atualizar a lista
   - Recarregue a página após alguns minutos

## 📊 Status dos Workflows

### Workflows Ativos

Todos os workflows estão configurados e ativos:

- ✅ `ci-cd-production.yml` - Ativo
- ✅ `ci-cd-development.yml` - Ativo
- ✅ `backup-database.yml` - Ativo
- ✅ `backup.yml` - Ativo
- ✅ `deploy-gcp.yml` - Ativo

### Verificar Status

Para verificar se todos os workflows estão sendo reconhecidos:

1. Vá em **Actions** no GitHub
2. Clique em **All workflows** (se disponível)
3. Ou acesse diretamente: `https://github.com/VrsEco/Principal/actions`

## 🚀 Executar Workflows Manualmente

Todos os workflows podem ser executados manualmente:

1. Vá em **Actions**
2. Clique no workflow desejado
3. Clique em **Run workflow**
4. Selecione a branch
5. Clique em **Run workflow**

## 📝 Notas

- Workflows com `workflow_dispatch` sempre podem ser executados manualmente
- Workflows agendados (schedule) executam automaticamente no horário configurado
- Workflows de push executam automaticamente quando há push na branch configurada

## 🔄 Atualizar Lista de Workflows

Se os workflows não aparecerem na sidebar:

1. **Forçar atualização:**
   - Faça um pequeno commit e push
   - Isso força o GitHub a reindexar os workflows

2. **Verificar sintaxe:**
   - Todos os workflows foram validados e estão corretos
   - Não há erros de sintaxe

3. **Aguardar:**
   - O GitHub pode levar até 24 horas para atualizar completamente
   - Workflows executados recentemente aparecem primeiro

---

**Última atualização**: Todos os workflows estão configurados e funcionais. Se algum não aparecer na sidebar, execute-o manualmente uma vez para que seja adicionado à lista.

