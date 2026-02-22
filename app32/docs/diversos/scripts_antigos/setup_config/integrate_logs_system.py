#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrate User Logs System into main application
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def integrate_logs_system():
    """Integrate the logs system into the main application"""
    print("🔗 Integrando Sistema de Logs na Aplicação Principal")
    print("=" * 60)

    # Check if app_pev.py exists
    if not os.path.exists("app_pev.py"):
        print("❌ Arquivo app_pev.py não encontrado")
        return False

    # Read current app_pev.py
    with open("app_pev.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already integrated
    if "from api.auth import auth_bp" in content:
        print("✅ Sistema de logs já integrado")
        return True

    # Add imports
    imports_to_add = [
        "from api.auth import auth_bp",
        "from api.logs import logs_bp",
        "from middleware.audit_middleware import init_audit_middleware",
    ]

    # Find where to add imports (after existing imports)
    lines = content.split("\n")
    import_end = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("from ") or line.strip().startswith("import "):
            import_end = i

    # Add new imports
    for import_line in imports_to_add:
        lines.insert(import_end + 1, import_line)
        import_end += 1

    # Add blueprint registrations
    blueprint_registrations = [
        "",
        "# Register authentication and logs blueprints",
        "app.register_blueprint(auth_bp)",
        "app.register_blueprint(logs_bp)",
        "",
        "# Initialize audit middleware",
        "init_audit_middleware(app)",
    ]

    # Find where to add blueprint registrations (after app creation)
    blueprint_insert_point = 0
    for i, line in enumerate(lines):
        if "app.register_blueprint(" in line:
            blueprint_insert_point = i

    if blueprint_insert_point == 0:
        # Find app creation
        for i, line in enumerate(lines):
            if "app = Flask(" in line:
                blueprint_insert_point = i + 1
                break

    # Add blueprint registrations
    for blueprint_line in blueprint_registrations:
        lines.insert(blueprint_insert_point, blueprint_line)
        blueprint_insert_point += 1

    # Add dashboard route
    dashboard_route = '''
# Dashboard route
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/login')
def login_redirect():
    """Redirect to auth login"""
    return redirect(url_for('auth.login'))
'''

    # Find where to add routes (before the main block)
    route_insert_point = len(lines) - 1
    for i, line in enumerate(lines):
        if 'if __name__ == "__main__":' in line:
            route_insert_point = i
            break

    # Add dashboard route
    for route_line in dashboard_route.strip().split("\n"):
        lines.insert(route_insert_point, route_line)
        route_insert_point += 1

    # Write updated content
    with open("app_pev.py", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("✅ Sistema de logs integrado com sucesso!")
    print("\n📋 Modificações realizadas:")
    print("   ✅ Imports adicionados")
    print("   ✅ Blueprints registrados")
    print("   ✅ Middleware de auditoria inicializado")
    print("   ✅ Rotas de dashboard adicionadas")

    return True


def create_dashboard_template():
    """Create basic dashboard template"""
    dashboard_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - GestãoVersus</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-shield-alt"></i> GestãoVersus
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('logs.logs_dashboard') }}">
                    <i class="fas fa-history"></i> Logs
                </a>
                <a class="nav-link" href="{{ url_for('auth.profile') }}">
                    <i class="fas fa-user"></i> Perfil
                </a>
                <a class="nav-link" href="{{ url_for('auth.logout') }}" onclick="return confirm('Deseja sair?')">
                    <i class="fas fa-sign-out-alt"></i> Sair
                </a>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <h1>Dashboard</h1>
                <p>Bem-vindo, {{ current_user.name }}!</p>
                
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="fas fa-history"></i> Logs de Atividade
                                </h5>
                                <p class="card-text">Visualize todas as atividades do sistema</p>
                                <a href="{{ url_for('logs.logs_dashboard') }}" class="btn btn-primary">
                                    Ver Logs
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="fas fa-users"></i> Usuários
                                </h5>
                                <p class="card-text">Gerencie usuários do sistema</p>
                                <a href="{{ url_for('auth.list_users') }}" class="btn btn-primary">
                                    Gerenciar
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">
                                    <i class="fas fa-user-cog"></i> Perfil
                                </h5>
                                <p class="card-text">Configure seu perfil</p>
                                <a href="{{ url_for('auth.profile') }}" class="btn btn-primary">
                                    Configurar
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""

    # Create templates directory if it doesn't exist
    os.makedirs("templates", exist_ok=True)

    # Write dashboard template
    with open("templates/dashboard.html", "w", encoding="utf-8") as f:
        f.write(dashboard_html)

    print("✅ Template de dashboard criado")


def main():
    """Main integration function"""
    print("🚀 Integrando Sistema de Logs na Aplicação")
    print("=" * 60)

    # Integrate logs system
    if not integrate_logs_system():
        return False

    # Create dashboard template
    create_dashboard_template()

    print("\n🎉 Integração concluída com sucesso!")
    print("\n📋 Próximos passos:")
    print("   1. Execute: python app_pev.py")
    print("   2. Acesse: http://localhost:5002/auth/login")
    print("   3. Login: admin@versus.com.br / 123456")
    print("   4. Teste o dashboard e sistema de logs")
    print("\n🌐 Rotas disponíveis:")
    print("   / - Dashboard principal")
    print("   /auth/login - Login")
    print("   /auth/logout - Logout")
    print("   /auth/profile - Perfil do usuário")
    print("   /logs/ - Dashboard de logs")
    print("   /logs/stats - Estatísticas")
    print("   /auth/users - Listar usuários (admin)")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
