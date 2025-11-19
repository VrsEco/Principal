# Análise Comparativa de Indicadores - GRV

## 📋 Visão Geral

A página de **Análises Comparativas de Indicadores** foi totalmente redesenhada para permitir análises avançadas com comparação de múltiplos indicadores e metas em um único gráfico.

## 🎯 Funcionalidades Implementadas

### 1. Seleção Múltipla de Indicadores
- Interface visual com cards expansíveis
- Checkbox para selecionar/desselecionar indicadores
- Exibição automática das metas quando um indicador é selecionado

### 2. Seleção de Metas por Indicador
- Para cada indicador selecionado, você pode escolher uma ou mais metas
- Cada meta exibe:
  - Código da meta
  - Tipo da meta (única, diária, semanal, mensal, trimestral, semestral, anual)
  - Valor da meta
  - Período da meta (se aplicável)

### 3. Filtros de Período
- **Data Início**: Define o início do período de análise
- **Data Fim**: Define o fim do período de análise
- **Visualização**: Escolha como agregar os dados
  - Todos os Pontos: Mostra cada medição individualmente
  - Agregado por Mês: Agrupa medições por mês
  - Agregado por Trimestre: Agrupa medições por trimestre

### 4. Gráfico Comparativo
- Visualização de múltiplas séries temporais no mesmo gráfico
- Cada indicador/meta tem uma cor diferente
- Linhas de meta tracejadas para metas únicas
- Tooltips informativos ao passar o mouse
- Legenda clicável para ocultar/exibir séries

### 5. Tabela de Estatísticas
Após gerar a análise, uma tabela comparativa exibe:
- **Indicador / Meta**: Identificação da série
- **Valor da Meta**: Meta estabelecida
- **Média Realizada**: Média dos valores medidos no período
- **Última Medição**: Valor mais recente
- **Total Medições**: Quantidade de registros no período
- **Performance**: Indicador visual se a meta foi atingida

## 🚀 Como Usar

### Passo 1: Selecionar Indicadores
1. Acesse a página em: `http://127.0.0.1:5002/grv/company/5/indicators/analysis`
2. Na seção "Seleção de Indicadores e Metas", marque os checkboxes dos indicadores desejados
3. Os cards expandem automaticamente ao selecionar um indicador

### Passo 2: Selecionar Metas
1. Dentro de cada indicador selecionado, aparecerão as metas disponíveis
2. Marque as metas que deseja comparar
3. Você pode selecionar múltiplas metas do mesmo indicador ou de indicadores diferentes

### Passo 3: Definir Período (Opcional)
1. Defina a **Data Início** e **Data Fim** para filtrar o período
2. Escolha o modo de **Visualização** (todos os pontos ou agregado)
3. Se não definir, todos os dados disponíveis serão exibidos

### Passo 4: Gerar Análise
1. Clique no botão **"Gerar Análise Comparativa"**
2. O gráfico e a tabela de estatísticas serão exibidos
3. Analise as tendências e compare os indicadores

## 💡 Casos de Uso

### Caso 1: Comparar Indicadores de Diferentes Processos
Selecione indicadores de processos distintos com suas respectivas metas para identificar qual processo está performando melhor.

### Caso 2: Comparar Metas Diferentes do Mesmo Indicador
Selecione um único indicador mas múltiplas metas (por exemplo, meta mensal vs. meta trimestral) para avaliar diferentes estratégias.

### Caso 3: Análise de Tendência de Múltiplos Indicadores
Selecione vários indicadores relacionados e compare suas evoluções ao longo do tempo para identificar padrões.

### Caso 4: Análise de Performance por Período
Use os filtros de período para focar em trimestres, semestres ou anos específicos.

## 📊 Agregação de Dados

Quando você escolhe uma visualização agregada, o sistema calcula os valores baseado na **forma de avaliação** definida na meta:

- **Soma do Período**: Soma todos os valores do período
- **Média do Período**: Calcula a média dos valores
- **Último Valor**: Pega apenas o último registro do período
- **Valor Pontual**: Para metas únicas, usa o valor individual

## 🎨 Recursos Visuais

- **Cores Diferenciadas**: Cada série tem uma cor única (até 10 cores diferentes, depois repete)
- **Linhas de Meta**: Metas únicas são exibidas como linhas tracejadas
- **Indicadores de Cor**: A tabela de estatísticas mostra a cor correspondente de cada série
- **Badges de Performance**: 
  - ✓ Verde: Meta atingida
  - ✗ Vermelho: Meta não atingida
  - — Cinza: Não aplicável

## 🔧 Detalhes Técnicos

### Tipos de Meta Suportados
- `single`: Meta Única (com data específica)
- `daily`: Meta Diária
- `weekly`: Meta Semanal
- `monthly`: Meta Mensal
- `quarterly`: Meta Trimestral
- `biannual`: Meta Semestral
- `annual`: Meta Anual

### APIs Utilizadas
- `GET /grv/api/company/{company_id}/indicators` - Lista todos os indicadores
- `GET /grv/api/company/{company_id}/indicator-goals` - Lista todas as metas
- `GET /grv/api/company/{company_id}/indicator-data` - Lista todos os registros de dados

### Bibliotecas JavaScript
- **Chart.js 4.4.0**: Para renderização dos gráficos
- **chartjs-adapter-date-fns**: Para manipulação de datas no gráfico

## 📝 Observações Importantes

1. **Mínimo de Seleção**: É necessário selecionar pelo menos uma meta para gerar a análise
2. **Dados Filtrados**: Apenas os dados dentro do período selecionado são exibidos
3. **Performance**: A análise de performance só é calculada para metas únicas ou com avaliação pontual
4. **Polaridade**: O cálculo de performance considera a polaridade do indicador (se maior é melhor ou menor é melhor)

## 🎯 Próximos Passos

A funcionalidade está completa e pronta para uso. Possíveis melhorias futuras:
- Export de gráficos como imagem
- Export de dados em CSV/Excel
- Análise de correlação entre indicadores
- Previsões e tendências usando machine learning
- Salvamento de análises favoritas

---

**Página**: `http://127.0.0.1:5002/grv/company/{company_id}/indicators/analysis`

**Navegação**: GRV → Gestão de Indicadores → Análises

