# 👥 Sistema de Múltiplas Visões - My Work

## 🎯 Visão Geral

Sistema de 3 visões hierárquicas na mesma interface, permitindo que usuários naveguem entre diferentes escopos de visualização de atividades.

---

## 📊 As 3 Visões

### **👤 Minhas Atividades**
- **Escopo:** Atividades onde o usuário é responsável OU executor
- **Permissão:** Todos os usuários
- **Dados mostrados:**
  - Minhas atividades de projetos
  - Minhas instâncias de processos
  - Meu performance score
  - Minhas horas trabalhadas

### **👥 Minha Equipe**
- **Escopo:** Atividades de todos os membros da equipe do usuário
- **Permissão:** Usuários que são líderes de equipe ou membros
- **Dados mostrados:**
  - Atividades de todos os membros
  - Distribuição de carga da equipe
  - Alertas (sobrecarga, disponibilidade, atrasos)
  - Performance média da equipe
  - Ranking de produtividade

### **🏢 Empresa**
- **Escopo:** Todas as atividades da empresa
- **Permissão:** Gestores, diretores, executivos
- **Dados mostrados:**
  - Visão consolidada de todas as atividades
  - Comparação entre equipes/departamentos
  - Indicadores estratégicos
  - Análise de recursos

---

## 🎨 Componentes da Interface

### 1. **Abas de Navegação**

```
┌─────────────────────────────────────────────────────────┐
│  [👤 Minhas Atividades] [👥 Minha Equipe] [🏢 Empresa]  │
│   17 atividades         45 atividades     180 atividades │
└─────────────────────────────────────────────────────────┘
```

**Recursos:**
- Contador de atividades em cada aba
- Aba ativa destacada com gradiente azul
- Ícones SVG temáticos
- Animação ao trocar de aba
- Contexto atual exibido

### 2. **Team Overview** (Só aparece na aba "Minha Equipe")

```
┌───────────────────────────────────────────────────────┐
│  📊 Distribuição de Carga                             │
│  João Silva (Líder)      ████████░░ 80%    32h / 40h │
│  Maria Santos (Membro)   █████████░ 95% ⚠️ 38h / 40h │
│  Pedro Costa (Membro)    ██████░░░░ 60%    24h / 40h │
├───────────────────────────────────────────────────────┤
│  ⚠️ Alertas                                           │
│  ⚠️ Maria Santos sobrecarregada (95% capacidade)     │
│  🔴 8 atividades atrasadas (atenção imediata)        │
│  ✅ Pedro Costa disponível (16h livres)              │
├───────────────────────────────────────────────────────┤
│  📈 Performance da Equipe                             │
│  Score Médio: 78 pts                                  │
│  Taxa de Conclusão: 85% no prazo                      │
│  Capacidade Utilizada: 75% da equipe                  │
└───────────────────────────────────────────────────────┘
```

---

## 🔐 Sistema de Permissões

### **Backend - Definir privilégios do usuário**

```python
def get_user_privileges(user_id):
    """
    Retorna os privilégios de visualização do usuário
    
    Returns:
        {
            'can_view_own': True,        # Sempre True
            'can_view_team': True/False, # Se pertence a alguma equipe
            'can_view_company': True/False, # Se é gestor/executivo
            'team_id': 5,                # ID da equipe padrão
            'role': 'member'             # 'member', 'leader', 'manager', 'executive'
        }
    """
    user = User.query.get(user_id)
    
    # Verificar se é membro de alguma equipe
    team_membership = TeamMember.query.filter_by(user_id=user_id).first()
    
    # Verificar role para visão de empresa
    can_view_company = user.role in ['manager', 'executive', 'admin']
    
    return {
        'can_view_own': True,
        'can_view_team': team_membership is not None,
        'can_view_company': can_view_company,
        'team_id': team_membership.team_id if team_membership else None,
        'role': user.role
    }
```

### **API - Retornar privilégios**

```python
@my_work_bp.route('/api/privileges')
@login_required
def get_privileges():
    """Retorna privilégios de visualização do usuário"""
    privileges = get_user_privileges(current_user.id)
    
    return jsonify({
        'success': True,
        'data': privileges
    })
```

### **Frontend - Esconder abas sem permissão**

```javascript
async function loadUserPrivileges() {
  try {
    const response = await fetch('/my-work/api/privileges');
    const data = await response.json();
    
    if (data.success) {
      const privileges = data.data;
      
      // Esconder aba "Equipe" se não tiver permissão
      if (!privileges.can_view_team) {
        document.getElementById('tabTeam').style.display = 'none';
      }
      
      // Esconder aba "Empresa" se não tiver permissão
      if (!privileges.can_view_company) {
        document.getElementById('tabCompany').style.display = 'none';
      }
    }
  } catch (error) {
    console.error('Erro ao carregar privilégios:', error);
  }
}
```

---

## 📡 **Endpoints da API**

### **GET `/my-work/api/activities?scope=me|team|company`**

**Query Parameters:**
- `scope` - Escopo da visualização (me, team, company)
- `filter` - Filtro temporal (all, today, week, overdue)
- `search` - Busca por texto
- `sort` - Ordenação (deadline, priority, status)

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "type": "project",
      "title": "Revisar proposta...",
      "assigned_to": {
        "id": 10,
        "name": "João Silva"
      },
      "executor": {
        "id": 10,
        "name": "João Silva"
      },
      ...
    }
  ],
  "stats": {
    "pending": 12,
    "in_progress": 3,
    "overdue": 2,
    "completed": 45
  },
  "counts": {
    "me": 17,
    "team": 45,
    "company": 180
  }
}
```

### **GET `/my-work/api/team-overview`**

**Response:**
```json
{
  "success": true,
  "data": {
    "team_name": "Equipe Comercial",
    "members": [
      {
        "id": 10,
        "name": "João Silva",
        "role": "leader",
        "capacity": 40,
        "allocated": 32,
        "worked": 18,
        "utilization_percent": 80,
        "activities_count": 12
      }
    ],
    "alerts": [
      {
        "type": "overload",
        "severity": "warning",
        "user_id": 11,
        "user_name": "Maria Santos",
        "message": "Maria Santos sobrecarregada",
        "details": "38h alocadas (95% da capacidade)"
      }
    ],
    "performance": {
      "avg_score": 78,
      "completion_rate": 85,
      "capacity_utilization": 75
    }
  }
}
```

---

## 🔄 **Lógica de Queries (Backend)**

### **Visão "Minhas"**
```python
def get_my_activities(user_id):
    # Projetos onde sou responsável ou executor
    project_activities = db.session.query(ProjectActivity).filter(
        or_(
            ProjectActivity.responsible_id == user_id,
            ProjectActivity.executor_id == user_id
        ),
        ProjectActivity.is_deleted == False
    )
    
    # Processos onde sou executor
    process_instances = db.session.query(ProcessInstance).filter(
        ProcessInstance.executor_id == user_id,
        ProcessInstance.is_deleted == False
    )
    
    return combine_activities(project_activities, process_instances)
```

### **Visão "Equipe"**
```python
def get_team_activities(user_id):
    # Buscar equipe do usuário
    team = get_user_team(user_id)
    if not team:
        return []
    
    # Buscar IDs dos membros
    member_ids = [m.user_id for m in team.members]
    
    # Atividades de projetos da equipe
    project_activities = db.session.query(ProjectActivity).filter(
        or_(
            ProjectActivity.responsible_id.in_(member_ids),
            ProjectActivity.executor_id.in_(member_ids)
        ),
        ProjectActivity.is_deleted == False
    )
    
    # Instâncias de processos da equipe
    process_instances = db.session.query(ProcessInstance).filter(
        ProcessInstance.executor_id.in_(member_ids),
        ProcessInstance.is_deleted == False
    )
    
    return combine_activities(project_activities, process_instances)
```

### **Visão "Empresa"**
```python
def get_company_activities(user_id):
    # Verificar permissão
    if not can_view_company(user_id):
        raise PermissionError("Usuário sem permissão para visualizar atividades da empresa")
    
    # Buscar empresa do usuário
    user = User.query.get(user_id)
    company_id = user.company_id
    
    # Todas as atividades de projetos da empresa
    project_activities = db.session.query(ProjectActivity).filter(
        ProjectActivity.company_id == company_id,
        ProjectActivity.is_deleted == False
    )
    
    # Todas as instâncias de processos da empresa
    process_instances = db.session.query(ProcessInstance).filter(
        ProcessInstance.company_id == company_id,
        ProcessInstance.is_deleted == False
    )
    
    return combine_activities(project_activities, process_instances)
```

---

## 🎯 **Diferenças Visuais por Visão**

### **Cards de Estatísticas**
- **Minhas:** Números pessoais
- **Equipe:** Soma da equipe + indicador de quem está atrasado
- **Empresa:** Totais gerais + comparação entre equipes

### **Lista de Atividades**
- **Minhas:** Só minhas atividades
- **Equipe:** Mostra nome do executor em cada atividade
- **Empresa:** Mostra equipe + executor

### **Sidebar de Horas**
- **Minhas:** Minhas horas
- **Equipe:** Total da equipe (breakdown por pessoa)
- **Empresa:** Total da empresa (breakdown por equipe)

---

## 🚀 **Funcionalidades Especiais**

### **Visão de Equipe - Extras**

1. **Redistribuir Atividades** (Futuro)
   - Arrastar atividade de um membro para outro
   - Sistema de sugestões (quem tem capacidade)

2. **Alertas Inteligentes**
   - 🔴 Pessoa sobrecarregada (> 90% capacidade)
   - 🟡 Atividades em risco de atraso
   - 🟢 Pessoas com capacidade disponível

3. **Timeline da Equipe**
   - Visualizar próximos 7 dias
   - Ver quem está ocupado quando

4. **Matriz de Responsabilidade**
   - Ver quem está em quais projetos
   - Identificar dependências

---

## 📋 **Configuração de Equipes**

### **Criar Equipe:**
```python
team = Team(
    company_id=company_id,
    name="Equipe Comercial",
    leader_id=user_id
)
db.session.add(team)
db.session.commit()

# Adicionar membros
members = [
    TeamMember(team_id=team.id, user_id=10, role='leader'),
    TeamMember(team_id=team.id, user_id=11, role='member'),
    TeamMember(team_id=team.id, user_id=12, role='member'),
]
db.session.add_all(members)
db.session.commit()
```

### **Equipe "Empresa":**
- Opção especial que representa toda a empresa
- Criada automaticamente ou configurada por admin
- `team_id = NULL` ou `team_id = 0` = Empresa toda

---

## 🎨 **Layout Responsivo**

### **Desktop (> 1024px)**
```
┌───────────────────────────────────────┐
│ [👤 Minhas] [👥 Equipe] [🏢 Empresa] │
│  17 atv.     45 atv.     180 atv.    │
└───────────────────────────────────────┘
```

### **Mobile (< 768px)**
```
┌──────────────────────┐
│ [👤 Minhas Ativid.]  │
│  17 atividades       │
├──────────────────────┤
│ [👥 Minha Equipe]    │
│  45 atividades       │
├──────────────────────┤
│ [🏢 Empresa]         │
│  180 atividades      │
└──────────────────────┘
```

---

## 📊 **Exemplo de Uso - Cenários**

### **Cenário 1: Desenvolvedor Jr**
```
Privilégios:
✅ Pode ver: Minhas
❌ Não pode ver: Equipe, Empresa

Interface mostra:
- Apenas aba "Minhas Atividades"
- Suas próprias atividades
- Seu performance score
```

### **Cenário 2: Líder de Equipe**
```
Privilégios:
✅ Pode ver: Minhas, Equipe
❌ Não pode ver: Empresa

Interface mostra:
- Abas "Minhas" e "Minha Equipe"
- Na aba Equipe: Distribuição de carga, alertas, performance
- Pode identificar quem precisa de ajuda
```

### **Cenário 3: Gestor/Diretor**
```
Privilégios:
✅ Pode ver: Minhas, Equipe, Empresa

Interface mostra:
- Todas as 3 abas
- Visão estratégica completa
- Comparação entre equipes
- Indicadores consolidados
```

---

## 🔧 **Implementação no Backend**

### **1. Criar Models de Equipe**

```python
# models/team.py
from datetime import datetime
from . import db

class Team(db.Model):
    """Equipe de trabalho"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    members = db.relationship('TeamMember', backref='team', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'leader_id': self.leader_id,
            'members_count': self.members.count()
        }


class TeamMember(db.Model):
    """Membro de equipe"""
    __tablename__ = 'team_members'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(50), default='member')  # 'leader', 'member', 'viewer'
    
    # Auditoria
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Constraint: Usuário não pode estar duplicado na mesma equipe
    __table_args__ = (
        db.UniqueConstraint('team_id', 'user_id', name='unique_team_member'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'team_id': self.team_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None
        }
```

### **2. Atualizar Rotas para Suportar Scope**

```python
@my_work_bp.route('/api/activities')
@login_required
def get_activities():
    """Lista atividades conforme scope"""
    try:
        scope = request.args.get('scope', 'me')
        
        # Validar permissão
        privileges = get_user_privileges(current_user.id)
        
        if scope == 'team' and not privileges['can_view_team']:
            return jsonify({
                'success': False,
                'error': 'Sem permissão para visualizar atividades da equipe'
            }), 403
        
        if scope == 'company' and not privileges['can_view_company']:
            return jsonify({
                'success': False,
                'error': 'Sem permissão para visualizar atividades da empresa'
            }), 403
        
        # Buscar atividades conforme scope
        if scope == 'me':
            activities = get_my_activities(current_user.id)
        elif scope == 'team':
            activities = get_team_activities(current_user.id)
        elif scope == 'company':
            activities = get_company_activities(current_user.id)
        
        # Buscar contadores de todas as visões
        counts = {
            'me': count_my_activities(current_user.id),
            'team': count_team_activities(current_user.id) if privileges['can_view_team'] else 0,
            'company': count_company_activities(current_user.id) if privileges['can_view_company'] else 0
        }
        
        return jsonify({
            'success': True,
            'data': activities,
            'counts': counts
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
```

---

## 📊 **Cálculos Necessários**

### **Distribuição de Carga da Equipe**
```python
def get_team_load_distribution(team_id):
    """
    Calcula distribuição de carga entre membros da equipe
    """
    members = TeamMember.query.filter_by(team_id=team_id).all()
    
    distribution = []
    for member in members:
        user = User.query.get(member.user_id)
        
        # Calcular horas alocadas
        time_data = get_user_time_tracking_week(user.id)
        
        utilization = (time_data['planned'] / time_data['capacity']) * 100
        
        # Classificar status
        if utilization > 90:
            status = 'overload'
        elif utilization > 75:
            status = 'high'
        elif utilization < 50:
            status = 'available'
        else:
            status = 'normal'
        
        distribution.append({
            'id': user.id,
            'name': user.name,
            'role': member.role,
            'capacity': time_data['capacity'],
            'allocated': time_data['planned'],
            'worked': time_data['done'],
            'utilization_percent': round(utilization),
            'status': status,
            'activities_count': count_user_activities(user.id)
        })
    
    return sorted(distribution, key=lambda x: x['utilization_percent'], reverse=True)
```

### **Alertas da Equipe**
```python
def get_team_alerts(team_id):
    """
    Gera alertas automáticos da equipe
    """
    alerts = []
    members = get_team_load_distribution(team_id)
    
    # Verificar sobrecarga
    for member in members:
        if member['status'] == 'overload':
            alerts.append({
                'type': 'overload',
                'severity': 'warning',
                'user_id': member['id'],
                'user_name': member['name'],
                'message': f"{member['name']} sobrecarregado(a)",
                'details': f"{member['allocated']}h alocadas ({member['utilization_percent']}% da capacidade)"
            })
        
        if member['status'] == 'available':
            alerts.append({
                'type': 'available',
                'severity': 'success',
                'user_id': member['id'],
                'user_name': member['name'],
                'message': f"{member['name']} disponível",
                'details': f"{member['capacity'] - member['allocated']}h de capacidade livre"
            })
    
    # Verificar atividades atrasadas
    overdue_count = count_team_overdue_activities(team_id)
    if overdue_count > 0:
        alerts.append({
            'type': 'overdue',
            'severity': 'danger',
            'message': f"{overdue_count} atividades atrasadas",
            'details': "Requer atenção imediata"
        })
    
    return alerts
```

---

## ✅ **Status de Implementação**

```
Frontend:  ✅ 100% Completo
- [x] Abas de navegação
- [x] Team Overview cards
- [x] JavaScript de troca de abas
- [x] CSS responsivo
- [x] Animações e transições

Backend:   ⏳ Pendente
- [ ] Models de Team e TeamMember
- [ ] Endpoints com parâmetro scope
- [ ] Sistema de privilégios
- [ ] Cálculos de distribuição de carga
- [ ] Geração de alertas
```

---

## 📱 **Para Testar Agora**

Reinicie o Docker e acesse: `http://127.0.0.1:5003/my-work-demo`

**Teste:**
1. ✅ Clicar na aba "Minhas Atividades"
2. ✅ Clicar na aba "Minha Equipe" → Veja o Team Overview aparecer
3. ✅ Clicar na aba "Empresa"
4. ✅ Observe o título e subtítulo mudarem
5. ✅ Observe o contador de atividades mudar

---

**Versão:** 1.0  
**Data:** 21/10/2025  
**Status:** ✅ Frontend Completo - Aguardando Backend

