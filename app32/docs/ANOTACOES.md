# 📝 Funcionalidade de Anotações - Documentação Técnica

## Visão Geral

Sistema completo de gerenciamento de anotações pessoais integrado ao Ecossistema Versus, permitindo que usuários criem, visualizem e excluam notas de forma rápida e intuitiva.

---

## 🏗️ Arquitetura

### Camadas Implementadas

```
┌─────────────────────────────────────────┐
│         Interface Web (HTML/JS)         │
│         templates/ecosystem.html        │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│          API REST (Flask)               │
│           api/notes.py                  │
│  GET /api/notes/                        │
│  POST /api/notes/                       │
│  DELETE /api/notes/<id>                 │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Camada de Serviço (Python)         │
│       services/notes_service.py         │
│  - get_user_notes()                     │
│  - create_note()                        │
│  - delete_note()                        │
│  - _generate_note_code()                │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Modelo de Dados (SQLAlchemy)       │
│          models/note.py                 │
│  - Note (id, code, user_id, text, ...)  │
└─────────────────────────────────────────┘
```

---

## 📊 Modelo de Dados

### Tabela: `notes`

| Campo       | Tipo         | Descrição                          | Constraints        |
|-------------|--------------|------------------------------------|--------------------|
| id          | Integer      | Identificador único                | PK, Auto-increment |
| code        | String(32)   | Código de referência (NT-XXXX)     | Unique, Not Null   |
| user_id     | Integer      | ID do usuário proprietário         | FK users.id        |
| text        | Text         | Conteúdo da anotação               | Not Null           |
| location    | String(256)  | Localização/contexto (opcional)    | Nullable           |
| status      | String(32)   | Status da nota                     | Default: 'ativa'   |
| created_at  | DateTime     | Data/hora de criação               | Server default     |

### Relacionamentos

- **Note.user** → **User** (Many-to-One)
- **User.notes** → **Note[]** (One-to-Many, lazy='dynamic')

---

## 🔌 API Endpoints

### 1. Listar Notas
```http
GET /api/notes/
Authorization: Required (Flask-Login)
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "notes": [
    {
      "id": 1,
      "code": "NT-1234",
      "text": "Minha anotação",
      "location": "",
      "status": "ativa",
      "created_at": "2025-11-24T16:30:00"
    }
  ]
}
```

**Resposta de Erro (500):**
```json
{
  "success": false,
  "message": "Erro ao recuperar notas. Tente novamente."
}
```

---

### 2. Criar Nota
```http
POST /api/notes/
Authorization: Required (Flask-Login)
Content-Type: application/json
```

**Corpo da Requisição:**
```json
{
  "text": "Conteúdo da nota",
  "location": "Contexto opcional"
}
```

**Resposta de Sucesso (201):**
```json
{
  "success": true,
  "message": "Nota criada com sucesso!",
  "note": {
    "id": 2,
    "code": "NT-5678",
    "text": "Conteúdo da nota",
    "location": "Contexto opcional",
    "status": "ativa",
    "created_at": "2025-11-24T16:35:00"
  }
}
```

**Resposta de Erro (400):**
```json
{
  "success": false,
  "message": "O texto da nota é obrigatório."
}
```

---

### 3. Excluir Nota
```http
DELETE /api/notes/<note_id>
Authorization: Required (Flask-Login)
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Nota excluída com sucesso!"
}
```

**Resposta de Erro (404):**
```json
{
  "success": false,
  "message": "Nota não encontrada."
}
```

**Resposta de Erro (403):**
```json
{
  "success": false,
  "message": "Você não tem permissão para excluir esta nota."
}
```

---

## 🔐 Segurança

### Validações Implementadas

1. **Autenticação**: Todos os endpoints requerem `@login_required`
2. **Ownership**: Usuários só podem excluir suas próprias notas
3. **Validação de Dados**:
   - Texto da nota não pode estar vazio
   - Texto é trimmed antes de salvar
   - Location é opcional e também trimmed

### Geração de Código

- **Formato**: `NT-XXXX` (4 dígitos aleatórios)
- **Unicidade**: Verifica duplicatas no banco antes de criar
- **Fallback**: Usa timestamp se 100 tentativas falharem

---

## 🎨 Interface do Usuário

### Componentes

1. **Formulário de Criação**
   - Campo de texto (textarea)
   - Botão "Salvar nota"
   - Feedback visual: "Salvando..." → "✓ Salva!"

2. **Lista de Notas**
   - Exibição de código e data
   - Seleção via checkbox
   - Preview do texto (2 linhas)
   - Localização (se disponível)

3. **Ações**
   - **Criar atividade**: Desabilitado (pendente)
   - **Excluir**: Com confirmação
   - Feedback visual: "Excluindo..." → "✓ Excluída!"

### Estados da UI

- **Loading**: Carregando notas do servidor
- **Empty**: Nenhuma nota cadastrada
- **Error**: Erro ao carregar/salvar/excluir
- **Success**: Operação concluída com sucesso

---

## 🚀 Como Usar

### 1. Executar Migration

```bash
flask db upgrade
```

### 2. Acessar Interface

Navegue para: `http://localhost:5000/main`

### 3. Criar Nota

1. Digite o texto no campo "Descreva a anotação..."
2. Clique em "Salvar nota"
3. Aguarde confirmação "✓ Salva!"

### 4. Excluir Nota

1. Clique na nota para selecioná-la
2. Clique no botão "Excluir"
3. Confirme a exclusão no dialog
4. Aguarde confirmação "✓ Excluída!"

---

## 🧪 Testes

Execute o script de testes:

```bash
python scripts/test_notes_feature.py
```

### Testes Incluídos

- ✅ Geração de código único
- ✅ Validação de texto vazio
- ✅ Validação de espaços em branco

---

## 📝 Logs

### Eventos Registrados

- **INFO**: Criação e exclusão bem-sucedidas
- **ERROR**: Falhas em operações
- **EXCEPTION**: Stack traces completos

### Exemplo de Log

```
INFO: Nota NT-1234 criada com sucesso para usuário 5
INFO: Nota NT-1234 excluída com sucesso pelo usuário 5
ERROR: Erro ao criar nota para usuário 5: <detalhes>
```

---

## 🔄 Fluxo de Dados

### Criação de Nota

```
1. Usuário preenche formulário
2. Frontend envia POST /api/notes/
3. API valida dados
4. Serviço gera código único
5. Serviço cria registro no banco
6. API retorna nota criada
7. Frontend adiciona à lista local
8. Frontend exibe feedback de sucesso
```

### Exclusão de Nota

```
1. Usuário seleciona nota
2. Usuário clica em "Excluir"
3. Frontend exibe confirmação
4. Frontend envia DELETE /api/notes/<id>
5. API valida ownership
6. Serviço remove do banco
7. API confirma exclusão
8. Frontend remove da lista local
9. Frontend exibe feedback de sucesso
```

---

## 🎯 Melhorias Futuras

### Prioridade Alta
- [ ] Endpoint PUT para editar notas
- [ ] Integração com sistema de atividades

### Prioridade Média
- [ ] Paginação de notas
- [ ] Busca e filtros
- [ ] Categorias/tags
- [ ] Ordenação customizável

### Prioridade Baixa
- [ ] Anexos de arquivos
- [ ] Compartilhamento de notas
- [ ] Notificações
- [ ] Exportação (PDF, CSV)

---

## 📚 Referências

- **Modelo**: `models/note.py`
- **Serviço**: `services/notes_service.py`
- **API**: `api/notes.py`
- **Interface**: `templates/ecosystem.html`
- **Migration**: `migrations/versions/20231123_0001_add_notes.py`
- **Testes**: `scripts/test_notes_feature.py`

---

**Última atualização**: 2025-11-24  
**Versão**: 1.0.0  
**Status**: ✅ Funcional (exceto integração com atividades)
