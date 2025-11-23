import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def simulate_lookup(test_path):
    """Simula o que o context processor faz"""
    print(f"\n{'='*60}")
    print(f"Testando path: '{test_path}'")
    print(f"{'='*60}")
    
    # Carregar páginas
    pages = UIReferenceService.get_all_pages()
    cache = {}
    for page in pages:
        if page.get('page_route'):
            cache[page['page_route']] = page['page_code']
    
    print(f"Total de rotas no cache: {len(cache)}")
    
    # Tentar match exato
    page_code = cache.get(test_path)
    if page_code:
        print(f"✓ MATCH EXATO: '{test_path}' -> Code: '{page_code}'")
        return page_code
    
    print(f"✗ Sem match exato para '{test_path}'")
    
    # Tentar variações
    variations = [
        f"/templates{test_path}",
        f"{test_path}.html",
        f"/templates{test_path}.html",
        test_path.replace('-', '_'),
        f"/templates{test_path.replace('-', '_')}",
        test_path.replace('_', '-'),
        f"/templates{test_path.replace('_', '-')}"
    ]
    
    print(f"\nTentando {len(variations)} variações:")
    for v in variations:
        code = cache.get(v)
        if code:
            print(f"  ✓ MATCH: '{v}' -> Code: '{code}'")
            return code
        else:
            print(f"  ✗ Sem match: '{v}'")
    
    # Mostrar rotas similares
    print(f"\nRotas similares no banco:")
    similar = [r for r in cache.keys() if any(part in r for part in test_path.split('/') if part)]
    for r in similar[:10]:
        print(f"  - '{r}' -> {cache[r]}")
    
    print(f"\n✗ NENHUM MATCH ENCONTRADO")
    return None

if __name__ == '__main__':
    import io
    output = io.StringIO()
    
    # Testar com as páginas que o usuário está vendo
    test_paths = [
        '/implantacao/financeiro-plano-investimento',
        '/implantacao/financeiro_plano_investimento',
        '/pev/implantacao/financeiro-plano-investimento',
        '/modelo-matriz-diferenciais'
    ]
    
    # Redirecionar prints para o buffer
    import sys
    old_stdout = sys.stdout
    sys.stdout = output
    
    for path in test_paths:
        result = simulate_lookup(path)
        if result:
            print(f"\n>>> RESULTADO: {result}-XX <<<\n")
        else:
            print(f"\n>>> RESULTADO: ??-XX <<<\n")
    
    sys.stdout = old_stdout
    
    # Salvar em arquivo
    with open('debug_output.txt', 'w', encoding='utf-8') as f:
        f.write(output.getvalue())
    
    print("Output salvo em debug_output.txt")
