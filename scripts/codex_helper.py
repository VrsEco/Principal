#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex Helper - Gerador de Código usando OpenAI Codex

Este script facilita a geração de código seguindo a governança do projeto.

Uso:
    python scripts/codex_helper.py
    
    # Ou modo interativo:
    python -c "from scripts.codex_helper import interactive_mode; interactive_mode()"
"""

import os
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import openai
except ImportError:
    print("ERRO: openai não instalado")
    print("Instale: pip install openai")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("AVISO: python-dotenv não instalado (opcional)")
    print("Instale: pip install python-dotenv")
    load_dotenv = lambda: None

# Carregar variáveis de ambiente
load_dotenv()

# Configurar API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Caminho do arquivo de instruções
INSTRUCTIONS_FILE = project_root / '.ai' / 'codex-instructions.md'


def load_system_message():
    """Carrega instruções de governança do projeto."""
    if not INSTRUCTIONS_FILE.exists():
        print(f"ERRO: Arquivo {INSTRUCTIONS_FILE} não encontrado")
        print("Execute este script da raiz do projeto")
        sys.exit(1)
    
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
    if not openai.api_key:
        return "ERRO: OPENAI_API_KEY não configurada no .env"
    
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


def generate_route(entity_name, operation="create", model="gpt-3.5-turbo"):
    """
    Gera rota Flask para uma entidade.
    
    Args:
        entity_name (str): Nome da entidade (ex: "Project", "User")
        operation (str): Operação (create, list, get, update, delete)
        model (str): Modelo OpenAI a usar
    
    Returns:
        str: Código da rota
    
    Examples:
        >>> code = generate_route("Project", "create")
        >>> print(code)
    """
    prompts = {
        "create": f"""Generate complete Flask POST route to create {entity_name} with:
- Route: POST /api/{{entity_plural}}
- @login_required decorator
- @auto_log_crud('{entity_name.lower()}') decorator
- Input validation (check required fields)
- Response format: {{"success": bool, "data": {{...}}}}
- Status code 201 on success
- Docstring with type hints
- Compatible with PostgreSQL and SQLite""",
        
        "list": f"""Generate complete Flask GET route to list {entity_name}s with:
- Route: GET /api/{{entity_plural}}
- @login_required decorator
- Pagination (page, per_page)
- Response with pagination metadata
- Docstring with type hints""",
        
        "get": f"""Generate complete Flask GET route to get one {entity_name} with:
- Route: GET /api/{{entity_plural}}/<int:id>
- @login_required decorator
- Return 404 if not found
- Response format: {{"success": bool, "data": {{...}}}}
- Docstring with type hints""",
        
        "update": f"""Generate complete Flask PUT route to update {entity_name} with:
- Route: PUT /api/{{entity_plural}}/<int:id>
- @login_required decorator
- @auto_log_crud('{entity_name.lower()}') decorator
- Input validation
- Return 404 if not found
- Response format: {{"success": bool, "data": {{...}}}}
- Docstring with type hints""",
        
        "delete": f"""Generate complete Flask DELETE route to delete {entity_name} with:
- Route: DELETE /api/{{entity_plural}}/<int:id>
- @login_required decorator
- @auto_log_crud('{entity_name.lower()}') decorator
- Soft delete (set is_deleted=True, NOT hard delete)
- Return 404 if not found
- Response format: {{"success": bool}}
- Docstring with type hints"""
    }
    
    prompt = prompts.get(operation, f"Generate Flask route for {entity_name}")
    
    return generate_code(prompt, model=model)


def generate_model(entity_name, fields, model="gpt-3.5-turbo"):
    """
    Gera model SQLAlchemy para uma entidade.
    
    Args:
        entity_name (str): Nome da entidade
        fields (list): Lista de campos no formato "nome:tipo"
                      Ex: ["name:String(200)", "age:Integer"]
        model (str): Modelo OpenAI a usar
    
    Returns:
        str: Código do model
    
    Examples:
        >>> fields = ["name:String(200)", "description:Text"]
        >>> code = generate_model("Project", fields)
        >>> print(code)
    """
    fields_str = "\n".join([f"- {f}" for f in fields])
    
    prompt = f"""Generate SQLAlchemy model for {entity_name} with these fields:
{fields_str}

Requirements:
- Include primary key 'id'
- Include audit fields: created_at, updated_at, is_deleted (soft delete)
- Include foreign keys if needed
- Include relationships if needed
- Include to_dict() method
- Include __repr__() method
- Use types compatible with PostgreSQL AND SQLite (no JSONB, ARRAY, UUID)
- Add docstring
- Add __tablename__"""
    
    return generate_code(prompt, model=model)


def interactive_mode():
    """Modo interativo para gerar código."""
    print("=" * 70)
    print("🤖 Codex Helper - GestaoVersus")
    print("=" * 70)
    print("\nModo Interativo")
    print("\nComandos especiais:")
    print("  exit, quit, sair  - Sair do modo interativo")
    print("  route <Entity> <operation> - Gerar rota (ex: route Project create)")
    print("  model <Entity> - Gerar model básico")
    print("\nOu digite seu prompt customizado.\n")
    
    while True:
        try:
            user_input = input(">>> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'sair']:
                print("\n👋 Até logo!")
                break
            
            # Comando route
            if user_input.startswith('route '):
                parts = user_input.split()
                if len(parts) >= 3:
                    entity = parts[1]
                    operation = parts[2]
                    print(f"\n⏳ Gerando rota {operation} para {entity}...\n")
                    code = generate_route(entity, operation)
                else:
                    print("Uso: route <Entity> <operation>")
                    print("Operações: create, list, get, update, delete")
                    continue
            
            # Comando model
            elif user_input.startswith('model '):
                entity = user_input.split()[1] if len(user_input.split()) > 1 else "Entity"
                print(f"\n⏳ Gerando model para {entity}...\n")
                fields = ["name:String(200)", "description:Text"]
                code = generate_model(entity, fields)
            
            # Prompt customizado
            else:
                print("\n⏳ Gerando código...\n")
                code = generate_code(user_input)
            
            print("─" * 70)
            print(code)
            print("─" * 70)
            print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Até logo!")
            break
        except Exception as e:
            print(f"\nERRO: {e}\n")


def main():
    """Função principal com exemplos."""
    print("=" * 70)
    print("🤖 Codex Helper - GestaoVersus")
    print("=" * 70)
    
    # Verificar configuração
    if not openai.api_key:
        print("\n⚠️  OPENAI_API_KEY não configurada!")
        print("\nPara usar este script:")
        print("1. Crie arquivo .env na raiz do projeto")
        print("2. Adicione: OPENAI_API_KEY=sk-abc123...")
        print("3. Execute novamente\n")
        return
    
    print("\n✅ API Key configurada!")
    print(f"✅ Instruções carregadas de: {INSTRUCTIONS_FILE.relative_to(project_root)}")
    
    # Menu
    print("\n" + "=" * 70)
    print("Escolha uma opção:")
    print("=" * 70)
    print("\n1. Gerar rota Flask")
    print("2. Gerar model SQLAlchemy")
    print("3. Gerar CRUD completo")
    print("4. Modo interativo (livre)")
    print("5. Sair")
    
    choice = input("\nOpção (1-5): ").strip()
    
    if choice == "1":
        entity = input("Nome da entidade (ex: Project): ").strip()
        print("\nOperações disponíveis:")
        print("1. create")
        print("2. list")
        print("3. get")
        print("4. update")
        print("5. delete")
        op_choice = input("\nOperação (1-5): ").strip()
        operations = {
            "1": "create", "2": "list", "3": "get",
            "4": "update", "5": "delete"
        }
        operation = operations.get(op_choice, "create")
        
        print(f"\n⏳ Gerando rota {operation} para {entity}...\n")
        code = generate_route(entity, operation)
        print("─" * 70)
        print(code)
        print("─" * 70)
    
    elif choice == "2":
        entity = input("Nome da entidade (ex: Project): ").strip()
        print("\nDigite os campos (um por linha, formato: nome:tipo)")
        print("Exemplo: name:String(200)")
        print("Digite 'fim' quando terminar")
        fields = []
        while True:
            field = input("Campo: ").strip()
            if field.lower() == 'fim':
                break
            if field:
                fields.append(field)
        
        print(f"\n⏳ Gerando model para {entity}...\n")
        code = generate_model(entity, fields)
        print("─" * 70)
        print(code)
        print("─" * 70)
    
    elif choice == "3":
        entity = input("Nome da entidade (ex: Project): ").strip()
        print(f"\n⏳ Gerando CRUD completo para {entity}...\n")
        
        operations = ['create', 'list', 'get', 'update', 'delete']
        for op in operations:
            print(f"\n📝 Gerando {op.upper()}...")
            code = generate_route(entity, op)
            print(f"\n### {op.upper()} ###")
            print("─" * 70)
            print(code)
            print("─" * 70)
    
    elif choice == "4":
        interactive_mode()
    
    elif choice == "5":
        print("\n👋 Até logo!")
    
    else:
        print("\n⚠️  Opção inválida!")


if __name__ == "__main__":
    main()


