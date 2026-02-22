# Resumo: Gestão da Eficiência - Página de Eficiência por Colaborador

**Data**: 11/10/2025  
**Módulo**: GRV - Gestão da Rotina  
**Funcionalidade**: Visualização de eficiência por colaborador

---

## 🎯 Objetivo

Criar uma página na seção de Gestão da Eficiência que mostra dados agregados por colaborador, incluindo:
- Atividades de projetos
- Instâncias de processos
- Ocorrências positivas e negativas

Com totalizadores no topo que obedecem aos filtros aplicados.

---

## ✅ Implementações Realizadas

### 1️⃣ API de Eficiência por Colaborador

**Arquivo**: `app_pev.py` (linhas 1811-1984)

**Endpoint**: 
```
GET /api/companies/{company_id}/efficiency/collaborators
```

**Funcionalidade**:
- Busca todos os colaboradores da empresa
- Para cada colaborador, agrega:
  - **Atividades de Projetos** (onde é responsável)
  - **Instâncias de Processos** (onde está atribuído)
  - **Ocorrências** (positivas e negativas)

**Estrutura de dados retornada**:
```json
[
  {
    "employee_id": 1,
    "employee_name": "João Silva",
    "in_progress": {
      "total": 5,
      "on_time": 3,
      "late": 2
    },
    "completed": {
      "total": 10,
      "on_time": 8,
      "late": 2
    },
    "positive_occurrences": {
      "count": 3,
      "score": 15
    },
    "negative_occurrences": {
      "count": 1,
      "score": -5
    }
  }
]
```

**Lógica de Atrasado**:
- Para **Em Andamento**: Compara `due_date` com hoje
- Para **Concluídos**: Compara `completed_at` com `due_date`

---

### 2️⃣ Template HTML

**Arquivo**: `templates/grv_routine_efficiency.html`

**Características**:
- Layout similar à página de atividades de rotina
- Sidebar com navegação GRV
- Cards de estatísticas no topo
- Grid de colaboradores

**Componentes principais**:

#### Cards de Estatísticas (Topo)
- Em Andamento (total, no prazo, atrasadas)
- Concluídas (total, no prazo, atrasadas)
- Ocorrências Positivas (quantidade, pontuação)
- Ocorrências Negativas (quantidade, pontuação)

Os totais são **calculados dinamicamente** com base nos dados filtrados.

#### Filtros
- Buscar por nome de colaborador
- Filtrar por tipo (todos, com atividades, com ocorrências)
- Botão limpar filtros

#### Cards de Colaborador
Cada card mostra:
- Nome do colaborador
- Total de atividades e ocorrências

**4 caixas de métricas**:
1. **Em Andamento** (azul)
   - Total
   - No prazo
   - Atrasadas

2. **Concluídas** (verde)
   - Total
   - No prazo
   - Atrasadas

3. **Ocorrências Positivas** (verde)
   - Quantidade
   - Pontuação

4. **Ocorrências Negativas** (vermelho)
   - Quantidade
   - Pontuação

---

### 3️⃣ Rota GRV

**Arquivo**: `modules/grv/__init__.py` (linha 643-646)

**URL**: 
```
/grv/company/{company_id}/routine/efficiency
```

A rota já estava implementada, apenas renderiza o template com os dados básicos (company, navigation).

**Navegação**:
- Acessível via sidebar GRV → Gestão da Rotina → Gestão da Eficiência

---

## 🎨 Design e UX

### Visual
- Cards com bordas coloridas à esquerda para indicar tipo de métrica
- Cores consistentes:
  - 🔵 Azul: Em andamento
  - 🟢 Verde: Concluído/Positivo
  - 🔴 Vermelho: Atrasado/Negativo
- Hover effects nos cards
- Responsive design

### Funcionalidades JavaScript
- Carregamento assíncrono via API
- Filtragem em tempo real
- Atualização dinâmica dos totalizadores
- Estado de filtros salvo em localStorage
- Empty states informativos

---

## 📊 Métricas Calculadas

### Atividades em Andamento
- **Origem**: 
  - Atividades de projetos com `stage in ['executing', 'waiting']`
  - Instâncias de processos com `status in ['in_progress', 'executing']`
- **Em dia**: `due_date >= hoje`
- **Atrasadas**: `due_date < hoje`

### Atividades Concluídas
- **Origem**: 
  - Atividades de projetos com `stage = 'completed'`
  - Instâncias de processos com `status = 'completed'`
- **Em dia**: `completed_at <= due_date`
- **Atrasadas**: `completed_at > due_date`

### Ocorrências
- **Positivas**: `type = 'positive'`
- **Negativas**: `type = 'negative'`
- **Pontuação**: Soma dos scores de todas as ocorrências do tipo

---

## 🔗 Integração

### APIs Utilizadas
- `/api/companies/{company_id}/efficiency/collaborators` (nova)

### Tabelas do Banco
- `employees`
- `company_projects` (coluna `activities` JSON)
- `process_instances`
- `occurrences`

---

## 🚀 Como Usar

1. Acesse: `http://127.0.0.1:5002/grv/company/{company_id}/routine/efficiency`
2. Visualize os totalizadores no topo (soma de todos os colaboradores)
3. Use os filtros para encontrar colaboradores específicos
4. Analise as métricas individuais de cada colaborador
5. Os totalizadores se atualizam automaticamente conforme os filtros

---

## 📌 Observações

- A página **só considera** atividades e processos onde o colaborador está envolvido (responsável ou executor)
- Os filtros afetam tanto a listagem quanto os totalizadores
- A pontuação de ocorrências pode ser positiva ou negativa
- Colaboradores sem atividades aparecem na lista (podem ser filtrados)

---

## ✨ Próximas Melhorias Possíveis

1. Adicionar gráficos de desempenho
2. Comparação entre colaboradores
3. Exportação de relatórios
4. Filtros por período de tempo
5. Drill-down para ver detalhes das atividades
6. Ranking de eficiência

---

## 🎉 Status

**IMPLEMENTAÇÃO CONCLUÍDA E TESTADA** ✅

A página está funcional e pronta para uso no endereço:
`http://127.0.0.1:5002/grv/company/{company_id}/routine/efficiency`


