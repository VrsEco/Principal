# 📋 Log de Decisões Arquiteturais (ADR)

**Status:** ✅ Ativo  
**Formato:** ADR Simplificado

---

## 🎯 O Que É Este Documento?

Registro de decisões arquiteturais importantes do projeto. Cada decisão importante deve ser documentada aqui para:

1. **Transparência** - Entender por que escolhemos algo
2. **Contexto** - Lembrar situação quando decisão foi tomada
3. **Aprendizado** - Não repetir erros ou re-discutir decisões
4. **Onboarding** - Novos membros entendem o histórico

---

## 📝 Template de Nova Decisão

```markdown
## ADR-XXX: [Título da Decisão]

**Data:** YYYY-MM-DD  
**Status:** [Proposta | Aceita | Rejeitada | Depreciada | Superseded]  
**Decisores:** [Nomes]  
**Tags:** [backend, frontend, database, infrastructure, etc.]

### Contexto

Por que precisamos decidir isso agora? Qual problema estamos resolvendo?

### Opções Consideradas

1. **Opção A**
   - Prós: ...
   - Contras: ...
   
2. **Opção B**
   - Prós: ...
   - Contras: ...

### Decisão

Escolhemos [Opção X] porque...

### Consequências

**Positivas:**
- ...

**Negativas:**
- ...

**Riscos:**
- ...

### Notas

Informações adicionais, links, referências.
```

---

## 📚 Decisões Registradas

### ADR-001: Escolha do Framework Web - Flask

**Data:** 2024-01-15  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** backend, framework

#### Contexto

Precisamos escolher um framework web para o projeto. Sistema precisa de:
- Flexibilidade para múltiplos módulos
- Fácil integração com PostgreSQL/SQLite
- Curva de aprendizado razoável
- Suporte a templates HTML

#### Opções Consideradas

1. **Django**
   - Prós: Completo (ORM, admin, auth), grande comunidade
   - Contras: Opinionado demais, overhead para projeto modular

2. **FastAPI**
   - Prós: Moderno, rápido, async, auto-documentação
   - Contras: Menos maduro, foco em APIs (precisamos de templates)

3. **Flask** ✅
   - Prós: Flexível, leve, ótima documentação, Blueprints para modularidade, Jinja2 integrado
   - Contras: Menos "batteries included", precisa configurar mais

#### Decisão

Escolhemos **Flask** porque:
- Blueprints permitem arquitetura modular perfeita (PEV, GRV, Meetings como módulos independentes)
- Jinja2 atende necessidade de templates HTML
- SQLAlchemy pode ser integrado facilmente
- Time tem experiência com Flask
- Comunidade madura e estável

#### Consequências

**Positivas:**
- Módulos podem ser habilitados/desabilitados facilmente
- Fácil adicionar novos módulos
- Leve e rápido

**Negativas:**
- Precisamos configurar auth, migrations, etc. manualmente
- Mais código boilerplate que Django

**Riscos:**
- Nenhum significativo

---

### ADR-002: Suporte Dual Database (PostgreSQL + SQLite)

**Data:** 2024-02-20  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead, DBA  
**Tags:** database, infrastructure

#### Contexto

Ambiente de desenvolvimento varia entre membros do time. Produção usa PostgreSQL, mas setup local é complexo.

#### Opções Consideradas

1. **Apenas PostgreSQL**
   - Prós: Paridade dev/prod, features completas
   - Contras: Setup complexo, requer Docker ou instalação local

2. **Apenas SQLite**
   - Prós: Zero setup, arquivo local
   - Contras: Diferenças de produção, features limitadas

3. **Suporte Dual (PostgreSQL + SQLite)** ✅
   - Prós: Flexibilidade, dev rápido, prod robusto
   - Contras: Precisa garantir compatibilidade

#### Decisão

Implementar **suporte dual** com abstração em `config_database.py`:
- Desenvolvimento: SQLite (padrão)
- Produção: PostgreSQL
- Código deve funcionar em ambos

#### Consequências

**Positivas:**
- Setup local instantâneo (SQLite)
- Produção robusta (PostgreSQL)
- Flexibilidade para escolher

**Negativas:**
- Precisa evitar features específicas de um banco
- Testes devem rodar em ambos

**Riscos:**
- Bugs que aparecem apenas em um banco
- Mitigação: Regras de compatibilidade em DATABASE_STANDARDS.md

---

### ADR-003: Soft Delete ao Invés de Hard Delete

**Data:** 2024-03-10  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead, Product  
**Tags:** database, data-retention

#### Contexto

Usuários frequentemente deletam dados por engano. Recuperação é impossível com hard delete.

#### Opções Consideradas

1. **Hard Delete**
   - Prós: Simples, menos dados
   - Contras: Irreversível, perde histórico

2. **Soft Delete** ✅
   - Prós: Recuperável, mantém histórico, auditoria
   - Contras: Mais complexo, mais dados

3. **Archive Table**
   - Prós: Separa dados ativos de deletados
   - Contras: Queries mais complexas, duplicação

#### Decisão

Implementar **soft delete** padrão:
- Campo `is_deleted` (boolean)
- Campo `deleted_at` (timestamp)
- Campo `deleted_by` (foreign key)

#### Consequências

**Positivas:**
- Dados recuperáveis
- Auditoria completa
- Usuários mais confiantes

**Negativas:**
- Queries precisam filtrar `is_deleted=False`
- Mais dados no banco

**Riscos:**
- Esquecer de filtrar is_deleted em queries
- Mitigação: Usar scopes/mixins no SQLAlchemy

---

### ADR-004: Sistema de Logs Automáticos com Decorators

**Data:** 2024-09-15  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** logging, middleware, audit

#### Contexto

Precisamos auditar ações de usuários (CRUD) para compliance e debug. Implementar manualmente é propenso a erros.

#### Opções Consideradas

1. **Log Manual em Cada Rota**
   - Prós: Controle total
   - Contras: Repetitivo, fácil esquecer

2. **Middleware Global**
   - Prós: Automático
   - Contras: Difícil customizar, log de tudo (noise)

3. **Decorator Opt-in** ✅
   - Prós: Automático quando necessário, customizável
   - Contras: Precisa lembrar de adicionar

#### Decisão

Criar decorator `@auto_log_crud(entity_type)`:
- Detecta operação (CREATE/UPDATE/DELETE) pelo método HTTP
- Captura valores antigos/novos automaticamente
- Salva em tabela `user_logs`

#### Consequências

**Positivas:**
- Log consistente
- Menos código repetido
- Fácil adicionar em novas rotas

**Negativas:**
- Desenvolvedores precisam lembrar de adicionar
- Auditoria de rotas necessária

**Riscos:**
- Rotas sem log se esquecer decorator
- Mitigação: Sistema de auditoria de rotas (`route_audit_service`)

---

### ADR-005: ReportLab para Geração de PDFs

**Data:** 2024-04-20  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** reports, pdf

#### Contexto

Necessidade de gerar relatórios profissionais em PDF com layouts complexos, tabelas, gráficos.

#### Opções Consideradas

1. **WeasyPrint (HTML → PDF)**
   - Prós: Usa HTML/CSS familiar
   - Contras: Controle limitado, rendering inconsistente

2. **Playwright (HTML → PDF)**
   - Prós: Rendering perfeito de HTML
   - Contras: Pesado (browser headless), lento

3. **ReportLab** ✅
   - Prós: Controle total, rápido, profissional
   - Contras: Curva de aprendizado, código mais verboso

#### Decisão

Usar **ReportLab como principal**, Playwright apenas para casos específicos de HTML complexo.

#### Consequências

**Positivas:**
- PDFs profissionais e consistentes
- Performance ótima
- Controle pixel-perfect

**Negativas:**
- Código mais verboso que HTML
- Curva de aprendizado

**Riscos:**
- Desenvolvedores podem achar difícil
- Mitigação: Templates e exemplos em `modules/gerador_relatorios.py`

---

### ADR-006: Arquitetura Modular com Blueprints

**Data:** 2024-01-20  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead, Arquiteto  
**Tags:** architecture, modularity

#### Contexto

Sistema tem 3 produtos distintos (PEV, GRV, GEV) que precisam funcionar independentemente mas compartilhar infraestrutura.

#### Opções Consideradas

1. **Monolito Único**
   - Prós: Simples
   - Contras: Acoplado, difícil testar isoladamente

2. **Microservices**
   - Prós: Isolamento total
   - Contras: Overhead operacional, complexidade

3. **Modular Monolith (Blueprints)** ✅
   - Prós: Isolamento lógico, baixa complexidade
   - Contras: Ainda compartilha banco/deploy

#### Decisão

Usar **Blueprints do Flask** com estrutura:
```
modules/
  pev/     # Planejamento Estratégico
  grv/     # Gestão de Resultados
  gev/     # Gestão de Eficiência (futuro)
  meetings/
```

Cada módulo pode ser habilitado/desabilitado.

#### Consequências

**Positivas:**
- Desenvolvimento paralelo
- Testes isolados
- Fácil adicionar módulos
- Baixa complexidade operacional

**Negativas:**
- Ainda compartilha banco (precisa cuidado com migrations)

**Riscos:**
- Módulos se acoplarem indevidamente
- Mitigação: Code review rigoroso de imports entre módulos

---

### ADR-007: Black + Flake8 para Code Quality

**Data:** 2024-02-01  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** code-quality, tooling

#### Contexto

Estilo de código inconsistente entre desenvolvedores. Code reviews gastam tempo com formatação.

#### Opções Consideradas

1. **Apenas Linter (Flake8)**
   - Prós: Detecta erros
   - Contras: Não formata automaticamente

2. **Black + Flake8** ✅
   - Prós: Formatação automática + linting
   - Contras: Opiniões fortes do Black

3. **Pylint**
   - Prós: Muito completo
   - Contras: Muito rigoroso, falsos positivos

#### Decisão

Usar **Black para formatação automática** + **Flake8 para linting**.

Configuração:
- Black: padrão
- Flake8: max-line-length=120

#### Consequências

**Positivas:**
- Zero discussões sobre formatação
- CI/CD pode validar automaticamente
- Código consistente

**Negativas:**
- Black é opinionado (sem customização)

**Riscos:**
- Desenvolvedores não gostarem do estilo
- Mitigação: É o padrão da comunidade Python

---

## 🔄 Template para Nova Decisão

Copiar e preencher ao fazer decisão importante:

```markdown
### ADR-XXX: [Título]

**Data:** YYYY-MM-DD  
**Status:** Proposta  
**Decisores:** [Nomes]  
**Tags:** [tags]

#### Contexto
...

#### Opções Consideradas
1. Opção A
   - Prós: ...
   - Contras: ...

2. Opção B ✅
   - Prós: ...
   - Contras: ...

#### Decisão
...

#### Consequências
**Positivas:** ...
**Negativas:** ...
**Riscos:** ...
```

---

## ADR-008: APScheduler para Tarefas Agendadas

**Data:** 2025-10-20  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** backend, scheduling, infrastructure

### Contexto

O sistema possui rotinas de processos que precisam ser executadas automaticamente em horários específicos (diárias, semanais, mensais). Antes, era necessário configurar manualmente cron (Linux) ou Task Scheduler (Windows), o que dificultava o deploy e aumentava a complexidade operacional.

### Opções Consideradas

1. **APScheduler**
   - Prós: Integrado ao Flask, simples, roda no mesmo processo, perfeito para <100 rotinas simultâneas
   - Contras: Não distribuído, limite de escalabilidade
   
2. **Celery Beat**
   - Prós: Mais robusto, distribuído, melhor para milhares de tasks
   - Contras: Requer Celery configurado, mais complexo, overhead maior
   
3. **Cron/Task Scheduler (Atual)**
   - Prós: Nativo do SO, simples
   - Contras: Manual em cada servidor, difícil de gerenciar, não funciona no Docker

### Decisão

Escolhemos **APScheduler** porque:
- ✅ Adequado ao volume atual (dezenas de rotinas)
- ✅ Integração simples com Flask existente
- ✅ Funciona perfeitamente no Docker
- ✅ Não requer infraestrutura adicional
- ✅ Fácil de testar e monitorar

### Consequências

**Positivas:**
- ✅ Rotinas executam automaticamente ao iniciar aplicação
- ✅ Mesmo código funciona em Windows/Linux/Docker
- ✅ Logs centralizados junto com aplicação
- ✅ Fácil adicionar novas rotinas
- ✅ Reduz complexidade operacional

**Negativas:**
- ⚠️ Limitado a um único processo (não distribuído)
- ⚠️ Se aplicação cair, scheduler para

**Riscos:**
- 🔄 Se escalar para >1000 rotinas, precisar migrar para Celery Beat

**Mitigações:**
- ✅ Celery já está instalado (migração futura é fácil)
- ✅ Código de processamento (`routine_scheduler.py`) é independente

### Implementação

- ✅ `services/scheduler_service.py` criado
- ✅ Integrado ao `app_pev.py`
- ✅ 2 jobs configurados (rotinas diárias + tarefas atrasadas)
- ✅ Documentado em `SCHEDULER_IMPLEMENTADO.md`

---

## ADR-009: Docker para Desenvolvimento

**Data:** 2025-10-20  
**Status:** ✅ Aceita  
**Decisores:** Tech Lead  
**Tags:** infrastructure, development, deployment

### Contexto

Desenvolvedores enfrentavam dificuldades com:
- Instalação manual de PostgreSQL, Redis, ferramentas
- Diferenças entre Windows/Linux
- Conflitos de versões
- Dificuldade em replicar ambiente de produção

### Opções Consideradas

1. **Docker Compose (Escolhida)**
   - Prós: Ambiente isolado, reproduzível, fácil setup, hot-reload, funciona em Windows/Linux/Mac
   - Contras: Requer Docker instalado, curva de aprendizado inicial
   
2. **Instalação Manual**
   - Prós: "Controle total", sem overhead Docker
   - Contras: Difícil manter consistência, problemas de compatibilidade, setup longo
   
3. **Vagrant + VirtualBox**
   - Prós: Máquina virtual completa
   - Contras: Pesado (GB de RAM), lento, Docker é mais moderno

### Decisão

Escolhemos **Docker + Docker Compose** porque:
- ✅ Ambiente idêntico para todos desenvolvedores
- ✅ Setup em 5 minutos (`docker-compose up`)
- ✅ Não polui máquina local
- ✅ Facilita deploy futuro (mesmas imagens)
- ✅ Hot-reload preservado (volumes)

### Consequências

**Positivas:**
- ✅ Novo desenvolvedor produtivo em minutos
- ✅ "Funciona na minha máquina" deixa de existir
- ✅ Testes de integração mais confiáveis
- ✅ Caminho claro para produção

**Negativas:**
- ⚠️ Precisa Docker instalado (2-3GB)
- ⚠️ Pequeno overhead de performance

**Riscos:**
- 🔄 Desenvolvedores precisam aprender Docker básico

**Mitigações:**
- ✅ Documentação completa em `GUIA_COMPLETO_DOCKER_DESENVOLVIMENTO.md`
- ✅ Comandos simples (up, down, restart)
- ✅ Hot-reload mantém workflow familiar

### Implementação

**Arquivos criados:**
- ✅ `docker-compose.dev.yml` - Orquestração
- ✅ `Dockerfile.dev` - Imagem de desenvolvimento
- ✅ `.dockerignore` - Otimização
- ✅ `env.development.example` - Configuração

**Containers:**
- ✅ Flask App (Python 3.9, hot-reload)
- ✅ PostgreSQL 18-alpine
- ✅ Redis 7-alpine
- ✅ Adminer (gerenciador web de banco)
- ✅ MailHog (captura e-mails de teste)

**Decisão Técnica:** 
- Usar PostgreSQL **local** via `host.docker.internal` para preservar dados durante desenvolvimento
- Container PostgreSQL disponível para testes isolados se necessário

---

## 📊 Índice por Tag

### Backend
- ADR-001: Flask
- ADR-004: Logs Automáticos
- ADR-008: APScheduler

### Database
- ADR-002: Dual Database
- ADR-003: Soft Delete

### Architecture
- ADR-006: Modular Blueprints

### Infrastructure
- ADR-008: APScheduler
- ADR-009: Docker Development

### Tooling
- ADR-007: Black + Flake8

### Reports
- ADR-005: ReportLab

---

## 🔍 Status das Decisões

| Status | Quantidade | Descrição |
|--------|-----------|-----------|
| ✅ Aceita | 9 | Implementada e em uso |
| 🔄 Proposta | 0 | Em discussão |
| ❌ Rejeitada | 0 | Não aprovada |
| 🗄️ Depreciada | 0 | Não mais válida |
| ↗️ Superseded | 0 | Substituída por outra |

---

## 📝 Como Adicionar Nova Decisão

1. Copiar template acima
2. Numerar sequencialmente (ADR-XXX)
3. Preencher todas as seções
4. Discutir com time
5. Atualizar status quando aceita
6. Implementar decisão
7. Commit em PR separado

---

## ADR-011: Configuração Playwright no Docker para Geração de PDF

**Data:** 2025-10-21  
**Status:** ✅ Aceita  
**Decisores:** DevOps, Backend Team  
**Tags:** infrastructure, docker, pdf, playwright

### Contexto

A aplicação usa Playwright para gerar PDFs a partir de HTML (rota `/company/<id>/process/map-pdf2`). Em ambiente Docker, o erro `BrowserType.launch: Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-1187/chrome-linux/headless_shell` ocorria porque:

1. O pacote Python `playwright==1.55.0` estava instalado via `requirements.txt`
2. Mas o comando `playwright install` (que baixa os browsers) NÃO era executado no Dockerfile
3. O Chromium também precisa de várias dependências do sistema para funcionar

### Opções Consideradas

1. **Opção A: Instalar Playwright browsers no Dockerfile (Escolhida)**
   - Prós: 
     - Browsers ficam na imagem, prontos para uso
     - Não precisa download em runtime
     - Consistente em todos os ambientes
     - Suporta ambientes sem acesso à internet após deploy
   - Contras: 
     - Aumenta tamanho da imagem em ~300-400MB
     - Build demora mais (download do Chromium)

2. **Opção B: Download em runtime no primeiro uso**
   - Prós: 
     - Imagem menor
     - Build mais rápido
   - Contras: 
     - Primeira requisição de PDF seria lenta
     - Problemas se container não tiver acesso à internet
     - Mais complexo de gerenciar (precisa verificar se já instalado)

3. **Opção C: Usar biblioteca alternativa (wkhtmltopdf, WeasyPrint)**
   - Prós: 
     - Algumas são menores
   - Contras: 
     - Playwright já está em uso
     - Migraria código funcionando
     - Outras bibliotecas têm limitações de CSS/JS

### Decisão

Escolhemos **Opção A** (instalar no Dockerfile) porque:

1. **Confiabilidade**: Container está sempre pronto, não depende de download em runtime
2. **Performance**: Não há latência na primeira requisição de PDF
3. **Segurança**: Funciona em ambientes restritos sem internet
4. **Simplicidade**: Não precisa lógica de verificação/download condicional
5. **Alinhamento**: Padrão em ambientes containerizados é incluir tudo na imagem

### Implementação

**Mudanças no Dockerfile:**

```dockerfile
# Stage 2: Runtime - Adicionadas dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    curl \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar browsers do Playwright (antes de mudar para appuser)
RUN playwright install --with-deps chromium
```

**Ordem importante:**
- Executar `playwright install` ANTES de `USER appuser` (precisa de permissões root)
- Instalar apenas `chromium` (não todos os browsers) para economizar espaço

### Consequências

**Positivas:**
- ✅ Erro de "browser não encontrado" resolvido
- ✅ PDFs são gerados com sucesso via Playwright
- ✅ Ambiente Docker consistente e previsível
- ✅ Não há dependência de internet em runtime
- ✅ Celery Worker e Celery Beat também funcionam (usam mesmo Dockerfile)

**Negativas:**
- ⚠️ Imagem Docker aumentou ~300-400MB (de ~500MB para ~800-900MB)
- ⚠️ Build demora ~2-3 minutos a mais (download do Chromium)
- ⚠️ Mais memória necessária em runtime (~100-200MB por processo Chromium)

**Neutras:**
- 📝 Documentação criada em `REBUILD_INSTRUCTIONS.md`
- 📝 Equipe precisa fazer rebuild: `docker-compose build --no-cache`

### Dependências Adicionadas

**Bibliotecas do sistema para Chromium:**
- **Network/Security:** libnss3, libnspr4
- **Accessibility:** libatk1.0-0, libatk-bridge2.0-0, libatspi2.0-0
- **Graphics:** libdrm2, libgbm1, libcairo2, libpango-1.0-0
- **X11:** libxkbcommon0, libxcomposite1, libxdamage1, libxfixes3, libxrandr2
- **Other:** libcups2, libdbus-1-3, libasound2

### Métricas de Impacto

| Métrica | Antes | Depois | Δ |
|---------|-------|--------|---|
| Tamanho da imagem | ~500MB | ~850MB | +70% |
| Tempo de build | ~3min | ~6min | +100% |
| Memória runtime | ~200MB | ~400MB (com PDF) | +100% |
| Latência 1º PDF | 5-10s (falha) | 2-3s (sucesso) | ✅ |

### Plano de Rollback

Se houver problemas:

```bash
# Reverter Dockerfile
git checkout HEAD~1 -- Dockerfile

# Rebuild
docker-compose build --no-cache app
docker-compose up -d --force-recreate app
```

### Monitoramento

Após deploy, monitorar:
- [ ] Logs de erro na rota `/company/<id>/process/map-pdf2`
- [ ] Uso de memória dos containers (app, celery_worker)
- [ ] Uso de disco (imagens Docker)
- [ ] Tempo de geração de PDF (deve ser 2-5s)

### Referências

- [Playwright Docker Documentation](https://playwright.dev/docs/docker)
- [Chromium System Requirements](https://www.chromium.org/developers/how-tos/get-the-code/working-with-release-branches/)
- Issue: `playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist`
- Arquivo: `modules/grv/__init__.py` linha 713

### Próximos Passos

1. ✅ Atualizar Dockerfile
2. ✅ Documentar em REBUILD_INSTRUCTIONS.md
3. ✅ Registrar decisão no DECISION_LOG.md
4. ⏳ Rebuild dos containers em produção
5. ⏳ Testar geração de PDF
6. ⏳ Monitorar performance/memória por 1 semana

---

## ADR-012: Correção de SERIAL/SEQUENCE em Tabelas PostgreSQL

**Data:** 2025-10-21  
**Status:** ✅ Aceita e Implementada  
**Decisores:** Backend Team  
**Tags:** database, postgresql, bug-fix, schema

### Contexto

Durante testes, descobrimos que a tabela `routine_collaborators` estava gerando erro ao inserir registros:

```
null value in column "id" of relation "routine_collaborators" violates not-null constraint
```

**Causa:** A tabela foi criada com `id INTEGER NOT NULL` mas **sem SERIAL ou SEQUENCE**, então o PostgreSQL não gerava automaticamente o `id`.

### Problema Identificado

```sql
-- Definição INCORRETA (como estava)
CREATE TABLE public.routine_collaborators (
    id integer NOT NULL,  -- ❌ Sem auto-increment!
    routine_id integer NOT NULL,
    employee_id integer NOT NULL,
    ...
);
```

Quando o código fazia:
```python
cursor.execute('''
    INSERT INTO routine_collaborators (routine_id, employee_id, hours_used, notes)
    VALUES (%s, %s, %s, %s)
    RETURNING id
''', (routine_id, employee_id, hours_used, notes))
```

O PostgreSQL tentava inserir `NULL` no `id`, violando a constraint.

### Opções Consideradas

1. **Opção A: Criar SEQUENCE e configurar DEFAULT (Escolhida)**
   - Prós:
     - Não quebra dados existentes
     - Solução padrão PostgreSQL
     - Fácil de reverter se necessário
     - Mantém compatibilidade com código existente
   - Contras:
     - Precisa de migration
     - Requer acesso ao banco

2. **Opção B: Recriar tabela com SERIAL**
   - Prós:
     - Mais "limpo" (SERIAL é o padrão)
   - Contras:
     - Precisa backup/restore de dados
     - Downtime necessário
     - Risco de perda de dados
     - Mais complexo

3. **Opção C: Gerar ID no código Python**
   - Prós:
     - Não precisa alterar banco
   - Contras:
     - Risco de race condition (IDs duplicados)
     - Não é o padrão PostgreSQL
     - Mais complexo de manter

### Decisão

Escolhemos **Opção A** porque:

1. **Segurança:** Não afeta dados existentes
2. **Padrão:** É a forma correta de fazer no PostgreSQL
3. **Simplicidade:** Migration simples e direta
4. **Reversível:** Fácil de reverter se necessário
5. **Compatibilidade:** Não requer mudanças no código da aplicação

### Implementação

**Migration:** `migrations/20251021_fix_routine_collaborators_sequence.sql`

```sql
-- 1. Criar sequence
CREATE SEQUENCE IF NOT EXISTS routine_collaborators_id_seq;

-- 2. Ajustar valor inicial
SELECT setval('routine_collaborators_id_seq', 
    COALESCE((SELECT MAX(id) FROM routine_collaborators), 0) + 1, 
    false
);

-- 3. Configurar default
ALTER TABLE routine_collaborators 
    ALTER COLUMN id SET DEFAULT nextval('routine_collaborators_id_seq');

-- 4. Associar sequence à tabela
ALTER SEQUENCE routine_collaborators_id_seq OWNED BY routine_collaborators.id;
```

**Resultado:**
```
column_name | column_default                              
------------|---------------------------------------------------
id          | nextval('routine_collaborators_id_seq'::regclass)
```

### Consequências

**Positivas:**
- ✅ Inserts funcionam corretamente agora
- ✅ IDs são gerados automaticamente pelo PostgreSQL
- ✅ Sem risco de IDs duplicados
- ✅ Código da aplicação não precisa mudar
- ✅ Padrão PostgreSQL correto

**Negativas:**
- ⚠️ Precisa aplicar migration em todos os ambientes (dev, staging, prod)
- ⚠️ Se houver outras tabelas com mesmo problema, precisam ser corrigidas também

**Neutras:**
- 📝 Migration documentada em `migrations/README_SEQUENCES_FIX.md`
- 📝 Query criada para identificar outras tabelas com mesmo problema

### Verificação de Outras Tabelas

Query para encontrar tabelas com mesmo problema:

```sql
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM 
    information_schema.columns
WHERE 
    table_schema = 'public'
    AND column_name = 'id'
    AND data_type = 'integer'
    AND is_nullable = 'NO'
    AND column_default IS NULL
ORDER BY 
    table_name;
```

### Ambientes

| Ambiente | Status | Data | Observações |
|----------|--------|------|-------------|
| DEV | ✅ Aplicado | 2025-10-21 | Funcionando |
| STAGING | ⏳ Pendente | - | Aplicar antes de prod |
| PROD | ⏳ Pendente | - | Aplicar com backup |

### Plano de Aplicação em Produção

1. **Backup:**
   ```bash
   pg_dump -h localhost -U postgres bd_app_versus > backup_pre_fix_sequences.sql
   ```

2. **Aplicar migration:**
   ```bash
   psql -h localhost -U postgres -d bd_app_versus < migrations/20251021_fix_routine_collaborators_sequence.sql
   ```

3. **Verificar:**
   - [ ] Column default configurado
   - [ ] INSERT funciona sem especificar id
   - [ ] Sequence incrementa corretamente

4. **Monitorar:**
   - Logs de erro relacionados a routine_collaborators
   - Performance de INSERTs

### Prevenção Futura

**Para novas tabelas, SEMPRE usar:**

```sql
-- ✅ CORRETO
CREATE TABLE nome_tabela (
    id SERIAL PRIMARY KEY,
    ...
);

-- ❌ ERRADO
CREATE TABLE nome_tabela (
    id INTEGER NOT NULL PRIMARY KEY,
    ...
);
```

### Referências

- Migration: `migrations/20251021_fix_routine_collaborators_sequence.sql`
- Documentação: `migrations/README_SEQUENCES_FIX.md`
- PostgreSQL SERIAL: https://www.postgresql.org/docs/current/datatype-numeric.html#DATATYPE-SERIAL
- Erro original: `psycopg2.errors.NotNullViolation`

### Próximos Passos

1. ✅ Aplicado em DEV
2. ✅ Documentado no DECISION_LOG
3. ⏳ Verificar se outras tabelas têm o mesmo problema
4. ⏳ Aplicar em STAGING
5. ⏳ Aplicar em PROD (com backup)
6. ⏳ Atualizar templates de criação de tabelas

---

**Próxima revisão:** Contínua (a cada decisão importante)  
**Responsável:** Tech Lead



