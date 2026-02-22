import os

file_path = r'c:\GestaoVersus\app32\src\intelligence\tools.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Substituicoes de Elite
content = content.replace("session.get('active_company_id')", "get_active_company_id()")
content = content.replace("Contexto de empresa não identificado", "Contexto de empresa nao identificado")
content = content.replace("Nenhuma empresa ativa selecionada na sessão", "Nenhuma empresa ativa identificada")
content = content.replace("Empresa não selecionada", "Empresa nao selecionada")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Batch update on tools.py completed.")
