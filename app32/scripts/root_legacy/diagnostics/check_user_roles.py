
import os, sys
sys.path.append(os.getcwd())
from app import create_app
from models.user import User

def check():
    app = create_app()
    with app.app_context():
        u3 = User.query.get(3)
        u4 = User.query.get(4)
        print(f"User 3 ({u3.name if u3 else 'N/A'}): {u3.role if u3 else 'N/A'}")
        print(f"User 4 ({u4.name if u4 else 'N/A'}): {u4.role if u4 else 'N/A'}")

if __name__ == "__main__":
    check()
