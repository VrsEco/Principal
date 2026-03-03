import os
import sys

# Corrige sys.path para o servidor
server_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32'
if server_path not in sys.path:
    sys.path.append(server_path)

from flask import Flask
from models import db
from models.user import User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://appgestaoversuscombr:Y71j9T8y@localhost/appgestaoversuscombr'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def check_user(telegram_id):
    with app.app_context():
        u = User.query.filter_by(telegram=telegram_id).first()
        if u:
            print(f"USER FOUND: ID={u.id}, Name={u.name}, Role={u.role}")
        else:
            print(f"USER NOT FOUND for Telegram ID: {telegram_id}")

if __name__ == "__main__":
    check_user("8507771166")
