import re

file_path = r'c:\GestaoVersus\app32\templates\modules\pev\plan_drivers.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

tokens = {
    'block': (r'\{% block', r'\{% endblock'),
    'if': (r'\{% if', r'\{% endif'),
    'for': (r'\{% for', r'\{% endfor'),
    'macro': (r'\{% macro', r'\{% endmacro'),
    'call': (r'\{% call', r'\{% endcall')
}

for name, (open_p, close_p) in tokens.items():
    opens = len(re.findall(open_p, content))
    closes = len(re.findall(close_p, content))
    print(f"{name}: Open={opens}, Close={closes}")

# Also check for malformed {{ ... }}
unclosed_braces = len(re.findall(r'\{\{[^}]*?(?=\{|\Z)', content))
print(f"Malformed braces ({{{{ without }}}}}}): {unclosed_braces}")
