# GitHub Copilot - Instruções do Projeto GestaoVersus

> Este arquivo é lido automaticamente pelo GitHub Copilot para entender as regras do projeto.

## 🎯 Contexto do Projeto

Sistema de gestão empresarial modular construído com:
- **Backend:** Python 3.9+ + Flask 2.3.3
- **Database:** PostgreSQL (prod) / SQLite (dev) com SQLAlchemy 2.0.21
- **Arquitetura:** Modular com Blueprints (PEV, GRV, Meetings)
- **Frontend:** Jinja2 Templates + JavaScript Vanilla

## 📚 Governança Completa

**IMPORTANTE:** Consultar `docs/governance/` antes de sugerir código:
- `TECH_STACK.md` - Stack aprovada
- `ARCHITECTURE.md` - Arquitetura do sistema
- `CODING_STANDARDS.md` - Padrões de código
- `DATABASE_STANDARDS.md` - Padrões de banco
- `API_STANDARDS.md` - Padrões de API
- `FORBIDDEN_PATTERNS.md` - Anti-patterns proibidos
- `DECISION_LOG.md` - Decisões arquiteturais

## ✅ Stack Tecnológica

### USAR (Aprovado)
- Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21
- PostgreSQL, SQLite, bcrypt
- Jinja2, JavaScript ES6+ (vanilla)
- ReportLab, pytest, Black, Flake8

### NUNCA SUGERIR (Proibido)
- Django, FastAPI, MongoDB, MySQL
- jQuery, React, Vue, Angular, TypeScript
- GraphQL, ORMs alternativos

## 💻 Padrões de Código

### Nomenclatura
```python
# ✅ CORRETO
def calculate_total_value(company_id: int) -> float:
    """Calcula valor total."""
    pass

class ProjectService:
    pass

MAX_UPLOAD_SIZE = 5242880

# ❌ ERRADO
def calcTotal(companyId):  # camelCase
    pass

class project_service:  # snake_case
    pass
```

### Estrutura de Código
```python
# ✅ SEMPRE usar
from flask_login import login_required
from middleware.auto_log_decorator import auto_log_crud

@app.route('/api/projects', methods=['POST'])
@login_required                    # ✅ Obrigatório
@auto_log_crud('project')          # ✅ Para CRUD
def create_project():
    data = request.get_json()
    
    # ✅ Validar entrada
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Nome obrigatório'}), 400
    
    # ✅ Criar entidade
    project = Project(name=data['name'], company_id=company_id)
    db.session.add(project)
    db.session.commit()
    
    # ✅ Response padronizado
    return jsonify({'success': True, 'data': project.to_dict()}), 201
```

## 🗄️ Banco de Dados

### Compatibilidade PostgreSQL/SQLite
```python
# ✅ USAR (compatível com ambos)
db.Column(db.Integer)
db.Column(db.String(100))
db.Column(db.Text)
db.Column(db.JSON)        # ✅ JSON (não JSONB)
db.Column(db.DateTime)
db.Column(db.Boolean)

# ❌ NUNCA usar (específico PostgreSQL)
db.Column(JSONB)          # ❌ Usar JSON
db.Column(ARRAY)          # ❌ Usar relação 1:N
db.Column(UUID)           # ❌ Usar String(36)
```

### Campos Obrigatórios em Models
```python
class Project(db.Model):
    __tablename__ = 'projects'
    
    # ✅ SEMPRE incluir
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)  # Soft delete
```

## 🌐 APIs REST

### Padrão de URLs
```python
# ✅ CORRETO
GET    /api/companies
GET    /api/companies/1
POST   /api/companies
PUT    /api/companies/1
DELETE /api/companies/1

# ❌ ERRADO
GET /api/getCompanies        # Verbo na URL
POST /api/createCompany       # Verbo na URL
```

### Response Format
```python
# ✅ Sucesso
return jsonify({
    'success': True,
    'data': {'id': 1, 'name': 'Project'}
}), 201

# ✅ Erro
return jsonify({
    'success': False,
    'error': 'Nome obrigatório'
}), 400
```

## 🚫 NUNCA Fazer (Crítico)

### Segurança
```python
# ❌ PROIBIDO - Credenciais
password = "123456"                    # ❌ Usar os.getenv()

# ❌ PROIBIDO - SQL Injection
query = f"SELECT * FROM users WHERE name = '{name}'"  # ❌ Usar ORM

# ❌ PROIBIDO - Senha sem hash
user.password = request.form['password']  # ❌ Usar bcrypt
```

### Código Python
```python
# ❌ PROIBIDO - Bare except
try:
    do_something()
except:              # ❌ Especificar exceção
    pass

# ❌ PROIBIDO - print para debug
print(user_data)     # ❌ Usar logger.info()

# ❌ PROIBIDO - eval/exec
eval(user_input)     # ❌ NUNCA executar código arbitrário
```

### Banco de Dados
```python
# ❌ PROIBIDO - Query sem paginação
projects = Project.query.all()  # ❌ Usar .paginate()

# ❌ PROIBIDO - N+1 queries
for project in projects:
    print(project.company.name)  # ❌ Usar joinedload()

# ❌ PROIBIDO - Commits em loop
for item in items:
    db.session.add(Project(**item))
    db.session.commit()  # ❌ Commit fora do loop
```

### APIs
```python
# ❌ PROIBIDO - Rota sem autenticação
@app.route('/api/users')     # ❌ Falta @login_required
def list_users():
    pass

# ❌ PROIBIDO - GET modificando dados
@app.route('/api/delete/<int:id>', methods=['GET'])  # ❌ Usar DELETE
def delete_item(id):
    pass
```

## 📝 Exemplos Completos

### Model com Auditoria
```python
from datetime import datetime
from models import db

class Project(db.Model):
    """Modelo de Projeto."""
    __tablename__ = 'projects'
    
    # PK
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # FK
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Auditoria (OBRIGATÓRIO)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
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

### Rota CRUD Completa
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from middleware.auto_log_decorator import auto_log_crud
from models import db, Project

api = Blueprint('projects', __name__)

@api.route('/api/companies/<int:company_id>/projects', methods=['POST'])
@login_required
@auto_log_crud('project')
def create_project(company_id):
    """Cria novo projeto."""
    data = request.get_json()
    
    # Validação
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Nome obrigatório'}), 400
    
    # Criar
    project = Project(
        name=data['name'],
        description=data.get('description'),
        company_id=company_id,
        created_by=current_user.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({'success': True, 'data': project.to_dict()}), 201
```

## 🎯 Prioridades

1. **Segurança** - Sempre em primeiro lugar
2. **Compatibilidade** - PostgreSQL E SQLite
3. **Padrões** - Seguir governança
4. **Performance** - Paginar, eager loading
5. **Manutenibilidade** - Código legível

## 📖 Documentação Completa

Consulte `docs/governance/` para padrões completos:
- Código: `CODING_STANDARDS.md`
- Database: `DATABASE_STANDARDS.md`
- APIs: `API_STANDARDS.md`
- Proibido: `FORBIDDEN_PATTERNS.md`

---

**Ao sugerir código, SEMPRE:**
1. Verificar se segue estes padrões
2. Incluir validações e error handling
3. Incluir docstrings
4. Usar nomenclatura correta (snake_case/PascalCase)
5. Adicionar `@login_required` em rotas protegidas
6. Adicionar `@auto_log_crud` em rotas CRUD
7. Garantir compatibilidade PostgreSQL/SQLite
8. Evitar anti-patterns listados

**Versão:** 1.0
**Última atualização:** 18/10/2025

