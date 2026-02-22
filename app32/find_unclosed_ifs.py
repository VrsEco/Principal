import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content_no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)

stack = []
tokens = re.finditer(r'\{%\s*(if|endif|elif|else)\s*.*?%\}', content_no_comments)

for match in tokens:
    tag = match.group(1)
    if tag == 'if':
        stack.append(match)
    elif tag == 'endif':
        if stack:
            stack.pop()
        else:
            print(f"Unexpected endif at character {match.start()}")

if stack:
    print("\nUnclosed if blocks:")
    for match in stack:
        # find line number
        line_num = content_no_comments.count('\n', 0, match.start()) + 1
        print(f"if at line {line_num}: {match.group(0)}")
