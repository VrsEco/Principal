import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def debug():
    print("Debug Injeção...")
    
    # 1. Testar retorno do banco
    try:
        pages = UIReferenceService.get_all_pages()
        print(f"Páginas: {len(pages)}")
        if pages:
            first = pages[0]
            print(f"Tipo do item: {type(first)}")
            print(f"Conteúdo: {first}")
            tpl = first.get('template_file')
            print(f"Template file: {tpl} (Tipo: {type(tpl)})")
            
            if isinstance(tpl, tuple):
                print("ALERTA: Template file é tupla!")
    except Exception as e:
        print(f"Erro no banco: {e}")
        import traceback
        traceback.print_exc()

    # 2. Testar Regex
    content = '<input type="text" name="foo" />'
    pattern = r'(<input\b(?!.*type=["\']hidden["\'])[^>]*)(>)'
    
    def repl(match):
        print(f"Match groups: {match.groups()}")
        g1 = match.group(1)
        print(f"G1: {g1} (Tipo: {type(g1)})")
        return match.group(0)
        
    try:
        re.sub(pattern, repl, content)
    except Exception as e:
        print(f"Erro no regex: {e}")

if __name__ == '__main__':
    debug()
