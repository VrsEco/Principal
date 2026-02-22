# 📅 Sistema de Rotina dos Processos

**Implementado:** 10/10/2025  
**Status:** ✅ Completo e Funcionando

---

## 🎯 OBJETIVO

Cadastrar **agendamentos** e **datas limite** para os processos da empresa, permitindo:
- ✅ Definir quando uma atividade deve ser disparada
- ✅ Definir prazo para conclusão
- ✅ Vincular a processos específicos
- 🔜 Futuramente: associar responsáveis

---

## 🚀 COMO USAR

### Acessar:
```
http://127.0.0.1:5002/companies/1/routines
```

### Cadastrar Nova Rotina:

1. **Nome da Rotina** (obrigatório)
   - Ex: "Relatório Mensal de Vendas"

2. **Processo Associado** (obrigatório)
   - Selecione da lista de processos cadastrados

3. **Tipo de Agendamento** (obrigatório)
   - **Diário:** Todos os dias em um horário específico
   - **Semanal:** Toda semana em um dia específico
   - **Mensal:** Todo mês em um dia específico
   - **Trimestral:** A cada 3 meses
   - **Anual:** Uma vez por ano
   - **Data Específica:** Data única (não se repete)

4. **Detalhes do Agendamento** (dinâmico)
   - Muda conforme o tipo selecionado
   - Ex: Horário, Dia da semana, Dia do mês, etc.

5. **Prazo (opcional)**
   - Quantos dias para concluir após disparo
   - Ex: 5 dias

6. **Data Limite Fixa (opcional)**
   - Ou defina uma data específica de vencimento

7. **Descrição** (opcional)
   - Observações e detalhes adicionais

---

## 📊 ESTRUTURA DO BANCO

### Tabela `routines` - Campos Adicionados:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `process_id` | INTEGER | ID do processo vinculado |
| `schedule_type` | TEXT | Tipo: daily, weekly, monthly, etc. |
| `schedule_value` | TEXT | Valor do agendamento (horário, dia, etc.) |
| `deadline_days` | INTEGER | Prazo em dias após disparo |
| `deadline_date` | TEXT | Data limite fixa |

### Campos Existentes:
- `id` - ID da rotina
- `company_id` - Empresa
- `name` - Nome da rotina
- `description` - Descrição
- `is_active` - Ativo/Inativo
- `created_at` - Data de criação
- `updated_at` - Última atualização

---

## 🎨 INTERFACE

### Formulário de Cadastro:
- ✅ Grid responsivo
- ✅ Campos dinâmicos conforme tipo de agendamento
- ✅ Validação em tempo real
- ✅ Hints explicativos em cada campo
- ✅ Botões: Limpar e Cadastrar

### Tabela de Rotinas:
- ✅ Lista todas as rotinas cadastradas
- ✅ Mostra processo vinculado
- ✅ Badge de agendamento (azul)
- ✅ Badge de prazo (amarelo)
- ✅ Ações: Editar e Excluir

### Empty State:
- ✅ Mensagem quando não há rotinas
- ✅ Orientação para cadastrar primeira

---

## 📋 TIPOS DE AGENDAMENTO

### 1. **Diário**
- Dispara todos os dias
- Valor: Horário (ex: 09:00)

### 2. **Semanal**
- Dispara toda semana
- Valor: Dia da semana (ex: Segunda-feira)

### 3. **Mensal**
- Dispara todo mês
- Valor: Dia do mês (1 a 31)

### 4. **Trimestral**
- Dispara a cada 3 meses
- Valor: Mês do trimestre (ex: Último mês)

### 5. **Anual**
- Dispara uma vez por ano
- Valor: Data (ex: 31/01)

### 6. **Data Específica**
- Disparo único
- Valor: Data completa

---

## 🔔 EXEMPLOS DE USO

### Exemplo 1: Relatório Mensal
```
Nome: Relatório Mensal de Vendas
Processo: AO.C.1.1.3 - Planejamento Estratégico
Agendamento: Mensal
Valor: Dia 5
Prazo: 3 dias
```

### Exemplo 2: Reunião Semanal
```
Nome: Reunião de Alinhamento
Processo: AO.C.1.3 - Gestão Estratégica
Agendamento: Semanal
Valor: Segunda-feira
Prazo: 1 dia (preparar pauta)
```

### Exemplo 3: Entrega Anual
```
Nome: Demonstrações Contábeis
Processo: AO.C.3.2.1 - Contabilidade
Agendamento: Anual
Valor: 31/03
Prazo: 15 dias
```

---

## 🔧 APIs CRIADAS

### GET - Listar Rotinas:
```
GET /api/companies/{company_id}/process-routines
```

**Response:**
```json
{
  "success": true,
  "routines": [
    {
      "id": 1,
      "name": "Relatório Mensal",
      "process_id": 3,
      "process_name": "AO.C.1.1.3 - Planejamento Estratégico",
      "schedule_type": "monthly",
      "schedule_value": "5",
      "deadline_days": 3,
      "deadline_date": null
    }
  ]
}
```

### POST - Criar Rotina:
```
POST /api/companies/{company_id}/process-routines
Content-Type: application/json

{
  "name": "Relatório Mensal",
  "process_id": 3,
  "schedule_type": "monthly",
  "schedule_value": "5",
  "deadline_days": 3,
  "description": "Relatório de vendas do mês"
}
```

### DELETE - Excluir Rotina:
```
DELETE /api/companies/{company_id}/process-routines/{routine_id}
```

---

## ✅ FUNCIONALIDADES IMPLEMENTADAS

### Cadastro:
- ✅ Formulário inline na mesma página
- ✅ Seleção de processo
- ✅ Tipo de agendamento dinâmico
- ✅ Prazo em dias OU data fixa
- ✅ Validação de campos obrigatórios

### Listagem:
- ✅ Tabela responsiva
- ✅ Badges visuais (agendamento e prazo)
- ✅ Informações do processo vinculado
- ✅ Ações rápidas (editar/excluir)

### Backend:
- ✅ Colunas adicionadas no banco
- ✅ APIs REST completas
- ✅ Validações de segurança
- ✅ Mensagens de erro claras

---

## 🔮 PRÓXIMAS ETAPAS (Futuro)

### 1. Associar Responsáveis
- Adicionar campo `responsible_user_id`
- Tabela de associação rotina <-> usuários
- Interface para definir responsáveis

### 2. Notificações Automáticas
- Disparo de e-mails/WhatsApp
- Alertas no dashboard
- Lembretes antes do vencimento

### 3. Acompanhamento
- Status: Pendente, Em Andamento, Concluído
- Histórico de execuções
- Relatórios de cumprimento

### 4. Acesso de Outras Páginas
- Link no dashboard da empresa
- Link na página do processo
- Atalho no menu GRV

---

## 📁 ARQUIVOS CRIADOS

### Template:
- `templates/process_routines.html` - Interface completa

### Backend:
- `app_pev.py` - Rotas e APIs adicionadas

### Banco de Dados:
- Colunas adicionadas na tabela `routines`

---

## 🎉 RESULTADO

Sistema **completo e funcional** para cadastrar rotinas de processos:

- ✅ Interface profissional
- ✅ Formulário inline
- ✅ Listagem com badges
- ✅ CRUD completo (Create, Read, Delete)
- ✅ Validações
- ✅ Preparado para expansão futura

**Acesse agora:**
```
http://127.0.0.1:5002/companies/1/routines
```

E comece a cadastrar suas rotinas! 📅

---

**Criado em:** 10/10/2025  
**Status:** Pronto para uso  
**Próximo:** Associar responsáveis




