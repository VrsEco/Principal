# 🧩 Catálogo de Componentes UI - GestaoVersus

**Versão:** 1.0 (Em construção)  
**Data:** 30/10/2025  
**Metodologia:** Incremental (adicionar conforme uso real)

---

## 🎯 COMO USAR ESTE CATÁLOGO

Este documento é um **catálogo vivo** de componentes UI aprovados e reutilizáveis.

### **Processo:**
1. Você encontra um padrão que gosta em alguma página
2. Me envia: URL + descrição ("Gostei dos botões de X")
3. Eu extraio, documento e adiciono aqui
4. Código fica disponível para reutilizar

---

## 📚 COMPONENTES DOCUMENTADOS

### **Status:**
- ✅ Documentado e aprovado
- 🔄 Em análise
- 📝 Pendente de documentação

---

## 1️⃣ MODAIS (✅ Documentado)

### **Modal Padrão - Sistema ModeFin**

**Referência:** `/pev/implantacao/modelo/modefin`  
**Status:** ✅ Aprovado e testado  
**Z-index:** 25000 (padrão do sistema)

**HTML:**
```html
<div id="meuModal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h3>Título do Modal</h3>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    
    <div class="form-group">
      <label>Campo</label>
      <input type="text" required>
    </div>
    
    <div class="modal-actions">
      <button class="btn-secondary" onclick="closeModal()">Cancelar</button>
      <button class="btn-primary" onclick="salvar()">Salvar</button>
    </div>
  </div>
</div>
```

**JavaScript (OBRIGATÓRIO):**
```javascript
function openModal() {
  const modal = document.getElementById('meuModal');
  modal.className = ''; // Remover classe
  
  // Forçar estilos
  modal.style.cssText = `
    display: flex !important;
    opacity: 1 !important;
    position: fixed !important;
    z-index: 25000 !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    background-color: rgba(0, 0, 0, 0.6) !important;
    align-items: center !important;
    justify-content: center !important;
  `;
  
  const content = modal.querySelector('.modal-content');
  if (content) {
    content.style.cssText = `
      background: white !important;
      color: #000000 !important;
      padding: 32px !important;
      border-radius: 16px !important;
      max-width: 600px !important;
      width: 90% !important;
    `;
  }
}

function closeModal() {
  const modal = document.getElementById('meuModal');
  modal.style.cssText = 'display: none !important;';
  modal.className = 'modal';
}

// Expor no window
window.openModal = openModal;
window.closeModal = closeModal;
```

**Documentação Completa:** `MODAL_STANDARDS.md`

---

## 2️⃣ BOTÕES (🔄 Adicionar Exemplos)

**Aguardando:** Você me enviar exemplo de botões que gostou

**Estrutura Preparada:**
```
- Botão Primário
- Botão Secundário
- Botão Ghost
- Botão de Ação (editar/deletar)
- Botão Flutuante (FAB)
```

---

## 3️⃣ CARDS (🔄 Adicionar Exemplos)

**Aguardando:** Você me enviar exemplo de cards que gostou

**Estrutura Preparada:**
```
- Card Padrão
- Card com Gradiente
- Card de Métrica
- Card Colapsável
```

---

## 4️⃣ TABELAS (🔄 Adicionar Exemplos)

**Aguardando:** Exemplo que você gostar

---

## 5️⃣ FORMULÁRIOS (🔄 Adicionar Exemplos)

**Aguardando:** Exemplo que você gostar

---

## 6️⃣ INFO BOXES (✅ Documentado Parcial)

**Referência:** ModeFin  
**Status:** ✅ Funcional

```html
<div class="info-box info">
  ℹ️ <strong>Informação:</strong> Texto explicativo.
</div>
```

**Variações:** info, success, warning, error

---

## 🎨 COMO ADICIONAR NOVO COMPONENTE

### **Template de Documentação:**

```markdown
## X️⃣ NOME DO COMPONENTE (Status)

**Referência:** URL da página  
**Usado em:** Lista de páginas  
**Status:** ✅ Aprovado  
**Data:** DD/MM/YYYY

**Descrição:**
Breve descrição do componente e quando usar.

**HTML:**
```html
<!-- Código HTML aqui -->
```

**CSS:**
```css
/* Estilos aqui */
```

**JavaScript (se necessário):**
```javascript
// Código JS aqui
```

**Screenshot:**
[Imagem ou descrição visual]

**Uso:**
- Quando usar
- Quando NÃO usar
- Variações disponíveis
```

---

## 📊 PROGRESSO

**Componentes Documentados:** 2/50+  
**Status:** Em construção incremental  
**Método:** Orgânico (conforme necessidade real)

---

## 🚀 PRÓXIMOS PASSOS

### **Você:**
1. Navegue pelo sistema
2. Quando ver algo que gosta, me envie:
   - URL da página
   - O que gostou (ex: "botões", "cards", "tabela")
   - (Opcional) Screenshot

### **Eu:**
1. Analiso o padrão
2. Extraio código
3. Documento aqui
4. Crio template reutilizável

### **Juntos:**
- Construímos catálogo completo
- Padronizamos o sistema
- Facilitamos desenvolvimento futuro

---

**Versão:** 1.0 (Estrutura Inicial)  
**Status:** 🔄 Em Construção Incremental  
**Última Atualização:** 30/10/2025

---

**ME ENVIE O PRIMEIRO EXEMPLO QUANDO QUISER!** 🎨

