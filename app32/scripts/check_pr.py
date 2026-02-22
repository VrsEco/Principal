from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    res = db.session.execute(text("SELECT id, name, code, order_index FROM process_routines ORDER BY id DESC LIMIT 5")).fetchall()
    print("Recent process_routines:")
    for r in res:
        print(r)
