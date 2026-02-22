# 🏢 Semana 2: Companies - Migração Incremental

**Data:** 02/01/2026  
**Objetivo:** Implementar funcionalidade completa de Companies (Backend + Frontend)  
**Tempo Estimado:** 5-7 dias

---

## 📋 Plano de Execução

### Dia 1-2: Backend (Models + Schemas + APIs)
- [ ] Criar estrutura de pastas
- [ ] Configurar SQLAlchemy + Alembic
- [ ] Criar `models/company.py`
- [ ] Criar `schemas/company.py`
- [ ] Criar `api/resources/company.py`
- [ ] Criar migration inicial
- [ ] Testar APIs com Postman/curl

### Dia 3-4: Frontend (Migração de Telas)
- [ ] Migrar `companies.html` → `layouts/app.html`
- [ ] Migrar `company_form.html` → `layouts/form.html`
- [ ] Conectar com APIs
- [ ] Testar CRUD completo

### Dia 5: Testes & Refinamento
- [ ] Testes de integração
- [ ] Ajustes de UX
- [ ] Validações
- [ ] Documentação

---

## 🗂️ Estrutura de Pastas (Nova)

```
app32/
├── models/
│   ├── __init__.py
│   └── company.py          ← Novo
├── schemas/
│   ├── __init__.py
│   └── company.py          ← Novo
├── api/
│   ├── __init__.py
│   └── resources/
│       ├── __init__.py
│       └── company.py      ← Novo
├── services/
│   ├── __init__.py
│   └── company_service.py  ← Novo (opcional)
├── migrations/
│   └── versions/
│       └── 001_create_companies.py  ← Novo
├── templates/
│   ├── companies_v2.html   ← Migrado
│   └── company_form_v2.html ← Migrado
└── static/
    └── js/
        └── companies.js    ← Novo
```

---

## 📊 Model: Company

**Campos (baseado no APP31):**
```python
class Company(db.Model):
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    client_code = Column(String(50), unique=True)
    description = Column(Text)
    segment = Column(String(100))
    size = Column(String(50))  # Pequeno, Médio, Grande
    
    # Logos
    logo_primary = Column(String(500))
    logo_secondary = Column(String(500))
    logo_icon = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    # indicators = relationship('Indicator', back_populates='company')
    # projects = relationship('Project', back_populates='company')
```

---

## 🔄 Schema: Company

**Marshmallow Schema:**
```python
class CompanySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Company
        load_instance = True
        include_fk = True
    
    # Validações
    name = fields.String(required=True, validate=validate.Length(min=1, max=200))
    client_code = fields.String(validate=validate.Length(max=50))
    
    # Campos computados
    logo_count = fields.Method("get_logo_count")
    
    def get_logo_count(self, obj):
        count = 0
        if obj.logo_primary: count += 1
        if obj.logo_secondary: count += 1
        if obj.logo_icon: count += 1
        return count
```

---

## 🌐 API: Company Resource

**Endpoints:**
```python
GET    /api/companies          # Listar todas
GET    /api/companies/<id>     # Buscar por ID
POST   /api/companies          # Criar nova
PUT    /api/companies/<id>     # Atualizar
DELETE /api/companies/<id>     # Deletar
```

**Exemplo de Resource:**
```python
class CompanyListResource(Resource):
    def get(self):
        companies = Company.query.filter_by(is_active=True).all()
        return company_schema.dump(companies, many=True), 200
    
    def post(self):
        data = request.get_json()
        company = company_schema.load(data)
        db.session.add(company)
        db.session.commit()
        return company_schema.dump(company), 201

class CompanyResource(Resource):
    def get(self, company_id):
        company = Company.query.get_or_404(company_id)
        return company_schema.dump(company), 200
    
    def put(self, company_id):
        company = Company.query.get_or_404(company_id)
        data = request.get_json()
        company = company_schema.load(data, instance=company, partial=True)
        db.session.commit()
        return company_schema.dump(company), 200
    
    def delete(self, company_id):
        company = Company.query.get_or_404(company_id)
        company.is_active = False  # Soft delete
        db.session.commit()
        return '', 204
```

---

## 🎨 Frontend: companies_v2.html

**Estrutura:**
```html
{% extends "layouts/app.html" %}

{% block content %}
<div class="companies-page">
  <header class="page-header">
    <div>
      <h1 class="text-h1">Empresas</h1>
      <p class="text-sm">Gerencie as empresas cadastradas</p>
    </div>
    <a href="/companies/new" class="btn btn-primary">+ Nova Empresa</a>
  </header>

  <div class="companies-grid" id="companiesGrid">
    <!-- Cards carregados via JavaScript -->
  </div>
</div>

<script src="{{ url_for('static', filename='js/companies.js') }}"></script>
{% endblock %}
```

**JavaScript (companies.js):**
```javascript
async function loadCompanies() {
  const response = await fetch('/api/companies');
  const companies = await response.json();
  
  const grid = document.getElementById('companiesGrid');
  grid.innerHTML = companies.map(company => `
    <div class="company-card">
      <div class="company-card-header">
        <h3>${company.name}</h3>
        <span class="badge">${company.client_code || 'Sem código'}</span>
      </div>
      <p>${company.description || 'Sem descrição'}</p>
      <div class="company-card-footer">
        <a href="/companies/${company.id}/edit" class="btn btn-secondary">Editar</a>
        <button onclick="deleteCompany(${company.id})" class="btn btn-ghost">Excluir</button>
      </div>
    </div>
  `).join('');
}

document.addEventListener('DOMContentLoaded', loadCompanies);
```

---

## 📝 Frontend: company_form_v2.html

**Estrutura:**
```html
{% extends "layouts/form.html" %}

{% block form_title %}
  {{ 'Editar Empresa' if company else 'Nova Empresa' }}
{% endblock %}

{% block form_subtitle %}
  {{ 'Atualize as informações da empresa' if company else 'Preencha os dados da nova empresa' }}
{% endblock %}

{% block form_content %}
  <div class="form-group">
    <label class="form-label">Nome da Empresa *</label>
    <input type="text" class="form-input" id="name" required>
  </div>

  <div class="form-group">
    <label class="form-label">Código do Cliente</label>
    <input type="text" class="form-input" id="client_code">
  </div>

  <div class="form-group">
    <label class="form-label">Descrição</label>
    <textarea class="form-textarea" id="description"></textarea>
  </div>

  <div class="form-group">
    <label class="form-label">Segmento</label>
    <select class="form-select" id="segment">
      <option value="">Selecione...</option>
      <option value="Tecnologia">Tecnologia</option>
      <option value="Saúde">Saúde</option>
      <option value="Educação">Educação</option>
    </select>
  </div>
{% endblock %}

{% block form_buttons %}
  <button type="button" class="btn btn-secondary" onclick="window.history.back()">Cancelar</button>
  <button type="submit" class="btn btn-primary" id="submitBtn">Salvar</button>
{% endblock %}
```

---

## ✅ Checklist de Implementação

### Backend
- [ ] Criar `models/__init__.py`
- [ ] Criar `models/company.py`
- [ ] Criar `schemas/__init__.py`
- [ ] Criar `schemas/company.py`
- [ ] Criar `api/__init__.py`
- [ ] Criar `api/resources/__init__.py`
- [ ] Criar `api/resources/company.py`
- [ ] Configurar SQLAlchemy no `app.py`
- [ ] Criar migration inicial
- [ ] Testar APIs

### Frontend
- [ ] Criar `companies_v2.html`
- [ ] Criar `company_form_v2.html`
- [ ] Criar `static/js/companies.js`
- [ ] Adicionar rotas no `app.py`
- [ ] Testar listagem
- [ ] Testar criação
- [ ] Testar edição
- [ ] Testar exclusão

### Testes
- [ ] CRUD completo funcional
- [ ] Validações de formulário
- [ ] Responsividade mobile
- [ ] Tratamento de erros

---

## 🎯 Resultado Esperado

**Ao final da Semana 2:**
- ✅ Backend completo de Companies (Models + Schemas + APIs)
- ✅ Frontend migrado para layouts padronizados
- ✅ CRUD completo funcional
- ✅ Testes de integração passando
- ✅ Documentação atualizada

**Próximo:** Semana 3 - Indicators

---

**Versão:** 1.0  
**Status:** 🚧 **EM ANDAMENTO**  
**Próximo Passo:** Criar estrutura de pastas e configurar SQLAlchemy
