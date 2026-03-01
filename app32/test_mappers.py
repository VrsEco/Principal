
import os
import sys
from app import create_app
from models import db
from sqlalchemy.orm import configure_mappers

os.environ['TELEGRAM_SETUP_WEBHOOK'] = 'false'
print("Testing mapper configuration...")
try:
    app = create_app('production')
    with app.app_context():
        configure_mappers()
        print("✅ SQLAlchemy Mappers configured successfully.")
except Exception as e:
    print(f"❌ Mapper Configuration FAILED: {e}")
    import traceback
    traceback.print_exc()
