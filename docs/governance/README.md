# 📖 Governança do Projeto GestaoVersus

**Versão:** 1.0  
**Data:** 18/10/2025  
**Status:** ✅ Ativo

---

## 🎯 O Que É Este Sistema?

Este é o **sistema de governança técnica** do projeto GestaoVersus. Ele define:

- ✅ **O QUE** usar (tecnologias aprovadas)
- ✅ **COMO** usar (padrões e convenções)
- ✅ **POR QUÊ** usamos (decisões documentadas)
- ❌ **O QUE NÃO** fazer (anti-patterns)

**Objetivo:** Evitar que o sistema vire uma "colcha de retalhos" com decisões inconsistentes.

---

## 🆚 Nossa Solução vs Proposta Original

### Proposta da Outra IA (Rejeitada)
```
/ai/
  CONSTITUTION.md
  SYSTEM_PROMPT.md
  ROUTING_POLICY.md    ← Para múltiplas IAs
  DEFINITION_OF_DONE.md
  STYLE_GUIDE.md
  CONTEXT_MAP.yaml
  FORBIDDEN_MOVES.md
  TEMPLATES/
  EVALS/
```

**Problemas:**
- ❌ Overhead excessivo para 1-2 devs
- ❌ Focado em múltiplas IAs (não é nosso caso)
- ❌ YAML adiciona dependência extra
- ❌ Ignora cultura de .md já existente

### Nossa Solução (Implementada) ✅
```
docs/
  governance/          ← Regras (7 arquivos .md)
  templates/           ← Templates (3 arquivos .md)
  workflows/           ← Processos (2 arquivos .md)
.cursorrules          ← Integração nativa Cursor
tests/governance/     ← Testes automatizados
```

**Vantagens:**
- ✅ Enxuto (apenas essencial)
- ✅ Integrado ao workflow (Cursor, pytest)
- ✅ Compatível com cultura existente (.md)
- ✅ Testável (testes automatizados)
- ✅ Incremental (cresce conforme necessário)
- ✅ Pragmático (foca em prevenir problemas reais)

---

## 📁 Estrutura Completa

### Governança (Regras e Padrões)
```
governance/
├── TECH_STACK.md           ← Stack aprovada + versões
├── ARCHITECTURE.md         ← Arquitetura do sistema
├── CODING_STANDARDS.md     ← Padrões Python
├── DATABASE_STANDARDS.md   ← Padrões de DB
├── API_STANDARDS.md        ← Padrões REST
├── FORBIDDEN_PATTERNS.md   ← Anti-patterns (NUNCA fazer)
└── DECISION_LOG.md         ← ADR (decisões)
```

### Templates (Documentação Padronizada)
```
templates/
├── feature_template.md     ← Nova feature
├── bugfix_template.md      ← Correção de bug
└── module_template.md      ← Novo módulo
```

### Workflows (Processos)
```
workflows/
├── DEVELOPMENT_WORKFLOW.md   ← Git flow, commits, PRs
└── DEPLOYMENT_CHECKLIST.md   ← Checklist de deploy
```

### Integração
```
.cursorrules               ← Regras para Cursor AI (raiz do projeto)
tests/governance/          ← Testes automatizados de padrões
```

---

## 🚀 Como Usar

### Para Novos Desenvolvedores

**Leitura obrigatória (nesta ordem):**

1. **[TECH_STACK.md](TECH_STACK.md)** (15 min)
   - Entenda o que usamos e por quê
   - Veja o que é proibido

2. **[ARCHITECTURE.md](ARCHITECTURE.md)** (20 min)
   - Compreenda a estrutura do projeto
   - Veja como os módulos se conectam

3. **[CODING_STANDARDS.md](CODING_STANDARDS.md)** (30 min)
   - Aprenda nosso estilo de código
   - Veja exemplos práticos

4. **[FORBIDDEN_PATTERNS.md](FORBIDDEN_PATTERNS.md)** (15 min)
   - **CRÍTICO:** O que NUNCA fazer
   - Evite problemas de segurança

5. **[../workflows/DEVELOPMENT_WORKFLOW.md](../workflows/DEVELOPMENT_WORKFLOW.md)** (20 min)
   - Aprenda nosso Git flow
   - Veja como fazer PRs

**Tempo total:** ~2 horas

### Para Criar Nova Feature

```
1. Use ../templates/feature_template.md
2. Consulte TECH_STACK.md (tecnologia permitida?)
3. Consulte API_STANDARDS.md (se criar API)
4. Consulte DATABASE_STANDARDS.md (se alterar DB)
5. Siga CODING_STANDARDS.md (ao escrever código)
6. Evite FORBIDDEN_PATTERNS.md
7. Siga ../workflows/DEVELOPMENT_WORKFLOW.md (PR)
```

### Para Corrigir Bug

```
1. Use ../templates/bugfix_template.md
2. Consulte FORBIDDEN_PATTERNS.md (causa provável?)
3. Siga CODING_STANDARDS.md (correção)
4. Siga ../workflows/DEVELOPMENT_WORKFLOW.md (PR)
```

### Para Fazer Deploy

```
1. OBRIGATÓRIO: ../workflows/DEPLOYMENT_CHECKLIST.md
```

### Para Adicionar Tecnologia

```
1. Verificar se não está em TECH_STACK.md (proibidas)
2. Preencher checklist em TECH_STACK.md
3. Documentar decisão em DECISION_LOG.md
4. Aguardar aprovação
```

---

## ⚡ Comandos Rápidos

### Verificar Conformidade

```bash
# Formatar código
black .

# Linting
flake8

# Testes
pytest

# Testes de governança (verifica padrões)
pytest tests/governance/

# Cobertura
pytest --cov=.
```

### Git (seguindo nossos padrões)

```bash
# Feature
git checkout -b feature/nome-descritivo
git commit -m "feat(module): descrição"

# Bugfix
git checkout -b bugfix/nome-descritivo
git commit -m "fix(module): descrição"

# Hotfix
git checkout -b hotfix/nome-descritivo
git commit -m "hotfix: descrição urgente"
```

---

## 🎓 Integração com Cursor AI

O arquivo **`.cursorrules`** (raiz do projeto) contém todas as regras para o Cursor AI seguir automaticamente.

**O que o Cursor AI sabe:**
- ✅ Stack aprovada
- ✅ Padrões de código
- ✅ Padrões de API
- ✅ Padrões de banco
- ✅ O que é proibido
- ✅ Como estruturar features

**Sempre que pedir ajuda ao Cursor, ele consultará automaticamente estas regras!**

---

## 🧪 Testes Automatizados

Execute para verificar se o código segue os padrões:

```bash
pytest tests/governance/test_code_standards.py -v
```

**O que é verificado:**
- ❌ Credenciais hardcoded
- ❌ print() statements (usar logger)
- ❌ Bare except (especificar exceção)
- ❌ SQL string concatenation
- ❌ import * (usar explícito)
- ❌ Classes não-PascalCase
- ❌ Tipos PostgreSQL específicos
- ❌ eval() ou exec()
- ❌ Logging de senhas

---

## 📊 Estatísticas

### Documentos Criados
- **Governança:** 7 documentos
- **Templates:** 3 documentos
- **Workflows:** 2 documentos
- **Configuração:** 1 arquivo (.cursorrules)
- **Testes:** 1 suite (test_code_standards.py)

**Total:** 14 arquivos

### Cobertura

| Área | Documentado |
|------|-------------|
| Stack Tecnológica | ✅ 100% |
| Arquitetura | ✅ 100% |
| Código Python | ✅ 100% |
| Banco de Dados | ✅ 100% |
| APIs REST | ✅ 100% |
| Segurança | ✅ 100% |
| Git Flow | ✅ 100% |
| Deploy | ✅ 100% |
| Templates | ✅ 100% |

---

## 🔄 Manutenção

### Responsabilidades

| Item | Frequência | Responsável |
|------|-----------|-------------|
| TECH_STACK.md | Mensal (dia 1º) | Tech Lead |
| Outros docs | Trimestral | Tech Lead |
| DECISION_LOG.md | Contínuo | Quem decide |
| Testes de padrões | A cada PR | CI/CD |

### Como Propor Mudança

1. Abrir issue com label "governance"
2. Descrever problema e solução
3. Discutir com time
4. Implementar via PR
5. Atualizar DECISION_LOG.md se decisão importante

---

## ✅ Checklist de Adoção

Para que a governança funcione, todos devem:

- [ ] Ler documentação obrigatória (TECH_STACK, ARCHITECTURE, CODING_STANDARDS, FORBIDDEN_PATTERNS)
- [ ] Configurar ferramentas (Black, Flake8, pytest)
- [ ] Usar templates ao criar features/bugs
- [ ] Seguir DEVELOPMENT_WORKFLOW.md
- [ ] Rodar testes de governança antes de PR
- [ ] Consultar documentos antes de decisões técnicas
- [ ] Documentar decisões importantes em DECISION_LOG.md

---

## 🎯 Benefícios Esperados

### Curto Prazo (1-2 meses)
- ✅ Código mais consistente
- ✅ Menos tempo em code review (padrões claros)
- ✅ Menos bugs por anti-patterns
- ✅ Onboarding mais rápido

### Médio Prazo (3-6 meses)
- ✅ Menos débito técnico
- ✅ Decisões mais rápidas (já documentadas)
- ✅ Menos retrabalho
- ✅ Mais confiança em mudanças

### Longo Prazo (6+ meses)
- ✅ Sistema escalável e mantível
- ✅ Time alinhado tecnicamente
- ✅ Cultura de qualidade estabelecida
- ✅ **Sistema NÃO vira colcha de retalhos**

---

## ❓ FAQ

**P: É obrigatório seguir tudo?**  
R: Sim para código em produção. Em protótipos pode flexibilizar (mas documente).

**P: E se eu discordar de algum padrão?**  
R: Ótimo! Abra issue com proposta de mudança e justificativa.

**P: Posso usar tecnologia X que não está aprovada?**  
R: Siga processo em TECH_STACK.md (justificar, documentar, aprovar).

**P: Isso não vai engessar o desenvolvimento?**  
R: Não. Governança previne problemas, não impede inovação. Sempre pode propor mudanças.

**P: Quanto tempo para adotar tudo?**  
R: Gradual. Comece com FORBIDDEN_PATTERNS (crítico) e DEVELOPMENT_WORKFLOW. Resto incremental.

**P: E se eu esquecer algum padrão?**  
R: Code review e testes automatizados vão pegar. É normal no início.

---

## 🔗 Links Úteis

- **[Índice Geral](../INDEX.md)** - Navegação completa
- **[Busca Rápida](../INDEX.md#-busca-rápida)** - Encontre documento por pergunta
- **[Guias Passo-a-Passo](../INDEX.md#-guias-passo-a-passo)** - Tutoriais práticos

---

## 📞 Contato

**Dúvidas sobre governança?**
- Slack: #tech
- Email: tech-lead@example.com
- Issue: label "governance" + "question"

**Propor mudança:**
- Issue: label "governance" + "proposal"

---

## 🎉 Conclusão

Este sistema de governança foi **projetado especificamente para o GestaoVersus**, considerando:

- ✅ Tamanho do time (1-2 devs principais)
- ✅ Stack atual (Python + Flask + PostgreSQL/SQLite)
- ✅ Cultura existente (documentação em .md)
- ✅ Ferramentas em uso (Cursor AI, pytest)
- ✅ Problemas reais que você enfrenta

**Não é uma solução genérica copiada da internet. É sua solução.**

Use-a, melhore-a, e mantenha seu sistema organizado e escalável! 🚀

---

**Criado em:** 18/10/2025  
**Por:** Time de Desenvolvimento + IA  
**Próxima revisão:** Trimestral (18/01/2026)



