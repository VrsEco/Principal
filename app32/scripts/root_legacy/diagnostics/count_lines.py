import os

def count_lines(root_dir):
    exclude = {'venv', 'node_modules', '__pycache__', '.git', '.idea', '.vscode', 'dist', 'build'}
    exts = {'.py', '.html', '.js', '.css'}
    stats = {ext: 0 for ext in exts}
    stats['total'] = 0
    
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in exclude]
        
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in exts:
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = sum(1 for line in file)
                        stats[ext] += lines
                        stats['total'] += lines
                except:
                    pass
                
    return stats

for app in ['app31', 'app32']:
    path = os.path.join('c:\\GestaoVersus', app)
    if os.path.exists(path):
        stats = count_lines(path)
        print(f"--- {app.upper()} ---")
        print(f"Total de Linhas: {stats['total']}")
        print(f"Python (.py): {stats['.py']}")
        print(f"Templates (.html): {stats['.html']}")
        print(f"Javascript (.js): {stats['.js']}")
        print(f"Styles (.css): {stats['.css']}")
        print()
