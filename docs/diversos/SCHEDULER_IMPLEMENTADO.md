# ⏰ Sistema de Agendamento Automático - APScheduler

**Data de Implementação:** 20/10/2025  
**Status:** ✅ **ATIVO E FUNCIONANDO**

---

## 🎯 **Objetivo**

Executar **automaticamente** as rotinas e processos configurados no sistema, sem necessidade de intervenção manual ou configuração de cron/task scheduler do sistema operacional.

---

## 🚀 **O que Foi Implementado**

### 1. **APScheduler Integrado**
- **Biblioteca:** APScheduler 3.10.4
- **Tipo:** BackgroundScheduler (roda junto com o Flask)
- **Timezone:** America/Sao_Paulo

### 2. **Jobs Configurados**

#### **Job 1: Processamento Diário de Rotinas**
```python
Horário: 00:01 (todos os dias)
Função: process_daily_routines()
Descrição: Processa todas as rotinas agendadas (diárias, semanais, mensais, etc.)
```

**O que faz:**
- ✅ Verifica todas as rotinas ativas
- ✅ Identifica quais devem disparar hoje
- ✅ Cria instâncias de processos automaticamente
- ✅ Atribui colaboradores
- ✅ Define prazos

#### **Job 2: Verificação de Tarefas Atrasadas**
```python
Horário: A cada hora cheia (00:00, 01:00, 02:00, ...)
Função: check_overdue_tasks()
Descrição: Atualiza status de tarefas que passaram do prazo
```

**O que faz:**
- ✅ Busca tarefas pendentes/em andamento
- ✅ Compara com prazo (deadline)
- ✅ Marca como "atrasado" se vencido

---

## 📁 **Arquivos**

| Arquivo | Descrição |
|---------|-----------|
| `services/scheduler_service.py` | Serviço principal do APScheduler |
| `routine_scheduler.py` | Lógica de processamento de rotinas |
| `test_scheduler_manual.py` | Script para teste manual |

---

## 🔧 **Como Funciona**

### Inicialização Automática

Quando você inicia o Flask (`docker-compose up` ou `python app_pev.py`):

1. ✅ Flask carrega
2. ✅ Scheduler é inicializado automaticamente
3. ✅ Jobs são registrados
4. ✅ Scheduler fica aguardando os horários

**Logs de inicialização:**
```
🔧 Inicializando Scheduler de Tarefas...
📅 Scheduler Service inicializado
✅ Job 'process_daily_routines' adicionado
✅ Job 'check_overdue_tasks' adicionado
✅ SCHEDULER ATIVO E FUNCIONANDO!
📋 Jobs agendados: 2
  - check_overdue_tasks: próxima execução em 2025-10-20 20:00:00
  - process_daily_routines: próxima execução em 2025-10-21 00:01:00
```

### Execução Automática

**Não precisa fazer nada!** O scheduler roda sozinho.

```
┌─ 00:01 (meia-noite) ─────────────────┐
│                                       │
│  🔄 Scheduler dispara                │
│  └─► process_daily_routines()       │
│      ├─ Busca rotinas diárias       │
│      ├─ Busca rotinas semanais      │
│      ├─ Busca rotinas mensais       │
│      ├─ Cria instâncias             │
│      └─ Logs no console             │
│                                       │
└───────────────────────────────────────┘

┌─ A cada hora cheia ──────────────────┐
│                                       │
│  ⏰ Scheduler dispara                │
│  └─► check_overdue_tasks()          │
│      ├─ Busca tarefas pendentes     │
│      ├─ Verifica prazos             │
│      ├─ Atualiza status             │
│      └─ Logs no console             │
│                                       │
└───────────────────────────────────────┘
```

---

## 📊 **Monitoramento**

### Ver Jobs Ativos

```bash
# Logs da aplicação mostram os jobs
docker logs gestaoversos_app_dev | grep -i scheduler
```

**Saída esperada:**
```
INFO:services.scheduler_service:📋 Jobs agendados: 2
INFO:services.scheduler_service:  - check_overdue_tasks: próxima execução em ...
INFO:services.scheduler_service:  - process_daily_routines: próxima execução em ...
```

### Ver Execuções

Quando um job executa, você verá nos logs:

```bash
# Monitorar execuções em tempo real
docker logs -f gestaoversos_app_dev
```

**Saída quando executa:**
```
================================================================================
🔄 Iniciando processamento de rotinas - 2025-10-21 00:01:00
================================================================================
📊 Processando empresa: Minha Empresa (ID: 1)
   📋 Rotina: Relatório Mensal (ID: 5)
      ✓ Tarefa criada: Relatório Mensal (ID: 123)
================================================================================
✅ Processamento concluído!
  - Empresas processadas: 1
  - Rotinas processadas: 3
  - Tarefas criadas: 2
================================================================================
```

---

## 🧪 **Testes**

### Teste Manual (Executar Imediatamente)

Se quiser testar SEM esperar o horário:

```bash
# Dentro do container
docker exec -it gestaoversos_app_dev python test_scheduler_manual.py
```

Ou localmente:
```bash
python test_scheduler_manual.py
```

### Teste de Horário Específico

Para testar com horário diferente, edite `services/scheduler_service.py`:

```python
# Mudar de 00:01 para daqui a 2 minutos (por exemplo)
scheduler_service.add_job(
    func=process_daily_routines,
    trigger='cron',
    job_id='process_daily_routines',
    hour=22,    # Hora atual + alguns minutos
    minute=35,  # Minuto específico
)
```

Reinicie a aplicação e aguarde!

---

## 🔧 **Configuração Avançada**

### Adicionar Novo Job

Edite `services/scheduler_service.py`, função `setup_routine_jobs()`:

```python
def setup_routine_jobs():
    # Jobs existentes...
    
    # Novo job: Backup diário às 03:00
    scheduler_service.add_job(
        func=backup_database,
        trigger='cron',
        job_id='daily_backup',
        hour=3,
        minute=0,
        name='Backup Diário do Banco'
    )
```

### Tipos de Triggers

```python
# Diário (horário específico)
trigger='cron', hour=0, minute=1

# A cada X minutos
trigger='interval', minutes=30

# Semanais (segunda-feira às 09:00)
trigger='cron', day_of_week='mon', hour=9, minute=0

# Mensais (dia 1 às 00:00)
trigger='cron', day=1, hour=0, minute=0

# Data específica
trigger='date', run_date='2025-12-31 23:59:00'
```

---

## ⚠️ **Importante**

### Em Produção

- ✅ **Funciona automaticamente** no Docker
- ✅ **Logs ficam no console** do container
- ✅ **Não precisa** configurar cron/task scheduler
- ✅ **Reinicia automaticamente** se o container reiniciar

### Em Desenvolvimento

- ✅ Ativo ao rodar `python app_pev.py`
- ✅ Para quando você para o Flask (Ctrl+C)
- ✅ Logs aparecem no console

### Sem use_reloader=False

**IMPORTANTE:** No `app_pev.py` temos:
```python
app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
```

O `use_reloader=False` é **essencial**! Se mudar para `True`:
- ❌ Scheduler será inicializado 2x (processo pai + filho)
- ❌ Jobs rodarão em duplicata
- ❌ Comportamento imprevisível

---

## 🐛 **Troubleshooting**

### Scheduler não iniciou

**Sintoma:** Não vê mensagens `✅ SCHEDULER ATIVO` nos logs

**Solução:**
```bash
# Ver logs completos
docker logs gestaoversos_app_dev

# Verificar se APScheduler está instalado
docker exec gestaoversos_app_dev pip list | grep -i apscheduler
```

### Jobs não executam

**Sintoma:** Horário passou mas nada aconteceu

**Verificar:**
1. Timezone correto? (America/Sao_Paulo)
2. Container rodando?
3. Logs mostram próxima execução?

```bash
# Ver próximas execuções
docker logs gestaoversos_app_dev | grep "próxima execução"
```

### Jobs executam 2x

**Causa:** `use_reloader=True` no Flask

**Solução:**
```python
# Garantir que está False
app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
```

---

## 📈 **Vantagens**

### Antes (Manual/Cron)
- ❌ Configurar cron em cada servidor
- ❌ Diferente Windows vs Linux
- ❌ Precisa acesso root/admin
- ❌ Logs espalhados
- ❌ Não funciona no Docker facilmente

### Agora (APScheduler)
- ✅ Automático ao iniciar o Flask
- ✅ Mesmo código Windows/Linux/Docker
- ✅ Não precisa permissões especiais
- ✅ Logs centralizados
- ✅ Funciona perfeitamente no Docker
- ✅ Fácil de testar
- ✅ Fácil de monitorar

---

## 🔮 **Próximos Passos (Opcional)**

- [ ] Dashboard web para ver jobs (Flask-Admin + APScheduler)
- [ ] Notificações quando jobs falham
- [ ] Histórico de execuções no banco
- [ ] API para disparar jobs manualmente
- [ ] Retry automático em caso de falha

---

## 📞 **Suporte**

- **Logs:** `docker logs -f gestaoversos_app_dev`
- **Código:** `services/scheduler_service.py`
- **Testes:** `python test_scheduler_manual.py`

---

**Implementado por:** Cursor AI  
**Data:** 20/10/2025  
**Versão:** 1.0  
**Status:** ✅ **PRODUÇÃO**

