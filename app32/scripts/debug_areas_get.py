import sys
import os
sys.path.insert(0, os.getcwd())
from app import create_app
from models import db, User, ProcessArea
from flask import session

app = create_app('testing')

with app.app_context():
    from api.resources.process import ProcessAreaListResource
    from flask import request
    
    # Simulate a request context
    with app.test_request_context('/api/process-areas?company_id=5'):
        # Mocking current_user for permission_required (if possible)
        # Actually, let's just query the data directly to see what the API WOULD see
        cid = 5
        query = ProcessArea.query.filter_by(company_id=cid)
        areas = query.all()
        # Natural sort as in the resource
        from api.resources.process import natural_sort_key
        areas.sort(key=lambda x: (natural_sort_key(x.code), x.order_index or 0, x.name or ""))
        
        import sys
        
        print(f"Total areas for Company 5: {len(areas)}")
        for a in areas:
            output = f"ID: {a.id} | Code: {a.code} | Name: {a.name}"
            # Ensure we print using sys.stdout.buffer to avoid encoding issues or just encode/decode
            print(output.encode('ascii', 'ignore').decode('ascii'))
