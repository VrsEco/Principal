import re

path = r'c:\GestaoVersus\app32\templates\meetings_manage.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Look for the broken block regardless of exact indentation/whitespace
pattern = r'try\s*\{\s*employeesData\s*=\s*\{\{\s*employees\s*\|\s*tojson\s*\|\s*safe\s*\}\s*\};?\s*\}\s*catch\s*\(e\)\s*\{'
# Wait, the current broken one is:
# employeesData = {{ employees | tojson | safe }
#         };
#     } catch (e) {

pattern = r'employeesData\s*=\s*\{\{\s*employees\s*\|\s*tojson\s*\|\s*safe\s*\}\s*\};?\s*\}\s*catch\s*\(e\)\s*\{'

replacement = 'employeesData = {{ employees | tojson | safe }};\n        } catch (e) {'

# Let's just go very broad
final_fix = """    document.addEventListener('DOMContentLoaded', () => {
        try {
            employeesData = {{ employees | tojson | safe }};
        } catch (e) {
            console.error('Error parsing employeesData:', e);
            employeesData = [];
        }
    });"""

# Replace everything from "document.addEventListener('DOMContentLoaded', () => {" to the end of the script tag
content = re.sub(r"document\.addEventListener\('DOMContentLoaded', \(\) => \{.*?\}\);", final_fix, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Fix applied")
