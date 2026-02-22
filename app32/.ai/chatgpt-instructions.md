# Instruções para ChatGPT - Projeto GestaoVersus

> Use este conteúdo como Custom Instructions no ChatGPT ou cole no início da conversa.

---

## 🎯 Sobre o Projeto

Você está ajudando no **GestaoVersus**, um sistema de gestão empresarial modular com:

- **Backend:** Python 3.9+ + Flask 2.3.3 + SQLAlchemy 2.0.21
- **Database:** PostgreSQL (produção) / SQLite (desenvolvimento)
- **Frontend:** Jinja2 Templates + JavaScript Vanilla ES6+
- **Arquitetura:** Modular com Flask Blueprints

## 📚 Governança Técnica (Obrigatório Seguir)

Este projeto tem **governança completa** em `docs/governance/`:

1. **TECH_STACK.md** - Tecnologias aprovadas/proibidas
2. **ARCHITECTURE.md** - Arquitetura modular com Blueprints
3. **CODING_STANDARDS.md** - Padrões Python (PEP 8 adaptado)
4. **DATABASE_STANDARDS.md** - Padrões DB (compatibilidade PG/SQLite)
5. **API_STANDARDS.md** - Padrões REST
6. **FORBIDDEN_PATTERNS.md** - Anti-patterns proibidos
7. **DECISION_LOG.md** - Decisões arquiteturais (ADR)

## ✅ O Que Usar (Stack Aprovada)

**Backend:**
- Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21
- Flask-Login, bcrypt, Werkzeug, pytest

**Database:**
- PostgreSQL 12+ (produção)
- SQLite 3.x (desenvolvimento)
- **Código DEVE funcionar em AMBOS**

**Frontend:**
- Jinja2, JavaScript Vanilla ES6+

## ❌ O Que NÃO Usar (Proibido)

- ❌ Django, FastAPI
- ❌ MongoDB, MySQL
- ❌ jQuery, React, Vue, Angular, TypeScript
- ❌ GraphQL

## 💻 Padrões de Código

### Nomenclatura
```python
# ✅ Funções/variáveis: snake_case
def calculate_total_value(company_id: int) -> float:
    """Calcula valor total."""
    pass

# ✅ Classes: PascalCase
class ProjectService:
    pass

# ✅ Constantes: UPPER_SNAKE_CASE
MAX_FILE_SIZE = 5242880
```

### Rota Flask Padrão
```python
from flask import request, jsonify
from flask_login import login_required
from middleware.auto_log_decorator import auto_log_crud

@app.route('/api/projects', methods=['POST'])
@login_required              # ✅ Obrigatório
@auto_log_crud('project')    # ✅ Para CRUD
def create_project():
    """Cria projeto."""
    data = request.get_json()
    
    # Validar
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'error': 'Nome obrigatório'
        }), 400
    
    # Criar
    project = Project(name=data['name'])
    db.session.add(project)
    db.session.commit()
    
    # Response padronizado
    return jsonify({
        'success': True,
        'data': project.to_dict()
    }), 201
```

### Model Padrão
```python
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    
    # ✅ Auditoria obrigatória
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
```

## 🗄️ Database - Compatibilidade

### ✅ Usar (Compatível)
```python
db.Column(db.Integer)
db.Column(db.String(100))
db.Column(db.Text)
db.Column(db.JSON)           # ✅ Não JSONB
db.Column(db.DateTime)
db.Column(db.Boolean)
```

### ❌ Não Usar (Incompatível)
```python
db.Column(JSONB)             # ❌ PostgreSQL only
db.Column(ARRAY)             # ❌ PostgreSQL only
db.Column(UUID)              # ❌ PostgreSQL only
```

## 🌐 APIs REST

### URLs
```python
# ✅ Correto
GET    /api/companies
POST   /api/companies
PUT    /api/companies/{id}
DELETE /api/companies/{id}

# ❌ Errado
GET /api/getCompanies        # Verbo
```

### Response
```json
// ✅ Sucesso
{"success": true, "data": {...}}

// ✅ Erro
{"success": false, "error": "Mensagem"}
```

### Status Codes
- 200 OK, 201 Created, 204 No Content
- 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found

## 🚫 NUNCA Fazer

### Segurança
```python
# ❌ Credenciais hardcoded
password = "123456"

# ❌ SQL injection
query = f"SELECT * FROM users WHERE id={id}"

# ❌ Senha sem hash
user.password = password
```

### Código
```python
# ❌ Bare except
try: x
except: pass

# ❌ print() debug
print(data)

# ❌ eval/exec
eval(code)
```

### Database
```python
# ❌ Sem paginação
Project.query.all()

# ❌ N+1 queries
for p in projects:
    print(p.company.name)
```

## 📝 Ao Gerar Código, SEMPRE:

1. ✅ Nomenclatura correta (snake_case/PascalCase)
2. ✅ Docstrings em funções públicas
3. ✅ Type hints
4. ✅ Validação de entrada
5. ✅ `@login_required` em rotas
6. ✅ `@auto_log_crud` em CRUD
7. ✅ Response padronizado
8. ✅ Compatibilidade PostgreSQL + SQLite
9. ✅ Soft delete (is_deleted)
10. ✅ Error handling

## 🎯 Como me Usar Melhor

**Bom:**
```
"Crie API REST para projetos seguindo:
- docs/governance/API_STANDARDS.md
- docs/governance/CODING_STANDARDS.md"
```

**Ruim:**
```
"Crie API para projetos"
```

## ✅ Confirmação

Responda: **"✅ Vou seguir a governança do GestaoVersus."**

---

**Versão:** 1.0  
**Data:** 18/10/2025

