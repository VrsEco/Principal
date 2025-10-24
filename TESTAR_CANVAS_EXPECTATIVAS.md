# 🧪 TESTE - Canvas de Expectativas (CRUD Completo)

**URL:** `http://127.0.0.1:5003/pev/implantacao/alinhamento/canvas-expectativas?plan_id=8`

---

## ✅ O Que Testar

### **1. ADICIONAR SÓCIO**
1. Clique em **"+ Adicionar Sócio"**
2. Preencha todos os campos
3. Clique em **"Salvar"**
4. ✅ Deve: Aparecer notificação verde + sócio na tabela

### **2. EDITAR SÓCIO**
1. Clique no botão **✏️** de um sócio
2. Modifique algum campo
3. Clique em **"Salvar"**
4. ✅ Deve: Atualizar os dados na tabela

### **3. DELETAR SÓCIO**
1. Clique no botão **🗑️**
2. Confirme
3. ✅ Deve: Sócio desaparece da tabela

### **4. SALVAR ALINHAMENTO**
1. Preencha "Visão Compartilhada"
2. Preencha "Metas Financeiras"
3. Adicione 2-3 critérios de decisão
4. Clique em **"Salvar Alinhamento"**
5. ✅ Deve: Notificação de sucesso

### **5. ADICIONAR PRÓXIMO PASSO**
1. Clique em **"+ Adicionar Passo"**
2. Preencha os campos
3. Clique em **"Adicionar"**
4. ✅ Deve: Card aparece na lista

### **6. DELETAR PRÓXIMO PASSO**
1. Clique no **×** no canto do card
2. Confirme
3. ✅ Deve: Card desaparece

---

## 🐛 Se Algo Der Errado

### **Erro 500:**
- Verifique console do navegador (F12)
- Veja logs do servidor

### **Modal não abre:**
- Limpe cache (Ctrl+Shift+R)
- Verifique console (F12)

### **Dados não salvam:**
- Verifique se está usando PostgreSQL
- Verifique se tabelas existem

---

**TESTE TUDO E ME AVISE! 🚀**

