# 🚫 Padrões Proibidos e Anti-Patterns

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório - Violações Bloqueiam PR

---

## ⚠️ O Que É Este Documento?

Lista de práticas **PROIBIDAS** no projeto. Violações devem ser corrigidas antes de merge.

**Níveis de Severidade:**
- 🔴 **CRÍTICO** - Bloqueia deploy, vulnerabilidade de segurança
- 🟡 **ALTO** - Bloqueia PR, impacta qualidade/performance
- 🟢 **MÉDIO** - Refatorar em até 1 sprint

---

## 🔐 SEGURANÇA

### 🔴 NUNCA: Credenciais no Código

```python
# ❌ PROIBIDO - Credenciais hardcoded
DATABASE_URL = "postgresql://user:password123@localhost/db"
API_KEY = "sk-abc123xyz"
SECRET_KEY = "my-secret-key"

# ✅ CORRETO - Usar variáveis de ambiente
import os
DATABASE_URL = os.getenv('DATABASE_URL')
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
```

**Consequência:** Vazamento de credenciais, acesso não autorizado

**Correção:** Usar `.env` file + python-dotenv

### 🔴 NUNCA: SQL Injection Vulnerável

```python
# ❌ PROIBIDO - String concatenation em SQL
user_input = request.args.get('name')
query = f"SELECT * FROM users WHERE name = '{user_input}'"
db.session.execute(query)

# ❌ PROIBIDO - Format strings em SQL
query = "SELECT * FROM users WHERE email = '{}'".format(email)

# ✅ CORRETO - Usar ORM
users = User.query.filter_by(name=user_input).all()

# ✅ CORRETO - Parâmetros nomeados
query = "SELECT * FROM users WHERE name = :name"
db.session.execute(query, {'name': user_input})
```

**Consequência:** Injeção SQL, perda de dados, acesso não autorizado

### 🔴 NUNCA: Senha em Plain Text

```python
# ❌ PROIBIDO - Salvar senha sem hash
user.password = request.form['password']

# ❌ PROIBIDO - Hash MD5/SHA1 (fracos)
import hashlib
user.password = hashlib.md5(password.encode()).hexdigest()

# ✅ CORRETO - Usar bcrypt
import bcrypt
user.password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

**Consequência:** Comprometimento de contas em caso de vazamento

### 🔴 NUNCA: Logar Dados Sensíveis

```python
# ❌ PROIBIDO
logger.info(f"User password: {user.password}")
logger.info(f"Credit card: {credit_card_number}")
logger.info(f"SSN: {ssn}")
print(f"Token: {api_token}")

# ✅ CORRETO - Logar apenas dados não sensíveis
logger.info(f"User login: {user.email}")
logger.info(f"Payment method: card ending {card_last4}")
```

---

## 💾 BANCO DE DADOS

### 🟡 NUNCA: Queries sem Paginação

```python
# ❌ PROIBIDO - Buscar tudo
projects = Project.query.all()
users = User.query.filter_by(active=True).all()

# ✅ CORRETO - Sempre paginar
projects = Project.query.paginate(page=1, per_page=20)
users = User.query.filter_by(active=True).limit(100).all()
```

**Consequência:** Timeout, alto uso de memória, lentidão

### 🟡 NUNCA: N+1 Query Problem

```python
# ❌ PROIBIDO - N+1 queries
projects = Project.query.all()
for project in projects:
    print(project.company.name)  # Query adicional para cada projeto!

# ✅ CORRETO - Eager loading
projects = Project.query.options(db.joinedload(Project.company)).all()
for project in projects:
    print(project.company.name)
```

**Consequência:** Performance ruim, timeout, alto uso de DB

### 🟡 NUNCA: Commits em Loop

```python
# ❌ PROIBIDO - Commit individual em loop
for data in items:
    project = Project(**data)
    db.session.add(project)
    db.session.commit()  # Lento!

# ✅ CORRETO - Bulk operation
for data in items:
    project = Project(**data)
    db.session.add(project)
db.session.commit()  # Um commit só

# ✅ AINDA MELHOR - Bulk insert
projects = [Project(**data) for data in items]
db.session.bulk_save_objects(projects)
db.session.commit()
```

**Consequência:** Lentidão extrema, locks no banco

### 🔴 NUNCA: Deletar sem Backup

```python
# ❌ PROIBIDO - Hard delete sem confirmação
@app.route('/delete-all-projects', methods=['POST'])
def delete_all():
    Project.query.delete()
    db.session.commit()
    return "Deleted"

# ✅ CORRETO - Soft delete
@app.route('/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    project.is_deleted = True
    project.deleted_at = datetime.utcnow()
    db.session.commit()
```

**Consequência:** Perda irreversível de dados

---

## 🐍 CÓDIGO PYTHON

### 🟡 NUNCA: Bare Except

```python
# ❌ PROIBIDO - Catch all sem especificar
try:
    risky_operation()
except:  # Pega tudo, inclusive KeyboardInterrupt!
    pass

# ✅ CORRETO - Específico
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except DatabaseError as e:
    logger.error(f"DB error: {e}")
    return error_response()
```

**Consequência:** Bugs silenciosos, difícil debug

### 🟡 NUNCA: Usar `eval()` ou `exec()`

```python
# ❌ PROIBIDO - Executar código arbitrário
user_code = request.form['code']
result = eval(user_code)  # MUITO PERIGOSO!

# ✅ CORRETO - Validar e processar de forma segura
allowed_operations = {'sum': sum, 'max': max, 'min': min}
if operation in allowed_operations:
    result = allowed_operations[operation](values)
```

**Consequência:** Execução remota de código, comprometimento total

### 🟡 NUNCA: Imports Circulares

```python
# ❌ PROIBIDO - models.py
from services.user_service import UserService

class User(db.Model):
    pass

# ❌ PROIBIDO - services/user_service.py
from models import User  # Circular!

# ✅ CORRETO - Import dentro da função
# services/user_service.py
def get_user():
    from models import User  # Import local
    return User.query.first()
```

**Consequência:** ImportError, aplicação não inicia

### 🟡 NUNCA: Mutable Default Arguments

```python
# ❌ PROIBIDO - Lista mutável como default
def add_item(item, items=[]):
    items.append(item)
    return items

# Problema: items é compartilhado entre chamadas!
add_item(1)  # [1]
add_item(2)  # [1, 2] ← Bug!

# ✅ CORRETO - Usar None
def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items
```

**Consequência:** Bugs sutis e difíceis de rastrear

---

## 🌐 APIs E ROTAS

### 🟡 NUNCA: Rota sem Autenticação

```python
# ❌ PROIBIDO - Dados sensíveis sem autenticação
@app.route('/api/users')
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

# ✅ CORRETO - Sempre usar @login_required
@app.route('/api/users')
@login_required
def list_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])
```

**Consequência:** Vazamento de dados, acesso não autorizado

### 🟡 NUNCA: Retornar Exceção Completa ao Cliente

```python
# ❌ PROIBIDO - Expõe stack trace
@app.route('/api/projects/<int:id>')
def get_project(id):
    try:
        project = Project.query.get(id)
        return jsonify(project.to_dict())
    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# ✅ CORRETO - Mensagem genérica ao cliente, log detalhado no servidor
@app.route('/api/projects/<int:id>')
def get_project(id):
    try:
        project = Project.query.get_or_404(id)
        return jsonify({'success': True, 'data': project.to_dict()})
    except Exception as e:
        logger.exception("Error fetching project")  # Log completo
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500
```

**Consequência:** Exposição de informações sensíveis do sistema

### 🟡 NUNCA: GET para Modificar Dados

```python
# ❌ PROIBIDO - GET modificando dados
@app.route('/api/projects/<int:id>/delete', methods=['GET'])
def delete_project(id):
    project = Project.query.get(id)
    db.session.delete(project)
    db.session.commit()

# ✅ CORRETO - Usar DELETE
@app.route('/api/projects/<int:id>', methods=['DELETE'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    project.is_deleted = True
    db.session.commit()
```

**Consequência:** CSRF, bots podem deletar dados, cache problems

---

## 🎨 FRONTEND E TEMPLATES

### 🟡 NUNCA: Lógica de Negócio no Template

```jinja2
{# ❌ PROIBIDO - Queries no template #}
{% for user in User.query.all() %}
    {{ user.name }}
{% endfor %}

{# ❌ PROIBIDO - Cálculos complexos no template #}
{% set total = 0 %}
{% for item in items %}
    {% set total = total + (item.price * item.quantity * (1 - item.discount)) %}
{% endfor %}

{# ✅ CORRETO - Passar dados processados #}
{# Na rota: users = User.query.all() #}
{% for user in users %}
    {{ user.name }}
{% endfor %}

{# Na rota: total = calculate_total(items) #}
{{ total }}
```

**Consequência:** Performance ruim, difícil manutenção

### 🟡 NUNCA: JavaScript Inline com Dados do Backend

```html
<!-- ❌ PROIBIDO - XSS vulnerável -->
<script>
    var userData = {{ user_data|safe }};  // Perigoso!
</script>

<!-- ✅ CORRETO - Usar tojson filter -->
<script>
    var userData = {{ user_data|tojson }};  // Escapado automaticamente
</script>
```

**Consequência:** XSS (Cross-Site Scripting)

---

## 📁 ARQUIVOS E ESTRUTURA

### 🟡 NUNCA: Código Comentado em Commits

```python
# ❌ PROIBIDO - Código comentado
def my_function():
    result = new_implementation()
    # old_result = old_implementation()
    # if some_condition:
    #     do_something()
    # else:
    #     do_other_thing()
    return result

# ✅ CORRETO - Remover código morto (Git guarda histórico)
def my_function():
    result = new_implementation()
    return result
```

**Consequência:** Código confuso, dificulta leitura

### 🟡 NUNCA: Arquivos > 500 Linhas

```python
# ❌ PROIBIDO - app.py com 2000 linhas
# Tudo em um arquivo gigante

# ✅ CORRETO - Modular
# app.py (100 linhas) - Setup e config
# modules/grv/__init__.py (200 linhas) - Rotas GRV
# services/project_service.py (150 linhas) - Lógica de projetos
# models/project.py (50 linhas) - Model
```

**Consequência:** Difícil manutenção, merge conflicts

### 🟡 NUNCA: `import *`

```python
# ❌ PROIBIDO
from flask import *
from sqlalchemy import *

# ✅ CORRETO - Imports explícitos
from flask import Flask, request, jsonify
from sqlalchemy import Column, Integer, String
```

**Consequência:** Namespace poluído, conflitos, difícil rastrear origem

---

## ⚡ PERFORMANCE

### 🟡 NUNCA: Operações Pesadas Síncronas

```python
# ❌ PROIBIDO - Bloquear requisição HTTP
@app.route('/api/send-emails', methods=['POST'])
def send_bulk_emails():
    users = User.query.all()
    for user in users:  # Pode levar minutos!
        send_email(user.email, "...")
    return jsonify({'success': True})

# ✅ CORRETO - Usar Celery para background job
@app.route('/api/send-emails', methods=['POST'])
def send_bulk_emails():
    send_emails_task.delay()  # Celery task assíncrona
    return jsonify({
        'success': True,
        'message': 'Emails sendo enviados em background'
    })

@celery.task
def send_emails_task():
    users = User.query.all()
    for user in users:
        send_email(user.email, "...")
```

**Consequência:** Timeout, UX ruim, servidor bloqueado

### 🟡 NUNCA: Ler Arquivo Grande de Uma Vez

```python
# ❌ PROIBIDO - Carregar tudo na memória
with open('huge_file.csv', 'r') as f:
    content = f.read()  # 2GB na RAM!
    process(content)

# ✅ CORRETO - Processar linha por linha
with open('huge_file.csv', 'r') as f:
    for line in f:  # Streaming
        process(line)
```

**Consequência:** Out of memory, servidor travado

---

## 🧪 TESTES

### 🟡 NUNCA: Testes Dependentes

```python
# ❌ PROIBIDO - Teste depende de outro
def test_create_user():
    user = create_user("test@example.com")
    assert user.id == 1

def test_update_user():
    user = User.query.get(1)  # Depende do teste anterior!
    update_user(user, {"name": "New Name"})

# ✅ CORRETO - Testes independentes
def test_create_user():
    user = create_user("test@example.com")
    assert user.id is not None

def test_update_user():
    user = create_user("test@example.com")  # Cria seu próprio dado
    update_user(user, {"name": "New Name"})
    assert user.name == "New Name"
```

**Consequência:** Testes quebradiços, ordem importa

### 🟡 NUNCA: Testar em Banco de Produção

```python
# ❌ PROIBIDO
def test_delete_user():
    User.query.filter_by(email="real@user.com").delete()  # 💀

# ✅ CORRETO - Usar banco de teste
@pytest.fixture
def db_session():
    # Setup banco de teste
    connection = test_engine.connect()
    transaction = connection.begin()
    yield session
    transaction.rollback()
```

**Consequência:** Perda de dados de produção!

---

## 📝 DOCUMENTAÇÃO

### 🟢 NUNCA: Função Pública sem Docstring

```python
# ❌ PROIBIDO - Sem documentação
def calculate_indicator_average(company_id, indicator_id, start_date, end_date):
    # 50 linhas de código complexo
    pass

# ✅ CORRETO - Com docstring
def calculate_indicator_average(company_id, indicator_id, start_date, end_date):
    """
    Calcula a média de um indicador em um período.
    
    Args:
        company_id: ID da empresa
        indicator_id: ID do indicador
        start_date: Data inicial do período
        end_date: Data final do período
    
    Returns:
        float: Média calculada
    
    Raises:
        ValueError: Se indicador não existir
    """
    pass
```

**Consequência:** Código difícil de entender e manter

---

## ✅ Como Evitar Violações

### Pre-commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120']
```

### Code Review Checklist

- [ ] Sem credenciais hardcoded
- [ ] Sem SQL injection vulnerável
- [ ] Sem bare except
- [ ] Rotas protegidas com @login_required
- [ ] Listas paginadas
- [ ] Eager loading quando necessário
- [ ] Código morto removido
- [ ] Docstrings em funções públicas

---

## 🚨 Reportar Nova Proibição

Se identificar novo anti-pattern crítico:

1. Abrir issue com label "governance"
2. Propor adição neste documento
3. Aguardar aprovação do time
4. Adicionar ao checklist de code review

---

**Este documento é vivo:** Atualizar sempre que identificar novos anti-patterns.

**Próxima revisão:** Trimestral



