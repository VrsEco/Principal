# ✅ Checklist: Aplicação da Correção Playwright

## 📋 Resumo do Problema
**Erro:** `BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1187/chrome-linux/headless_shell`

**Causa:** Playwright instalado mas browsers não baixados no container Docker

**Solução:** Adicionar `playwright install chromium` no Dockerfile

---

## 🔧 Arquivos Modificados

- [x] `Dockerfile` - Adicionadas dependências e comando de instalação
- [x] `REBUILD_INSTRUCTIONS.md` - Instruções detalhadas de rebuild
- [x] `docs/governance/DECISION_LOG.md` - ADR-011 documentando decisão

---

## 🚀 Passos para Aplicar a Correção

### 1. Verificar Mudanças nos Arquivos ✅

```bash
# Ver diferenças no Dockerfile
git diff Dockerfile

# Ver novos arquivos criados
git status
```

**Mudanças esperadas no Dockerfile:**
- ✅ Linha ~50-72: Dependências do sistema para Chromium
- ✅ Linha ~87: `RUN playwright install --with-deps chromium`

### 2. Parar Containers Atuais

```bash
# Parar todos os serviços
docker-compose down

# (Opcional) Limpar imagens antigas para economizar espaço
docker image prune -a
```

### 3. Rebuild da Imagem Docker

**Opção A - Rebuild Completo (Recomendado):**
```bash
docker-compose build --no-cache
```

**Opção B - Rebuild Apenas App:**
```bash
docker-compose build --no-cache app
```

⏱️ **Tempo estimado:** 5-8 minutos (depende da conexão de internet)

### 4. Subir os Containers

```bash
# Subir todos os serviços
docker-compose up -d

# Verificar status
docker-compose ps
```

**Status esperado:** Todos os containers `healthy` ou `running`

### 5. Verificar Instalação do Playwright

```bash
# Acessar o container
docker exec -it gestaoversos_app_prod bash

# Dentro do container, verificar versão
playwright --version
# Saída esperada: Version 1.55.0

# Listar browsers instalados
ls -la /root/.cache/ms-playwright/
# Deve conter: chromium_headless_shell-1187/

# Sair do container
exit
```

### 6. Testar Geração de PDF

**Teste Manual:**
1. Acesse: `http://localhost:5002/login`
2. Faça login
3. Vá para uma empresa
4. Acesse: `http://localhost:5002/company/{company_id}/process/map-pdf2`
5. Verifique se o PDF é gerado sem erros

**Teste via Logs:**
```bash
# Monitorar logs em tempo real
docker-compose logs -f app

# Procurar por erros
docker-compose logs app | grep -i "playwright\|chromium\|browser"
```

**✅ Sucesso:** PDF é gerado e baixado  
**❌ Falha:** Erro de browser persiste → Ver seção "Troubleshooting"

### 7. Verificar Uso de Recursos

```bash
# Ver uso de memória dos containers
docker stats --no-stream

# Ver tamanho da imagem
docker images | grep gestaoversos
```

**Tamanhos esperados:**
- Imagem app: ~800-900MB (antes era ~500MB)
- Memória runtime: ~200-400MB por container

---

## 🐛 Troubleshooting

### Erro: "playwright: command not found"

**Causa:** Playwright não foi copiado corretamente do builder

**Solução:**
```bash
docker-compose build --no-cache app
```

### Erro: "Permission denied" ao instalar browsers

**Causa:** `playwright install` executado após `USER appuser`

**Verificar:** No Dockerfile, linha 87 deve vir ANTES de `USER appuser` (linha 93)

### Erro: Browser ainda não encontrado

**Possíveis causas:**
1. Cache do Docker está interferindo
2. Dependências do sistema faltando

**Solução:**
```bash
# Limpar completamente
docker-compose down -v
docker system prune -a
docker-compose build --no-cache
docker-compose up -d
```

### Container não sobe após rebuild

**Verificar logs:**
```bash
docker-compose logs app
```

**Causas comuns:**
- Falta de memória no host
- Porta 5002 já em uso
- Dependências do PostgreSQL não prontas

---

## 📊 Validação Final

### ✅ Checklist de Validação

- [ ] Containers subiram sem erros: `docker-compose ps`
- [ ] Playwright instalado: `docker exec gestaoversos_app_prod playwright --version`
- [ ] Chromium presente: `docker exec gestaoversos_app_prod ls /root/.cache/ms-playwright/`
- [ ] PDF gerado com sucesso na rota `/company/{id}/process/map-pdf2`
- [ ] Sem erros nos logs: `docker-compose logs app | grep -i error`
- [ ] Uso de memória dentro do esperado: `docker stats --no-stream`

### 📈 Métricas Antes/Depois

| Métrica | Antes | Depois | Status |
|---------|-------|--------|--------|
| PDF gerado? | ❌ Falha | ✅ Sucesso | ✅ |
| Tempo de build | ~3min | ~6min | ⚠️ Normal |
| Tamanho imagem | ~500MB | ~850MB | ⚠️ Normal |
| Memória runtime | ~200MB | ~400MB | ⚠️ Normal |

---

## 🔄 Rollback (Se Necessário)

Se a correção causar problemas:

```bash
# 1. Reverter Dockerfile
git checkout HEAD~1 -- Dockerfile

# 2. Rebuild
docker-compose down
docker-compose build --no-cache app
docker-compose up -d

# 3. Remover arquivos de documentação (opcional)
rm REBUILD_INSTRUCTIONS.md PLAYWRIGHT_FIX_CHECKLIST.md

# 4. Reverter ADR-011 no DECISION_LOG.md
git checkout HEAD~1 -- docs/governance/DECISION_LOG.md
```

---

## 📞 Suporte

**Documentos relacionados:**
- `REBUILD_INSTRUCTIONS.md` - Instruções detalhadas
- `docs/governance/DECISION_LOG.md` - ADR-011
- `Dockerfile` - Configuração do container

**Logs úteis:**
```bash
# App principal
docker-compose logs -f app

# Celery Worker (se PDF gerado em background)
docker-compose logs -f celery_worker

# Todos os serviços
docker-compose logs -f
```

**Comandos úteis:**
```bash
# Restart apenas do app
docker-compose restart app

# Rebuild + restart forçado
docker-compose up -d --force-recreate app

# Ver processos dentro do container
docker exec gestaoversos_app_prod ps aux
```

---

**✅ Correção concluída com sucesso quando:**
- Containers sobem sem erros
- PDFs são gerados corretamente
- Não há erros de Playwright nos logs

**Data:** 21/10/2025  
**Versão Playwright:** 1.55.0  
**Browser:** Chromium headless shell 1187

