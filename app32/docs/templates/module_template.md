# Módulo: [Nome do Módulo]

**Data de Criação:** YYYY-MM-DD  
**Responsável:** [Nome]  
**Status:** 🔄 Em Desenvolvimento | ✅ Ativo | 🗄️ Depreciado  
**Versão:** 1.0

---

## 📋 Visão Geral

### Propósito
[Descrever o propósito do módulo em 2-3 frases]

### Escopo
[O que o módulo faz e o que NÃO faz]

**Faz:**
- [Funcionalidade 1]
- [Funcionalidade 2]
- [Funcionalidade 3]

**Não Faz:**
- [Fora do escopo 1]
- [Fora do escopo 2]

---

## 🏗️ Arquitetura

### Estrutura de Diretórios

```
modules/[nome_modulo]/
├── __init__.py           # Blueprint + rotas
├── models.py             # Models específicos do módulo (se houver)
├── services.py           # Lógica de negócio (se houver)
├── utils.py              # Utilitários (se houver)
└── README.md             # Documentação do módulo
```

### Blueprint

```python
# modules/[nome_modulo]/__init__.py
from flask import Blueprint

[nome]_bp = Blueprint(
    '[nome]',
    __name__,
    url_prefix='/[nome]',
    template_folder='../../templates/[nome]'
)
```

**Registrado em:** `app_pev.py`

---

## 🗄️ Modelos de Dados

### Tabelas Criadas

#### [Nome da Tabela 1]

```sql
CREATE TABLE [table_name] (
    id INTEGER PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Foreign Keys
    company_id INTEGER REFERENCES companies(id),
    
    -- Auditoria
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_[table]_[field] ON [table]([field]);
```

**Modelo SQLAlchemy:**
```python
class [ModelName](db.Model):
    __tablename__ = '[table_name]'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    # ... outros campos
```

**Relacionamentos:**
- `[Model].company` → Company (many-to-one)
- `[Model].items` → [OtherModel] (one-to-many)

#### [Nome da Tabela 2]
[Repetir estrutura acima para cada tabela]

---

## 🌐 APIs

### Endpoints Públicos

| Método | URL | Descrição | Auth | Body | Response |
|--------|-----|-----------|------|------|----------|
| GET | `/[module]` | Lista recursos | ✅ | - | HTML |
| GET | `/[module]/<int:id>` | Detalhe | ✅ | - | HTML |
| GET | `/api/[module]` | Lista (API) | ✅ | - | JSON |
| GET | `/api/[module]/<int:id>` | Detalhe (API) | ✅ | - | JSON |
| POST | `/api/[module]` | Criar | ✅ | JSON | JSON |
| PUT | `/api/[module]/<int:id>` | Atualizar | ✅ | JSON | JSON |
| DELETE | `/api/[module]/<int:id>` | Deletar | ✅ | - | JSON |

### Exemplos de Request/Response

#### Criar Recurso
```http
POST /api/[module]
Content-Type: application/json
Authorization: Bearer [token]

{
  "name": "Nome do Recurso",
  "description": "Descrição"
}
```

**Response 201 Created:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Nome do Recurso",
    "description": "Descrição",
    "created_at": "2025-10-18T10:00:00Z"
  }
}
```

#### Listar Recursos
```http
GET /api/[module]?page=1&per_page=20&status=active
Authorization: Bearer [token]
```

**Response 200 OK:**
```json
{
  "success": true,
  "data": [
    {"id": 1, "name": "Recurso 1"},
    {"id": 2, "name": "Recurso 2"}
  ],
  "total": 50,
  "page": 1,
  "pages": 3
}
```

---

## 🎨 Interface do Usuário

### Páginas

#### Lista de Recursos (`/[module]`)
- Tabela com recursos
- Filtros (status, data, etc.)
- Busca
- Paginação
- Botão "Novo"

**Template:** `templates/[module]/index.html`

#### Detalhe do Recurso (`/[module]/<id>`)
- Informações completas
- Ações (Editar, Deletar)
- Histórico (se aplicável)
- Relacionamentos

**Template:** `templates/[module]/detail.html`

#### Criar/Editar (`/[module]/new` ou `/[module]/<id>/edit`)
- Formulário completo
- Validações client-side
- Mensagens de erro/sucesso

**Template:** `templates/[module]/form.html`

---

## 🔐 Permissões e Segurança

### Níveis de Acesso

| Ação | Admin | Manager | User | Guest |
|------|-------|---------|------|-------|
| Visualizar | ✅ | ✅ | ✅ | ❌ |
| Criar | ✅ | ✅ | ⚠️ | ❌ |
| Editar | ✅ | ✅ | ⚠️ | ❌ |
| Deletar | ✅ | ⚠️ | ❌ | ❌ |

**Legenda:**
- ✅ Sempre permitido
- ⚠️ Apenas próprios recursos
- ❌ Negado

### Validações de Segurança

```python
@[module]_bp.route('/api/[module]/<int:id>', methods=['DELETE'])
@login_required
def delete_resource(id):
    resource = Resource.query.get_or_404(id)
    
    # Verificar permissão
    if not current_user.can_delete(resource):
        return jsonify({
            'success': False,
            'error': 'Acesso negado'
        }), 403
    
    # Prosseguir
    resource.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True})
```

---

## 🔄 Integrações

### Módulos Dependentes

**Este módulo depende de:**
- [ ] `models/company.py` - [para que]
- [ ] `models/user.py` - [para que]
- [ ] `services/auth_service.py` - [para que]

**Módulos que dependem deste:**
- [ ] `modules/[outro_modulo]` - [para que]

### Serviços Externos

**APIs Externas:**
- [ ] Nenhuma
- [ ] [Nome da API] - [propósito]

**Integrações:**
- [ ] Email (via `email_service.py`)
- [ ] S3/Storage (via `boto3`)
- [ ] Outros: [listar]

---

## 🧪 Testes

### Cobertura de Testes

**Objetivo:** > 80%  
**Atual:** [X%]

### Arquivos de Teste

```
tests/[module]/
├── __init__.py
├── test_models.py        # Testes de models
├── test_services.py      # Testes de services
├── test_routes.py        # Testes de rotas
└── test_integration.py   # Testes de integração
```

### Executar Testes

```bash
# Todos os testes do módulo
pytest tests/[module]/

# Apenas unitários
pytest tests/[module]/test_models.py

# Com cobertura
pytest tests/[module]/ --cov=modules/[module]
```

---

## 📊 Logging e Monitoramento

### Logs Automáticos

Rotas com `@auto_log_crud`:
- [x] POST `/api/[module]` - CREATE
- [x] PUT `/api/[module]/<id>` - UPDATE
- [x] DELETE `/api/[module]/<id>` - DELETE

**Visualizar logs:** `/logs/?entity_type=[entity_name]`

### Métricas

**KPIs do módulo:**
- Total de recursos criados
- Taxa de uso (DAU/MAU)
- Tempo médio de resposta
- Taxa de erro

**Dashboard:** [link se houver]

---

## 🚀 Deploy e Configuração

### Variáveis de Ambiente

```bash
# .env
[MODULE]_ENABLED=true          # Habilitar módulo
[MODULE]_FEATURE_X=true        # Feature flag específica
```

### Migrations

```bash
# Criar migration para este módulo
flask db migrate -m "Add [module] tables"

# Aplicar
flask db upgrade

# Reverter (se necessário)
flask db downgrade
```

### Seeds/Fixtures

```python
# scripts/seed_[module].py
def seed_[module]_data():
    """Popula dados iniciais do módulo."""
    # Implementação
    pass
```

---

## 📚 Documentação Adicional

### Guias de Uso

- [ ] [Guia Rápido](./QUICK_START_[MODULE].md)
- [ ] [Guia Completo](./USER_GUIDE_[MODULE].md)
- [ ] [FAQ](./FAQ_[MODULE].md)

### Para Desenvolvedores

- [ ] [Arquitetura Detalhada](./ARCHITECTURE_[MODULE].md)
- [ ] [Como Contribuir](./CONTRIBUTING_[MODULE].md)
- [ ] [Troubleshooting](./TROUBLESHOOTING_[MODULE].md)

---

## 🔧 Configurações

### Configurações Padrão

```python
# config.py
class Config:
    [MODULE]_PER_PAGE = 20           # Itens por página
    [MODULE]_MAX_UPLOAD_SIZE = 5MB   # Tamanho máximo upload
    [MODULE]_CACHE_TIMEOUT = 300     # Cache em segundos
```

### Configurações Customizáveis

[Listar configurações que podem ser alteradas por empresa/usuário]

---

## 📝 Changelog

### Versão 1.0 (YYYY-MM-DD)
- ✅ Implementação inicial
- ✅ CRUD completo
- ✅ Testes básicos
- ✅ Documentação

### Versão 1.1 (YYYY-MM-DD)
- ✅ [Feature adicionada]
- ✅ [Bug corrigido]

---

## 🐛 Issues Conhecidos

| Issue | Severidade | Status | Workaround |
|-------|-----------|--------|------------|
| [Descrição] | 🟡 Média | 🔄 Em andamento | [Descrição] |

---

## 🗺️ Roadmap

### Próximas Features

**Curto Prazo (1-2 sprints):**
- [ ] [Feature 1]
- [ ] [Feature 2]

**Médio Prazo (3-6 sprints):**
- [ ] [Feature 3]
- [ ] [Feature 4]

**Longo Prazo:**
- [ ] [Feature 5]
- [ ] [Feature 6]

---

## 🤝 Contribuindo

### Como Adicionar Feature

1. Ler este documento completamente
2. Seguir template em `/docs/templates/feature_template.md`
3. Seguir padrões em `/docs/governance/`
4. Adicionar testes
5. Atualizar este README
6. Abrir PR

### Code Review

Revisor deve verificar:
- [ ] Segue arquitetura do módulo
- [ ] Testes adicionados
- [ ] Documentação atualizada
- [ ] Não quebra funcionalidades existentes

---

## 📞 Contato

**Responsável pelo módulo:** [Nome]  
**Email:** [email]  
**Slack:** [canal]

---

## 📚 Referências

- [Link para documentação externa]
- [Link para design/mockup]
- [Link para ADR relacionado]

---

**Última Atualização:** YYYY-MM-DD  
**Versão deste documento:** 1.0



