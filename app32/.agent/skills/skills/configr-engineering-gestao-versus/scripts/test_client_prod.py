import sys
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv

def run_diagnostic():
    """
    Executa diagnóstico do startup/login do Flask em produção (CloudEZ).
    Deve rodar no servidor usando o binário do virtualenv (python3.12).
    """

    # 1. Caminhos absolutos do servidor Configr
    ROOT_WWW = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www"
    APP_DIR = os.path.join(ROOT_WWW, "app32")
    ENV_FILE = os.path.join(APP_DIR, ".env")

    print(f"--- DIAGNÓSTICO CONFIGR: {APP_DIR} ---")

    # 2. Carrega .env explicitamente
    if os.path.exists(ENV_FILE):
        load_dotenv(ENV_FILE)
        print(f"✅ Arquivo .env carregado de {ENV_FILE}")
    else:
        print(f"❌ ERRO: .env NÃO encontrado em {ENV_FILE}")
        return

    # 3. Importa Flask (injeta path do app32)
    sys.path.insert(0, APP_DIR)
    try:
        from app import create_app
        print("✅ Importação de 'app' bem-sucedida.")
    except ImportError as e:
        print(f"❌ ERRO de Importação: {e}")
        traceback.print_exc()
        return

    # 4. Cria App e Client
    try:
        # Puxa configuração 'production' conforme o .env FLASK_ENV
        config_mode = os.environ.get('FLASK_ENV', 'production')
        app = create_app(config_mode)
        client = app.test_client()
        print(f"✅ App inicializado em modo: {config_mode}")

        # 5. Testa Rota Crítica (Login)
        print("🔍 Testando GET /login ...")
        response = client.get('/login', follow_redirects=True)
        print(f"STATUS HTTP: {response.status_code}")

        if response.status_code == 200:
            print("🚀 SUCESSO! A aplicação está ONLINE e respondendo OK.")
        else:
            print(f"⚠️ AVISO: A rota retornou o código {response.status_code}")
            # Se der erro 500, o Flask-Debug ou logs mostram mais.
    
    except Exception as e:
        print("💀 ERRO CRÍTICO no Startup da Aplicação:")
        traceback.print_exc()

if __name__ == "__main__":
    run_diagnostic()
