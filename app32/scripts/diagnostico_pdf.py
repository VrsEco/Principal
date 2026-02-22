#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar o problema do PDF no Configr
"""

import sys
import os

print("=" * 80)
print("DIAGNÓSTICO - Geração de PDF My Work")
print("=" * 80)
print()

# 1. Verificar versão do Python
print("1. Versão do Python:")
print(f"   {sys.version}")
print()

# 2. Verificar se reportlab está instalado
print("2. Verificando reportlab:")
try:
    import reportlab
    print(f"   ✓ reportlab instalado - versão: {reportlab.Version}")
    
    # Testar imports específicos
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            BaseDocTemplate,
            PageTemplate,
            Frame,
            Paragraph,
            Table,
            TableStyle,
            Spacer,
        )
        from reportlab.pdfgen import canvas
        print("   ✓ Todos os módulos do reportlab importados com sucesso")
    except ImportError as e:
        print(f"   ✗ Erro ao importar módulos do reportlab: {e}")
except ImportError:
    print("   ✗ reportlab NÃO está instalado")
    print("   Execute: pip install reportlab")
print()

# 3. Verificar se o Flask está rodando
print("3. Verificando Flask:")
try:
    from flask import Flask
    print(f"   ✓ Flask instalado")
except ImportError:
    print("   ✗ Flask NÃO está instalado")
print()

# 4. Verificar se o módulo my_work existe
print("4. Verificando módulo my_work:")
try:
    from modules.my_work import my_work_bp
    print(f"   ✓ Blueprint my_work_bp importado")
    print(f"   URL Prefix: {my_work_bp.url_prefix}")
    
    # Listar todas as rotas do blueprint
    print("   Rotas registradas:")
    for rule in my_work_bp.url_map if hasattr(my_work_bp, 'url_map') else []:
        print(f"     - {rule}")
except ImportError as e:
    print(f"   ✗ Erro ao importar my_work_bp: {e}")
except Exception as e:
    print(f"   ✗ Erro: {e}")
print()

# 5. Verificar se a aplicação está configurada
print("5. Verificando aplicação Flask:")
try:
    from app_pev import app
    print(f"   ✓ Aplicação Flask importada")
    print(f"   Debug mode: {app.debug}")
    print(f"   Environment: {os.environ.get('FLASK_ENV', 'development')}")
    
    # Listar rotas relacionadas ao my-work
    print("\n   Rotas relacionadas ao /my-work:")
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if 'my-work' in str(rule) or 'my_work' in str(rule.endpoint):
                print(f"     - {rule.rule} -> {rule.endpoint}")
except ImportError as e:
    print(f"   ✗ Erro ao importar app: {e}")
except Exception as e:
    print(f"   ✗ Erro: {e}")
print()

# 6. Testar geração de PDF simples
print("6. Testando geração de PDF simples:")
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from io import BytesIO
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 750, "Teste de PDF")
    c.save()
    
    pdf_size = len(buffer.getvalue())
    print(f"   ✓ PDF gerado com sucesso ({pdf_size} bytes)")
except Exception as e:
    print(f"   ✗ Erro ao gerar PDF: {e}")
    import traceback
    traceback.print_exc()
print()

print("=" * 80)
print("FIM DO DIAGNÓSTICO")
print("=" * 80)
