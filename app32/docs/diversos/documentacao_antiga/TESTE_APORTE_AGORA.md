# 🧪 TESTE O APORTE AGORA!

## ✅ Correção Aplicada

O erro **"Erro ao salvar aporte"** foi **CORRIGIDO**.

**Problema:** O HTML tinha IDs fixos (1-6), mas para `plan_id=8` os IDs reais são **19-24**.

**Solução:** O select agora carrega os itens **dinamicamente** do banco de dados.

---

## 🎬 Como Testar

### 1️⃣ Acesse a Página

```
http://127.0.0.1:5003/pev/implantacao/modelo/modelagem-financeira?plan_id=8
```

### 2️⃣ Abra o DevTools (F12)

- Clique em **Console** para ver os logs

### 3️⃣ Clique em "+ Adicionar Aporte"

Você deve ver no console:
```
📦 Investment items cached: 6
```

### 4️⃣ Verifique o Select

O campo **"Tipo de Investimento"** deve mostrar:

**Capital de Giro:**
- Caixa
- Recebíveis
- Estoques

**Imobilizado:**
- Instalações
- Máquinas e Equipamentos
- Outros Investimentos

### 5️⃣ Preencha o Formulário

- **Tipo de Investimento:** Caixa
- **Data do Aporte:** 2026-01-15
- **Valor:** 50000
- **Observações:** (opcional) "Teste de aporte"

### 6️⃣ Clique em "Salvar"

### 7️⃣ Resultado Esperado ✅

1. Deve aparecer: **"Aporte salvo com sucesso!"**
2. A página deve **recarregar automaticamente**
3. O aporte deve aparecer na **planilha de investimentos**
4. O **total** do item Caixa deve ser atualizado

---

## 🔍 Se Ainda Der Erro

### No Console (F12):

Copie e cole aqui:
- Mensagem de erro completa
- Stack trace

### No Network (F12 → Network):

1. Tente salvar novamente
2. Procure por: `finance/investment/contributions`
3. Clique nele
4. Veja:
   - **Headers** → Status Code
   - **Payload** → Dados enviados
   - **Response** → Resposta do servidor

### No Servidor (Terminal):

Procure por mensagens:
```
Error creating investment contribution: ...
```

---

## 📊 Verificação do Banco (Opcional)

Para confirmar que os itens existem:

```bash
python -c "from config_database import get_db; db = get_db(); conn = db._get_connection(); cursor = conn.cursor(); cursor.execute('SELECT i.id, i.item_name FROM plan_finance_investment_items i JOIN plan_finance_investment_categories c ON i.category_id = c.id WHERE c.plan_id = 8'); rows = cursor.fetchall(); [print(f'ID {r[0]}: {r[1]}') for r in rows]; conn.close()"
```

**Deve mostrar:**
```
ID 19: Caixa
ID 20: Recebíveis
ID 21: Estoques
ID 22: Instalações
ID 23: Máquinas e Equipamentos
ID 24: Outros Investimentos
```

---

## ✅ O Que Foi Corrigido

### Antes:
- Select com IDs hardcoded (1, 2, 3, 4, 5, 6)
- Não funcionava para plan_id ≠ 1

### Depois:
- Select carrega IDs dinamicamente do banco
- Funciona para **qualquer plan_id**
- Mais robusto e manutenível

---

## 🎯 Teste Adicional

Depois de salvar um aporte, tente:

1. **Editar** o aporte (clique no ícone de editar)
2. **Deletar** o aporte (clique no ícone de deletar)
3. **Adicionar múltiplos** aportes com datas diferentes
4. **Verificar** se os totais são calculados corretamente

---

**🚀 Está funcionando? Me avise!**  
**❌ Deu erro? Envie os logs do console e do servidor.**

