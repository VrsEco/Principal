from app import create_app
from models import db
from models.company_performance_settings import CompanyPerformanceSettings
import json

app = create_app()
with app.app_context():
    s = CompanyPerformanceSettings.query.filter_by(company_id=1).first()
    if s:
        print(json.dumps(s.to_dict()))
    else:
        print("None")
