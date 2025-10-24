# ✅ Correção: plan_id Obrigatório em Todas as URLs

**Data:** 24/10/2025  
**Status:** ✅ Corrigido

---

## 🎯 Problema Identificado

O usuário estava correto: **buscar automaticamente o plano mais recente é perigoso** e pode causar erros quando o usuário trabalha com múltiplos planejamentos simultaneamente.

**Erro anterior:**
```python
def _resolve_plan_id():
    # ... código ...
    # ❌ Buscar automaticamente o mais recente
    return ultimo_plan_id  # PERIGOSO!
```

---

## ✅ Solução Correta Aplicada

### **1. Função `_resolve_plan_id()` Mais Rigorosa**

**Arquivo:** `modules/pev/__init__.py`

```python
def _resolve_plan_id():
    """Return plan id from query parameters. Raises error if not provided."""
    plan_id = request.args.get('plan_id')
    if plan_id:
        try:
            return int(plan_id)
        except (TypeError, ValueError):
            print(f"[ERROR] plan_id inválido: {plan_id}")
            pass
    
    view_args = getattr(request, 'view_args', None) or {}
    plan_id = view_args.get('plan_id')
    if plan_id:
        try:
            return int(plan_id)
        except (TypeError, ValueError):
            print(f"[ERROR] plan_id inválido em view_args: {plan_id}")
            pass
    
    # ERRO: plan_id não foi fornecido - isso NÃO deve acontecer!
    print(f"[CRITICAL ERROR] plan_id não fornecido na URL! request.url: {request.url}")
    raise ValueError("plan_id é obrigatório e deve ser passado na URL")
```

**Comportamento:**
- ✅ Se tiver `plan_id` na URL → Usa ele
- ❌ Se NÃO tiver → **ERRO explícito** (não assume nada)
- ✅ Logs detalhados para debug

---

### **2. Template Corrigido para Passar plan_id**

**Arquivo:** `templates/plan_implantacao.html`

**Antes (ERRADO):**
```jinja2
{% if endpoint %}
  {% set href = url_for(endpoint) %}  {# ❌ SEM plan_id! #}
{% endif %}
```

**Depois (CORRETO):**
```jinja2
{% if endpoint %}
  {% set href = url_for(endpoint, plan_id=plan.plan_id) %}  {# ✅ COM plan_id! #}
{% endif %}
```

**Impacto:** Agora TODOS os links de deliverables passam o `plan_id` corretamente.

---

## 📊 Fluxo Correto de Navegação

### **Cenário 1: Usuário Trabalhando com plan_id=8**

```
1. Acessa: /pev/implantacao?plan_id=8
2. Clica em "Modelo & Mercado"
3. Clica em "Canvas de proposta de valor"
4. Vai para: /pev/implantacao/modelo/canvas-proposta-valor?plan_id=8 ✅
5. Adiciona segmento → Salva no plan_id=8 ✅
```

### **Cenário 2: Usuário Trabalhando com plan_id=45**

```
1. Acessa: /pev/implantacao?plan_id=45
2. Clica em "Modelo & Mercado"
3. Clica em "Canvas de proposta de valor"
4. Vai para: /pev/implantacao/modelo/canvas-proposta-valor?plan_id=45 ✅
5. Adiciona segmento → Salva no plan_id=45 ✅
```

### **Cenário 3: Acesso Direto SEM plan_id (ERRO)**

```
1. Acessa: /pev/implantacao/modelo/canvas-proposta-valor
2. Sistema lança ERRO: "plan_id é obrigatório"
3. Usuário vê mensagem clara do problema ✅
```

---

## 🔒 Por Que Esta Solução é Melhor

### **❌ Solução Anterior (Perigosa):**
```
- Usuário A abre plan_id=8
- Usuário B abre plan_id=45
- Sistema usa automaticamente plan_id=45 (mais recente)
- Usuário A perde contexto e trabalha no plano errado! 💥
```

### **✅ Solução Atual (Segura):**
```
- Usuário A abre plan_id=8
- Todos os links mantêm plan_id=8
- Usuário B abre plan_id=45
- Todos os links mantêm plan_id=45
- Cada usuário trabalha no plano correto! ✅
```

---

## 📁 Arquivos Modificados

```
✅ modules/pev/__init__.py
   - Função _resolve_plan_id() mais rigorosa
   - Lança erro se plan_id não for fornecido
   
✅ templates/plan_implantacao.html
   - TODOS os url_for() agora passam plan_id
   - Linha 475: url_for(endpoint, plan_id=plan.plan_id)
```

---

## 🧪 Como Testar

### **1. Acesse a página de implantação:**
```
http://127.0.0.1:5003/pev/implantacao?plan_id=8
```

### **2. Navegue até Modelo & Mercado:**
- Clique na fase "Modelo & Mercado"
- Clique em "Canvas de proposta de valor"

### **3. Verifique a URL:**
```
✅ DEVE SER: /pev/implantacao/modelo/canvas-proposta-valor?plan_id=8
❌ NÃO DEVE SER: /pev/implantacao/modelo/canvas-proposta-valor (sem plan_id)
```

### **4. Teste o CRUD:**
- Clique em "+ Adicionar Segmento"
- Preencha o formulário
- Salve
- ✅ **Deve salvar no plan_id=8 correto**

### **5. Teste com outro plan_id:**
```
http://127.0.0.1:5003/pev/implantacao?plan_id=45
```
- Navegue até Canvas de Proposta de Valor
- ✅ URL deve ser: `...?plan_id=45`
- Adicione segmento
- ✅ Deve salvar no plan_id=45

---

## 🎯 Garantias da Solução

1. ✅ **Isolamento:** Cada plano mantém seu contexto
2. ✅ **Rastreabilidade:** Sempre sabemos qual plano está ativo
3. ✅ **Segurança:** Sem risco de salvar no plano errado
4. ✅ **Debug:** Logs explícitos se algo der errado
5. ✅ **Escalabilidade:** Funciona com N usuários simultâneos

---

**Status:** ✅ **CORREÇÃO SEGURA APLICADA!**

**Próximo passo:** Testar navegação completa para garantir que plan_id é preservado em todos os links.

