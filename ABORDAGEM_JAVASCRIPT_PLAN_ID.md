# 🔧 NOVA ABORDAGEM: JavaScript pega plan_id da URL

**Data:** 23/10/2025  
**Status:** ✅ Implementado

---

## 🚨 **PROBLEMA:**

O `plan_id` estava vazio na URL:
```
http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=
```

---

## ✅ **NOVA SOLUÇÃO: JavaScript Inteligente**

Ao invés de confiar apenas no template, o JavaScript agora:

### **1. Tenta pegar da URL atual:**
```javascript
const urlParams = new URLSearchParams(window.location.search);
const planId = urlParams.get('plan_id');
```

### **2. Se não encontrar, tenta do referrer (página anterior):**
```javascript
const referrer = document.referrer;
const referrerUrl = new URL(referrer);
const referrerPlanId = new URLSearchParams(referrerUrl.search).get('plan_id');
```

### **3. Último recurso: valor do backend:**
```javascript
return {{ plan_id if plan_id else 'null' }};
```

### **4. Exibe erro se não encontrar:**
```javascript
if (!planId) {
  showMessage('ERRO: plan_id não foi encontrado na URL!', 'error');
}
```

---

## 🔍 **DEBUG ADICIONADO:**

O backend agora loga:
```python
print(f"DEBUG: Canvas Expectativas - plan_id resolvido: {plan_id}")
print(f"DEBUG: request.args: {request.args}")
print(f"DEBUG: plan loaded: {plan.get('id')}")
```

---

## 🚀 **COMO TESTAR:**

### **1. REINICIE o servidor Flask:**
```bash
Ctrl+C
python app_pev.py
```

### **2. Acesse DIRETAMENTE com plan_id:**
```
http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=5
```

### **3. Abra o Console do Navegador (F12):**

Você deve ver:
```
Plan ID detectado: 5
```

### **4. Adicione o sócio:**

Agora deve funcionar porque o JavaScript está usando o plan_id correto!

---

## 📋 **VANTAGENS DESSA ABORDAGEM:**

✅ **Não depende do template** passar o plan_id corretamente  
✅ **Pega da URL atual** (mais confiável)  
✅ **Fallback para referrer** se necessário  
✅ **Exibe erro claro** se plan_id não for encontrado  
✅ **Debug no console** para verificar o valor  

---

## 🧪 **TESTE COMPLETO:**

### **Cenário 1: Acesso direto**
```
URL: /canvas-expectativas?plan_id=5
Resultado: planId = 5 ✅
```

### **Cenário 2: Vindo do sidebar**
```
Página anterior: /pev/implantacao?plan_id=5
Clica: Alinhamento Estratégico
URL atual: /canvas-expectativas?plan_id=5
Resultado: planId = 5 ✅
```

### **Cenário 3: URL sem plan_id (erro)**
```
URL: /canvas-expectativas
Resultado: Erro exibido + planId = null ❌
```

---

## 📁 **ARQUIVOS MODIFICADOS:**

```
✅ templates/implantacao/alinhamento_canvas_expectativas.html
   - JavaScript melhorado para pegar plan_id
   - Debug no console
   - Mensagem de erro se plan_id não encontrado

✅ modules/pev/__init__.py
   - Logs de debug adicionados
   - Passa plan completo para template
```

---

## 🎯 **PRÓXIMO TESTE:**

1. **REINICIE** o servidor
2. **ACESSE:** `http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=5`
3. **ABRA F12** (console do navegador)
4. **VEJA:** "Plan ID detectado: 5"
5. **ADICIONE** sócio
6. **VERIFIQUE** no terminal do servidor os logs de debug

---

**🚀 TESTE AGORA COM ESSA NOVA ABORDAGEM!**

