# 🚀 Guia Rápido - ModeFin

**URL:** `http://localhost:5003/pev/implantacao/modelo/modefin?plan_id=6`

---

## 📊 8 SEÇÕES - O QUE CADA UMA FAZ

### 1️⃣ **Resultados** (Verde)
**O que faz:** Mostra margem de contribuição e resultado operacional  
**Ação:** Visualizar valores (dados vêm de Produtos e Estruturas)

### 2️⃣ **Investimentos** (Roxo)
**O que faz:** Gerencia capital de giro e mostra imobilizado  
**Ação:** Clique `+ Capital de Giro` → Cadastre Caixa, Recebíveis, Estoques

### 3️⃣ **Fontes de Recursos** (Verde Escuro)
**O que faz:** Gerencia fontes de financiamento  
**Ação:** Clique `+ Nova Fonte` → Cadastre Capital Próprio, Empréstimos, etc

### 4️⃣ **Distribuição de Lucros** (Laranja)
**O que faz:** Define % de distribuição e outras destinações  
**Ações:**
- Clique no **card "Distribuição"** → Configure %
- Clique `+ Nova Destinação` → Reservas, fundos (% ou fixo)

### 5️⃣ **Fluxo Investimento** (Azul Claro)
**O que faz:** Mostra investimentos vs fontes mês a mês  
**Ação:** Visualizar (calculado automaticamente)

### 6️⃣ **Fluxo Negócio** (Verde Água)
**O que faz:** Projeta receitas, custos e resultado por 60 meses  
**Ação:** Visualizar e rolar tabela (scroll vertical)  
**Tem:** 11 colunas, 60 meses, 3 acumulados

### 7️⃣ **Fluxo Investidor** (Roxo Escuro)
**O que faz:** Mostra perspectiva do investidor (60 meses)  
**Ação:** Visualizar recuperação do investimento

### 8️⃣ **Análise** (Rosa)
**O que faz:** Calcula métricas de viabilidade  
**Ações:**
- Clique `⚙️ Configurar Análise` → Período e Custo Oportunidade
- Clique `✏️ Editar Resumo` → Texto para relatório

---

## ⚡ AÇÕES RÁPIDAS

### Cadastrar Investimento:
1. Seção 2 → `+ Capital de Giro`
2. Tipo: Caixa | Data: 01/05/2026 | Valor: 100000
3. Salvar

### Cadastrar Fonte:
1. Seção 3 → `+ Nova Fonte`
2. Tipo: Capital Próprio | Valor: 500000
3. Salvar

### Configurar Distribuição:
1. Seção 4 → Clique no card "Distribuição (0%)"
2. Percentual: 30 | Data início: 01/06/2026
3. Salvar

### Adicionar Reserva:
1. Seção 4 → `+ Nova Destinação`
2. Descrição: Reserva | Tipo: Percentual | Valor: 10%
3. Data início: 01/07/2026
4. Salvar

### Configurar Análise:
1. Seção 8 → `⚙️ Configurar Análise`
2. Período: 60 meses | Custo: 12%
3. Salvar

---

## 🎯 VALORES IMPORTANTES

### Com seus dados atuais:
- **Faturamento Mensal:** R$ 1.200.000
- **Margem:** R$ 816.000 (68%)
- **Custos Fixos:** R$ 65.400
- **Despesas Fixas:** R$ 8.800
- **Resultado Operacional:** R$ 741.800
- **Total Investimentos:** R$ 448.500 (+ capital giro)

---

## ⚠️ REGRAS IMPORTANTES

1. **Destinações %:** Só aplicam se resultado POSITIVO
2. **Datas de início:** Destinações só aplicam após a data configurada
3. **Faturamento:** Já é mensal (não precisa multiplicar)
4. **Scroll:** Fluxos 6 e 7 têm 60 linhas (use scroll vertical)

---

## 🐛 SE ALGO NÃO FUNCIONAR

### Modal não aparece:
1. `Ctrl + F5` (force reload)
2. Verifique console (F12)
3. Veja `MODAL_STANDARDS.md`

### Erro ao salvar:
1. Verifique logs: `docker-compose logs app`
2. Confirme que tabelas existem
3. Reinicie: `docker-compose restart app`

### Valores errados:
1. Verifique dados em Produtos e Estruturas
2. Recarregue página: `F5`
3. Verifique console para erros

---

**📖 Documentação completa:** `MODEFIN_IMPLEMENTACAO_COMPLETA_FINAL.md`

**🎉 Aproveite o ModeFin!** 🚀

