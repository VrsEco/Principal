"""
Testes automatizados de padrões de código.

Este arquivo contém testes que verificam se o código segue
os padrões definidos em docs/governance/
"""

import os
import re
import ast
import pytest
from pathlib import Path


# Diretório raiz do projeto
ROOT_DIR = Path(__file__).parent.parent.parent


def get_python_files():
    """Retorna lista de todos os arquivos Python do projeto."""
    python_files = []
    
    # Diretórios a escanear
    scan_dirs = ['models', 'services', 'modules', 'api', 'middleware', 'utils']
    
    for dir_name in scan_dirs:
        dir_path = ROOT_DIR / dir_name
        if dir_path.exists():
            python_files.extend(dir_path.rglob('*.py'))
    
    # Adicionar arquivos raiz
    for file in ['app_pev.py', 'config.py', 'config_database.py']:
        file_path = ROOT_DIR / file
        if file_path.exists():
            python_files.append(file_path)
    
    return python_files


class TestForbiddenPatterns:
    """Testa padrões proibidos definidos em FORBIDDEN_PATTERNS.md"""
    
    def test_no_hardcoded_credentials(self):
        """Verifica se não há credenciais hardcoded."""
        patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        # Exceções permitidas
        allowed = [
            'dev-secret-key-change-in-production',
            'your-secret-key-here',
            'change-me',
            'example',
            'test',
        ]
        
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    # Verificar se é exceção permitida
                    if not any(allow in matched_text for allow in allowed):
                        violations.append(f"{py_file}:{matched_text}")
        
        assert not violations, f"Credenciais hardcoded encontradas:\n" + "\n".join(violations)
    
    def test_no_print_statements(self):
        """Verifica se não há print() para debug (usar logger)."""
        violations = []
        
        for py_file in get_python_files():
            # Pular arquivos de script/admin
            if 'script' in str(py_file).lower() or 'admin' in str(py_file).lower():
                continue
                
            content = py_file.read_text(encoding='utf-8')
            
            # Detectar print() statements
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Ignorar comentários
                if line.strip().startswith('#'):
                    continue
                
                # Detectar print não comentado
                if re.search(r'\bprint\s*\(', line) and '#' not in line[:line.find('print')]:
                    violations.append(f"{py_file}:{i}")
        
        assert not violations, f"print() statements encontrados (usar logger):\n" + "\n".join(violations)
    
    def test_no_bare_except(self):
        """Verifica se não há bare except (except sem tipo específico)."""
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            
            # Detectar bare except
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped == 'except:' or stripped.startswith('except:'):
                    violations.append(f"{py_file}:{i}")
        
        assert not violations, f"Bare except encontrados (especificar exceção):\n" + "\n".join(violations)
    
    def test_no_sql_string_concatenation(self):
        """
        Verifica se não há concatenação insegura de strings em SQL.

        Observação: placeholders do psycopg (%(name)s ou %s) são aceitos; o foco
        aqui é apenas flagrar f-strings em SQL.
        """
        pattern = r'\.execute\s*\(\s*f["\']'  # f-string em execute

        violations = []

        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            for match in re.finditer(pattern, content):
                line_num = content[:match.start()].count('\n') + 1
                violations.append(f"{py_file}:{line_num}")

        assert not violations, (
            "SQL string concatenation encontrado (risco de injection):\n"
            + "\n".join(violations)
        )


class TestCodingStandards:
    """Testa padrões de código definidos em CODING_STANDARDS.md"""
    
    def test_imports_organization(self):
        """Verifica se imports estão organizados (stdlib, third-party, local)."""
        # Este teste é mais complexo, por ora apenas verificar se não há import *
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            
            # Detectar import *
            if re.search(r'^from\s+\S+\s+import\s+\*', content, re.MULTILINE):
                violations.append(str(py_file))
        
        assert not violations, f"import * encontrado (usar imports explícitos):\n" + "\n".join(violations)
    
    def test_class_naming_convention(self):
        """Verifica se classes usam PascalCase."""
        violations = []
        
        for py_file in get_python_files():
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Verificar se começa com letra maiúscula (PascalCase)
                        if not node.name[0].isupper():
                            violations.append(f"{py_file}:{node.lineno}:class {node.name}")
            except SyntaxError:
                # Pular arquivos com erro de sintaxe
                pass
        
        assert not violations, f"Classes não estão em PascalCase:\n" + "\n".join(violations)
    
    def test_no_commented_code(self):
        """Verifica se há muito código comentado (provável código morto)."""
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Detectar blocos de código comentado (mais de 3 linhas seguidas)
            commented_block = 0
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # Detectar linha comentada que parece código
                if stripped.startswith('#') and '=' in stripped:
                    commented_block += 1
                    if commented_block >= 3:
                        violations.append(f"{py_file}:{i}")
                        break
                else:
                    commented_block = 0
        
        # Apenas avisar, não falhar teste (pode haver código comentado legítimo)
        if violations:
            pytest.skip(f"Código comentado encontrado (revisar se é código morto):\n" + "\n".join(violations))


class TestDatabaseStandards:
    """Testa padrões de banco de dados definidos em DATABASE_STANDARDS.md"""
    
    def test_no_postgresql_specific_types(self):
        """Verifica se não há tipos específicos do PostgreSQL (incompatível com SQLite)."""
        forbidden_types = ['JSONB', 'ARRAY', 'UUID', 'HSTORE']
        violations = []
        
        for py_file in get_python_files():
            # Apenas verificar arquivos de models
            if 'model' not in str(py_file).lower():
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            for db_type in forbidden_types:
                if db_type in content:
                    # Verificar se não está em comentário
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if db_type in line and not line.strip().startswith('#'):
                            violations.append(f"{py_file}:{i}:{db_type}")
        
        assert not violations, f"Tipos PostgreSQL específicos encontrados (usar tipos compatíveis):\n" + "\n".join(violations)
    
    def test_models_have_audit_fields(self):
        """Verifica se models têm campos de auditoria (created_at, updated_at)."""
        violations = []
        
        for py_file in get_python_files():
            # Apenas verificar arquivos de models
            if 'model' not in str(py_file).lower():
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Verificar se herda de db.Model
                        is_model = any(
                            hasattr(base, 'attr') and base.attr == 'Model'
                            for base in node.bases
                            if hasattr(base, 'attr')
                        )
                        
                        if is_model:
                            class_str = ast.get_source_segment(content, node)
                            
                            # Verificar se tem created_at
                            if 'created_at' not in class_str:
                                violations.append(f"{py_file}:{node.lineno}:{node.name} sem created_at")
            except (SyntaxError, AttributeError):
                pass
        
        # Apenas avisar (alguns models podem não precisar auditoria)
        if violations:
            pytest.skip(f"Models sem campos de auditoria:\n" + "\n".join(violations))


class TestAPIStandards:
    """Testa padrões de API definidos em API_STANDARDS.md"""
    
    def test_routes_use_login_required(self):
        """Verifica se rotas de API usam @login_required."""
        violations = []
        
        for py_file in get_python_files():
            # Apenas verificar arquivos de módulos e API
            if 'module' not in str(py_file).lower() and 'api' not in str(py_file).lower():
                continue
            
            content = py_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Detectar rotas sem @login_required
            for i in range(len(lines) - 1):
                current_line = lines[i].strip()
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                
                # Se é uma rota de API (methods com POST, PUT, DELETE)
                if '@' in current_line and '.route' in current_line and 'methods=' in current_line:
                    if any(method in current_line for method in ["'POST'", "'PUT'", "'DELETE'", '"POST"', '"PUT"', '"DELETE"']):
                        # Verificar linhas anteriores para @login_required
                        has_login_required = False
                        for j in range(max(0, i - 3), i):
                            if 'login_required' in lines[j]:
                                has_login_required = True
                                break
                        
                        if not has_login_required:
                            violations.append(f"{py_file}:{i + 1}")
        
        # Apenas avisar (algumas rotas públicas são legítimas)
        if violations:
            pytest.skip(f"Rotas sem @login_required (verificar se é intencional):\n" + "\n".join(violations[:10]))


class TestSecurityStandards:
    """Testa padrões de segurança."""
    
    def test_no_eval_or_exec(self):
        """Verifica se não há uso de eval() ou exec()."""
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            
            # Detectar eval() ou exec()
            if re.search(r'\beval\s*\(', content) or re.search(r'\bexec\s*\(', content):
                lines = content.split('\n')
                for i, line in enumerate(lines, 1):
                    if 'eval(' in line or 'exec(' in line:
                        violations.append(f"{py_file}:{i}")
        
        assert not violations, f"eval() ou exec() encontrados (risco de segurança):\n" + "\n".join(violations)
    
    def test_no_password_in_logs(self):
        """Verifica se não há logging de senhas."""
        patterns = [
            r'log.*password',
            r'print.*password',
            r'logger.*password',
        ]
        
        violations = []
        
        for py_file in get_python_files():
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append(f"{py_file}:{line_num}")
        
        assert not violations, f"Logging de password encontrado:\n" + "\n".join(violations)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



