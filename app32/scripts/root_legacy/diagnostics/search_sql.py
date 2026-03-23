
import re

filename = 'c:/GestaoVersus/app32/archive/backups/backup_bd_app_versus_cloud.sql'

try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if 'occurrence' in line.lower() or 'ocorr' in line.lower():
            print(f"Line {i+1}: {line.strip()}")
            # Print next 10 lines to see table definition if it's a CREATE TABLE
            for j in range(1, 15):
                if i + j < len(lines):
                    print(f"  {lines[i+j].strip()}")
            print("-" * 20)
            
except Exception as e:
    print(f"Error: {e}")
