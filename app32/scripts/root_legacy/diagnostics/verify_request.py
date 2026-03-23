
import os
import sys
import traceback

sys.path.append(os.getcwd())

try:
    from app import create_app
    
    app = create_app('testing')
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess['active_company_id'] = 1
            sess['_user_id'] = '1'
        
        rsp = c.get('/incentives')
        print("Status code:", rsp.status_code)
        
        if rsp.status_code == 500:
            print("Response text:", rsp.get_data(as_text=True))
        
except Exception as e:
    traceback.print_exc()
