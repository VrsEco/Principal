
import os, sys
sys.path.append(os.getcwd())
try:
    from app import create_app
    app = create_app()
    print("SUCCESS: App created successfully.")
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
