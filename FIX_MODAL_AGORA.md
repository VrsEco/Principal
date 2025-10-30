# 🔧 FIX IMEDIATO - Forçar HTML do Modal

## 🎯 PROBLEMA

`modalContent` está `null` - o HTML não está sendo inserido no modal.

## ✅ SOLUÇÃO IMEDIATA

Cole este código no **Console (F12)**:

```javascript
const modal = document.getElementById('capitalGiroModal');

// Inserir HTML completo forçadamente
modal.innerHTML = `
  <div class="modal-content" style="
    background: white !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    padding: 32px !important;
    border-radius: 16px !important;
    max-width: 600px !important;
    width: 90% !important;
    max-height: 90vh !important;
    overflow-y: auto !important;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3) !important;
    position: relative !important;
    z-index: 10 !important;
    display: block !important;
    opacity: 1 !important;
  ">
    <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
      <h3 style="margin: 0; font-size: 20px; color: #0f172a;">Novo Investimento em Capital de Giro</h3>
      <button class="modal-close" onclick="closeCapitalGiroModal()" style="background: none; border: none; font-size: 28px; color: #94a3b8; cursor: pointer;">&times;</button>
    </div>
    
    <div class="form-group" style="margin-bottom: 20px;">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #334155;">Tipo *</label>
      <select id="cg-tipo" required style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px;">
        <option value="">Selecione...</option>
        <option value="caixa">Caixa</option>
        <option value="recebiveis">Recebíveis</option>
        <option value="estoques">Estoques</option>
      </select>
    </div>
    
    <div class="form-group" style="margin-bottom: 20px;">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #334155;">Data do Aporte *</label>
      <input type="date" id="cg-data" required style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px;">
    </div>
    
    <div class="form-group" style="margin-bottom: 20px;">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #334155;">Valor (R$) *</label>
      <input type="number" id="cg-valor" step="0.01" min="0" required style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px;">
    </div>
    
    <div class="form-group" style="margin-bottom: 20px;">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #334155;">Descrição</label>
      <textarea id="cg-descricao" rows="3" style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; resize: vertical;"></textarea>
    </div>
    
    <div class="form-group" style="margin-bottom: 20px;">
      <label style="display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #334155;">Observações</label>
      <textarea id="cg-obs" rows="3" style="width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; resize: vertical;"></textarea>
    </div>
    
    <div class="modal-actions" style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px;">
      <button class="btn-modefin btn-secondary" onclick="closeCapitalGiroModal()" style="padding: 10px 16px; border-radius: 8px; border: none; font-size: 14px; cursor: pointer; background: rgba(255,255,255,0.2); color: #334155;">
        Cancelar
      </button>
      <button class="btn-modefin btn-primary" onclick="saveCapitalGiro()" style="padding: 10px 16px; border-radius: 8px; border: none; font-size: 14px; cursor: pointer; background: #3b82f6; color: white;">
        Salvar
      </button>
    </div>
  </div>
`;

// Forçar estilos do modal container
modal.style.display = 'flex';
modal.style.zIndex = '25000';
modal.style.alignItems = 'center';
modal.style.justifyContent = 'center';

console.log('✅ Modal HTML inserido com sucesso!');
console.log('Verifique se o card branco apareceu!');
```

---

## 📊 RESULTADO ESPERADO

Após executar:

✅ **Card branco aparece no centro**  
✅ **Formulário totalmente visível**  
✅ **Todos os campos editáveis**

---

**Execute AGORA e me diga se apareceu!**

