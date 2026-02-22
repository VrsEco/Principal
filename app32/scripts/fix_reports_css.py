import os

file_path = r'c:\GestaoVersus\app32\static\css\reports.css'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '/* Ocultar elementos não imprimíveis */' in line:
        new_lines.append('  /* Ocultar elementos não imprimíveis do sistema */\n')
    elif '.no-print {' in line and lines[lines.index(line)+1].strip() == 'display: none !important;':
        # This is a bit complex in a loop, let's just use string replace on the whole content
        pass
    else:
        new_lines.append(line)

# Let's try a safer way:
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """  /* Ocultar elementos não imprimíveis */
  .no-print {
    display: none !important;
  }"""

# Try both LF and CRLF
replacement = """  /* Ocultar elementos não imprimíveis do sistema */
  .no-print, .workspace-navbar, .workspace-sidebar, .workspace-sidebar-right, .navbar-actions, .app-header, .btn, .user-pill, #ui-ref-toggle {
    display: none !important;
  }"""

if target in content:
    content = content.replace(target, replacement)
elif target.replace('\n', '\r\n') in content:
    content = content.replace(target.replace('\n', '\r\n'), replacement.replace('\n', '\r\n'))
else:
    # If still not found, search only the class
    content = content.replace('.no-print {', '.no-print, .workspace-navbar, .workspace-sidebar, .workspace-sidebar-right, .navbar-actions, .app-header, .btn, .user-pill, #ui-ref-toggle {')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement attempted via script.")
