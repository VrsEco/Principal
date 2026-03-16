import sys
import os

pkg_dir = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app_packages'
sys.path.insert(0, pkg_dir)

print("Interpreter:", sys.executable)
print("SYS.PATH:", sys.path)

print("Files in app_packages:")
try:
    for item in os.listdir(pkg_dir):
        print(" -", item)
except Exception as e:
    print("Error listing dir:", e)

print("Trying to import flask_restful...")
try:
    import flask_restful
    print("SUCCESS! File:", flask_restful.__file__)
except Exception as e:
    print("FAILED:", e)
