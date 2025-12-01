# 📁 Estrutura App31 (Prod) + App32 (Dev)

## 🎯 Conceito Simples

Duas pastas separadas para manter produção estável e desenvolvimento livre:

- **`app31`** = Produção (versão estável em uso)
- **`app32`** = Desenvolvimento (onde você trabalha à vontade)

---

## 📂 Estrutura de Pastas

```
C:\GestaoVersus\
├── app31\          ← PRODUÇÃO (Git conectado, deploy)
│   ├── .git\       ← Controle de versão AQUI
│   ├── .env.production
│   ├── docker-compose.yml
│   └── ... (código em uso)
│
└── app32\          ← DESENVOLVIMENTO (sem Git, local)
    ├── .env.development
    ├── docker-compose.override.yml
    └── ... (código em desenvolvimento)
```

---

## 🔄 Fluxo de Trabalho

### 1. **Desenvolvimento (app32)**

```bash
# Trabalhe normalmente em app32
cd C:\GestaoVersus\app32

# Edite arquivos, teste, desenvolva
# Use Docker normalmente
docker-compose up

# Quando estiver pronto e testado:
```

### 2. **Promover para Produção**

```bash
# Execute o script de promoção
cd C:\GestaoVersus\app31
PROMOVER_DEV_PARA_PROD.bat

# O script faz:
# ✅ Backup automático de app31
# ✅ Copia código de app32 → app31
# ✅ Preserva configurações de produção
```

### 3. **Testar em Produção Local**

```bash
cd C:\GestaoVersus\app31

# Revise as mudanças
# Teste localmente
docker-compose up

# Se tudo OK:
git add .
git commit -m "Promovido de app32 - [descrição]"
git push
```

### 4. **Deploy**

O deploy depende de onde está hospedado:

- **Configr.com**: Push para Git conecta automaticamente
- **Google Cloud**: `gcloud run deploy` ou CI/CD configurado

---

## ⚙️ Configuração Inicial

### App31 (Produção)

1. **Conectar ao Git**:
```bash
cd C:\GestaoVersus\app31
git init
git remote add origin [URL_DO_REPOSITORIO]
git add .
git commit -m "Versão inicial produção"
git push -u origin main
```

2. **Configurar .env.production**:
```env
FLASK_ENV=production
DATABASE_URL=postgresql://[credenciais_producao]
SECRET_KEY=[chave_secreta_producao]
```

3. **docker-compose.yml**:
   - Já configurado para produção
   - Usa `.env.production`

### App32 (Desenvolvimento)

1. **Criar pasta**:
```bash
cd C:\GestaoVersus
mkdir app32
cd app32
```

2. **Copiar estrutura de app31**:
```bash
# Copiar tudo exceto .git
xcopy /E /I ..\app31\* . /EXCLUDE:exclude.txt
```

3. **Criar docker-compose.override.yml**:
```yaml
services:
  app:
    volumes:
      - ./modules:/app/modules
      - ./templates:/app/templates
      - ./services:/app/services
      - ./api:/app/api
      # ... outros volumes para hot-reload
```

4. **Configurar .env.development**:
```env
FLASK_ENV=development
FLASK_DEBUG=1
DATABASE_URL=postgresql://[credenciais_dev]
SECRET_KEY=dev-secret-key
```

---

## 🚨 Regras Importantes

### ✅ **FAZER em app32**:
- ✅ Desenvolver novas features
- ✅ Testar mudanças
- ✅ Experimentar
- ✅ Quebrar coisas (sem medo!)

### ❌ **NÃO FAZER em app32**:
- ❌ Conectar ao Git de produção
- ❌ Fazer deploy direto
- ❌ Editar .env.production

### ✅ **FAZER em app31**:
- ✅ Apenas correções urgentes
- ✅ Testar antes de fazer commit
- ✅ Manter versão estável

### ❌ **NÃO FAZER em app31**:
- ❌ Desenvolver novas features
- ❌ Experimentar sem testar
- ❌ Commitar código não testado

---

## 📋 Checklist Antes de Promover

Antes de executar `PROMOVER_DEV_PARA_PROD.bat`:

- [ ] **Testei tudo em app32** (localmente funcionando)
- [ ] **Sem erros** (lint, syntax, runtime)
- [ ] **Documentação atualizada** (se necessário)
- [ ] **Backup de app31** será feito automaticamente
- [ ] **Configurações preservadas** (.env.production não será sobrescrito)

---

## 🔍 Quando Usar Cada Pasta

### Use **app32** quando:
- 💡 Desenvolver nova feature
- 🐛 Testar correção de bug
- 🎨 Ajustar layout/design
- 📝 Adicionar documentação
- 🧪 Experimentar novas bibliotecas

### Use **app31** quando:
- 🔴 Correção urgente em produção
- ✅ Promover código testado de app32
- 📊 Verificar versão em produção
- 🚀 Fazer deploy

---

## 📝 Exemplo Prático

### Cenário: Adicionar nova funcionalidade

1. **Desenvolvimento (app32)**:
```bash
cd C:\GestaoVersus\app32

# Crio nova feature
# Edito arquivos...
# Testo localmente...

docker-compose up
# Testa em http://localhost:5003

# Funciona! ✅
```

2. **Promover (app31)**:
```bash
cd C:\GestaoVersus\app31
PROMOVER_DEV_PARA_PROD.bat

# Script faz backup e copia
# Agora app31 tem o código novo
```

3. **Testar em Produção Local**:
```bash
cd C:\GestaoVersus\app31
docker-compose up

# Testa novamente
# Tudo OK? ✅
```

4. **Commit e Deploy**:
```bash
git add .
git commit -m "Nova feature: [nome]"
git push

# Deploy automático ou manual
```

---

## 🆘 Troubleshooting

### Erro ao promover
- ✅ Verifique se app32 está funcionando
- ✅ Verifique espaço em disco (backup)
- ✅ Execute como Administrador

### Código não aparece em app31
- ✅ Verifique se o script executou completamente
- ✅ Verifique se há arquivos bloqueados (feche editores)
- ✅ Verifique permissões de pasta

### Git não funciona em app31
- ✅ Verifique se `.git` existe em app31
- ✅ Verifique `git remote -v`
- ✅ Configure Git: `git config user.name` e `git config user.email`

---

## 📚 Referências

- Script de promoção: `PROMOVER_DEV_PARA_PROD.bat`
- Documentação Git: Ver `docs/governance/`
- Docker: Ver `Dockerfile` e `docker-compose.yml`

---

**Última atualização:** 19/11/2025







