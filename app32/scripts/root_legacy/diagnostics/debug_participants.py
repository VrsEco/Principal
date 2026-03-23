import os

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'participantsList' in line:
            print(f"{i+1}: {line.strip()}")
        if 4465 <= i+1 <= 4480:
             print(f"L{i+1}: {line.strip()}")
