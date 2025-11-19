# 📏 Sistema de Espaçamento dos Relatórios

**Data:** 13/10/2025  
**Arquivo:** `relatorios/generators/process_pop.py`  
**Status:** ✅ Implementado

---

## 🎯 Regras de Espaçamento

### **a) Margens, Cabeçalho e Rodapé**
✅ Conforme configuração da página (Model_7)

```css
@page {
    margin: 5mm 5mm 5mm 5mm;  /* Do modelo */
}
```

**Cabeçalho:** Vazio (retorna "")  
**Rodapé:** Vazio (retorna "")

---

### **b) Espaço entre Sessões**
✅ **5mm** entre cada sessão principal

**Sessões principais:**
1. Título do Book
2. Dados Gerais do Processo
3. Fluxo do Processo
4. Procedimento Operacional
5. Rotinas Associadas
6. Indicadores de Desempenho

```css
.book-title {
    margin: 0 0 5mm 0;  /* 5mm embaixo */
}

.process-info-section {
    margin: 0 0 5mm 0;  /* 5mm embaixo */
}

.report-section {
    margin: 0 0 5mm 0;  /* 5mm embaixo */
}
```

---

### **c) Espaço entre Subseções**
✅ **2.5mm** entre elementos dentro de uma sessão

**Exemplos de subseções:**
- Linhas de informações do processo
- Cards de atividades
- Cards de rotinas
- Passos de uma atividade
- Linhas de colaboradores

```css
.process-info-grid {
    gap: 2.5mm;  /* Entre linhas de info */
}

.activity-list {
    gap: 2.5mm;  /* Entre cards de atividades */
}

.routine-list {
    gap: 2.5mm;  /* Entre cards de rotinas */
}

.step-list {
    gap: 2.5mm;  /* Entre passos */
}

.activity-card h3 {
    margin-bottom: 2.5mm;  /* Título → Metadados */
}

.activity-description {
    margin-bottom: 2.5mm;  /* Descrição → Passos */
}
```

---

### **d) Título = Uma Sessão**
✅ O título do Book é considerado uma sessão completa

```html
<div class="book-title">
    <h1>Book do Processo: AB.C.1.1.1 Diagnostico...</h1>
</div>
<!-- 5mm de espaço aqui -->
```

---

### **e) Dados Gerais = Uma Sessão**
✅ Os dados gerais são considerados uma sessão completa

```html
<div class="process-info-section">
    <div class="process-info-grid">
        <div class="process-info-row">...</div>  <!-- Empresa -->
        <!-- 2.5mm -->
        <div class="process-info-row">...</div>  <!-- Processo -->
        <!-- 2.5mm -->
        <div class="process-info-row">...</div>  <!-- Macroprocesso -->
        <!-- 2.5mm -->
        <div class="process-info-row">...</div>  <!-- Nº Páginas -->
    </div>
</div>
<!-- 5mm de espaço aqui -->
```

---

### **f) Sem Cabeçalho = Sem Espaço Extra**
✅ Quando não há cabeçalho, não há offset adicional

**Antes (com cabeçalho):**
```
Margem da página: 5mm
+ Offset do cabeçalho: 25mm
+ Espaço extra: 3mm
= 33mm de espaço no topo
```

**Agora (sem cabeçalho):**
```
Margem da página: 5mm
= 5mm de espaço no topo ✅
```

---

## 📊 Estrutura de Espaçamento Visual

```
┌─────────────────────────────────── Página ────────────────────────────────┐
│ ↕ 5mm (margem da página)                                                  │
│ ┌─────────────────── Título do Book ────────────────────┐                 │
│ │ Book do Processo: AB.C.1.1.1 Diagnostico...           │                 │
│ └────────────────────────────────────────────────────────┘                 │
│ ↕ 5mm (espaço entre sessões)                                              │
│ ┌─────────────────── Dados Gerais ──────────────────────┐                 │
│ │ Empresa: [Nome]                                        │                 │
│ │ ↕ 2.5mm (espaço entre subseções)                      │                 │
│ │ Processo: [Nome] | Responsável: [Nome]                │                 │
│ │ ↕ 2.5mm                                                │                 │
│ │ Macroprocesso: [Nome] | Dono: [Nome]                  │                 │
│ │ ↕ 2.5mm                                                │                 │
│ │ Nº de Páginas: [Valor]                                │                 │
│ └────────────────────────────────────────────────────────┘                 │
│ ↕ 5mm (espaço entre sessões)                                              │
│ ┌─────────────────── Fluxo do Processo ─────────────────┐                 │
│ │ [Conteúdo da seção]                                    │                 │
│ └────────────────────────────────────────────────────────┘                 │
│ ↕ 5mm (espaço entre sessões)                                              │
│ ┌─────────────────── Procedimento Operacional ──────────┐                 │
│ │ Atividade 1                                            │                 │
│ │   ↕ 2.5mm                                              │                 │
│ │   Passo 1                                              │                 │
│ │   ↕ 2.5mm (espaço entre subseções)                    │                 │
│ │   Passo 2                                              │                 │
│ │ ↕ 2.5mm (espaço entre atividades)                     │                 │
│ │ Atividade 2                                            │                 │
│ └────────────────────────────────────────────────────────┘                 │
│ ↕ 5mm (espaço entre sessões)                                              │
│ ┌─────────────────── Rotinas Associadas ────────────────┐                 │
│ │ [Cards de rotinas com 2.5mm entre eles]               │                 │
│ └────────────────────────────────────────────────────────┘                 │
│ ↕ 5mm (margem inferior da página)                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 📐 Resumo dos Valores

| Elemento | Espaçamento |
|----------|-------------|
| **Margem da página** | 5mm (todas) |
| **Entre sessões** | 5mm |
| **Entre subseções** | 2.5mm |
| **Cabeçalho** | 0mm (vazio) |
| **Rodapé** | 0mm (vazio) |
| **Offset extra** | 0mm (removido) |

---

## 🎨 Paddings Reduzidos

Todos os paddings foram minimizados para não afetar o sistema de espaçamento:

| Elemento | Padding Antes | Padding Agora |
|----------|---------------|---------------|
| Book title | 32px | 12px |
| Process info | 24px | 12px |
| Report section | 18px-22px | 12px-16px |
| Activity card | 16px-18px | 12px-16px |
| Routine card | 16px-18px | 12px-16px |
| Info callout | 12px-14px | 10px-12px |
| Steps | 10px-12px | 8px-10px |

---

## ✅ Resultado Esperado

### **Primeira Página:**
```
Margem da página: 5mm
Título do Book (altura ~15mm)
Espaço entre sessões: 5mm
Dados do Processo (altura ~25mm)
Espaço entre sessões: 5mm
Primeira seção...
```

**Total no topo até o conteúdo:** ≈5mm + 15mm + 5mm + 25mm = **50mm**

### **Demais Páginas:**
```
Margem da página: 5mm
Continuação da seção ou nova seção...
```

**Total no topo:** **5mm**

---

## 🧪 Como Testar

1. **Abra o relatório:**
   ```
   C:\GestaoVersus\teste_relatorio_novo.html
   ```

2. **Abra a pré-visualização de impressão:**
   ```
   Ctrl + P
   ```

3. **Meça os espaços:**
   - Entre o topo da página e o título: **5mm**
   - Entre título e dados: **5mm**
   - Entre dados e primeira seção: **5mm**
   - Entre linhas de dados: **2.5mm**
   - Entre atividades: **2.5mm**
   - Entre passos: **2.5mm**

---

## 💡 Observação

A primeira página naturalmente terá mais conteúdo no topo porque contém:
- Título do Book (≈15mm)
- Dados do Processo (≈25mm)
- 2 espaços de 5mm

Mas agora **todas as páginas respeitam o sistema de 5mm + 2.5mm de forma consistente!**

---

## 📋 Checklist de Implementação

- [x] Margens da página: 5mm (do modelo)
- [x] Cabeçalho: removido (retorna vazio)
- [x] Rodapé: removido (retorna vazio)
- [x] Offset extra: removido (0mm)
- [x] Espaço entre sessões: 5mm
- [x] Espaço entre subseções: 2.5mm
- [x] Título = sessão
- [x] Dados gerais = sessão
- [x] Paddings reduzidos
- [x] Sistema consistente
- [x] Testado e funcionando

---

**Status:** ✅ Sistema de espaçamento uniforme implementado!  
**Arquivo:** `relatorios/generators/process_pop.py`  
**Teste:** `C:\GestaoVersus\teste_relatorio_novo.html` (aberto no navegador)


