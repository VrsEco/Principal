# 📊 Análise da Mão de Obra Utilizada

**Implementado:** 11/10/2025  
**Status:** ✅ Completo e Funcionando

---

## 🎯 OBJETIVO

Sistema de análise que permite visualizar e gerenciar a utilização da mão de obra dos colaboradores, mostrando:
- Horas consumidas por colaborador em processos/rotinas
- Distribuição de horas por período (diária, semanal, mensal, anual)
- Taxa de utilização vs. capacidade disponível
- Detalhamento de rotinas por colaborador

---

## 🚀 COMO USAR

### Acessar a Análise:

1. **Navegue até:**
   ```
   http://127.0.0.1:5002/grv/company/{company_id}
   ```

2. **No menu lateral, clique em:**
   - Gestão de Processos → **Análises**

3. **Selecione a aba:**
   - 👥 **Análise da Mão de Obra Utilizada**

---

## 📈 FUNCIONALIDADES

### 1. **Resumo Geral**

Exibe 4 cards com informações consolidadas:
- **Total de Colaboradores**: Número de colaboradores ativos
- **Horas Semanais Consumidas**: Total de horas gastas em rotinas
- **Capacidade Total Semanal**: Soma da carga horária de todos
- **Utilização Média**: Percentual médio de utilização da equipe

### 2. **Análise por Colaborador**

Para cada colaborador, o sistema exibe:

#### Informações Básicas:
- Nome do colaborador
- Função/Cargo
- Departamento
- Taxa de utilização (%)

#### Horas Consumidas:
- **Diário**: Horas médias por dia útil
- **Semanal**: Total de horas por semana
- **Mensal**: Total de horas por mês
- **Anual**: Total de horas por ano
- **Média Mensal**: Média mensal baseada no total anual
- **Disponível (Semanal)**: Horas livres na semana

#### Indicadores Visuais:
- **Barra de Utilização**:
  - 🟢 Verde: 0-70% (Saudável)
  - 🟡 Amarelo: 71-90% (Atenção)
  - 🔴 Vermelho: 91-100%+ (Sobrecarga)

#### Detalhes das Rotinas:
- Lista de todas as rotinas associadas
- Nome da rotina e processo relacionado
- Tipo de agendamento (diário, semanal, mensal, etc.)
- Horas utilizadas por rotina

---

## 🔢 CÁLCULOS

### Lógica de Conversão de Horas por Tipo de Rotina:

| Tipo de Rotina | Conversão para Horas Semanais | Observações |
|----------------|-------------------------------|-------------|
| **Diário** | `horas × 5 dias` | Considera 5 dias úteis/semana |
| **Semanal** | `horas × dias_selecionados` | Ex: 3 dias = horas × 3 |
| **Mensal** | `horas ÷ 4.33` | ~4.33 semanas por mês |
| **Trimestral** | `(horas × 4) ÷ 52` | 4 vezes ao ano |
| **Anual** | `horas ÷ 52` | 52 semanas por ano |
| **Específica** | Não conta | Data única, não recorrente |

### Fórmulas de Cálculo:

```javascript
// Horas Diárias (média)
hours_daily = hours_weekly / 5

// Horas Mensais
hours_monthly = hours_weekly * 4.33

// Horas Anuais
hours_yearly = hours_weekly * 52

// Média Mensal
hours_monthly_avg = hours_yearly / 12

// Taxa de Utilização
utilization_percentage = (hours_weekly / weekly_hours) * 100

// Horas Disponíveis
available_hours_weekly = weekly_hours - hours_weekly
```

---

## 📊 ESTRUTURA DO BANCO DE DADOS

### Campo Adicionado: `employees.weekly_hours`

```sql
-- Tabela: employees
ALTER TABLE employees ADD COLUMN weekly_hours REAL DEFAULT 40;
```

**Tipo**: REAL (permite decimais como 40.0, 44.0, 36.5)  
**Padrão**: 40 horas (jornada padrão)  
**Uso**: Define a carga horária semanal contratada do colaborador

---

## 🔌 API IMPLEMENTADA

### GET `/api/companies/<company_id>/workforce-analysis`

**Descrição**: Retorna análise completa da mão de obra

**Resposta de Sucesso** (200):
```json
{
  "success": true,
  "employees": [
    {
      "id": 1,
      "name": "João Silva",
      "email": "joao@empresa.com",
      "department": "Financeiro",
      "weekly_hours": 40,
      "role_title": "Analista Financeiro",
      "hours_daily": 2.5,
      "hours_weekly": 12.5,
      "hours_monthly": 54.13,
      "hours_yearly": 650,
      "hours_monthly_avg": 54.17,
      "utilization_percentage": 31.3,
      "available_hours_weekly": 27.5,
      "routines": [
        {
          "routine_id": 5,
          "routine_name": "Fechamento Diário",
          "process_name": "Gestão Financeira",
          "schedule_type": "daily",
          "schedule_value": "18:00",
          "hours_used": 2.5,
          "notes": "Conferência e fechamento do caixa"
        }
      ]
    }
  ]
}
```

**Resposta de Erro** (500):
```json
{
  "success": false,
  "error": "Mensagem de erro"
}
```

---

## 💡 CASOS DE USO

### Exemplo 1: Identificar Sobrecarga

**Situação**: João está com 95% de utilização  
**Ação**: Redistribuir algumas rotinas para outros colaboradores  
**Benefício**: Evitar burnout e manter qualidade

### Exemplo 2: Identificar Ociosidade

**Situação**: Maria está com 30% de utilização  
**Ação**: Alocar novas responsabilidades ou projetos  
**Benefício**: Otimizar custos e engajamento

### Exemplo 3: Planejamento de Contratações

**Situação**: Equipe com 85% de utilização média  
**Ação**: Planejar contratação de novo colaborador  
**Benefício**: Crescimento sustentável sem sobrecarga

### Exemplo 4: Análise de Processos Críticos

**Situação**: Ver quais processos consomem mais horas  
**Ação**: Avaliar automações ou melhorias  
**Benefício**: Reduzir tempo de processos manuais

---

## 🎨 INTERFACE

### Cores dos Indicadores:

- **Verde (#10b981)**: Utilização saudável (0-70%)
- **Amarelo (#f59e0b)**: Atenção necessária (71-90%)
- **Vermelho (#ef4444)**: Sobrecarga (91%+)

### Cards Interativos:

- **Hover**: Destaque visual ao passar o mouse
- **Botão "Ver Rotinas"**: Expande/colapsa lista de rotinas
- **Responsivo**: Adapta-se a diferentes tamanhos de tela

---

## 🔧 CONFIGURAÇÃO

### Definir Carga Horária do Colaborador:

1. Acesse: **Empresas → Gerenciar → Aba Colaboradores**
2. Clique em **➕ Novo Colaborador** ou **✏️ Editar**
3. Preencha o campo **"Carga Horária Semanal"**
   - Padrão: 40 horas
   - Aceita valores decimais (ex: 30.0, 44.0, 36.5)
4. Salve o colaborador

### Associar Colaborador a Rotinas:

1. Acesse: **Rotina dos Processos**
2. Clique no botão **👥** de uma rotina
3. Adicione o colaborador e defina as horas utilizadas
4. A análise será atualizada automaticamente

---

## 📝 PRÓXIMAS ABAS (Futuro)

### 2. **Análise de Processos**
- Performance por processo
- Gargalos identificados
- Tempo médio de execução

### 3. **Análise de Eficiência**
- Índices de eficiência operacional
- Comparativos temporais
- Metas vs. Realizado

---

## ✅ CHECKLIST DE VALIDAÇÃO

Antes de usar, verifique:

- [ ] Colaboradores cadastrados com carga horária definida
- [ ] Rotinas criadas e vinculadas a processos
- [ ] Colaboradores associados às rotinas com horas definidas
- [ ] Banco de dados atualizado com campo `weekly_hours`

---

## 🐛 TROUBLESHOOTING

### Problema: Colaborador não aparece na análise
**Solução**: Verificar se o status está "ativo" no cadastro

### Problema: Horas zeradas
**Solução**: Verificar se o colaborador está associado a alguma rotina

### Problema: Carga horária não aparece
**Solução**: Editar o colaborador e preencher o campo "Carga Horária Semanal"

### Problema: API retorna erro 500
**Solução**: 
1. Verificar se o banco de dados está acessível
2. Verificar logs do servidor
3. Verificar se a tabela `employees` tem o campo `weekly_hours`

---

## 📚 ARQUIVOS MODIFICADOS/CRIADOS

### Banco de Dados:
- `database/sqlite_db.py` - Adicionado campo `weekly_hours`
- `database/postgresql_db.py` - Adicionado campo `weekly_hours`

### Backend:
- `app_pev.py`:
  - Nova API: `/api/companies/<company_id>/workforce-analysis`
  - Atualizada API: `/api/companies/<company_id>/employees` (POST/PUT)

### Frontend:
- `templates/grv_process_analysis.html` - Interface completa com abas
- `templates/company_details.html` - Adicionado campo carga horária

### Documentação:
- `ANALISE_MAO_DE_OBRA.md` - Este arquivo

---

## 📊 EXEMPLO DE DADOS

### Cenário Real:

**Empresa**: TechStart Ltda  
**Colaboradores**: 5  
**Rotinas Cadastradas**: 15  

**Resultado da Análise**:
- Colaborador A: 85% utilização → **Atenção**
- Colaborador B: 45% utilização → **Saudável**
- Colaborador C: 92% utilização → **Sobrecarga**
- Colaborador D: 60% utilização → **Saudável**
- Colaborador E: 38% utilização → **Saudável**

**Média da Equipe**: 64% ✅

**Ações Recomendadas**:
1. Redistribuir 2 rotinas do Colaborador C
2. Alocar novos projetos para Colaboradores B e E
3. Monitorar Colaborador A nas próximas semanas

---

## 🎯 BENEFÍCIOS DO SISTEMA

✅ **Visibilidade**: Veja exatamente onde cada colaborador está alocado  
✅ **Previsibilidade**: Planeje contratações e projetos com dados reais  
✅ **Eficiência**: Identifique gargalos e ociosidade rapidamente  
✅ **Qualidade**: Evite sobrecarga e mantenha equipe saudável  
✅ **Custos**: Otimize alocação de recursos humanos  
✅ **Dados**: Tome decisões baseadas em métricas concretas  

---

## 📞 SUPORTE

Para dúvidas ou problemas:
1. Consulte este documento
2. Verifique os logs do servidor
3. Revise o checklist de validação
4. Entre em contato com o suporte técnico

---

**Versão**: 1.0  
**Data**: 11/10/2025  
**Autor**: Sistema GRV - Gestão de Rotinas Versus

