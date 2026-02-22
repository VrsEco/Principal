import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove comments to avoid false positives
content = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)

stack = []
# Regex to find Jinja tags
tag_pattern = re.compile(r'\{%\s*(?P<tag>if|elif|else|endif|for|endfor|block|endblock|macro|endmacro|call|endcall|set|endset)\s*')

for match in tag_pattern.finditer(content):
    tag = match.group('tag')
    line_num = content.count('\n', 0, match.start()) + 1
    
    if tag in ['if', 'for', 'block', 'macro', 'call', 'set']:
        stack.append({'tag': tag, 'line': line_num})
    elif tag.startswith('end'):
        expected = tag[3:]
        if not stack:
            print(f"ERROR: Unexpected {tag} at line {line_num}")
        else:
            top = stack.pop()
            if top['tag'] != expected:
                print(f"ERROR: Mismatch at line {line_num}: found {tag}, expected end{top['tag']} (opened at line {top['line']})")
                # Put back the top if it was a mismatch? No, stack is already popped.
    elif tag in ['elif', 'else']:
        # Check if we are inside an if
        if not any(item['tag'] == 'if' for item in stack):
             print(f"ERROR: {tag} without if at line {line_num}")

if stack:
    print("ERROR: Unclosed blocks:")
    for item in stack:
        print(f"  {item['tag']} opened at line {item['line']}")
else:
    print("SUCCESS: All Jinja blocks are balanced!")
