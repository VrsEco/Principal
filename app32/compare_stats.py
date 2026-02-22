import os

def get_stats(root_dir):
    exclude = {'venv', 'node_modules', '__pycache__', '.git', '.idea', '.vscode', 'dist', 'build'}
    counts = {'py': 0, 'html': 0, 'js': 0, 'css': 0, 'total': 0}
    total_size = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in exclude]
        
        for f in files:
            counts['total'] += 1
            ext = f.split('.')[-1].lower() if '.' in f else ''
            if ext in counts:
                counts[ext] += 1
            
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except:
                pass
                
    return counts, total_size

for app in ['app31', 'app32']:
    path = os.path.join('c:\\GestaoVersus', app)
    if os.path.exists(path):
        stats, size = get_stats(path)
        print(f"--- {app.upper()} ---")
        print(f"Arquivos Totais (sem venv/node): {stats['total']}")
        print(f"Tamanho Total: {size / (1024*1024):.2f} MB")
        print(f"Python (.py): {stats['py']}")
        print(f"Templates (.html): {stats['html']}")
        print(f"Javascript (.js): {stats['js']}")
        print(f"Styles (.css): {stats['css']}")
        print()
