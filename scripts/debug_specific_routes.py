import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def debug_specific():
    print("Buscando rotas específicas...")
    pages = UIReferenceService.get_all_pages()
    
    targets = [
        'financeiro_plano_investimento',
        'modelo_matriz_diferenciais'
    ]
    
    found = 0
    for p in pages:
        for t in targets:
            if t in p['template_file'] or t in p['page_route']:
                print(f"MATCH: {t}")
                print(f"  Code: {p['page_code']}")
                print(f"  Route: '{p['page_route']}'")
                print(f"  File: '{p['template_file']}'")
                found += 1
                
    print(f"Total encontrados: {found}")

if __name__ == '__main__':
    debug_specific()
