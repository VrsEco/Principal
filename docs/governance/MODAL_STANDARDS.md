# 📐 Padrão de Modais - GestaoVersus

## 🎯 OBJETIVO

Estabelecer um padrão **único e definitivo** para modais em todo o projeto, eliminando problemas de z-index e inconsistências.

---

## 🚫 PROBLEMA HISTÓRICO

**Sintoma:** Modais não aparecem ou ficam escondidos atrás de outros elementos.

**Causa:** 
- Z-index inconsistente (999, 9999, 99999, 999999)
- Cada desenvolvedor/IA adiciona mais 9s sem padrão
- Conflito com Global Activity Button e outros elementos
- CSS sendo sobrescrito

**Impacto:**
- Horas perdidas debugando
- Frustração do time
- Código duplicado e inconsistente

---

## ✅ SOLUÇÃO ESTRUTURAL

### **Sistema Centralizado de Modais**

Todos os modais do projeto DEVEM usar o sistema centralizado em:
- `static/js/modal-system.js`
- `static/css/modal-system.css`

---

## 📊 HIERARQUIA DE Z-INDEX DO PROJETO

**PADRÃO OBRIGATÓRIO:**

```
1-99         → Conteúdo normal
100-999      → Dropdowns, tooltips
1.000-9.999  → Sidebars, overlays
10.000-19.999 → Botões flutuantes (Global Activity Button)
20.000-29.999 → Modais do sistema (USAR ESTE!)
30.000-39.999 → Modais críticos/alerts
40.000+      → Debug/desenvolvimento
```

### **Valores Específicos:**

| Elemento | Z-Index | Arquivo |
|----------|---------|---------|
| Conteúdo da página | 1-99 | - |
| Dropdown de menu | 100 | base.html |
| Sidebar | 1000 | base.html |
| Global Activity Button | 10000 | components/global_activity_button.html |
| **Modais padrão** | **25000** | **modal-system.js** |
| Alerts/confirmações | 30000 | modal-system.js (opção) |

---

## 🔧 COMO USAR

### **Opção 1: Sistema JavaScript (RECOMENDADO)**

#### 1. Incluir arquivos no template:

```html
<!-- No <head> ou antes de </body> -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/modal-system.css') }}">
<script src="{{ url_for('static', filename='js/modal-system.js') }}"></script>
```

#### 2. Criar HTML do modal:

```html
<div id="meuModal" class="modal-system">
  <div class="modal-content-system">
    <button class="modal-close-system" data-modal-close>&times;</button>
    <div class="modal-body-system">
      <h2>Título do Modal</h2>
      <p>Conteúdo aqui</p>
      <button onclick="modal.close()">Fechar</button>
    </div>
  </div>
</div>
```

#### 3. Inicializar e usar no JavaScript:

```javascript
// Inicializar
const modal = new Modal('meuModal');

// Abrir
function abrirModal() {
  modal.open();
}

// Fechar
function fecharModal() {
  modal.close();
}

// Ou via onclick
<button onclick="modal.open()">Abrir Modal</button>
```

#### 4. Opções avançadas:

```javascript
const modal = new Modal('meuModal', {
  zIndex: 25000,           // Padrão: 25000
  backdrop: true,          // Padrão: true (fundo escuro)
  closeOnBackdrop: true,   // Padrão: true (clicar fora fecha)
  closeOnEscape: true,     // Padrão: true (ESC fecha)
  animation: true          // Padrão: true (com animação)
});
```

---

### **Opção 2: Helper Rápido**

Para modais simples e rápidos:

```javascript
// Criar e abrir em uma linha
const modal = createModal('alertaModal', `
  <h2>Atenção!</h2>
  <p>Esta ação não pode ser desfeita.</p>
  <button onclick="modal.close()">OK</button>
`);
modal.open();
```

---

## ⚠️ REGRAS OBRIGATÓRIAS

### ✅ FAZER

1. **SEMPRE usar `modal-system.js`** para novos modais
2. **SEMPRE usar z-index 25000** (padrão do sistema)
3. **NUNCA adicionar `!important`** no z-index
4. **SEMPRE usar classe `modal-system`** no container
5. **SEMPRE incluir botão de fechar** com `data-modal-close`

### ❌ NÃO FAZER

1. **NUNCA inventar z-index aleatório** (999, 9999, 999999, etc)
2. **NUNCA usar CSS inline** para z-index (sistema JS cuida)
3. **NUNCA criar sistema de modal próprio**
4. **NUNCA usar `position: absolute`** (usar `fixed`)
5. **NUNCA esquecer de incluir os arquivos** CSS e JS

---

## 🔄 MIGRAÇÃO DE MODAIS EXISTENTES

### Antes (ERRADO):

```html
<div class="modal" id="meuModal" style="z-index: 999999 !important">
  <div class="modal-content">
    <h2>Título</h2>
    <button onclick="closeModal()">X</button>
  </div>
</div>

<script>
function openModal() {
  document.getElementById('meuModal').style.display = 'block';
}
function closeModal() {
  document.getElementById('meuModal').style.display = 'none';
}
</script>
```

### Depois (CORRETO):

```html
<div id="meuModal" class="modal-system">
  <div class="modal-content-system">
    <button class="modal-close-system" data-modal-close>&times;</button>
    <div class="modal-body-system">
      <h2>Título</h2>
    </div>
  </div>
</div>

<script>
const modal = new Modal('meuModal');
window.openModal = () => modal.open();
</script>
```

---

## 📋 CHECKLIST DE VALIDAÇÃO

Antes de fazer commit de código com modal:

- [ ] Arquivos `modal-system.js` e `modal-system.css` incluídos no template
- [ ] Modal usa classe `modal-system`
- [ ] Modal inicializado com `new Modal(id)`
- [ ] Não há z-index customizado no CSS
- [ ] Não há `!important` em estilos do modal
- [ ] Botão de fechar tem `data-modal-close`
- [ ] Testado: modal aparece acima de tudo
- [ ] Testado: clicar fora fecha
- [ ] Testado: ESC fecha
- [ ] Testado: não há scroll na página quando modal aberto

---

## 🐛 TROUBLESHOOTING

### Modal não aparece

**Debug:**
```javascript
// No console
const modal = new Modal('meuModal');
console.log('Modal element:', modal.modalElement);
console.log('Modal z-index:', window.getComputedStyle(modal.modalElement).zIndex);
modal.open();
```

**Soluções:**
1. Verificar se arquivos JS/CSS estão incluídos
2. Verificar se ID do modal está correto
3. Verificar console para erros
4. Verificar se elemento existe no DOM

### Modal aparece mas está atrás de outros elementos

**Causa:** Outro elemento com z-index >= 25000

**Solução:**
```javascript
// Aumentar z-index específico deste modal
const modal = new Modal('meuModal', { zIndex: 30000 });
```

Ou ajustar z-index do elemento que está na frente.

### ESC ou clicar fora não fecha

**Causa:** Opções desabilitadas

**Solução:**
```javascript
const modal = new Modal('meuModal', {
  closeOnBackdrop: true,  // Habilitar
  closeOnEscape: true     // Habilitar
});
```

---

## 📚 EXEMPLOS COMPLETOS

### Exemplo 1: Modal de Confirmação

```html
<div id="confirmModal" class="modal-system">
  <div class="modal-content-system">
    <button class="modal-close-system" data-modal-close>&times;</button>
    <div class="modal-body-system">
      <h2>Confirmar Exclusão</h2>
      <p>Tem certeza que deseja deletar este item?</p>
      <div style="display: flex; gap: 12px; margin-top: 24px;">
        <button onclick="confirmModal.close()">Cancelar</button>
        <button onclick="deleteItem()" style="background: #ef4444; color: white;">Deletar</button>
      </div>
    </div>
  </div>
</div>

<script>
const confirmModal = new Modal('confirmModal');
window.showDeleteConfirm = () => confirmModal.open();
</script>
```

### Exemplo 2: Modal de Formulário

```html
<div id="formModal" class="modal-system">
  <div class="modal-content-system">
    <button class="modal-close-system" data-modal-close>&times;</button>
    <div class="modal-body-system">
      <h2>Novo Cadastro</h2>
      <form onsubmit="handleSubmit(event)">
        <input type="text" name="nome" placeholder="Nome" required>
        <input type="email" name="email" placeholder="Email" required>
        <button type="submit">Salvar</button>
      </form>
    </div>
  </div>
</div>

<script>
const formModal = new Modal('formModal');

function handleSubmit(e) {
  e.preventDefault();
  // Processar formulário
  formModal.close();
}
</script>
```

---

## 🎯 RESULTADO ESPERADO

Após implementar este padrão:

✅ **Modais SEMPRE aparecem** acima de tudo  
✅ **Z-index consistente** em todo projeto  
✅ **Código reutilizável** e manutenível  
✅ **Sem debugging** de z-index  
✅ **Animações suaves** e profissionais  
✅ **Acessibilidade** (ESC para fechar)  
✅ **Responsivo** automaticamente  

---

**Versão:** 1.0  
**Data:** 29/10/2025  
**Autor:** Sistema GestaoVersus  
**Status:** ✅ OBRIGATÓRIO para todos os modais novos

