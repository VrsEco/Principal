import glob
import os

directory = r"c:\GestaoVersus\app32\api\routes"
files_updated = 0

for filepath in glob.iglob(directory + '/**/*.py', recursive=True):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        
        # Replace occurrences
        content = content.replace('url_for("main.dashboard")', 'url_for("my_work.my_work")')
        content = content.replace("url_for('main.dashboard')", "url_for('my_work.my_work')")
        content = content.replace('"redirect": "/dashboard"', '"redirect": "/my-work"')
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Updated {filepath}')
            files_updated += 1
            
    except Exception as e:
        print(f'Error processing {filepath}: {e}')

print(f'Total files updated: {files_updated}')
