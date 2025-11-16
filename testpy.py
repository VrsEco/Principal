#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste Completo do Sistema GestaoVersus
Cobre: Configuração, Banco de Dados, Rotas, APIs, Módulos, Autenticação
"""

import sys
import os
import io
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Configurar encoding UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Cores para output
class Colors:
    """Cores ANSI para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Imprime cabeçalho formatado"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_success(text: str):
    """Imprime mensagem de sucesso"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text: str):
    """Imprime mensagem de erro"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text: str):
    """Imprime mensagem de aviso"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text: str):
    """Imprime informação"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

# Estatísticas globais
stats = {
    'total': 0,
    'passed': 0,
    'failed': 0,
    'warnings': 0
}

def test_result(name: str, passed: bool, message: str = "", warning: bool = False):
    """Registra resultado de teste"""
    stats['total'] += 1
    if warning:
        stats['warnings'] += 1
        print_warning(f"{name}: {message}")
        return True  # Warnings não são falhas
    elif passed:
        stats['passed'] += 1
        print_success(f"{name}: {message}")
        return True
    else:
        stats['failed'] += 1
        print_error(f"{name}: {message}")
        return False

# ============================================================================
# SEÇÃO 1: CONFIGURAÇÃO E AMBIENTE
# ============================================================================

def test_configuration():
    """Testa configuração do sistema"""
    print_header("1. TESTE DE CONFIGURAÇÃO E AMBIENTE")
    
    results = []
    
    # 1.1 Verificar Python
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            results.append(test_result(
                "Versão Python",
                True,
                f"{version.major}.{version.minor}.{version.micro}"
            ))
        else:
            results.append(test_result(
                "Versão Python",
                False,
                f"Requer Python 3.9+, encontrado {version.major}.{version.minor}"
            ))
    except Exception as e:
        results.append(test_result("Versão Python", False, str(e)))
    
    # 1.2 Verificar variáveis de ambiente
    try:
        from dotenv import load_dotenv
        load_dotenv()
        results.append(test_result("dotenv", True, "Carregado"))
    except Exception as e:
        results.append(test_result("dotenv", False, str(e)))
    
    # 1.3 Verificar configuração
    try:
        from config import Config
        config = Config()
        
        # Verificar SECRET_KEY
        if config.SECRET_KEY:
            results.append(test_result("SECRET_KEY", True, "Configurado"))
        else:
            results.append(test_result("SECRET_KEY", False, "Não configurado"))
        
        # Verificar DATABASE_URL
        if config.SQLALCHEMY_DATABASE_URI:
            db_type = "PostgreSQL" if "postgresql" in config.SQLALCHEMY_DATABASE_URI.lower() else "SQLite"
            results.append(test_result("DATABASE_URI", True, f"{db_type} configurado"))
        else:
            results.append(test_result("DATABASE_URI", False, "Não configurado"))
        
        # Verificar outras configurações importantes
        checks = [
            ("SQLALCHEMY_TRACK_MODIFICATIONS", config.SQLALCHEMY_TRACK_MODIFICATIONS == False),
            ("MAX_CONTENT_LENGTH", config.MAX_CONTENT_LENGTH > 0),
            ("UPLOAD_FOLDER", bool(config.UPLOAD_FOLDER)),
        ]
        
        for name, check in checks:
            results.append(test_result(name, check, "OK" if check else "Falhou"))
            
    except Exception as e:
        results.append(test_result("Config", False, str(e)))
    
    # 1.4 Verificar arquivos essenciais
    essential_files = [
        'app_pev.py',
        'config.py',
        'config_database.py',
        'models/__init__.py',
    ]
    
    for file in essential_files:
        exists = os.path.exists(file)
        results.append(test_result(
            f"Arquivo {file}",
            exists,
            "Existe" if exists else "Não encontrado"
        ))
    
    return all(results)

# ============================================================================
# SEÇÃO 2: BANCO DE DADOS
# ============================================================================

def test_database():
    """Testa conexão e modelos do banco de dados"""
    print_header("2. TESTE DE BANCO DE DADOS")
    
    results = []
    
    # 2.1 Testar conexão
    try:
        from config_database import get_db, db_config
        db_type = db_config.db_type if hasattr(db_config, 'db_type') else 'unknown'
        results.append(test_result("config_database", True, f"Módulo carregado ({db_type})"))
    except Exception as e:
        results.append(test_result("config_database", False, str(e)))
        return False
    
    # 2.2 Testar inicialização do SQLAlchemy
    try:
        from models import db
        results.append(test_result("SQLAlchemy DB", True, "Instância criada"))
    except Exception as e:
        results.append(test_result("SQLAlchemy DB", False, str(e)))
        return False
    
    # 2.3 Testar modelos principais
    models_to_test = [
        'User',
        'Company',
        'Project',
        'Portfolio',
    ]
    
    for model_name in models_to_test:
        try:
            module = __import__(f'models.{model_name.lower()}', fromlist=[model_name])
            model_class = getattr(module, model_name, None)
            if model_class:
                results.append(test_result(f"Model {model_name}", True, "Carregado"))
            else:
                results.append(test_result(f"Model {model_name}", False, "Classe não encontrada"))
        except ImportError:
            results.append(test_result(f"Model {model_name}", False, "Módulo não encontrado"))
        except Exception as e:
            results.append(test_result(f"Model {model_name}", False, str(e)))
    
    # 2.4 Testar conexão real (se possível)
    try:
        # Criar contexto de aplicação temporário
        from flask import Flask
        temp_app = Flask(__name__)
        temp_app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///test.db'
        temp_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(temp_app)
        
        with temp_app.app_context():
            # Tentar conectar
            db.engine.connect()
            results.append(test_result("Conexão DB", True, "Conectado com sucesso"))
    except Exception as e:
        results.append(test_result("Conexão DB", False, f"Erro: {str(e)[:100]}"))
    
    return all(results)

# ============================================================================
# SEÇÃO 3: APLICAÇÃO FLASK
# ============================================================================

def test_flask_app():
    """Testa inicialização da aplicação Flask"""
    print_header("3. TESTE DE APLICAÇÃO FLASK")
    
    results = []
    
    # 3.1 Importar app
    try:
        # Tentar importar sem inicializar servidor
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_pev", "app_pev.py")
        if spec and spec.loader:
            results.append(test_result("Import app_pev", True, "Módulo encontrado"))
        else:
            results.append(test_result("Import app_pev", False, "Arquivo não encontrado"))
    except Exception as e:
        results.append(test_result("Import app_pev", False, str(e)))
    
    # 3.2 Verificar blueprints registrados
    try:
        # Ler arquivo para verificar blueprints
        with open('app_pev.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        blueprints = ['pev_bp', 'grv_bp', 'meetings_bp', 'my_work_bp']
        found_blueprints = []
        
        for bp in blueprints:
            if bp in content:
                found_blueprints.append(bp)
                results.append(test_result(f"Blueprint {bp}", True, "Registrado"))
            else:
                results.append(test_result(f"Blueprint {bp}", False, "Não encontrado"))
        
        if found_blueprints:
            results.append(test_result("Blueprints", True, f"{len(found_blueprints)}/{len(blueprints)} encontrados"))
        
    except Exception as e:
        results.append(test_result("Verificar blueprints", False, str(e)))
    
    # 3.3 Verificar Flask-Login
    try:
        from flask_login import LoginManager
        results.append(test_result("Flask-Login", True, "Disponível"))
    except Exception as e:
        results.append(test_result("Flask-Login", False, str(e)))
    
    # 3.4 Verificar rotas principais
    try:
        with open('app_pev.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        main_routes = [
            ('/', 'Home'),
            ('/login', 'Login'),
            ('/main', 'Main Menu'),
            ('/companies', 'Companies'),
        ]
        
        for route, name in main_routes:
            if f"@app.route('{route}'" in content or f'@app.route("{route}"' in content:
                results.append(test_result(f"Rota {name}", True, f"{route}"))
            else:
                results.append(test_result(f"Rota {name}", False, f"{route} não encontrada"))
    
    except Exception as e:
        results.append(test_result("Verificar rotas", False, str(e)))
    
    return all(results)

# ============================================================================
# SEÇÃO 4: MÓDULOS
# ============================================================================

def test_modules():
    """Testa módulos do sistema"""
    print_header("4. TESTE DE MÓDULOS")
    
    results = []
    
    modules_to_test = [
        ('modules.pev', 'PEV'),
        ('modules.grv', 'GRV'),
        ('modules.meetings', 'Meetings'),
        ('modules.my_work', 'My Work'),
    ]
    
    for module_path, module_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[''])
            
            # Verificar se tem blueprint
            bp_name = f"{module_name.lower().replace(' ', '_')}_bp"
            blueprint = getattr(module, bp_name, None)
            
            if blueprint:
                results.append(test_result(f"Módulo {module_name}", True, "Blueprint encontrado"))
            else:
                results.append(test_result(f"Módulo {module_name}", False, "Blueprint não encontrado"))
        
        except ImportError as e:
            results.append(test_result(f"Módulo {module_name}", False, f"Import error: {str(e)[:50]}"))
        except Exception as e:
            results.append(test_result(f"Módulo {module_name}", False, str(e)))
    
    # Verificar estrutura de diretórios
    module_dirs = ['modules/pev', 'modules/grv', 'modules/meetings', 'modules/my_work']
    for dir_path in module_dirs:
        exists = os.path.exists(dir_path)
        results.append(test_result(
            f"Diretório {dir_path}",
            exists,
            "Existe" if exists else "Não encontrado"
        ))
    
    return all(results)

# ============================================================================
# SEÇÃO 5: SERVIÇOS
# ============================================================================

def test_services():
    """Testa serviços do sistema"""
    print_header("5. TESTE DE SERVIÇOS")
    
    results = []
    
    # Verificar se diretório services existe
    if os.path.exists('services'):
        results.append(test_result("Diretório services", True, "Existe"))
        
        # Listar serviços principais
        service_files = [
            'ai_service.py',
            'route_audit_service.py',
        ]
        
        for service_file in service_files:
            service_path = f"services/{service_file}"
            exists = os.path.exists(service_path)
            results.append(test_result(
                f"Serviço {service_file}",
                exists,
                "Existe" if exists else "Não encontrado"
            ))
    else:
        results.append(test_result("Diretório services", False, "Não encontrado"))
    
    # Testar importação de serviços principais
    try:
        from services.ai_service import ai_service
        results.append(test_result("AI Service", True, "Importado"))
    except Exception as e:
        results.append(test_result("AI Service", False, f"Erro: {str(e)[:50]}"))
    
    try:
        from services.route_audit_service import route_audit_service
        results.append(test_result("Route Audit Service", True, "Importado"))
    except Exception as e:
        results.append(test_result("Route Audit Service", False, f"Erro: {str(e)[:50]}"))
    
    return all(results)

# ============================================================================
# SEÇÃO 6: APIs
# ============================================================================

def test_apis():
    """Testa APIs do sistema"""
    print_header("6. TESTE DE APIs")
    
    results = []
    
    # Verificar diretório api
    if os.path.exists('api'):
        results.append(test_result("Diretório api", True, "Existe"))
        
        api_files = [
            'auth.py',
            'logs.py',
            'route_audit.py',
        ]
        
        for api_file in api_files:
            api_path = f"api/{api_file}"
            exists = os.path.exists(api_path)
            results.append(test_result(
                f"API {api_file}",
                exists,
                "Existe" if exists else "Não encontrado"
            ))
    else:
        results.append(test_result("Diretório api", False, "Não encontrado"))
    
    # Verificar rotas de API no app_pev.py
    try:
        with open('app_pev.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        api_routes = [
            ('/api/reports', 'Reports API'),
            ('/api/companies', 'Companies API'),
        ]
        
        for route_pattern, name in api_routes:
            if route_pattern in content:
                results.append(test_result(f"Rota API {name}", True, f"{route_pattern}"))
            else:
                results.append(test_result(f"Rota API {name}", False, f"{route_pattern} não encontrada"))
    
    except Exception as e:
        results.append(test_result("Verificar rotas API", False, str(e)))
    
    return all(results)

# ============================================================================
# SEÇÃO 7: MIDDLEWARE E DECORATORS
# ============================================================================

def test_middleware():
    """Testa middleware e decorators"""
    print_header("7. TESTE DE MIDDLEWARE")
    
    results = []
    
    # Verificar decorator de log automático
    try:
        from middleware.auto_log_decorator import auto_log_crud, get_auto_logging_config
        results.append(test_result("Auto Log Decorator", True, "Importado"))
        
        # Testar configuração
        try:
            config = get_auto_logging_config()
            results.append(test_result("Auto Log Config", True, "Configurado"))
        except Exception as e:
            results.append(test_result("Auto Log Config", False, str(e)))
    
    except ImportError:
        results.append(test_result("Auto Log Decorator", False, "Não encontrado"))
    except Exception as e:
        results.append(test_result("Auto Log Decorator", False, str(e)))
    
    # Verificar se diretório middleware existe
    if os.path.exists('middleware'):
        results.append(test_result("Diretório middleware", True, "Existe"))
    else:
        results.append(test_result("Diretório middleware", False, "Não encontrado"))
    
    return all(results)

# ============================================================================
# SEÇÃO 8: TEMPLATES E STATIC
# ============================================================================

def test_templates_static():
    """Testa templates e arquivos estáticos"""
    print_header("8. TESTE DE TEMPLATES E STATIC")
    
    results = []
    
    # Verificar diretórios
    dirs_to_check = [
        ('templates', 'Templates'),
        ('static', 'Static'),
        ('css', 'CSS'),
    ]
    
    for dir_path, name in dirs_to_check:
        exists = os.path.exists(dir_path)
        results.append(test_result(
            f"Diretório {name}",
            exists,
            "Existe" if exists else "Não encontrado"
        ))
    
    # Verificar templates principais
    if os.path.exists('templates'):
        main_templates = [
            'base.html',
            'login.html',
            'ecosystem.html',  # Template usado na rota /main
        ]
        
        for template in main_templates:
            template_path = f"templates/{template}"
            exists = os.path.exists(template_path)
            results.append(test_result(
                f"Template {template}",
                exists,
                "Existe" if exists else "Não encontrado"
            ))
    
    return all(results)

# ============================================================================
# SEÇÃO 9: TESTE DE SERVIDOR (OPCIONAL)
# ============================================================================

def test_server(port: int = 5002, timeout: int = 5):
    """Testa se o servidor está rodando e responde"""
    print_header("9. TESTE DE SERVIDOR (OPCIONAL)")
    
    results = []
    
    try:
        import requests
    except ImportError:
        results.append(test_result("requests", False, "Biblioteca não instalada"))
        print_warning("Instale com: pip install requests")
        return False
    
    base_url = f"http://127.0.0.1:{port}"
    
    # Testar rotas principais
    routes_to_test = [
        ('/', 'Home'),
        ('/login', 'Login'),
    ]
    
    for route, name in routes_to_test:
        try:
            response = requests.get(f"{base_url}{route}", timeout=timeout, allow_redirects=False)
            status = response.status_code
            
            if status in [200, 302, 401]:
                results.append(test_result(
                    f"Servidor {name}",
                    True,
                    f"Status {status}"
                ))
            else:
                results.append(test_result(
                    f"Servidor {name}",
                    False,
                    f"Status {status}"
                ))
        
        except requests.exceptions.ConnectionError:
            results.append(test_result(
                f"Servidor {name}",
                False,
                "Servidor não está rodando"
            ))
        except Exception as e:
            results.append(test_result(
                f"Servidor {name}",
                False,
                str(e)[:50]
            ))
    
    return all(results)

# ============================================================================
# SEÇÃO 10: DEPENDÊNCIAS
# ============================================================================

def test_dependencies():
    """Testa dependências principais"""
    print_header("10. TESTE DE DEPENDÊNCIAS")
    
    results = []
    
    dependencies = [
        ('flask', 'Flask'),
        ('flask_login', 'Flask-Login'),
        ('sqlalchemy', 'SQLAlchemy'),
        ('werkzeug', 'Werkzeug'),
        ('dotenv', 'python-dotenv'),
    ]
    
    for module_name, display_name in dependencies:
        try:
            __import__(module_name)
            results.append(test_result(display_name, True, "Instalado"))
        except ImportError:
            results.append(test_result(display_name, False, "Não instalado"))
    
    # Dependências opcionais
    optional_deps = [
        ('celery', 'Celery'),
        ('requests', 'Requests'),
        ('bcrypt', 'bcrypt'),
    ]
    
    for module_name, display_name in optional_deps:
        try:
            __import__(module_name)
            results.append(test_result(display_name, True, "Instalado (opcional)"))
        except ImportError:
            results.append(test_result(display_name, False, "Não instalado (opcional)", warning=True))
    
    # Retornar True se todas as dependências obrigatórias estão instaladas
    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Executa todos os testes"""
    print_header("TESTE COMPLETO DO SISTEMA GESTAOVERSUS")
    print_info(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Executar testes
    test_functions = [
        ("Configuração", test_configuration),
        ("Banco de Dados", test_database),
        ("Aplicação Flask", test_flask_app),
        ("Módulos", test_modules),
        ("Serviços", test_services),
        ("APIs", test_apis),
        ("Middleware", test_middleware),
        ("Templates/Static", test_templates_static),
        ("Dependências", test_dependencies),
    ]
    
    # Executar testes básicos primeiro
    for name, test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print_error(f"Erro ao executar teste {name}: {e}")
            stats['failed'] += 1
    
    # Teste de servidor (opcional, pode falhar se servidor não estiver rodando)
    try:
        test_server()
    except Exception as e:
        print_warning(f"Teste de servidor pulado: {e}")
    
    # Resumo final
    print_header("RESUMO DOS TESTES")
    
    total = stats['total']
    passed = stats['passed']
    failed = stats['failed']
    warnings = stats['warnings']
    
    print_info(f"Total de testes: {total}")
    print_success(f"Passou: {passed}")
    print_error(f"Falhou: {failed}")
    print_warning(f"Avisos: {warnings}")
    
    if total > 0:
        success_rate = (passed / total) * 100
        print_info(f"Taxa de sucesso: {success_rate:.1f}%")
    
    print_header("FIM DOS TESTES")
    
    # Exit code
    if failed == 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário.")
        sys.exit(130)
    except Exception as e:
        print_error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

