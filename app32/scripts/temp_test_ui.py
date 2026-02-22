import sys, os
sys.path.append('c:/GestaoVersus/app31')
from app_pev import app, inject_ui_reference
with app.test_request_context('/implantacao/financeiro-plano-investimento'):
    print('Result:', inject_ui_reference())
