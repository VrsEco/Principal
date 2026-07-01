# ✅ Checklist de Deploy

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório

---

## 🎯 Visão Geral

Este checklist deve ser seguido para **TODOS** os deploys em produção.

**Tipos de Deploy:**
- 🟢 **Regular:** Deploy planejado (features, melhorias)
- 🟡 **Urgente:** Bug fix importante mas não crítico
- 🔴 **Hotfix:** Correção crítica (produção quebrada)

**Modos operacionais do workflow de produção:**
- `quick` = código + restart + healthcheck
- `standard` = `quick` + dependências
- `full` = `standard` + migrations

---

## 📋 Checklist Completo

### Pré-Deploy (1-2 dias antes)

#### Código

- [ ] **Todos os testes passando**
  ```bash
  pytest
  ```

- [ ] **Cobertura de testes adequada**
  ```bash
  pytest --cov=. --cov-report=html
  # Cobertura > 80% em novos arquivos
  ```

- [ ] **Código formatado**
  ```bash
  black --check .
  ```

- [ ] **Sem erros de linting**
  ```bash
  flake8
  ```

- [ ] **Type checking OK (se aplicável)**
  ```bash
  mypy .
  ```

- [ ] **Sem código comentado ou TODOs críticos**

- [ ] **Sem `print()` statements para debug**

- [ ] **Sem credenciais hardcoded**
  ```bash
  # Verificar manualmente
  grep -r "password\s*=\s*['\"]" .
  grep -r "api_key\s*=\s*['\"]" .
  ```

#### Banco de Dados

- [ ] **Migrations criadas e testadas**
  ```bash
  flask db migrate -m "descrição"
  flask db upgrade
  flask db downgrade  # Testar rollback
  flask db upgrade
  ```

- [ ] **Backup do banco criado**
  ```bash
  python backup_automatico.py
  # Ou comando específico PostgreSQL
  pg_dump dbname > backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Migrations compatíveis com dados existentes**
  - [ ] Não quebra dados existentes
  - [ ] Não requer downtime (se possível)
  - [ ] Testado com cópia de dados de produção

- [ ] **Índices criados para novos campos consultados**

#### Dependências

- [ ] **requirements.txt atualizado**
  ```bash
  pip freeze > requirements.txt
  ```

- [ ] **Novas dependências documentadas**
  - [ ] Adicionadas em `docs/governance/TECH_STACK.md`
  - [ ] Justificativa em `docs/governance/DECISION_LOG.md` (se importante)

- [ ] **Versões pinadas (não usar >=)**

- [ ] **Verificar vulnerabilidades**
  ```bash
  pip-audit
  ```

#### Configuração

- [ ] **Variáveis de ambiente documentadas**
  - [ ] `.env.example` atualizado
  - [ ] Documentação atualizada

- [ ] **Configurações de produção verificadas**
  - [ ] `DEBUG = False`
  - [ ] `SECRET_KEY` segura (não usar padrão)
  - [ ] CORS configurado corretamente
  - [ ] Database URL correto

- [ ] **Feature flags configuradas (se aplicável)**

#### Documentação

- [ ] **CHANGELOG.md atualizado**
  ```markdown
  ## [Versão] - YYYY-MM-DD
  
  ### Added
  - Nova feature X
  
  ### Changed
  - Melhoria Y
  
  ### Fixed
  - Bug Z
  
  ### Deprecated
  - Feature W (será removida em v2.0)
  ```

- [ ] **README.md atualizado (se necessário)**

- [ ] **Documentação de API atualizada (se mudanças em API)**

- [ ] **Guias de usuário atualizados (se UI mudou)**

#### Testes

- [ ] **Testado localmente (PostgreSQL)**
  ```bash
  # Ambiente local com PostgreSQL
  python app_pev.py
  # Testar manualmente features principais
  ```

- [ ] **Testado localmente (SQLite)**
  ```bash
  # Ambiente local com SQLite
  python app_pev.py
  # Testar manualmente features principais
  ```

- [ ] **Testado em staging/homologação**
  - [ ] Deploy em staging realizado
  - [ ] Smoke tests passaram
  - [ ] Features novas testadas manualmente
  - [ ] Regressão: features antigas funcionam

- [ ] **Testes de carga (se mudanças significativas)**
  ```bash
  # Usar locust, ab, ou similar
  ```

- [ ] **Testes de integração com serviços externos**
  - [ ] APIs externas funcionando
  - [ ] Email service funcionando
  - [ ] S3/Storage funcionando

#### Segurança

- [ ] **Scan de vulnerabilidades**
  ```bash
  bandit -r .
  pip-audit
  ```

- [ ] **Code review de segurança (se mudanças sensíveis)**

- [ ] **OWASP Top 10 verificado (se mudanças em auth/API)**
  - [ ] SQL Injection
  - [ ] XSS
  - [ ] CSRF
  - [ ] Authentication
  - [ ] Authorization

- [ ] **Dados sensíveis não expostos**

#### Comunicação

- [ ] **Time notificado sobre deploy**
  - [ ] Data e hora definidas
  - [ ] Janela de manutenção comunicada
  - [ ] Mudanças principais listadas

- [ ] **Usuários notificados (se breaking changes ou downtime)**
  - [ ] Email enviado
  - [ ] Banner no sistema
  - [ ] Status page atualizado

- [ ] **Stakeholders informados (se mudanças importantes)**

---

### Deploy (Dia D)

#### Pré-Deploy Imediato

- [ ] **Confirmar horário** (preferir horários de baixo tráfego)
  - ✅ Recomendado: Madrugada, fim de semana
  - ❌ Evitar: Horário comercial, início do mês, fim do ano

- [ ] **Escolher o modo correto do workflow**
  - [ ] `quick` para mudança sem schema e sem dependência
  - [ ] `standard` para mudança com dependência, sem migration
  - [ ] `full` para mudança estrutural com migration

- [ ] **Team de prontidão**
  - [ ] Dev responsável disponível
  - [ ] DevOps/SRE disponível
  - [ ] Tech lead disponível (se deploy grande)

- [ ] **Ferramentas de monitoramento abertas**
  - [ ] Logs
  - [ ] Métricas (CPU, RAM, Requests)
  - [ ] Error tracking (Sentry, etc.)

- [ ] **Backup final**
  ```bash
  python backup_automatico.py
  # Aguardar confirmação de sucesso
  ```

#### Executar Deploy

**Método varia por infraestrutura, exemplo genérico:**

```bash
# 1. Conectar ao servidor
ssh user@production-server

# 2. Navegar para diretório
cd /var/www/app

# 3. Ativar modo de manutenção (se disponível)
touch maintenance.flag

# 4. Acionar workflow manual no GitHub Actions
# - ref
# - deploy_mode = quick | standard | full
# - restart_mcp = true | false
# - confirm_production = PRODUCAO

# 5. Aguardar o healthcheck final do workflow

# 6. Verificar logs/resultados pós-publicação
tail -f /var/log/app/app.log
```

#### Verificação Pós-Deploy Imediata (0-15 min)

- [ ] **Aplicação iniciou sem erros**
  ```bash
  sudo systemctl status app.service
  tail -n 100 /var/log/app/app.log
  ```

- [ ] **Health check passando**
  ```bash
  curl http://localhost:5000/health
  # Esperado: {"status": "healthy"}
  ```

- [ ] **Smoke tests manuais**
  - [ ] Login funciona
  - [ ] Dashboard carrega
  - [ ] API responde
  - [ ] Database conectado

- [ ] **Sem erros críticos nos logs**
  ```bash
  tail -f /var/log/app/app.log | grep ERROR
  ```

- [ ] **Métricas normais**
  - [ ] CPU < 80%
  - [ ] RAM < 80%
  - [ ] Response time < 2s
  - [ ] Error rate < 1%

- [ ] **Features novas funcionando**
  - Testar manualmente cada feature nova

#### Monitoramento Estendido (15 min - 2 horas)

- [ ] **Monitorar logs continuamente**
  - [ ] Sem erros anormais
  - [ ] Sem exceções não tratadas
  - [ ] Sem warnings críticos

- [ ] **Monitorar métricas**
  - [ ] Taxa de requisições estável
  - [ ] Response time estável
  - [ ] Error rate estável
  - [ ] Database connections normais

- [ ] **Verificar integrações**
  - [ ] Emails sendo enviados
  - [ ] Background jobs rodando
  - [ ] APIs externas respondendo

- [ ] **Feedback de usuários**
  - [ ] Nenhum report de erro
  - [ ] Features funcionando

---

### Pós-Deploy (1-7 dias)

#### Dia 1

- [ ] **Análise de métricas**
  - [ ] Comparar com baseline pré-deploy
  - [ ] Identificar anomalias
  - [ ] Investigar se necessário

- [ ] **Revisar logs**
  - [ ] Analisar padrões de erro
  - [ ] Identificar warnings recorrentes

- [ ] **Coletar feedback de usuários**
  - [ ] Via suporte
  - [ ] Via analytics

- [ ] **Documentar issues encontrados**

#### Semana 1

- [ ] **Monitoramento contínuo**
  - [ ] Métricas de performance
  - [ ] Error rates
  - [ ] User feedback

- [ ] **Post-mortem (se houve problemas)**
  - [ ] O que correu bem
  - [ ] O que correu mal
  - [ ] Ações corretivas
  - [ ] Atualizar este checklist

- [ ] **Marcar deploy como estável** (se tudo OK)

---

## 🔴 Rollback Plan

### Quando Fazer Rollback

**Critérios para rollback imediato:**
- 🔴 Sistema completamente fora do ar
- 🔴 Perda de dados detectada
- 🔴 Vulnerabilidade de segurança crítica
- 🔴 Error rate > 10%
- 🔴 Response time > 10s

**Critérios para rollback urgente (< 1h):**
- 🟡 Features principais quebradas
- 🟡 Error rate > 5%
- 🟡 Performance degradada significativamente

### Como Fazer Rollback

```bash
# 1. Conectar ao servidor
ssh user@production-server

# 2. Navegar para diretório
cd /var/www/app

# 3. Modo de manutenção
touch maintenance.flag

# 4. Reverter código
git log --oneline  # Ver commits
git revert HEAD    # Reverter último commit
# Ou: git reset --hard <commit-hash-anterior>

# 5. Reverter migrations (se aplicável)
flask db downgrade

# 6. Reiniciar aplicação
sudo systemctl restart app.service

# 7. Verificar funcionamento
curl http://localhost:5000/health

# 8. Desativar manutenção
rm maintenance.flag

# 9. Notificar time
# Enviar mensagem no Slack/Email
```

### Após Rollback

- [ ] **Investigar causa raiz**
- [ ] **Documentar problema**
- [ ] **Criar plano de correção**
- [ ] **Atualizar checklist se necessário**

---

## 🔥 Hotfix Emergencial

### Processo Acelerado (Mínimo Necessário)

**Use apenas em emergências críticas!**

- [ ] Identificar problema
- [ ] Criar `hotfix/nome` branch
- [ ] Implementar correção mínima
- [ ] Testes básicos localmente
- [ ] Code review rápido (1 pessoa, < 30 min)
- [ ] Deploy direto em produção
- [ ] Monitorar intensivamente (1h)
- [ ] Backport para outras branches
- [ ] Post-mortem obrigatório

**Documentar tudo para post-mortem!**

---

## 📊 Métricas de Sucesso

### KPIs de Deploy

- **Deploy Frequency:** Quantas vezes por semana
- **Lead Time:** Tempo de commit até produção
- **MTTR:** Mean Time to Recover (rollback)
- **Change Fail %:** % de deploys que precisam rollback

### Metas

- Deploy Frequency: 2-3x/semana
- Lead Time: < 2 dias
- MTTR: < 1 hora
- Change Fail: < 5%

---

## 🛠️ Ferramentas Úteis

### Monitoramento

```bash
# Ver logs em tempo real
tail -f /var/log/app/app.log

# Filtrar erros
tail -f /var/log/app/app.log | grep ERROR

# Ver status do serviço
sudo systemctl status app.service

# Ver uso de recursos
top
htop
free -h
df -h
```

### Database

```bash
# Backup PostgreSQL
pg_dump dbname > backup.sql

# Restore PostgreSQL
psql dbname < backup.sql

# Ver migrations aplicadas
flask db current

# Ver histórico de migrations
flask db history
```

---

## 📝 Template de Comunicação

### Notificação Pré-Deploy

```
🚀 Deploy Agendado

Data: [YYYY-MM-DD]
Horário: [HH:MM - HH:MM] (horário de Brasília)
Downtime esperado: [X minutos] ou [Nenhum]

Mudanças principais:
- [Feature/Fix 1]
- [Feature/Fix 2]
- [Feature/Fix 3]

Breaking changes: [Sim/Não]
[Se sim, descrever e indicar ações necessárias]

Mais detalhes: [link para CHANGELOG]
```

### Notificação Pós-Deploy

```
✅ Deploy Concluído

Data: [YYYY-MM-DD HH:MM]
Status: Sucesso / Parcial / Rollback

Features implantadas:
- [Feature 1]
- [Feature 2]

Issues conhecidos:
- [Issue 1] - [Status]

Próximos passos:
- [Ação 1]
- [Ação 2]
```

---

## ❓ FAQ

**P: Posso pular algum item do checklist?**  
R: Apenas em hotfix crítico. Documente o que foi pulado.

**P: Quanto tempo devo monitorar após deploy?**  
R: Mínimo 2 horas ativo, depois 1 semana passivo.

**P: Quando fazer rollback?**  
R: Se qualquer critério de rollback for atingido, não hesite.

**P: Posso deployar sexta à tarde?**  
R: Evite! Se deploy quebrar, time não está disponível no fim de semana.

**P: E se migration não reverter?**  
R: Sempre testar downgrade antes. Ter backup recente é obrigatório.

---

## 📚 Recursos Adicionais

- **Incident Response Plan:** [link]
- **Monitoring Dashboard:** [link]
- **Status Page:** [link]
- **Runbook:** [link]

---

**Este documento salva vidas (e finais de semana)! Use-o religiosamente.**

**Próxima revisão:** Após cada deploy com problemas  
**Responsável:** DevOps Lead / Tech Lead



