import sys
import os

# ─────────────────────────────────────────────────────────────────
# ENTRYPOINT: passenger_wsgi.py  (Flask – Gestão Versus)
# Este arquivo é carregado pelo uWSGI/Passenger do Configr.
# Nunca deve importar Django – a stack é: Flask + PostgreSQL.
# ─────────────────────────────────────────────────────────────────

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'

# 1. Garante que o virtualenv tem prioridade no sys.path
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# 2. Garante que a pasta do app (onde está app.py) está no path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# 3. Sinaliza modo produção antes de qualquer import do Flask
os.environ.setdefault('FLASK_ENV',    'production')
os.environ.setdefault('FLASK_CONFIG', 'production')

# 4. Carrega variáveis do .env local (complementa as do uWSGI)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
except ImportError:
    pass  # python-dotenv não instalado – variáveis virão do uWSGI

# 5. Inicializa a aplicação Flask
try:
    from app import create_app
    application = create_app('production')
except Exception:
    # Salva traceback completo para diagnóstico sem suprimir o erro
    import traceback
    _log_path = os.path.join(BASE_DIR, 'logs', 'startup_error.log')
    os.makedirs(os.path.dirname(_log_path), exist_ok=True)
    with open(_log_path, 'a') as _f:
        _f.write('\n\n--- STARTUP ERROR ---\n')
        traceback.print_exc(file=_f)
    raise
