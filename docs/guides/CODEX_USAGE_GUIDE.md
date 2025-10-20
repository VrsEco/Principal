# 🤖 Guia Prático: Como Usar OpenAI Codex

**Data:** 18/10/2025  
**Versão:** 1.0  
**Objetivo:** Tutorial completo para usar Codex seguindo governança do projeto

---

## 🎯 O Que É o Codex?

OpenAI Codex é um modelo de IA especializado em gerar código. Você pode usá-lo de 3 formas:

1. **Via API** (Programático) - Para scripts e automação
2. **Via Playground** (Web) - Interface visual para testes
3. **Via IDE Plugin** - Integrado no editor

---

## 🔑 1. Pré-Requisitos

### Obter API Key da OpenAI

```bash
1. Acesse: https://platform.openai.com/
2. Login/Cadastro
3. Navegue: API Keys → Create new secret key
4. Copie a key (ex: sk-abc123...)
5. IMPORTANTE: Guardar em lugar seguro!
```

### Instalar Biblioteca Python (Para API)

```bash
pip install openai
```

---

## 🌐 2. Método 1: Via Playground (Mais Simples)

### Passo 1: Acessar Playground

```
URL: https://platform.openai.com/playground
```

### Passo 2: Configurar

**1. Selecionar Modelo:**
```
Mode: Chat
Model: gpt-3.5-turbo (mais rápido/barato)
   ou: gpt-4 (melhor qualidade)
```

**2. Configurar System Message:**

Clique em "System" e cole o conteúdo completo do arquivo:
```
.ai/codex-instructions.md
```

Ou use este resumo:

```
You are a Python/Flask expert for GestaoVersus project.

STRICT RULES:
- Stack: Python 3.9+, Flask 2.3.3, SQLAlchemy 2.0.21
- Database: PostgreSQL + SQLite (code MUST work on both)
- NEVER suggest: Django, FastAPI, MongoDB, React, TypeScript
- ALL routes: @login_required + @auto_log_crud for CRUD
- Response: {"success": bool, "data": ...}
- Naming: snake_case (functions), PascalCase (classes)
- NO: eval(), exec(), print(), bare except, hardcoded credentials

Governance: docs/governance/
```

**3. Ajustar Parâmetros:**
```
Temperature: 0.2 (mais consistente, menos criativo)
Maximum length: 2000 tokens
Top P: 1
Frequency penalty: 0
Presence penalty: 0
```

### Passo 3: Fazer Perguntas

**Campo "User":**

```
Generate a complete Flask route to create projects with:
- @login_required and @auto_log_crud decorators
- Input validation
- Response format: {"success": bool, "data": ...}
- Status code 201
- Docstring with type hints
- Compatible with PostgreSQL and SQLite
```

### Passo 4: Ver Resultado

Clique "Submit" e veja o código gerado seguindo todos os padrões!

### Exemplo Visual do Playground

```
┌─────────────────────────────────────────────────────────┐
│ OpenAI Playground                                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Model: gpt-4                      Temperature: 0.2     │
│                                                         │
│ System:                                                 │
│ ┌─────────────────────────────────────────────────┐   │
│ │ You are a Python/Flask expert for               │   │
│ │ GestaoVersus project...                         │   │
│ │ [Cole instruções completas aqui]                │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ User:                                                   │
│ ┌─────────────────────────────────────────────────┐   │
│ │ Generate Flask route to create projects         │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ [Submit]                                                │
│                                                         │
│ Assistant:                                              │
│ ┌─────────────────────────────────────────────────┐   │
│ │ from flask import Blueprint, request...         │   │
│ │ [Código gerado aqui]                            │   │
│ └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 💻 3. Método 2: Via API Python (Programático)

### Configuração Inicial

**Criar arquivo `.env` (raiz do projeto):**

```bash
# .env
OPENAI_API_KEY=sk-abc123xyz...
```

**Adicionar ao `.gitignore`:**

```bash
echo ".env" >> .gitignore
```

### Script Básico

**Criar arquivo `scripts/codex_helper.py`:**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper para usar Codex seguindo governança do projeto.
"""

import os
import openai
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Caminho do arquivo de instruções
INSTRUCTIONS_FILE = Path(__file__).parent.parent / '.ai' / 'codex-instructions.md'


def load_system_message():
    """Carrega instruções de governança."""
    with open(INSTRUCTIONS_FILE, 'r', encoding='utf-8') as f:
        return f.read()


def generate_code(prompt, model="gpt-3.5-turbo", temperature=0.2):
    """
    Gera código usando Codex seguindo governança do projeto.
    
    Args:
        prompt (str): O que você quer que o Codex gere
        model (str): Modelo a usar (gpt-3.5-turbo ou gpt-4)
        temperature (float): Criatividade (0.0-1.0, recomendado: 0.2)
    
    Returns:
        str: Código gerado
    
    Examples:
        >>> code = generate_code("Create Flask route for projects")
        >>> print(code)
    """
    system_message = load_system_message()
    
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=2000
        )
        
        code = response.choices[0].message.content
        return code
    
    except openai.error.AuthenticationError:
        return "ERRO: API key inválida. Verifique OPENAI_API_KEY no .env"
    
    except openai.error.RateLimitError:
        return "ERRO: Limite de requisições atingido. Aguarde um momento."
    
    except Exception as e:
        return f"ERRO: {str(e)}"


def generate_route(entity_name, operation="create"):
    """
    Gera rota Flask para uma entidade.
    
    Args:
        entity_name (str): Nome da entidade (ex: "Project", "User")
        operation (str): Operação (create, list, get, update, delete)
    
    Returns:
        str: Código da rota
    
    Examples:
        >>> code = generate_route("Project", "create")
        >>> print(code)
    """
    prompts = {
        "create": f"Generate complete Flask POST route to create {entity_name}",
        "list": f"Generate complete Flask GET route to list {entity_name}s with pagination",
        "get": f"Generate complete Flask GET route to get one {entity_name}",
        "update": f"Generate complete Flask PUT route to update {entity_name}",
        "delete": f"Generate complete Flask DELETE route to delete {entity_name} (soft delete)"
    }
    
    prompt = prompts.get(operation, f"Generate Flask route for {entity_name}")
    prompt += "\n\nInclude ALL project standards: @login_required, @auto_log_crud, validation, docstring"
    
    return generate_code(prompt)


def generate_model(entity_name, fields):
    """
    Gera model SQLAlchemy para uma entidade.
    
    Args:
        entity_name (str): Nome da entidade
        fields (list): Lista de campos no formato "nome:tipo"
    
    Returns:
        str: Código do model
    
    Examples:
        >>> fields = ["name:String(200)", "description:Text", "status:String(20)"]
        >>> code = generate_model("Project", fields)
        >>> print(code)
    """
    fields_str = ", ".join(fields)
    
    prompt = f"""
Generate SQLAlchemy model for {entity_name} with these fields: {fields_str}

Requirements:
- Include audit fields (created_at, updated_at, is_deleted)
- Include docstring
- Include to_dict() method
- Include __repr__() method
- Use types compatible with PostgreSQL AND SQLite
"""
    
    return generate_code(prompt)


def interactive_mode():
    """Modo interativo para gerar código."""
    print("=" * 60)
    print("🤖 Codex Helper - GestaoVersus")
    print("=" * 60)
    print("\nModo Interativo")
    print("Digite 'exit' para sair\n")
    
    while True:
        prompt = input("O que você quer gerar? ")
        
        if prompt.lower() in ['exit', 'quit', 'sair']:
            print("👋 Até logo!")
            break
        
        if not prompt.strip():
            continue
        
        print("\n⏳ Gerando código...\n")
        
        code = generate_code(prompt)
        
        print("─" * 60)
        print(code)
        print("─" * 60)
        print()


if __name__ == "__main__":
    # Exemplos de uso
    
    # 1. Gerar rota de criação
    print("Exemplo 1: Gerando rota de criação de projetos...\n")
    code = generate_route("Project", "create")
    print(code)
    print("\n" + "=" * 60 + "\n")
    
    # 2. Gerar model
    print("Exemplo 2: Gerando model de projetos...\n")
    fields = ["name:String(200)", "description:Text", "status:String(20)"]
    code = generate_model("Project", fields)
    print(code)
    print("\n" + "=" * 60 + "\n")
    
    # 3. Modo interativo
    # Descomente para usar:
    # interactive_mode()
```

### Como Usar o Script

**1. Configurar:**

```bash
# Instalar dependências
pip install openai python-dotenv

# Criar .env com sua API key
echo "OPENAI_API_KEY=sk-abc123..." > .env
```

**2. Executar:**

```bash
# Exemplos prontos
python scripts/codex_helper.py

# Modo interativo
python -c "from scripts.codex_helper import interactive_mode; interactive_mode()"
```

**3. Usar em seus scripts:**

```python
from scripts.codex_helper import generate_route, generate_model

# Gerar rota CRUD completa
create_route = generate_route("Indicator", "create")
print(create_route)

# Gerar model
fields = ["code:String(50)", "name:String(200)", "target:Numeric(10,2)"]
model_code = generate_model("Indicator", fields)
print(model_code)
```

---

## 🔧 4. Exemplos Práticos

### Exemplo 1: Gerar Rota Completa

**Prompt:**
```
Generate complete Flask route to create indicators with:
- Route: POST /api/companies/<company_id>/indicators
- @login_required and @auto_log_crud decorators
- Validate: code, name, unit are required
- Response format: {"success": bool, "data": {...}}
- Status 201 on success
- Docstring with type hints
```

**Resultado:**
```python
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from middleware.auto_log_decorator import auto_log_crud
from models import db, Indicator

@api.route('/api/companies/<int:company_id>/indicators', methods=['POST'])
@login_required
@auto_log_crud('indicator')
def create_indicator(company_id: int):
    """
    Cria novo indicador para empresa.
    
    Args:
        company_id: ID da empresa
        
    Returns:
        JSON com indicador criado
    """
    data = request.get_json()
    
    # Validação
    required_fields = ['code', 'name', 'unit']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'error': f'{field} é obrigatório'
            }), 400
    
    # Criar indicador
    indicator = Indicator(
        code=data['code'],
        name=data['name'],
        unit=data['unit'],
        description=data.get('description'),
        company_id=company_id,
        created_by=current_user.id
    )
    
    db.session.add(indicator)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'data': indicator.to_dict()
    }), 201
```

### Exemplo 2: Gerar Model

**Prompt:**
```
Generate SQLAlchemy model for Indicator with:
- Fields: code (String 50), name (String 200), unit (String 20), 
  description (Text), target (Numeric 10,2), company_id (FK)
- Include audit fields
- Include to_dict() and __repr__()
- Compatible PostgreSQL + SQLite
```

**Resultado:**
```python
from datetime import datetime
from models import db

class Indicator(db.Model):
    """Modelo de Indicador."""
    
    __tablename__ = 'indicators'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Campos de negócio
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    target = db.Column(db.Numeric(10, 2))
    
    # Foreign Keys
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Auditoria
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relacionamentos
    company = db.relationship('Company', backref='indicators')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        """Serializa para dict."""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'unit': self.unit,
            'description': self.description,
            'target': float(self.target) if self.target else None,
            'company_id': self.company_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Indicator {self.code}: {self.name}>'
```

### Exemplo 3: Gerar CRUD Completo

**Usar o script:**
```python
from scripts.codex_helper import generate_route

operations = ['create', 'list', 'get', 'update', 'delete']

for op in operations:
    code = generate_route("Indicator", op)
    
    # Salvar em arquivo
    with open(f'generated/indicator_{op}.py', 'w') as f:
        f.write(code)
    
    print(f"✅ {op.upper()} gerado!")
```

---

## 💡 5. Dicas e Boas Práticas

### Prompts Efetivos

**✅ BOM (Específico):**
```
Generate Flask POST route to create users with:
- Validation: email format, password min 8 chars
- Hash password with bcrypt
- @login_required (admin only)
- @auto_log_crud('user')
- Return 201 on success
```

**❌ RUIM (Vago):**
```
Create user route
```

### Temperatura (Criatividade)

```python
temperature=0.0   # Determinístico (sempre mesmo resultado)
temperature=0.2   # ✅ RECOMENDADO (consistente mas não robótico)
temperature=0.5   # Mais criativo
temperature=1.0   # Muito criativo (pode fugir dos padrões)
```

### Validar Código Gerado

**Sempre:**
1. ✅ Revisar código gerado
2. ✅ Rodar Black para formatar
3. ✅ Rodar Flake8 para lint
4. ✅ Rodar testes de governança
5. ✅ Testar manualmente

```bash
# Após gerar código
black generated/
flake8 generated/
pytest tests/governance/
```

---

## 🚨 6. Troubleshooting

### Erro: Authentication Error

```
ERRO: API key inválida
```

**Solução:**
```bash
# Verificar .env
cat .env

# Deve conter:
OPENAI_API_KEY=sk-abc123...

# Se não tiver, criar:
echo "OPENAI_API_KEY=sua-key-aqui" > .env
```

### Erro: Rate Limit

```
ERRO: Limite de requisições atingido
```

**Solução:**
- Aguardar alguns minutos
- Ou usar plano pago da OpenAI (mais requisições)

### Código Não Segue Padrões

**Problema:** Codex gera código sem @login_required

**Solução:**
1. Verificar se system message está configurado
2. Ser mais específico no prompt:
```
Generate route WITH @login_required decorator (mandatory)
```

### Código Usa Tecnologia Proibida

**Problema:** Codex sugere Django

**Solução:**
1. Reforçar no prompt:
```
IMPORTANT: Use ONLY Flask, NEVER Django
```
2. Verificar system message está carregado

---

## 📊 7. Custos (OpenAI API)

### Preços Aproximados (2025)

| Modelo | Input (1K tokens) | Output (1K tokens) | Uso Recomendado |
|--------|-------------------|-------------------|-----------------|
| gpt-3.5-turbo | $0.0015 | $0.002 | Código simples, testes |
| gpt-4 | $0.03 | $0.06 | Código complexo, produção |

### Estimativa de Custos

```
Geração típica de rota:
- System message: ~1000 tokens
- Prompt: ~100 tokens
- Response: ~500 tokens

gpt-3.5-turbo:
- Input: (1100 / 1000) * $0.0015 = $0.00165
- Output: (500 / 1000) * $0.002 = $0.001
- Total por rota: ~$0.003 (menos de 1 centavo)

gpt-4:
- Total por rota: ~$0.063 (6 centavos)

100 gerações:
- gpt-3.5-turbo: ~$0.30
- gpt-4: ~$6.30
```

### Dica de Economia

```python
# Use gpt-3.5-turbo para desenvolver
code = generate_code(prompt, model="gpt-3.5-turbo")

# Se não ficar bom, use gpt-4
if not is_good_enough(code):
    code = generate_code(prompt, model="gpt-4")
```

---

## 🎓 8. Casos de Uso Avançados

### Gerar Migration

```python
from scripts.codex_helper import generate_code

prompt = """
Generate Alembic migration to:
- Add table 'indicators' with fields: code, name, unit, description, target
- Add foreign key to companies
- Add audit fields
- Create indexes
- Compatible PostgreSQL + SQLite
"""

migration = generate_code(prompt)
print(migration)
```

### Gerar Testes

```python
prompt = """
Generate pytest tests for create_project route:
- Test successful creation
- Test validation errors
- Test authentication required
- Test duplicate name
- Use pytest fixtures
"""

tests = generate_code(prompt)
# Salvar em tests/test_project.py
```

### Gerar Documentação

```python
prompt = """
Generate API documentation for project endpoints:
- List projects (GET /api/projects)
- Create project (POST /api/projects)
- Update project (PUT /api/projects/<id>)
- Delete project (DELETE /api/projects/<id>)

Format: Markdown with examples
"""

docs = generate_code(prompt)
# Salvar em docs/api/projects.md
```

---

## ✅ Checklist de Uso

Antes de usar código gerado pelo Codex:

- [ ] Revisar código linha por linha
- [ ] Verificar se segue nomenclatura (snake_case/PascalCase)
- [ ] Verificar @login_required em rotas
- [ ] Verificar @auto_log_crud em CRUD
- [ ] Verificar validação de entrada
- [ ] Verificar response format padronizado
- [ ] Verificar compatibilidade PostgreSQL + SQLite
- [ ] Rodar Black para formatar
- [ ] Rodar Flake8 para lint
- [ ] Rodar testes de governança
- [ ] Testar manualmente

---

## 📚 Recursos

- **OpenAI Playground:** https://platform.openai.com/playground
- **Docs da API:** https://platform.openai.com/docs
- **Governança do Projeto:** `docs/governance/`
- **Instruções Codex:** `.ai/codex-instructions.md`

---

**Dúvidas?** Consulte a documentação ou abra issue com label "codex"

**Versão:** 1.0  
**Última atualização:** 18/10/2025



