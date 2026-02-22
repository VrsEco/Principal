
from app import create_app
from models import db, User
import sys

app = create_app()

def manage_admin(email, password):
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"User {email} found. Current details: role={user.role}, is_active={user.is_active}")
            print(f"Updating password to {password} and ensuring admin role.")
            user.set_password(password)
            user.role = 'admin'
            user.is_active = True
            db.session.commit()
            print("DONE: Password and role updated successfully.")
        else:
            print(f"User {email} not found. Creating a new admin user.")
            try:
                new_user = User(
                    email=email,
                    name="Administrador Master",
                    role="admin",
                    is_active=True
                )
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                print("DONE: New admin user created successfully.")
            except Exception as e:
                db.session.rollback()
                print(f"ERROR: Failed to create user: {str(e)}")

if __name__ == "__main__":
    manage_admin("admin@gestaoversus.com.br", "123456")
