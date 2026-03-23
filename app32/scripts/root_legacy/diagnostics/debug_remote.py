
import subprocess
import os

key_path = "deploy_key_SECRETA.txt"
host = "app@69.164.205.75"
port = "22122"
remote_test_script = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/test_prod_init.py"

# Primeiro, criar o arquivo de teste no servidor
create_test_file_cmd = r"""
cat > /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/test_prod_init.py << 'EOF'
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
from app import create_app
print("--- TEST START ---")
try:
    app = create_app('production')
    print("✅ create_app('production') successful.")
    with app.app_context():
        from models.user import User
        count = User.query.count()
        print(f"✅ DB Connected. User count: {count}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
EOF
"""

cmd_create = [
    "ssh", "-i", key_path, "-p", port, "-o", "StrictHostKeyChecking=no", host,
    f"bash -c \"{create_test_file_cmd}\""
]

cmd_run = [
    "ssh", "-i", key_path, "-p", port, "-o", "StrictHostKeyChecking=no", host,
    "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python /srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/test_prod_init.py"
]

try:
    print("Creating test script on server...")
    subprocess.run(cmd_create, timeout=30)
    print("Running test script...")
    result = subprocess.run(cmd_run, capture_output=True, text=True, timeout=60)
    print("--- STDOUT ---")
    print(result.stdout)
    print("--- STDERR ---")
    print(result.stderr)
except Exception as e:
    print(f"Error: {e}")
