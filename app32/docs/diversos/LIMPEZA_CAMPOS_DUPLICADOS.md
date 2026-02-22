# 🧹 Limpeza de Campos Duplicados do PEV

## ✅ Objetivo

Remover campos duplicados do PEV que agora são gerenciados no **Cadastro Centralizado de Empresas**.

---

## 🗑️ Campos Removidos do PEV

### **1. Headcount por Nível** (3 campos)
- ❌ `headcount_strategic` (Diretoria/Estratégico)
- ❌ `headcount_tactical` (Gerência/Tático)
- ❌ `headcount_operational` (Operação/Operacional)

**Novo local:** Aba "💰 Cadastro Econômico" em `/companies/<id>`

### **2. Missão/Visão/Valores** (3 campos)
- ❌ `mission` (Missão)
- ❌ `vision` (Visão)
- ❌ `company_values` (Valores da Organização)

**Novo local:** Aba "🎯 MVV" em `/companies/<id>`

### **3. Uploads de PDF** (2 campos)
- ❌ `process_map_file` (Mapa de Processos PDF)
- ❌ `org_chart_file` (Organograma PDF)

**Motivo da remoção:**
- Mapa de Processos: Agora gerenciado pelo GRV dinamicamente
- Organograma: Agora gerado automaticamente pelo GRV com base em funções/colaboradores

---

## 📂 Arquivos Modificados

### **1. Template do PEV** ✅
**Arquivo:** `templates/plan_company.html`

**Removido:**
- Seção de Headcount (3 cards)
- Seção de MVV (3 textareas)
- Upload de Mapa de Processos
- Upload de Organograma

**Adicionado:**
- Box informativo explicando a migração
- Link direto para cadastro centralizado

```html
<!-- Box informativo -->
<div style="background: #eff6ff; border: 2px solid #3b82f6;">
  ℹ️ Campos Migrados para Cadastro Centralizado
  
  - Missão/Visão/Valores → Aba "🎯 MVV"
  - Headcount → Aba "💰 Cadastro Econômico"
  - Funções e Colaboradores → Abas "👔" e "👥"
  
  [⚙️ Acessar Cadastro Centralizado]
</div>
```

### **2. Backend - Salvamento** ✅
**Arquivo:** `app_pev.py` (linha ~3240)

**Removido do payload de salvamento:**
```python
# ANTES - 14 campos
data = {
    'mission': ...,
    'vision': ...,
    'company_values': ...,
    'headcount_strategic': ...,
    'headcount_tactical': ...,
    'headcount_operational': ...,
    'process_map_file': ...,
    'org_chart_file': ...,
    ...outros...
}

# DEPOIS - 6 campos a menos
data = {
    'trade_name': ...,
    'legal_name': ...,
    'cnpj': ...,
    'coverage_physical': ...,
    'coverage_online': ...,
    'experience_total': ...,
    'experience_segment': ...,
    'cnaes': ...,
    'financials': ...,
    'financial_total_revenue': ...,
    'financial_total_margin': ...,
    'other_information': ...,
    # Campos de análise preservados
    'ai_insights': ...,
    'consultant_analysis': ...
}
```

**Removido também:**
- Lógica de upload de PDF (process_map, org_chart)
- Processamento de arquivos

---

## 💾 Backup Realizado

**Arquivo:** `backup_company_data_20251010_201913.json`

**Conteúdo:** Todos os dados da tabela `company_data` antes das alterações

**Registros salvos:** 3

**Uso futuro:** Caso seja necessário recuperar dados antigos

---

## 🔄 Onde os Dados Estão Agora

### **Tabela `companies` (Centralizada)**

**Headcount:**
- `companies.headcount_strategic`
- `companies.headcount_tactical`
- `companies.headcount_operational`

**MVV:**
- `companies.mvv_mission`
- `companies.mvv_vision`
- `companies.mvv_values`

**Localização e Fiscal:**
- `companies.cnpj`
- `companies.city`
- `companies.state`
- `companies.cnaes`

**Outros econômicos:**
- `companies.coverage_physical`
- `companies.coverage_online`
- `companies.experience_total`
- `companies.experience_segment`
- `companies.financial_total_revenue`
- `companies.financial_total_margin`

### **Tabela `company_data` (PEV - Específicos do Plano)**

**Mantidos:**
- `trade_name` - Nome comercial específico do plano
- `legal_name` - Razão social específica
- `cnpj` - CNPJ específico (pode variar por plano)
- `coverage_physical` - Cobertura no momento do plano
- `coverage_online` - Cobertura online no momento do plano
- `experience_total` - Experiência na data do plano
- `experience_segment` - Experiência no segmento na data
- `cnaes` - CNAEs no momento do plano
- `financials` - Dados financeiros detalhados (JSON)
- `financial_total_revenue` - Receita total calculada
- `financial_total_margin` - Margem total calculada
- `other_information` - Outras informações
- `ai_insights` - Análises de IA
- `consultant_analysis` - Análises do consultor

**Removidos:**
- ❌ `mission`, `vision`, `company_values`
- ❌ `headcount_strategic`, `headcount_tactical`, `headcount_operational`
- ❌ `process_map_file`, `org_chart_file`

---

## 🎯 Benefícios da Limpeza

### **1. Eliminação de Duplicação**
- ✅ Dados agora têm **fonte única de verdade**
- ✅ Não há conflito entre company_data e companies
- ✅ Sincronização automática

### **2. Melhor Organização**
- ✅ Dados gerais em `companies`
- ✅ Dados específicos do plano em `company_data`
- ✅ Hierarquia clara de informações

### **3. Facilidade de Manutenção**
- ✅ Atualizar uma vez, reflete em todos os lugares
- ✅ Menos código duplicado
- ✅ Menos chance de inconsistências

### **4. Integração**
- ✅ GRV usa dados de `companies`
- ✅ PEV usa dados de `companies` + `company_data`
- ✅ Futuros módulos usam `companies`

---

## 🔍 O Que Ficou no PEV

### **company_data ainda tem utilidade:**

**Dados históricos/temporais:**
- Informações específicas do plano estratégico
- Snapshot da empresa no momento do plano
- Análises de IA e consultoria específicas

**Dados financeiros detalhados:**
- Array `financials` com quebra por linha de negócio
- Métricas calculadas para o plano específico

**Análises:**
- `ai_insights` - Insights de IA
- `consultant_analysis` - Análise do consultor

---

## 🚀 Fluxo Atualizado

### **Para dados gerais da empresa:**
1. Acesse: `/companies/<id>`
2. Use as 5 abas:
   - Dados Básicos
   - MVV
   - Funções/Cargos
   - Colaboradores
   - Cadastro Econômico

### **Para dados do plano PEV:**
1. Acesse: `/plans/<plan_id>/company`
2. Veja o box informativo
3. Clique em "Acessar Cadastro Centralizado" se precisar editar MVV, Headcount, etc.

---

## ✅ Status Final

**LIMPEZA COMPLETA E FUNCIONAL**

**Removido:**
- 8 campos duplicados do PEV
- Código de upload de PDF
- Interface redundante

**Benefícios:**
- Fonte única de verdade
- Melhor organização
- Facilita manutenção
- Integração entre módulos

**Backup:**
- Dados salvos em JSON
- Recuperação possível se necessário

**Documentação:**
- `LIMPEZA_CAMPOS_DUPLICADOS.md` (este arquivo)
- `RESUMO_FINAL_SESSAO.md`
- `ABA_CADASTRO_ECONOMICO.md`

**Sistema limpo e organizado!** 🧹✨
