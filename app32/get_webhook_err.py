
log_path = '/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log'
try:
    with open(log_path, 'r', encoding='latin-1') as f:
        log = f.read()
    blocks = log.split('ERROR:app:Exception on /webhook')
    if len(blocks) > 1:
        print("LAST EXCEPTION BLOCK:")
        print(blocks[-1][:2000])
    else:
        print("No exception found")
except Exception as e:
    print(e)
