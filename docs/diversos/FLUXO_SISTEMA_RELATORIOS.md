# 📊 FLUXO COMPLETO DO SISTEMA DE RELATÓRIOS - APP28

## 🎯 Visão Geral do Sistema

O sistema de relatórios funciona em **DUAS ETAPAS DISTINTAS**:

### **ETAPA 1: Configuração de Estrutura de Página (Modelo)**
### **ETAPA 2: Geração de Relatórios com Conteúdo**

---

## 📋 ETAPA 1: Configuração de Estrutura de Página

### **O QUE É?**
É a criação de um **modelo/template** que define apenas:
- ✅ Tamanho do papel (A4, Carta, Ofício)
- ✅ Orientação (Retrato ou Paisagem)
- ✅ Margens (superior, inferior, esquerda, direita)
- ✅ Cabeçalho (altura, linhas, colunas, conteúdo)
- ✅ Rodapé (altura, linhas, colunas, conteúdo)

### **ONDE FAZER?**
```
http://127.0.0.1:5002/settings/reports
```

### **O QUE ACONTECE?**
1. Você configura os parâmetros visuais da página
2. Define conteúdo do cabeçalho/rodapé com variáveis:
   - `{{ company.name }}` - Nome da empresa
   - `{{ report.title }}` - Título do relatório
   - `{{ date }}` - Data atual
   - `{{ page }}` - Número da página
   - Etc.
3. Salva o modelo com um nome (ex: "Relatório Executivo A4")

### **RESULTADO:**
Um **MODELO** é salvo no banco de dados (`report_models`) com:
- Estrutura da página
- Configurações de cabeçalho/rodapé
- Nenhum conteúdo específico ainda!

---

## 📄 ETAPA 2: Geração de Relatórios com Conteúdo

### **O QUE É?**
É a aplicação do modelo criado + inserção de **conteúdo real** para gerar o relatório final.

### **ONDE ACONTECE?**
Existem diferentes locais dependendo do tipo de relatório:

#### **A) Relatórios de Processos (GRV)**
- **Página:** `/companies/<company_id>/processes/<process_id>`
- **Como:** Botão "Gerar Relatório" → Seleciona seções
- **Seções disponíveis:**
  - 🔄 Fluxo do Processo
  - 📋 POP - Procedimento Operacional
  - 📊 Indicadores
  - 📝 Rotinas Associadas
  - 📈 Análises

#### **B) Relatórios de Teste (Settings)**
- **Página:** `/settings/reports`
- **Como:** Botão "Visualizar Impressão" ou "Gerar PDF"
- **Conteúdo:** Dados fictícios do sistema para teste

#### **C) Relatórios do PEV (Planejamento Estratégico)**
- **Página:** `/plans/<plan_id>/reports` (ainda em desenvolvimento)
- **Seções possíveis:**
  - Dashboard
  - Participantes
  - Empresa
  - Direcionadores
  - OKRs
  - Projetos

### **O QUE ACONTECE NA GERAÇÃO?**

```
┌────────────────────────────────────────────────┐
│  1. Usuário clica "Gerar Relatório"           │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  2. Sistema pergunta: qual modelo usar?        │
│     (pode usar um modelo salvo ou config atual)│
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  3. Usuário seleciona SEÇÕES do relatório      │
│     Ex: ☑ Introdução                          │
│         ☑ Dados da Empresa                    │
│         ☑ Projetos                            │
│         ☐ Análises                            │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  4. Sistema busca DADOS REAIS do banco         │
│     - Dados da empresa                         │
│     - Projetos                                 │
│     - Processos                                │
│     - Colaboradores                            │
│     - Métricas calculadas                      │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  5. Sistema MONTA o relatório:                 │
│     ┌──────────────────────────────────┐      │
│     │ CABEÇALHO (do modelo)            │      │
│     ├──────────────────────────────────┤      │
│     │ SEÇÃO 1: Introdução              │      │
│     │ (conteúdo real do banco)         │      │
│     ├──────────────────────────────────┤      │
│     │ SEÇÃO 2: Dados da Empresa        │      │
│     │ (conteúdo real do banco)         │      │
│     ├──────────────────────────────────┤      │
│     │ SEÇÃO 3: Projetos                │      │
│     │ (conteúdo real do banco)         │      │
│     ├──────────────────────────────────┤      │
│     │ RODAPÉ (do modelo)               │      │
│     └──────────────────────────────────┘      │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  6. Sistema gera HTML → converte para PDF     │
└──────────────┬─────────────────────────────────┘
               │
               ▼
┌────────────────────────────────────────────────┐
│  7. Usuário baixa/visualiza o relatório       │
└────────────────────────────────────────────────┘
```

---

## 🔧 ARQUITETURA DO SISTEMA

### **Módulos Python:**

```
modules/
├── report_models.py           # Gerencia MODELOS (estrutura)
│   └── Salva/Carrega/Edita modelos de página
│
├── report_generator.py        # Gera RELATÓRIOS (conteúdo)
│   └── Monta HTML com dados reais
│
└── placeholder_generator.py   # Gera dados de TESTE
    └── Para testar modelos sem dados reais
```

### **Banco de Dados:**

```sql
-- Tabela de MODELOS (estrutura de página)
report_models:
  - id
  - name
  - description
  - paper_size, orientation
  - margins (top, right, bottom, left)
  - header (height, rows, columns, content)
  - footer (height, rows, columns, content)

-- Tabela de INSTÂNCIAS (relatórios gerados)
report_instances:
  - id
  - model_id (qual modelo foi usado)
  - title
  - report_type
  - company_id
  - file_path
  - generated_at
```

---

## 🎨 EXEMPLO PRÁTICO COMPLETO

### **Cenário: Gerar Relatório de Processo**

#### **Passo 1: Criar Modelo (uma vez)**
```
1. Acessa: http://127.0.0.1:5002/settings/reports
2. Configura:
   - Papel: A4
   - Orientação: Retrato
   - Margens: 20mm todas
   - Cabeçalho: "{{ company.name }} - {{ report.title }}"
   - Rodapé: "Página {{ page }} de {{ pages }}"
3. Salva como: "Modelo Processo Padrão"
```

#### **Passo 2: Gerar Relatório (sempre que precisar)**
```
1. Vai para: /companies/6/processes/123
2. Clica: "Gerar Relatório"
3. Modal abre pedindo:
   ┌─────────────────────────────────────┐
   │ Selecione o modelo:                 │
   │ [▼] Modelo Processo Padrão          │
   │                                     │
   │ Selecione as seções:                │
   │ ☑ Fluxo do Processo                │
   │ ☑ POP                              │
   │ ☐ Indicadores                      │
   │ ☑ Rotinas                          │
   │                                     │
   │ [Cancelar]  [Gerar Relatório]      │
   └─────────────────────────────────────┘
4. Sistema gera o relatório com:
   - Estrutura do "Modelo Processo Padrão"
   - Conteúdo real do processo 123
   - Apenas as seções marcadas
```

---

## 🔍 DIAGNÓSTICO: O QUE PODE ESTAR FALTANDO

Com base na sua descrição, aqui está o que pode estar faltando:

### **✅ JÁ IMPLEMENTADO:**
1. ✅ Página de configuração de modelos (`/settings/reports`)
2. ✅ Salvamento de modelos no banco
3. ✅ Geração de HTML com dados
4. ✅ Sistema de placeholder para testes

### **❌ PODE ESTAR FALTANDO:**

#### **1. Modal de Seleção de Seções nos Processos**
```python
# Verificar se existe em: templates/grv_process_detail.html
# Deve ter um modal como:
<div class="report-modal">
  <h3>Gerar Relatório</h3>
  
  <!-- SELETOR DE MODELO -->
  <select id="report_model">
    <option value="">Configuração Padrão</option>
    {% for model in models %}
      <option value="{{ model.id }}">{{ model.name }}</option>
    {% endfor %}
  </select>
  
  <!-- SELETOR DE SEÇÕES -->
  <label><input type="checkbox" value="flow" checked> Fluxo</label>
  <label><input type="checkbox" value="pop" checked> POP</label>
  <label><input type="checkbox" value="indicators"> Indicadores</label>
  
  <button onclick="generateReport()">Gerar</button>
</div>
```

#### **2. Endpoint de Geração com Modelo e Seções**
```python
# Verificar em app_pev.py se existe:
@app.route('/api/companies/<int:company_id>/processes/<int:process_id>/report')
def generate_process_report(company_id, process_id):
    # Deve receber:
    model_id = request.args.get('model_id')
    sections = request.args.getlist('sections')
    
    # Buscar dados reais
    process = get_process(process_id)
    
    # Aplicar modelo
    if model_id:
        model = report_models_manager.get_model(model_id)
    
    # Gerar relatório com seções selecionadas
    html = report_generator.generate(process, sections, model)
    
    return html
```

#### **3. Templates de Seções Individuais**
Cada tipo de relatório precisa de templates para suas seções:
```
templates/reports/
├── process_sections/
│   ├── flow.html         # Seção de fluxo
│   ├── pop.html          # Seção de POP
│   ├── indicators.html   # Seção de indicadores
│   └── routines.html     # Seção de rotinas
```

---

## 🚀 PRÓXIMOS PASSOS SUGERIDOS

### **Para Entender o Estado Atual:**

1. **Verificar o modal de relatório:**
   ```bash
   # Ver se tem modal completo em grv_process_detail.html
   ```

2. **Verificar endpoints de geração:**
   ```bash
   # Ver quais endpoints de geração existem em app_pev.py
   ```

3. **Testar o fluxo:**
   ```bash
   # Ir em /companies/6/processes/X
   # Clicar em "Gerar Relatório"
   # Ver o que acontece
   ```

---

## 💡 RESUMO SIMPLIFICADO

```
┌─────────────────────────────────────────────────────────┐
│  ETAPA 1: CONFIGURAR MODELO (estrutura visual)          │
│  📍 Local: /settings/reports                            │
│  🎯 Objetivo: Definir layout da página                  │
│  💾 Salva em: report_models                             │
└─────────────────────────────────────────────────────────┘
                         │
                         │ (usa para)
                         ▼
┌─────────────────────────────────────────────────────────┐
│  ETAPA 2: GERAR RELATÓRIO (conteúdo + estrutura)       │
│  📍 Local: várias páginas do sistema                   │
│  🎯 Objetivo: Criar relatório com dados reais          │
│  📝 Processo:                                           │
│     1. Escolhe modelo (ou usa padrão)                  │
│     2. Escolhe seções para incluir                     │
│     3. Sistema busca dados reais                       │
│     4. Monta HTML e gera PDF                           │
│  💾 Salva em: report_instances + arquivo PDF           │
└─────────────────────────────────────────────────────────┘
```

---

**🎯 CONCLUSÃO:**

O sistema TEM os dois componentes principais:
1. ✅ **Configuração de modelos** (estrutura de página)
2. ✅ **Geração de relatórios** (conteúdo)

O que pode estar faltando é a **CONEXÃO** entre eles em alguns locais do sistema, principalmente:
- Modal completo de seleção nas páginas de processos
- Endpoint que recebe modelo + seções + dados reais
- Templates para renderizar cada tipo de seção

**Vamos agora verificar o que especificamente está faltando ou não está funcionando!** 🔍

