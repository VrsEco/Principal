# 🛠️ Scripts do Projeto

Esta pasta contém scripts utilitários para o projeto GestaoVersus.

---

## 📁 Scripts Disponíveis

### `codex_helper.py` - Gerador de Código com IA

**O que faz:**
Usa OpenAI Codex para gerar código seguindo a governança do projeto automaticamente.

**Como usar:**

#### 1. Configuração Inicial (Uma Vez)

```bash
# 1. Instalar dependências
pip install openai python-dotenv

# 2. Obter API Key da OpenAI
# Acesse: https://platform.openai.com/api-keys
# Crie uma nova key (ex: sk-abc123...)

# 3. Criar arquivo .env na raiz do projeto
echo "OPENAI_API_KEY=sk-abc123..." > .env

# 4. Adicionar .env ao .gitignore (se não estiver)
echo ".env" >> .gitignore
```

#### 2. Executar Script

**Modo Menu (Interativo):**
```bash
python scripts/codex_helper.py
```

Você verá um menu:
```
🤖 Codex Helper - GestaoVersus
======================================================================

Escolha uma opção:
======================================================================

1. Gerar rota Flask
2. Gerar model SQLAlchemy
3. Gerar CRUD completo
4. Modo interativo (livre)
5. Sair

Opção (1-5):
```

**Exemplos de Uso:**

**Opção 1: Gerar Rota**
```
Opção: 1
Nome da entidade: Indicator
Operação: 1 (create)

[Código gerado com @login_required, @auto_log_crud, validation, etc.]
```

**Opção 2: Gerar Model**
```
Opção: 2
Nome da entidade: Indicator
Campo: code:String(50)
Campo: name:String(200)
Campo: target:Numeric(10,2)
Campo: fim

[Modelo SQLAlchemy completo gerado]
```

**Opção 3: CRUD Completo**
```
Opção: 3
Nome da entidade: Indicator

[Gera CREATE, LIST, GET, UPDATE, DELETE de uma vez]
```

**Opção 4: Modo Livre**
```
Opção: 4

>>> route Indicator create
[Gera rota de criação]

>>> model Project
[Gera model básico]

>>> Generate Flask route to export projects to CSV
[Gera código customizado]

>>> exit
```

#### 3. Usar em Seus Scripts Python

```python
from scripts.codex_helper import generate_route, generate_model, generate_code

# Gerar rota
create_route = generate_route("Indicator", "create")
print(create_route)

# Gerar model
fields = ["code:String(50)", "name:String(200)", "target:Numeric(10,2)"]
model_code = generate_model("Indicator", fields)
print(model_code)

# Gerar código customizado
code = generate_code("Generate function to calculate indicator average")
print(code)
```

#### 4. Exemplo Completo: Criar Novo Módulo

```python
from scripts.codex_helper import generate_route, generate_model

# 1. Gerar model
fields = [
    "code:String(50)",
    "name:String(200)",
    "description:Text",
    "target:Numeric(10,2)",
    "company_id:Integer"
]
model = generate_model("Indicator", fields)

# Salvar
with open('models/indicator.py', 'w') as f:
    f.write(model)

# 2. Gerar rotas CRUD
operations = ['create', 'list', 'get', 'update', 'delete']
routes = []

for op in operations:
    code = generate_route("Indicator", op)
    routes.append(f"\n# {op.upper()}\n{code}")

# Salvar todas rotas
with open('modules/indicators/__init__.py', 'w') as f:
    f.write("from flask import Blueprint\n\n")
    f.write("indicators_bp = Blueprint('indicators', __name__)\n\n")
    f.write("\n".join(routes))

print("✅ Módulo de indicadores criado!")
```

---

## 💰 Custos (Estimativa)

**OpenAI API:**
- gpt-3.5-turbo: ~$0.003 por geração (~R$ 0,015)
- gpt-4: ~$0.06 por geração (~R$ 0,30)

**Recomendação:** Use gpt-3.5-turbo para testes, gpt-4 para produção.

---

## 🧪 Validar Código Gerado

**SEMPRE** validar código gerado:

```bash
# 1. Formatar
black arquivo_gerado.py

# 2. Lint
flake8 arquivo_gerado.py

# 3. Testes de governança
pytest tests/governance/

# 4. Testar manualmente
python -c "from arquivo_gerado import funcao; funcao()"
```

---

## 📚 Documentação Completa

- **Guia Detalhado:** `docs/guides/CODEX_USAGE_GUIDE.md`
- **Instruções Codex:** `.ai/codex-instructions.md`
- **Governança:** `docs/governance/`

---

## ❓ Troubleshooting

### Erro: OPENAI_API_KEY não configurada

```bash
# Criar .env
echo "OPENAI_API_KEY=sk-sua-key" > .env
```

### Erro: openai não instalado

```bash
pip install openai python-dotenv
```

### Código gerado não segue padrões

- Verifique se `.ai/codex-instructions.md` existe
- Seja mais específico no prompt
- Use gpt-4 ao invés de gpt-3.5-turbo

---

## 🤝 Contribuindo

Adicione novos scripts nesta pasta seguindo o padrão:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nome do Script - Descrição

Uso:
    python scripts/nome_script.py
"""

# Seu código aqui
```

---

**Última atualização:** 18/10/2025


