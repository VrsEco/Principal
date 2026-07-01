# 📋 RUNBOOK: Manutenção e Atualizações de Produção
> **Status:** Documento de Referência Obrigatória  
> **Criado por:** @ARQUITETO — Squad Gestão Versus  
> **Data:** 2026-02-25  
> **Origem:** Pós-mortem do incidente de HTTP 500 (48h fora do ar, Fev/2026)

---

## 🏗️ Arquitetura do Ambiente de Produção

| Componente | Valor |
|---|---|
| **Host** | Configr (Cloudez) |
| **Domínio** | app.gestaoversus.com.br |
| **Caminho raiz** | `/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/` |
| **Pasta do app** | `.../www/app32/` |
| **Entrypoint** | `.../www/app32/passenger_wsgi.py` |
| **Servidor WSGI** | uWSGI (config: `.../etc/uwsgi/`) |
| **Virtualenv** | `.../virtualenv/3.12/` (Python 3.12) |
| **Banco** | PostgreSQL (externo ao servidor Flask) |
| **Deploy** | GitHub Actions manual (`workflow_dispatch`) → SSH → deploy por modo (`quick`/`standard`/`full`) |

> ⚠️ **CRÍTICO:** O arquivo `uwsgi.ini` do servidor está **fora do repositório Git** e é controlado pela Configr. Alterações nele requerem intervenção do suporte.

---

## ✅ O QUE PODE SER FEITO (Via Git Push)

### 1. Código da Aplicação
- Criar, editar e remover arquivos Python, HTML, CSS, JS dentro de `app32/`
- Atualizar rotas (`api/routes/`), serviços (`services/`), modelos (`models/`)
- Atualizar templates Jinja2 (`templates/`)

### 2. Arquivo `passenger_wsgi.py`
- **SEMPRE versionado no Git**, na raiz de `app32/`
- É o único entrypoint Flask que o uWSGI carrega
- Qualquer alteração aqui é entregue automaticamente pelo deploy

### 3. Arquivo `requirements.txt`
- Atualizar versões de pacotes **com faixas testadas** (prefira `>=x.y,<x+1.0`)
- Adicionar novos pacotes após testar localmente
- **NÃO use pin exato (`==`)** para pacotes do ecossistema LangChain/LangGraph — eles têm alta rotatividade de versões e é comum terem versões "yanked" (recolhidas) sem aviso

### 4. Variáveis de Ambiente (`.env`)
- O `.env` dentro de `app32/` é lido pelo `passenger_wsgi.py` via `dotenv`
- Pode ser atualizado via Git (exceto secrets que devem estar no GitHub Secrets)

### 5. Migrations do Banco
- Geradas localmente com `flask db migrate` e enviadas via Git
- Executadas apenas quando o operador escolher o modo `full` no workflow manual de produção

---

## 🚦 Modelo oficial de deploy em produção

O deploy de produção passa a ser **manual e controlado pelo operador**, sem publicação automática a cada `push` na `main`.

### Modos oficiais

| Modo | O que faz | Quando usar |
|---|---|---|
| `quick` | atualiza código + reinicia app web + valida health + opcionalmente reinicia MCP | ajustes leves, UI, textos, correções sem mudança de dependência/schema |
| `standard` | `quick` + `pip install -r requirements.txt` | mudanças com dependências novas/alteradas, sem migration |
| `full` | `standard` + migrations | mudanças estruturais, schema, rollout controlado |

### Regras de ouro do novo fluxo

1. **Não existe mais deploy automático por push na `main`.**
2. **Dependência Python não é mais instalada por comando avulso fora do `requirements.txt`.**
3. **Migration não roda por padrão; só no modo `full`.**
4. **Restart continua automatizado**, com validação de `healthz` ao final.
5. **MCP pode ser reiniciado no mesmo workflow**, mas continua sob decisão explícita do operador.

### Decisão prática por tipo de mudança

- mudança leve sem schema e sem dependência -> `quick`
- mudança com dependência, sem schema -> `standard`
- mudança com schema/migration/backfill -> `full`

---

## ❌ O QUE NÃO PODE SER FEITO (Via Git Push)

### 1. Alterar o arquivo de configuração do uWSGI
- **Caminho:** `/srv/appgestaoversuscombr.../etc/uwsgi/app.ini` (e `conf.d/*.ini`)
- **Motivo:** Está fora do diretório `www/` — o Git não o alcança
- **Como alterar:** Abrir chamado no suporte da Configr com o texto exato desejado

### 2. Restartar o processo uWSGI manualmente via SSH
- **Motivo:** A porta SSH 22 não está acessível externamente para nossa chave de deploy
- **Como restartar:** Painel da Configr → Aplicação → Reiniciar Instância  
  OU via deploy (o script toca o `restart.txt`, que sinaliza ao Passenger)

### 3. Instalar softwares no OS do servidor (apt, yum, etc.)
- **Motivo:** Ambiente de hospedagem compartilhada — sem acesso root
- **Alternativa:** Usar apenas pacotes Python via `pip` no virtualenv

### 4. Ver logs de erro em tempo real
- **Motivo:** Sem acesso SSH direto
- **Como obter:** Painel da Configr → Logs de Aplicação  
  OU abrir chamado solicitando as últimas 50-100 linhas do `error.log`

---

## 🔥 PROTOCOLO DE INCIDENTE (HTTP 500 em Produção)

Siga **nesta ordem exata**. Não pule etapas.

### Passo 1 — Verificar se o deploy chegou
```bash
# Verificar último commit na branch main
git log -1

# Checar status do GitHub Actions (https://github.com/VrsEco/Principal/actions)
# O último run deve ter: conclusion = "success"
```

### Passo 2 — Testar ambiente local
```bash
# PostgreSQL 14 rodando?
Get-Service -Name postgresql-x64-14

# Subir app local
python run_dev.py

# Acessar http://127.0.0.1:5032/
```
> Se o local não sobe → o problema é no código. Corrija localmente antes de fazer push.  
> Se o local sobe → o problema é exclusivo do servidor de produção.

### Passo 3 — Verificar o entrypoint
Confirmar que `app32/passenger_wsgi.py` existe e está versionado:
```bash
git ls-files | Select-String passenger_wsgi
```

### Passo 4 — Solicitar logs ao suporte da Configr
Mensagem padrão:
```
Olá, nossa aplicação está retornando HTTP 500.
O deploy foi concluído com sucesso (pip install OK, git pull OK).
Precisamos das últimas 100 linhas do arquivo de log de erro do uWSGI:
  /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log
  ou outro caminho onde o STDERR da aplicação Python é capturado.
```

### Passo 5 — Analisar o log recebido

| Erro no log | Causa | Solução |
|---|---|---|
| `cannot import name 'X' from 'langchain_core'` | Versão do LangChain/LangGraph incompatível | Ajustar `requirements.txt` com faixas `>=x.y,<x+1.0` |
| `No module named 'django'` | uWSGI apontando para módulo errado | Solicitar ao suporte alterar `module = passenger_wsgi:application` |
| `connection refused` / `could not connect` | PostgreSQL de produção inacessível | Verificar com suporte o DATABASE_URL no `.env` |
| `ModuleNotFoundError: No module named 'X'` | Pacote não instalado no virtualenv prod | Adicionar pacote ao `requirements.txt` e fazer push |

### Passo 6 — Restartar após correção
1. Fazer `git push origin main` com a correção
2. Acionar manualmente o workflow de produção no modo adequado
3. Aguardar o `healthz` web responder com sucesso
4. Validar MCP, se o deploy tiver reiniciado o runtime remoto

---

## 📦 REGRAS DE OURO PARA `requirements.txt`

```
# ✅ CERTO — faixa segura que tolera patches e evita versões yanked
langchain>=0.2.16,<0.3.0
langgraph>=0.2.16,<0.3.0
langchain-core>=0.2.43,<0.3.0

# ❌ ERRADO — pin exato pode ser "yanked" pelo mantenedor sem aviso
langgraph-checkpoint-postgres==1.0.12   ← NUNCA faça isso sem testar antes

# ❌ ERRADO — upgrade cego no CI destrói o ambiente de produção
pip install --upgrade langchain langgraph   ← PROIBIDO no deploy.yml
```

---

## 🛑 LIÇÕES APRENDIDAS — Incidente Fev/2026 (48h)

| # | Falha | Consequência | Regra Criada |
|---|---|---|---|
| 1 | `pip install --upgrade` no `deploy.yml` forçava atualização cega | LangChain quebrou compatibilidade causando `ImportError` | Remover `--upgrade` do CI. Apenas `pip install -r requirements.txt` |
| 2 | Versões do LangGraph pinadas com `==` sem verificar disponibilidade no pip do servidor | Versões 1.0.10, 1.0.11, 1.0.12 foram "yanked" e o pip falhou | Usar faixas `>=x.y,<x+1` em vez de pins exatos |
| 3 | `passenger_wsgi.py` não estava versionado no Git | Servidor continuou usando config Django mesmo após conversão para Flask | **`passenger_wsgi.py` é obrigatório na raiz do `app32/` e deve estar no Git** |
| 4 | Configuração do uWSGI (`module = django.core.wsgi`) nunca atualizada | Todos os deploys Flask falhavam silenciosamente com HTTP 500 | Alterar via suporte Configr: `module = passenger_wsgi:application` |
| 5 | Sem visibilidade de logs do servidor | Levou ~2 dias para isolar a causa | Solicitar logs imediatamente ao suporte no início de qualquer incidente |

---

## 📞 Contato Suporte Configr (Cloudez)

- **Portal:** https://painel.configr.com
- **Chamado para:** Alteração de `uwsgi.ini`, consulta de logs, restart de serviços de baixo nível
- **Informação necessária sempre:** Nome do app (`appgestaoversuscombr.45a4cd4b.configr.cloud`), ambiente (produção), tipo de request

---

*Documento mantido pelo @ARQUITETO. Atualizar após cada incidente de produção.*
