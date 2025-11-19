# GUIA DE APLICAÇÃO - PADRÃO "FUNDO CLARO"

## 🚀 **APLICAÇÃO RÁPIDA**

### **Comando para o Assistente:**
```
"Aplique o padrão 'Fundo Claro' nesta página: [URL ou nome da página]"
```

### **O que o padrão faz:**
- ✅ Converte fundos escuros em fundos claros
- ✅ Converte fontes claras em fontes escuras
- ✅ Garante contraste mínimo de 4.5:1
- ✅ Aplica bordas e sombras consistentes
- ✅ Adiciona efeitos hover e transições

## 📋 **CHECKLIST DE APLICAÇÃO**

### **1. Fundos**
- [ ] `background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;`
- [ ] Cards: `background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%) !important;`
- [ ] Hover: `background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;`

### **2. Fontes**
- [ ] Títulos: `color: #000000 !important;`
- [ ] Texto: `color: #1e293b !important;`
- [ ] Muted: `color: #475569 !important;`
- [ ] Destaque: `color: #1e40af !important;`

### **3. Bordas e Sombras**
- [ ] Bordas: `border: 1px solid rgba(30, 64, 175, 0.1) !important;`
- [ ] Hover: `border: 1px solid rgba(30, 64, 175, 0.2) !important;`
- [ ] Sombras: `box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;`
- [ ] Hover: `box-shadow: 0 8px 24px rgba(30, 64, 175, 0.12) !important;`

### **4. Interações**
- [ ] Transições: `transition: all 0.3s ease !important;`
- [ ] Hover: `transform: translateY(-2px) !important;`
- [ ] Focus: `box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1) !important;`

## 🎯 **ELEMENTOS ESPECÍFICOS**

### **Cards e Superfícies**
```css
.elemento {
  background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%) !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
  transition: all 0.3s ease !important;
}
```

### **Botões**
```css
.botao {
  background: linear-gradient(135deg, #1e40af, #7c3aed, #dc2626) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 8px 16px !important;
  font-weight: 600 !important;
  transition: all 0.3s ease !important;
}
```

### **Inputs**
```css
.input {
  background: #ffffff !important;
  color: #000000 !important;
  border: 1px solid rgba(148, 163, 184, 0.3) !important;
  border-radius: 8px !important;
  padding: 10px 12px !important;
}
```

### **Modais**
```css
.modal {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  box-shadow: 0 16px 48px rgba(30, 64, 175, 0.15) !important;
  border-radius: 16px !important;
}
```

## 📱 **RESPONSIVIDADE**
```css
@media (max-width: 768px) {
  .elemento {
    margin: 8px !important;
    padding: 16px !important;
  }
}
```

## ⚡ **APLICAÇÃO AUTOMÁTICA**

### **CSS Global Incluído:**
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/grv-global-pattern.css') }}" />
```

### **Classes Utilitárias:**
- `.fundo-claro` - Fundo principal
- `.fundo-card` - Fundo de cards
- `.texto-principal` - Texto preto
- `.texto-secundario` - Texto azul escuro
- `.borda-padrao` - Borda azul sutil
- `.sombra-padrao` - Sombra azul sutil

## 🎨 **IDENTIFICAÇÃO VISUAL**

### **Barras Coloridas (apenas para identificação):**
```css
.elemento::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #1e40af, #7c3aed, #dc2626);
}
```

## ✅ **VALIDAÇÃO**

### **Antes da Aplicação:**
- [ ] Página tem fundos escuros?
- [ ] Página tem fontes claras?
- [ ] Contraste é insuficiente?

### **Após a Aplicação:**
- [ ] Todos os fundos são claros?
- [ ] Todas as fontes são escuras?
- [ ] Contraste é adequado (4.5:1+)?
- [ ] Hover effects funcionam?
- [ ] Responsividade mantida?

## 📝 **EXEMPLO DE APLICAÇÃO**

### **Antes:**
```css
.elemento {
  background: #1e293b;
  color: #ffffff;
  border: 1px solid #000000;
}
```

### **Depois:**
```css
.elemento {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%) !important;
  color: #000000 !important;
  border: 1px solid rgba(30, 64, 175, 0.1) !important;
  box-shadow: 0 4px 12px rgba(30, 64, 175, 0.08) !important;
  transition: all 0.3s ease !important;
}
```

---
**Nota**: Este padrão garante consistência visual e máxima legibilidade em todas as páginas do sistema GRV.
