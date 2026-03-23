import traceback
import sys

with open('full_error_2.txt', 'w') as f:
    try:
        from app import create_app
        f.write("Import successful\n")
    except Exception:
        traceback.print_exc(file=f)
