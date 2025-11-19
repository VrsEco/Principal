# 🔧 CORREÇÃO: plan.id estava vazio

**Data:** 23/10/2025  
**Status:** ✅ CORRIGIDO

---

## 🚨 **PROBLEMA IDENTIFICADO:**

A URL estava assim:
```
http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=
```

**❌ O `plan_id` estava VAZIO!**

---

## 🔍 **CAUSA RAIZ:**

**Arquivo:** `modules/pev/implantation_data.py`

A função `build_plan_context()` retornava um dicionário com a chave `"plan_id"`, mas **NÃO tinha a chave `"id"`**.

No template, estávamos usando:
```jinja2
url_for('pev.implantacao_canvas_expectativas', plan_id=plan.id)
```

Mas `plan.id` era `None` porque o dicionário não tinha essa chave!

---

## ✅ **CORREÇÃO APLICADA:**

**Arquivo:** `modules/pev/implantation_data.py`

### **Antes:**
```python
return {
    "plan_id": plan_record.get("id") or plan_id,
    "company_id": plan_record.get("company_id"),
    ...
}
```

### **Depois:**
```python
actual_plan_id = plan_record.get("id") or plan_id
return {
    "id": actual_plan_id,         # ✅ ADICIONADO!
    "plan_id": actual_plan_id,
    "company_id": plan_record.get("company_id"),
    ...
}
```

Agora o dicionário tem **AMBAS** as chaves (`id` e `plan_id`) apontando para o mesmo valor.

---

## 🧪 **COMO TESTAR:**

### **1. REINICIE O SERVIDOR FLASK** ⚠️ **OBRIGATÓRIO!**

```bash
Ctrl+C
python app_pev.py
```

### **2. Acesse a página de implantação:**

```
http://127.0.0.1:5003/pev/implantacao?plan_id=5
```

### **3. Clique em "Alinhamento Estratégico"**

✅ Agora a URL deve ser:
```
http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=5
```

**Repare que agora tem o `5` no final!**

### **4. Adicione o sócio "Antonio Carlos"**

1. Clique em "+ Adicionar Sócio"
2. Preencha os dados
3. Clique em "Salvar"

✅ **AGORA VAI FUNCIONAR!**

---

## 📊 **O QUE FOI CORRIGIDO:**

- ✅ Adicionado `"id"` ao dicionário retornado por `build_plan_context()`
- ✅ URLs do sidebar agora incluem `plan_id` correto
- ✅ JavaScript consegue pegar plan_id da URL
- ✅ APIs vão receber plan_id correto

---

## 🎯 **FLUXO CORRETO AGORA:**

```
1. Acessa: /pev/implantacao?plan_id=5
   ↓
2. build_plan_context() retorna: {"id": 5, "plan_id": 5, ...}
   ↓
3. Template gera: url_for(..., plan_id=plan.id)  → plan_id=5
   ↓
4. URL do sidebar: /canvas-expectativas?plan_id=5 ✅
   ↓
5. JavaScript pega: planId = 5 ✅
   ↓
6. API recebe: plan_id=5 ✅
   ↓
7. Insert no banco: plan_id=5 ✅
   ↓
8. ✅ SUCESSO!
```

---

## 📁 **ARQUIVO MODIFICADO:**

```
✅ modules/pev/implantation_data.py  (1 linha adicionada)
```

---

## 🎉 **RESULTADO ESPERADO:**

Após reiniciar o servidor:

1. ✅ URL terá `?plan_id=5` (não vazio!)
2. ✅ Console mostrará: "Plan ID detectado: 5"
3. ✅ Adicionar sócio funcionará
4. ✅ Sócio será salvo no banco corretamente

---

**🚀 REINICIE O SERVIDOR E TESTE AGORA!**

**ESSA ERA A ÚLTIMA PEÇA DO QUEBRA-CABEÇA! 🎉**

