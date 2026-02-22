import os

search_dir = r"c:\GestaoVersus\app32\templates"
old_layout_pattern = 'extends "layouts/app.html"'
mojibake_pattern = "Ã§"

print("Searching for old layout usage and encoding issues...")

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(".html"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    if old_layout_pattern in content:
                        print(f"OLD LAYOUT: {path}")
                        
                    if mojibake_pattern in content or "Ã£" in content:
                        print(f"ENCODING ISSUE: {path}")
                        
            except Exception as e:
                # If utf-8 fails, it might be another encoding, but we are looking for utf-8 interpreted as latin-1, so reading as utf-8 should show the characters as they are stored. 
                # Wait, if the file IS utf-8 and contains "Ã§", reading as utf-8 will show "Ã§".
                # If the file is Latin-1 and we read as utf-8, it might fail or show invalid chars.
                pass
