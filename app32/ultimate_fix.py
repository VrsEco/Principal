import os

path = r'c:\GestaoVersus\app32\templates\meetings_manage.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The broken block at the end
broken_block = """    // Initialization
    document.addEventListener('DOMContentLoaded', () => {
        try {
            employeesData = {{ employees | tojson | safe }
        };
    } catch (e) {
        console.error('Failed to load employee data:', e);
        employeesData = [];
    }
    });"""

fixed_block = """    // Initialization
    document.addEventListener('DOMContentLoaded', () => {
        try {
            employeesData = {{ employees | tojson | safe }};
        } catch (e) {
            console.error('Failed to load employee data:', e);
            employeesData = [];
        }
    });"""

if broken_block in content:
    new_content = content.replace(broken_block, fixed_block)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(new_content)
    print("Fixed target!")
else:
    print("Broken block not found exactly. Trying fuzzy match.")
    import re
    # Match // Initialization until the end of that block
    pattern = r'// Initialization.*?document\.addEventListener\(.*?\}\);'
    # Actually, let's just find the last occurrence of employeesData = {{ employees | tojson | safe }
    if 'employeesData = {{ employees | tojson | safe }' in content:
        # Replace only that line and fix surrounding
        content = content.replace('employeesData = {{ employees | tojson | safe }', 'employeesData = {{ employees | tojson | safe }};')
        # Also fix the weird }; } catch structure
        content = content.replace('};\n    } catch (e) {', '} catch (e) {')
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        print("Fixed via simple replace!")
    else:
        print("Tag not found.")
