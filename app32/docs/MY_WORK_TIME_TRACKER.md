# ⏱️ Painel de Controle de Horas - My Work

## 🎯 Visão Geral

Adicionado **painel de controle de horas** no lado direito da página "Minhas Atividades", permitindo que o usuário visualize e gerencie suas horas previstas vs realizadas.

---

## ✅ O Que Foi Implementado

### 📍 Localização
- **Sidebar direito** (380px de largura)
- **Sticky** (acompanha o scroll)
- **Responsivo** (vai para baixo em telas menores)

### 🔄 Duas Visualizações

#### 1. **Visão do Dia (Hoje)**
- ⏱️ **Resumo em 3 cards:**
  - Capacidade (8h padrão)
  - Previsto (soma das horas estimadas)
  - Realizado (soma das horas trabalhadas)

- 📊 **Barra de Progresso:**
  - Verde: Realizado
  - Azul claro: Previsto restante
  - Cinza: Tempo livre

- 📁 **Detalhamento por Tipo:**
  - **Atividades de Projetos**
    - Previsto vs Realizado
    - Mini barra de progresso
    - Contagem de atividades
  
  - **Instâncias de Processos**
    - Previsto vs Realizado
    - Mini barra de progresso
    - Contagem de instâncias
  
  - **Outros / Disponível**
    - Diferença entre capacidade e previsto
    - Destaque visual (amarelo)

- ⚠️ **Alerta de Sobrecarga:**
  - Aparece quando previsto > capacidade

#### 2. **Visão da Semana**
- ⏱️ **Resumo em 3 cards:**
  - Capacidade (40h padrão - 5 dias)
  - Previsto semanal
  - Realizado semanal

- 📊 **Barra de Progresso Semanal**

- 📅 **Gráfico de Barras por Dia:**
  - Segunda a Sexta
  - Barras empilhadas (realizado + previsto)
  - Dia atual destacado com badge "HOJE"
  - Tooltip com valores

- 📁 **Detalhamento Semanal por Tipo:**
  - Atividades de Projetos
  - Instâncias de Processos
  - Outros / Disponível

---

## 🎨 Visual Implementado

### Layout de 2 Colunas
```
┌─────────────────────────────────┬─────────────────┐
│                                 │                 │
│  CONTEÚDO PRINCIPAL             │   SIDEBAR       │
│  (Atividades, Filtros, etc)     │  (Controle de   │
│                                 │   Horas)        │
│                                 │                 │
│                                 │   ⏱️ Hoje/Semana│
│                                 │   📊 Resumo     │
│                                 │   📁 Projetos   │
│                                 │   ⚙️ Processos  │
│                                 │   📋 Outros     │
│                                 │                 │
│                                 │   💡 Dica       │
└─────────────────────────────────┴─────────────────┘
```

### Cores e Estilos
- **Verde (#10b981):** Realizado
- **Azul (#06b6d4):** Previsto
- **Amarelo (#fbbf24):** Disponível/Outros
- **Vermelho (#ef4444):** Sobrecarga/Alerta

### Ícones
- 📁 Atividades de Projetos (azul claro)
- ⚙️ Instâncias de Processos (roxo)
- 📋 Outros / Disponível (amarelo)

---

## 🔧 Funcionalidades JavaScript

### Troca de Abas (Hoje ↔ Semana)
```javascript
initializeTimeTracker()
// Adiciona listeners nos botões "Hoje" e "Semana"
// Alterna entre as duas visualizações
```

### Cálculo Automático
```javascript
calculateTimeFromActivities(activities)
// Calcula horas previstas e realizadas
// Agrupa por tipo (projeto, processo)
// Calcula tempo disponível
```

### Atualização Dinâmica
```javascript
updateTimeTracking(data)
// Atualiza visão do dia
// Atualiza visão da semana
// Mostra alerta de sobrecarga se necessário
```

---

## 📊 Formato de Dados Esperado (Backend)

### API Endpoint Sugerido
```
GET /my-work/api/time-tracking?period=day|week
```

### Response Format
```json
{
  "success": true,
  "data": {
    "day": {
      "capacity": 8,
      "planned": 6.5,
      "done": 4.25,
      "projects": {
        "planned": 4,
        "done": 2.75,
        "count": 3
      },
      "processes": {
        "planned": 2.5,
        "done": 1.5,
        "count": 2
      },
      "available": 1.5
    },
    "week": {
      "capacity": 40,
      "planned": 32,
      "done": 18.5,
      "projects": {
        "planned": 20,
        "done": 12,
        "count": 12
      },
      "processes": {
        "planned": 12,
        "done": 6.5,
        "count": 8
      },
      "available": 8,
      "daily_breakdown": [
        {
          "day": "seg",
          "date": "2025-10-20",
          "planned": 8,
          "done": 6
        },
        {
          "day": "ter",
          "date": "2025-10-21",
          "planned": 8,
          "done": 5
        }
        // ... outros dias
      ]
    }
  }
}
```

---

## 🗄️ Campos Necessários no Banco

### Atividades de Projetos
```sql
ALTER TABLE activities ADD COLUMN estimated_hours DECIMAL(5,2);
ALTER TABLE activities ADD COLUMN worked_hours DECIMAL(5,2);
```

### Instâncias de Processos
```sql
ALTER TABLE process_instances ADD COLUMN estimated_hours DECIMAL(5,2);
ALTER TABLE process_instances ADD COLUMN worked_hours DECIMAL(5,2);
```

### Configuração do Usuário (Opcional)
```sql
ALTER TABLE users ADD COLUMN daily_capacity DECIMAL(4,2) DEFAULT 8.0;
ALTER TABLE users ADD COLUMN weekly_capacity DECIMAL(5,2) DEFAULT 40.0;
```

---

## 🔄 Cálculos Necessários (Backend Service)

### 1. Calcular Horas do Dia
```python
def get_user_time_tracking_day(user_id, date=None):
    """
    Calcula horas previstas e realizadas do dia
    
    Args:
        user_id: ID do usuário
        date: Data específica (default: hoje)
    
    Returns:
        Dict com horas do dia
    """
    if not date:
        date = datetime.now().date()
    
    # Buscar atividades de projetos do dia
    project_activities = Activity.query.filter(
        or_(
            Activity.responsible_id == user_id,
            Activity.executor_id == user_id
        ),
        Activity.deadline == date,
        Activity.is_deleted == False,
        Activity.status != 'completed'
    ).all()
    
    # Buscar instâncias de processos do dia
    process_instances = ProcessInstance.query.filter(
        ProcessInstance.executor_id == user_id,
        ProcessInstance.due_date == date,
        ProcessInstance.is_deleted == False,
        ProcessInstance.status != 'completed'
    ).all()
    
    # Calcular totais
    projects_planned = sum(a.estimated_hours or 0 for a in project_activities)
    projects_done = sum(a.worked_hours or 0 for a in project_activities)
    
    processes_planned = sum(p.estimated_hours or 0 for p in process_instances)
    processes_done = sum(p.worked_hours or 0 for p in process_instances)
    
    # Capacidade do usuário
    user = User.query.get(user_id)
    capacity = user.daily_capacity or 8.0
    
    total_planned = projects_planned + processes_planned
    total_done = projects_done + processes_done
    available = capacity - total_planned
    
    return {
        'capacity': capacity,
        'planned': total_planned,
        'done': total_done,
        'available': available,
        'projects': {
            'planned': projects_planned,
            'done': projects_done,
            'count': len(project_activities)
        },
        'processes': {
            'planned': processes_planned,
            'done': processes_done,
            'count': len(process_instances)
        }
    }
```

### 2. Calcular Horas da Semana
```python
def get_user_time_tracking_week(user_id, start_date=None):
    """
    Calcula horas previstas e realizadas da semana
    
    Args:
        user_id: ID do usuário
        start_date: Início da semana (default: segunda-feira desta semana)
    
    Returns:
        Dict com horas da semana
    """
    if not start_date:
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())
    
    end_date = start_date + timedelta(days=4)  # Sexta-feira
    
    # Buscar atividades da semana
    project_activities = Activity.query.filter(
        or_(
            Activity.responsible_id == user_id,
            Activity.executor_id == user_id
        ),
        Activity.deadline >= start_date,
        Activity.deadline <= end_date,
        Activity.is_deleted == False
    ).all()
    
    process_instances = ProcessInstance.query.filter(
        ProcessInstance.executor_id == user_id,
        ProcessInstance.due_date >= start_date,
        ProcessInstance.due_date <= end_date,
        ProcessInstance.is_deleted == False
    ).all()
    
    # Calcular totais
    projects_planned = sum(a.estimated_hours or 0 for a in project_activities)
    projects_done = sum(a.worked_hours or 0 for a in project_activities)
    
    processes_planned = sum(p.estimated_hours or 0 for p in process_instances)
    processes_done = sum(p.worked_hours or 0 for p in process_instances)
    
    # Capacidade semanal
    user = User.query.get(user_id)
    capacity = user.weekly_capacity or 40.0
    
    total_planned = projects_planned + processes_planned
    total_done = projects_done + processes_done
    available = capacity - total_planned
    
    # Breakdown por dia
    daily_breakdown = []
    for i in range(5):  # Segunda a Sexta
        day_date = start_date + timedelta(days=i)
        day_data = get_user_time_tracking_day(user_id, day_date)
        daily_breakdown.append({
            'day': ['seg', 'ter', 'qua', 'qui', 'sex'][i],
            'date': day_date.isoformat(),
            'planned': day_data['planned'],
            'done': day_data['done']
        })
    
    return {
        'capacity': capacity,
        'planned': total_planned,
        'done': total_done,
        'available': available,
        'projects': {
            'planned': projects_planned,
            'done': projects_done,
            'count': len(project_activities)
        },
        'processes': {
            'planned': processes_planned,
            'done': processes_done,
            'count': len(process_instances)
        },
        'daily_breakdown': daily_breakdown
    }
```

---

## 📱 Responsividade

### Desktop (> 1200px)
- Sidebar: 380px
- Layout de 2 colunas

### Tablet (1024px - 1200px)
- Sidebar: 320px
- Layout de 2 colunas (compactado)

### Mobile (< 1024px)
- Sidebar vai para baixo
- Layout de 1 coluna
- Abas Hoje/Semana ocupam largura total

---

## 💡 Card de Dica

Adicionado card roxo com dica de produtividade:
```
💡 Dica de Produtividade
Distribua suas atividades ao longo do dia para 
manter o equilíbrio entre previsto e realizado.
```

---

## 🎯 Benefícios

1. ✅ **Visibilidade:** Usuário vê suas horas de forma clara
2. ✅ **Controle:** Sabe quanto tempo tem disponível
3. ✅ **Planejamento:** Evita sobrecarga
4. ✅ **Análise:** Compara previsto vs realizado
5. ✅ **Gestão:** Identifica gargalos
6. ✅ **Produtividade:** Distribui melhor as tarefas

---

## 🚀 Próximos Passos (Backend)

1. [ ] Adicionar campos `estimated_hours` e `worked_hours` nos models
2. [ ] Criar service `my_work_time_service.py`
3. [ ] Implementar endpoint `/my-work/api/time-tracking`
4. [ ] Conectar frontend com API real
5. [ ] Adicionar campo de capacidade nas configurações do usuário
6. [ ] Implementar registro de horas trabalhadas (timer?)

---

## 📝 Exemplo de Uso

### Cenário 1: Dia Normal
```
Capacidade: 8h
Previsto: 6h 30min
Realizado: 4h 15min
Disponível: 1h 30min

Status: ✅ Dentro da capacidade
Progresso: 65% do previsto concluído
```

### Cenário 2: Sobrecarga
```
Capacidade: 8h
Previsto: 10h
Realizado: 3h
Disponível: -2h

Status: ⚠️ ALERTA: Sobrecarga!
Ação: Redistribuir atividades
```

### Cenário 3: Tempo Livre
```
Capacidade: 8h
Previsto: 4h
Realizado: 3h
Disponível: 4h

Status: ✅ Tempo disponível
Sugestão: Buscar novas atividades
```

---

**Versão:** 1.0  
**Data:** 21/10/2025  
**Status:** ✅ Frontend Completo - Aguardando Backend

