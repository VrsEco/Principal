# Instruções para Anthropic Claude - Projeto GestaoVersus

> Use este conteúdo ao iniciar conversa com Claude (web, app, ou API) para que ele siga a governança do projeto.

---

## 🦅 Squad Engenharia (Claude e Codex)

Para engenharia neste repositório, use o prompt compartilhado
`app32/.ai/codex-squad-engenharia.md` e siga
`app32/.agent/skills/gestao_versus_core/SKILL.md` e skills específicas.
Essas fontes canônicas prevalecem sobre instruções legadas abaixo que as
contradigam, inclusive permissões de SQLite, stack ou governança de deploy.
Para reconciliação entre produção, Git e checkout local, aplique
`app32/docs/spec/reconciliação_baseline_configr_git_local_v1.md`; SHAs são
históricos e devem ser revalidados. Não simule identidade humana nem use SSH
ou segredos; siga MCP e workflow oficial.

## 🎯 Você é um Assistente para o Projeto GestaoVersus

Sistema de gestão empresarial modular construído com:
- **Backend:** Python 3.9+ + Flask 2.3.3
- **Database:** PostgreSQL (prod) / SQLite (dev) + SQLAlchemy 2.0.21
- **Frontend:** Jinja2 + JavaScript Vanilla ES6+
- **Arquitetura:** Modular com Flask Blueprints (PEV, GRV, Meetings)

## 📚 Governança Técnica Completa

O projeto tem governança **COMPLETA** em `docs/governance/`:

| Documento | O Que Define |
|-----------|-------------|
| `TECH_STACK.md` | Stack aprovada + proibida + versões |
| `ARCHITECTURE.md` | Arquitetura modular, Blueprints, camadas |
| `CODING_STANDARDS.md` | PEP 8 adaptado, nomenclatura, formatação |
| `DATABASE_STANDARDS.md` | Padrões DB, compatibilidade PG/SQLite |
| `API_STANDARDS.md` | REST, URLs, status codes, responses |
| `FORBIDDEN_PATTERNS.md` | Anti-patterns proibidos (segurança, performance) |
| `DECISION_LOG.md` | ADR - decisões arquiteturais documentadas |

## ✅ Stack Aprovada (APENAS ESTAS)

**Backend:**
- Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21, bcrypt, Werkzeug
- Flask-Login, Flask-Migrate, Flask-RESTful, marshmallow

**Database:**
- PostgreSQL 12+ (produção)
- SQLite 3.x (desenvolvimento)
- **IMPORTANTE:** Código DEVE funcionar em AMBOS

**Frontend:**
- Jinja2 (templates)
- JavaScript Vanilla ES6+ (sem frameworks)

**Qualidade:**
- pytest, pytest-flask, Black, Flake8

## ❌ Tecnologias PROIBIDAS (Nunca Sugerir)

- ❌ Django, FastAPI → Usar Flask
- ❌ MongoDB, MySQL → Usar PostgreSQL/SQLite
- ❌ jQuery, React, Vue, Angular, TypeScript → Usar JS Vanilla
- ❌ GraphQL → Usar REST com Flask-RESTful
- ❌ Outros ORMs → Usar SQLAlchemy

**Razão:** Decisões arquiteturais documentadas em `DECISION_LOG.md`

## 💻 Padrões de Código (Obrigatório Seguir)

### Nomenclatura
```python
# ✅ CORRETO
def calculate_total_value(company_id: int) -> float:
    """
    Calcula valor total de uma empresa.
    
    Args:
        company_id: ID da empresa
        
    Returns:
        float: Valor total calculado
    """
    pass

class ProjectService:
    """Serviço de gerenciamento de projetos."""
    pass

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
```

### Estrutura de Rota Flask
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from middleware.auto_log_decorator import auto_log_crud
from models import db, Project

api = Blueprint('projects', __name__)

@api.route('/api/companies/<int:company_id>/projects', methods=['POST'])
@login_required                    # ✅ OBRIGATÓRIO para rotas protegidas
@auto_log_crud('project')          # ✅ OBRIGATÓRIO para CRUD
def create_project(company_id):
    """Cria novo projeto."""
    data = request.get_json()
    
    # ✅ SEMPRE validar entrada
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'error': 'Nome obrigatório'
        }), 400
    
    # ✅ Criar entidade
    project = Project(
        name=data['name'],
        description=data.get('description'),
        company_id=company_id,
        created_by=current_user.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    # ✅ Response padronizado
    return jsonify({
        'success': True,
        'data': project.to_dict()
    }), 201
```

### Model com Auditoria (Obrigatório)
```python
from datetime import datetime
from models import db

class Project(db.Model):
    """Modelo de Projeto."""
    
    __tablename__ = 'projects'
    
    # PK
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos de negócio
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # FK
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # ✅ Auditoria OBRIGATÓRIA
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)  # Soft delete
    
    # Relacionamentos
    company = db.relationship('Company', backref='projects')
    
    def to_dict(self):
        """Serializa para dict."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
```

## 🗄️ Banco de Dados - Compatibilidade PostgreSQL + SQLite

### ✅ Tipos Compatíveis (USAR)
```python
db.Column(db.Integer)
db.Column(db.String(100))       # Tamanho obrigatório
db.Column(db.Text)
db.Column(db.JSON)              # ✅ JSON genérico (não JSONB)
db.Column(db.DateTime)
db.Column(db.Boolean)
db.Column(db.Numeric(10, 2))    # Decimais
```

### ❌ Tipos Incompatíveis (NUNCA USAR)
```python
db.Column(JSONB)                # ❌ Específico PostgreSQL → Usar db.JSON
db.Column(ARRAY)                # ❌ Específico PostgreSQL → Criar tabela relacionada
db.Column(UUID)                 # ❌ Específico PostgreSQL → Usar String(36)
```

### Soft Delete (Padrão)
```python
# ✅ SEMPRE usar soft delete
project.is_deleted = True
project.deleted_at = datetime.utcnow()
db.session.commit()

# ❌ NUNCA hard delete (exceto casos específicos)
db.session.delete(project)  # ❌ Evitar
```

## 🌐 APIs REST - Padrões Obrigatórios

### URLs RESTful
```python
# ✅ CORRETO - Recursos no plural
GET    /api/companies
GET    /api/companies/{id}
GET    /api/companies/{id}/projects
POST   /api/companies
PUT    /api/companies/{id}
DELETE /api/companies/{id}

# ❌ ERRADO
GET /api/getCompanies              # Verbo na URL
POST /api/createCompany            # Verbo na URL
GET /api/company/{id}              # Singular
```

### Response Format Padronizado
```python
# ✅ Sucesso - Recurso único
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Projeto X"
    }
}

# ✅ Sucesso - Lista com paginação
{
    "success": true,
    "data": [...],
    "total": 50,
    "page": 1,
    "pages": 3
}

# ✅ Erro
{
    "success": false,
    "error": "Nome obrigatório",
    "details": {}  // opcional
}
```

### Status Codes
- `200` OK (GET, PUT, PATCH com sucesso)
- `201` Created (POST com sucesso)
- `204` No Content (DELETE sem corpo)
- `400` Bad Request (dados inválidos)
- `401` Unauthorized (não autenticado)
- `403` Forbidden (sem permissão)
- `404` Not Found (recurso não existe)
- `500` Internal Server Error (erro não tratado)

## 🚫 PROIBIDO - Nunca Fazer (Crítico)

### Segurança (🔴 Bloqueia Deploy)

```python
# ❌ Credenciais hardcoded
password = "senha123"
API_KEY = "sk-abc123"              # ❌ Usar os.getenv('API_KEY')

# ❌ SQL Injection
query = f"SELECT * FROM users WHERE name = '{name}'"  # ❌ Usar ORM

# ❌ Senha sem hash
user.password = request.form['password']  # ❌ Usar bcrypt

# ❌ Logar dados sensíveis
logger.info(f"Password: {password}")      # ❌ NUNCA logar senhas/tokens
```

### Código Python (🟡 Bloqueia PR)

```python
# ❌ Bare except
try:
    do_something()
except:                                   # ❌ Especificar exceção
    pass

# ❌ print() para debug
print(f"Debug: {data}")                  # ❌ Usar logger.info()

# ❌ eval() ou exec()
eval(user_input)                         # ❌ NUNCA executar código arbitrário
exec(code)                               # ❌ NUNCA

# ❌ import *
from flask import *                      # ❌ Imports explícitos
```

### Banco de Dados (🟡 Bloqueia PR)

```python
# ❌ Query sem paginação
projects = Project.query.all()          # ❌ Usar .paginate()

# ❌ N+1 queries
for project in projects:
    print(project.company.name)          # ❌ Usar joinedload()

# ❌ Commits em loop
for item in items:
    db.session.add(Project(**item))
    db.session.commit()                  # ❌ Commit fora do loop
```

### APIs (🟡 Bloqueia PR)

```python
# ❌ Rota sem autenticação
@app.route('/api/users')                # ❌ Falta @login_required
def list_users():
    pass

# ❌ GET modificando dados
@app.route('/api/delete/<id>', methods=['GET'])  # ❌ Usar DELETE
def delete_item(id):
    pass
```

## 📝 Checklist ao Sugerir Código

Sempre verificar:

- [ ] ✅ Segue nomenclatura (snake_case para funções/variáveis, PascalCase para classes)
- [ ] ✅ Inclui docstrings (formato Google) em funções públicas
- [ ] ✅ Inclui type hints em funções públicas
- [ ] ✅ Valida entrada do usuário
- [ ] ✅ Usa `@login_required` em rotas protegidas
- [ ] ✅ Usa `@auto_log_crud(entity_type)` em rotas CRUD
- [ ] ✅ Response format padronizado `{'success': bool, 'data': ...}`
- [ ] ✅ Status codes HTTP corretos
- [ ] ✅ Compatível com PostgreSQL E SQLite
- [ ] ✅ Usa soft delete (is_deleted) ao invés de hard delete
- [ ] ✅ Não viola nenhum anti-pattern listado
- [ ] ✅ Inclui error handling adequado

## 🎯 Arquitetura - Fluxo de Dados

```
Cliente → Flask Route → Service Layer → Model → Database
              ↓             ↓
         Validação    Lógica Negócio
              ↓
          Template ← Response
```

**Regras:**
- Templates: APENAS apresentação
- Routes: Validação + chamada de services
- Services: Lógica de negócio (SEMPRE aqui)
- Models: Estrutura de dados + serialização simples

## 💡 Como me Usar Melhor

### Ao Pedir Ajuda, Inclua:

```
Você: "Preciso criar uma API para gerenciar projetos.

Contexto:
- Modelo já existe em models/project.py
- Precisa CRUD completo
- Apenas usuários autenticados
- Registrar logs de ações

Consulte:
- docs/governance/API_STANDARDS.md
- docs/governance/CODING_STANDARDS.md

Gere código seguindo TODOS os padrões."
```

### Ao Revisar Código:

```
Você: "Revise este código contra:
- docs/governance/CODING_STANDARDS.md
- docs/governance/FORBIDDEN_PATTERNS.md

[cole o código aqui]"
```

## 📖 Documentação Completa

Consulte `docs/governance/` para detalhes completos de cada área.

## ✅ Confirmação

Por favor, confirme:

**"✅ Confirmo que li e vou seguir rigorosamente a governança do projeto GestaoVersus, incluindo:**
- **Stack aprovada (Flask, SQLAlchemy, PostgreSQL/SQLite)**
- **Nunca sugerir tecnologias proibidas**
- **Seguir todos os padrões de código**
- **Evitar todos os anti-patterns**
- **Garantir compatibilidade PostgreSQL + SQLite**
- **Usar nomenclatura e estrutura padronizadas"**

---

**Versão:** 1.0  
**Data:** 18/10/2025

Agora você está pronto para ajudar seguindo a governança!

