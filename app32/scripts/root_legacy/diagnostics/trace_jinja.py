import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    matches = re.findall(r'\{%\s*(if|endif|for|endfor|block|endblock)\s*.*?%\}', line)
    for m in matches:
        if m in ['if', 'for', 'block']:
            stack.append((m, i + 1))
        elif m.startswith('end'):
            if not stack:
                print(f"Unexpected {m} at line {i+1}")
            else:
                expected = 'end' + stack[-1][0]
                if m != expected:
                    print(f"Mismatch: found {m} at line {i+1}, expected {expected} (from line {stack[-1][1]})")
                else:
                    stack.pop()

if stack:
    print("\nUnclosed blocks:")
    for tag, line in stack:
        print(f"{tag} opened at line {line}")
