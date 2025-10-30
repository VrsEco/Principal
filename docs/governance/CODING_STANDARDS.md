# 💻 Padrões de Código

**Última Atualização:** 18/10/2025  
**Versão:** 1.0  
**Status:** ✅ Obrigatório

---

## 🎯 Princípios

1. **Legibilidade > Concisão** - Código é lido 10x mais que escrito
2. **Consistência** - Seguir os padrões existentes
3. **Simplicidade** - KISS (Keep It Simple, Stupid)
4. **Testabilidade** - Código deve ser fácil de testar
5. **Documentação** - Código complexo deve ter comentários

---

## 🐍 Python Style Guide

### PEP 8 com Exceções

Seguimos **PEP 8** com algumas adaptações:

```python
# ✅ BOM
def calculate_indicator_average(company_id: int, indicator_id: int) -> float:
    """
    Calcula média de um indicador.
    
    Args:
        company_id: ID da empresa
        indicator_id: ID do indicador
        
    Returns:
        float: Média calculada
        
    Raises:
        ValueError: Se indicador não existir
    """
    # Implementação
    pass

# ❌ RUIM
def calc(c,i):  # Nomes não descritivos
    return 0    # Sem docstring
```

### Nomenclatura

#### Variáveis e Funções

```python
# ✅ snake_case para variáveis e funções
user_name = "João"
total_projects = 10

def get_user_projects(user_id):
    pass

# ❌ Evitar
userName = "João"          # camelCase
TotalProjects = 10         # PascalCase
def GetUserProjects():     # PascalCase
    pass
```

#### Classes

```python
# ✅ PascalCase para classes
class ProjectService:
    pass

class IndicatorGoal:
    pass

# ❌ Evitar
class project_service:     # snake_case
    pass
```

#### Constantes

```python
# ✅ UPPER_SNAKE_CASE para constantes
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
DEFAULT_PAGINATION = 20
API_VERSION = "v1"

# ❌ Evitar
max_upload_size = 5242880
```

#### Nomes Privados

```python
class UserService:
    # ✅ Prefixo _ para métodos/atributos privados
    def _validate_email(self, email):
        pass
    
    # ✅ Público
    def create_user(self, data):
        if not self._validate_email(data['email']):
            raise ValueError("Email inválido")
```

---

## 📏 Formatação

### Indentação

```python
# ✅ 4 espaços (NUNCA tabs)
def my_function():
    if condition:
        do_something()
        
# ❌ Evitar
def my_function():
  if condition:  # 2 espaços
      do_something()
```

### Tamanho de Linha

```python
# ✅ Máximo 120 caracteres (não 79)
# Motivo: Monitores modernos comportam mais

# ✅ Quebra de linha em argumentos
result = some_function(
    argument1="value1",
    argument2="value2",
    argument3="value3"
)

# ❌ Evitar
result = some_function(argument1="value1", argument2="value2", argument3="value3", argument4="value4")
```

### Espaçamento

```python
# ✅ BOM
x = 1
y = 2
total = x + y

def function_name(param1, param2):
    return param1 + param2

# ❌ RUIM
x=1
y=2
total=x+y

def function_name(param1,param2):
    return param1+param2
```

### Imports

```python
# ✅ BOM - Ordem correta
# 1. Standard library
import os
import sys
from datetime import datetime

# 2. Third-party
from flask import Flask, request
from sqlalchemy import Column, Integer

# 3. Local/project
from models import db
from services.auth_service import auth_service

# ❌ RUIM - Tudo misturado
from flask import Flask
from models import db
import os
from services.auth_service import auth_service
```

```python
# ✅ Imports absolutos
from modules.grv.services import ProjectService

# ❌ Imports relativos (evitar)
from ..services import ProjectService
```

---

## 🔤 Strings

### Aspas

```python
# ✅ Preferir aspas simples
name = 'João'
message = 'Olá mundo'

# ✅ Aspas duplas quando há aspas simples dentro
message = "Não posso ir"

# ✅ Triple quotes para strings multilinhas
description = """
Este é um texto longo
que ocupa várias linhas
"""

# ❌ Inconsistente
name = "João"
message = 'Olá'
```

### F-strings (Preferir)

```python
# ✅ F-strings (Python 3.6+)
name = "João"
age = 30
message = f"Olá, {name}! Você tem {age} anos."

# ⚠️ Aceito mas não preferido
message = "Olá, {}! Você tem {} anos.".format(name, age)

# ❌ Evitar
message = "Olá, " + name + "! Você tem " + str(age) + " anos."
```

---

## 🏗️ Estrutura de Código

### Funções

```python
# ✅ Funções pequenas e focadas
def get_active_users():
    """Retorna usuários ativos."""
    return User.query.filter_by(active=True).all()

def send_welcome_email(user):
    """Envia email de boas-vindas."""
    email_service.send(
        to=user.email,
        template='welcome',
        context={'user': user}
    )

# ❌ Funções muito grandes
def process_user(user_data):
    # 200 linhas fazendo muitas coisas diferentes
    pass
```

### Limite de Complexidade

```python
# ✅ BOM - Máximo 3 níveis de indentação
def process_data(data):
    if data:
        for item in data:
            if item.is_valid():
                save(item)

# ❌ RUIM - Muita complexidade
def process_data(data):
    if data:
        for item in data:
            if item.is_valid():
                if item.type == 'A':
                    if item.value > 0:
                        # Muito aninhado!
                        pass
```

### Early Returns

```python
# ✅ BOM - Early return
def validate_user(user):
    if not user:
        return False
    
    if not user.email:
        return False
    
    if not user.is_active:
        return False
    
    return True

# ❌ RUIM - Aninhamento desnecessário
def validate_user(user):
    if user:
        if user.email:
            if user.is_active:
                return True
    return False
```

---

## 🎯 Type Hints (Recomendado)

```python
# ✅ Com type hints
def get_user_by_id(user_id: int) -> Optional[User]:
    """Busca usuário por ID."""
    return User.query.get(user_id)

def calculate_total(items: List[Dict[str, Any]]) -> float:
    """Calcula total de itens."""
    return sum(item['value'] for item in items)

# ⚠️ Aceito mas não preferido
def get_user_by_id(user_id):
    return User.query.get(user_id)
```

---

## 🗂️ Organização de Arquivos

### Estrutura de um Módulo

```python
# modules/grv/__init__.py

"""
Módulo GRV - Gestão de Resultados Versus

Este módulo contém toda a lógica de gestão de resultados,
incluindo projetos, indicadores, OKRs e processos.
"""

# Imports
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

# Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Blueprint definition
grv_bp = Blueprint('grv', __name__, url_prefix='/grv')

# Routes (organizadas por entidade)
# --- Projects ---
@grv_bp.route('/projects')
def list_projects():
    pass

@grv_bp.route('/projects/<int:id>')
def get_project(id):
    pass

# --- Indicators ---
@grv_bp.route('/indicators')
def list_indicators():
    pass
```

### Ordem no Arquivo

1. Docstring do módulo
2. Imports (standard → third-party → local)
3. Constantes
4. Configurações
5. Funções/Classes
6. Rotas (se blueprint)
7. Main block (se executável)

---

## 🧪 Comentários e Documentação

### Docstrings

```python
# ✅ BOM - Docstring completa
def create_project(company_id: int, data: dict) -> Project:
    """
    Cria um novo projeto para uma empresa.
    
    Args:
        company_id (int): ID da empresa
        data (dict): Dados do projeto (name, description, start_date, etc.)
    
    Returns:
        Project: Projeto criado
    
    Raises:
        ValueError: Se dados inválidos
        PermissionError: Se usuário sem permissão
    
    Examples:
        >>> create_project(1, {'name': 'Projeto X'})
        <Project id=1>
    """
    # Implementação
    pass

# ❌ RUIM - Sem docstring
def create_project(company_id, data):
    pass
```

### Comentários Inline

```python
# ✅ BOM - Comentário explicando "por quê"
# Arredondar para 2 casas devido a limitação do relatório PDF
value = round(total, 2)

# Usar transação para garantir consistência
with db.session.begin_nested():
    save_project()
    send_notification()

# ❌ RUIM - Comentário explicando "o quê" (óbvio)
# Somar x e y
total = x + y

# Retornar resultado
return total
```

### TODO Comments

```python
# ✅ BOM - TODO com contexto
# TODO(joao, 2025-10-20): Adicionar validação de CPF
# Ref: Issue #123

# ⚠️ Aceito
# TODO: Melhorar performance

# ❌ RUIM
# TODO: Arrumar isso
```

---

## 🔍 Error Handling

### Exceções

```python
# ✅ BOM - Específico
try:
    user = User.query.get(user_id)
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    raise
except ValueError as e:
    logger.warning(f"Invalid user_id: {user_id}")
    return None

# ❌ RUIM - Genérico demais
try:
    user = User.query.get(user_id)
except:  # Pega tudo!
    pass  # E ignora!
```

### Custom Exceptions

```python
# ✅ Criar exceções customizadas
class BusinessException(Exception):
    """Exceção de regra de negócio."""
    pass

class PermissionDeniedException(BusinessException):
    """Usuário sem permissão."""
    pass

# Uso
if not user.can_edit(project):
    raise PermissionDeniedException("Sem permissão para editar")
```

---

## 🎨 Flask/Jinja2

### Rotas

```python
# ✅ BOM
@app.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project.html', project=project)

# ❌ RUIM
@app.route('/projects/<project_id>')  # Sem type hint
def view_project(project_id):
    project = Project.query.get(int(project_id))  # Conversão manual
    if not project:
        return "Not found", 404
    return render_template('project.html', project=project)
```

### Templates

```jinja2
{# ✅ BOM - Comentários descritivos #}
{# Cabeçalho do projeto com botões de ação #}
<div class="project-header">
    <h1>{{ project.name }}</h1>
    {% if current_user.can_edit(project) %}
        <button>Editar</button>
    {% endif %}
</div>

{# ✅ Usar includes para componentes #}
{% include 'components/project_card.html' %}

{# ❌ RUIM - Template muito grande sem organização #}
<div>
    {# 500 linhas de HTML #}
</div>
```

---

## 🗃️ SQLAlchemy

> Para diretrizes completas de metadata, importação de models e rotina de serviços, consulte também **[ORM_STANDARDS.md](ORM_STANDARDS.md)**.

### Models

```python
# ✅ BOM
class Project(db.Model):
    """Modelo de Projeto."""
    
    __tablename__ = 'projects'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos básicos
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    
    # Relacionamentos
    company = db.relationship('Company', backref='projects')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        """Serializa para dict."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

# ❌ RUIM - Sem organização
class Project(db.Model):
    company = db.relationship('Company', backref='projects')
    name = db.Column(db.String(200), nullable=False)
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
```

### Queries

```python
# ✅ BOM - Legível
active_projects = (
    Project.query
    .filter_by(active=True)
    .filter(Project.start_date >= datetime.now())
    .order_by(Project.name)
    .all()
)

# ✅ Eager loading quando necessário
projects = (
    Project.query
    .options(db.joinedload(Project.company))
    .all()
)

# ❌ RUIM - Ilegível
projects = Project.query.filter_by(active=True).filter(Project.start_date >= datetime.now()).order_by(Project.name).all()
```

---

## ⏰ Tarefas Agendadas (APScheduler)

### Padrões para Jobs

```python
# ✅ BOM
def process_daily_backups():
    """
    Processa backups diários.
    
    Executado automaticamente às 03:00 todos os dias.
    """
    logger.info("Iniciando backup diário...")
    try:
        # Lógica do backup
        pass
    except Exception as e:
        logger.error(f"Erro no backup: {e}")
        # Notificar admin

# ❌ RUIM
def backup():  # Nome genérico
    print("backup")  # Usar logger, não print
    # Sem tratamento de erro
```

### Adicionar Novo Job

**Localização:** `services/scheduler_service.py` → função `setup_routine_jobs()`

```python
def setup_routine_jobs():
    # Jobs existentes...
    
    # Adicionar novo job
    scheduler_service.add_job(
        func=nome_da_funcao,
        trigger='cron',
        job_id='identificador_unico',
        hour=3,  # Horário
        minute=0,
        name='Nome Descritivo para Logs'
    )
```

### Regras de Jobs

- ✅ **Sempre** usar `try/except` em funções de jobs
- ✅ **Sempre** usar `logger` (nunca `print`)
- ✅ **Sempre** usar IDs únicos e descritivos
- ✅ **Sempre** adicionar docstring com horário de execução
- ❌ **Nunca** fazer operações bloqueantes longas (>5min)
- ❌ **Nunca** usar `use_reloader=True` com scheduler

### Tipos de Triggers

```python
# Diário (horário específico)
trigger='cron', hour=0, minute=1

# A cada X minutos
trigger='interval', minutes=30

# Semanal (segunda-feira às 09:00)
trigger='cron', day_of_week='mon', hour=9, minute=0

# Mensal (dia 1 às 00:00)
trigger='cron', day=1, hour=0, minute=0

# Data específica
trigger='date', run_date='2025-12-31 23:59:00'
```

---

## 🐳 Docker

### Padrões de Dockerfile

```dockerfile
# ✅ BOM - Multi-stage, otimizado
FROM python:3.9-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ❌ RUIM - Tudo em uma camada
FROM python:3.9
RUN apt-get update && apt-get install everything
COPY . .
```

### Docker Compose

```yaml
# ✅ BOM
services:
  app:
    build: .
    environment:
      DATABASE_URL: ${DATABASE_URL}
    volumes:
      - .:/app  # Hot-reload
    depends_on:
      db:
        condition: service_healthy

# ❌ RUIM
services:
  app:
    image: myapp
    environment:
      DB_PASS: senha123  # Hardcoded!
```

### Regras Docker

- ✅ **Sempre** usar `.dockerignore`
- ✅ **Sempre** usar health checks
- ✅ **Sempre** usar volumes nomeados para dados
- ✅ **Sempre** usar variáveis de ambiente
- ❌ **Nunca** hardcode credenciais
- ❌ **Nunca** usar `latest` em produção
- ❌ **Nunca** rodar como root em produção

---

## 🧰 Ferramentas

### Black (Formatação Automática)

```bash
# Formatar arquivo
black app_pev.py

# Formatar projeto inteiro
black .

# Verificar sem modificar
black --check .
```

### Flake8 (Linting)

```bash
# Verificar código
flake8 app_pev.py

# Configuração em setup.cfg
[flake8]
max-line-length = 120
exclude = .git,__pycache__,migrations
```

### Pytest (Testes)

```bash
# Rodar todos os testes
pytest

# Rodar com cobertura
pytest --cov=.

# Rodar testes específicos
pytest tests/test_auth.py
```

---

## ✅ Checklist de Code Review

### Antes de Commit

- [ ] Código formatado com Black
- [ ] Sem erros de Flake8
- [ ] Testes passando
- [ ] Docstrings em funções públicas
- [ ] Type hints em funções complexas
- [ ] Sem código comentado
- [ ] Sem `print()` para debug (usar `logger`)
- [ ] Sem credenciais hardcoded

### Antes de PR

- [ ] Branch atualizada com main
- [ ] Commits organizados
- [ ] Mensagens de commit descritivas
- [ ] Documentação atualizada
- [ ] CHANGELOG atualizado (se aplicável)

---

## 📚 Recursos

- **PEP 8:** https://pep8.org/
- **Black:** https://black.readthedocs.io/
- **Type Hints:** https://docs.python.org/3/library/typing.html
- **Docstrings:** https://peps.python.org/pep-0257/

---

**Dúvidas?** Consulte o time ou abra uma discussão no repositório.


