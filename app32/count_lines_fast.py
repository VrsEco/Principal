import os

def count_lines(root_dir):
    # Narrowing down to the app logic, excluding common library directories often found in c:\GestaoVersus
    # app31 and app32 should have subfolders like 'api', 'models', 'templates', 'static'
    # We will only look at these to avoid counting the whole lib directory if it's there
    targets = {'api', 'models', 'services', 'templates', 'static', 'utils', 'database'}
    exts = {'.py', '.html', '.js', '.css'}
    stats = {ext: 0 for ext in exts}
    stats['total'] = 0
    
    # Also check root level files like app.py, config.py
    for f in os.listdir(root_dir):
        ext = os.path.splitext(f)[1].lower()
        if ext in exts:
            file_path = os.path.join(root_dir, f)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        lines = sum(1 for line in file)
                        stats[ext] += lines
                        stats['total'] += lines
                except: pass

    for target in targets:
        target_path = os.path.join(root_dir, target)
        if not os.path.exists(target_path): continue
        
        for root, dirs, files in os.walk(target_path):
            if 'node_modules' in dirs: dirs.remove('node_modules')
            if 'venv' in dirs: dirs.remove('venv')
            
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
