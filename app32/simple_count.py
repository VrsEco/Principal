import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

content_no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)

# Count exact occurrences
ifs = len(re.findall(r'\{%\s*if\s+', content_no_comments))
endifs = len(re.findall(r'\{%\s*endif\s*%\}', content_no_comments))

print(f"if count: {ifs}")
print(f"endif count: {endifs}")
