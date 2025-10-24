# 🔧 Guia de Integração - My Work

## 📋 Checklist de Integração

### Fase 1: Visualização (✅ COMPLETO)
- [x] Template HTML criado
- [x] CSS moderno implementado
- [x] JavaScript interativo funcional
- [x] Rota demo criada

### Fase 2: Backend (⏳ PRÓXIMO)
- [ ] Criar módulo `modules/my_work/`
- [ ] Implementar rotas API
- [ ] Criar services de lógica de negócio
- [ ] Integrar com models existentes
- [ ] Implementar cálculo de performance
- [ ] Criar páginas de detalhamento

### Fase 3: Integração (🔜 FUTURO)
- [ ] Adicionar link no menu principal
- [ ] Notificações de atividades
- [ ] Testes automatizados
- [ ] Documentação de API

---

## 🚀 Passo a Passo de Integração

### **1. Testar Visualização (Agora)**

#### Opção A: Rota Temporária
```python
# No app.py ou __init__.py, adicionar:
from my_work_demo import my_work_bp
app.register_blueprint(my_work_bp)
```

Acessar: `http://127.0.0.1:5003/my-work/`

#### Opção B: Rota Direta (mais rápido)
```python
# No app.py
@app.route('/my-work-demo')
def my_work_demo():
    return render_template('my_work.html')
```

---

### **2. Criar Estrutura de Módulo**

```bash
mkdir -p modules/my_work
touch modules/my_work/__init__.py
touch modules/my_work/routes.py
touch services/my_work_service.py
```

---

### **3. Implementar Backend Básico**

#### `modules/my_work/__init__.py`
```python
"""
Módulo My Work - Minhas Atividades
"""
from flask import Blueprint

my_work_bp = Blueprint(
    'my_work',
    __name__,
    url_prefix='/my-work'
)

from . import routes
```

#### `modules/my_work/routes.py`
```python
"""
Rotas do módulo My Work
"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from . import my_work_bp
from services.my_work_service import (
    get_user_activities,
    get_user_stats,
    get_user_performance,
    update_activity_status,
    approve_process_instance,
    reject_process_instance
)
from middleware.auto_log_decorator import auto_log_crud


@my_work_bp.route('/')
@login_required
def dashboard():
    """Página principal - Minhas Atividades"""
    return render_template('my_work.html')


@my_work_bp.route('/api/activities')
@login_required
def get_activities():
    """API: Lista de atividades do usuário"""
    try:
        filters = {
            'filter': request.args.get('filter', 'all'),
            'search': request.args.get('search', ''),
            'sort': request.args.get('sort', 'deadline')
        }
        
        activities = get_user_activities(current_user.id, filters)
        
        return jsonify({
            'success': True,
            'data': activities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/stats')
@login_required
def get_stats():
    """API: Estatísticas do usuário"""
    try:
        stats = get_user_stats(current_user.id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/performance')
@login_required
def get_performance():
    """API: Performance score do usuário"""
    try:
        performance = get_user_performance(current_user.id)
        
        return jsonify({
            'success': True,
            'data': performance
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/activities/<int:activity_id>/status', methods=['PUT'])
@login_required
@auto_log_crud('activity')
def update_status(activity_id):
    """API: Atualizar status de atividade"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status obrigatório'
            }), 400
        
        activity = update_activity_status(
            activity_id,
            current_user.id,
            new_status
        )
        
        return jsonify({
            'success': True,
            'data': activity
        })
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/process-instances/<int:instance_id>/approve', methods=['POST'])
@login_required
@auto_log_crud('process_instance')
def approve_instance(instance_id):
    """API: Aprovar instância de processo"""
    try:
        instance = approve_process_instance(instance_id, current_user.id)
        
        return jsonify({
            'success': True,
            'data': instance,
            'message': 'Instância aprovada com sucesso'
        })
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/api/process-instances/<int:instance_id>/reject', methods=['POST'])
@login_required
@auto_log_crud('process_instance')
def reject_instance(instance_id):
    """API: Rejeitar instância de processo"""
    try:
        data = request.get_json()
        reason = data.get('reason')
        
        if not reason:
            return jsonify({
                'success': False,
                'error': 'Motivo obrigatório'
            }), 400
        
        instance = reject_process_instance(
            instance_id,
            current_user.id,
            reason
        )
        
        return jsonify({
            'success': True,
            'data': instance,
            'message': 'Instância rejeitada'
        })
    except PermissionError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 403
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@my_work_bp.route('/activity/<int:activity_id>')
@login_required
def view_activity(activity_id):
    """Página de detalhes da atividade de projeto"""
    # TODO: Implementar página de detalhamento
    return "Detalhes da atividade (em desenvolvimento)"


@my_work_bp.route('/process-instance/<int:instance_id>')
@login_required
def view_process_instance(instance_id):
    """Página de detalhes da instância de processo"""
    # TODO: Implementar página de detalhamento
    return "Detalhes da instância (em desenvolvimento)"
```

#### `services/my_work_service.py`
```python
"""
Service para My Work - Lógica de negócio
"""
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
from models import db
# from models.activity import Activity  # TODO: Ajustar import
# from models.process_instance import ProcessInstance  # TODO: Ajustar import


def get_user_activities(user_id, filters=None):
    """
    Retorna atividades do usuário (projetos + processos)
    
    Args:
        user_id: ID do usuário
        filters: Dict com filtros (filter, search, sort)
    
    Returns:
        List de atividades formatadas
    """
    filters = filters or {}
    
    # TODO: Implementar query real
    # Exemplo:
    # activities = Activity.query.filter(
    #     or_(
    #         Activity.responsible_id == user_id,
    #         Activity.executor_id == user_id
    #     ),
    #     Activity.is_deleted == False
    # )
    
    # Aplicar filtros
    filter_type = filters.get('filter', 'all')
    if filter_type == 'today':
        # activities = activities.filter(Activity.deadline <= datetime.now().date())
        pass
    elif filter_type == 'week':
        # week_end = datetime.now() + timedelta(days=7)
        # activities = activities.filter(Activity.deadline <= week_end.date())
        pass
    elif filter_type == 'overdue':
        # activities = activities.filter(Activity.deadline < datetime.now().date())
        pass
    
    # Busca
    search = filters.get('search', '')
    if search:
        # activities = activities.filter(
        #     or_(
        #         Activity.title.ilike(f'%{search}%'),
        #         Activity.description.ilike(f'%{search}%')
        #     )
        # )
        pass
    
    # Ordenação
    sort_by = filters.get('sort', 'deadline')
    # if sort_by == 'deadline':
    #     activities = activities.order_by(Activity.deadline.asc())
    # elif sort_by == 'priority':
    #     activities = activities.order_by(Activity.priority.desc())
    
    # TODO: Retornar atividades reais
    # return [activity.to_dict() for activity in activities.all()]
    
    # Mock para teste
    return []


def get_user_stats(user_id):
    """
    Retorna estatísticas do usuário
    
    Returns:
        Dict com contadores
    """
    # TODO: Implementar queries reais
    
    return {
        'pending': 12,
        'in_progress': 3,
        'overdue': 2,
        'completed': 45,
        'trends': {
            'pending': '+2',
            'in_progress': '0',
            'overdue': '-1',
            'completed': '+10'
        }
    }


def get_user_performance(user_id):
    """
    Calcula performance score do usuário
    
    Returns:
        Dict com score, badges e relatórios
    """
    # TODO: Implementar cálculo real
    
    score = calculate_performance_score(user_id)
    badges = calculate_badges(user_id)
    reports = calculate_reports(user_id)
    
    status = 'excellent' if score >= 80 else 'good' if score >= 60 else 'needs_improvement'
    
    return {
        'score': score,
        'status': status,
        'badges': badges,
        'reports': reports
    }


def calculate_performance_score(user_id):
    """Calcula pontuação de performance (0-100)"""
    # TODO: Implementar cálculo baseado em:
    # - Taxa de conclusão no prazo
    # - Produtividade (vs média)
    # - Streak de dias ativos
    # - Tempo médio de resposta
    
    return 85


def calculate_badges(user_id):
    """Calcula badges do usuário"""
    badges = []
    
    # TODO: Implementar lógica real
    # Streak
    streak_days = 7  # get_active_streak_days(user_id)
    if streak_days >= 3:
        badges.append({
            'type': 'streak',
            'icon': '🔥',
            'label': f'{streak_days} dias',
            'description': f'Sequência de {streak_days} dias consecutivos'
        })
    
    # Produtividade
    completed_week = 10  # get_completed_this_week(user_id)
    if completed_week >= 5:
        badges.append({
            'type': 'productivity',
            'icon': '🏆',
            'label': f'{completed_week}/semana',
            'description': f'{completed_week} atividades concluídas esta semana'
        })
    
    return badges


def calculate_reports(user_id):
    """Calcula dados de relatórios"""
    # TODO: Implementar queries reais
    
    return {
        'productivity_weekly': {
            'values': [6, 8, 7, 9, 8, 4, 0],
            'total': 10,
            'summary': '10 atividades concluídas esta semana'
        },
        'avg_completion_time': {
            'value': 2.5,
            'unit': 'dias',
            'comparison': '+15%',
            'summary': '15% mais rápido que no mês passado'
        },
        'completion_rate': {
            'percent': 80,
            'completed': 45,
            'total': 56,
            'summary': '45 de 56 atividades concluídas'
        }
    }


def update_activity_status(activity_id, user_id, new_status):
    """Atualiza status de atividade"""
    # TODO: Implementar
    # 1. Buscar atividade
    # 2. Verificar permissão
    # 3. Atualizar status
    # 4. Registrar log
    
    raise NotImplementedError("TODO: Implementar")


def approve_process_instance(instance_id, user_id):
    """Aprova instância de processo"""
    # TODO: Implementar
    # 1. Buscar instância
    # 2. Verificar se usuário é executor
    # 3. Aprovar
    # 4. Avançar para próxima etapa
    
    raise NotImplementedError("TODO: Implementar")


def reject_process_instance(instance_id, user_id, reason):
    """Rejeita instância de processo"""
    # TODO: Implementar
    # 1. Buscar instância
    # 2. Verificar se usuário é executor
    # 3. Rejeitar com motivo
    # 4. Retornar para etapa anterior ou finalizar
    
    raise NotImplementedError("TODO: Implementar")
```

---

### **4. Registrar Blueprint no App**

#### `app.py` ou `__init__.py`
```python
# Importar blueprint
from modules.my_work import my_work_bp

# Registrar
app.register_blueprint(my_work_bp)

print("✅ My Work module registered at /my-work")
```

---

### **5. Adicionar Link no Menu**

#### `templates/base.html`
```html
<div class="header-nav">
  <a href="/main" class="nav-link">Ecossistema</a>
  <a href="{{ url_for('pev.pev_dashboard') }}" class="nav-link">PEV</a>
  <a href="{{ url_for('grv.grv_dashboard') }}" class="nav-link">GRV</a>
  <!-- NOVO -->
  <a href="{{ url_for('my_work.dashboard') }}" class="nav-link">Minhas Atividades</a>
</div>
```

---

### **6. Conectar JavaScript com API**

#### Atualizar `static/js/my-work.js`

Descomentar as chamadas de API:
```javascript
async function loadActivitiesData() {
  try {
    // Chamar API real
    const response = await fetch('/my-work/api/activities');
    const data = await response.json();
    
    if (data.success) {
      state.activities = data.data;
      renderActivities(data.data);
    }
    
    // Carregar stats
    const statsResponse = await fetch('/my-work/api/stats');
    const statsData = await statsResponse.json();
    if (statsData.success) {
      updateStats(statsData.data);
    }
    
    // Carregar performance
    const perfResponse = await fetch('/my-work/api/performance');
    const perfData = await perfResponse.json();
    if (perfData.success) {
      updatePerformanceScore(perfData.data);
    }
  } catch (error) {
    console.error('Erro ao carregar atividades:', error);
    window.showMessage('Erro ao carregar atividades', 'error');
  }
}
```

---

## 🧪 Testando a Integração

### Checklist de Testes

1. **Frontend Standalone:**
   - [ ] Página carrega sem erros
   - [ ] CSS aplicado corretamente
   - [ ] Filtros funcionam
   - [ ] Busca funciona
   - [ ] Botões interativos

2. **API Endpoints:**
   ```bash
   # Testar com curl ou Postman
   curl http://localhost:5003/my-work/api/activities
   curl http://localhost:5003/my-work/api/stats
   curl http://localhost:5003/my-work/api/performance
   ```

3. **Integração Completa:**
   - [ ] Login funciona
   - [ ] Dados carregam da API
   - [ ] Ações atualizam backend
   - [ ] Logs são registrados
   - [ ] Permissões são verificadas

---

## 🐛 Troubleshooting

### Problema: Página não carrega
- Verificar se blueprint está registrado
- Verificar rota no Flask: `flask routes | grep my-work`
- Verificar logs do console

### Problema: CSS não aplicado
- Verificar se arquivo existe: `static/css/my-work.css`
- Limpar cache do navegador (Ctrl+F5)
- Verificar console do navegador

### Problema: JavaScript não funciona
- Verificar console do navegador (F12)
- Verificar se arquivo existe: `static/js/my-work.js`
- Verificar se jQuery não está conflitando

### Problema: API retorna 404
- Verificar se blueprint está registrado
- Verificar nome da rota
- Verificar `@login_required` (fazer login primeiro)

---

## 📝 Notas de Implementação

### Prioridades:
1. **MVP:** Listar atividades + Filtros básicos
2. **V1:** APIs completas + Ações funcionais
3. **V2:** Performance score + Badges
4. **V3:** Relatórios + Páginas de detalhamento

### Dependências:
- Models de `Activity` e `ProcessInstance` devem existir
- Campos necessários nos models:
  - `responsible_id`, `executor_id`
  - `status`, `priority`, `deadline`
  - `is_deleted`, `created_at`, `updated_at`

### Performance:
- Indexar colunas: `responsible_id`, `executor_id`, `deadline`, `status`
- Considerar cache para performance score (calcular 1x/hora)
- Paginar lista de atividades (20-50 por página)

---

## 🎯 Roadmap

### Sprint 1 (Esta semana):
- [x] Frontend completo
- [ ] Backend básico (listar atividades)
- [ ] Integração API + Frontend

### Sprint 2 (Próxima semana):
- [ ] Ações (iniciar, pausar, aprovar)
- [ ] Páginas de detalhamento
- [ ] Performance score básico

### Sprint 3 (Futuro):
- [ ] Sistema de badges
- [ ] Relatórios avançados
- [ ] Notificações

---

## 📚 Documentação Adicional

- `docs/MY_WORK_FRONTEND.md` - Detalhes do frontend
- `docs/governance/API_STANDARDS.md` - Padrões de API
- `docs/governance/CODING_STANDARDS.md` - Padrões de código

---

**Última atualização:** 21/10/2025  
**Status:** ✅ Pronto para backend

