# 🐛 DEBUG: Plan Mode não está funcionando

**Status:** Investigando

---

## 🔍 Passo a Passo de Debug

### **Passo 1: Verificar o que está no Banco de Dados**

Execute este comando:

```bash
# PostgreSQL
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < verificar_plan_mode_banco.sql

# OU manualmente:
docker exec -it gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev

# Dentro do PostgreSQL, execute:
SELECT id, name, plan_mode, created_at FROM plans ORDER BY created_at DESC LIMIT 5;
```

**O QUE VERIFICAR:**
- ✅ A coluna `plan_mode` existe?
- ✅ Os planos têm valores: 'evolucao' ou 'implantacao'?
- ✅ O plano que você criou tem o `plan_mode` correto?

---

### **Passo 2: Verificar o Console do Navegador**

1. Abra o Chrome/Edge
2. Pressione **F12** (DevTools)
3. Vá na aba **Console**
4. Acesse: `http://127.0.0.1:5003/pev/dashboard`
5. Veja os logs:

```javascript
🔍 Plans loaded for company [Nome da Empresa] : [...]
```

**O QUE VERIFICAR:**
- ✅ Os planos aparecem no console?
- ✅ Cada plano tem `plan_mode: "evolucao"` ou `plan_mode: "implantacao"`?
- ✅ O plano de "Novo Negócio" tem `plan_mode: "implantacao"`?

---

### **Passo 3: Testar a Seleção**

1. Selecione uma **empresa**
2. Selecione um **planejamento**
3. Veja no console:

```javascript
📋 Plan selected: {
  planId: "X",
  planMode: "implantacao" ou "evolucao",
  optionDataset: {...}
}
```

**O QUE VERIFICAR:**
- ✅ O `planMode` está correto?
- ✅ Se for "Novo Negócio", deveria ser "implantacao"

---

### **Passo 4: Testar o Clique**

1. Clique em **"Ir para planejamento"**
2. ANTES de redirecionar, veja no console:

```javascript
🚀 Redirecting - Plan ID: X, Plan Mode: implantacao
✅ Going to IMPLANTACAO: /pev/implantacao?plan_id=X
```

**O QUE VERIFICAR:**
- ✅ Qual URL está sendo usada?
- ✅ Se `plan_mode` é "implantacao", vai para `/pev/implantacao?plan_id=X`?

---

## 🐛 Possíveis Problemas e Soluções

### **Problema 1: Coluna `plan_mode` não existe no banco**

**Sintoma:** SQL retorna vazio ou erro

**Solução:**
```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/20251023_add_plan_mode_field.sql
```

---

### **Problema 2: Planos criados têm `plan_mode` = NULL**

**Sintoma:** SQL mostra `plan_mode` vazio/null

**Solução:** O plano foi criado ANTES da migration. Atualize manualmente:

```sql
-- Encontre o ID do plano
SELECT id, name, plan_mode FROM plans ORDER BY created_at DESC;

-- Atualize o plano de "Novo Negócio"
UPDATE plans SET plan_mode = 'implantacao' WHERE id = X;
```

Substitua `X` pelo ID do plano que você criou.

---

### **Problema 3: JavaScript não está pegando `plan_mode`**

**Sintoma:** Console mostra `plan_mode: undefined` ou `plan_mode: "evolucao"` para todos

**Solução:** 
1. Limpar cache do navegador (Ctrl+Shift+R)
2. Verificar se o backend está retornando `plan_mode`:

```javascript
// No console do navegador, execute:
fetch('/pev/dashboard').then(r => r.text()).then(html => {
  const div = document.createElement('div');
  div.innerHTML = html;
  const hub = div.querySelector('#project-hub');
  const data = JSON.parse(hub.getAttribute('data-companies'));
  console.log('Companies data:', data);
});
```

---

### **Problema 4: Plano foi criado com tipo errado**

**Sintoma:** Você criou como "Implantação" mas salvou como "Evolução"

**Solução:** Verifique a criação. Crie um novo plano de teste:

1. Vá em "Novo planejamento"
2. Selecione tipo **"Planejamento de Implantação (Novo Negócio)"**
3. Preencha os dados
4. Clique em "Criar"
5. Verifique no banco se salvou `plan_mode = 'implantacao'`

---

## 📝 Template de Reporte

Copie e preencha:

```
### Resultado do Debug:

**1. Banco de Dados:**
- [ ] Coluna plan_mode existe? Sim/Não
- [ ] Plano criado tem plan_mode? Valor: ___________
- [ ] ID do plano: ___________

**2. Console do Navegador:**
- [ ] Plans loaded mostra plan_mode? Sim/Não
- [ ] Valor do plan_mode: ___________

**3. Seleção:**
- [ ] Plan selected mostra planMode correto? Sim/Não
- [ ] planMode valor: ___________

**4. Redirecionamento:**
- [ ] URL de destino: ___________
- [ ] Era esperado: ___________
```

---

## 🚀 Solução Rápida (Se Tudo Falhar)

Se o plano já foi criado mas com `plan_mode` errado, execute:

```sql
-- 1. Ver planos recentes
SELECT id, name, plan_mode FROM plans ORDER BY created_at DESC LIMIT 5;

-- 2. Atualizar o plano correto (substitua X pelo ID)
UPDATE plans 
SET plan_mode = 'implantacao' 
WHERE id = X AND name LIKE '%Novo%';

-- 3. Verificar
SELECT id, name, plan_mode FROM plans WHERE id = X;
```

Depois:
1. Recarregue a página (Ctrl+Shift+R)
2. Selecione o plano novamente
3. Teste!

---

**Me envie os resultados do debug para eu ajudar! 🔍**

