# 🚀 Guia Rápido - Análise Comparativa de Indicadores

## 📍 Como Acessar

1. Navegue para: `http://127.0.0.1:5002/grv/company/5/indicators/analysis`
2. Ou pelo menu: **GRV** → **Gestão de Indicadores** → **Análises**

---

## 🎯 Passo a Passo Simples

### PASSO 1: Selecionar Indicadores

```
┌─────────────────────────────────────────────┐
│ 🎯 SELEÇÃO DE INDICADORES E METAS          │
├─────────────────────────────────────────────┤
│                                             │
│  ☑️ AA.I.1.001                              │
│     Taxa de Conversão de Vendas             │
│     ├─ ☑️ META-0001 - Meta Mensal: 85%     │
│     └─ ☐ META-0002 - Meta Trimestral: 90%  │
│                                             │
│  ☑️ AA.I.2.003                              │
│     Tempo Médio de Atendimento              │
│     ├─ ☐ META-0005 - Meta Mensal: 15 min   │
│     └─ ☑️ META-0006 - Meta Semanal: 12 min │
│                                             │
│  ☐ AA.I.3.007                               │
│     Satisfação do Cliente                   │
│                                             │
└─────────────────────────────────────────────┘
```

**Ações**:
- Clique no **checkbox do indicador** para selecioná-lo
- O card **expande automaticamente** mostrando as metas
- Marque as **metas** que deseja comparar

---

### PASSO 2: Definir Período

```
┌─────────────────────────────────────────────┐
│ 📅 PERÍODO DE ANÁLISE                       │
├─────────────────────────────────────────────┤
│                                             │
│  Data Início: [01/04/2025]                  │
│  Data Fim:    [13/10/2025]                  │
│  Visualização: [Agregado por Mês ▼]         │
│                                             │
│  [Limpar Seleção] [Gerar Análise Comparativa]│
└─────────────────────────────────────────────┘
```

**Ações**:
- Defina **Data Início** e **Data Fim** (ou deixe em branco para todos os dados)
- Escolha o **modo de visualização**:
  - **Todos os Pontos**: Cada medição individual
  - **Agregado por Mês**: Agrupa por mês
  - **Agregado por Trimestre**: Agrupa por trimestre
- Clique em **"Gerar Análise Comparativa"**

---

### PASSO 3: Visualizar Resultados

#### 📈 Gráfico Comparativo

```
┌─────────────────────────────────────────────┐
│ 📈 EVOLUÇÃO COMPARATIVA                     │
├─────────────────────────────────────────────┤
│                                             │
│  100% ┤                     ╱────           │
│       │                  ╱─╱                │
│   85% ┼─────────────────●  ← Meta           │
│       │            ╱─●─╱                    │
│   70% ┤       ╱─●─╱                         │
│       │  ●─●─╱                              │
│   50% ┼───────────────────────────────      │
│       └─┬────┬────┬────┬────┬────┬──→      │
│        Abr  Mai  Jun  Jul  Ago  Set         │
│                                             │
│  Legenda:                                   │
│  ━━ AA.I.1.001 - META-0001 (Taxa Conv.)     │
│  ━━ AA.I.2.003 - META-0006 (Tempo Atend.)   │
│  ╌╌ Meta: AA.I.1.001                        │
└─────────────────────────────────────────────┘
```

---

#### 📋 Tabela de Estatísticas

```
┌────────────────────────────────────────────────────────────────┐
│ 📋 ESTATÍSTICAS COMPARATIVAS                                  │
├─────────────────┬──────┬─────────┬─────────┬────────┬─────────┤
│ Indicador/Meta  │ Meta │  Média  │ Última  │ Medições│ Perform.│
├─────────────────┼──────┼─────────┼─────────┼────────┼─────────┤
│ 🔵 AA.I.1.001   │      │         │         │        │         │
│ META-0001       │ 85%  │  82.5%  │  88.3%  │   24   │ ✓ Atingiu│
│ (Meta Mensal)   │      │         │         │        │         │
├─────────────────┼──────┼─────────┼─────────┼────────┼─────────┤
│ 🟢 AA.I.2.003   │      │         │         │        │         │
│ META-0006       │ 12min│ 13.2min │ 11.8min │   26   │ ✓ Atingiu│
│ (Meta Semanal)  │      │         │         │        │         │
└─────────────────┴──────┴─────────┴─────────┴────────┴─────────┘
```

**Informações na Tabela**:
- **🔵/🟢**: Cor da série no gráfico
- **Meta**: Valor alvo estabelecido
- **Média**: Média de todas as medições no período
- **Última**: Valor da medição mais recente
- **Medições**: Quantidade de registros
- **Performance**: ✓ (verde) ou ✗ (vermelho)

---

## 💡 Dicas e Truques

### ✨ Comparando Estratégias de Meta

**Cenário**: Quer saber se uma meta mensal é mais realista que uma trimestral?

1. Selecione **um único indicador**
2. Marque **ambas as metas** (mensal E trimestral)
3. Gere a análise
4. Compare visualmente no gráfico qual meta está sendo mais atingida

---

### 🔍 Identificando Correlações

**Cenário**: Suspeita que o tempo de atendimento afeta a satisfação?

1. Selecione **Tempo de Atendimento** e **Satisfação**
2. Escolha metas do mesmo período
3. No gráfico, observe se quando um sobe o outro desce (ou vice-versa)

---

### 📊 Análise de Tendência

**Cenário**: Precisa saber se os indicadores estão melhorando ao longo do tempo?

1. Selecione múltiplos indicadores
2. Defina um **período longo** (ex: 12 meses)
3. Use **Agregado por Mês** ou **Trimestre**
4. Observe as linhas: subindo ✅ ou descendo ❌

---

### 🎯 Foco em Períodos Específicos

**Cenário**: Análise apenas do último trimestre

1. **Data Início**: Primeiro dia do trimestre
2. **Data Fim**: Hoje
3. **Visualização**: Todos os Pontos (para ver detalhe)

---

## ⚙️ Configurações Avançadas

### Tipos de Meta e Como Funcionam

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| **Meta Única** | Um valor alvo em data específica | Atingir 100 vendas até 31/12 |
| **Meta Diária** | Valor alvo por dia | 10 vendas por dia |
| **Meta Semanal** | Valor alvo por semana | 50 vendas por semana |
| **Meta Mensal** | Valor alvo por mês | 200 vendas por mês |
| **Meta Trimestral** | Valor alvo por trimestre | 600 vendas por trimestre |
| **Meta Semestral** | Valor alvo por semestre | 1200 vendas por semestre |
| **Meta Anual** | Valor alvo por ano | 2400 vendas por ano |

---

### Formas de Avaliação

| Forma | Quando Usar | Como Calcula |
|-------|-------------|--------------|
| **Valor Pontual** | Metas únicas, comparação direta | Compara valor com meta |
| **Soma** | Metas de volume (vendas, produção) | Soma todos os valores do período |
| **Média** | Metas de taxa, percentual | Média dos valores |
| **Último Valor** | Status atual mais importante | Considera só o último registro |

---

## 🎨 Personalizações Visuais

### Cores das Séries

O sistema usa 10 cores diferentes:
1. 🔵 Azul (`#3b82f6`)
2. 🟢 Verde (`#10b981`)
3. 🟡 Âmbar (`#f59e0b`)
4. 🟣 Roxo (`#8b5cf6`)
5. 🔴 Vermelho (`#ef4444`)
6. 🔷 Ciano (`#06b6d4`)
7. 🟢 Lima (`#84cc16`)
8. 🟠 Laranja (`#f97316`)
9. 🩷 Pink (`#ec4899`)
10. 🔵 Teal (`#14b8a6`)

Após a 10ª série, as cores se repetem.

---

### Interatividade do Gráfico

**Hover (passar o mouse)**:
- Mostra valores exatos
- Destaca a série

**Clique na legenda**:
- Oculta/exibe a série
- Útil para focar em séries específicas

**Zoom** (futuro):
- Scroll para zoom
- Arrastar para pan

---

## 🚨 Solução de Problemas

### ❌ Gráfico não aparece

**Possíveis causas**:
1. Nenhuma meta selecionada → Selecione pelo menos uma meta
2. Nenhum dado no período → Verifique se há registros de medições
3. Período muito restrito → Expanda o período

**Solução**: Siga o alerta amarelo no topo da página

---

### ⚠️ Não vejo minhas metas

**Possíveis causas**:
1. Indicador não selecionado → Marque o checkbox do indicador
2. Nenhuma meta cadastrada → Cadastre metas primeiro

**Solução**: Vá para **Gestão de Indicadores → Metas** e crie metas

---

### 📉 Performance sempre "—"

**Causa**: A meta não é do tipo "única" ou não tem avaliação "valor pontual"

**Explicação**: Performance só é calculada para comparações diretas (metas únicas)

**Solução**: Normal para metas de soma, média ou agregadas

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Consulte `ANALISE_COMPARATIVA_INDICADORES.md` (documentação completa)
2. Verifique `RESUMO_ANALISE_INDICADORES.md` (detalhes técnicos)
3. Entre em contato com o suporte técnico

---

## 🎉 Pronto!

Agora você está pronto para usar a **Análise Comparativa de Indicadores**!

**Boa análise!** 📊✨

---

**Última atualização**: 13/10/2025  
**Versão**: 1.0

