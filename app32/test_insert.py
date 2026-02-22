import os
import datetime
from sqlalchemy import create_engine, text
try:
    from config import Config
    db_uri = Config.SQLALCHEMY_DATABASE_URI
except:
    db_uri = "postgresql://postgres:postgres@localhost:5432/gestao_versus"

engine = create_engine(db_uri)
try:
    with engine.connect() as conn:
        with conn.begin():
            # Test inserting a process_instance
            conn.execute(
                text("INSERT INTO activity_work_logs (activity_type, activity_id, employee_id, employee_name, work_date, hours_worked, description, created_at) VALUES ('process_instance', 9999, 3, 'Test Employee', :work_date, 1.00, 'test insert', :created_at)"),
                {"work_date": datetime.date.today(), "created_at": datetime.datetime.now()}
            )
            print("Successfully inserted process_instance!")
            # rollback so we don't leave trash
            conn.execute(text("ROLLBACK"))
            print("Rolled back test successfully.")
except Exception as e:
    print(f"Error: {e}")
