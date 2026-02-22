# 📋 PFPN - Padrão de Formulário com Pilares de Negócio

**Nome:** PFPN (Padrão de Formulário com Pilares de Negócio)  
**Versão:** 1.0  
**Data:** 23/10/2025  
**Autor:** Cursor AI  
**Status:** ✅ Aprovado

---

## 🎯 **OBJETIVO**

Padrão de formulário com **dois modos** (Visualização e Edição), onde:
- **Visualização:** Campos com fundo cinza (readonly)
- **Edição:** Campos com fundo branco (editável)

---

## 🎨 **VISUAL**

### **Modo Visualização (Padrão):**
```
┌─────────────────────────────────────────┐
│ Título do Formulário  [✏️ Editar] [🗑️ Excluir] │
├─────────────────────────────────────────┤
│ Campo 1:                                │
│ ┌─────────────────────────────────────┐ │
│ │ Conteúdo... (FUNDO CINZA #f1f5f9)   │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Campo 2:                                │
│ ┌─────────────────────────────────────┐ │
│ │ Conteúdo... (FUNDO CINZA #f1f5f9)   │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### **Modo Edição:**
```
┌─────────────────────────────────────────┐
│ Título do Formulário                    │
├─────────────────────────────────────────┤
│ Campo 1:                                │
│ ┌─────────────────────────────────────┐ │
│ │ Conteúdo... (FUNDO BRANCO)          │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Campo 2:                                │
│ ┌─────────────────────────────────────┐ │
│ │ Conteúdo... (FUNDO BRANCO)          │ │
│ └─────────────────────────────────────┘ │
│                                         │
│        [Cancelar] [Salvar]              │
└─────────────────────────────────────────┘
```

---

## 📦 **COMPONENTES**

### **1. CSS**

```css
/* Campos em modo readonly (visualização) */
textarea.readonly-field,
input.readonly-field {
  background: #f1f5f9 !important;
  cursor: not-allowed;
  color: #475569 !important;
}

textarea.readonly-field:focus,
input.readonly-field:focus {
  border-color: rgba(148, 163, 184, 0.3) !important;
  box-shadow: none !important;
}

/* Campos normais (edição) */
.form-group input,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  background: white;
  color: #0f172a;
  font-size: 14px;
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
```

---

### **2. HTML Template**

```html
<div class="canvas-card canvas-section">
  <h2>
    Título do Formulário
    <div style="display: flex; gap: 8px;">
      <button id="edit-form-btn" class="button button-secondary button-sm" 
              onclick="editarFormulario()" style="display: inline-flex;">
        ✏️ Editar
      </button>
      <button id="delete-form-btn" class="button button-danger button-sm" 
              onclick="excluirFormulario()" style="display: inline-flex;">
        🗑️ Excluir
      </button>
    </div>
  </h2>
  
  <form id="meu-formulario">
    <!-- Campo 1 -->
    <div class="form-group">
      <label for="campo1">Campo 1</label>
      <textarea id="campo1" name="campo1" class="readonly-field" readonly>{{ dados.campo1 or '' }}</textarea>
    </div>
    
    <!-- Campo 2 -->
    <div class="form-group">
      <label for="campo2">Campo 2</label>
      <textarea id="campo2" name="campo2" class="readonly-field" readonly>{{ dados.campo2 or '' }}</textarea>
    </div>
    
    <!-- Campo 3 (lista, um item por linha) -->
    <div class="form-group">
      <label for="campo3">Campo 3 (um por linha)</label>
      <textarea id="campo3" name="campo3" class="readonly-field" readonly>{% if dados.campo3 %}{{ dados.campo3 | join('\n') }}{% endif %}</textarea>
    </div>
    
    <!-- Ações (oculto por padrão) -->
    <div class="form-actions" id="form-actions" style="display: none;">
      <button type="button" class="button button-secondary" onclick="cancelarEdicao()">Cancelar</button>
      <button type="submit" class="button button-primary">Salvar</button>
    </div>
  </form>
</div>
```

---

### **3. JavaScript**

```javascript
// IDs dos campos que fazem parte do formulário
const camposFormulario = ['campo1', 'campo2', 'campo3'];

// Armazenar valores originais
let dadosOriginais = {};
camposFormulario.forEach(campo => {
  dadosOriginais[campo] = document.getElementById(campo).value;
});

/**
 * PFPN: Função para entrar no modo de edição
 */
function editarFormulario() {
  // Habilitar todos os campos
  camposFormulario.forEach(campoId => {
    const field = document.getElementById(campoId);
    field.removeAttribute('readonly');
    field.classList.remove('readonly-field');
    field.style.background = 'white';
  });
  
  // Esconder botões editar/excluir
  document.getElementById('edit-form-btn').style.display = 'none';
  document.getElementById('delete-form-btn').style.display = 'none';
  
  // Mostrar ações de salvar/cancelar
  document.getElementById('form-actions').style.display = 'flex';
}

/**
 * PFPN: Função para cancelar edição e restaurar valores
 */
function cancelarEdicao() {
  // Restaurar valores originais
  camposFormulario.forEach(campoId => {
    document.getElementById(campoId).value = dadosOriginais[campoId];
  });
  
  // Desabilitar todos os campos
  camposFormulario.forEach(campoId => {
    const field = document.getElementById(campoId);
    field.setAttribute('readonly', true);
    field.classList.add('readonly-field');
    field.style.background = '#f1f5f9';
  });
  
  // Mostrar botões editar/excluir
  document.getElementById('edit-form-btn').style.display = 'inline-flex';
  document.getElementById('delete-form-btn').style.display = 'inline-flex';
  
  // Esconder ações
  document.getElementById('form-actions').style.display = 'none';
}

/**
 * PFPN: Função para excluir todos os dados
 */
async function excluirFormulario() {
  if (!confirm('Tem certeza que deseja excluir todos os dados?')) return;
  
  // Limpar campos
  camposFormulario.forEach(campoId => {
    document.getElementById(campoId).value = '';
  });
  
  // Preparar dados vazios
  const data = {};
  camposFormulario.forEach(campoId => {
    data[campoId] = '';
  });
  
  try {
    const response = await fetch(`/api/endpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      showMessage('Dados excluídos com sucesso!', 'success');
      dadosOriginais = data;
    } else {
      showMessage('Erro ao excluir: ' + result.error, 'error');
    }
  } catch (error) {
    showMessage('Erro ao excluir dados', 'error');
  }
}

/**
 * PFPN: Handler do formulário (submit)
 */
document.getElementById('meu-formulario').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Coletar dados
  const data = {};
  camposFormulario.forEach(campoId => {
    const value = document.getElementById(campoId).value;
    
    // Se for um campo de lista (um item por linha), converter para array
    if (campoId === 'campo3') {
      data[campoId] = value.split('\n').map(v => v.trim()).filter(v => v.length > 0);
    } else {
      data[campoId] = value;
    }
  });
  
  try {
    const response = await fetch(`/api/endpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      showMessage('Dados salvos com sucesso!', 'success');
      
      // Atualizar valores originais
      camposFormulario.forEach(campoId => {
        dadosOriginais[campoId] = document.getElementById(campoId).value;
      });
      
      // Voltar ao modo visualização
      camposFormulario.forEach(campoId => {
        const field = document.getElementById(campoId);
        field.setAttribute('readonly', true);
        field.classList.add('readonly-field');
        field.style.background = '#f1f5f9';
      });
      
      // Mostrar botões editar/excluir
      document.getElementById('edit-form-btn').style.display = 'inline-flex';
      document.getElementById('delete-form-btn').style.display = 'inline-flex';
      
      // Esconder ações
      document.getElementById('form-actions').style.display = 'none';
    } else {
      showMessage('Erro ao salvar: ' + result.error, 'error');
    }
  } catch (error) {
    showMessage('Erro ao salvar dados', 'error');
  }
});

/**
 * PFPN: Função auxiliar para mostrar mensagens
 */
function showMessage(message, type = 'info') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 16px 24px;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    z-index: 10000;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  `;
  
  const colors = {
    success: '#10b981',
    error: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6'
  };
  
  notification.style.backgroundColor = colors[type] || colors.info;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 5000);
}
```

---

## 🔄 **FLUXO DE USO**

```
1. Página carrega
   ↓
2. Campos em modo VISUALIZAÇÃO (cinza, readonly)
   ↓
3. Usuário clica "✏️ Editar"
   ↓
4. Campos ficam BRANCOS e EDITÁVEIS
   ↓
5. Usuário edita o conteúdo
   ↓
6a. Clica "Salvar" → Salva + Notificação + Volta ao cinza
   OU
6b. Clica "Cancelar" → Descarta mudanças + Volta ao cinza
   OU
6c. Clica "🗑️ Excluir" → Confirma + Limpa tudo + Salva vazio
```

---

## ✅ **CHECKLIST DE IMPLEMENTAÇÃO**

Ao aplicar o padrão PFPN em um novo formulário:

- [ ] Adicionar CSS do padrão
- [ ] Criar HTML com estrutura correta
- [ ] Definir array `camposFormulario` com IDs dos campos
- [ ] Implementar `editarFormulario()`
- [ ] Implementar `cancelarEdicao()`
- [ ] Implementar `excluirFormulario()`
- [ ] Implementar handler de submit
- [ ] Atualizar endpoint da API
- [ ] Testar fluxo completo (editar → salvar)
- [ ] Testar fluxo de cancelamento
- [ ] Testar fluxo de exclusão

---

## 📝 **EXEMPLO DE APLICAÇÃO**

### **Arquivo:** `templates/meu_formulario.html`

```html
<!-- CSS -->
<style>
  textarea.readonly-field,
  input.readonly-field {
    background: #f1f5f9 !important;
    cursor: not-allowed;
    color: #475569 !important;
  }
  /* ... resto do CSS do padrão ... */
</style>

<!-- HTML -->
<div class="canvas-card canvas-section">
  <h2>
    Meus Dados
    <div style="display: flex; gap: 8px;">
      <button id="edit-form-btn" class="button button-secondary button-sm" 
              onclick="editarFormulario()">✏️ Editar</button>
      <button id="delete-form-btn" class="button button-danger button-sm" 
              onclick="excluirFormulario()">🗑️ Excluir</button>
    </div>
  </h2>
  
  <form id="meu-formulario">
    <div class="form-group">
      <label for="nome">Nome</label>
      <input type="text" id="nome" class="readonly-field" readonly 
             value="{{ dados.nome or '' }}">
    </div>
    
    <div class="form-group">
      <label for="descricao">Descrição</label>
      <textarea id="descricao" class="readonly-field" readonly>{{ dados.descricao or '' }}</textarea>
    </div>
    
    <div class="form-actions" id="form-actions" style="display: none;">
      <button type="button" class="button button-secondary" 
              onclick="cancelarEdicao()">Cancelar</button>
      <button type="submit" class="button button-primary">Salvar</button>
    </div>
  </form>
</div>

<!-- JavaScript -->
<script>
  const camposFormulario = ['nome', 'descricao'];
  
  let dadosOriginais = {};
  camposFormulario.forEach(campo => {
    dadosOriginais[campo] = document.getElementById(campo).value;
  });
  
  // ... resto do JavaScript do padrão ...
</script>
```

---

## 🎨 **CORES E ESTILOS**

| Elemento | Cor/Estilo |
|----------|-----------|
| Fundo readonly | `#f1f5f9` (cinza claro) |
| Fundo editável | `white` |
| Texto readonly | `#475569` (cinza escuro) |
| Texto editável | `#0f172a` (preto) |
| Borda normal | `rgba(148, 163, 184, 0.3)` |
| Borda focus | `#3b82f6` (azul) |
| Shadow focus | `rgba(59, 130, 246, 0.1)` |

---

## 📋 **VARIAÇÕES**

### **Variação 1: Com validação**
```javascript
document.getElementById('meu-formulario').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Validar campos obrigatórios
  if (!document.getElementById('campo1').value.trim()) {
    showMessage('Campo 1 é obrigatório!', 'error');
    return;
  }
  
  // ... resto do código ...
});
```

### **Variação 2: Sem botão Excluir**
```html
<h2>
  Título do Formulário
  <button id="edit-form-btn" class="button button-secondary button-sm" 
          onclick="editarFormulario()">✏️ Editar</button>
</h2>
```

### **Variação 3: Com confirmação ao salvar**
```javascript
if (!confirm('Deseja salvar as alterações?')) return;
```

---

## 🚀 **BENEFÍCIOS DO PADRÃO**

1. ✅ **Consistência:** Mesmo comportamento em todos os formulários
2. ✅ **UX profissional:** Estados visuais claros
3. ✅ **Segurança:** Confirmação antes de excluir
4. ✅ **Reversibilidade:** Cancelar mudanças a qualquer momento
5. ✅ **Simplicidade:** Código reutilizável e fácil de manter
6. ✅ **Feedback claro:** Notificações de sucesso/erro

---

## 📚 **REFERÊNCIAS**

- Implementado em: `templates/implantacao/alinhamento_canvas_expectativas.html`
- Documentação original: `MELHORIA_UX_ALINHAMENTO.md`
- Data de criação: 23/10/2025

---

**Versão:** 1.0  
**Última atualização:** 23/10/2025  
**Status:** ✅ Aprovado para uso em produção

