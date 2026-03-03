import re

with open("src/intelligence/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

# Put the function after get_active_company_id
func = """
def get_active_user_id():
    \"\"\"Recupera o ID do usuario logado ou via webhook.\"\"\"
    try:
        from flask_login import current_user
        if current_user and getattr(current_user, 'is_authenticated', False):
            return current_user.id
    except:
        pass
    usr_id = os.environ.get('ACTIVE_USER_ID')
    return int(usr_id) if dict(os.environ).get('ACTIVE_USER_ID') else None

def sanitize_output(data):"""

content = content.replace("def sanitize_output(data):", func)

# Replace occurrences
replacements = [
    ("user_id = getattr(current_user, 'id', None)", "user_id = get_active_user_id()"),
    ("user_id = current_user.id if current_user.is_authenticated else None", "user_id = get_active_user_id()"),
    ("from flask_login import current_user", ""),
]

for old, new in replacements:
    content = content.replace(old, new)

with open("src/intelligence/tools.py", "w", encoding="utf-8") as f:
    f.write(content)
