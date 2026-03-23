import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

stack = []
tokens = re.finditer(r'\{%\s*(if|endif|for|endfor|block|endblock)\s*.*?%\}', content)

for match in tokens:
    tag = match.group(1)
    line_num = content.count('\n', 0, match.start()) + 1
    if tag in ['if', 'for', 'block']:
        stack.append((tag, line_num))
    elif tag.startswith('end'):
        expected = tag[3:]
        if not stack:
            print(f"ERROR: Unexpected {tag} at line {line_num}")
        else:
            top_tag, top_line = stack.pop()
            if top_tag != expected:
                print(f"ERROR: Mismatch at line {line_num}. Found {tag}, expected end{top_tag} (opened at line {top_line})")

if stack:
    print("ERROR: Unclosed blocks:")
    for tag, line in stack:
        print(f"  {tag} opened at line {line}")
else:
    print("SUCCESS: All Jinja blocks are balanced!")
