
import sys
import os
from datetime import datetime

sys.path.append(os.getcwd())
from app import create_app
from models import db, ProcessInstance

app = create_app()

with app.app_context():
    # Create a dummy instance to be deleted
    inst = ProcessInstance(
        company_id=5,
        process_id=33, # Using the process we know exists
        title="Instance to Delete",
        status="pending",
        instance_code="DEL-001",
        created_at=datetime.utcnow()
    )
    db.session.add(inst)
    db.session.commit()
    print(f"Created instance {inst.id} for deletion test.")
