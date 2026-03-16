import sys
import os

# Add virtualenv site-packages — Cloudez já faz isso via uwsgi.ini pythonpath
# Mas garantimos aqui também para segurança
VENV_SITE = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

# Adiciona a pasta app32 ao path
APP32_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app32')
if APP32_DIR not in sys.path:
    sys.path.insert(0, APP32_DIR)

# Carrega o .env da pasta app32
from dotenv import load_dotenv
load_dotenv(os.path.join(APP32_DIR, '.env'))

# Cria a aplicação Flask
from app import create_app
application = create_app('production')
