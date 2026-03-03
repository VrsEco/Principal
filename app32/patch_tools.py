
# Patch direto por número de linha
with open("src/intelligence/tools.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Lines 461-470:")
for i in range(460, 470):
    print(f"  {i+1}: {repr(lines[i])}")

# Insert after line 465 (index 464) which is the blank line before user_id
# Replace lines 466-468 (index 465-467) with the patched version
insert_at = 465  # after the blank line

# Find the exact position of 'user_id = get_active_user_id()'
for i in range(460, 475):
    if 'user_id = get_active_user_id()' in lines[i]:
        print(f"Found target at line {i+1}")
        # Replace lines[i] through lines[i+2] (the user_id = ..., if not user_id:, return)
        new_lines = [
            '    import logging as _logging\n',
            '    _log = _logging.getLogger(__name__)\n',
            '    user_id = get_active_user_id()\n',
            '    # Fallback extra: ler direto da ENV (contexto Telegram)\n',
            '    if not user_id:\n',
            '        _raw = os.environ.get(\'ACTIVE_USER_ID\')\n',
            '        if _raw:\n',
            '            user_id = int(_raw)\n',
            '    _log.warning(f"[get_my_work] user_id={user_id} | ACTIVE_USER_ID_env={os.environ.get(\'ACTIVE_USER_ID\')}")\n',
            '    if not user_id:\n',
            '        return "Erro: Usuário não autenticado."\n',
        ]
        lines[i:i+3] = new_lines
        break

with open("src/intelligence/tools.py", "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Done!")
