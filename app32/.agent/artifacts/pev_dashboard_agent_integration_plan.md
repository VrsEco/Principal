# 🚀 Plano de Integração: Dashboard PEV com Agentes IA

**Data:** 15/02/2026  
**Objetivo:** Reconstruir o dashboard PEV (`/pev/dashboard`) integrando a estrutura de agentes IA para auxiliar no desenvolvimento e análise estratégica.

---

## 📋 Contexto Atual

### Estrutura Existente

#### 1. **Dashboard PEV Atual** (`/pev/dashboard`)
- **Rota:** `c:\GestaoVersus\app32\api\routes\pev.py` (linha 267)
- **Template:** `templates/modules/pev/plan_selector_compact.html`
- **Funcionalidade:** Lista planos da empresa ativa, mostra métricas básicas
- **Limitações:** Interface básica, sem análise inteligente, sem sugestões proativas

#### 2. **Estrutura de Agentes Existente**
- **Board Agents** (`agents/board/`):
  - `supervisor.py` - Orquestrador principal
  - `cso.py` - Chief Strategy Officer (estratégia)
  - `skeptic.py` - Analista crítico
  - `coo.py` - Chief Operating Officer (operações)
  
- **Intelligence Agents** (`src/intelligence/agents/`):
  - `supervisor.py` - Roteador de consultas
  - `expert.py` - Especialista técnico
  - `specialists.py` - Especialistas específicos

- **Graph Orchestration** (`agents/graph.py`):
  - LangGraph com MemorySaver
  - Padrão Supervisor-Worker
  - Human-in-the-loop (HITL)

#### 3. **Documentação de Agentes**
- `docs/SISTEMA_AGENTES_IA.md` - Arquitetura completa
- Agentes propostos:
  - **Agente PEV** - Planejamento Estratégico Visionário
  - **Agente Processos** - Otimizador de Eficiência
  - **Agente Rotina** - Gestor de Atividades
  - **Agente Performance** - Analista de Desempenho
  - **Agente Estratégico** - Monitor do PEV

---

## 🎯 Objetivos da Reconstrução

### 1. **Interface Modernizada**
- Dashboard com design premium e interativo
- Cards com análises em tempo real
- Visualizações de dados inteligentes
- Micro-animações e feedback visual

### 2. **Integração com Agentes IA**
- **Análise Automática de Planos**
  - Avaliação de maturidade estratégica
  - Identificação de gaps e oportunidades
  - Sugestões proativas de melhorias
  
- **Assistente Interativo**
  - Chat integrado no dashboard
  - Consultas sobre planejamento
  - Análise de mercado e benchmarking
  
- **Monitoramento Inteligente**
  - Alertas sobre desvios
  - Recomendações de ações
  - Análise de progresso vs. metas

### 3. **Funcionalidades Avançadas**
- **Análise de Planos com IA**
  - Validação de OKRs
  - Análise de direcionadores
  - Avaliação de coerência estratégica
  
- **Insights Proativos**
  - Identificação de riscos
  - Oportunidades de melhoria
  - Comparação com benchmarks
  
- **Relatórios Automatizados**
  - Resumos executivos gerados por IA
  - Análises de tendências
  - Recomendações personalizadas

---

## 🏗️ Arquitetura Proposta

### Camadas da Solução

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Dashboard PEV)                      │
│  ├─ Interface Modernizada (HTML/CSS/JS)                         │
│  ├─ Cards Interativos com Análises                              │
│  ├─ Chat Widget (Assistente IA)                                 │
│  └─ Visualizações de Dados                                      │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (Flask Routes)                      │
│  ├─ /pev/dashboard (Dashboard principal)                        │
│  ├─ /pev/api/analyze-plan (Análise de plano)                   │
│  ├─ /pev/api/chat (Chat com assistente)                        │
│  └─ /pev/api/insights (Insights proativos)                     │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATION                           │
│  ├─ PEV Agent (Análise estratégica)                            │
│  ├─ Board Supervisor (Orquestração)                            │
│  ├─ CSO Agent (Estratégia)                                     │
│  ├─ Skeptic Agent (Análise crítica)                            │
│  └─ Expert Agent (Consultas técnicas)                          │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DATA & TOOLS                                  │
│  ├─ Database (PostgreSQL)                                       │
│  ├─ RAG System (ChromaDB)                                       │
│  ├─ OpenAI API (GPT-4o)                                        │
│  └─ External APIs (Google Search, etc.)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Plano de Implementação

### **FASE 1: Preparação e Estrutura Base** (2-3 horas)

#### 1.1. Criar Agente PEV Especializado
**Arquivo:** `agents/pev/pev_agent.py`

```python
"""
Agente PEV - Planejamento Estratégico Visionário
Especializado em análise e sugestões para planejamento estratégico.
"""
from langchain_core.messages import SystemMessage
from src.intelligence.llm import model_with_tools

class PEVAgent:
    def __init__(self):
        self.system_prompt = """
        Você é o Agente PEV (Planejamento Estratégico Visionário) do Gestão Versus.
        
        Sua missão é:
        1. Analisar planos estratégicos de forma CRÍTICA e PROVOCATIVA
        2. Identificar gaps, inconsistências e oportunidades
        3. Sugerir melhorias concretas e acionáveis
        4. Validar OKRs, direcionadores e projetos
        5. Fornecer insights baseados em benchmarks e melhores práticas
        
        Seja sempre:
        - ESPECÍFICO (dados concretos, não generalidades)
        - PROVOCATIVO (desafie o status quo)
        - ACIONÁVEL (recomendações práticas)
        - VISIONÁRIO (identifique tendências futuras)
        """
    
    def analyze_plan(self, plan_data):
        """Analisa um plano estratégico completo."""
        pass
    
    def validate_okrs(self, okrs):
        """Valida e sugere melhorias para OKRs."""
        pass
    
    def analyze_drivers(self, drivers):
        """Analisa direcionadores estratégicos."""
        pass
```

#### 1.2. Criar Tools para PEV
**Arquivo:** `agents/tools/pev_tools.py`

```python
"""
Ferramentas específicas para o Agente PEV.
"""
from langchain_core.tools import tool

@tool
def get_plan_data(plan_id: int):
    """Busca dados completos de um plano estratégico."""
    pass

@tool
def analyze_plan_maturity(plan_id: int):
    """Analisa a maturidade de um plano estratégico."""
    pass

@tool
def get_market_insights(industry: str, region: str):
    """Busca insights de mercado para um setor específico."""
    pass

@tool
def validate_okr_quality(okr_text: str):
    """Valida a qualidade de um OKR."""
    pass
```

#### 1.3. Integrar PEV Agent no Graph
**Arquivo:** `agents/graph.py` (atualizar)

```python
# Adicionar nó PEV ao grafo existente
from agents.pev.pev_agent import pev_node

workflow.add_node("PEV", pev_node)
workflow.add_edge("PEV", "supervisor")

# Adicionar ao roteador
workflow.add_conditional_edges(
    "supervisor",
    router,
    {
        # ... rotas existentes ...
        "PEV": "PEV",
    }
)
```

---

### **FASE 2: API Endpoints** (2-3 horas)

#### 2.1. Endpoint de Análise de Plano
**Arquivo:** `api/routes/pev.py` (adicionar)

```python
@pev_bp.route("/api/analyze-plan/<int:plan_id>", methods=["POST"])
@login_required
def analyze_plan_with_ai(plan_id):
    """
    Analisa um plano estratégico usando o Agente PEV.
    
    Returns:
        {
            "success": true,
            "analysis": {
                "overall_score": 7.5,
                "strengths": [...],
                "weaknesses": [...],
                "opportunities": [...],
                "recommendations": [...]
            }
        }
    """
    from agents.graph import board_intelligence
    
    # Buscar dados do plano
    db = get_db()
    plan = db.get_plan(plan_id)
    
    # Preparar contexto
    context = {
        "plan": plan,
        "drivers": db.get_driver_topics(plan_id),
        "okrs": db.get_okrs(plan_id),
        "projects": db.get_projects(plan_id)
    }
    
    # Invocar agente
    result = board_intelligence.invoke({
        "messages": [
            HumanMessage(content=f"Analise o plano estratégico: {json.dumps(context)}")
        ],
        "next_node": "PEV"
    })
    
    return jsonify({"success": True, "analysis": result})
```

#### 2.2. Endpoint de Chat
**Arquivo:** `api/routes/pev.py` (adicionar)

```python
@pev_bp.route("/api/chat", methods=["POST"])
@login_required
def pev_chat():
    """
    Chat interativo com o Agente PEV.
    
    Request:
        {
            "message": "Como melhorar meus OKRs?",
            "plan_id": 123,
            "thread_id": "abc-123" (opcional)
        }
    
    Returns:
        {
            "success": true,
            "response": "...",
            "thread_id": "abc-123"
        }
    """
    data = request.get_json()
    message = data.get("message")
    plan_id = data.get("plan_id")
    thread_id = data.get("thread_id") or str(uuid.uuid4())
    
    # Invocar agente com contexto
    from agents.graph import board_intelligence
    
    config = {"configurable": {"thread_id": thread_id}}
    result = board_intelligence.invoke({
        "messages": [HumanMessage(content=message)],
        "plan_id": plan_id
    }, config)
    
    response = result["messages"][-1].content
    
    return jsonify({
        "success": True,
        "response": response,
        "thread_id": thread_id
    })
```

#### 2.3. Endpoint de Insights Proativos
**Arquivo:** `api/routes/pev.py` (adicionar)

```python
@pev_bp.route("/api/insights/<int:plan_id>", methods=["GET"])
@login_required
def get_plan_insights(plan_id):
    """
    Gera insights proativos para um plano.
    
    Returns:
        {
            "success": true,
            "insights": [
                {
                    "type": "warning|opportunity|suggestion",
                    "title": "...",
                    "description": "...",
                    "action": "..."
                }
            ]
        }
    """
    # Implementar lógica de insights
    pass
```

---

### **FASE 3: Frontend Modernizado** (4-5 horas)

#### 3.1. Novo Template do Dashboard
**Arquivo:** `templates/modules/pev/dashboard_v2.html`

**Estrutura:**
```html
{% extends "base_layout.html" %}

{% block content %}
<div class="pev-dashboard">
  <!-- Hero Section -->
  <section class="dashboard-hero">
    <h1>Planejamento Estratégico</h1>
    <p>Gerencie e analise seus planos com inteligência artificial</p>
  </section>

  <!-- AI Insights Panel -->
  <section class="ai-insights-panel">
    <div class="insight-card critical">
      <span class="insight-icon">⚠️</span>
      <div class="insight-content">
        <h3>Atenção Necessária</h3>
        <p id="critical-insight">Carregando...</p>
      </div>
    </div>
    <div class="insight-card opportunity">
      <span class="insight-icon">💡</span>
      <div class="insight-content">
        <h3>Oportunidade Identificada</h3>
        <p id="opportunity-insight">Carregando...</p>
      </div>
    </div>
  </section>

  <!-- Plans Grid -->
  <section class="plans-grid">
    {% for plan in plans %}
    <div class="plan-card" data-plan-id="{{ plan.id }}">
      <div class="plan-header">
        <h3>{{ plan.name }}</h3>
        <span class="plan-status {{ plan.status }}">{{ plan.status }}</span>
      </div>
      <div class="plan-metrics">
        <div class="metric">
          <span class="metric-label">Progresso</span>
          <div class="progress-bar">
            <div class="progress-fill" style="width: {{ plan.progress }}%"></div>
          </div>
          <span class="metric-value">{{ plan.progress }}%</span>
        </div>
      </div>
      <div class="plan-actions">
        <button class="btn-primary" onclick="openPlan({{ plan.id }})">
          Abrir Plano
        </button>
        <button class="btn-secondary" onclick="analyzePlan({{ plan.id }})">
          🤖 Analisar com IA
        </button>
      </div>
    </div>
    {% endfor %}
  </section>

  <!-- AI Chat Widget -->
  <div id="ai-chat-widget" class="chat-widget collapsed">
    <div class="chat-header" onclick="toggleChat()">
      <span>🤖 Assistente PEV</span>
      <button class="chat-toggle">▼</button>
    </div>
    <div class="chat-body">
      <div id="chat-messages"></div>
      <div class="chat-input">
        <input type="text" id="chat-input" placeholder="Pergunte algo sobre seu planejamento...">
        <button onclick="sendMessage()">Enviar</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/pev_dashboard.js') }}"></script>
{% endblock %}
```

#### 3.2. Estilos CSS Premium
**Arquivo:** `static/css/pev_dashboard.css`

```css
/* Dashboard PEV - Estilo Premium */
.pev-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
}

.dashboard-hero {
  text-align: center;
  padding: 3rem 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  color: white;
  margin-bottom: 2rem;
}

.dashboard-hero h1 {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

/* AI Insights Panel */
.ai-insights-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.insight-card {
  background: var(--surface);
  border-radius: 12px;
  padding: 1.5rem;
  border-left: 4px solid;
  display: flex;
  gap: 1rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.insight-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.insight-card.critical {
  border-left-color: #ef4444;
}

.insight-card.opportunity {
  border-left-color: #10b981;
}

.insight-icon {
  font-size: 2rem;
}

/* Plans Grid */
.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.plan-card {
  background: var(--surface);
  border-radius: 12px;
  padding: 1.5rem;
  border: 1px solid var(--border);
  transition: all 0.3s;
}

.plan-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.plan-status {
  padding: 0.25rem 0.75rem;
  border-radius: 99px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.plan-status.active {
  background: #dbeafe;
  color: #1e40af;
}

/* Progress Bar */
.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--surface-secondary);
  border-radius: 4px;
  overflow: hidden;
  margin: 0.5rem 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s;
}

/* Chat Widget */
.chat-widget {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  width: 400px;
  max-height: 600px;
  background: var(--surface);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2);
  z-index: 1000;
  transition: all 0.3s;
}

.chat-widget.collapsed {
  max-height: 60px;
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  border-radius: 16px 16px 0 0;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-body {
  padding: 1rem;
  max-height: 500px;
  overflow-y: auto;
}

.chat-input {
  display: flex;
  gap: 0.5rem;
  padding: 1rem;
  border-top: 1px solid var(--border);
}

.chat-input input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
}

/* Animations */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.plan-card {
  animation: slideIn 0.3s ease-out;
}
```

#### 3.3. JavaScript Interativo
**Arquivo:** `static/js/pev_dashboard.js`

```javascript
// PEV Dashboard - Interatividade

let currentThreadId = null;

// Carregar insights ao abrir a página
document.addEventListener('DOMContentLoaded', function() {
  loadInsights();
  initializeChat();
});

// Carregar insights proativos
async function loadInsights() {
  const planId = getCurrentPlanId(); // Implementar
  if (!planId) return;
  
  try {
    const response = await fetch(`/pev/api/insights/${planId}`);
    const data = await response.json();
    
    if (data.success && data.insights) {
      displayInsights(data.insights);
    }
  } catch (error) {
    console.error('Erro ao carregar insights:', error);
  }
}

// Exibir insights
function displayInsights(insights) {
  insights.forEach(insight => {
    const element = document.getElementById(`${insight.type}-insight`);
    if (element) {
      element.textContent = insight.description;
    }
  });
}

// Analisar plano com IA
async function analyzePlan(planId) {
  const card = document.querySelector(`[data-plan-id="${planId}"]`);
  card.classList.add('analyzing');
  
  try {
    const response = await fetch(`/pev/api/analyze-plan/${planId}`, {
      method: 'POST'
    });
    const data = await response.json();
    
    if (data.success) {
      showAnalysisModal(data.analysis);
    }
  } catch (error) {
    console.error('Erro ao analisar plano:', error);
    alert('Erro ao analisar plano. Tente novamente.');
  } finally {
    card.classList.remove('analyzing');
  }
}

// Chat com assistente
async function sendMessage() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  
  // Adicionar mensagem do usuário
  addChatMessage('user', message);
  input.value = '';
  
  // Enviar para API
  try {
    const response = await fetch('/pev/api/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: message,
        plan_id: getCurrentPlanId(),
        thread_id: currentThreadId
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      currentThreadId = data.thread_id;
      addChatMessage('assistant', data.response);
    }
  } catch (error) {
    console.error('Erro no chat:', error);
    addChatMessage('assistant', 'Desculpe, ocorreu um erro. Tente novamente.');
  }
}

// Adicionar mensagem ao chat
function addChatMessage(role, content) {
  const messagesDiv = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message ${role}`;
  messageDiv.textContent = content;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Toggle chat widget
function toggleChat() {
  const widget = document.getElementById('ai-chat-widget');
  widget.classList.toggle('collapsed');
}

// Inicializar chat
function initializeChat() {
  const input = document.getElementById('chat-input');
  input.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });
}

// Helper: obter plan_id atual
function getCurrentPlanId() {
  // Implementar lógica para obter plan_id do contexto
  return null;
}

// Exibir modal de análise
function showAnalysisModal(analysis) {
  // Implementar modal com resultados da análise
  console.log('Análise:', analysis);
}
```

---

### **FASE 4: Testes e Refinamento** (2-3 horas)

#### 4.1. Testes de Integração
- Testar análise de planos
- Testar chat interativo
- Testar geração de insights
- Validar performance

#### 4.2. Ajustes de UX
- Refinar animações
- Melhorar feedback visual
- Otimizar responsividade
- Ajustar cores e tipografia

#### 4.3. Documentação
- Documentar novos endpoints
- Criar guia de uso
- Atualizar README

---

## 📊 Métricas de Sucesso

1. **Performance**
   - Tempo de resposta do chat < 2s
   - Análise de plano < 5s
   - Dashboard carrega em < 1s

2. **Qualidade**
   - Análises relevantes e acionáveis
   - Sugestões específicas e práticas
   - Interface intuitiva e responsiva

3. **Adoção**
   - Usuários utilizando chat
   - Análises de planos realizadas
   - Feedback positivo

---

## 🚀 Próximos Passos

1. **Validar com stakeholders**
2. **Implementar FASE 1** (Agentes)
3. **Implementar FASE 2** (APIs)
4. **Implementar FASE 3** (Frontend)
5. **Testar e refinar** (FASE 4)
6. **Deploy em produção**

---

## 📚 Referências

- `docs/SISTEMA_AGENTES_IA.md` - Arquitetura de agentes
- `docs/governance/AGENT_ARCHITECTURE.md` - Governança
- `agents/graph.py` - Orquestração atual
- `api/routes/pev.py` - Rotas PEV existentes
