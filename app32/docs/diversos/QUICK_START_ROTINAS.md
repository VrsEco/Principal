# 🚀 Início Rápido - Sistema de Rotinas

## ⚡ Começar em 3 Passos

### 1️⃣ Configurar o Agendamento (EXECUTAR UMA VEZ)

```cmd
# Abrir CMD como Administrador
cd C:\GestaoVersus\app25
setup_routine_scheduler.bat
```

✅ Isso configura a execução automática às 00:01 todos os dias

---

### 2️⃣ Testar Manualmente (Opcional)

```cmd
# Testar se está funcionando
cd C:\GestaoVersus\app25
venv\Scripts\python.exe routine_scheduler.py
```

✅ Você verá o relatório de processamento

---

### 3️⃣ Criar Sua Primeira Rotina

1. **Acessar**: `http://localhost:5000/companies/1/routines`
   - Substitua `1` pelo ID da sua empresa

2. **Criar Rotina**:
   - Clique em "Nova Rotina"
   - Nome: "Backup Diário"
   - Descrição: "Backup do sistema"
   - Salvar

3. **Adicionar Gatilho**:
   - Clique em "Adicionar Gatilho"
   - Tipo: Diário
   - Horário: 14:00
   - Prazo: 2 horas
   - Salvar

4. **Visualizar Tarefas**:
   - Acesse: `http://localhost:5000/companies/1/routine-tasks`

✅ Pronto! No dia seguinte às 00:01, tarefas serão criadas automaticamente!

---

## 📋 Tipos de Gatilhos

### Diário
- **Quando usar**: Tarefas que devem acontecer todo dia
- **Exemplo**: Backup às 02:00
- **Configuração**: Escolher horário (ex: 14:00)

### Semanal
- **Quando usar**: Tarefas que devem acontecer em dias específicos da semana
- **Exemplo**: Relatório toda segunda e sexta
- **Configuração**: Escolher dia da semana

### Mensal
- **Quando usar**: Tarefas que devem acontecer em dias específicos do mês
- **Exemplo**: Fechamento no dia 1º e 15
- **Configuração**: Escolher dia do mês (1-31)

### Anual
- **Quando usar**: Tarefas que acontecem em datas específicas do ano
- **Exemplo**: Declaração de IR em 01/03
- **Configuração**: Digitar data DD/MM

---

## 💡 Exemplo Prático

### Criar Rotina de Relatórios Semanais

```
1. Nova Rotina
   Nome: Relatório de Vendas
   Descrição: Relatório semanal consolidado

2. Adicionar Gatilho 1
   Tipo: Semanal
   Dia: Segunda-feira
   Prazo: 2 dias

3. Adicionar Gatilho 2
   Tipo: Semanal
   Dia: Sexta-feira
   Prazo: 2 dias
```

**Resultado**: Toda segunda E toda sexta, uma tarefa é criada com 2 dias de prazo!

---

## 🔍 Verificar se está Funcionando

### Ver Tarefa Agendada no Windows
```cmd
schtasks /Query /TN "RoutineScheduler" /V /FO LIST
```

### Testar Processamento
```cmd
cd C:\GestaoVersus\app25
venv\Scripts\python.exe routine_scheduler.py
```

### Verificar Banco de Dados
As tarefas criadas ficam na tabela `routine_tasks`

---

## 📁 Arquivos Importantes

- **`routine_scheduler.py`** - Script de processamento
- **`setup_routine_scheduler.bat`** - Configuração do agendamento
- **`README_ROTINAS.md`** - Documentação completa
- **`SISTEMA_ROTINAS_COMPLETO.md`** - Resumo técnico

---

## ⚠️ Problemas Comuns

### "Erro ao criar tarefa agendada"
**Solução**: Execute o CMD como Administrador

### "Python não encontrado"
**Solução**: Verifique se o venv está configurado em `C:\GestaoVersus\app25\venv`

### "Tarefas não aparecem"
**Solução**: 
1. Execute `routine_scheduler.py` manualmente
2. Verifique se há rotinas ativas
3. Verifique se os gatilhos estão configurados corretamente

---

## 📞 Próximos Passos

1. ✅ Configure o agendamento
2. ✅ Crie suas rotinas
3. ✅ Adicione gatilhos
4. ✅ Aguarde até 00:01 ou teste manualmente
5. ✅ Acompanhe as tarefas em `/companies/{id}/routine-tasks`

---

**Dúvidas?** Consulte o `README_ROTINAS.md` para documentação completa!



