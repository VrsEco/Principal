# Sistema de Gestão de Rotinas

## 📋 Visão Geral

O Sistema de Gestão de Rotinas permite criar e gerenciar rotinas recorrentes com gatilhos automáticos e prazos de conclusão. O sistema processa automaticamente os gatilhos configurados e cria tarefas que podem ser acompanhadas e gerenciadas.

## 🎯 Funcionalidades

### 1. Gerenciamento de Rotinas
- Criar rotinas com nome e descrição
- Editar rotinas existentes
- Excluir rotinas
- Visualizar todas as rotinas de uma empresa

### 2. Configuração de Gatilhos (Triggers)
Cada rotina pode ter múltiplos gatilhos configurados. Tipos de gatilhos disponíveis:

- **Diário**: Executa em horário específico todos os dias
  - Exemplo: 12:00, 14:30, 18:00
  
- **Semanal**: Executa em dia(s) específico(s) da semana
  - Exemplo: Segunda-feira, Quarta-feira, Sexta-feira
  
- **Mensal**: Executa em dia(s) específico(s) do mês
  - Exemplo: Dia 01, Dia 15, Dia 30
  
- **Anual**: Executa em data(s) específica(s) do ano
  - Exemplo: 01/03, 25/12, 31/12

### 3. Prazos de Conclusão
Para cada gatilho, você define:
- **Valor**: Número de horas ou dias
- **Unidade**: Horas ou Dias

Exemplo: "24 horas" ou "3 dias"

### 4. Tarefas Automáticas
O sistema cria automaticamente tarefas quando os gatilhos são acionados, com:
- Data de agendamento
- Data limite (deadline) calculada automaticamente
- Status (pendente, em progresso, concluído, atrasado)

## 🚀 Como Usar

### Acessar o Sistema
1. Faça login no sistema
2. Navegue até a página de empresas
3. Selecione uma empresa
4. Clique em "Rotinas" ou acesse: `/companies/{company_id}/routines`

### Criar uma Nova Rotina
1. Clique no botão "Nova Rotina"
2. Preencha:
   - **Nome**: Nome descritivo da rotina
   - **Descrição**: Detalhes sobre a rotina (opcional)
3. Clique em "Salvar Rotina"

### Adicionar Gatilhos à Rotina
1. No card da rotina, clique em "Adicionar Gatilho"
2. Selecione o **Tipo de Gatilho**:
   - Diário, Semanal, Mensal ou Anual
3. Configure o **valor do gatilho**:
   - Para Diário: Escolha o horário (ex: 14:00)
   - Para Semanal: Escolha o dia da semana
   - Para Mensal: Escolha o dia do mês (1-31)
   - Para Anual: Digite a data no formato DD/MM
4. Configure o **prazo**:
   - Valor numérico (ex: 24)
   - Unidade: Horas ou Dias
5. Clique em "Salvar Gatilho"

### Exemplos Práticos

#### Exemplo 1: Backup Diário
- **Rotina**: Backup do Sistema
- **Gatilho**: Diário às 02:00
- **Prazo**: 6 horas
- **Resultado**: Todo dia às 02:00, uma tarefa de backup é criada com prazo até 08:00

#### Exemplo 2: Relatório Semanal
- **Rotina**: Relatório de Vendas
- **Gatilhos**:
  - Semanal: Segunda-feira (Prazo: 2 dias)
  - Semanal: Sexta-feira (Prazo: 2 dias)
- **Resultado**: Toda segunda e sexta, uma tarefa de relatório é criada com 2 dias de prazo

#### Exemplo 3: Fechamento Mensal
- **Rotina**: Fechamento Contábil
- **Gatilho**: Mensal no dia 01 (Prazo: 5 dias)
- **Resultado**: Todo dia 1º do mês, uma tarefa é criada com prazo até o dia 6

#### Exemplo 4: Declaração Anual
- **Rotina**: Declaração de Imposto de Renda
- **Gatilho**: Anual em 01/03 (Prazo: 60 dias)
- **Resultado**: Todo dia 01/03, uma tarefa é criada com prazo até 30/04

## ⚙️ Configuração do Processamento Automático

### Windows

#### Configuração Automática (Recomendado)
1. Abra o Prompt de Comando como **Administrador**
2. Navegue até a pasta do projeto:
   ```
   cd C:\GestaoVersus\app25
   ```
3. Execute o script de configuração:
   ```
   setup_routine_scheduler.bat
   ```

#### Configuração Manual
1. Abra o "Agendador de Tarefas" do Windows
2. Clique em "Criar Tarefa"
3. Configure:
   - **Nome**: RoutineScheduler
   - **Gatilhos**: Diário às 00:01
   - **Ações**: Executar programa
     - Programa: `C:\GestaoVersus\app25\venv\Scripts\python.exe`
     - Argumentos: `C:\GestaoVersus\app25\routine_scheduler.py`
4. Salve a tarefa

### Linux/Mac

Adicione ao crontab:
```bash
# Editar crontab
crontab -e

# Adicionar linha (executa todos os dias às 00:01)
1 0 * * * cd /path/to/app25 && /path/to/app25/venv/bin/python routine_scheduler.py >> /var/log/routine_scheduler.log 2>&1
```

## 🧪 Testar Manualmente

Para testar o processamento das rotinas sem esperar até 00:01:

```bash
# Windows
venv\Scripts\python.exe routine_scheduler.py

# Linux/Mac
venv/bin/python routine_scheduler.py
```

O script irá:
1. Processar todas as rotinas ativas
2. Verificar quais gatilhos devem ser acionados
3. Criar tarefas para os gatilhos acionados
4. Marcar tarefas atrasadas como "overdue"
5. Exibir um relatório do processamento

## 📊 API Endpoints

### Rotinas
- `GET /api/companies/{company_id}/routines` - Listar rotinas
- `POST /api/companies/{company_id}/routines` - Criar rotina
- `GET /api/routines/{routine_id}` - Obter rotina
- `PUT /api/routines/{routine_id}` - Atualizar rotina
- `DELETE /api/routines/{routine_id}` - Excluir rotina

### Gatilhos
- `GET /api/routines/{routine_id}/triggers` - Listar gatilhos
- `POST /api/routines/{routine_id}/triggers` - Criar gatilho
- `PUT /api/triggers/{trigger_id}` - Atualizar gatilho
- `DELETE /api/triggers/{trigger_id}` - Excluir gatilho

### Tarefas
- `GET /api/companies/{company_id}/routine-tasks` - Listar tarefas
- `GET /api/companies/{company_id}/routine-tasks/overdue` - Listar atrasadas
- `GET /api/companies/{company_id}/routine-tasks/upcoming` - Listar próximas
- `PUT /api/routine-tasks/{task_id}/status` - Atualizar status

## 🗄️ Estrutura do Banco de Dados

### Tabela: routines
- `id` - ID da rotina
- `company_id` - ID da empresa
- `name` - Nome da rotina
- `description` - Descrição
- `is_active` - Status (ativo/inativo)
- `created_at` - Data de criação
- `updated_at` - Data de atualização

### Tabela: routine_triggers
- `id` - ID do gatilho
- `routine_id` - ID da rotina
- `trigger_type` - Tipo (daily, weekly, monthly, yearly)
- `trigger_value` - Valor do gatilho
- `deadline_value` - Valor do prazo
- `deadline_unit` - Unidade (hours, days)
- `is_active` - Status (ativo/inativo)
- `created_at` - Data de criação
- `updated_at` - Data de atualização

### Tabela: routine_tasks
- `id` - ID da tarefa
- `routine_id` - ID da rotina
- `trigger_id` - ID do gatilho
- `title` - Título da tarefa
- `description` - Descrição
- `scheduled_date` - Data de agendamento
- `deadline_date` - Data limite
- `status` - Status (pending, in_progress, completed, overdue)
- `completed_at` - Data de conclusão
- `completed_by` - Quem completou
- `notes` - Observações
- `created_at` - Data de criação
- `updated_at` - Data de atualização

## 🔍 Monitoramento

### Verificar Tarefas Agendadas (Windows)
```
schtasks /Query /TN "RoutineScheduler" /V /FO LIST
```

### Ver Log de Execução
O script exibe informações detalhadas no console quando executado:
- Empresas processadas
- Rotinas verificadas
- Tarefas criadas
- Tarefas marcadas como atrasadas

## ❓ Solução de Problemas

### O agendamento não está funcionando
1. Verifique se a tarefa foi criada no Agendador de Tarefas
2. Verifique se o caminho do Python está correto
3. Execute manualmente para verificar erros

### Tarefas não estão sendo criadas
1. Verifique se as rotinas estão ativas (`is_active = 1`)
2. Verifique se os gatilhos estão configurados corretamente
3. Verifique o formato dos valores de gatilho
4. Execute o script manualmente para ver mensagens de erro

### Tarefas não aparecem na interface
1. Verifique se o banco de dados está sendo atualizado
2. Atualize a página no navegador
3. Verifique o console do navegador para erros JavaScript

## 📝 Próximas Funcionalidades (Planejadas)

- Dashboard de acompanhamento de tarefas
- Notificações por e-mail/WhatsApp
- Histórico de execução
- Relatórios de cumprimento de prazos
- Atribuição de responsáveis
- Anexos em tarefas
- Comentários e colaboração

---

**Desenvolvido por**: Versus Tecnologia  
**Versão**: 1.0.0  
**Data**: Outubro 2025



