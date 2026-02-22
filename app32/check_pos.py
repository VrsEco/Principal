import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

pos = 93616
start = max(0, pos - 500)
end = min(len(content), pos + 500)
print(content[start:end])
