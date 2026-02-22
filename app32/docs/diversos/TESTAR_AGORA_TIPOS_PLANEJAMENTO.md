# 🧪 TESTE RÁPIDO - Tipos de Planejamento

**PRONTO PARA TESTAR AGORA! ✅**

---

## 🎯 O Que Foi Implementado

Agora você pode escolher entre **2 tipos de planejamento** ao criar um novo plano:

1. **📊 Planejamento de Evolução** → Interface clássica (`/plans/<id>`)
2. **🚀 Planejamento de Implantação** → Interface nova (`/pev/implantacao?plan_id=<id>`)

---

## 🚀 Teste Rápido (5 minutos)

### Passo 1: Abrir o Dashboard PEV
```
http://127.0.0.1:5003/pev/dashboard
```

### Passo 2: Criar Planejamento de EVOLUÇÃO

1. Clique em **"Novo planejamento"**
2. Preencha:
   - **Empresa:** Escolha qualquer empresa
   - **Tipo:** Selecione **"Planejamento de Evolução (Clássico)"**
   - 📝 Veja a descrição que aparece!
   - **Nome:** "Teste Evolução 2025"
   - **Data Início:** 01/01/2025
   - **Data Fim:** 31/12/2025
3. Clique em **"Criar Planejamento"**
4. ✅ **ESPERADO:** Vai para `/plans/<id>` com Dashboard, OKRs, Projetos, etc.

### Passo 3: Criar Planejamento de IMPLANTAÇÃO

1. Volte para `http://127.0.0.1:5003/pev/dashboard`
2. Clique em **"Novo planejamento"**
3. Preencha:
   - **Empresa:** Escolha qualquer empresa
   - **Tipo:** Selecione **"Planejamento de Implantação (Novo Negócio)"**
   - 📝 Veja a descrição diferente!
   - **Nome:** "Teste Implantação 2025"
   - **Data Início:** 01/03/2025
   - **Data Fim:** 30/09/2025
4. Clique em **"Criar Planejamento"**
5. ✅ **ESPERADO:** Vai para `/pev/implantacao?plan_id=<id>` com fases: Alinhamento, Modelo, Execução, Entrega

---

## ⚠️ IMPORTANTE: Aplicar Migration

**ANTES DE TESTAR**, aplique a migration do PostgreSQL:

### Se estiver usando Docker Dev:
```bash
docker exec -i gestaoversus_db_dev psql -U postgres -d bd_app_versus_dev < migrations/20251023_add_plan_mode_field.sql
```

### Se estiver usando SQLite:
✅ **Nada a fazer!** A coluna será criada automaticamente na primeira criação de plano.

---

## ✅ Checklist de Validação

Marque conforme testa:

- [ ] Modal abre e mostra campo "Tipo de Planejamento"
- [ ] Ao selecionar "Evolução", aparece descrição correta
- [ ] Ao selecionar "Implantação", aparece descrição correta
- [ ] Ao tentar criar SEM selecionar tipo, dá erro
- [ ] Criar tipo "Evolução" → redireciona para `/plans/<id>`
- [ ] Criar tipo "Implantação" → redireciona para `/pev/implantacao?plan_id=<id>`

---

## 🎬 Vídeo do Fluxo

### Fluxo Esperado:

```
1. Dashboard PEV
   ↓
2. Clique "Novo planejamento"
   ↓
3. Modal abre
   ↓
4. Seleciona tipo → mostra descrição
   ↓
5. Preenche dados
   ↓
6. Cria
   ↓
7. Redireciona para interface correta
```

---

## 🐛 Se Algo Der Errado

### Erro: "Coluna plan_mode não existe"
**Solução:** Aplicar migration (ver acima)

### Erro: Modal não abre
**Solução:** 
1. Limpar cache (Ctrl+Shift+R)
2. Verificar console do navegador (F12)

### Erro: Não redireciona após criar
**Solução:**
1. Verificar console do navegador (F12)
2. Copiar URL manualmente:
   - Evolução: `http://127.0.0.1:5003/plans/<id>`
   - Implantação: `http://127.0.0.1:5003/pev/implantacao?plan_id=<id>`

---

## 📞 Feedback

Após testar, me informe:
- ✅ O que funcionou
- ❌ O que não funcionou
- 💡 Sugestões de melhoria

---

**PRONTO! Bora testar? 🚀**

