import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

pos = 93616
current_pos = 0
for i, line in enumerate(lines):
    if current_pos <= pos < current_pos + len(line):
        start = max(0, i - 10)
        end = min(len(lines), i + 10)
        for j in range(start, end):
            print(f"{j+1}: {lines[j]}", end='')
        break
    current_pos += len(line)
