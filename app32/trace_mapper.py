
import traceback
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

try:
    print("DEBUG: Importing app...")
    from app import create_app
    print("DEBUG: Importing models...")
    from models import db, ProcessArea, MacroProcess, Process, Company, Plan
    
    print("DEBUG: Creating app...")
    app = create_app()
    
    print("DEBUG: Setting up app context...")
    with app.app_context():
        print("DEBUG: Running query on ProcessArea...")
        print(f"Areas count: {len(ProcessArea.query.all())}")
        print("DEBUG: Running query on MacroProcess...")
        print(f"Macros count: {len(MacroProcess.query.all())}")
        print("DEBUG: Running query on Process...")
        print(f"Processes count: {len(Process.query.all())}")
        print("DEBUG: Success!")
except Exception:
    print("DEBUG: Error occurred!")
    traceback.print_exc()
