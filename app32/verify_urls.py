
import os
import sys
import traceback

sys.path.append(os.getcwd())

try:
    from app import create_app
    from flask import url_for
    
    app = create_app('testing')
    with app.test_request_context():
        print(f"Dashboard: {url_for('incentives.dashboard')}")
        print(f"Seed: {url_for('incentives.seed_mock_data')}")
        print(f"Indicators: {url_for('incentives.indicator_list')}")
        print(f"Rules: {url_for('incentives.manage_rules', rule_set_id=1)}")
        print("All URLs resolved correctly.")

except Exception:
    traceback.print_exc()
