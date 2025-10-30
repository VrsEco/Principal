# 🎨 Padrões Frontend - GestaoVersus

## 🎯 OBJETIVO

Estabelecer padrões para desenvolvimento frontend que garantam consistência, manutenibilidade e previnem problemas comuns.

---

## 📐 PADRÃO DE MODAIS (CRÍTICO)

### **Problema Histórico**

Modais não apareciam ou ficavam escondidos atrás de outros elementos devido a:
- Z-index inconsistente
- CSS sobrescrevendo estilos inline
- Classes CSS com `display: none` e `opacity: 0`

### **Solução Estrutural**

**TODOS os modais DEVEM:**

1. ✅ **Usar z-index: 25000** (padrão do sistema)
2. ✅ **Remover classes CSS ao abrir** (evitar conflitos)
3. ✅ **Forçar estilos via JavaScript** com `cssText`
4. ✅ **Usar `!important` quando necessário**

### **Template Padrão de Modal**

```html
<!-- HTML do Modal -->
<div id="meuModal" class="modal">
  <div class="modal-content">
    <!-- Conteúdo aqui -->
  </div>
</div>

<style>
  /* NÃO USAR display: none ou opacity: 0 em .modal! */
  .modal {
    position: fixed;
    z-index: 25000;
    /* Outros estilos OK */
  }
  
  .modal-content {
    background: white;
    /* Estilos do card */
  }
</style>

<script>
  function abrirModal() {
    const modal = document.getElementById('meuModal');
    
    // IMPORTANTE: Remover classe para evitar conflitos
    modal.className = '';
    
    // Forçar estilos via cssText
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
    
    // Forçar estilos do conteúdo
    const content = modal.querySelector('.modal-content');
    if (content) {
      content.style.cssText = `
        background: white !important;
        color: #000000 !important;
        padding: 32px !important;
        border-radius: 16px !important;
        max-width: 600px !important;
        width: 90% !important;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3) !important;
      `;
    }
  }
  
  function fecharModal() {
    const modal = document.getElementById('meuModal');
    modal.style.cssText = 'display: none !important;';
    modal.className = 'modal'; // Restaurar classe
  }
  
  // Expor no window para onclick
  window.abrirModal = abrirModal;
  window.fecharModal = fecharModal;
</script>
```

### **Sistema Centralizado (Opção Avançada)**

Para novos modais, considere usar o sistema centralizado:
- `static/js/modal-system.js`
- `static/css/modal-system.css`

Veja `docs/governance/MODAL_STANDARDS.md` para detalhes.

---

## 📊 HIERARQUIA DE Z-INDEX

**PADRÃO OBRIGATÓRIO DO PROJETO:**

| Camada | Z-Index | Elementos |
|--------|---------|-----------|
| Conteúdo | 1-99 | Páginas, cards, tabelas |
| Dropdowns | 100-999 | Menus suspensos, tooltips |
| Overlays | 1.000-9.999 | Sidebars, painéis laterais |
| Botões Flutuantes | 10.000-19.999 | Global Activity Button |
| **Modais** | **20.000-29.999** | **USAR 25.000** |
| Alerts Críticos | 30.000-39.999 | Confirmações, avisos |
| Debug | 40.000+ | Ferramentas de desenvolvimento |

### **Regras:**

✅ **SEMPRE usar 25.000 para modais**  
❌ **NUNCA inventar z-index** (999, 9999, 999999, etc)  
❌ **NUNCA usar z-index > 30.000** (exceto debug)  
✅ **DOCUMENTAR** se precisar valor diferente  

---

## 🧩 PADRÃO VISUAL DE PÁGINAS (ModeFin e Main)

### Cores e contraste
- Fundo da página: branco ou gradiente cinza claro (ex.: `linear-gradient(135deg, #ffffff, #f7f7f9, #f1f2f4)`).
- Tipografia: fontes escuras (preto, azul-escuro). Evitar cores fortes em grandes áreas.
- Cartões/seções: borda 1px `#e5e7eb` e sombra suave.

### Layout
- Container de conteúdo padrão: largura máxima 1120px.
- Quando não houver sidebar, alinhar o conteúdo à esquerda.
- Rolagem horizontal deve ocorrer dentro dos blocos com tabelas/planilhas, nunca na página.

### Botões
- Fundo branco, texto escuro, borda `#cbd5e1`.
- Acentos laterais sutis (“furta-cor”) via pseudo-elementos.
- Variações `primary`/`secondary` mudam apenas borda/hover, não o preenchimento com cores fortes.

### Cards de valores (KPIs)
- Usar gradiente cinza claro no fundo do item e borda 1px `#e5e7eb`.
- Estado destacado: gradiente sutil com leve ênfase (não usar cores saturadas de fundo).

### Tabelas
- Borda externa 1px `#e5e7eb` e linhas de grade verticais/horizontais.
- Cabeçalhos (títulos): fundo cinza mais escuro `#e5e7eb`.
- Subtítulos/linhas de seção: cinza intermediário `#f1f5f9`.
- Linhas de dados em zebra: ímpares branco `#ffffff`, pares cinza claro `#f8fafc`.
- Overflow-x: auto no container da tabela para evitar scroll na página.

### Acessibilidade
- Manter contraste AA em textos e ícones.
- Evitar transmitir informação apenas por cor.

### Anti‑padrões (não fazer)
- Gradientes fortes em cards de conteúdo.
- Cores saturadas como fundo de seção/tabela.
- Scroll horizontal na página inteira.


## 🎨 PADRÕES DE CSS

### **1. CSS Inline vs Classes**

**Quando usar CSS inline:**
- Estilos dinâmicos (cores calculadas, etc)
- Sobrescrever CSS de classes
- Garantir precedência

**Quando usar classes CSS:**
- Estilos reutilizáveis
- Temas e variações
- Manutenção facilitada

### **2. !important**

**USAR quando:**
- Forçar visibilidade de modais
- Sobrescrever CSS de bibliotecas
- Correção de conflitos críticos

**NÃO USAR quando:**
- Estilos normais de página
- Pode usar especificidade CSS
- Apenas por preguiça

### **3. Formatação de Valores**

**Moeda:**
```javascript
function formatCurrency(value) {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL'
  }).format(value);
}
```

**Percentuais:**
```javascript
function formatPercent(value) {
  return `${parseFloat(value).toFixed(1)}%`;
}
```

**Datas:**
```javascript
function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString('pt-BR');
}
```

---

## 🚀 JAVASCRIPT

### **1. Eventos onclick**

**Funções DEVEM estar no window:**
```javascript
function minhaFuncao() { ... }

// Expor no window
window.minhaFuncao = minhaFuncao;
```

Depois pode usar:
```html
<button onclick="minhaFuncao()">Clique</button>
```

### **2. APIs**

**Helper padrão:**
```javascript
async function apiCall(url, method = 'GET', data = null) {
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    
    if (data && method !== 'GET') {
      options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    const result = await response.json();
    
    if (!result.success) {
      throw new Error(result.error || 'Erro na requisição');
    }
    
    return result;
  } catch (error) {
    console.error('[API Error]', error);
    alert('Erro: ' + error.message);
    throw error;
  }
}
```

### **3. Debug**

**Logs devem:**
- ✅ Usar tags: `[Modal]`, `[API]`, `[Component]`
- ✅ Ser informativos
- ❌ **NUNCA** ter emojis (causam encoding issues)

**Exemplo:**
```javascript
console.log('[Modal] Abrindo modal...');
console.log('[API] Salvando dados:', data);
```

---

## 📋 CHECKLIST DE CODE REVIEW

Antes de fazer commit de código frontend:

### Modais:
- [ ] Z-index é 25000
- [ ] Classe removida ao abrir (`modal.className = ''`)
- [ ] Estilos forçados com `cssText`
- [ ] Conteúdo com background branco forçado
- [ ] Funções expostas no `window`
- [ ] Testado: modal aparece acima de tudo

### JavaScript:
- [ ] Funções onclick estão no window
- [ ] APIs usam helper padrão
- [ ] Tratamento de erros com try/catch
- [ ] Logs com tags informativas
- [ ] Sem emojis em console.log

### CSS:
- [ ] Z-index seguindo hierarquia
- [ ] !important apenas quando necessário
- [ ] Comentários explicativos

### Formatação:
- [ ] Moedas formatadas com Intl.NumberFormat
- [ ] Datas formatadas com toLocaleDateString
- [ ] Números com precisão adequada

---

## 🐛 TROUBLESHOOTING COMUM

### Modal não aparece

**Debug:**
```javascript
const modal = document.getElementById('meuModal');
console.log('Display:', window.getComputedStyle(modal).display);
console.log('Opacity:', window.getComputedStyle(modal).opacity);
console.log('Z-index:', window.getComputedStyle(modal).zIndex);
```

**Soluções:**
1. Verificar se classe CSS tem `display: none`
2. Remover classe ao abrir
3. Usar `cssText` com `!important`
4. Verificar z-index de outros elementos

### Função onclick não funciona

**Causa:** Função não está no `window`

**Solução:**
```javascript
window.minhaFuncao = minhaFuncao;
```

### CSS não aplica

**Causa:** Especificidade ou cache

**Solução:**
1. Usar `!important`
2. Force reload: `Ctrl + F5`
3. Limpar cache do navegador

---

## ✅ RESULTADO ESPERADO

Seguindo estes padrões:

✅ **Modais SEMPRE aparecem**  
✅ **CSS consistente**  
✅ **JavaScript robusto**  
✅ **Sem debugging desnecessário**  
✅ **Código manutenível**  
✅ **Experiência do usuário profissional**  

---

**Versão:** 1.0  
**Data:** 29/10/2025  
**Status:** ✅ OBRIGATÓRIO para todo código frontend  
**Relacionado:** `MODAL_STANDARDS.md`, `CODING_STANDARDS.md`

