import sys
import os

# ─────────────────────────────────────────────────────────────────
# ENTRYPOINT: passenger_wsgi.py  (Flask – Gestão Versus)
# Este arquivo é carregado pelo uWSGI/Passenger do Configr.
# Nunca deve importar Django – a stack é: Flask + PostgreSQL.
# ─────────────────────────────────────────────────────────────────

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
APP_DIR   = BASE_DIR if os.path.exists(os.path.join(BASE_DIR, 'app.py')) else os.path.join(BASE_DIR, 'app32')
VENV_SITE = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages'

# 1. Garante que o virtualenv tem prioridade no sys.path
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# 2. Garante que a pasta real do app (onde está app.py) está no path
#    No Configr, o entrypoint público fica em /www/passenger_wsgi.py,
#    enquanto a aplicação Flask versionada fica em /www/app32/app.py.
for path in (APP_DIR, BASE_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

if os.path.isdir(APP_DIR):
    os.chdir(APP_DIR)

# 3. Sinaliza modo produção antes de qualquer import do Flask
os.environ.setdefault('FLASK_ENV',    'production')
os.environ.setdefault('FLASK_CONFIG', 'production')

# 4. Carrega variáveis do .env local (complementa as do uWSGI)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    if APP_DIR != BASE_DIR:
        load_dotenv(os.path.join(APP_DIR, '.env'), override=True)
except ImportError:
    pass  # python-dotenv não instalado – variáveis virão do uWSGI

# 5. Inicializa a aplicação Flask
try:
    from app import create_app
    application = create_app('production')
except Exception:
    # Salva traceback completo para diagnóstico sem suprimir o erro
    import traceback
    _log_path = os.path.join(APP_DIR, 'logs', 'startup_error.log')
    os.makedirs(os.path.dirname(_log_path), exist_ok=True)
    with open(_log_path, 'a') as _f:
        _f.write('\n\n--- STARTUP ERROR ---\n')
        traceback.print_exc(file=_f)
    raise
