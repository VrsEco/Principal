import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def debug_routes():
    print("Diagnóstico de Rotas...")
    pages = UIReferenceService.get_all_pages()
    
    print(f"Total de páginas: {len(pages)}")
    if pages:
        p = pages[0]
        print(f"Type p: {type(p)}")
        print(f"Content p: {p}")
        
        # Tentar acessar chaves
        try:
            print(f"Code type: {type(p.get('page_code'))}")
        except:
            pass

if __name__ == '__main__':
    debug_routes()
