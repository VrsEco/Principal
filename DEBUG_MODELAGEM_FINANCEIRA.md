# 🔍 DEBUG - Modelagem Financeira

**Problema:** Botão "Adicionar Premissa" não responde

---

## ✅ PASSO 1: Verificar Console (F12)

1. **Abra a página:**
   ```
   http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=45
   ```

2. **Abra o Console (F12)**

3. **Procure pelas mensagens de debug:**
   - 🔵 `Script de Modelagem Financeira carregado!`
   - 🔵 `plan_id: 45`
   - 🔵 `Dados carregados: {...}`

### **Cenário A: NÃO aparece NENHUMA mensagem**

**Problema:** O JavaScript não está carregando!

**Possíveis causas:**

#### 1. Erro de sintaxe no template

Verifique se há erro no console antes do script. Procure por:
- `Uncaught SyntaxError`
- `Unexpected token`
- Mensagens de erro em vermelho

#### 2. Docker não recarregou o código

**Solução:**
```bash
# Reiniciar o container Flask
docker-compose restart app

# Aguardar 10 segundos
# Limpar cache do navegador (Ctrl+Shift+Delete)
# Recarregar a página (Ctrl+F5)
```

#### 3. Arquivo não foi atualizado no container

**Solução:**
```bash
# Verificar se o arquivo está montado corretamente
docker exec gestaoversos_app_prod ls -la templates/implantacao/modelo_modelagem_financeira.html

# Se não existir ou estiver desatualizado, reconstruir:
docker-compose down
docker-compose up -d --build
```

---

### **Cenário B: Mensagens aparecem mas botão não funciona**

**Procure no console:**
- 🟢 `openPremiseModal chamado! premiseId: null`
- 🟢 `Modal encontrado: SIM`

Se estas mensagens **NÃO aparecem** ao clicar:

**Problema:** O evento onclick não está funcionando

**Soluções:**

#### 1. Verificar se o botão existe

No console, digite:
```javascript
document.querySelector('.btn-add')
```

Deve retornar o elemento HTML do botão.

#### 2. Verificar se a função existe

No console, digite:
```javascript
typeof openPremiseModal
```

Deve retornar: `"function"`

#### 3. Testar a função manualmente

No console, digite:
```javascript
openPremiseModal()
```

Se o modal abrir → o problema é o evento onclick
Se der erro → o problema é no código da função

---

### **Cenário C: Mensagem "Modal encontrado: NÃO"**

**Problema:** O modal não está no DOM

**Verificar:**

No console, digite:
```javascript
document.getElementById('premiseModal')
```

Se retornar `null` → O HTML do modal não está sendo renderizado.

**Solução:**
Verificar se há erro no template antes do modal.

---

## ✅ PASSO 2: Verificar Plan ID

No console, verifique:
```javascript
const urlParams = new URLSearchParams(window.location.search);
console.log('plan_id:', urlParams.get('plan_id'));
```

**Se retornar `null`:**
- ❌ A URL está sem o parâmetro `plan_id`
- ✅ Adicione: `?plan_id=45` na URL

**Se retornar um número:**
- ✅ O plan_id está correto

---

## ✅ PASSO 3: Verificar Dados do Backend

No console, execute:
```javascript
console.log('Premissas:', premisesData);
console.log('Investimentos:', investmentsData);
console.log('Fontes:', sourcesData);
```

**Se der erro "premisesData is not defined":**
- ❌ Os dados não foram carregados do backend
- Verificar se o template está recebendo os dados

**Se retornar arrays vazios `[]`:**
- ✅ Normal! O banco está vazio
- Não impede de adicionar novos

**Se der erro de sintaxe:**
- ❌ Problema no tojson do Jinja2
- Ver logs do Flask

---

## ✅ PASSO 4: Verificar Logs do Flask (Docker)

```bash
docker logs gestaoversos_app_prod --tail 50
```

Procure por:
- ❌ Erros Python
- ❌ Template errors
- ❌ Database errors

**Mensagens comuns:**

### "jinja2.exceptions.UndefinedError"
O template está tentando acessar variável que não existe.

**Solução:** Verificar se a rota está passando todas as variáveis:
```python
return render_template(
    "implantacao/modelo_modelagem_financeira.html",
    user_name=...,
    premissas=...,
    investimento=...,
    fluxo_negocio=...,
    fluxo_investidor=...
)
```

### "AttributeError: 'NoneType' object has no attribute"
Alguma variável está None.

**Solução:** Adicionar defaults:
```python
premissas=financeiro.get("premissas", [])
```

---

## ✅ PASSO 5: Teste Manual da Função

Abra o console (F12) e execute:

```javascript
// Testar se a função existe
console.log(typeof openPremiseModal);
// Deve retornar: "function"

// Testar se o modal existe
console.log(document.getElementById('premiseModal'));
// Deve retornar: <div class="modal" id="premiseModal">...

// Abrir o modal manualmente
openPremiseModal();
```

**Se o modal abrir:**
✅ O JavaScript está funcionando!
❌ O problema é o evento onclick no botão

**Solução para onclick:**
```javascript
// Adicionar o evento manualmente
document.querySelector('[onclick="openPremiseModal()"]').addEventListener('click', function() {
  openPremiseModal();
});
```

---

## ✅ PASSO 6: Verificar CSP (Content Security Policy)

No console, procure por mensagens:
- `Refused to execute inline script`
- `Content Security Policy`

**Se aparecer:**

O Flask está bloqueando scripts inline.

**Solução:**
Verificar se há CSP configurado no `base.html` ou nas configurações do Flask.

---

## ✅ PASSO 7: Verificar Network (F12 → Network)

1. Abra F12 → Aba "Network"
2. Recarregue a página (Ctrl+F5)
3. Procure pela requisição da página HTML

**Verificar:**
- ✅ Status: 200 OK
- ✅ Type: document
- ✅ Size: Deve ser > 50KB

**Se Status for 500:**
- ❌ Erro no servidor
- Ver logs: `docker logs gestaoversos_app_prod`

**Se Size for muito pequeno (<10KB):**
- ❌ Template não está renderizando
- Ver logs do Flask

---

## ✅ PASSO 8: Teste Simplificado

Crie um arquivo de teste:

**Arquivo:** `test_modal.html`

```html
<!DOCTYPE html>
<html>
<head>
  <title>Teste Modal</title>
  <style>
    .modal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); }
    .modal.active { display: flex; align-items: center; justify-content: center; }
    .modal-content { background: white; padding: 20px; border-radius: 10px; }
  </style>
</head>
<body>
  <button onclick="openModal()">Abrir Modal</button>
  
  <div class="modal" id="testModal">
    <div class="modal-content">
      <h3>Teste</h3>
      <button onclick="closeModal()">Fechar</button>
    </div>
  </div>
  
  <script>
    console.log('Script carregado!');
    
    function openModal() {
      console.log('openModal chamado!');
      const modal = document.getElementById('testModal');
      console.log('Modal:', modal);
      modal.classList.add('active');
    }
    
    function closeModal() {
      document.getElementById('testModal').classList.remove('active');
    }
  </script>
</body>
</html>
```

**Se este teste funcionar:**
✅ O problema NÃO é o navegador
❌ O problema é específico da página de Modelagem Financeira

---

## 🐳 DOCKER - Checklist Específico

### 1. Container está rodando?
```bash
docker ps | grep gestaoversos_app_prod
```

### 2. Código está atualizado no container?
```bash
# Ver data de modificação do arquivo
docker exec gestaoversos_app_prod stat templates/implantacao/modelo_modelagem_financeira.html
```

### 3. Volumes estão montados corretamente?
```bash
docker inspect gestaoversos_app_prod | grep -A 10 "Mounts"
```

### 4. Hot reload está funcionando?
```bash
# Verificar se FLASK_ENV está configurado
docker exec gestaoversos_app_prod env | grep FLASK
```

Se `FLASK_ENV=production` → Hot reload DESATIVADO!

**Solução:**
```bash
# Reiniciar sempre após alterações
docker-compose restart app
```

### 5. Porta está correta?
```bash
docker ps | grep 5003
```

Deve mostrar: `0.0.0.0:5003->5002/tcp`

---

## 🎯 Solução Rápida (Tentar Primeiro)

```bash
# 1. Reiniciar Flask
docker-compose restart app

# 2. Aguardar 10 segundos
sleep 10

# 3. Limpar cache do navegador
# Ctrl+Shift+Delete → Limpar cache

# 4. Recarregar página com força
# Ctrl+F5

# 5. Abrir F12 → Console
# Verificar mensagens de debug

# 6. Testar função manualmente
# No console: openPremiseModal()
```

---

## 📝 Reporte os Resultados

Depois de testar, informe:

1. ✅ Mensagens que aparecem no console (F12)
2. ✅ Erros (se houver)
3. ✅ Resultado do teste manual: `openPremiseModal()`
4. ✅ Logs do Flask (últimas 20 linhas)
5. ✅ Status dos containers: `docker ps`

---

**Com essas informações, consigo identificar exatamente o problema!**



















































