
from app import create_app
from models import db

def init():
    app = create_app()
    with app.app_context():
        print("Criando tabelas no bdversusv2...")
        db.create_all()
        print("Tabelas criadas com sucesso.")

if __name__ == "__main__":
    init()
