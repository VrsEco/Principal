# 🚀 PFPN - Quick Start (Guia Rápido)

**Padrão:** PFPN (Padrão de Formulário com Pilares de Negócio)  
**Tempo de implementação:** ~10 minutos

---

## ⚡ **IMPLEMENTAÇÃO RÁPIDA**

### **1. Copie o CSS (cole no `<style>` do template)**

```css
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
```

---

### **2. Copie o HTML (substitua pelos seus campos)**

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
    <div class="form-group">
      <label for="campo1">Campo 1</label>
      <textarea id="campo1" class="readonly-field" readonly>{{ dados.campo1 or '' }}</textarea>
    </div>
    
    <div class="form-actions" id="form-actions" style="display: none;">
      <button type="button" class="button button-secondary" onclick="cancelarEdicao()">Cancelar</button>
      <button type="submit" class="button button-primary">Salvar</button>
    </div>
  </form>
</div>
```

---

### **3. Copie o JavaScript (atualize os IDs e endpoint)**

```javascript
<script>
  const camposFormulario = ['campo1', 'campo2']; // ← EDITE AQUI
  
  let dadosOriginais = {};
  camposFormulario.forEach(campo => {
    dadosOriginais[campo] = document.getElementById(campo).value;
  });
  
  function editarFormulario() {
    camposFormulario.forEach(campoId => {
      const field = document.getElementById(campoId);
      field.removeAttribute('readonly');
      field.classList.remove('readonly-field');
      field.style.background = 'white';
    });
    document.getElementById('edit-form-btn').style.display = 'none';
    document.getElementById('delete-form-btn').style.display = 'none';
    document.getElementById('form-actions').style.display = 'flex';
  }
  
  function cancelarEdicao() {
    camposFormulario.forEach(campoId => {
      const field = document.getElementById(campoId);
      field.value = dadosOriginais[campoId];
      field.setAttribute('readonly', true);
      field.classList.add('readonly-field');
      field.style.background = '#f1f5f9';
    });
    document.getElementById('edit-form-btn').style.display = 'inline-flex';
    document.getElementById('delete-form-btn').style.display = 'inline-flex';
    document.getElementById('form-actions').style.display = 'none';
  }
  
  async function excluirFormulario() {
    if (!confirm('Tem certeza?')) return;
    // Implementar lógica de exclusão
  }
  
  document.getElementById('meu-formulario').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const data = {};
    camposFormulario.forEach(campoId => {
      data[campoId] = document.getElementById(campoId).value;
    });
    
    const response = await fetch('/api/endpoint', { // ← EDITE AQUI
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      alert('Salvo com sucesso!');
      camposFormulario.forEach(campoId => {
        dadosOriginais[campoId] = document.getElementById(campoId).value;
        const field = document.getElementById(campoId);
        field.setAttribute('readonly', true);
        field.classList.add('readonly-field');
        field.style.background = '#f1f5f9';
      });
      document.getElementById('edit-form-btn').style.display = 'inline-flex';
      document.getElementById('delete-form-btn').style.display = 'inline-flex';
      document.getElementById('form-actions').style.display = 'none';
    }
  });
</script>
```

---

## ✏️ **PERSONALIZE**

1. **Array de campos:**
   ```javascript
   const camposFormulario = ['seu_campo1', 'seu_campo2'];
   ```

2. **Endpoint da API:**
   ```javascript
   fetch('/api/seu-endpoint', { ... })
   ```

3. **Título:**
   ```html
   <h2>Seu Título Aqui</h2>
   ```

---

## ✅ **PRONTO!**

Seu formulário agora tem:
- ✅ Modo visualização (cinza, readonly)
- ✅ Modo edição (branco, editável)
- ✅ Botões Editar, Cancelar, Salvar, Excluir
- ✅ Restauração de valores ao cancelar

---

**📄 Documentação completa:** `docs/patterns/PFPN_PADRAO_FORMULARIO.md`

