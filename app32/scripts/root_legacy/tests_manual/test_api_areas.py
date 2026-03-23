
from app import create_app
from models import db, ProcessArea
import json

app = create_app()
with app.app_context():
    client = app.test_client()
    # We might need to mock login or session
    with client.session_transaction() as sess:
        sess['active_company_id'] = 5
        sess['_user_id'] = '1' # Assuming user 1 exists and is admin
    
    response = client.get('/api/process-areas?company_id=5')
    print(f"Status Code: {response.status_code}")
    try:
        data = response.get_json()
        print(f"Data: {json.dumps(data, indent=2)}")
    except:
        print(f"Raw Output: {response.data.decode('utf-8')}")
