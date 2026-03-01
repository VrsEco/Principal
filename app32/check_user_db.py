
import os
import sys
from app import create_app
from models.user import User

os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('development')
with app.app_context():
    user = User.query.filter(User.telegram.isnot(None)).all()
    print("Users with Telegram ID:")
    for u in user:
        print(f"ID: {u.id}, Name: {u.name}, Email: {u.email}, Telegram: {u.telegram}")
    
    # Check specifically for the one in the debug script
    user2 = User.query.filter_by(telegram='551989445').first()
    if user2:
        print(f"Found user in debug script: {user2.name}")
    else:
        print("User 551989445 not found!")
