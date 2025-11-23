import os
import re
import sys
# Adicionar diretório pai ao path para importar services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ui_reference_service import UIReferenceService

def normalize_path(path):
    """Normaliza path para usar forward slashes e remover ./ inicial"""
    if isinstance(path, tuple):
        path = path[0]
    return str(path).replace('\\', '/').strip('/')

def inject_refs_into_file(file_path, page_code):
    """
    Injeta data-ref em elementos interativos de um arquivo HTML.
    Usa Regex para evitar quebrar tags Jinja2 que o BeautifulSoup poderia corromper.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except:
            print(f"[ERRO] Não foi possível ler {file_path}")
            return []

    # Contadores para gerar códigos sequenciais (01, 02...)
    # Verificar qual o maior código já existente no arquivo para continuar dele
    existing_codes = re.findall(r'data-ref="([0-9A-Z]{2})"', content)
    
    max_counter = 0
    for code in existing_codes:
        # Tentar converter código em número para achar o maior
        try:
            if code.isdigit():
                val = int(code)
                if val > max_counter: max_counter = val
            # Ignorar códigos alfanuméricos complexos por enquanto na contagem simples
        except:
            pass
            
    counter = max_counter + 1
    
    # Lista de elementos modificados para salvar no banco
    elements_to_save = []

    # Função de substituição para regex
    def replace_tag(match):
        nonlocal counter
        tag_full = match.group(0)
        
        # Se já tem data-ref, mantém
        if 'data-ref=' in tag_full:
            return tag_full
            
        # Gerar código: 01, 02... 99, A0...
        if counter < 100:
            code = f"{counter:02d}"
        else:
            prefix_idx = (counter - 100) // 10
            suffix = (counter - 100) % 10
            import string
            letters = string.ascii_uppercase
            if prefix_idx < len(letters):
                code = f"{letters[prefix_idx]}{suffix}"
            else:
                code = f"Z{suffix}" # Fallback
        
        counter += 1
        
        tag_name = match.group(1).split()[0].replace('<', '')
        
        # Salvar para registrar no banco depois
        elements_to_save.append({
            'page_code': page_code,
            'element_code': code,
            'element_type': tag_name,
            'element_name': f"Elemento {code}",
            'description': f"Elemento auto-gerado {tag_name}"
        })
        
        # Inserção na string
        if tag_full.endswith('/>'):
            return tag_full[:-2] + f' data-ref="{code}" />'
        else:
            return tag_full[:-1] + f' data-ref="{code}">'

    # Regex patterns
    patterns = [
        r'(<button\b[^>]*)(>)',
        r'(<input\b(?!.*type=["\']hidden["\'])[^>]*)(>)',
        r'(<select\b[^>]*)(>)',
        r'(<textarea\b[^>]*)(>)',
        r'(<table\b[^>]*)(>)',
        r'(<a\b[^>]*class=["\'][^"\']*(?:btn|button)[^"\']*["\'][^>]*)(>)'
    ]
    
    original_content = content
    
    for pattern in patterns:
        content = re.sub(pattern, replace_tag, content, flags=re.IGNORECASE)

    # Salvar arquivo se houve alteração
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Injetados {len(elements_to_save)} códigos em {os.path.basename(file_path)}")
        return elements_to_save
    else:
        return []

def main():
    print("Iniciando injeção global de referências de UI...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, 'templates')
    
    # Obter todas as páginas do banco
    pages = UIReferenceService.get_all_pages()
    
    # Criar mapa normalizado: path -> page_code
    file_map = {}
    for p in pages:
        if p['template_file']:
            norm_path = normalize_path(p['template_file'])
            file_map[norm_path] = p['page_code']
            if len(file_map) <= 5:
                print(f"DEBUG MAP: Raw='{p['template_file']}' -> Norm='{norm_path}'")
            
    print(f"Páginas mapeadas do banco: {len(file_map)}")
    
    total_elements = 0
    files_processed = 0
    
    for root, dirs, files in os.walk(templates_dir):
        for file in files:
            if not file.endswith('.html'):
                continue
                
            if file == 'base.html':
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, templates_dir)
            norm_rel_path = normalize_path(rel_path)
            
            # Tentar encontrar page_code
            page_code = file_map.get(norm_rel_path)
            
            # Se não achou, tentar variações (com ou sem templates/ no inicio)
            if not page_code:
                alt_path = normalize_path(os.path.join('templates', rel_path))
                page_code = file_map.get(alt_path)
            
            if not page_code:
                # Criar nova página
                # print(f"[INFO] Criando registro para: {norm_rel_path}")
                try:
                    # Gerar código
                    next_code = UIReferenceService.get_next_page_code()
                    UIReferenceService.create_page(
                        page_code=next_code,
                        page_name=file.replace('.html', '').replace('_', ' ').title(),
                        page_route=f"/{norm_rel_path.replace('.html', '')}",
                        module=norm_rel_path.split('/')[0] if '/' in norm_rel_path else 'geral',
                        template_file=norm_rel_path
                    )
                    page_code = next_code
                    file_map[norm_rel_path] = page_code # Atualizar mapa local
                except Exception as e:
                    print(f"[ERRO] Falha ao criar página {norm_rel_path}: {e}")
                    continue
            
            # Injetar
            try:
                new_elements = inject_refs_into_file(file_path, page_code)
                if new_elements:
                    files_processed += 1
                    # Salvar elementos no banco
                    for el in new_elements:
                        try:
                            UIReferenceService.create_element(
                                page_code=el['page_code'],
                                element_code=el['element_code'],
                                element_type=el['element_type'],
                                element_name=el['element_name'],
                                description=el['description']
                            )
                            total_elements += 1
                        except:
                            pass
            except Exception as e:
                print(f"[ERRO] Falha ao processar {file}: {e}")
                import traceback
                traceback.print_exc()


    print(f"Concluído! {files_processed} arquivos alterados. Total de elementos: {total_elements}")

if __name__ == '__main__':
    main()
