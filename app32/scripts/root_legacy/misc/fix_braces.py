file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'const participantsList = {' in line and '{{' not in line:
        print(f"Fixing missing Jinja braces at line {i+1}")
        new_lines.append("        const participantsList = {{ participants | tojson | safe }};\n")
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done!")
