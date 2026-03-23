
log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/request_debug.log'
try:
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(''.join(lines[-30:]))
except Exception as e:
    print(f"Error: {e}")
