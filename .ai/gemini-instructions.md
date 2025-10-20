# Instruções para Google Gemini - Projeto GestaoVersus

> Cole este conteúdo no início da sua conversa com o Gemini para que ele siga a governança do projeto.

---

## 🎯 Contexto do Projeto

Você está ajudando no desenvolvimento do **GestaoVersus**, um sistema de gestão empresarial modular.

**Stack Tecnológica:**
- Backend: Python 3.9+ com Flask 2.3.3
- Database: PostgreSQL (produção) + SQLite (desenvolvimento)
- ORM: SQLAlchemy 2.0.21
- Frontend: Jinja2 Templates + JavaScript Vanilla (ES6+)
- Arquitetura: Modular com Flask Blueprints

## 📚 Governança - LEIA ANTES DE RESPONDER

Este projeto tem governança técnica COMPLETA em `docs/governance/`:

1. **TECH_STACK.md** - Tecnologias aprovadas e proibidas
2. **ARCHITECTURE.md** - Arquitetura do sistema (Blueprints, camadas)
3. **CODING_STANDARDS.md** - Padrões Python (PEP 8 adaptado)
4. **DATABASE_STANDARDS.md** - Padrões de DB (compatibilidade PG/SQLite)
5. **API_STANDARDS.md** - Padrões REST (URLs, status codes, responses)
6. **FORBIDDEN_PATTERNS.md** - Anti-patterns PROIBIDOS
7. **DECISION_LOG.md** - Decisões arquiteturais (ADR)

## ✅ Stack Aprovada - APENAS USAR ESTAS

**Backend:**
- Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21
- Flask-Login, Flask-Migrate, bcrypt, Werkzeug
- PostgreSQL 12+, SQLite 3.x

**Frontend:**
- Jinja2 (templates)
- JavaScript Vanilla ES6+ (NÃO usar frameworks)

**Testes:**
- pytest, pytest-flask, Black, Flake8

## ❌ Tecnologias PROIBIDAS - NUNCA SUGERIR

- Django, FastAPI (usar Flask)
- MongoDB, MySQL (usar PostgreSQL/SQLite)
- jQuery, React, Vue, Angular, TypeScript (usar JS Vanilla)
- GraphQL (usar REST)

## 💻 Padrões de Código Obrigatórios

### Nomenclatura
```python
# ✅ CORRETO
def calculate_total_revenue(company_id: int) -> float:
    """Calcula receita total da empresa."""
    pass

class ProjectService:
    """Serviço de gerenciamento de projetos."""
    pass

MAX_FILE_SIZE = 5242880
```

### Estrutura de Rota Flask
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from middleware.auto_log_decorator import auto_log_crud

@app.route('/api/projects', methods=['POST'])
@login_required                    # ✅ OBRIGATÓRIO
@auto_log_crud('project')          # ✅ Para operações CRUD
def create_project():
    """Cria novo projeto."""
    data = request.get_json()
    
    # ✅ Validar entrada
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'error': 'Nome obrigatório'
        }), 400
    
    # ✅ Criar entidade
    project = Project(name=data['name'])
    db.session.add(project)
    db.session.commit()
    
    # ✅ Response padronizado
    return jsonify({
        'success': True,
        'data': project.to_dict()
    }), 201
```

### Models - Campos Obrigatórios
```python
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    
    # ✅ SEMPRE incluir auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)  # Soft delete
```

## 🗄️ Banco de Dados - Compatibilidade

### ✅ USAR (Compatível PostgreSQL + SQLite)
```python
db.Column(db.Integer)
db.Column(db.String(100))
db.Column(db.Text)
db.Column(db.JSON)          # ✅ JSON genérico
db.Column(db.DateTime)
db.Column(db.Boolean)
db.Column(db.Numeric(10,2))
```

### ❌ NUNCA USAR (Específico PostgreSQL)
```python
db.Column(JSONB)            # ❌ Usar db.JSON
db.Column(ARRAY)            # ❌ Criar tabela relacionada
db.Column(UUID)             # ❌ Usar String(36)
```

## 🌐 APIs REST - Padrões

### URLs
```python
# ✅ CORRETO
GET    /api/companies
GET    /api/companies/{id}
POST   /api/companies
PUT    /api/companies/{id}
DELETE /api/companies/{id}

# ❌ ERRADO
GET /api/getCompanies           # Verbo na URL
POST /api/companies/create      # Ação na URL
```

### Response Format Padronizado
```python
# ✅ Sucesso
{'success': True, 'data': {...}}

# ✅ Erro
{'success': False, 'error': 'Mensagem de erro'}

# ✅ Lista com paginação
{
    'success': True,
    'data': [...],
    'total': 50,
    'page': 1,
    'pages': 3
}
```

### Status Codes
- 200 OK (GET, PUT)
- 201 Created (POST)
- 204 No Content (DELETE)
- 400 Bad Request (dados inválidos)
- 401 Unauthorized (não autenticado)
- 403 Forbidden (sem permissão)
- 404 Not Found (recurso não existe)

## 🚫 PROIBIDO - Nunca Sugerir

### Segurança (🔴 Crítico)
```python
# ❌ Credenciais hardcoded
password = "123456"                               # ❌ Usar os.getenv()

# ❌ SQL injection
query = f"SELECT * FROM users WHERE id = {id}"   # ❌ Usar ORM

# ❌ Senha sem hash
user.password = request.form['password']         # ❌ Usar bcrypt

# ❌ Logar dados sensíveis
logger.info(f"Password: {password}")             # ❌ NUNCA
```

### Código Python (🟡 Alto)
```python
# ❌ Bare except
try:
    do_something()
except:                                          # ❌ Especificar exceção
    pass

# ❌ print() para debug
print(f"User: {user}")                          # ❌ Usar logger

# ❌ eval/exec
eval(user_input)                                # ❌ NUNCA

# ❌ import *
from flask import *                             # ❌ Imports explícitos
```

### Banco de Dados (🟡 Alto)
```python
# ❌ Query sem paginação
Project.query.all()                             # ❌ Usar .paginate()

# ❌ N+1 queries
for project in projects:
    print(project.company.name)                  # ❌ Usar joinedload()

# ❌ Hard delete
db.session.delete(project)                      # ❌ Soft delete (is_deleted=True)
```

### APIs (🟡 Alto)
```python
# ❌ Rota sem autenticação
@app.route('/api/users')                        # ❌ Adicionar @login_required
def list_users():
    pass

# ❌ GET modificando dados
@app.route('/delete/<id>', methods=['GET'])     # ❌ Usar DELETE
def delete_item(id):
    pass
```

## 📝 Ao Sugerir Código, SEMPRE:

1. ✅ Seguir nomenclatura (snake_case, PascalCase)
2. ✅ Incluir docstrings (formato Google)
3. ✅ Incluir type hints em funções públicas
4. ✅ Validar entrada do usuário
5. ✅ Usar `@login_required` em rotas protegidas
6. ✅ Usar `@auto_log_crud` em rotas CRUD
7. ✅ Garantir compatibilidade PostgreSQL + SQLite
8. ✅ Response format padronizado `{'success': bool, 'data': ...}`
9. ✅ Evitar TODOS os anti-patterns listados
10. ✅ Incluir error handling adequado

## 🎯 Arquitetura - Organização

```
Camadas (top-down):
1. Templates (Jinja2)      - Apenas apresentação
2. Routes (Blueprints)     - Validação + chamada de services
3. Services                - Lógica de negócio
4. Models (SQLAlchemy)     - Estrutura de dados
5. Database                - PostgreSQL/SQLite
```

**Regra:** Lógica de negócio SEMPRE em services, NUNCA em routes ou templates.

## 📖 Documentação Completa

Para detalhes completos, consulte:
- `docs/governance/CODING_STANDARDS.md` - Padrões completos de código
- `docs/governance/DATABASE_STANDARDS.md` - Padrões completos de DB
- `docs/governance/API_STANDARDS.md` - Padrões completos de API
- `docs/governance/FORBIDDEN_PATTERNS.md` - Lista completa de proibições

## ✅ Confirmação

Por favor, confirme que você:
1. ✅ Leu e entendeu a governança
2. ✅ Vai seguir APENAS a stack aprovada
3. ✅ NUNCA vai sugerir tecnologias proibidas
4. ✅ Vai seguir todos os padrões de código
5. ✅ Vai evitar todos os anti-patterns
6. ✅ Vai garantir compatibilidade PostgreSQL + SQLite

**Responda: "✅ Confirmo que li e vou seguir a governança do projeto GestaoVersus."**

---

Agora você está pronto para ajudar no projeto seguindo todos os padrões!

