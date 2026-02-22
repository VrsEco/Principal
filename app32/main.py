import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from src.core.database import db

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

def create_app():
    """
    Factory function para inicializar o servidor Flask.
    """
    # Define a pasta de templates relativa ao src
    app = Flask(__name__, template_folder='src/templates')
    
    # Habilita CORS
    CORS(app)

    # Registro de Blueprints
    from src.core.routes import core_bp
    app.register_blueprint(core_bp)

    # Rota de Health Check (mantida no main ou movida para o bp)
    @app.route('/health', methods=['GET'])
    def health():
        is_healthy, message = db.health_check()
        return jsonify({
            "status": "success" if is_healthy else "error",
            "database": {"status": "connected" if is_healthy else "disconnected", "details": message}
        }), 200 if is_healthy else 500

    @app.route('/')
    def root():
        return jsonify({
            "name": "Gestão Versus API",
            "version": "2.0.0",
            "architecture": "Body-Brain Separation (v2.0)"
        })

    return app

if __name__ == '__main__':
    # Inicializa o app
    app = create_app()
    
    # Configurações de execução
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5010)) # Usando porta diferente do legado para coexistência se necessário
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Iniciando Gestão Versus v2.0 na porta {port}...")
    app.run(host=host, port=port, debug=debug)
