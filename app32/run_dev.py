import os
import sys
from dotenv import load_dotenv

# Carrega variáveis de ambiente primeiro
load_dotenv()

from app import create_app
from api.webhooks.telegram_webhook import setup_webhook

def start_ngrok(port):
    """Inicializa o túnel do Ngrok e retorna a URL pública."""
    from pyngrok import ngrok
    
    auth_token = os.environ.get("NGROK_AUTH_TOKEN")
    if not auth_token:
        print("❌ NGROK_AUTH_TOKEN não encontrado no arquivo .env!")
        print("Por favor, adicione seu token do Ngrok no .env antes de rodar.")
        return None

    # Configura o Ngrok com seu AuthToken
    ngrok.set_auth_token(auth_token)
    
    # Inicia túnel seguro na porta do Flask
    public_url = ngrok.connect(port, bind_tls=True).public_url
    print(f"\n🌐 [NGROK] Túnel criado com sucesso: {public_url}")
    return public_url

if __name__ == '__main__':
    port = 5032
    print("🚀 Preparando ambiente de Desenvolvimento Integrado (APP + Telegram)...")
    
    public_url = start_ngrok(port)
    
    dev_token = os.environ.get("TELEGRAM_BOT_TOKEN_DEV")
    if public_url and dev_token:
        print("\n🤖 [TELEGRAM] Registrando Webhook na API do Telegram...")
        try:
            # Chama a função que criamos no telegram_webhook.py
            setup_webhook(public_url)
        except Exception as e:
            print(f"❌ Erro ao registrar Webhook: {str(e)}")
    elif public_url and not dev_token:
        print("\n⚠️ [TELEGRAM] TELEGRAM_BOT_TOKEN_DEV não configurado. Webhook DEV não será registrado para evitar mistura com produção.")
    
    app = create_app()
    print(f"\n⚡ [FLASK] Iniciando Servidor na porta {port}...")
    
    # use_reloader=False é vital para evitar que o Flask abra dois túneis do Ngrok ao recarregar
    app.run(debug=True, port=port, use_reloader=False)
