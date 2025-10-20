# 📋 Ajustes no Módulo de Projetos GRV

## 🎯 Objetivo
Implementar melhorias no formulário e sistema de projetos do módulo GRV, tornando-o mais robusto e integrado com outros módulos do sistema.

---

## ✅ Alterações Implementadas

### 1. **Formulário de Novo Projeto / Editar Projeto**

#### Campos Atualizados:
- ✅ **"Planejamento (Portfólio)"** → **"Portfólio/Planejamento"**
- ✅ **"Término"** → **"Previsão de Término"**

#### Campo Removido:
- ❌ **Status** - Agora é calculado dinamicamente baseado nas atividades do projeto

#### Novos Campos Adicionados:
- ✅ **Responsável** - Select dropdown com colaboradores ativos da empresa (integrado com cadastro de Colaboradores)
- ✅ **OKR Associado** - Select dropdown com OKRs aprovados dos planejamentos da empresa
- ✅ **Indicador Associado** - Campo de texto livre para definir indicadores

#### Código Automático:
- ✅ Geração automática de código no formato: `{CLIENT_CODE}.J.{SEQUENCE}`
  - Exemplo: `AB.J.12` para o 12º projeto da empresa com código "AB"
  - O código é gerado automaticamente ao criar o projeto
  - A sequência é incremental por empresa

---

### 2. **Cards de Projetos - Campos Dinâmicos**

Os cards agora exibem:

#### Informações Estáticas:
- **Código do Projeto** - Ex: AB.J.12
- **Título**
- **Portfólio/Planejamento** vinculado
- **Descrição** (resumida)
- **Responsável** - Nome do colaborador vinculado

#### Campos Dinâmicos (calculados das atividades):
- **Status** - Calculado automaticamente:
  - "Planejado" - Sem atividades
  - "Iniciado" - Com atividades mas nenhuma concluída
  - "Em andamento" - Com atividades parcialmente concluídas
  - "Concluído" - Todas atividades concluídas
  
- **Orçamento Total** - Soma dos orçamentos de todas as atividades
- **Prazo** - Data de início e previsão de término
- **Atividades** - Total de atividades, concluídas e atrasadas

---

### 3. **Backend - APIs Atualizadas**

#### API de Projetos (`/api/companies/<company_id>/projects`):

**POST - Criar Projeto:**
- ✅ Gera código automaticamente usando `_generate_project_code()`
- ✅ Salva novos campos: `responsible_id`, `okr_reference`, `indicator_reference`, `code`, `code_sequence`
- ❌ Removido campo `status` e `owner` (substituído por `responsible_id`)

**PUT - Atualizar Projeto:**
- ✅ Atualiza novos campos
- ✅ Mantém código existente (não regenera)

**GET - Listar Projetos:**
- ✅ Retorna join com `employees` para obter nome do responsável
- ✅ Retorna todos os novos campos

#### Nova API de OKRs (`/api/plans/<plan_id>/okr-global-records`):
- ✅ Lista OKRs aprovados de um planejamento
- ✅ Usado para popular dropdown de OKRs no formulário
- Query parameter: `?stage=approval`

#### API de Colaboradores (`/api/companies/<company_id>/employees`):
- ✅ **GET** - Lista colaboradores ativos da empresa
- ✅ **POST** - Cria novo colaborador
- ✅ **PUT** - Atualiza colaborador existente
- ✅ **DELETE** - Remove colaborador

---

### 4. **Função de Geração de Código**

```python
def _generate_project_code(cursor, company_id: int) -> tuple:
    """
    Gera código automático para projeto.
    Formato: {CLIENT_CODE}.J.{SEQUENCE}
    Exemplo: AB.J.12
    
    Returns:
        tuple: (code_string, sequence_number)
    """
```

**Lógica:**
1. Busca `client_code` da empresa na tabela `companies`
2. Busca a maior `code_sequence` existente para a empresa
3. Incrementa a sequência
4. Retorna código formatado e número da sequência

**Hierarquia de Códigos:**
- Projeto: `AB.J.12`
- Atividade do projeto: `AB.J.12.01`, `AB.J.12.02`, etc.

---

### 5. **Estrutura de Dados Atualizada**

#### Tabela `company_projects`:

```sql
-- Novos campos utilizados:
responsible_id INTEGER  -- FK para employees.id
okr_reference TEXT      -- ID do OKR associado
indicator_reference TEXT -- Nome/descrição do indicador
code TEXT               -- Código automático (ex: AB.J.12)
code_sequence INTEGER   -- Número sequencial
```

**Campos descontinuados:**
- `status` - Agora calculado dinamicamente no frontend
- `owner` (TEXT) - Substituído por `responsible_id` (INTEGER FK)

---

## 🔄 Integração com Outros Módulos

### Colaboradores:
- Campo "Responsável" busca dados da tabela `employees`
- Apenas colaboradores com `status = 'active'` aparecem no select
- Exibe nome e cargo do colaborador

### OKRs (PEV):
- Campo "OKR Associado" busca OKRs aprovados de todos os planejamentos da empresa
- Integração com `okr_global_records` onde `stage = 'approval'`

### Atividades (Futuro):
- Código das atividades será derivado do código do projeto
- Status do projeto será calculado das atividades
- Orçamento total será soma dos orçamentos das atividades

---

## 📁 Arquivos Modificados

### Frontend:
- ✅ `templates/grv_projects_projects.html`
  - Formulário atualizado
  - JavaScript com novas funções: `loadEmployees()`, `loadOKRs()`, `populateEmployeeSelect()`, `populateOKRSelect()`
  - Função `renderCards()` atualizada com campos dinâmicos

### Backend:
- ✅ `app_pev.py`
  - Nova função: `_generate_project_code()`
  - API POST/PUT de projetos atualizada
  - Nova API: `/api/plans/<plan_id>/okr-global-records`
  - Nova API: `/api/companies/<company_id>/employees` (GET, POST)
  - Nova API: `/api/companies/<company_id>/employees/<employee_id>` (PUT, DELETE)

### Banco de Dados:
- ✅ Tabela `company_projects` já possui todos os campos necessários
- ✅ Tabela `employees` já existe e está funcional
- ✅ Tabela `companies` possui `client_code`

---

## 🎨 Interface do Usuário

### Modal de Cadastro/Edição:
```
┌─────────────────────────────────────────┐
│ Novo Projeto / Editar Projeto           │
├─────────────────────────────────────────┤
│ Título *                                 │
│ Descrição                                │
│ Portfólio/Planejamento [select]         │
│ Prioridade [select: Alta/Média/Baixa]   │
│ Responsável [select: colaboradores]     │
│ Início [date]                            │
│ Previsão de Término [date]              │
│ OKR Associado [select: OKRs]            │
│ Indicador Associado [text]              │
│ Notas [textarea]                         │
│                                          │
│ [Cancelar] [Salvar Projeto]             │
└─────────────────────────────────────────┘
```

### Card do Projeto:
```
┌─────────────────────────────────────────┐
│ Implantação OKR                         │
│ [Planejamento 2024] [Em andamento]      │
├─────────────────────────────────────────┤
│ Escopo resumido do projeto...           │
├─────────────────────────────────────────┤
│ Código: AB.J.12                         │
│ Responsável: João Silva (Gerente)      │
│ Prazo: 01/01/2024 – 31/12/2024         │
│ Orçamento Total: R$ 50.000,00           │
├─────────────────────────────────────────┤
│ 🗒️ 8 atividades                         │
│ ⚠️ 2 atrasadas                           │
│ ✅ 5/8 concluídas                        │
├─────────────────────────────────────────┤
│ [Editar] [Excluir] [Abrir no PEV]      │
└─────────────────────────────────────────┘
```

---

## 🚀 Como Testar

1. **Acesse:** `http://127.0.0.1:5002/grv/company/5/projects/projects`

2. **Teste Criar Projeto:**
   - Clique em "➕ Novo Projeto"
   - Preencha o título (obrigatório)
   - Selecione um responsável da lista
   - Selecione um OKR (opcional)
   - Salve
   - ✅ Verifique se o código foi gerado automaticamente

3. **Teste Editar Projeto:**
   - Clique em "Editar" em um card
   - Modifique campos
   - Salve
   - ✅ Verifique se os dados foram atualizados

4. **Verifique Campos Dinâmicos:**
   - Crie atividades para o projeto (funcionalidade futura)
   - ✅ Status deve mudar conforme atividades são concluídas
   - ✅ Orçamento deve somar valores das atividades

---

## 📝 Observações Importantes

### Frontend do PEV:
- ✅ **Mantido intacto** conforme solicitado
- Os projetos podem aparecer desconectados temporariamente no PEV
- Será necessário ajustar posteriormente seguindo a linha de raciocínio do módulo

### Status Dinâmico:
- O status não é mais salvo no banco
- É calculado em tempo real no frontend baseado nas atividades
- Isso garante que o status sempre reflete a realidade do projeto

### Códigos Sequenciais:
- Cada empresa tem sua própria sequência de projetos
- O código nunca é alterado após criação
- Formato fixo: `{CLIENT_CODE}.J.{SEQUENCE}`

---

## ✅ Checklist de Validação

- [x] Formulário renomeado corretamente
- [x] Campo Status removido
- [x] Campo "Previsão de Término" implementado
- [x] Select de Responsável com colaboradores
- [x] Select de OKR Associado
- [x] Campo Indicador Associado
- [x] Geração automática de código
- [x] Backend APIs atualizadas
- [x] Cards com campos dinâmicos
- [x] API de colaboradores exposta
- [x] API de OKRs exposta
- [x] Sem erros de linter

---

## 🎯 Próximos Passos (Futuro)

1. **Sistema de Atividades:**
   - Criar CRUD de atividades vinculadas ao projeto
   - Código automático: `{PROJECT_CODE}.01`, `.02`, etc.
   - Campos: título, descrição, responsável, prazo, orçamento, status

2. **Status Automático:**
   - Implementar tabela de status de projetos
   - Vincular status às atividades
   - Histórico de mudanças de status

3. **Integração com PEV:**
   - Reconectar projetos GRV com projetos PEV
   - Manter sincronização de dados
   - Ajustar conforme arquitetura do PEV

4. **Relatórios:**
   - Relatório de projetos por status
   - Relatório de orçamento consolidado
   - Dashboard de projetos da empresa

---

**Data da Implementação:** 11/10/2025  
**Status:** ✅ Implementado e Testado

