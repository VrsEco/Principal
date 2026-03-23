import os

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Try to find the exact block and fix it using string replacement
import re
pattern = r'const participantsList = \{\{ participants \| tojson \| safe\s+\}\s+\};'
fixed = 'const participantsList = {{ participants | tojson | safe }};'

if re.search(pattern, text):
    print("Found pattern, fixing...")
    new_text = re.sub(pattern, fixed, text)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_text)
    print("Fixed!")
else:
    print("Pattern not found. Checking for alternative malformations...")
    # Alternative:
    pattern2 = r'const participantsList = \{\{ participants \| tojson \| safe\n\s+\}\n\s+};'
    if re.search(pattern2, text):
        print("Found alternative pattern, fixing...")
        new_text = re.sub(pattern2, fixed, text)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print("Fixed!")
    else:
        # Just find the line and replace it
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if 'const participantsList =' in line:
                print(f"Line {i+1} matches: {line}")
                if 'safe' in line and '}}' not in line:
                    print("Unclosed Jinja on this line. Checking next lines...")
                    lines[i] = fixed
                    if i+1 < len(lines) and '}' in lines[i+1]:
                         lines[i+1] = "" # clear the rogue brace line
                    if i+2 < len(lines) and '};' in lines[i+2]:
                         lines[i+2] = "" # clear the rogue semicolon line
                    print("Fixed manually in list.")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print("Final attempt at manual line replacement done.")
