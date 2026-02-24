from app import create_app
from models import db, Company
import json

app = create_app()
app.config['TESTING'] = True
client = app.test_client()

with app.app_context():
    # Setup test user for permissions
    pass
