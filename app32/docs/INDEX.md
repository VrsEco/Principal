# 📚 Índice de Documentação - Governança do Projeto

**Bem-vindo ao sistema de governança do GestaoVersus!**

Este índice te ajuda a navegar por toda a documentação de governança do projeto.

---

## 🚀 Começando

### Se você é novo no projeto:

1. **Leia primeiro:** [TECH_STACK.md](governance/TECH_STACK.md) - Entenda as tecnologias que usamos
2. **Depois:** [ARCHITECTURE.md](governance/ARCHITECTURE.md) - Compreenda a arquitetura do sistema
3. **Em seguida:** [CODING_STANDARDS.md](governance/CODING_STANDARDS.md) - Aprenda nossos padrões
4. **Por fim:** [DEVELOPMENT_WORKFLOW.md](workflows/DEVELOPMENT_WORKFLOW.md) - Saiba como trabalhar

### Se você vai fazer uma feature:

1. Use o template: [feature_template.md](templates/feature_template.md)
2. Consulte: [API_STANDARDS.md](governance/API_STANDARDS.md) se criar APIs
3. Consulte: [DATABASE_STANDARDS.md](governance/DATABASE_STANDARDS.md) se alterar banco
4. Siga: [DEVELOPMENT_WORKFLOW.md](workflows/DEVELOPMENT_WORKFLOW.md)

### Se você vai corrigir um bug:

1. Use o template: [bugfix_template.md](templates/bugfix_template.md)
2. Consulte: [FORBIDDEN_PATTERNS.md](governance/FORBIDDEN_PATTERNS.md) para evitar anti-patterns
3. Siga: [DEVELOPMENT_WORKFLOW.md](workflows/DEVELOPMENT_WORKFLOW.md)

### Se você vai fazer deploy:

1. **OBRIGATÓRIO:** [DEPLOYMENT_CHECKLIST.md](workflows/DEPLOYMENT_CHECKLIST.md)

---

## 📁 Estrutura da Documentação

```
docs/
├── INDEX.md                          ← VOCÊ ESTÁ AQUI
│
├── governance/                       ← Regras e padrões
│   ├── TECH_STACK.md                ← Stack tecnológica aprovada
│   ├── ARCHITECTURE.md              ← Arquitetura do sistema
│   ├── CODING_STANDARDS.md          ← Padrões de código Python
│   ├── DATABASE_STANDARDS.md        ← Padrões de banco de dados
│   ├── API_STANDARDS.md             ← Padrões de APIs REST
│   ├── FORBIDDEN_PATTERNS.md        ← Anti-patterns proibidos
│   ├── DECISION_LOG.md              ← Log de decisões (ADR)
│   └── AI_INTEGRATION.md            ← Integração com múltiplas IAs
│
├── templates/                        ← Templates para documentar
│   ├── feature_template.md          ← Template de nova feature
│   ├── bugfix_template.md           ← Template de correção
│   └── module_template.md           ← Template de novo módulo
│
├── patterns/                         ← Padrões reutilizáveis
│   ├── PFPN_PADRAO_FORMULARIO.md    ← Padrão de formulário (visualização/edição)
│   └── PFPN_QUICK_START.md          ← Guia rápido PFPN (10 min)
│
├── workflows/                        ← Processos de trabalho
│   ├── DEVELOPMENT_WORKFLOW.md      ← Git flow, commits, PRs
│   └── DEPLOYMENT_CHECKLIST.md      ← Checklist de deploy
│
└── guides/                           ← Guias práticos
    └── CODEX_USAGE_GUIDE.md         ← Como usar OpenAI Codex
```

---

## 🎯 Documentos por Categoria

### 🛠️ Stack e Tecnologia

| Documento | O Que Contém | Quando Consultar |
|-----------|--------------|------------------|
| [TECH_STACK.md](governance/TECH_STACK.md) | Tecnologias aprovadas e proibidas | Antes de adicionar nova dependência |
| [DECISION_LOG.md](governance/DECISION_LOG.md) | Histórico de decisões técnicas | Entender por que escolhemos algo |
| [AI_INTEGRATION.md](governance/AI_INTEGRATION.md) | Como usar IAs (Cursor, Copilot, Codex, etc.) | Configurar assistente de IA |

### 🏗️ Arquitetura e Design

| Documento | O Que Contém | Quando Consultar |
|-----------|--------------|------------------|
| [ARCHITECTURE.md](governance/ARCHITECTURE.md) | Estrutura do sistema, camadas, módulos | Entender como tudo se conecta |
| [DATABASE_STANDARDS.md](governance/DATABASE_STANDARDS.md) | Padrões de tabelas, migrations, queries | Criar/modificar tabelas |
| [API_STANDARDS.md](governance/API_STANDARDS.md) | Padrões REST, endpoints, responses | Criar/modificar APIs |

### 💻 Código e Qualidade

| Documento | O Que Contém | Quando Consultar |
|-----------|--------------|------------------|
| [CODING_STANDARDS.md](governance/CODING_STANDARDS.md) | Estilo, nomenclatura, estrutura | Antes de escrever código |
| [FORBIDDEN_PATTERNS.md](governance/FORBIDDEN_PATTERNS.md) | O que NUNCA fazer | Antes de code review |

### 🔄 Processos e Workflows

| Documento | O Que Contém | Quando Consultar |
|-----------|--------------|------------------|
| [DEVELOPMENT_WORKFLOW.md](workflows/DEVELOPMENT_WORKFLOW.md) | Git flow, commits, PRs | Todo desenvolvimento |
| [DEPLOYMENT_CHECKLIST.md](workflows/DEPLOYMENT_CHECKLIST.md) | Checklist completo de deploy | Antes de CADA deploy |

### 📝 Templates

| Template | Para Que | Quando Usar |
|----------|----------|-------------|
| [feature_template.md](templates/feature_template.md) | Documentar nova feature | Ao criar feature |
| [bugfix_template.md](templates/bugfix_template.md) | Documentar correção de bug | Ao corrigir bug |
| [module_template.md](templates/module_template.md) | Documentar novo módulo | Ao criar módulo |

### 🎨 Padrões de Desenvolvimento

| Padrão | Para Que | Quando Usar |
|--------|----------|-------------|
| [PFPN](patterns/PFPN_PADRAO_FORMULARIO.md) | Formulário com modo visualização/edição | Criar formulários editáveis |
| [PFPN Quick Start](patterns/PFPN_QUICK_START.md) | Implementação rápida do PFPN | Aplicar padrão em ~10 min |

### 📖 Guias Práticos

| Guia | Para Que | Quando Usar |
|------|----------|-------------|
| [CODEX_USAGE_GUIDE.md](guides/CODEX_USAGE_GUIDE.md) | Tutorial completo de uso do Codex | Gerar código via IA/API |

---

## 🔍 Busca Rápida

### "Posso usar tecnologia X?"
→ [TECH_STACK.md](governance/TECH_STACK.md)

### "Como nomear variáveis/funções/classes?"
→ [CODING_STANDARDS.md](governance/CODING_STANDARDS.md)

### "Como criar uma tabela no banco?"
→ [DATABASE_STANDARDS.md](governance/DATABASE_STANDARDS.md)

### "Como criar uma API REST?"
→ [API_STANDARDS.md](governance/API_STANDARDS.md)

### "O que NUNCA devo fazer?"
→ [FORBIDDEN_PATTERNS.md](governance/FORBIDDEN_PATTERNS.md)

### "Como faço um commit?"
→ [DEVELOPMENT_WORKFLOW.md](workflows/DEVELOPMENT_WORKFLOW.md)

### "Como faço deploy?"
→ [DEPLOYMENT_CHECKLIST.md](workflows/DEPLOYMENT_CHECKLIST.md)

### "Por que escolhemos Flask ao invés de Django?"
→ [DECISION_LOG.md](governance/DECISION_LOG.md)

### "Como criar formulário com modo visualização/edição?"
→ [PFPN Quick Start](patterns/PFPN_QUICK_START.md)

---

## 🎓 Guias Passo-a-Passo

### 📝 Criar Nova Feature

```
1. Leia: feature_template.md
2. Crie branch: feature/nome
3. Desenvolva seguindo: CODING_STANDARDS.md
4. Se criar API: consulte API_STANDARDS.md
5. Se criar tabelas: consulte DATABASE_STANDARDS.md
6. Adicione testes (cobertura > 80%)
7. Siga: DEVELOPMENT_WORKFLOW.md para PR
8. Deploy com: DEPLOYMENT_CHECKLIST.md
```

### 🐛 Corrigir Bug

```
1. Leia: bugfix_template.md
2. Crie branch: bugfix/nome
3. Investigue e documente causa raiz
4. Corrija seguindo: CODING_STANDARDS.md
5. Adicione teste que reproduz bug
6. Verifique: FORBIDDEN_PATTERNS.md
7. Siga: DEVELOPMENT_WORKFLOW.md para PR
8. Se crítico: hotfix via DEPLOYMENT_CHECKLIST.md
```

### 🚀 Fazer Deploy

```
1. OBRIGATÓRIO: DEPLOYMENT_CHECKLIST.md
2. Testes locais OK
3. Staging OK
4. Comunicar time
5. Backup do banco
6. Deploy
7. Monitorar 2h
8. Acompanhar 1 semana
```

### 🧩 Criar Novo Módulo

```
1. Leia: module_template.md
2. Consulte: ARCHITECTURE.md (estrutura de blueprints)
3. Crie estrutura em modules/nome/
4. Registre blueprint em app_pev.py
5. Crie models seguindo: DATABASE_STANDARDS.md
6. Crie APIs seguindo: API_STANDARDS.md
7. Adicione testes (cobertura > 80%)
8. Documente em README do módulo
```

---

## ⚡ Comandos Úteis

### Verificar Padrões

```bash
# Formatar código
black .

# Linting
flake8

# Testes
pytest

# Testes de governança
pytest tests/governance/

# Cobertura
pytest --cov=.
```

### Git

```bash
# Criar branch de feature
git checkout -b feature/nome

# Commit seguindo padrão
git commit -m "feat(module): descrição"

# Atualizar branch
git rebase main
```

### Database

```bash
# Criar migration
flask db migrate -m "descrição"

# Aplicar migrations
flask db upgrade

# Testar rollback
flask db downgrade
```

---

## 🚫 Checklist Rápido - O Que NUNCA Fazer

- [ ] ❌ Commitar direto na main
- [ ] ❌ Credenciais no código
- [ ] ❌ SQL injection (usar ORM)
- [ ] ❌ Senhas sem hash
- [ ] ❌ GET para modificar dados
- [ ] ❌ Rotas sem `@login_required`
- [ ] ❌ Queries sem paginação
- [ ] ❌ Bare `except:`
- [ ] ❌ `print()` para debug (usar `logger`)
- [ ] ❌ Tipos PostgreSQL específicos (JSONB, ARRAY)
- [ ] ❌ Deploy sem backup do banco
- [ ] ❌ Deploy sexta à tarde

**Mais detalhes:** [FORBIDDEN_PATTERNS.md](governance/FORBIDDEN_PATTERNS.md)

---

## 📊 Arquivos de Configuração

### Raiz do Projeto

| Arquivo | Propósito | Link |
|---------|-----------|------|
| `.cursorrules` | Regras para Cursor AI | [.cursorrules](../.cursorrules) |
| `requirements.txt` | Dependências Python | [requirements.txt](../requirements.txt) |
| `.gitignore` | Arquivos ignorados pelo Git | [.gitignore](../.gitignore) |
| `.env.example` | Exemplo de variáveis de ambiente | [.env.example](../.env.example) |

### Testes

| Arquivo | Propósito |
|---------|-----------|
| `tests/governance/test_code_standards.py` | Testes automatizados de padrões |
| `pytest.ini` | Configuração do pytest |
| `.coveragerc` | Configuração de cobertura |

---

## 🤝 Contribuindo

### Para Atualizar a Governança

1. **Propor mudança:**
   - Abrir issue com label "governance"
   - Descrever problema e solução proposta
   - Discutir com time

2. **Implementar:**
   - Criar branch `docs/nome-mudanca`
   - Atualizar documento(s) relevante(s)
   - Atualizar este INDEX.md se necessário
   - Abrir PR

3. **Aprovar:**
   - Tech Lead deve aprovar
   - Merge após aprovação

### Para Reportar Problema

1. Abrir issue descrevendo:
   - Qual documento
   - Qual seção
   - Qual problema
   - Sugestão de correção

---

## 📞 Dúvidas?

### Não encontrou o que procurava?

1. Use o índice de busca rápida acima
2. Procure no [DECISION_LOG.md](governance/DECISION_LOG.md)
3. Pergunte no canal #tech do Slack
4. Abra issue com label "question"

### Documentação Desatualizada?

1. Abra issue com label "documentation"
2. Ou faça PR corrigindo diretamente

---

## 📈 Estatísticas

**Total de Documentos:** 14  
**Última Atualização:** 23/10/2025  
**Versão:** 1.1

### Documentos por Categoria

- **Governança:** 7 documentos
- **Templates:** 3 documentos
- **Padrões:** 2 documentos (PFPN)
- **Workflows:** 2 documentos
- **Configuração:** 1 arquivo (.cursorrules)
- **Testes:** 1 arquivo (test_code_standards.py)

---

## ✅ Status dos Documentos

| Documento | Status | Última Revisão |
|-----------|--------|----------------|
| TECH_STACK.md | ✅ Ativo | 18/10/2025 |
| ARCHITECTURE.md | ✅ Ativo | 18/10/2025 |
| CODING_STANDARDS.md | ✅ Ativo | 18/10/2025 |
| DATABASE_STANDARDS.md | ✅ Ativo | 18/10/2025 |
| API_STANDARDS.md | ✅ Ativo | 18/10/2025 |
| FORBIDDEN_PATTERNS.md | ✅ Ativo | 18/10/2025 |
| DECISION_LOG.md | ✅ Ativo | 23/10/2025 |
| PFPN_PADRAO_FORMULARIO.md | ✅ Ativo | 23/10/2025 |
| PFPN_QUICK_START.md | ✅ Ativo | 23/10/2025 |
| DEVELOPMENT_WORKFLOW.md | ✅ Ativo | 18/10/2025 |
| DEPLOYMENT_CHECKLIST.md | ✅ Ativo | 18/10/2025 |
| .cursorrules | ✅ Ativo | 18/10/2025 |

---

## 🗓️ Calendário de Revisões

### Mensal
- [ ] TECH_STACK.md (dia 1º)
- [ ] Verificar dependências desatualizadas

### Trimestral
- [ ] ARCHITECTURE.md
- [ ] CODING_STANDARDS.md
- [ ] DATABASE_STANDARDS.md
- [ ] API_STANDARDS.md
- [ ] FORBIDDEN_PATTERNS.md
- [ ] DEVELOPMENT_WORKFLOW.md
- [ ] DEPLOYMENT_CHECKLIST.md

### Contínuo
- [ ] DECISION_LOG.md (a cada decisão importante)

---

## 🎉 Bem-Vindo!

Este sistema de governança foi criado para:
- **Facilitar** o desenvolvimento
- **Padronizar** o código
- **Prevenir** problemas comuns
- **Documentar** decisões
- **Onboarding** de novos membros

**Use-o, contribua com ele, e ajude a mantê-lo atualizado!**

---

**Responsável pela governança:** Tech Lead  
**Contribuidores:** Todo o time de desenvolvimento  
**Próxima revisão geral:** Trimestral



