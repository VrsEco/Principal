
import os
import sys
import traceback

sys.path.append(os.getcwd())

try:
    from app import create_app
    
    app = create_app('testing')
    with app.test_request_context():
        # Context processors run during render OR we can call them manually to seed jinja_env
        ctx = {}
        for func in app.template_context_processors[None]:
            ctx.update(func())
            
        t = app.jinja_env.get_template('modules/incentives/dashboard.html')
        res = t.render(
            stats={'indicators': 0, 'total_payout': 0, 'participants': 0, 'last_closing': None},
            rule_sets=[],
            history=[],
            **ctx # Pass mock context to Jinja
        )
        print("Render Successful! HTML Length:", len(res))

except Exception as e:
    traceback.print_exc()
