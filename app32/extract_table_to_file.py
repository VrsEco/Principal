
filename = 'c:/GestaoVersus/app32/archive/backups/backup_bd_app_versus_cloud.sql'
outfile = 'c:/GestaoVersus/app32/occurrences_def.txt'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    with open(outfile, 'w', encoding='utf-8') as out:
        start_printing = False
        for line in lines:
            if 'CREATE TABLE public.occurrences (' in line:
                start_printing = True
            
            if start_printing:
                out.write(line)
                if ');' in line:
                    break
                
except Exception as e:
    with open(outfile, 'w') as out:
        out.write(f"Error: {e}")
