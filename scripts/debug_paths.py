import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def normalize_path(path):
    if isinstance(path, tuple):
        path = path[0]
    return str(path).replace('\\', '/').strip('/')

def diagnose():
    print("Diagnóstico de Paths com Normalização...")
    
    # 1. Verificar Banco
    pages = UIReferenceService.get_all_pages()
    print(f"Páginas no banco: {len(pages)}")
    
    db_paths = set()
    for p in pages:
        if p['template_file']:
            norm = normalize_path(p['template_file'])
            db_paths.add(norm)
            
    print(f"Paths normalizados no banco (amostra): {list(db_paths)[:20]}")
    return
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, 'templates')
    
    sample_files = []
    matches = 0
    count = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                if file == 'base.html': continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, templates_dir)
                norm_path = normalize_path(rel_path)
                
                print(f"Arquivo disco: {norm_path}")
                
                if norm_path in db_paths:
                    matches += 1
                    print("MATCH DIRETO!")
                else:
                    # Tentar com templates/ prefix
                    alt = normalize_path(os.path.join('templates', rel_path))
                    print(f"Tentando alt: {alt}")
                    if alt in db_paths:
                        matches += 1
                        print(f"MATCH ALT!")
                    else:
                        print("NO MATCH")
                
                count += 1
                if count >= 10: return

    print(f"Total Matches: {matches}")

    print(f"Total Matches: {matches}")

if __name__ == '__main__':
    diagnose()
