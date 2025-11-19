# Sistema de Gestão de Reuniões

## Visão Geral

O Sistema de Gestão de Reuniões foi desenvolvido para gerenciar todo o ciclo de vida das reuniões da empresa, desde o convite inicial até o acompanhamento das atividades geradas.

## Arquitetura do Sistema

### Três Momentos de Registro

1. **Convite** - Planejamento inicial da reunião
2. **Reunião** - Registro durante ou logo após a reunião
3. **Atividades Criadas** - Acompanhamento pós-reunião

## Estrutura de Dados

### Campos da Reunião

#### Informações Básicas
- **Título da Reunião** - Nome descritivo da reunião
- **Data** - Data agendada para a reunião
- **Horário** - Hora de início da reunião
- **Responsável** - Pessoa responsável pela organização

#### Convidados (Fase: Convite)
- **Convidados Internos** - Lista de colaboradores da empresa
- **Convidados Externos** - Lista de pessoas externas à empresa
- **Observações do Convite** - Informações adicionais sobre o convite

#### Pauta (Fase: Convite)
- **Tópicos da Pauta** - Lista de assuntos a serem discutidos

#### Participantes (Fase: Reunião)
- **Participantes Internos** - Colaboradores que efetivamente participaram
- **Participantes Externos** - Externos que efetivamente participaram
- **Notas da Reunião** - Observações gerais da reunião

#### Discussões (Fase: Reunião)
- **Tópico da Discussão** - Assunto discutido
- **Texto da Discussão** - Descrição detalhada e definições tomadas

#### Atividades (Fase: Atividades Criadas)
- **Título da Atividade** - Nome da tarefa
- **Responsável** - Pessoa designada
- **Prazo** - Data limite para conclusão
- **Status** - Estado atual (pending, in_progress, completed, cancelled)

## Integração com Projetos

### Criação Automática de Projeto

Ao criar uma reunião, o sistema **automaticamente cria um projeto vinculado** com:

- **Título do Projeto**: `Reunião [Nome da Reunião] - YYYY.MM.DD`
- **Descrição**: Gerada automaticamente mencionando a reunião
- **Status**: Planned
- **Prioridade**: Medium
- **Código**: Gerado automaticamente (ex: `EMP.J.001`)

### Estrutura do Projeto de Reunião

O projeto criado contém:

1. **Card de Resumo** - Primeiro card com informações consolidadas:
   - Convidados
   - Pauta
   - Discussões e Definições
   - Atividades Criadas

2. **Atividades do Projeto** - Cada atividade criada na reunião se torna uma atividade do projeto, permitindo:
   - Acompanhamento centralizado
   - Gestão de prazos
   - Atribuição de responsáveis
   - Controle de status

## Estrutura de Arquivos

### Backend

#### Database (`database/sqlite_db.py`)
```python
# Funções implementadas:
- list_company_meetings(company_id)      # Lista reuniões de uma empresa
- get_meeting(meeting_id)                # Busca reunião específica
- create_meeting(company_id, data)       # Cria nova reunião + projeto
- update_meeting(meeting_id, data)       # Atualiza reunião
- delete_meeting(meeting_id)             # Exclui reunião
```

#### Módulo (`modules/meetings/__init__.py`)
```python
# Rotas implementadas:
- /meetings/company/<int:company_id>                          # Lista de reuniões
- /meetings/company/<int:company_id>/new                      # Nova reunião
- /meetings/company/<int:company_id>/meeting/<int:meeting_id> # Detalhes
- /meetings/company/<int:company_id>/meeting/<int:meeting_id>/edit   # Editar
- /meetings/company/<int:company_id>/meeting/<int:meeting_id>/delete # Deletar

# APIs:
- /meetings/api/company/<int:company_id>/meetings    # API: listar reuniões
- /meetings/api/meeting/<int:meeting_id>             # API: detalhes
```

### Frontend

#### Templates
- `templates/meetings_list.html` - Lista de reuniões (próximas e passadas)
- `templates/meeting_form.html` - Formulário para criar/editar reunião
- `templates/meeting_detail.html` - Visualização detalhada da reunião
- `templates/meetings_sidebar.html` - Sidebar de navegação

### Banco de Dados

#### Tabela `meetings`
```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    project_id INTEGER,                    -- Projeto vinculado
    title TEXT NOT NULL,
    scheduled_date DATE,
    scheduled_time TEXT,
    invite_notes TEXT,
    meeting_notes TEXT,
    guests_json TEXT,                      -- JSON: {internal: [], external: []}
    agenda_json TEXT,                      -- JSON: ["item1", "item2", ...]
    participants_json TEXT,                -- JSON: {internal: [], external: []}
    discussions_json TEXT,                 -- JSON: [{topic, text}, ...]
    activities_json TEXT,                  -- JSON: [{title, responsible, deadline, status}, ...]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies (id),
    FOREIGN KEY (project_id) REFERENCES company_projects (id)
)
```

## Fluxo de Uso

### 1. Criar Nova Reunião (Convite)

1. Acessar `Gestão de Reuniões` > `Nova Reunião`
2. Preencher informações básicas:
   - Título
   - Data e horário
   - Responsável
3. Adicionar convidados (internos e externos)
4. Definir pauta (tópicos a discutir)
5. Adicionar observações do convite
6. Salvar → Sistema cria:
   - Reunião no banco de dados
   - Projeto vinculado automaticamente

### 2. Registrar Reunião Realizada

1. Acessar a reunião na lista
2. Clicar em "Editar"
3. Preencher informações da reunião:
   - Participantes efetivos (quem compareceu)
   - Notas da reunião
   - Discussões e definições
   - Atividades criadas
4. Salvar

### 3. Acompanhar Atividades

- As atividades ficam registradas na reunião
- Podem ser gerenciadas através do projeto vinculado
- Status pode ser atualizado conforme progresso

## Navegação

### Menu Principal (Sidebar GRV)

O módulo de reuniões foi adicionado ao menu principal:

```
Gestão de Reuniões
├── Reuniões         → Lista todas as reuniões
└── Nova Reunião     → Criar nova reunião
```

### Breadcrumb

Todas as páginas incluem navegação contextual:
```
Dashboard › [Empresa] › Reuniões › [Ação específica]
```

## Funcionalidades Especiais

### 1. Separação Automática de Reuniões
- **Próximas Reuniões**: Reuniões com data >= hoje
- **Reuniões Passadas**: Reuniões com data < hoje

### 2. Formulário Dinâmico
- Adicionar/remover convidados dinamicamente
- Adicionar/remover itens da pauta
- Adicionar/remover discussões
- Adicionar/remover atividades

### 3. Visualização Rico
- Cards coloridos para diferentes seções
- Badges de status para atividades
- Links diretos para projetos vinculados
- Contador de participantes e atividades

### 4. Integração com Projetos
- Link direto para visualizar projeto
- Projeto herda código da empresa
- Projeto pode ser gerenciado independentemente

## API REST

### Listar Reuniões
```http
GET /meetings/api/company/{company_id}/meetings
```

**Resposta:**
```json
{
  "success": true,
  "meetings": [
    {
      "id": 1,
      "title": "Planejamento Q4",
      "scheduled_date": "2025-10-20",
      "scheduled_time": "09:00",
      "project_id": 123,
      "project_code": "EMP.J.001",
      "guests": {...},
      "agenda": [...],
      ...
    }
  ]
}
```

### Detalhes da Reunião
```http
GET /meetings/api/meeting/{meeting_id}
```

### Deletar Reunião
```http
POST /meetings/company/{company_id}/meeting/{meeting_id}/delete
```

## Segurança

- Todas as operações verificam se a reunião pertence à empresa
- Blueprint registrado com prefix `/meetings`
- Validação de dados no backend
- Confirmação antes de deletar

## Extensibilidade

### Futuras Melhorias Possíveis

1. **Notificações**
   - Email de convite automático
   - Lembretes antes da reunião
   - Notificações de atividades pendentes

2. **Calendário**
   - Visualização em calendário
   - Sincronização com calendários externos
   - Detecção de conflitos de horário

3. **Documentos**
   - Anexar arquivos à reunião
   - Gerar ata automaticamente
   - Export para PDF

4. **Relatórios**
   - Dashboard de reuniões
   - Estatísticas de participação
   - Relatório de atividades geradas

5. **Integrações**
   - Teams/Zoom/Google Meet
   - Calendário do Google
   - Outlook

## Suporte e Manutenção

### Logs
- Erros são logados no console
- Mensagens flash para feedback ao usuário

### Debug
```python
# Verificar reuniões de uma empresa
db.list_company_meetings(company_id)

# Verificar reunião específica
db.get_meeting(meeting_id)

# Verificar projeto vinculado
db.get_company_project(company_id, project_id)
```

## Conclusão

O Sistema de Gestão de Reuniões oferece uma solução completa para gerenciar o ciclo de vida das reuniões, desde o planejamento até o acompanhamento das atividades geradas, com integração automática ao sistema de projetos da empresa.

---

**Data de Implementação**: Outubro de 2025  
**Versão**: 1.0  
**Status**: ✅ Implementado e Funcional

