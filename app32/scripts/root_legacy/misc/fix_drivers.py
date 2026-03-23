import os

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

broken = """        const participantsList = {{ participants | tojson | safe
      }
    };"""

fixed = """        const participantsList = {{ participants | tojson | safe }};"""

if broken in content:
    print("Found broken content, fixing...")
    new_content = content.replace(broken, fixed)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed!")
else:
    print("Broken content not found exactly as specified.")
    # Try a more fuzzy match
    import re
    fuzzy_pattern = r'const participantsList = \{\{ participants \| tojson \| safe\s+\}\s+\};'
    if re.search(fuzzy_pattern, content):
        print("Found fuzzy match, fixing...")
        new_content = re.sub(fuzzy_pattern, 'const participantsList = {{ participants | tojson | safe }};', content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed fuzzy!")
    else:
        print("Could not find patterns.")
        # Print a small chunk to see what's actually there
        start = content.find('const participantsList =')
        if start != -1:
            print(f"Actual content found: '{content[start:start+100]}'")
