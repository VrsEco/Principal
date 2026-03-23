
import re
log_path = "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/log/uwsgi/uwsgi.log"
with open(log_path, "r", encoding="latin-1") as f:
    log = f.read()

# Use regex to find all traceback blocks
blocks = re.split(r'Traceback \(most recent call last\):', log)
if len(blocks) > 1:
    last_block = blocks[-1]
    # Print the lines of the last block until it ends (empty line or INFO/ERROR)
    lines = last_block.split('\n')
    print("Traceback (most recent call last):")
    for line in lines[:30]:
        print(line)
else:
    print("No traceback found.")
