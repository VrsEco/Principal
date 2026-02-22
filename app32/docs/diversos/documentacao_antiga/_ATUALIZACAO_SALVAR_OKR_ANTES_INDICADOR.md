# 🔄 Atualização: Salvar OKR Antes de Criar Indicador

## 📋 Problema Identificado

Ao tentar criar um indicador a partir de um OKR que ainda não foi salvo, o sistema não conseguia pré-preencher o campo "OKR Associado" porque o OKR não tinha um ID no banco de dados.

---

## ✅ Solução Implementada

### **Fluxo Inteligente de Validação**

Agora, quando o usuário clica em "📊 Novo Indicador Completo" em um formulário de OKR não salvo:

#### **1. Detectar Estado do OKR**
- Sistema verifica se o OKR já está salvo (tem ID)
- Se **SIM**: Abre o formulário de indicadores diretamente ✅
- Se **NÃO**: Exibe modal de confirmação ⚠️

#### **2. Modal de Confirmação**
```
┌─────────────────────────────────────────┐
│  ⚠️ Salvar OKR Primeiro                 │
├─────────────────────────────────────────┤
│                                          │
│  Para adicionar ou associar um          │
│  indicador, é necessário salvar o       │
│  OKR primeiro.                           │
│                                          │
│  O sistema irá validar os campos        │
│  obrigatórios, salvar o OKR e então     │
│  abrir o formulário de indicadores com  │
│  o Planejamento e OKR já preenchidos.   │
│                                          │
├─────────────────────────────────────────┤
│           [Cancelar] [💾 Salvar e       │
│                      Continuar]          │
└─────────────────────────────────────────┘
```

#### **3. Validação de Campos Obrigatórios**

**Para OKR Global:**
- ✅ Objetivo do OKR
- ✅ Tipo (Estruturante/Aceleração)
- ✅ Direcionador Base

**Para OKR de Área:**
- ✅ Objetivo do OKR
- ✅ Tipo (Estruturante/Aceleração)
- ✅ Área/Departamento
- ✅ OKR Global Base

Se algum campo obrigatório estiver vazio:
```
⚠️ Por favor, preencha os seguintes 
campos obrigatórios antes de continuar:

• Objetivo do OKR
• Tipo
• Direcionador Base
```

Modal fecha e usuário pode preencher os campos faltantes.

#### **4. Salvamento do OKR**

Se todos os campos estiverem preenchidos:
1. Botão muda para "⏳ Salvando..."
2. Sistema envia o formulário via AJAX
3. OKR é salvo no banco de dados
4. Intenção de abrir indicador é guardada no `sessionStorage`
5. Página recarrega

#### **5. Abertura Automática do Formulário de Indicadores**

Após recarregar:
1. Sistema detecta intenção salva no `sessionStorage`
2. Busca o OKR recém-criado pelo título (matching)
3. Extrai o ID do OKR
4. Mostra mensagem: "✅ OKR salvo com sucesso! Abrindo formulário de indicadores..."
5. **Abre automaticamente** o formulário com:
   - ✅ Planejamento pré-selecionado
   - ✅ OKR pré-selecionado
   - ✅ Usuário só precisa preencher os demais campos!

---

## 🔧 Implementação Técnica

### **1. Detecção de Estado**

```javascript
// Check if we're in an edit context with a saved OKR
const hasOkrId = currentEditId && currentEditId > 0;

// If we don't have an OKR ID, we need to save first
if (!hasOkrId) {
    showSaveOkrBeforeIndicatorModal(containerType, planId, pageType, companyId);
    return;
}
```

### **2. Validação de Campos**

```javascript
const objective = form.querySelector('[name="okr_objective"]')?.value?.trim();
const type = form.querySelector('[name="okr_type"]')?.value;
const directional = form.querySelector('[name="okr_directional"]')?.value;

const missingFields = [];
if (!objective) missingFields.push('Objetivo do OKR');
if (!type) missingFields.push('Tipo');
if (!directional) missingFields.push('Direcionador Base');

if (missingFields.length > 0) {
    alert(`⚠️ Por favor, preencha os seguintes campos...`);
    closeSaveOkrModal();
    return;
}
```

### **3. Salvamento com Intenção**

```javascript
// Save intent to open indicator form after reload
sessionStorage.setItem('openIndicatorFormAfterSave', JSON.stringify({
    planId: planId,
    pageType: pageType,
    companyId: companyId,
    okrObjective: objective,
    timestamp: Date.now()
}));

// Submit the form
const response = await fetch(form.action, {
    method: 'POST',
    body: formData
});

// Reload the page
window.location.reload();
```

### **4. Recuperação Automática**

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const intent = sessionStorage.getItem('openIndicatorFormAfterSave');
    
    if (intent) {
        const data = JSON.parse(intent);
        
        // Check if intent is recent (within last 10 seconds)
        if (Date.now() - data.timestamp < 10000) {
            sessionStorage.removeItem('openIndicatorFormAfterSave');
            
            // Find the OKR by matching objective text
            const okrItems = document.querySelectorAll('.okr-workshop-item, .okr-approval-item');
            
            let foundOkrId = null;
            for (const item of okrItems) {
                const objectiveElement = item.querySelector('h5');
                if (objectiveElement && objectiveElement.textContent.includes(data.okrObjective)) {
                    // Extract OKR ID from edit button
                    const editButton = item.querySelector('[onclick*="editOKR"]');
                    const match = editButton.getAttribute('onclick').match(/editOKR\('(\w+)',\s*(\d+)\)/);
                    if (match) {
                        foundOkrId = match[2];
                        break;
                    }
                }
            }
            
            if (foundOkrId) {
                // Open indicator form with OKR ID
                const url = `/grv/company/${data.companyId}/indicators/form?plan_id=${data.planId}&okr_id=${foundOkrId}...`;
                window.open(url, ...);
            }
        }
    }
});
```

---

## 📊 Cenários de Uso

### **Cenário 1: OKR Já Salvo (Editando)**

```
Usuário clica em ✏️ Editar OKR
→ Modal de edição abre
→ Clica em "📊 Novo Indicador Completo"
→ Formulário abre DIRETAMENTE com Planejamento e OKR pré-selecionados ✅
```

### **Cenário 2: OKR Novo (Não Salvo) - Campos Completos**

```
Usuário preenche formulário de novo OKR
→ Preenche: Objetivo, Tipo, Direcionador
→ Clica em "📊 Novo Indicador Completo"
→ Modal aparece: "⚠️ Salvar OKR Primeiro"
→ Clica em "💾 Salvar e Continuar"
→ Sistema valida: ✅ Todos os campos OK
→ Salva o OKR
→ Página recarrega
→ Formulário de indicadores abre AUTOMATICAMENTE com tudo pré-preenchido ✅
```

### **Cenário 3: OKR Novo (Não Salvo) - Campos Incompletos**

```
Usuário começa a preencher novo OKR
→ Preenche apenas: Objetivo
→ Clica em "📊 Novo Indicador Completo"
→ Modal aparece: "⚠️ Salvar OKR Primeiro"
→ Clica em "💾 Salvar e Continuar"
→ Sistema valida: ❌ Faltam campos
→ Alerta: "⚠️ Por favor, preencha os seguintes campos obrigatórios:
           • Tipo
           • Direcionador Base"
→ Modal fecha
→ Usuário preenche os campos faltantes
→ Tenta novamente ✅
```

### **Cenário 4: Cancelamento**

```
Usuário preenche formulário de novo OKR
→ Clica em "📊 Novo Indicador Completo"
→ Modal aparece: "⚠️ Salvar OKR Primeiro"
→ Clica em "Cancelar"
→ Modal fecha
→ Nada acontece, usuário pode continuar editando o OKR ✅
```

---

## 🎯 Benefícios

### **1. Experiência do Usuário**
- ✅ Não há mais confusão sobre por que o OKR não aparece
- ✅ Feedback claro sobre o que precisa ser feito
- ✅ Processo guiado e intuitivo
- ✅ Abertura automática do formulário após salvar

### **2. Validação Inteligente**
- ✅ Valida campos obrigatórios antes de tentar salvar
- ✅ Mensagens de erro claras e específicas
- ✅ Não permite salvar OKR incompleto

### **3. Integração Perfeita**
- ✅ Planejamento e OKR pré-preenchidos automaticamente
- ✅ Fluxo contínuo sem interrupções
- ✅ Menos cliques e menos erros

### **4. Confiabilidade**
- ✅ Usa `sessionStorage` para garantir persistência temporária
- ✅ Timeout de 10 segundos para evitar ações duplicadas
- ✅ Tratamento de erros robusto

---

## 📂 Arquivos Modificados

### **1. `templates/plan_okr_global.html`**
- ✅ Função `openIndicatorFormFromOKR()` - Detecta se OKR está salvo
- ✅ Função `showSaveOkrBeforeIndicatorModal()` - Exibe modal de confirmação
- ✅ Função `saveOkrAndOpenIndicatorForm()` - Valida, salva e guarda intenção
- ✅ Event listener `DOMContentLoaded` - Recupera intenção e abre formulário

### **2. `templates/plan_okr_area.html`**
- ✅ Mesmas funções adaptadas para OKRs de Área
- ✅ Validação inclui campos específicos (Área/Departamento, OKR Global Base)

---

## 🧪 Como Testar

### **Teste 1: OKR Novo - Campos Completos**

1. Acesse: `http://127.0.0.1:5002/plans/5/okr-global`
2. Abra seção "Versão Preliminar"
3. Preencha:
   - Direcionador Base: [selecione um]
   - Objetivo: "Aumentar receita em 30%"
   - Tipo: "Estruturante"
4. **NÃO clique em "Salvar OKR Preliminar"**
5. Clique em "📊 Novo Indicador Completo"
6. **Esperado**: Modal aparece
7. Clique em "💾 Salvar e Continuar"
8. **Esperado**: 
   - OKR é salvo
   - Página recarrega
   - Mensagem: "✅ OKR salvo com sucesso!"
   - Formulário de indicadores abre automaticamente
   - Planejamento e OKR já estão selecionados

### **Teste 2: OKR Novo - Campos Incompletos**

1. Acesse: `http://127.0.0.1:5002/plans/5/okr-global`
2. Abra seção "Versão Preliminar"
3. Preencha apenas:
   - Objetivo: "Aumentar vendas"
4. Clique em "📊 Novo Indicador Completo"
5. **Esperado**: Modal aparece
6. Clique em "💾 Salvar e Continuar"
7. **Esperado**: 
   - Alerta com campos faltantes: "⚠️ Por favor, preencha: • Tipo • Direcionador Base"
   - Modal fecha
   - Formulário permanece na tela

### **Teste 3: Cancelamento**

1. Siga passos do Teste 1
2. Quando o modal aparecer, clique em "Cancelar"
3. **Esperado**: 
   - Modal fecha
   - Formulário de OKR permanece aberto
   - Nada é salvo

### **Teste 4: OKR Já Salvo (Editando)**

1. Acesse: `http://127.0.0.1:5002/plans/5/okr-global`
2. Encontre um OKR existente na lista
3. Clique em "✏️ Editar"
4. No modal de edição, clique em "📊 Novo Indicador Completo"
5. **Esperado**: 
   - Formulário de indicadores abre DIRETAMENTE (sem modal intermediário)
   - Planejamento e OKR já estão selecionados

---

## ⚙️ Configurações Técnicas

### **SessionStorage**
- **Chave**: `openIndicatorFormAfterSave`
- **Timeout**: 10 segundos
- **Conteúdo**: `{ planId, pageType, companyId, okrObjective, timestamp }`

### **Campos Obrigatórios**

**OKR Global:**
- `okr_objective` - Objetivo do OKR
- `okr_type` - Tipo (estruturante/aceleracao)
- `okr_directional` - Direcionador Base

**OKR de Área:**
- `okr_objective` - Objetivo do OKR
- `okr_type` - Tipo (estruturante/aceleracao)
- `okr_department` - Área/Departamento
- `okr_global_ref` - OKR Global Base

---

## 🎉 Resultado Final

Agora os usuários têm uma experiência fluida e intuitiva:

1. ✅ **Tentam criar indicador** → Sistema detecta que OKR não está salvo
2. ✅ **Recebem orientação clara** → "Precisa salvar primeiro"
3. ✅ **Sistema valida campos** → Garante que dados obrigatórios estão completos
4. ✅ **Salva automaticamente** → Sem esforço adicional
5. ✅ **Abre formulário pronto** → Com Planejamento e OKR já preenchidos

**Status**: ✅ **Implementação Completa e Testada**

**Data**: Outubro 2025

