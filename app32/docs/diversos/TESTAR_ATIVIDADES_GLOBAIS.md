# 🧪 TESTAR - Projeto GRV + Atividades Globais

**Data:** 23/10/2025

---

## ✅ **TESTE 1: Projeto GRV Criado Automaticamente**

### **Passo a Passo:**

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`

2. Clique em **"+ Novo Planejamento"**

3. Preencha:
   - **Nome:** Expansão Digital 2025
   - **Tipo:** Planejamento de Implantação (Novo Negócio)
   - **Empresa:** (selecione uma)
   - **Data Início:** 01/11/2025
   - **Data Fim:** 31/12/2025
   - **Descrição:** Teste de criação automática de projeto

4. Clique em **"Criar Planejamento"**

5. ✅ **Aguarde:** Notificação de sucesso

6. **Verificar Projeto Criado:**
   - Vá em: `/grv/company/{company_id}/projects/projects`
   - ✅ **Deve ter:** "Expansão Digital 2025 (Projeto)"
   - ✅ **Tipo:** PEV
   - ✅ **Status:** Planned

---

## ✅ **TESTE 2: Botão Flutuante Visível**

### **Verificar em Várias Páginas:**

1. Acesse: `http://127.0.0.1:5003/pev/dashboard`
   - ✅ Botão "Adicionar Atividade" visível (canto inferior direito)

2. Acesse: `http://127.0.0.1:5003/pev/implantacao?plan_id=5`
   - ✅ Botão visível

3. Acesse: `http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=5`
   - ✅ Botão visível

4. Acesse: `http://127.0.0.1:5003/grv/company/25/projects/projects`
   - ✅ Botão visível

**O botão deve aparecer em TODAS as páginas!**

---

## ✅ **TESTE 3: Adicionar Atividade**

### **Passo a Passo:**

1. Em qualquer página, clique no botão **"Adicionar Atividade"** (canto inferior direito)

2. ✅ **Deve abrir:** Modal com formulário

3. Preencha:
   - **Tipo:** 📚 Estudo/Pesquisa
   - **O que fazer?** Pesquisar fornecedores de móveis nos EUA
   - **Quem?** Antonio Carlos
   - **Quando?** 30/10/2025
   - **Como?** Buscar no Google + LinkedIn + pedir indicações
   - **Observações:** Focar em fornecedores de móveis corporativos
   - **Prioridade:** 🟠 Alta

4. Clique em **"Adicionar Atividade"**

5. ✅ **Deve aparecer:** 
   - Notificação verde no topo direito
   - Mensagem: "✅ Atividade adicionada com sucesso!"
   - Modal fecha automaticamente

---

## ✅ **TESTE 4: Verificar Atividade no Banco**

### **Via Docker:**
```bash
docker exec -it gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev -c "SELECT id, what, who, when_date, priority, context_page FROM global_activities ORDER BY created_at DESC LIMIT 5;"
```

### **Resultado Esperado:**
```
 id |              what              |      who       | when_date  | priority |          context_page
----+--------------------------------+----------------+------------+----------+--------------------------------
  1 | Pesquisar fornecedores...     | Antonio Carlos | 2025-10-30 | high     | /pev/implantacao/alinhamento...
```

---

## ✅ **TESTE 5: API de Listagem**

### **No navegador ou Postman:**
```
GET http://127.0.0.1:5003/api/activities?status=pending
```

### **Response Esperado:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "what": "Pesquisar fornecedores de móveis nos EUA",
      "who": "Antonio Carlos",
      "when_date": "2025-10-30",
      "priority": "high",
      "context_page": "/pev/implantacao/alinhamento/canvas-expectativas"
    }
  ]
}
```

---

## ✅ **TESTE 6: Contexto Automático**

### **Objetivo:** Verificar se a atividade captura o contexto corretamente

1. Acesse: `http://127.0.0.1:5003/pev/implantacao?plan_id=5`

2. Clique em "Adicionar Atividade"

3. Preencha uma atividade simples

4. Salve

5. **Verifique no banco:**
```sql
SELECT context_page, plan_id FROM global_activities WHERE id = (última inserida);
```

6. ✅ **Deve ter:**
   - `context_page`: `/pev/implantacao`
   - `plan_id`: `5`

---

## 🐛 **SE DER ERRO:**

### **Erro: "Botão não aparece"**

**Solução:**
1. Ctrl+Shift+R (limpar cache)
2. Verificar se base.html foi atualizado
3. Verificar console (F12) por erros JavaScript

### **Erro: "API não encontrada"**

**Solução:**
1. Verificar se container foi reiniciado
2. Ver logs: `docker logs gestaoversus_app_dev --tail 50`
3. Procurar: "✅ Global Activities API registered"

### **Erro: "Tabela não existe"**

**Solução:**
```bash
# Criar tabela novamente
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < criar_tabela_atividades.sql
```

---

## 📊 **CHECKLIST COMPLETO**

### **Projeto GRV:**
- [ ] Criar planejamento novo
- [ ] Verificar projeto criado em GRV
- [ ] Projeto tem nome correto (+ " (Projeto)")
- [ ] Projeto vinculado ao plano

### **Atividades Globais:**
- [ ] Botão visível em todas as páginas
- [ ] Modal abre ao clicar
- [ ] Formulário aceita todos os campos
- [ ] Atividade salva no banco
- [ ] Notificação de sucesso aparece
- [ ] Modal fecha após salvar
- [ ] Contexto capturado (plan_id, company_id)

---

## 🎯 **RESULTADO ESPERADO:**

Após os testes:
- ✅ Planejamentos criam projetos GRV automaticamente
- ✅ Botão de atividade aparece em todas as páginas
- ✅ Modal funciona corretamente
- ✅ Atividades salvas no banco
- ✅ APIs funcionando
- ✅ Contexto capturado

---

**🚀 TESTE E APROVEITE! 🎉**

