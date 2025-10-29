# 🚀 Como Acessar o Cadastro de Produtos

**Versão:** 1.0  
**Data:** 27/10/2025

---

## ⚡ Passo a Passo (SIMPLES)

### **1️⃣ Abra o Dashboard PEV**
```
http://localhost:5003/pev/dashboard
```

### **2️⃣ Escolha uma Empresa**
- Veja a lista de empresas cadastradas
- Clique na empresa que deseja trabalhar

### **3️⃣ Selecione um Planejamento**
- Veja os planejamentos da empresa
- Clique em **"Visualizar Implantação"**

### **4️⃣ Acesse Produtos no Menu Lateral**
- No menu lateral esquerdo
- Procure por **"📦 Cadastro de Produtos"**
- Clique!

---

## 🎯 Visual do Menu

```
┌─────────────────────────────┐
│  Fluxo da Implantação       │
├─────────────────────────────┤
│  📋 Dashboard               │
│  📊 Alinhamento Estratégico │
│  🏗️ Estruturas de Execução  │
│  📦 Cadastro de Produtos    │ ← CLIQUE AQUI!
│  💰 Modelagem Financeira    │
│  📄 Entrega do Relatório    │
└─────────────────────────────┘
```

---

## 🔗 Ou Use o Link Direto

Se você já sabe o `plan_id`:

```
http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=SEU_PLAN_ID
```

**Exemplos:**
```
http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=1
http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=8
http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=15
```

---

## ❓ Como Descobrir Meu plan_id?

### **Método 1: Olhe a URL**
Quando estiver em qualquer página do PEV, olhe o navegador:
```
http://localhost:5003/pev/implantacao?plan_id=8
                                              ↑
                                         Este é seu plan_id
```

### **Método 2: Dashboard**
No dashboard PEV, os planos mostram seus IDs

---

## 🛑 ERRO Comum: "plan_id é obrigatório"

**Causa:** Você tentou acessar sem o `plan_id`

**Solução:** Use SEMPRE um dos métodos acima:
- ✅ Via menu lateral (recomendado)
- ✅ Via URL com `?plan_id=X`

---

## ✅ Pronto!

Agora é só cadastrar seus produtos! 🎉

1. Clique em "➕ Novo Produto"
2. Preencha os campos
3. Observe os cálculos automáticos
4. Salve!

---

**Dúvidas?** Consulte:
- `CADASTRO_PRODUTOS_IMPLEMENTADO.md` - Guia completo
- `GUIA_RAPIDO_PRODUTOS.md` - Referência rápida

