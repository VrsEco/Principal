import os
import shutil
import glob

def move_files(pattern, destination):
    if not os.path.exists(destination):
        os.makedirs(destination)
    for file in glob.glob(pattern):
        # Skip core files
        if os.path.basename(file) in ["app.py", "app_pev.py", "config.py", "PROGRESSO_GERAL.md", "requirements.txt", "organize_root.py"]:
            continue
        if os.path.isfile(file):
            try:
                shutil.move(file, os.path.join(destination, os.path.basename(file)))
                print(f"Moved {file} to {destination}")
            except Exception as e:
                print(f"Error moving {file}: {e}")

# Target directories
ROOT = os.getcwd()

# 1. More Scripts
move_files("*.py", "scripts")
move_files("*.bat", "scripts")
move_files("*.sh", "scripts")
move_files("*.ps1", "scripts")

# 2. More Logs and Temporary
move_files("*.txt", "archive/temporary")
move_files("*.json", "archive/temporary")
move_files("*.html", "archive/temporary") # temp_configr...
move_files("*.csv", "archive/temporary")
move_files("*.xlsx", "archive/temporary") # Modelo Relatório...
move_files("*.xml", "archive/temporary") # BackupDiario_Task.xml
move_files("*.db", "archive/temporary") # pevapp22.db
move_files("*.js", "archive/temporary") # INTEGRAR_HORAS...

# 3. Strange leftovers
strangers = ["-p", "rm", "python", "p", "{rule.endpoint}')", "print(POSTGRES_HOST =", "print(POSTGRES_DB =", "print(DATABASE_URL =", "print(CLOUD_SQL_CONNECTION_NAME =", "print(json.dumps(targets", "pages"]
for s in strangers:
    if os.path.exists(s):
        dest = os.path.join("archive/temporary", s.replace("(", "").replace(")", "").replace("'", ""))
        if os.path.isdir(s):
            shutil.move(s, dest)
        else:
            shutil.move(s, dest)
        print(f"Moved stranger {s} to archive/temporary")

print("Second cleanup completed.")
