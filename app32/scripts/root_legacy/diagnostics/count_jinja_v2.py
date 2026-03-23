import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove Jinja comments
content_no_comments = re.sub(r'\{#.*?#\}', '', content, flags=re.DOTALL)

tokens = {
    'block': (r'\{% block', r'\{% endblock'),
    'if': (r'\{% if', r'\{% endif'),
    'for': (r'\{% for', r'\{% endfor'),
}

for name, (open_p, close_p) in tokens.items():
    opens = len(re.findall(open_p, content_no_comments))
    closes = len(re.findall(close_p, content_no_comments))
    print(f"{name}: Open={opens}, Close={closes}")
