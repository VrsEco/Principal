# 🗺️ ROADMAP TÉCNICO DETALHADO - GRV

## 📋 ÍNDICE
1. [Visão Geral](#visão-geral)
2. [Fase 1: Gestão de Processos](#fase-1-gestão-de-processos)
3. [Fase 2: Identidade Organizacional](#fase-2-identidade-organizacional)
4. [Fase 3: Gestão de Projetos](#fase-3-gestão-de-projetos)
5. [Fase 4: Gestão da Rotina](#fase-4-gestão-da-rotina)
6. [Fase 5: Polimento e Deploy](#fase-5-polimento-e-deploy)

---

## 🎯 VISÃO GERAL

**Objetivo**: Completar o módulo GRV (Gerenciamento da Rotina Versus) em 12-14 semanas

**Status Atual**: 40% completo
- ✅ Dashboard
- ✅ MVV (Missão/Visão/Valores)
- ✅ Cadastro de Funções
- ✅ Macroprocessos (100% funcional)
- 🔄 8 funcionalidades em estrutura básica

**Metas**:
- 100% de funcionalidades implementadas
- Testes de integração
- Documentação completa
- Pronto para produção

---

## 📊 FASE 1: GESTÃO DE PROCESSOS
**Duração**: 2-3 semanas  
**Prioridade**: CRÍTICA 🔴

### 🎯 Objetivo
Completar a estrutura de Gestão de Processos com interfaces visuais e funcionalidades completas.

---

### ✅ 1.1 Interface de Processos (Semana 1-2)

#### Frontend (Template)
**Arquivo**: `templates/grv_process_list.html`

```html
<!-- Estrutura similar a grv_process_macro.html -->
<div class="project-content plan-content" data-company-id="{{ company.id }}">
  <!-- Header -->
  <div class="surface-card">
    <div class="card-header">
      <div>
        <h3>Processos</h3>
        <p>Gerencie os processos operacionais detalhados</p>
      </div>
      <button id="btnNewProcess">➕ Novo Processo</button>
    </div>
  </div>

  <!-- Filtros -->
  <div class="filters-bar">
    <select id="filterArea">
      <option value="">Todas as Áreas</option>
      <!-- Populated dynamically -->
    </select>
    <select id="filterMacro">
      <option value="">Todos os Macroprocessos</option>
      <!-- Populated dynamically -->
    </select>
    <input type="text" id="searchProcess" placeholder="Buscar processo...">
  </div>

  <!-- Grid de Processos -->
  <div id="processesContainer">
    <!-- Processos agrupados por macroprocesso -->
  </div>
</div>
```

#### JavaScript
**Arquivo**: `static/js/grv-processes.js`

```javascript
(function() {
  'use strict';
  
  const companyId = getCompanyId();
  
  // Estado
  let areas = [];
  let macros = [];
  let processes = [];
  
  // Carregar dados
  async function loadData() {
    await Promise.all([
      loadAreas(),
      loadMacros(),
      loadProcesses()
    ]);
    renderProcesses();
  }
  
  // CRUD Operations
  async function createProcess(data) {
    // POST /api/companies/{companyId}/processes
  }
  
  async function updateProcess(processId, data) {
    // PUT /api/companies/{companyId}/processes/{processId}
  }
  
  async function deleteProcess(processId) {
    // DELETE /api/companies/{companyId}/processes/{processId}
  }
  
  // Renderização
  function renderProcesses() {
    // Agrupar por macroprocesso
    // Mostrar hierarquia visual
  }
  
  // Init
  loadData();
})();
```

#### Funcionalidades
- [ ] Modal de criação/edição similar ao de macroprocessos
- [ ] Seleção de área e macroprocesso
- [ ] Sistema de codificação automática: `{CLIENTE}.P.{ÁREA}.{MACRO}.{SEQ}`
- [ ] Campo "Dono do Processo"
- [ ] Agrupamento visual por macroprocesso
- [ ] Busca e filtros
- [ ] Validações client-side e server-side

---

### 🗺️ 1.2 Mapa de Processos Visual (Semana 2-3)

#### Biblioteca Recomendada
**D3.js** ou **vis.js** para visualização hierárquica

#### Estrutura de Dados
```javascript
{
  "areas": [
    {
      "id": 1,
      "name": "Financeiro",
      "code": "FN",
      "color": "#3b82f6",
      "macros": [
        {
          "id": 1,
          "name": "Gestão de Contas",
          "code": "VSA.C.FN.1",
          "processes": [
            {
              "id": 1,
              "name": "Contas a Pagar",
              "code": "VSA.P.FN.1.1"
            }
          ]
        }
      ]
    }
  ]
}
```

#### Frontend
**Arquivo**: `templates/grv_process_map.html`

```html
<div class="process-map-container">
  <!-- Controls -->
  <div class="map-controls">
    <button id="zoomIn">🔍 +</button>
    <button id="zoomOut">🔍 -</button>
    <button id="resetView">⟲ Reset</button>
    <button id="expandAll">📂 Expandir Tudo</button>
    <button id="collapseAll">📁 Colapsar Tudo</button>
    <button id="exportPDF">📄 Exportar PDF</button>
  </div>

  <!-- Visualization Canvas -->
  <div id="processMapViz"></div>

  <!-- Legend -->
  <div class="map-legend">
    <div class="legend-item">
      <span class="legend-color area"></span> Área de Gestão
    </div>
    <div class="legend-item">
      <span class="legend-color macro"></span> Macroprocesso
    </div>
    <div class="legend-item">
      <span class="legend-color process"></span> Processo
    </div>
  </div>
</div>
```

#### JavaScript
**Arquivo**: Atualizar `static/js/grv-process-map.js`

```javascript
import * as d3 from 'd3'; // ou usar CDN

class ProcessMapVisualizer {
  constructor(containerId, data) {
    this.container = d3.select(`#${containerId}`);
    this.data = data;
    this.setup();
  }
  
  setup() {
    // Configurar SVG
    this.svg = this.container.append('svg')
      .attr('width', '100%')
      .attr('height', '100%');
    
    // Zoom behavior
    this.zoom = d3.zoom()
      .on('zoom', (event) => {
        this.g.attr('transform', event.transform);
      });
    
    this.svg.call(this.zoom);
    this.g = this.svg.append('g');
  }
  
  render() {
    // Criar hierarquia
    const root = d3.hierarchy(this.transformData());
    
    // Tree layout
    const treeLayout = d3.tree()
      .size([height, width]);
    
    treeLayout(root);
    
    // Desenhar links
    this.renderLinks(root.links());
    
    // Desenhar nodes
    this.renderNodes(root.descendants());
  }
  
  renderNodes(nodes) {
    const nodeGroups = this.g.selectAll('.node')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', d => `node node-${d.data.type}`)
      .attr('transform', d => `translate(${d.y}, ${d.x})`);
    
    // Adicionar círculos/retângulos
    nodeGroups.append('rect')
      .attr('width', d => d.data.type === 'area' ? 200 : 150)
      .attr('height', 60)
      .attr('fill', d => d.data.color || '#39f2ae');
    
    // Adicionar texto
    nodeGroups.append('text')
      .text(d => d.data.name);
    
    // Click handlers
    nodeGroups.on('click', (event, d) => {
      this.onNodeClick(d);
    });
  }
  
  renderLinks(links) {
    // Desenhar linhas conectando nodes
    this.g.selectAll('.link')
      .data(links)
      .enter()
      .append('path')
      .attr('class', 'link')
      .attr('d', d3.linkHorizontal()
        .x(d => d.y)
        .y(d => d.x));
  }
  
  exportPDF() {
    // Usar html2canvas ou similar
    // Converter SVG para PDF
  }
}

// Inicializar
const visualizer = new ProcessMapVisualizer('processMapViz', processMapData);
visualizer.render();
```

#### CSS
**Arquivo**: `static/css/process-map.css`

```css
.process-map-container {
  position: relative;
  width: 100%;
  height: calc(100vh - 200px);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

#processMapViz {
  width: 100%;
  height: 100%;
}

.node-area rect {
  fill: var(--color-accent);
  stroke: var(--color-border);
  stroke-width: 2px;
}

.node-macro rect {
  fill: #3b82f6;
  stroke: var(--color-border);
}

.node-process rect {
  fill: #8b5cf6;
  stroke: var(--color-border);
}

.link {
  fill: none;
  stroke: var(--color-border);
  stroke-width: 2px;
}

.map-controls {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  gap: 8px;
  z-index: 10;
}

.map-legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: var(--color-surface-alt);
  padding: 16px;
  border-radius: var(--radius-md);
}
```

#### Funcionalidades
- [ ] Visualização hierárquica (Áreas → Macros → Processos)
- [ ] Zoom e pan
- [ ] Expandir/colapsar ramos
- [ ] Click em node para ver detalhes
- [ ] Busca visual (highlight)
- [ ] Exportação para PDF
- [ ] Exportação para imagem (PNG/SVG)
- [ ] Drag & drop para reorganização (opcional)

---

## 🏢 FASE 2: IDENTIDADE ORGANIZACIONAL
**Duração**: 1-2 semanas  
**Prioridade**: ALTA 🟠

### 📊 2.1 Organograma Interativo (Semana 3-4)

#### Biblioteca Recomendada
**OrgChart.js** ou **D3.js** com layout hierárquico

#### API de Dados
**Endpoint Existente**: `GET /api/companies/{company_id}/roles/tree`

**Resposta**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "CEO",
      "code": "CEO",
      "level": 1,
      "subordinates": [
        {
          "id": 2,
          "name": "CFO",
          "code": "CFO",
          "level": 2,
          "subordinates": [...]
        }
      ]
    }
  ]
}
```

#### Frontend
**Arquivo**: Atualizar `templates/grv_identity_org_chart.html`

```html
<div class="org-chart-container">
  <!-- Toolbar -->
  <div class="chart-toolbar">
    <button id="fitChart">⤢ Ajustar</button>
    <button id="expandAll">📂 Expandir</button>
    <button id="collapseAll">📁 Colapsar</button>
    <button id="exportChart">📥 Exportar</button>
    <select id="chartLayout">
      <option value="vertical">Vertical</option>
      <option value="horizontal">Horizontal</option>
    </select>
  </div>

  <!-- Chart Canvas -->
  <div id="orgChart"></div>

  <!-- Side Panel (detalhes do cargo) -->
  <div id="roleDetails" class="role-panel">
    <h3 id="roleName"></h3>
    <p id="roleDescription"></p>
    <button id="editRole">✏️ Editar</button>
  </div>
</div>
```

#### JavaScript
**Arquivo**: `static/js/grv-org-chart.js`

```javascript
import OrgChart from 'orgchart.js';

class OrgChartManager {
  constructor(containerId, companyId) {
    this.container = document.getElementById(containerId);
    this.companyId = companyId;
    this.chart = null;
  }
  
  async init() {
    const rolesTree = await this.loadRolesTree();
    this.renderChart(rolesTree);
  }
  
  async loadRolesTree() {
    const response = await fetch(`/api/companies/${this.companyId}/roles/tree`);
    const json = await response.json();
    return json.data;
  }
  
  renderChart(data) {
    this.chart = new OrgChart(this.container, {
      data: this.transformData(data),
      nodeWidth: 200,
      nodeHeight: 100,
      verticalSpacing: 40,
      horizontalSpacing: 20,
      nodeContent: 'name',
      createNode: (node, data) => {
        node.innerHTML = `
          <div class="org-node">
            <div class="node-title">${data.name}</div>
            <div class="node-code">${data.code}</div>
            <div class="node-level">Nível ${data.level}</div>
          </div>
        `;
      }
    });
    
    this.attachEvents();
  }
  
  transformData(roles) {
    // Converter formato da API para formato do OrgChart
    return roles.map(role => ({
      id: role.id,
      name: role.name,
      code: role.code,
      level: role.level,
      children: this.transformData(role.subordinates || [])
    }));
  }
  
  attachEvents() {
    // Click em node
    this.container.addEventListener('click', (e) => {
      if (e.target.closest('.org-node')) {
        const roleId = e.target.closest('[data-role-id]').dataset.roleId;
        this.showRoleDetails(roleId);
      }
    });
  }
  
  async showRoleDetails(roleId) {
    // Carregar e mostrar detalhes do cargo
  }
  
  exportChart(format = 'pdf') {
    // Exportar organograma
  }
}

// Init
const orgChart = new OrgChartManager('orgChart', companyId);
orgChart.init();
```

#### CSS
**Arquivo**: `static/css/org-chart.css`

```css
.org-chart-container {
  display: flex;
  gap: 24px;
  height: calc(100vh - 200px);
}

#orgChart {
  flex: 1;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: auto;
}

.org-node {
  background: linear-gradient(135deg, var(--color-surface-alt), var(--color-surface));
  border: 2px solid var(--color-accent);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.org-node:hover {
  transform: scale(1.05);
  box-shadow: var(--shadow-md);
}

.node-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.node-code {
  font-size: 11px;
  color: var(--color-accent);
  font-family: monospace;
  margin-bottom: 4px;
}

.node-level {
  font-size: 10px;
  color: var(--color-muted);
}

.role-panel {
  width: 300px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: none;
}

.role-panel.active {
  display: block;
}
```

#### Funcionalidades
- [ ] Visualização hierárquica de cargos
- [ ] Layout vertical e horizontal
- [ ] Zoom e navegação
- [ ] Click em cargo mostra detalhes
- [ ] Busca de cargos
- [ ] Exportação (PDF, PNG)
- [ ] Expandir/colapsar ramos
- [ ] Integração com CRUD de funções

---

## 📁 FASE 3: GESTÃO DE PROJETOS
**Duração**: 2-3 semanas  
**Prioridade**: ALTA 🟠

### 📋 3.1 Board de Projetos (Semana 5-6)

#### Estrutura de Dados

**Tabelas Necessárias** (verificar se já existem):
```sql
CREATE TABLE IF NOT EXISTS grv_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    code TEXT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planned', -- planned, in_progress, on_hold, completed, cancelled
    priority TEXT, -- low, medium, high, critical
    owner TEXT,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(15,2),
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id)
);

CREATE TABLE IF NOT EXISTS grv_project_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo', -- todo, in_progress, review, done
    assigned_to TEXT,
    due_date DATE,
    priority TEXT,
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES grv_projects (id) ON DELETE CASCADE
);
```

#### APIs

**Adicionar em `database/sqlite_db.py`**:
```python
def list_grv_projects(self, company_id: int) -> List[Dict[str, Any]]:
    """List all GRV projects for a company"""
    conn = self._get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM grv_projects WHERE company_id = ? ORDER BY created_at DESC', (company_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def create_grv_project(self, company_id: int, data: Dict[str, Any]) -> Optional[int]:
    """Create new GRV project"""
    # Implementation

def update_grv_project(self, project_id: int, data: Dict[str, Any]) -> bool:
    """Update GRV project"""
    # Implementation

def delete_grv_project(self, project_id: int) -> bool:
    """Delete GRV project"""
    # Implementation

def list_project_tasks(self, project_id: int) -> List[Dict[str, Any]]:
    """List tasks for a project"""
    # Implementation
```

**Adicionar em `app_pev.py`**:
```python
# GRV Projects APIs
@app.route('/api/companies/<int:company_id>/grv-projects', methods=['GET'])
def api_list_grv_projects(company_id: int):
    try:
        projects = db.list_grv_projects(company_id)
        return jsonify({'success': True, 'data': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/companies/<int:company_id>/grv-projects', methods=['POST'])
def api_create_grv_project(company_id: int):
    payload = request.get_json(silent=True) or {}
    new_id = db.create_grv_project(company_id, payload)
    if new_id:
        return jsonify({'success': True, 'id': new_id}), 201
    return jsonify({'success': False, 'error': 'create_failed'}), 400

# ... PUT, DELETE similares
```

#### Frontend - Board Kanban
**Arquivo**: Atualizar `templates/grv_projects_board.html`

```html
<div class="projects-board-container" data-company-id="{{ company.id }}">
  <!-- Header -->
  <div class="board-header">
    <h2>Projetos</h2>
    <div class="board-actions">
      <button id="btnNewProject" class="button button-primary">➕ Novo Projeto</button>
      <button id="btnFilterProjects" class="button button-ghost">🔍 Filtrar</button>
    </div>
  </div>

  <!-- Kanban Board -->
  <div class="kanban-board">
    <div class="kanban-column" data-status="planned">
      <div class="column-header">
        <h3>📋 Planejado</h3>
        <span class="column-count">0</span>
      </div>
      <div class="column-content" data-droppable="true">
        <!-- Project cards -->
      </div>
    </div>

    <div class="kanban-column" data-status="in_progress">
      <div class="column-header">
        <h3>🚀 Em Andamento</h3>
        <span class="column-count">0</span>
      </div>
      <div class="column-content" data-droppable="true">
        <!-- Project cards -->
      </div>
    </div>

    <div class="kanban-column" data-status="on_hold">
      <div class="column-header">
        <h3>⏸️ Em Pausa</h3>
        <span class="column-count">0</span>
      </div>
      <div class="column-content" data-droppable="true">
        <!-- Project cards -->
      </div>
    </div>

    <div class="kanban-column" data-status="completed">
      <div class="column-header">
        <h3>✅ Concluído</h3>
        <span class="column-count">0</span>
      </div>
      <div class="column-content" data-droppable="true">
        <!-- Project cards -->
      </div>
    </div>
  </div>
</div>

<!-- Modal de Projeto -->
<div id="projectModal" class="modal" style="display:none;">
  <!-- Similar structure to macro modal -->
</div>
```

#### JavaScript - Drag & Drop
**Arquivo**: `static/js/grv-projects-board.js`

```javascript
(function() {
  'use strict';
  
  const companyId = getCompanyId();
  let projects = [];
  let draggedCard = null;
  
  // Load projects
  async function loadProjects() {
    const response = await fetch(`/api/companies/${companyId}/grv-projects`);
    const json = await response.json();
    if (json && json.success) {
      projects = json.data;
      renderBoard();
    }
  }
  
  // Render board
  function renderBoard() {
    const columns = document.querySelectorAll('.column-content');
    
    columns.forEach(column => {
      column.innerHTML = '';
      const status = column.closest('[data-status]').dataset.status;
      const statusProjects = projects.filter(p => p.status === status);
      
      statusProjects.forEach(project => {
        const card = createProjectCard(project);
        column.appendChild(card);
      });
      
      // Update count
      const countEl = column.closest('.kanban-column').querySelector('.column-count');
      countEl.textContent = statusProjects.length;
    });
  }
  
  // Create project card
  function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'project-card';
    card.draggable = true;
    card.dataset.projectId = project.id;
    
    card.innerHTML = `
      <div class="card-header">
        <span class="project-code">${project.code || ''}</span>
        <span class="project-priority priority-${project.priority}">${project.priority}</span>
      </div>
      <h4 class="project-title">${project.name}</h4>
      <p class="project-description">${project.description || ''}</p>
      <div class="project-meta">
        <span class="project-owner">👤 ${project.owner || 'Sem responsável'}</span>
        <span class="project-progress">${project.progress || 0}%</span>
      </div>
      <div class="project-dates">
        <span>${formatDate(project.start_date)} - ${formatDate(project.end_date)}</span>
      </div>
    `;
    
    // Drag events
    card.addEventListener('dragstart', handleDragStart);
    card.addEventListener('dragend', handleDragEnd);
    
    // Click to open details
    card.addEventListener('click', (e) => {
      if (!e.target.closest('button')) {
        openProjectModal(project.id);
      }
    });
    
    return card;
  }
  
  // Drag & Drop handlers
  function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
  }
  
  function handleDragEnd(e) {
    this.classList.remove('dragging');
  }
  
  // Setup drop zones
  function setupDropZones() {
    const dropZones = document.querySelectorAll('[data-droppable]');
    
    dropZones.forEach(zone => {
      zone.addEventListener('dragover', handleDragOver);
      zone.addEventListener('drop', handleDrop);
      zone.addEventListener('dragleave', handleDragLeave);
    });
  }
  
  function handleDragOver(e) {
    if (e.preventDefault) {
      e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    this.classList.add('drag-over');
    return false;
  }
  
  function handleDragLeave(e) {
    this.classList.remove('drag-over');
  }
  
  async function handleDrop(e) {
    if (e.stopPropagation) {
      e.stopPropagation();
    }
    
    this.classList.remove('drag-over');
    
    const projectId = parseInt(draggedCard.dataset.projectId);
    const newStatus = this.closest('[data-status]').dataset.status;
    
    // Update project status
    await updateProjectStatus(projectId, newStatus);
    
    // Reload board
    await loadProjects();
    
    return false;
  }
  
  async function updateProjectStatus(projectId, status) {
    const response = await fetch(`/api/companies/${companyId}/grv-projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    
    const json = await response.json();
    if (json && json.success) {
      showMessage('Status do projeto atualizado', 'success');
    } else {
      showMessage('Erro ao atualizar projeto', 'error');
    }
  }
  
  // Init
  loadProjects();
  setupDropZones();
})();
```

#### CSS
**Arquivo**: `static/css/projects-board.css`

```css
.projects-board-container {
  padding: 24px;
}

.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-top: 24px;
}

.kanban-column {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: 16px;
  min-height: 600px;
}

.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--color-border);
}

.column-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.column-count {
  background: var(--color-accent);
  color: var(--color-bg);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.column-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.column-content.drag-over {
  background: rgba(58, 241, 174, 0.1);
  border-radius: var(--radius-md);
}

.project-card {
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 16px;
  cursor: move;
  transition: all 0.2s;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-accent);
}

.project-card.dragging {
  opacity: 0.5;
}

.project-code {
  font-size: 10px;
  font-family: monospace;
  color: var(--color-accent);
  background: rgba(58, 241, 174, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.project-priority {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.priority-low { background: #3b82f6; color: white; }
.priority-medium { background: #f59e0b; color: white; }
.priority-high { background: #ef4444; color: white; }
.priority-critical { background: #dc2626; color: white; }

.project-title {
  margin: 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.project-description {
  font-size: 12px;
  color: var(--color-muted);
  margin: 8px 0;
  line-height: 1.4;
}

.project-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  margin: 8px 0;
}

.project-progress {
  color: var(--color-accent);
  font-weight: 600;
}

.project-dates {
  font-size: 10px;
  color: var(--color-muted);
  margin-top: 8px;
}
```

#### Funcionalidades
- [ ] Board Kanban com 4 colunas (Planejado, Em Andamento, Em Pausa, Concluído)
- [ ] Drag & drop para alterar status
- [ ] Cards com informações resumidas
- [ ] Modal de criação/edição de projetos
- [ ] Progresso visual
- [ ] Prioridades com cores
- [ ] Filtros (por owner, prioridade, datas)
- [ ] Busca de projetos

---

### 📊 3.2 Portfólio de Projetos (Semana 6-7)

#### Frontend
**Arquivo**: Atualizar `templates/grv_projects_portfolio.html`

```html
<div class="portfolio-container">
  <!-- Summary Cards -->
  <div class="portfolio-summary">
    <div class="summary-card">
      <h4>Total de Projetos</h4>
      <div class="summary-value" id="totalProjects">0</div>
    </div>
    <div class="summary-card">
      <h4>Em Andamento</h4>
      <div class="summary-value" id="activeProjects">0</div>
    </div>
    <div class="summary-card">
      <h4>Concluídos</h4>
      <div class="summary-value" id="completedProjects">0</div>
    </div>
    <div class="summary-card">
      <h4>Orçamento Total</h4>
      <div class="summary-value" id="totalBudget">R$ 0</div>
    </div>
  </div>

  <!-- Charts -->
  <div class="portfolio-charts">
    <div class="chart-card">
      <h3>Projetos por Status</h3>
      <canvas id="projectsByStatus"></canvas>
    </div>
    <div class="chart-card">
      <h3>Projetos por Prioridade</h3>
      <canvas id="projectsByPriority"></canvas>
    </div>
    <div class="chart-card">
      <h3>Timeline</h3>
      <div id="projectsTimeline"></div>
    </div>
  </div>

  <!-- Projects Table -->
  <div class="projects-table-container">
    <h3>Todos os Projetos</h3>
    <table id="projectsTable" class="data-table">
      <thead>
        <tr>
          <th>Código</th>
          <th>Nome</th>
          <th>Status</th>
          <th>Prioridade</th>
          <th>Responsável</th>
          <th>Progresso</th>
          <th>Orçamento</th>
          <th>Prazo</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
        <!-- Populated dynamically -->
      </tbody>
    </table>
  </div>
</div>
```

#### JavaScript - Charts
**Arquivo**: `static/js/grv-projects-portfolio.js`

```javascript
import Chart from 'chart.js/auto';

(function() {
  'use strict';
  
  const companyId = getCompanyId();
  let projects = [];
  
  async function loadPortfolio() {
    const response = await fetch(`/api/companies/${companyId}/grv-projects`);
    const json = await response.json();
    if (json && json.success) {
      projects = json.data;
      renderPortfolio();
    }
  }
  
  function renderPortfolio() {
    updateSummaryCards();
    renderCharts();
    renderProjectsTable();
  }
  
  function updateSummaryCards() {
    document.getElementById('totalProjects').textContent = projects.length;
    document.getElementById('activeProjects').textContent = 
      projects.filter(p => p.status === 'in_progress').length;
    document.getElementById('completedProjects').textContent = 
      projects.filter(p => p.status === 'completed').length;
    
    const totalBudget = projects.reduce((sum, p) => sum + (parseFloat(p.budget) || 0), 0);
    document.getElementById('totalBudget').textContent = formatCurrency(totalBudget);
  }
  
  function renderCharts() {
    // Chart: Projects by Status
    const statusCounts = getCountsByField('status');
    new Chart(document.getElementById('projectsByStatus'), {
      type: 'doughnut',
      data: {
        labels: Object.keys(statusCounts),
        datasets: [{
          data: Object.values(statusCounts),
          backgroundColor: ['#3b82f6', '#39f2ae', '#f59e0b', '#10b981', '#ef4444']
        }]
      }
    });
    
    // Chart: Projects by Priority
    const priorityCounts = getCountsByField('priority');
    new Chart(document.getElementById('projectsByPriority'), {
      type: 'bar',
      data: {
        labels: Object.keys(priorityCounts),
        datasets: [{
          label: 'Projetos',
          data: Object.values(priorityCounts),
          backgroundColor: '#39f2ae'
        }]
      }
    });
  }
  
  function getCountsByField(field) {
    return projects.reduce((acc, project) => {
      const value = project[field] || 'Não definido';
      acc[value] = (acc[value] || 0) + 1;
      return acc;
    }, {});
  }
  
  function renderProjectsTable() {
    const tbody = document.querySelector('#projectsTable tbody');
    tbody.innerHTML = '';
    
    projects.forEach(project => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${project.code || '-'}</td>
        <td><strong>${project.name}</strong></td>
        <td><span class="status-badge status-${project.status}">${translateStatus(project.status)}</span></td>
        <td><span class="priority-badge priority-${project.priority}">${project.priority}</span></td>
        <td>${project.owner || '-'}</td>
        <td>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${project.progress || 0}%"></div>
          </div>
          <span class="progress-text">${project.progress || 0}%</span>
        </td>
        <td>${formatCurrency(project.budget)}</td>
        <td>${formatDate(project.end_date)}</td>
        <td>
          <button class="btn-icon" onclick="editProject(${project.id})">✏️</button>
          <button class="btn-icon" onclick="deleteProject(${project.id})">🗑️</button>
        </td>
      `;
      tbody.appendChild(row);
    });
  }
  
  // Init
  loadPortfolio();
})();
```

#### Funcionalidades
- [ ] Cards de resumo (total, ativos, concluídos, orçamento)
- [ ] Gráficos (status, prioridade, timeline)
- [ ] Tabela completa de projetos
- [ ] Filtros e ordenação
- [ ] Exportação para Excel/CSV
- [ ] Relatório PDF do portfólio

---

## ⚙️ FASE 4: GESTÃO DA ROTINA
**Duração**: 3-4 semanas  
**Prioridade**: MÉDIA 🟡

*(Detalhamento das 5 telas de Gestão da Rotina)*

### 📅 4.1 Atividades e Calendário (Semana 8-9)
- [ ] Calendário mensal/semanal/diário
- [ ] CRUD de atividades
- [ ] Recorrência
- [ ] Notificações

### 👥 4.2 Distribuição do Trabalho (Semana 9-10)
- [ ] Mapa de carga por pessoa
- [ ] Visualização de capacidade
- [ ] Balanceamento

### 📊 4.3 Capacidade Operacional (Semana 10)
- [ ] Métricas de capacidade
- [ ] Análise de gargalos
- [ ] Projeções

### 🚨 4.4 Ocorrências (Semana 11)
- [ ] Registro de ocorrências
- [ ] Análise de causas
- [ ] Planos de ação

### 📈 4.5 Eficiência (Semana 11)
- [ ] KPIs de eficiência
- [ ] Dashboards
- [ ] Relatórios

---

## 🎨 FASE 5: POLIMENTO E DEPLOY
**Duração**: 1-2 semanas  
**Prioridade**: CRÍTICA 🔴

### 5.1 Testes (Semana 12)
- [ ] Testes unitários (pytest)
- [ ] Testes de integração
- [ ] Testes de UI

### 5.2 Documentação (Semana 12-13)
- [ ] Documentação de APIs
- [ ] Guia do usuário
- [ ] Guia do desenvolvedor

### 5.3 Performance (Semana 13)
- [ ] Otimização de queries
- [ ] Cache (Redis)
- [ ] Paginação

### 5.4 Deploy (Semana 13-14)
- [ ] Configuração de produção
- [ ] Migração de dados
- [ ] Monitoramento
- [ ] Treinamento de usuários

---

## 📊 MÉTRICAS DE PROGRESSO

### Checklist Geral
- ✅ Dashboard GRV (100%)
- ✅ MVV (100%)
- ✅ Cadastro de Funções (100%)
- ✅ Macroprocessos (100%)
- 🔄 Organograma (20%)
- 🔄 Mapa de Processos (30%)
- 🔄 Processos (60%)
- 🔄 Portfólio de Projetos (20%)
- 🔄 Projetos Board (20%)
- 🔄 Distribuição do Trabalho (10%)
- 🔄 Capacidade Operacional (10%)
- 🔄 Atividades/Calendário (10%)
- 🔄 Ocorrências (10%)
- 🔄 Eficiência (10%)

### Progresso Geral: 40% → Meta: 100%

---

## 🚀 INÍCIO RÁPIDO

### Próximo Sprint (2 semanas)
**Foco**: Completar Gestão de Processos

**Tarefas**:
1. ✅ Implementar interface de Processos
2. ✅ Criar modal de criação/edição
3. ✅ Implementar Mapa de Processos visual
4. ✅ Adicionar drag & drop no mapa
5. ✅ Exportação de PDF do mapa

**Entregáveis**:
- Interface de Processos funcional
- Mapa de Processos interativo
- Testes básicos

---

**Última Atualização**: 7 de outubro de 2025  
**Versão**: 1.0








