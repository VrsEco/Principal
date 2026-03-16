
import os, sys
import traceback
sys.path.append(os.getcwd())
try:
    from models import IndicatorGroup
    print("SUCCESS: Imported IndicatorGroup from models.")
except Exception as e:
    traceback.print_exc()
