# 🚀 COMO USAR: Investimentos com Datas de Aporte

**Sistema 100% pronto! Siga estes passos:**

---

## ⚡ PASSO 1: Instalar (5 minutos)

### Execute o script de instalação:

```bash
.\APLICAR_INVESTIMENTOS_COMPLETO.bat
```

**O que o script faz:**
1. ✅ Verifica se Docker está rodando
2. ✅ Cria tabelas no banco de dados
3. ✅ Insere categorias e itens padrão
4. ✅ Valida a instalação

**Resultado esperado:**
```
✅ Migrations aplicadas com sucesso
✅ Seed executado com sucesso
✅ INSTALAÇÃO COMPLETA!
```

---

## ⚡ PASSO 2: Acessar (1 minuto)

### Abra no navegador:

```
http://127.0.0.1:5003/implantacao/financeiro?plan_id=1
```

**O que você verá:**
- 📊 Seção "Investimentos" com tabelas de Capital de Giro e Imobilizado
- 📋 Botões para adicionar aportes
- 📈 Planilha por período (12 meses)
- 💰 Seção "Fontes de Recursos"

---

## ⚡ PASSO 3: Testar (10 minutos)

### Teste 1️⃣: Adicionar Aporte de Caixa

1. **Localize a tabela "Capital de Giro"**
2. **Na linha "Caixa", clique no botão 📋**
3. **No modal que abrir, preencha:**
   - Data: `2026-01-15`
   - Valor: `50000`
   - Observações: `Aporte inicial de caixa`
4. **Clique em "Salvar"**

✅ **Resultado:** 
- Total de Caixa mostra: R$ 50.000,00
- Na planilha, Jan/2026 mostra: R$ 50.000,00

---

### Teste 2️⃣: Adicionar Fonte de Recursos

1. **Na seção "Fontes de Recursos", clique em "+ Adicionar Fonte"**
2. **Preencha:**
   - Tipo: `Aporte dos Sócios`
   - Data: `2026-01-10`
   - Valor: `200000`
   - Observações: `Capital inicial dos sócios`
3. **Clique em "Salvar"**

✅ **Resultado:**
- Nova linha aparece na tabela com os dados

---

### Teste 3️⃣: Múltiplos Aportes

1. **Adicione outro aporte de Caixa:**
   - Data: `2026-02-15`
   - Valor: `30000`
   
2. **Adicione aporte de Instalações:**
   - Data: `2026-01-20`
   - Valor: `180000`
   - Observações: `Compra do galpão`

✅ **Resultado:**
- Total de Caixa: R$ 80.000,00 (50k + 30k)
- Planilha mostra:
  - Jan/2026 em Caixa: R$ 50.000
  - Fev/2026 em Caixa: R$ 30.000
  - Jan/2026 em Instalações: R$ 180.000

---

### Teste 4️⃣: Visualizar Planilha

1. **Role até a seção "Planilha por Período"**
2. **Observe:**
   - Coluna "Total" soma todos os aportes
   - Cada mês mostra o valor do aporte
   - 12 meses são exibidos automaticamente

---

## 📊 O Que Esperar

### Interface Visual:

```
╔════════════════════════════════════════════════╗
║           INVESTIMENTOS                         ║
╠════════════════════════════════════════════════╣
║                                                 ║
║  Capital de Giro                                ║
║  ┌─────────────┬──────────────┬─────────────┐  ║
║  │ Item        │ Total        │ Aportes     │  ║
║  ├─────────────┼──────────────┼─────────────┤  ║
║  │ Caixa       │ R$ 50.000    │ [📋]        │  ║
║  │ Recebíveis  │ R$ 0,00      │ [📋]        │  ║
║  │ Estoques    │ R$ 0,00      │ [📋]        │  ║
║  └─────────────┴──────────────┴─────────────┘  ║
║                                                 ║
║  Imobilizado                                    ║
║  ┌─────────────┬──────────────┬─────────────┐  ║
║  │ Item        │ Total        │ Aportes     │  ║
║  ├─────────────┼──────────────┼─────────────┤  ║
║  │ Instalações │ R$ 180.000   │ [📋]        │  ║
║  │ Máquinas    │ R$ 0,00      │ [📋]        │  ║
║  │ Outros      │ R$ 0,00      │ [📋]        │  ║
║  └─────────────┴──────────────┴─────────────┘  ║
║                                                 ║
║  Planilha por Período                           ║
║  ┌──────┬──────┬──────┬────────┬────────┬───   ║
║  │ Cat. │ Item │Total │Jan/2026│Fev/2026│...   ║
║  ├──────┼──────┼──────┼────────┼────────┼───   ║
║  │ CG   │Caixa │50k   │ 50k    │   -    │...   ║
║  │ Imob │Inst. │180k  │ 180k   │   -    │...   ║
║  └──────┴──────┴──────┴────────┴────────┴───   ║
╠════════════════════════════════════════════════╣
║        FONTES DE RECURSOS                       ║
║                                    [+ Adicionar]║
║  ┌─────────┬─────────┬─────────┬──────┬────┐  ║
║  │ Tipo    │ Data    │ Valor   │ Obs  │Ação│  ║
║  ├─────────┼─────────┼─────────┼──────┼────┤  ║
║  │ Sócios  │10/01/26 │200.000  │Cap...│✏️🗑️│  ║
║  └─────────┴─────────┴─────────┴──────┴────┘  ║
╚════════════════════════════════════════════════╝
```

---

## ✅ Checklist de Validação

Após os testes, verifique:

- [ ] Total de Caixa atualiza ao adicionar aporte
- [ ] Planilha mostra valores nos meses corretos
- [ ] Fontes de recursos aparecem na tabela
- [ ] Totais somam corretamente
- [ ] Consegue editar/deletar aportes
- [ ] Console do navegador sem erros (F12)

---

## 🆘 Problemas?

### "Erro ao carregar dados"
→ Execute novamente: `.\APLICAR_INVESTIMENTOS_COMPLETO.bat`

### "Item_id não encontrado"
→ Execute no Docker:
```bash
docker exec -i gestaoversus_app python scripts/seed_investment_items.py
```

### "Modal não abre"
→ Limpe cache: `Ctrl+Shift+R`

### "Totais não atualizam"
→ Verifique console (F12) para erros JavaScript

---

## 📚 Documentação Completa

- **Este guia:** `COMO_USAR_INVESTIMENTOS_AGORA.md`
- **Guia detalhado:** `GUIA_INVESTIMENTOS_DATAS_APORTE.md`
- **Resumo técnico:** `RESUMO_IMPLEMENTACAO_INVESTIMENTOS.md`

---

## 🎉 Pronto!

Agora você tem um sistema completo de gestão de investimentos com:
- ✅ Múltiplos aportes por item
- ✅ Datas de aporte
- ✅ Fontes de recursos
- ✅ Visualização em planilha mensal
- ✅ Totais automáticos

**Boa gestão! 🚀**

