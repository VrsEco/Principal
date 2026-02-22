# 🔧 Correção: Detecção de Company ID

**Data:** 24/10/2025  
**Status:** ✅ Corrigido

---

## 🐛 PROBLEMA REPORTADO

Ao clicar no botão "+ Nova Atividade", a mensagem aparecia em **todas as páginas**:

```
⚠️ Empresa não detectada - acesse via página de planejamento
```

**Causa:** O sistema não conseguia detectar o `company_id` porque ele não estava na URL, mas sim passado como variável do template pelo backend.

---

## ✅ SOLUÇÃO IMPLEMENTADA

### 1. **Adicionadas Variáveis Globais no base.html**

O `base.html` agora injeta variáveis JavaScript globais quando disponíveis:

```javascript
// Arquivo: templates/base.html
window.companyId = 25;           // Se company.id estiver disponível
window.company = {...};          // Objeto completo da empresa
window.planId = 'expansao-2025'; // Se plan.id estiver disponível
window.portfolioId = 42;         // Se portfolio.id estiver disponível
```

**Benefício:** Qualquer JavaScript na página pode acessar essas variáveis.

### 2. **Detecção Multi-Fonte do Company ID**

O botão agora busca o `company_id` em **6 fontes diferentes**, em ordem de prioridade:

#### 🔍 Ordem de Tentativas:

**1. Query String da URL**
```javascript
// Exemplo: ?company_id=25
const companyId = urlParams.get('company_id');
```

**2. Path da URL**
```javascript
// Exemplo: /company/25/projects
const match = currentPath.match(/\/company\/(\d+)/);
```

**3. Variável Global window.companyId** ⭐ **NOVO**
```javascript
// Injetado pelo base.html
if (typeof window.companyId !== 'undefined') {
  companyId = window.companyId;
}
```

**4. Objeto Global window.company.id** ⭐ **NOVO**
```javascript
// Injetado pelo base.html
if (window.company && window.company.id) {
  companyId = window.company.id;
}
```

**5. Data Attribute**
```javascript
// Exemplo: <div data-company-id="25">
const element = document.querySelector('[data-company-id]');
companyId = element.dataset.companyId;
```

**6. API do Plano** (se tiver plan_id)
```javascript
// Busca company_id do plano via API
const response = await fetch(`/api/plans/${planId}`);
companyId = response.data.company_id;
```

### 3. **Logs de Debug Adicionados**

Agora você pode ver no **Console do Navegador (F12)** o que está sendo detectado:

```javascript
// No base.html
Contexto global: { 
  companyId: 25, 
  planId: 'expansao-2025',
  portfolioId: null
}

// No modal de atividade
Company ID encontrado em window.companyId: 25
Plan ID encontrado em window.planId: expansao-2025
Contexto detectado: { 
  companyId: 25, 
  planId: 'expansao-2025', 
  portfolioId: null, 
  currentPath: '/plans/expansao-2025/dashboard' 
}
```

---

## 🧪 COMO TESTAR A CORREÇÃO

### Teste 1: Verificar Variáveis Globais

1. Abra **qualquer página** do sistema
2. Pressione **F12** (abrir Console do Desenvolvedor)
3. Digite no console:
   ```javascript
   window.companyId
   ```
4. **Resultado esperado:** Deve mostrar o ID da empresa (ex: `25`) ou `undefined` se não houver contexto de empresa

### Teste 2: Página de Planejamento PEV

1. Acesse uma página de planejamento (ex: **Expansão 2025**)
2. Abra o Console (F12)
3. Verifique as mensagens:
   ```
   Contexto global: { companyId: 25, planId: 'expansao-2025', ... }
   ```
4. Clique no botão **"+ Nova Atividade"**
5. Observe os logs no console:
   ```
   Company ID encontrado em window.companyId: 25
   Plan ID encontrado em window.planId: expansao-2025
   Contexto detectado: { companyId: 25, planId: 'expansao-2025', ... }
   ```
6. **Resultado esperado:** O modal deve abrir e carregar os projetos da empresa

### Teste 3: Página GRV - Projetos

1. Acesse **GRV → Empresa → Projetos**
2. Clique no botão **"+ Nova Atividade"**
3. Observe os logs no console
4. **Resultado esperado:** Deve detectar company_id e listar projetos

### Teste 4: Gestão de Reuniões

1. Acesse **Gestão de Reuniões** de uma empresa
2. Clique no botão **"+ Nova Atividade"**
3. **Resultado esperado:** Deve detectar company_id e listar projetos

---

## 📊 CENÁRIOS DE DETECÇÃO

| Página | Como Detecta |
|--------|--------------|
| **PEV - Planejamento** | ✅ window.companyId (variável global) |
| **GRV - Projetos** | ✅ /company/25/... (path da URL) |
| **GRV - Kanban** | ✅ data-company-id (atributo HTML) |
| **Gestão de Reuniões** | ✅ /meetings/company/25 (path da URL) |
| **Dashboard Principal** | ✅ window.companyId (se disponível) |
| **Sem Contexto** | ⚠️ Mostra mensagem de erro (esperado) |

---

## 🔍 SE AINDA NÃO FUNCIONAR

Se após essas correções ainda aparecer "Empresa não detectada":

### 1. Verifique os Logs do Console

Abra o Console (F12) e procure por:
```
Contexto global: { companyId: null, ... }
Company ID encontrado em ...
Contexto detectado: { companyId: null, ... }
```

### 2. Identifique Qual Página

Anote:
- URL completa da página
- Path da URL
- Se há parâmetros na URL

**Exemplo:**
```
URL: http://127.0.0.1:5003/plans/expansao-2025/dashboard
Path: /plans/expansao-2025/dashboard
Query: (vazio)
```

### 3. Verifique Variáveis Globais

No console, digite:
```javascript
console.log({
  companyId: window.companyId,
  company: window.company,
  planId: window.planId,
  portfolioId: window.portfolioId
});
```

Se **todos** retornarem `undefined`, significa que o backend não está passando essas variáveis para aquela página específica.

### 4. Reportar o Problema

Me informe:
1. **Página:** Qual página você estava
2. **URL:** A URL completa
3. **Console:** O que apareceu no console
4. **Variáveis:** O resultado do `window.companyId`

---

## 📁 ARQUIVOS MODIFICADOS

```
✅ templates/base.html
   → Adicionadas variáveis globais JavaScript
   → window.companyId, window.planId, window.portfolioId
   → Logs de debug no console

✅ templates/components/global_activity_button.html
   → Detecção multi-fonte do company_id (6 métodos)
   → Logs de debug detalhados
   → Mensagens de erro mais claras
```

---

## 💡 MELHORIAS FUTURAS (Opcional)

Se algumas páginas ainda não funcionarem:

1. **Criar API de contexto global:**
   ```
   GET /api/context/current
   → Retorna { company_id, plan_id, portfolio_id, user_id }
   ```

2. **Armazenar no localStorage:**
   ```javascript
   localStorage.setItem('lastCompanyId', companyId);
   ```

3. **Adicionar data-attributes no body:**
   ```html
   <body data-company-id="25" data-plan-id="expansao-2025">
   ```

---

## ✅ STATUS ATUAL

- ✅ Variáveis globais adicionadas no base.html
- ✅ Detecção multi-fonte implementada (6 fontes)
- ✅ Logs de debug adicionados
- ✅ Sem erros de linter
- ⏳ **Aguardando teste do usuário**

---

**Próximo Passo:** Teste em diferentes páginas e me avise se funcionar ou se ainda houver problemas em alguma página específica! 🚀

