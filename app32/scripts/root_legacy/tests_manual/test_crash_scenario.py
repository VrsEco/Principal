
import os
import sys
import telebot
from threading import Thread
from app import create_app
from api.webhooks.telegram_webhook import process_telegram_message

class MockMessage:
    def __init__(self, text, from_id):
        self.text = text
        self.from_user = type('User', (), {'id': from_id, 'first_name': 'Unknown'})()
        self.chat = type('Chat', (), {'id': from_id, 'type': 'private'})()
        self.message_id = 999

print("Simulating non-existent user on Telegram...")
os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
app = create_app('development')
with app.app_context():
    # User ID 000000 doesn't exist
    msg = MockMessage("help", 123456789)
    print("Calling process_telegram_message...")
    try:
        process_telegram_message(app, msg)
        print("✅ Finished process_telegram_message without crashing (as expected).")
    except Exception as e:
        print(f"❌ CRASHED: {e}")
        import traceback
        traceback.print_exc()
