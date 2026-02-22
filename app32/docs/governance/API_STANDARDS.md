# 🌐 Padrões de API REST

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório

---

## 🎯 Princípios REST

1. **Stateless** - Cada request contém toda informação necessária
2. **Resource-Based** - URLs representam recursos, não ações
3. **HTTP Methods** - Usar verbos HTTP corretamente
4. **Consistent** - Padrões consistentes em toda API
5. **Versionado** - Suporte a múltiplas versões

---

## 📍 URL Structure

### Nomenclatura de Endpoints

```
✅ BOM - Recursos no plural, hierárquico

GET    /api/companies
GET    /api/companies/1
GET    /api/companies/1/projects
GET    /api/companies/1/projects/5
POST   /api/companies/1/projects
PUT    /api/companies/1/projects/5
DELETE /api/companies/1/projects/5

❌ RUIM

GET /api/company              # Singular
GET /api/getCompanies         # Verbo na URL
GET /api/companies/create     # Ação na URL
GET /api/companies-list       # Hífen no recurso
POST /api/createProject       # Verbo + PascalCase
```

### Hierarquia de Recursos

```
✅ BOM - Máximo 2 níveis de aninhamento

/api/companies/{id}/projects
/api/projects/{id}/tasks

✅ Usar query params para recursos relacionados profundos

/api/tasks?project_id=5&user_id=10

❌ RUIM - Aninhamento excessivo

/api/companies/{id}/departments/{id}/teams/{id}/members/{id}
```

### Query Parameters

```
✅ BOM - snake_case para query params

GET /api/projects?status=active&sort_by=created_at&order=desc
GET /api/users?is_active=true&role=admin&page=2&per_page=20

Filtros comuns:
- page, per_page        → Paginação
- sort_by, order        → Ordenação
- search, q             → Busca
- filter_[campo]        → Filtros específicos
- fields                → Seleção de campos
- include               → Incluir relacionamentos

❌ RUIM

GET /api/projects?Status=active           # PascalCase
GET /api/projects?sortBy=created_at       # camelCase
GET /api/projects?filter-status=active    # Hífen
```

---

## 🔤 HTTP Methods

### GET - Buscar Recursos

```python
# ✅ Listar todos
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    projects = Project.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in projects.items],
        'total': projects.total,
        'page': page,
        'pages': projects.pages
    })

# ✅ Buscar um específico
@api.route('/api/projects/<int:id>', methods=['GET'])
@login_required
def get_project(id):
    project = Project.query.get_or_404(id)
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    })

# ❌ RUIM - GET modificando dados
@api.route('/api/projects/<int:id>/activate', methods=['GET'])  # ERRADO!
def activate_project(id):
    project.active = True
    db.session.commit()
```

**Regras GET:**
- ✅ Idempotente (mesma resposta sempre)
- ✅ Sem efeitos colaterais (não modifica dados)
- ✅ Cacheable
- ❌ Nunca usar para criar/modificar/deletar

### POST - Criar Recursos

```python
# ✅ BOM
@api.route('/api/companies/<int:company_id>/projects', methods=['POST'])
@login_required
@auto_log_crud('project')
def create_project(company_id):
    # Validar dados
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'error': 'Nome obrigatório'
        }), 400
    
    # Criar recurso
    project = Project(
        name=data['name'],
        description=data.get('description'),
        company_id=company_id
    )
    
    db.session.add(project)
    db.session.commit()
    
    # Retornar 201 Created com Location header
    return jsonify({
        'success': True,
        'data': project.to_dict()
    }), 201, {'Location': f'/api/projects/{project.id}'}

# ❌ RUIM
@api.route('/api/createProject', methods=['POST'])  # Verbo na URL
def create_project():
    # Sem validação
    project = Project(**request.json)  # Perigoso!
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict())  # Sem status 201
```

**Regras POST:**
- ✅ Retornar status 201 Created
- ✅ Incluir Location header com URL do recurso criado
- ✅ Validar todos os dados
- ✅ Retornar o recurso criado

### PUT - Atualizar Recurso Completo

```python
# ✅ BOM - Atualização completa
@api.route('/api/projects/<int:id>', methods=['PUT'])
@login_required
@auto_log_crud('project')
def update_project(id):
    project = Project.query.get_or_404(id)
    data = request.get_json()
    
    # Atualizar todos os campos
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.status = data.get('status', project.status)
    project.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    })

# ❌ RUIM
@api.route('/api/updateProject/<int:id>', methods=['PUT'])  # Verbo na URL
def update_project(id):
    project = Project.query.get(id)
    if not project:
        return "Not found", 404  # Resposta inconsistente
    # Atualização sem validação
```

**Regras PUT:**
- ✅ Idempotente (mesma operação = mesmo resultado)
- ✅ Substituição completa do recurso
- ✅ Retornar recurso atualizado

### PATCH - Atualização Parcial

```python
# ✅ BOM - Atualização parcial
@api.route('/api/projects/<int:id>', methods=['PATCH'])
@login_required
@auto_log_crud('project')
def partial_update_project(id):
    project = Project.query.get_or_404(id)
    data = request.get_json()
    
    # Atualizar apenas campos enviados
    allowed_fields = ['name', 'description', 'status']
    for field in allowed_fields:
        if field in data:
            setattr(project, field, data[field])
    
    project.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    })
```

**Regras PATCH:**
- ✅ Atualizar apenas campos enviados
- ✅ Validar campos permitidos
- ✅ Retornar recurso atualizado

### DELETE - Remover Recurso

```python
# ✅ BOM - Soft delete (preferido)
@api.route('/api/projects/<int:id>', methods=['DELETE'])
@login_required
@auto_log_crud('project')
def delete_project(id):
    project = Project.query.get_or_404(id)
    
    # Soft delete
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    project.deleted_by = current_user.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Projeto removido com sucesso'
    }), 200

# ✅ Também aceito - Hard delete com confirmação
@api.route('/api/projects/<int:id>', methods=['DELETE'])
@login_required
def delete_project_hard(id):
    project = Project.query.get_or_404(id)
    
    # Verificar dependências
    if project.tasks.count() > 0:
        return jsonify({
            'success': False,
            'error': 'Projeto possui tarefas vinculadas'
        }), 400
    
    db.session.delete(project)
    db.session.commit()
    
    return '', 204  # No Content

# ❌ RUIM
@api.route('/api/projects/<int:id>/delete', methods=['POST'])  # Ação na URL + método errado
```

**Regras DELETE:**
- ✅ Preferir soft delete (is_deleted=True)
- ✅ Verificar dependências antes de deletar
- ✅ Retornar 200 (com mensagem) ou 204 (sem corpo)
- ✅ Idempotente (deletar 2x = mesmo resultado)

---

## 📦 Formato de Resposta

### Resposta de Sucesso

```json
// ✅ Sucesso - Recurso único
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Projeto X",
    "created_at": "2025-10-18T10:00:00Z"
  }
}

// ✅ Sucesso - Lista com paginação
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

// ✅ Sucesso - Operação sem retorno
{
  "success": true,
  "message": "Operação realizada com sucesso"
}
```

### Resposta de Erro

```json
// ✅ Erro de validação (400)
{
  "success": false,
  "error": "Dados inválidos",
  "details": {
    "name": ["Campo obrigatório"],
    "email": ["Email inválido"]
  }
}

// ✅ Erro de autenticação (401)
{
  "success": false,
  "error": "Não autenticado",
  "message": "Faça login para acessar este recurso"
}

// ✅ Erro de permissão (403)
{
  "success": false,
  "error": "Acesso negado",
  "message": "Você não tem permissão para esta operação"
}

// ✅ Erro de recurso não encontrado (404)
{
  "success": false,
  "error": "Recurso não encontrado",
  "resource": "project",
  "id": 999
}

// ✅ Erro de servidor (500)
{
  "success": false,
  "error": "Erro interno do servidor",
  "request_id": "abc123"  // Para rastreamento
}
```

---

## 🔢 Status Codes

### Status Codes Obrigatórios

| Código | Nome | Quando Usar |
|--------|------|-------------|
| **200** | OK | GET, PUT, PATCH com sucesso |
| **201** | Created | POST com sucesso |
| **204** | No Content | DELETE com sucesso (sem corpo) |
| **400** | Bad Request | Dados inválidos |
| **401** | Unauthorized | Não autenticado |
| **403** | Forbidden | Sem permissão |
| **404** | Not Found | Recurso não existe |
| **409** | Conflict | Conflito (ex: email duplicado) |
| **422** | Unprocessable Entity | Validação de negócio falhou |
| **500** | Internal Server Error | Erro não tratado |

### Exemplo de Uso

```python
# 200 OK
return jsonify({'success': True, 'data': data}), 200

# 201 Created
return jsonify({'success': True, 'data': new_resource}), 201

# 204 No Content
return '', 204

# 400 Bad Request
return jsonify({'success': False, 'error': 'Invalid data'}), 400

# 401 Unauthorized
return jsonify({'success': False, 'error': 'Not authenticated'}), 401

# 403 Forbidden
return jsonify({'success': False, 'error': 'Access denied'}), 403

# 404 Not Found
return jsonify({'success': False, 'error': 'Not found'}), 404

# 409 Conflict
return jsonify({'success': False, 'error': 'Email already exists'}), 409

# 422 Unprocessable Entity
return jsonify({'success': False, 'error': 'Invalid business rule'}), 422

# 500 Internal Server Error
return jsonify({'success': False, 'error': 'Server error'}), 500
```

---

## 🔐 Autenticação e Autorização

### Authentication

```python
# ✅ Usar Flask-Login
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    # current_user disponível automaticamente
    projects = Project.query.filter_by(company_id=current_user.company_id).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in projects]})

# ✅ Retornar 401 se não autenticado
@login_required  # Flask-Login já retorna 401 automaticamente
```

### Authorization

```python
# ✅ Verificar permissões
@api.route('/api/projects/<int:id>', methods=['DELETE'])
@login_required
def delete_project(id):
    project = Project.query.get_or_404(id)
    
    # Verificar se usuário pode deletar
    if not current_user.can_delete(project):
        return jsonify({
            'success': False,
            'error': 'Acesso negado'
        }), 403
    
    # Prosseguir com deleção
    project.is_deleted = True
    db.session.commit()
    
    return jsonify({'success': True})
```

---

## 📄 Paginação

### Padrão Obrigatório

```python
# ✅ Sempre paginar listas
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    # Parâmetros
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Limitar per_page máximo
    per_page = min(per_page, 100)
    
    # Query com paginação
    pagination = Project.query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in pagination.items],
        'pagination': {
            'total': pagination.total,
            'page': pagination.page,
            'per_page': pagination.per_page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })
```

---

## 🔍 Filtros e Busca

### Filtros Simples

```python
# ✅ Query params para filtros
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    query = Project.query
    
    # Filtro por status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # Filtro booleano
    is_active = request.args.get('is_active', type=bool)
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    # Filtro de data
    start_date = request.args.get('start_date')
    if start_date:
        query = query.filter(Project.start_date >= start_date)
    
    projects = query.all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in projects]})
```

### Busca por Texto

```python
# ✅ Usar 'q' ou 'search' para busca textual
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    search = request.args.get('q', '')
    
    query = Project.query
    if search:
        query = query.filter(
            db.or_(
                Project.name.ilike(f'%{search}%'),
                Project.description.ilike(f'%{search}%')
            )
        )
    
    projects = query.all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in projects]})
```

---

## 📊 Ordenação

```python
# ✅ Usar sort_by e order
@api.route('/api/projects', methods=['GET'])
@login_required
def list_projects():
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')
    
    # Validar campos permitidos
    allowed_sorts = ['name', 'created_at', 'updated_at', 'status']
    if sort_by not in allowed_sorts:
        sort_by = 'created_at'
    
    # Construir query
    query = Project.query
    
    if order == 'asc':
        query = query.order_by(getattr(Project, sort_by).asc())
    else:
        query = query.order_by(getattr(Project, sort_by).desc())
    
    projects = query.all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in projects]})
```

---

## 🔄 Versionamento

### Estratégia

```python
# ✅ Versão na URL (preferido)
/api/v1/projects
/api/v2/projects

# ✅ Implementação com blueprints
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
api_v2 = Blueprint('api_v2', __name__, url_prefix='/api/v2')

@api_v1.route('/projects')
def list_projects_v1():
    # Versão antiga
    pass

@api_v2.route('/projects')
def list_projects_v2():
    # Versão nova
    pass
```

---

## 🧪 Exemplo Completo de CRUD

```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Project
from middleware.auto_log_decorator import auto_log_crud

api = Blueprint('projects_api', __name__, url_prefix='/api')

# LIST
@api.route('/companies/<int:company_id>/projects', methods=['GET'])
@login_required
def list_projects(company_id):
    """Lista projetos de uma empresa."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    pagination = (
        Project.query
        .filter_by(company_id=company_id, is_deleted=False)
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    
    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })

# GET
@api.route('/projects/<int:id>', methods=['GET'])
@login_required
def get_project(id):
    """Busca projeto específico."""
    project = Project.query.get_or_404(id)
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    })

# CREATE
@api.route('/companies/<int:company_id>/projects', methods=['POST'])
@login_required
@auto_log_crud('project')
def create_project(company_id):
    """Cria novo projeto."""
    data = request.get_json()
    
    # Validação
    if not data or 'name' not in data:
        return jsonify({
            'success': False,
            'error': 'Nome obrigatório'
        }), 400
    
    # Criar
    project = Project(
        name=data['name'],
        description=data.get('description'),
        company_id=company_id,
        created_by=current_user.id
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    }), 201

# UPDATE
@api.route('/projects/<int:id>', methods=['PUT'])
@login_required
@auto_log_crud('project')
def update_project(id):
    """Atualiza projeto."""
    project = Project.query.get_or_404(id)
    data = request.get_json()
    
    # Validação de permissão
    if not current_user.can_edit(project):
        return jsonify({
            'success': False,
            'error': 'Acesso negado'
        }), 403
    
    # Atualizar
    project.name = data.get('name', project.name)
    project.description = data.get('description', project.description)
    project.updated_by = current_user.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': project.to_dict()
    })

# DELETE
@api.route('/projects/<int:id>', methods=['DELETE'])
@login_required
@auto_log_crud('project')
def delete_project(id):
    """Remove projeto (soft delete)."""
    project = Project.query.get_or_404(id)
    
    # Validação de permissão
    if not current_user.can_delete(project):
        return jsonify({
            'success': False,
            'error': 'Acesso negado'
        }), 403
    
    # Soft delete
    project.is_deleted = True
    project.deleted_by = current_user.id
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Projeto removido com sucesso'
    })
```

---

## ✅ Checklist de Nova API

- [ ] URLs seguem padrão REST (/api/resources)
- [ ] Métodos HTTP corretos (GET, POST, PUT, DELETE)
- [ ] Status codes apropriados (200, 201, 400, 404, etc.)
- [ ] Formato de resposta consistente (success, data, error)
- [ ] Autenticação obrigatória (@login_required)
- [ ] Validação de dados de entrada
- [ ] Paginação em listas
- [ ] Logging automático (@auto_log_crud)
- [ ] Tratamento de erros
- [ ] Documentação

---

**Referência:** RESTful API Design Best Practices  
**Próxima revisão:** Semestral



