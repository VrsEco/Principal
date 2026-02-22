import os
import sys

# Add app directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models.role import Role

def test_roles():
    with app.app_context():
        try:
            role = Role.query.first()
            if role:
                print(f"Role fetched successfully: {role.to_dict()}")
            else:
                print("No roles found but query succeeded.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    test_roles()
