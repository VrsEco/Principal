file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = 0
for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    
    if 'const participantsList =' in line:
        print(f"Found participantsList at line {i+1}")
        new_lines.append(f"        const participantsList = {{ participants | tojson | safe }};\n")
        # Check if next lines are the rogue braces
        if i + 1 < len(lines) and '}' in lines[i+1].strip() and len(lines[i+1].strip()) <= 2:
            print(f"Skipping rogue line {i+2}: {lines[i+1].strip()}")
            skip = 1
            if i + 2 < len(lines) and '};' in lines[i+2].strip() and len(lines[i+2].strip()) <= 3:
                print(f"Skipping rogue line {i+3}: {lines[i+2].strip()}")
                skip = 2
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print("Done!")
