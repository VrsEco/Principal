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

## 📊 Índice por Tag

### Backend
- ADR-001: Flask
- ADR-004: Logs Automáticos

### Database
- ADR-002: Dual Database
- ADR-003: Soft Delete

### Architecture
- ADR-006: Modular Blueprints

### Tooling
- ADR-007: Black + Flake8

### Reports
- ADR-005: ReportLab

---

## 🔍 Status das Decisões

| Status | Quantidade | Descrição |
|--------|-----------|-----------|
| ✅ Aceita | 7 | Implementada e em uso |
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

**Próxima revisão:** Contínua (a cada decisão importante)  
**Responsável:** Tech Lead



