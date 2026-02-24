import glob
import os

directory = r"c:\GestaoVersus\app32\templates"
files_updated = 0

for filepath in glob.iglob(directory + '/**/*.html', recursive=True):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        
        # Replace breadcrumb links
        content = content.replace('<a href="/dashboard">Dashboard</a>', '<a href="/my-work">Meu Trabalho</a>')
        content = content.replace('<a href="/dashboard">Cenário</a>', '<a href="/my-work">Meu Trabalho</a>')
        
        # Special catch all for remaining <a href="/dashboard"
        content = content.replace('href="/dashboard"', 'href="/my-work"')
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Updated {filepath}')
            files_updated += 1
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

print(f"Total files updated: {files_updated}")
