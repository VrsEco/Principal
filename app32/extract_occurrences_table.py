
filename = 'c:/GestaoVersus/app32/archive/backups/backup_bd_app_versus_cloud.sql'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_printing = False
    for line in lines:
        if 'CREATE TABLE public.occurrences (' in line:
            start_printing = True
        
        if start_printing:
            print(line.strip())
            if ');' in line:
                break
                
except Exception as e:
    print(f"Error: {e}")
