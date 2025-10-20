# 🔍 DIAGNÓSTICO DO SISTEMA DE RELATÓRIOS - STATUS ATUAL

## ✅ O QUE ESTÁ IMPLEMENTADO E FUNCIONANDO

### **1. Sistema de Modelos de Página** ✅
- **Local:** `http://127.0.0.1:5002/settings/reports`
- **Funcionalidades:**
  - ✅ Configuração de margens, cabeçalho e rodapé
  - ✅ Preview visual da página
  - ✅ Salvamento de modelos no banco (`report_models`)
  - ✅ Listagem de modelos salvos
  - ✅ Aplicação de modelos aos campos
  - ✅ Edição de modelos (com verificação de conflitos)
  - ✅ Botões de teste (Visualizar Impressão, Gerar PDF)

### **2. Módulos Backend** ✅
- **Arquivos:**
  - ✅ `modules/report_models.py` - Gerenciamento de modelos
  - ✅ `modules/report_generator.py` - Geração de relatórios
  - ✅ `modules/placeholder_generator.py` - Dados de teste

### **3. APIs REST** ✅
```python
# Em app_pev.py (linhas 369-468)
✅ GET  /settings/reports                    # Página de configuração
✅ POST /api/reports/preview                 # Preview HTML
✅ POST /api/reports/generate                # Gerar PDF
✅ POST /api/reports/models                  # Salvar modelo
✅ GET  /api/reports/models/<id>             # Buscar modelo
✅ PUT  /api/reports/models/<id>             # Atualizar modelo
✅ GET  /api/reports/models/<id>/conflicts   # Verificar conflitos
✅ GET  /api/reports/download/<filename>     # Download de arquivo
```

### **4. Banco de Dados** ✅
```sql
✅ report_models       - Modelos salvos
✅ report_instances    - Relatórios gerados
```

---

## 🔧 O QUE ESTÁ PARCIALMENTE IMPLEMENTADO

### **1. Geração de Relatórios de Processos** ⚠️

**Onde está:** `templates/grv_process_detail.html`

**O que tem:**
```html
<!-- Modal de relatório (linhas 1674-1757) -->
<div class="report-modal" data-report-modal>
  <h3>📄 Gerar Relatório do Processo</h3>
  
  <!-- Seletor de seções -->
  <input type="checkbox" value="flow" checked /> Fluxo
  <input type="checkbox" value="pop" checked /> POP
  <input type="checkbox" value="indicators" /> Indicadores
  <input type="checkbox" value="routines" /> Rotinas
  
  <button data-report-generate-btn>Gerar Relatório</button>
</div>
```

**O que FALTA:**
```html
<!-- ❌ FALTA: Seletor de modelo -->
<select id="report_model_selector">
  <option value="">Usar configuração padrão</option>
  {% for model in available_models %}
    <option value="{{ model.id }}">{{ model.name }}</option>
  {% endfor %}
</select>
```

### **2. JavaScript de Geração** ⚠️

**Onde está:** `templates/grv_process_detail.html` (linhas 3114-3167)

**O que faz:**
```javascript
// Captura seções selecionadas
const sections = Array.from(checkboxes).map(cb => cb.value);

// Monta URL
const url = `/api/companies/${companyId}/processes/${processId}/report?sections=${sections}`;

// Abre em nova aba
window.open(url, '_blank');
```

**O que FALTA:**
```javascript
// ❌ FALTA: Capturar modelo selecionado
const modelId = document.getElementById('report_model_selector').value;

// ❌ FALTA: Enviar modelo na requisição
const url = `/api/companies/${companyId}/processes/${processId}/report?sections=${sections}&model_id=${modelId}`;
```

### **3. Endpoint de Geração de Relatório de Processo** ❌

**O que DEVERIA existir em `app_pev.py`:**
```python
@app.route('/api/companies/<int:company_id>/processes/<int:process_id>/report')
def generate_process_report(company_id, process_id):
    """
    Gera relatório de processo com modelo e seções escolhidas
    """
    # 1. Captura parâmetros
    model_id = request.args.get('model_id')
    sections = request.args.getlist('sections')
    
    # 2. Busca dados do processo
    process = get_process_data(process_id)
    company = get_company_data(company_id)
    
    # 3. Carrega modelo (se especificado)
    model = None
    if model_id:
        from modules.report_models import ReportModelsManager
        manager = ReportModelsManager()
        model = manager.get_model(model_id)
    
    # 4. Gera HTML do relatório
    from modules.report_generator import ReportGenerator
    generator = ReportGenerator()
    html = generator.generate_process_report(
        process=process,
        company=company,
        sections=sections,
        model=model
    )
    
    # 5. Retorna HTML ou PDF
    return html
```

**STATUS ATUAL:** ❓ **PRECISA VERIFICAR SE EXISTE**

---

## 🎯 TEMPLATES DE SEÇÕES

### **O que existe:**
```
templates/reports/
├── process_documentation.html       # ✅ Template completo
├── process_documentation_v2.html    # ✅ Template v2
├── process_documentation_model5.html # ✅ Template modelo 5
├── formal_report.html               # ✅ Relatório formal PEV
└── presentation_slides.html         # ✅ Slides PEV
```

### **Como funcionam:**
Esses templates são renderizados diretamente passando todos os dados:
```python
return render_template(
    'reports/process_documentation.html',
    process=process,
    company=company,
    # ... todos os dados ...
)
```

### **O que está FALTANDO:**
Um sistema para **escolher quais seções incluir** dinamicamente!

Atualmente, os templates renderizam TUDO. Precisamos de:
```python
# Sistema que respeita as seções escolhidas
def generate_report(process, sections_selected):
    html_parts = []
    
    if 'flow' in sections_selected:
        html_parts.append(render_flow_section(process))
    
    if 'pop' in sections_selected:
        html_parts.append(render_pop_section(process))
    
    # ... etc
    
    return combine_sections(html_parts)
```

---

## 📊 FLUXO ATUAL vs FLUXO IDEAL

### **FLUXO ATUAL (Parcial):**
```
Usuário clica "Gerar Relatório"
         ↓
Modal abre com checkboxes de seções
         ↓
Seleciona seções (flow, pop, indicators)
         ↓
Clica "Gerar"
         ↓
JavaScript monta URL com sections
         ↓
Abre: /api/.../report?sections=flow,pop
         ↓
❌ ENDPOINT NÃO EXISTE OU NÃO USA MODELO
         ↓
❌ Renderiza template fixo (todas as seções)
```

### **FLUXO IDEAL (Completo):**
```
Usuário clica "Gerar Relatório"
         ↓
Modal abre com:
  - Seletor de modelo
  - Checkboxes de seções
         ↓
Seleciona:
  - Modelo: "Relatório Executivo"
  - Seções: flow, pop, indicators
         ↓
Clica "Gerar"
         ↓
JavaScript envia:
  model_id=3
  sections=flow,pop,indicators
         ↓
✅ Endpoint recebe parâmetros
         ↓
✅ Carrega modelo (margens, cabeçalho, rodapé)
         ↓
✅ Busca dados reais do processo
         ↓
✅ Renderiza APENAS seções selecionadas
         ↓
✅ Aplica estrutura do modelo
         ↓
✅ Gera PDF ou HTML formatado
```

---

## 🔍 CHECKLIST DE VERIFICAÇÃO

Execute os seguintes testes:

### **Teste 1: Modelos Funcionam?**
```
1. Acesse: http://127.0.0.1:5002/settings/reports
2. Configure um modelo
3. Salve com nome "Teste 1"
4. ✅ Aparece na lista?
5. ✅ Botão "Aplicar" carrega os valores?
6. ✅ Botão "Visualizar" abre preview?
7. ✅ Botão "Gerar PDF" baixa arquivo?
```

### **Teste 2: Modal de Processo Funciona?**
```
1. Acesse: /companies/6/processes/X (substitua X por um processo real)
2. Procure botão "Gerar Relatório"
3. ❓ Botão existe?
4. ❓ Modal abre?
5. ❓ Tem checkboxes de seções?
6. ❓ Tem seletor de modelo?
7. ❓ Ao clicar "Gerar", o que acontece?
```

### **Teste 3: Endpoint Existe?**
```bash
# No terminal, procure no código:
grep -n "def.*process.*report" app_pev.py

# Deve retornar algo como:
# 1234:def generate_process_report(company_id, process_id):
```

---

## 🚀 PLANO DE AÇÃO SUGERIDO

### **Fase 1: Diagnóstico Completo** 🔍
1. ✅ Testar criação de modelos em `/settings/reports`
2. ❓ Testar modal em página de processo
3. ❓ Verificar se endpoint de geração existe
4. ❓ Verificar como templates são renderizados

### **Fase 2: Implementação Faltante** 🛠️
Se alguma coisa estiver faltando:

#### **Opção A: Falta o Seletor de Modelo no Modal**
```html
<!-- Adicionar em grv_process_detail.html -->
<div class="form-group">
  <label>Modelo de Página</label>
  <select id="report_model_selector">
    <option value="">Configuração Padrão</option>
    {% for model in report_models %}
      <option value="{{ model.id }}">{{ model.name }}</option>
    {% endfor %}
  </select>
</div>
```

#### **Opção B: Falta o Endpoint de Geração**
```python
# Adicionar em app_pev.py
@app.route('/api/companies/<int:company_id>/processes/<int:process_id>/report')
def generate_process_report(company_id, process_id):
    # Implementação completa
    pass
```

#### **Opção C: Falta Passar Modelo para Template**
```python
# Na rota que renderiza grv_process_detail.html
from modules.report_models import ReportModelsManager

@app.route('/companies/<int:company_id>/processes/<int:process_id>')
def process_detail(company_id, process_id):
    # ... código existente ...
    
    # ADICIONAR:
    models_manager = ReportModelsManager()
    report_models = models_manager.get_all_models()
    
    return render_template(
        'grv_process_detail.html',
        process=process,
        report_models=report_models,  # ← NOVO!
        # ... resto ...
    )
```

---

## 💡 PERGUNTAS PARA O USUÁRIO

Para diagnosticar melhor, precisamos saber:

1. **Quando você vai em uma página de processo e clica "Gerar Relatório", o que acontece?**
   - [ ] Modal abre normalmente
   - [ ] Gera relatório mas ignora seções
   - [ ] Dá erro
   - [ ] Nada acontece

2. **O modal que abre tem seletor de modelo?**
   - [ ] Sim, tem dropdown com modelos
   - [ ] Não, só tem checkboxes de seções
   - [ ] Modal não abre

3. **Quando gera o relatório, ele usa o modelo configurado?**
   - [ ] Sim, usa o modelo selecionado
   - [ ] Não, sempre usa layout padrão
   - [ ] Não gera relatório

4. **As seções selecionadas são respeitadas?**
   - [ ] Sim, só aparecem seções marcadas
   - [ ] Não, sempre mostra tudo
   - [ ] Não testei ainda

---

## 🎯 PRÓXIMO PASSO

**Vamos executar os testes acima e identificar exatamente o que está faltando!**

Depois podemos implementar especificamente o que está faltando sem quebrar o que já funciona.

---

**📌 RESUMO:**

O sistema tem a **base sólida** implementada:
- ✅ Modelos de página funcionam
- ✅ APIs básicas existem
- ✅ Templates existem

O que provavelmente falta é a **conexão entre as partes**:
- ⚠️ Modal completo com seletor de modelo
- ⚠️ Endpoint que recebe modelo + seções
- ⚠️ Lógica para renderizar seções seletivamente

**Vamos agora fazer os testes para confirmar! 🚀**

