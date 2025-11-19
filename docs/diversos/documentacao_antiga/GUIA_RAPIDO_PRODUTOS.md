# 🚀 Guia Rápido: Cadastro de Produtos

**Versão:** 1.0  
**Data:** 27/10/2025

---

## ⚡ Iniciar AGORA (3 Passos)

### **1️⃣ Aplicar Migration**
```bash
apply_products_migration.bat
```

### **2️⃣ Já está rodando!**
```bash
# Container já foi reiniciado ✅
docker ps | findstr app_dev
```

### **3️⃣ Acessar**
```
http://localhost:5003/pev/implantacao/modelo/produtos?plan_id=SEU_PLAN_ID
```

**Substitua `SEU_PLAN_ID` pelo ID do seu planejamento!**

---

## 📱 Exemplo de Uso Rápido

### **Cadastrar Café Premium**

1. **Clique** em "➕ Novo Produto"

2. **Preencha:**
   - **Nome:** `Café Expresso Premium`
   - **Preço:** `8.00`
   - **Custos %:** `35`
   - **Despesas %:** `15`
   - **Mercado:** `50000` unidades/mês
   - **Market Share:** `10%`

3. **Observe** os cálculos automáticos:
   - ✅ Custos R$: `2.80`
   - ✅ Despesas R$: `1.20`
   - ✅ **MCU: 50% (R$ 4,00)**
   - ✅ **Faturamento Mercado: R$ 400.000,00**

4. **Salve!** 💾

---

## 🎯 Campos Principais

| Campo | Descrição | Cálculo |
|-------|-----------|---------|
| **Preço Venda** | Valor unitário | Manual |
| **Custos %** | Percentual | → Converte para R$ |
| **Despesas %** | Percentual | → Converte para R$ |
| **MCU** | Margem Contribuição | ✅ Automático |
| **Faturamento Mercado** | Unidades × Preço | ✅ Automático |

---

## 🧮 Fórmulas Automáticas

```
MCU (R$) = Preço - Custos - Despesas
MCU (%)  = (MCU R$ / Preço) × 100
Faturamento = Unidades × Preço
```

---

## 🆘 Problemas Comuns

### **Erro: Tabela não existe**
```bash
apply_products_migration.bat
```

### **Erro: Página não carrega**
```bash
# Verificar se container está healthy
docker ps

# Reiniciar se necessário
docker-compose -f docker-compose.dev.yml restart app_dev
```

### **Dúvidas: Ver documentação completa**
```
CADASTRO_PRODUTOS_IMPLEMENTADO.md
```

---

**✅ PRONTO PARA USAR!**

Sistema 100% funcional - basta acessar e cadastrar seus produtos! 🎉

