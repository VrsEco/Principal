
with open('deploy_stdout.txt', 'r', encoding='latin-1', errors='replace') as f:
    print("--- STDOUT ---")
    print(f.read())

with open('deploy_stderr.txt', 'r', encoding='latin-1', errors='replace') as f:
    print("--- STDERR ---")
    print(f.read())
