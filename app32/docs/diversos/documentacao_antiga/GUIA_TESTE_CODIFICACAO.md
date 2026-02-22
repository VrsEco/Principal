# 🧪 Guia de Teste - Sistema de Codificação Automática

## 🎯 Como Funciona

O sistema gera códigos **automaticamente** no formato:
```
{CÓDIGO_CLIENTE}.{TIPO}.{ÁREA}.{MACRO}.{PROCESSO}
```

Exemplo completo: **`AO.C.1.2.11`**

---

## 📋 Passo a Passo para Testar

### **PASSO 1: Configurar Código do Cliente** 🔖

1. Acesse: `http://localhost:5000`
2. Entre em uma empresa qualquer
3. Clique em **"Macroprocessos"** no menu GRV
4. No Dashboard, procure a seção **"⚙️ Configurações da Empresa"**
5. No campo **"Código do Cliente"**, digite: **`AO`** (ou AB, AC, FF, etc.)
6. Clique em **"💾 Salvar Configurações"**

**Resultado:** O código do cliente está configurado! ✅

---

### **PASSO 2: Criar uma Área** 📁

1. Vá para **"Mapa de Processos"** (menu lateral)
2. Clique na aba **"Áreas de Gestão"**
3. Preencha:
   - **Nome da Área:** `Finalísticos`
   - **Cor:** Escolha uma cor (opcional)
   - **Ordem:** Deixe `0` ou coloque `1`
4. Clique em **"Salvar Área"**

**Código Gerado:** `AO.C.1` ✨

**Explicação:**
- `AO` = Código do cliente
- `C` = Processos (C) ou Projetos (J)
- `1` = Número da área (baseado em order_index)

---

### **PASSO 3: Criar um Macroprocesso** 🏗️

1. Ainda no Mapa de Processos, clique na aba **"Macroprocessos"**
2. Ou vá direto para a página **"Macroprocessos"** no menu
3. Clique em **"➕ Novo Macroprocesso"**
4. Preencha:
   - **Área de Gestão:** Selecione `Finalísticos`
   - **Sequência/Ordem:** `1`
   - **Nome:** `Gerir Pessoas`
   - **Dono do Processo:** `João Silva` ⭐
   - **Descrição:** (opcional)
5. Clique em **"Salvar Macroprocesso"**

**Código Gerado:** `AO.C.1.1` ✨

**Explicação:**
- `AO.C.1` = Código da área
- `.1` = Sequência do macroprocesso (que você definiu)

---

### **PASSO 4: Criar um Processo** ⚙️

1. No Mapa de Processos, clique na aba **"Processos"**
2. Preencha:
   - **Macroprocesso:** Selecione `AO.C.1.1 Gerir Pessoas`
   - **Nome do Processo:** `Gerir SST`
   - **Sequência/Ordem:** `6`
   - **Nível Estruturação:** (opcional)
   - **Nível Desempenho:** (opcional)
   - **Responsável:** (opcional)
3. Clique em **"Salvar Processo"**

**Código Gerado:** `AO.C.1.1.6` ✨

**Explicação:**
- `AO.C.1.1` = Código do macroprocesso
- `.6` = Sequência do processo (que você definiu)

---

## 🎨 Visualização no Mapa

Após criar tudo, vá para a aba **"Visualizar Mapa"**:

```
┌─────────────────────────────────────────────────────┐
│                    Mapa de Processos                │
├─────────────────────────────────────────────────────┤
│ FINALÍSTICOS                                        │
│ ┌──────────────────────────────────────────────┐   │
│ │ AO.C.1.1 - Gerir Pessoas                     │   │
│ │ Dono: João Silva                              │   │
│ │                                               │   │
│ │ ┌──────────────────────────────────────────┐ │   │
│ │ │ AO.C.1.1.6 - Gerir SST                   │ │   │
│ │ │ ⬤ Est: N/A  |  ⬤ Desemp: N/A             │ │   │
│ │ └──────────────────────────────────────────┘ │   │
│ └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Os códigos estão automaticamente ordenados!** 🎉

---

## 🔄 Testando Múltiplos Elementos

### Teste Completo:

**1. Crie mais áreas:**
- Área 2: `Apoio` → Código: `AO.C.2`
- Área 3: `Gerenciais` → Código: `AO.C.3`

**2. Crie mais macros na Área 1:**
- Macro 2: `Gerir Vendas` → Código: `AO.C.1.2`
- Macro 3: `Gerir Marketing` → Código: `AO.C.1.3`

**3. Crie mais processos no Macro 1:**
- Processo 7: `Gerir Treinamentos` → Código: `AO.C.1.1.7`
- Processo 8: `Gerir Benefícios` → Código: `AO.C.1.1.8`

**4. Crie processos no Macro 2:**
- Processo 1: `Prospectar Clientes` → Código: `AO.C.1.2.1`
- Processo 2: `Fechar Vendas` → Código: `AO.C.1.2.2`

---

## 📊 Resultado Esperado

### Estrutura Hierárquica:

```
Empresa (Código: AO)
│
├─ Área 1: Finalísticos (AO.C.1)
│  ├─ Macro 1: Gerir Pessoas (AO.C.1.1)
│  │  ├─ Processo 6: Gerir SST (AO.C.1.1.6)
│  │  ├─ Processo 7: Gerir Treinamentos (AO.C.1.1.7)
│  │  └─ Processo 8: Gerir Benefícios (AO.C.1.1.8)
│  │
│  ├─ Macro 2: Gerir Vendas (AO.C.1.2)
│  │  ├─ Processo 1: Prospectar Clientes (AO.C.1.2.1)
│  │  └─ Processo 2: Fechar Vendas (AO.C.1.2.2)
│  │
│  └─ Macro 3: Gerir Marketing (AO.C.1.3)
│
├─ Área 2: Apoio (AO.C.2)
│
└─ Área 3: Gerenciais (AO.C.3)
```

### Ordenação Automática:

Os elementos serão listados sempre nesta ordem:
1. `AO.C.1` (Área 1)
2. `AO.C.1.1` (Macro 1.1)
3. `AO.C.1.1.6` (Processo 1.1.6)
4. `AO.C.1.1.7` (Processo 1.1.7)
5. `AO.C.1.1.8` (Processo 1.1.8)
6. `AO.C.1.2` (Macro 1.2)
7. `AO.C.1.2.1` (Processo 1.2.1)
8. `AO.C.1.2.2` (Processo 1.2.2)
9. `AO.C.1.3` (Macro 1.3)
10. `AO.C.2` (Área 2)
11. `AO.C.3` (Área 3)

---

## ✅ Verificações

### 1. **Código do Cliente Funciona?**
- [ ] Consegui configurar o código (ex: AO)
- [ ] Código aparece nas áreas criadas

### 2. **Geração Automática?**
- [ ] NÃO precisei digitar o código da área
- [ ] NÃO precisei digitar o código do macro
- [ ] NÃO precisei digitar o código do processo

### 3. **Códigos Corretos?**
- [ ] Área tem formato: `AO.C.1`
- [ ] Macro tem formato: `AO.C.1.2`
- [ ] Processo tem formato: `AO.C.1.2.11`

### 4. **Ordenação Funciona?**
- [ ] Elementos aparecem ordenados por código
- [ ] Hierarquia está correta

### 5. **Sequências Flexíveis?**
- [ ] Posso usar sequência 1, 2, 3...
- [ ] Posso pular números (1, 2, 5, 10...)
- [ ] Posso reorganizar depois

---

## 🐛 Troubleshooting

### Problema: "Código não aparece"
**Solução:** 
1. Verifique se configurou o código do cliente
2. Recarregue a página
3. Verifique no banco de dados

### Problema: "Código duplicado"
**Solução:**
- Use sequências diferentes
- Verifique o order_index

### Problema: "Não consigo ver o código"
**Solução:**
- O código é gerado automaticamente após salvar
- Recarregue a lista/mapa
- Verifique a aba "Visualizar Mapa"

---

## 🎯 URLs de Teste

- **Dashboard:** `http://localhost:5000`
- **Empresas:** `http://localhost:5000/companies`
- **GRV Dashboard:** `http://localhost:5000/grv/company/1`
- **Macroprocessos:** `http://localhost:5000/grv/company/1/process/macro`
- **Mapa de Processos:** `http://localhost:5000/grv/company/1/process/map`

---

## 💡 Dicas

1. **Comece sempre** configurando o código do cliente
2. **Use sequências lógicas** (1, 2, 3...) para facilitar
3. **Deixe gaps** se quiser adicionar itens no meio depois
4. **Visualize no mapa** para ver a hierarquia completa
5. **Códigos são permanentes** - não precisa redigitar

---

## 🎉 Sucesso!

Se você conseguiu criar:
- ✅ Uma área com código automático
- ✅ Um macroprocesso com código automático
- ✅ Um processo com código completo
- ✅ Tudo ordenado corretamente

**O sistema está funcionando perfeitamente!** 🚀

---

**Servidor:** `http://localhost:5000`  
**Data:** Outubro 2025  
**Versão:** app25 com Sistema de Codificação Automática
