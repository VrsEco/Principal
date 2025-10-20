# Instruções para OpenAI Codex - Projeto GestaoVersus

> Use este conteúdo ao configurar Codex (API, playground, ou integrações) para seguir a governança do projeto.

---

## 🎯 System Prompt para Codex

```
You are an expert Python/Flask developer working on GestaoVersus, 
a modular business management system.

STRICT RULES - ALWAYS FOLLOW:

1. Stack: ONLY Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21, PostgreSQL/SQLite
2. NEVER suggest: Django, FastAPI, MongoDB, MySQL, React, Vue, TypeScript
3. Code MUST work on PostgreSQL AND SQLite
4. ALL routes MUST have @login_required
5. CRUD routes MUST have @auto_log_crud(entity_type)
6. Response format: {"success": bool, "data": ...}
7. Use soft delete (is_deleted=True), NOT hard delete
8. snake_case for functions/variables, PascalCase for classes
9. NEVER use: eval(), exec(), bare except, print() for debug
10. NEVER hardcode credentials

Governance docs: docs/governance/
```

---

## 📚 Contexto Completo

### Stack Tecnológica

**Aprovado (USAR APENAS):**
```python
# Backend
Python 3.9+
Flask 2.3.3
SQLAlchemy 2.0.21
Flask-Login 0.6.3
bcrypt 4.0.1

# Database
PostgreSQL 12+ (produção)
SQLite 3.x (desenvolvimento)

# Frontend
Jinja2 (templates)
JavaScript Vanilla ES6+

# Qualidade
pytest, Black, Flake8
```

**Proibido (NUNCA SUGERIR):**
```python
# ❌ NUNCA usar
Django, FastAPI          # Já temos Flask
MongoDB, MySQL           # Já temos PostgreSQL/SQLite
React, Vue, Angular      # Usar JS Vanilla
jQuery, TypeScript       # Usar JS ES6+
GraphQL                  # Usar REST
```

---

## 💻 Padrões de Código (Obrigatório)

### Nomenclatura
```python
# ✅ CORRETO
def calculate_total_revenue(company_id: int) -> float:
    """Calcula receita total da empresa."""
    pass

class ProjectService:
    """Serviço de gerenciamento de projetos."""
    pass

MAX_FILE_SIZE = 5 * 1024 * 1024

# ❌ ERRADO
def calcTotal(companyId): pass          # camelCase
class project_service: pass             # snake_case para classe
maxFileSize = 5242880                   # camelCase para constante
```

### Estrutura de Rota Flask (Template)
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from middleware.auto_log_decorator import auto_log_crud
from models import db, Project

api = Blueprint('projects', __name__)

@api.route('/api/companies/<int:company_id>/projects', methods=['POST'])
@login_required                    # ✅ OBRIGATÓRIO
@auto_log_crud('project')          # ✅ OBRIGATÓRIO para CRUD
def create_project(company_id: int):
    """Cria novo projeto para empresa."""
    data = request.get_json()
    
    # ✅ Validação obrigatória
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

### Model SQLAlchemy (Template)
```python
from datetime import datetime
from models import db

class Project(db.Model):
    """Modelo de Projeto."""
    
    __tablename__ = 'projects'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos de negócio
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # ✅ Auditoria OBRIGATÓRIA
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relacionamentos
    company = db.relationship('Company', backref='projects')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        """Serializa model para dict."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Project {self.name}>'
```

---

## 🗄️ Database - Compatibilidade PostgreSQL/SQLite

### ✅ Tipos Compatíveis (USAR)
```python
# ✅ Funciona em ambos
db.Column(db.Integer)
db.Column(db.String(100))       # Tamanho obrigatório
db.Column(db.Text)
db.Column(db.JSON)              # ✅ JSON (NÃO JSONB)
db.Column(db.DateTime)
db.Column(db.Date)
db.Column(db.Time)
db.Column(db.Boolean)
db.Column(db.Numeric(10, 2))    # Decimais
db.Column(db.Float)
```

### ❌ Tipos Incompatíveis (NUNCA USAR)
```python
# ❌ Específico PostgreSQL
db.Column(JSONB)                # ❌ Usar db.JSON
db.Column(ARRAY)                # ❌ Criar tabela relacionada
db.Column(UUID)                 # ❌ Usar db.String(36)
db.Column(HSTORE)               # ❌ Usar db.JSON
db.Column(ENUM)                 # ❌ Usar db.String com CHECK constraint
```

### Soft Delete (Padrão do Projeto)
```python
# ✅ SEMPRE soft delete
@api.route('/api/projects/<int:id>', methods=['DELETE'])
@login_required
@auto_log_crud('project')
def delete_project(id: int):
    """Remove projeto (soft delete)."""
    project = Project.query.get_or_404(id)
    
    # ✅ Soft delete
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    project.deleted_by = current_user.id
    
    db.session.commit()
    
    return jsonify({'success': True}), 200

# ❌ NUNCA hard delete (exceto casos específicos aprovados)
db.session.delete(project)
db.session.commit()
```

---

## 🌐 APIs REST - Padrões

### URLs RESTful
```python
# ✅ CORRETO - Plural, hierárquico, sem verbos
GET    /api/companies
GET    /api/companies/{id}
GET    /api/companies/{id}/projects
POST   /api/companies
PUT    /api/companies/{id}
DELETE /api/companies/{id}

# ❌ ERRADO
GET /api/getCompanies              # Verbo na URL
POST /api/company/create           # Verbo + singular
GET /api/company/{id}              # Singular
PUT /api/updateCompany/{id}        # Verbo
```

### Response Format (Obrigatório)
```python
# ✅ Sucesso - Recurso único
{
    "success": true,
    "data": {
        "id": 1,
        "name": "Projeto X",
        "created_at": "2025-10-18T10:00:00Z"
    }
}

# ✅ Sucesso - Lista com paginação
{
    "success": true,
    "data": [
        {"id": 1, "name": "Projeto A"},
        {"id": 2, "name": "Projeto B"}
    ],
    "total": 50,
    "page": 1,
    "per_page": 20,
    "pages": 3
}

# ✅ Erro - Mensagem descritiva
{
    "success": false,
    "error": "Nome obrigatório",
    "details": {
        "field": "name",
        "type": "required"
    }
}

# ❌ ERRADO - Sem padrão
{"id": 1, "name": "X"}             # Sem success flag
{"error": "Erro"}                   # Sem success: false
[{"id": 1}, {"id": 2}]             # Lista sem metadata
```

### Status Codes (Obrigatório)
```python
# ✅ CORRETO
return jsonify(data), 200          # OK (GET, PUT)
return jsonify(data), 201          # Created (POST)
return '', 204                     # No Content (DELETE sem corpo)
return jsonify(error), 400         # Bad Request
return jsonify(error), 401         # Unauthorized
return jsonify(error), 403         # Forbidden
return jsonify(error), 404         # Not Found
return jsonify(error), 409         # Conflict
return jsonify(error), 500         # Server Error

# ❌ ERRADO
return jsonify(data)               # Sem status code explícito
return "OK", 200                   # String ao invés de JSON
return jsonify(data), 201          # 201 em PUT (usar 200)
```

---

## 🚫 PROIBIDO - Nunca Gerar

### Segurança (🔴 Crítico - Bloqueia Deploy)
```python
# ❌ Credenciais hardcoded
password = "senha123"
API_KEY = "sk-abc123xyz"
DATABASE_URL = "postgresql://user:pass@localhost/db"

# ✅ CORRETO
import os
password = os.getenv('PASSWORD')
API_KEY = os.getenv('API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# ❌ SQL Injection
query = f"SELECT * FROM users WHERE name = '{name}'"
db.session.execute(query)

# ✅ CORRETO
users = User.query.filter_by(name=name).all()

# ❌ Senha sem hash
user.password = request.form['password']

# ✅ CORRETO
import bcrypt
user.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# ❌ Logar dados sensíveis
logger.info(f"User password: {password}")
print(f"API Key: {api_key}")

# ✅ CORRETO
logger.info(f"User authenticated: {user.email}")
```

### Código Python (🟡 Bloqueia PR)
```python
# ❌ Bare except
try:
    do_something()
except:
    pass

# ✅ CORRETO
try:
    do_something()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise

# ❌ print() para debug
print(f"User data: {user}")

# ✅ CORRETO
import logging
logger = logging.getLogger(__name__)
logger.info(f"User logged in: {user.email}")

# ❌ eval() ou exec()
eval(user_input)
exec(code)

# ✅ CORRETO
# Validar entrada e processar de forma segura
allowed_ops = {'sum': sum, 'max': max}
if operation in allowed_ops:
    result = allowed_ops[operation](values)

# ❌ import *
from flask import *
from models import *

# ✅ CORRETO
from flask import Flask, request, jsonify
from models import db, User, Project
```

### Database (🟡 Bloqueia PR)
```python
# ❌ Query sem paginação
projects = Project.query.all()

# ✅ CORRETO
page = request.args.get('page', 1, type=int)
per_page = request.args.get('per_page', 20, type=int)
projects = Project.query.paginate(page=page, per_page=per_page)

# ❌ N+1 queries
for project in projects:
    print(project.company.name)  # Query adicional por projeto!

# ✅ CORRETO
from sqlalchemy.orm import joinedload
projects = Project.query.options(joinedload(Project.company)).all()

# ❌ Commits em loop
for item in items:
    project = Project(**item)
    db.session.add(project)
    db.session.commit()  # Lento!

# ✅ CORRETO
for item in items:
    project = Project(**item)
    db.session.add(project)
db.session.commit()  # Um commit só
```

### APIs (🟡 Bloqueia PR)
```python
# ❌ Rota sem autenticação
@app.route('/api/users')
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

# ✅ CORRETO
@app.route('/api/users')
@login_required
def list_users():
    users = User.query.all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]})

# ❌ GET modificando dados
@app.route('/api/projects/<int:id>/activate', methods=['GET'])
def activate_project(id):
    project = Project.query.get(id)
    project.active = True
    db.session.commit()

# ✅ CORRETO
@app.route('/api/projects/<int:id>/activate', methods=['POST'])
@login_required
def activate_project(id):
    project = Project.query.get_or_404(id)
    project.active = True
    db.session.commit()
    return jsonify({'success': True, 'data': project.to_dict()})
```

---

## 📝 Checklist Automático (Verificar Sempre)

Ao gerar código, AUTOMATICAMENTE incluir:

- [ ] ✅ Nomenclatura: snake_case (funções/vars), PascalCase (classes)
- [ ] ✅ Docstrings: Formato Google em todas funções públicas
- [ ] ✅ Type hints: Em parâmetros e retornos
- [ ] ✅ Validação: Sempre validar entrada do usuário
- [ ] ✅ @login_required: Em todas rotas protegidas
- [ ] ✅ @auto_log_crud: Em todas rotas CRUD
- [ ] ✅ Response format: {'success': bool, 'data': ...}
- [ ] ✅ Status codes: Corretos (200, 201, 400, 404, etc.)
- [ ] ✅ Compatibilidade: PostgreSQL E SQLite
- [ ] ✅ Soft delete: is_deleted=True (não hard delete)
- [ ] ✅ Error handling: try/except específicos
- [ ] ✅ Logging: logger (não print)

---

## 🎯 Exemplos de Prompts Efetivos

### Prompt Bom (Gera Código Perfeito)
```
Generate a complete Flask route to create projects with:
- @login_required and @auto_log_crud decorators
- Input validation
- Response format: {"success": bool, "data": ...}
- Status code 201
- Docstring with type hints
- Compatible with PostgreSQL and SQLite
```

### Prompt Ruim (Gera Código Fora do Padrão)
```
Create a route to add projects
```

---

## 🔧 Configuração de API (Se Usar Codex via API)

```python
import openai

# System message com governança
system_message = """
You are a Python/Flask expert for GestaoVersus project.

STRICT RULES:
- Stack: Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21
- NEVER: Django, FastAPI, MongoDB, React, TypeScript
- ALL routes: @login_required, @auto_log_crud for CRUD
- Response: {"success": bool, "data": ...}
- Database: Compatible PostgreSQL + SQLite
- Naming: snake_case (functions), PascalCase (classes)
- NO: eval(), exec(), bare except, print(), hardcoded credentials

Governance: docs/governance/
"""

response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # ou gpt-4
    messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": "Create a Flask route to list projects"}
    ],
    temperature=0.2  # Menos criativo, mais consistente
)
```

---

## 📚 Referências Completas

**Governança completa em:**
- `docs/governance/TECH_STACK.md` - Stack aprovada/proibida
- `docs/governance/CODING_STANDARDS.md` - Padrões completos
- `docs/governance/DATABASE_STANDARDS.md` - Padrões DB
- `docs/governance/API_STANDARDS.md` - Padrões REST
- `docs/governance/FORBIDDEN_PATTERNS.md` - Anti-patterns
- `docs/governance/DECISION_LOG.md` - Decisões (ADR)

---

## ✅ Validação

Ao gerar código, pergunte-se:

1. ✅ Usa APENAS stack aprovada?
2. ✅ Segue nomenclatura (snake_case/PascalCase)?
3. ✅ Tem docstrings e type hints?
4. ✅ Valida entrada do usuário?
5. ✅ Usa @login_required em rotas protegidas?
6. ✅ Usa @auto_log_crud em CRUD?
7. ✅ Response format padronizado?
8. ✅ Compatível PostgreSQL E SQLite?
9. ✅ Soft delete (não hard delete)?
10. ✅ Não viola nenhum anti-pattern?

**Se TODAS respostas são SIM → Código está correto! ✅**

---

**Versão:** 1.0  
**Data:** 18/10/2025  
**Projeto:** GestaoVersus




