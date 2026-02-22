import os; 
for root, dirs, files in os.walk('.'):
    # Do not remove .git to check if something is staged/indexed incorrectly
    for f in files:
        fp = os.path.join(root, f)
        try:
            sz = os.path.getsize(fp)
            if sz > 90 * 1024 * 1024:
                print(f'{sz/1024/1024:.2f} MB - {fp}')
        except: pass