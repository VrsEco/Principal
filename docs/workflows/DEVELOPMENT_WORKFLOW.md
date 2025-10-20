# 🔄 Workflow de Desenvolvimento

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório

---

## 🎯 Visão Geral

Este documento define o fluxo de trabalho padrão para desenvolvimento no projeto.

**Princípios:**
1. **Nunca commitar direto na main**
2. **Todo código passa por code review**
3. **Testes são obrigatórios**
4. **Documentação é parte da entrega**

---

## 🌿 Git Flow

### Branches Principais

```
main                 # Produção (sempre estável)
  ├── develop        # Desenvolvimento (integração)
  ├── staging        # Staging/Homologação
```

### Branches de Trabalho

```
feature/[nome]       # Novas features
bugfix/[nome]        # Correção de bugs
hotfix/[nome]        # Correções urgentes em produção
refactor/[nome]      # Refatorações
docs/[nome]          # Apenas documentação
```

**Convenção de nomes:**
- Usar `kebab-case`
- Ser descritivo
- Prefixar com tipo

**Exemplos:**
```
feature/user-authentication
feature/grv-indicators-module
bugfix/login-redirect-error
hotfix/critical-sql-injection
refactor/database-abstraction
docs/api-documentation
```

---

## 🚀 Fluxo Completo

### 1. Criar Branch

```bash
# Atualizar main
git checkout main
git pull origin main

# Criar branch
git checkout -b feature/nome-da-feature

# Ou a partir de develop
git checkout develop
git pull origin develop
git checkout -b feature/nome-da-feature
```

### 2. Desenvolver

```bash
# Fazer mudanças
# ... código ...

# Adicionar arquivos
git add .

# Commit (seguir convenção)
git commit -m "feat: adiciona autenticação de usuário"

# Push regularmente
git push origin feature/nome-da-feature
```

### 3. Manter Branch Atualizada

```bash
# Atualizar com main periodicamente
git checkout main
git pull origin main
git checkout feature/nome-da-feature
git merge main

# Ou usar rebase (preferido)
git rebase main

# Resolver conflitos se houver
# ... resolver ...
git add .
git rebase --continue
```

### 4. Preparar para PR

```bash
# Formatar código
black .

# Linting
flake8

# Rodar testes
pytest

# Verificar cobertura
pytest --cov

# Commit final se necessário
git add .
git commit -m "test: adiciona testes para autenticação"
git push origin feature/nome-da-feature
```

### 5. Criar Pull Request

**Via GitHub/GitLab:**
1. Abrir PR de `feature/nome` → `main` (ou `develop`)
2. Preencher template de PR
3. Adicionar labels apropriadas
4. Atribuir reviewers
5. Linkar issues relacionadas

### 6. Code Review

**Autor:**
- Responder comentários
- Fazer correções solicitadas
- Atualizar PR

**Revisor:**
- Verificar checklist de code review
- Testar localmente
- Aprovar ou solicitar mudanças

### 7. Merge

```bash
# Após aprovação
# Merge é feito via interface (GitHub/GitLab)
# Escolher "Squash and Merge" para PRs com muitos commits
# Ou "Merge Commit" para manter histórico

# Deletar branch após merge
git branch -d feature/nome-da-feature
git push origin --delete feature/nome-da-feature
```

---

## 📝 Convenção de Commits

### Formato

```
<tipo>(<escopo>): <descrição>

<corpo opcional>

<footer opcional>
```

### Tipos

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| `feat` | Nova feature | `feat(auth): adiciona login social` |
| `fix` | Bug fix | `fix(grv): corrige cálculo de indicador` |
| `docs` | Documentação | `docs(api): atualiza documentação de endpoints` |
| `style` | Formatação | `style: aplica black em todo projeto` |
| `refactor` | Refatoração | `refactor(db): melhora abstração de database` |
| `test` | Testes | `test(auth): adiciona testes unitários` |
| `chore` | Manutenção | `chore: atualiza dependências` |
| `perf` | Performance | `perf(query): otimiza query de projetos` |

### Exemplos Completos

```bash
# Feature simples
git commit -m "feat(grv): adiciona módulo de indicadores"

# Bug fix com descrição
git commit -m "fix(login): corrige redirect após login

Usuário estava sendo redirecionado para página errada após login.
Corrigido para redirecionar para /dashboard.

Fixes #123"

# Breaking change
git commit -m "feat(api)!: muda formato de resposta da API

BREAKING CHANGE: Response agora usa formato { success, data, error }
ao invés de retornar data diretamente.

Migration guide em docs/api-migration.md"
```

---

## 🧪 Testes

### Obrigatório Antes de PR

```bash
# Rodar todos os testes
pytest

# Com cobertura
pytest --cov=. --cov-report=html

# Apenas testes modificados
pytest tests/test_auth.py

# Com output verbose
pytest -v
```

### Cobertura Mínima

- **Novos arquivos:** 80% de cobertura
- **Arquivos modificados:** Não reduzir cobertura existente
- **Arquivos críticos (auth, security):** 90%+

---

## 🎨 Code Quality

### Formatação Automática

```bash
# Formatar todo projeto
black .

# Verificar sem modificar
black --check .

# Formatar arquivo específico
black app_pev.py
```

### Linting

```bash
# Lint todo projeto
flake8

# Arquivo específico
flake8 app_pev.py

# Ignorar avisos específicos
flake8 --extend-ignore=E501
```

### Type Checking (Opcional mas Recomendado)

```bash
# Instalar mypy
pip install mypy

# Rodar type check
mypy app_pev.py
```

---

## 📋 Checklist Pré-PR

### Código

- [ ] Código formatado com Black
- [ ] Sem erros de Flake8
- [ ] Sem código comentado
- [ ] Sem `print()` para debug
- [ ] Sem credenciais hardcoded
- [ ] Segue CODING_STANDARDS.md
- [ ] Não viola FORBIDDEN_PATTERNS.md

### Testes

- [ ] Testes unitários adicionados
- [ ] Testes de integração (se aplicável)
- [ ] Todos os testes passando
- [ ] Cobertura >= 80% em novos arquivos
- [ ] Testado em PostgreSQL
- [ ] Testado em SQLite

### Documentação

- [ ] Docstrings adicionadas
- [ ] README atualizado (se necessário)
- [ ] CHANGELOG atualizado
- [ ] Comentários em código complexo
- [ ] Templates de documentação preenchidos

### Database

- [ ] Migrations criadas (se necessário)
- [ ] Migrations testadas (up e down)
- [ ] Compatível com PostgreSQL E SQLite
- [ ] Índices adicionados onde necessário

### Segurança

- [ ] Rotas protegidas com `@login_required`
- [ ] Validação de input
- [ ] Sem SQL injection
- [ ] Sem XSS vulnerável
- [ ] CSRF protection (Flask-WTF)

### APIs (se aplicável)

- [ ] Segue API_STANDARDS.md
- [ ] Status codes corretos
- [ ] Response format consistente
- [ ] `@auto_log_crud` adicionado
- [ ] Paginação implementada

---

## 🔍 Code Review Checklist

### Para o Revisor

#### Funcionalidade
- [ ] Feature funciona como esperado
- [ ] Não quebra funcionalidades existentes
- [ ] Edge cases tratados
- [ ] Error handling adequado

#### Código
- [ ] Código legível e bem estruturado
- [ ] Sem complexidade desnecessária
- [ ] Segue padrões do projeto
- [ ] Sem duplicação de código
- [ ] Nomes descritivos

#### Arquitetura
- [ ] Segue arquitetura existente
- [ ] Camadas corretas (model, service, route)
- [ ] Sem acoplamento excessivo
- [ ] Reutiliza código existente

#### Performance
- [ ] Sem N+1 queries
- [ ] Queries otimizadas
- [ ] Eager loading quando necessário
- [ ] Paginação em listas

#### Segurança
- [ ] Sem vulnerabilidades conhecidas
- [ ] Validação de input
- [ ] Autenticação/Autorização
- [ ] Sem dados sensíveis em logs

#### Testes
- [ ] Testes adequados
- [ ] Cobertura suficiente
- [ ] Testes passando
- [ ] Casos de teste relevantes

#### Documentação
- [ ] Código autodocumentado
- [ ] Docstrings presentes
- [ ] Documentação atualizada
- [ ] Comentários úteis

---

## 🚨 Hotfix (Emergência)

### Quando Usar

- 🔴 Bug crítico em produção
- 🔴 Vulnerabilidade de segurança
- 🔴 Sistema fora do ar

### Processo Rápido

```bash
# 1. Criar branch de main
git checkout main
git pull origin main
git checkout -b hotfix/nome-do-bug

# 2. Fazer correção mínima
# ... código ...

# 3. Testar localmente
pytest

# 4. Commit e push
git add .
git commit -m "hotfix: corrige [descrição urgente]"
git push origin hotfix/nome-do-bug

# 5. PR direto para main (aprovação rápida)
# 6. Merge e deploy imediato

# 7. Backport para develop
git checkout develop
git merge hotfix/nome-do-bug
git push origin develop

# 8. Deletar branch
git branch -d hotfix/nome-do-bug
```

### Comunicação

- [ ] Notificar time no Slack
- [ ] Criar incident report
- [ ] Atualizar status page
- [ ] Post-mortem se crítico

---

## 📊 Métricas de Qualidade

### Monitorar

- **Lead Time:** Tempo de branch → produção
- **Cycle Time:** Tempo de PR → merge
- **Code Review Time:** Tempo até primeira revisão
- **Bug Rate:** Bugs por feature
- **Test Coverage:** % de cobertura
- **Build Success Rate:** % de builds passando

### Metas

- Lead Time: < 3 dias
- Code Review: < 24 horas
- Test Coverage: > 80%
- Build Success: > 95%

---

## 🔄 Fluxo por Tipo de Mudança

### Feature Nova

1. Issue/Ticket criado
2. Planning (estimar, definir escopo)
3. Branch `feature/nome`
4. Desenvolvimento
5. Testes
6. Documentação
7. PR → develop
8. Code review
9. Merge → develop
10. Deploy em staging
11. QA em staging
12. Merge develop → main
13. Deploy em produção

**Tempo típico:** 3-5 dias

### Bug Fix

1. Issue reportado
2. Investigação
3. Branch `bugfix/nome`
4. Correção
5. Testes (incluindo teste do bug)
6. PR → develop (ou main se crítico)
7. Code review (pode ser mais rápido)
8. Merge
9. Deploy

**Tempo típico:** 1-2 dias

### Documentação

1. Branch `docs/nome`
2. Escrever/Atualizar docs
3. PR → main (não precisa staging)
4. Review (pode ser rápido)
5. Merge

**Tempo típico:** < 1 dia

---

## 🛠️ Ferramentas

### Essenciais

- **Git:** Controle de versão
- **Black:** Formatação automática
- **Flake8:** Linting
- **pytest:** Testes
- **pytest-cov:** Cobertura

### Recomendadas

- **pre-commit:** Hooks automáticos
- **mypy:** Type checking
- **bandit:** Security linting
- **isort:** Organizar imports

---

## 📚 Recursos

- **Conventional Commits:** https://www.conventionalcommits.org/
- **Git Flow:** https://nvie.com/posts/a-successful-git-branching-model/
- **Code Review Best Practices:** https://google.github.io/eng-practices/review/

---

## ❓ FAQ

**P: Posso commitar direto na main?**  
R: Não. Sempre use branches e PRs.

**P: Quantos commits devo fazer?**  
R: Commits pequenos e frequentes. Squash no merge se necessário.

**P: Preciso de aprovação para documentação?**  
R: Sim, mas review pode ser mais rápido.

**P: E se CI falhar?**  
R: Corrigir antes de pedir review. CI verde é obrigatório.

**P: Posso fazer WIP PR?**  
R: Sim! Marque como Draft PR e adicione [WIP] no título.

---

**Próxima revisão:** Trimestral  
**Responsável:** Tech Lead



