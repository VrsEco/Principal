# ✅ Correção: Seleção de Planejamentos por Tipo

**Data:** 23/10/2025  
**Status:** ✅ Corrigido

---

## 🐛 Problema Identificado

Após criar um planejamento do tipo **"Novo Negócio" (implantacao)**, o usuário não conseguia acessá-lo pelo seletor do dashboard porque:

❌ O botão **"Ir para planejamento"** sempre redirecionava para `/plans/{id}` (interface clássica)  
❌ Não verificava o tipo do planejamento (`plan_mode`)  
❌ Planejamentos de implantação eram inacessíveis

---

## ✅ Solução Implementada

### 1. **Backend - Incluir `plan_mode` na Lista de Planos**

**Arquivo:** `modules/pev/__init__.py`

```python
companies_with_plans['plans'] = [
    {
        'id': plan['id'], 
        'name': plan['name'],
        'plan_mode': plan.get('plan_mode', 'evolucao')  # ← Adicionado
    }
    for plan in plans
]
```

### 2. **Frontend - Armazenar `plan_mode` nas Options**

**Arquivo:** `templates/plan_selector.html`

```javascript
// Mapear planos com plan_mode
const planMap = companiesData.reduce((acc, item) => {
  const plans = (item.plans || []).map(plan => ({
    id: plan.id || plan['id'],
    name: plan.name || plan['name'],
    plan_mode: plan.plan_mode || plan['plan_mode'] || 'evolucao'  // ← Adicionado
  }));
  acc[item.id] = plans;
  return acc;
}, {});

// Guardar plan_mode no data-attribute
plans.forEach(plan => {
  const opt = document.createElement('option');
  opt.value = plan.id;
  opt.textContent = plan.name;
  opt.dataset.planMode = plan.plan_mode || 'evolucao';  // ← Adicionado
  planSelect.appendChild(opt);
});
```

### 3. **Redirecionamento Inteligente**

```javascript
// Ao selecionar plano, guardar plan_mode
planSelect.addEventListener('change', function () {
  const value = this.value;
  const selectedOption = this.options[this.selectedIndex];
  const planMode = selectedOption ? selectedOption.dataset.planMode : 'evolucao';
  
  confirmBtn.disabled = !value;
  confirmBtn.dataset.planId = value || '';
  confirmBtn.dataset.planMode = planMode || 'evolucao';  // ← Guardado
});

// Ao clicar, redirecionar baseado no tipo
confirmBtn.addEventListener('click', function () {
  const planId = this.dataset.planId;
  const planMode = this.dataset.planMode || 'evolucao';
  
  if (!planId) return;
  
  // Redirecionar baseado no tipo de planejamento
  if (planMode === 'implantacao') {
    window.location.href = '/pev/implantacao?plan_id=' + planId;  // ← Novo Negócio
  } else {
    window.location.href = '/plans/' + planId;  // ← Evolução Clássica
  }
});
```

---

## 🎯 Como Funciona Agora

### **Fluxo de Seleção:**

```
1. Usuário seleciona EMPRESA
   ↓
2. Sistema carrega PLANOS da empresa (com plan_mode)
   ↓
3. Usuário seleciona PLANEJAMENTO
   ↓
4. Sistema verifica TIPO do plano (evolucao ou implantacao)
   ↓
5. Botão "Ir para planejamento" fica habilitado
   ↓
6. Usuário clica no botão
   ↓
7. Sistema redireciona para URL CORRETA:
   • evolucao → /plans/{id}
   • implantacao → /pev/implantacao?plan_id={id}
```

---

## 🧪 Como Testar

### **Teste 1: Planejamento de Evolução**

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
2. Selecione uma empresa
3. Selecione um planejamento do tipo **"Evolução"**
4. Clique em **"Ir para planejamento"**
5. ✅ **Esperado:** Redireciona para `/plans/{id}` (interface clássica)

### **Teste 2: Planejamento de Implantação**

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
2. Selecione uma empresa
3. Selecione um planejamento do tipo **"Novo Negócio"**
4. Clique em **"Ir para planejamento"**
5. ✅ **Esperado:** Redireciona para `/pev/implantacao?plan_id={id}` (interface nova)

### **Teste 3: Criar e Acessar Novo Planejamento de Implantação**

1. Crie um novo planejamento tipo "Implantação"
2. Após redirecionamento automático, volte ao dashboard
3. Selecione a empresa
4. Veja o planejamento na lista
5. Selecione-o
6. Clique em "Ir para planejamento"
7. ✅ **Esperado:** Vai para `/pev/implantacao?plan_id={id}`

---

## 📁 Arquivos Modificados

```
✅ modules/pev/__init__.py         (+1 linha)  - Include plan_mode
✅ templates/plan_selector.html    (+15 linhas) - JavaScript atualizado
```

---

## 🔍 Verificação no Console do Navegador

Você pode verificar se o `plan_mode` está sendo carregado corretamente:

```javascript
// Abrir Console (F12) e executar:
const hub = document.getElementById('project-hub');
const companies = JSON.parse(hub.getAttribute('data-companies'));
console.log(companies);
// Deve mostrar plans com plan_mode: "evolucao" ou "implantacao"
```

---

## ✅ Checklist de Validação

- [x] Backend inclui `plan_mode` na lista de planos
- [x] JavaScript armazena `plan_mode` nas options
- [x] JavaScript guarda `plan_mode` ao selecionar plano
- [x] Botão verifica `plan_mode` antes de redirecionar
- [x] Planejamentos de "Evolução" vão para `/plans/{id}`
- [x] Planejamentos de "Implantação" vão para `/pev/implantacao?plan_id={id}`
- [x] Compatibilidade com planos antigos (default: 'evolucao')

---

## 💡 Observações Importantes

### 1. **Compatibilidade com Planos Antigos**
Planos criados antes desta atualização não têm `plan_mode` definido, então o sistema usa `'evolucao'` como padrão:

```javascript
plan_mode: plan.get('plan_mode', 'evolucao')  // Default para evolucao
```

### 2. **Migration Aplicada**
O campo `plan_mode` foi adicionado com a migration `20251023_add_plan_mode_field.sql`. Se ainda não aplicou, execute:

```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/20251023_add_plan_mode_field.sql
```

### 3. **Banco de Dados Retorna `plan_mode`**
As funções `get_plans_by_company()` usam `SELECT *`, então o campo `plan_mode` é retornado automaticamente quando existe na tabela.

---

## 🎉 Resultado Final

**ANTES:**
- ❌ Criar planejamento de "Novo Negócio"
- ❌ Não conseguia acessá-lo depois
- ❌ Botão sempre ia para `/plans/{id}`

**AGORA:**
- ✅ Criar planejamento de "Novo Negócio"
- ✅ Aparece na lista normalmente
- ✅ Botão redireciona para `/pev/implantacao?plan_id={id}` ✨

---

## 📞 Suporte

Se ainda houver problemas:

1. Verificar no Console (F12) se há erros JavaScript
2. Verificar se migration foi aplicada:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'plans' AND column_name = 'plan_mode';
   ```
3. Limpar cache do navegador (Ctrl+Shift+R)

---

**Status:** ✅ **CORRIGIDO E PRONTO PARA USO!**

**Desenvolvido por:** Cursor AI  
**Testado por:** [Aguardando teste do usuário]  
**Data:** 23/10/2025

