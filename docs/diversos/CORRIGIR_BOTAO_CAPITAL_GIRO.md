# 🔧 Correção: Botão + Capital de Giro

## O QUE FOI CORRIGIDO

Adicionei debug e exposição explícita das funções no escopo `window` para garantir que os botões `onclick` funcionem corretamente.

### Mudanças Aplicadas:

1. ✅ **Debug logs** para rastrear execução
2. ✅ **Funções expostas no window** (window.openCapitalGiroModal, etc)
3. ✅ **Verificação de elemento do modal**
4. ✅ **Logs de inicialização**

---

## 🚀 PASSOS PARA TESTAR

### 1. Reiniciar o Docker

```bash
docker-compose restart app
```

### 2. Aguardar 5 segundos

```bash
timeout /t 5
```

### 3. Abrir a Página

```
http://localhost:5000/pev/implantacao/modelo/modefin?plan_id=1
```

### 4. Abrir o Console do Navegador

**Chrome/Edge:** Pressione `F12` → Aba **Console**

### 5. Verificar Logs Iniciais

Você deve ver no console:

```
[ModeFin] Iniciando...
Plan ID: 1
Products Totals: {...}
Fixed Costs: {...}
Capital Giro Items: []
[ModeFin] Renderização completa!
[ModeFin] Funções expostas no window: {
  openCapitalGiroModal: "function",
  closeCapitalGiroModal: "function",
  saveCapitalGiro: "function",
  editCapitalGiro: "function",
  deleteCapitalGiro: "function"
}
```

✅ **Se aparecer "function" para todas, está OK!**

❌ **Se aparecer "undefined", há um problema de escopo**

---

## 🧪 TESTES NO CONSOLE

### Teste 1: Verificar se o modal existe

```javascript
document.getElementById('capitalGiroModal')
```

✅ **Esperado:** Deve retornar um elemento `<div class="modal" id="capitalGiroModal"></div>`

❌ **Se retornar `null`:** O DOM não foi renderizado corretamente

### Teste 2: Verificar se a função existe

```javascript
typeof window.openCapitalGiroModal
```

✅ **Esperado:** `"function"`

❌ **Se retornar `"undefined"`:** A função não foi exposta corretamente

### Teste 3: Abrir modal via console

```javascript
window.openCapitalGiroModal()
```

✅ **Esperado:** Modal deve abrir e aparecer logs:
```
[Modal] Abrindo modal de Capital de Giro, itemId: null
[Modal] Elemento do modal: <div>...
[Modal] Modal aberto com sucesso!
```

❌ **Se aparecer erro:** Anote o erro e reporte

### Teste 4: Clicar no botão

Clique no botão **"+ Capital de Giro"** e verifique os logs:

✅ **Esperado:** Mesmos logs do Teste 3

❌ **Se não aparecer nada:** O evento onclick não está funcionando

---

## 🐛 POSSÍVEIS PROBLEMAS E SOLUÇÕES

### Problema 1: Modal não abre (nenhum log aparece)

**Causa:** Erro de JavaScript antes da função

**Solução:**
1. Verifique se há erros no console (vermelho)
2. Role o console até o primeiro erro
3. Reporte o erro

### Problema 2: Erro "capitalGiroModal não encontrado"

**Causa:** Modal não foi renderizado no DOM

**Solução:**
1. Verifique se o template está completo
2. Force reload: `Ctrl + F5`
3. Limpe cache: `Ctrl + Shift + Delete`

### Problema 3: Função "undefined"

**Causa:** Função não foi exposta no window

**Solução:**
1. Reinicie o Docker: `docker-compose restart app`
2. Force reload da página: `Ctrl + F5`
3. Verifique se não há erros de sintaxe no console

### Problema 4: Modal abre mas não salva

**Causa:** APIs não configuradas

**Solução:**
1. Verifique se migration foi aplicada: `aplicar_modefin.bat`
2. Verifique logs do Docker: `docker-compose logs -f app`

---

## 📊 LOGS ESPERADOS

### Quando clicar no botão "+ Capital de Giro":

```
[Modal] Abrindo modal de Capital de Giro, itemId: null
[Modal] Elemento do modal: <div class="modal" id="capitalGiroModal">...
[Modal] Modal aberto com sucesso!
```

### Quando preencher e clicar em "Salvar":

```
[API] Salvando capital de giro...
[API] Sucesso!
[Modal] Fechando modal
[Investimentos] Recarregando dados...
```

### Quando clicar em ✏️ (Editar):

```
[Modal] Abrindo modal de Capital de Giro, itemId: 123
[Modal] Dados do item: {id: 123, item_type: "caixa", ...}
[Modal] Elemento do modal: ...
[Modal] Modal aberto com sucesso!
```

### Quando clicar em 🗑️ (Deletar):

```
[Confirmação do navegador aparece]
[Se confirmar]
[API] Deletando capital de giro...
[API] Sucesso!
[Investimentos] Recarregando dados...
```

---

## 🎯 CHECKLIST RÁPIDO

- [ ] Reiniciei o Docker
- [ ] Aguardei 5 segundos
- [ ] Abri a página com plan_id válido
- [ ] Abri o Console (F12)
- [ ] Vi logs de inicialização
- [ ] Todas as funções aparecem como "function"
- [ ] Modal existe no DOM
- [ ] Cliquei no botão "+ Capital de Giro"
- [ ] Modal abriu
- [ ] Consegui preencher os campos
- [ ] Consegui salvar

---

## 🔍 SE AINDA NÃO FUNCIONAR

### Copie e envie estas informações:

1. **Logs do Console:**
   - Abra Console (F12)
   - Clique com botão direito nos logs
   - "Save as..." ou tire screenshot

2. **Logs do Docker:**
```bash
docker-compose logs --tail=50 app > logs_docker.txt
```

3. **Estrutura do DOM:**
```javascript
// Cole no console e copie o resultado:
console.log('Modal:', document.getElementById('capitalGiroModal'));
console.log('Funções:', {
  open: typeof window.openCapitalGiroModal,
  close: typeof window.closeCapitalGiroModal,
  save: typeof window.saveCapitalGiro
});
```

4. **Versão do Navegador:**
   - Chrome: Menu → Ajuda → Sobre o Google Chrome
   - Edge: Menu → Ajuda e comentários → Sobre o Microsoft Edge

---

## ✅ TESTE COMPLETO

Se tudo estiver funcionando, você conseguirá:

1. ✅ Clicar em "+ Capital de Giro"
2. ✅ Ver modal abrir com formulário
3. ✅ Preencher:
   - Tipo: Caixa
   - Data: 2026-05-01
   - Valor: 100000
   - Descrição: Teste inicial
4. ✅ Clicar em "Salvar"
5. ✅ Ver modal fechar
6. ✅ Ver item na tabela
7. ✅ Ver total atualizado no card
8. ✅ Clicar em ✏️ e editar
9. ✅ Clicar em 🗑️ e deletar

---

**Última atualização:** 29/10/2025 - 20:00

