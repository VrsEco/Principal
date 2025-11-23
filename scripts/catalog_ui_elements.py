"""
Script de Catalogação Automática de UI
Escaneia templates/ e atribui códigos sequenciais
Formato: 01-01, 01-02, 02-01, etc.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
import sys

# Configurar encoding do console para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.ui_reference_service import UIReferenceService
from bs4 import BeautifulSoup


class UICatalogScanner:
    """Scanner automático de templates HTML"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = Path(templates_dir)
        self.pages = []
        self.elements = []
    
    def scan_templates(self) -> List[Dict]:
        """Escaneia todos os templates HTML"""
        html_files = list(self.templates_dir.rglob('*.html'))
        
        print(f"[INFO] Encontrados {len(html_files)} arquivos HTML")
        
        for html_file in html_files:
            # Pular arquivos de sistema
            if any(skip in str(html_file) for skip in ['base.html', 'error', '404', '500']):
                continue
            
            page_info = self._analyze_page(html_file)
            if page_info:
                self.pages.append(page_info)
        
        # Ordenar por módulo e nome
        self.pages.sort(key=lambda x: (x['module'], x['name']))
        
        return self.pages
    
    def _analyze_page(self, html_file: Path) -> Dict:
        """Analisa um arquivo HTML e extrai informações"""
        try:
            # Tentar ler com utf-8, fallback para latin-1 se falhar
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(html_file, 'r', encoding='latin-1') as f:
                    content = f.read()
            
            # Detectar módulo pelo caminho
            module = self._detect_module(html_file)
            
            # Detectar rota
            route = self._detect_route(content, html_file)
            
            # Nome da página (do título ou nome do arquivo)
            name = self._detect_page_name(content, html_file)
            
            # Elementos principais
            elements = self._detect_elements(content)
            
            return {
                'name': name,
                'route': route,
                'module': module,
                'template_file': str(html_file.relative_to(self.templates_dir.parent)),
                'elements': elements,
                'file_path': str(html_file)
            }
        except Exception as e:
            print(f"[ERRO] Erro ao analisar {html_file}: {e}")
            return None
    
    def _detect_module(self, html_file: Path) -> str:
        """Detecta módulo pelo caminho do arquivo"""
        path_str = str(html_file)
        
        if 'grv' in path_str.lower():
            return 'GRV'
        elif 'pev' in path_str.lower() or 'plan' in path_str.lower():
            return 'PEV'
        elif 'my_work' in path_str.lower() or 'my-work' in path_str.lower():
            return 'My Work'
        elif 'implantacao' in path_str.lower():
            return 'Implantação'
        elif 'auth' in path_str.lower():
            return 'Auth'
        elif 'company' in path_str.lower() or 'companies' in path_str.lower():
            return 'Companies'
        elif 'config' in path_str.lower():
            return 'Configs'
        elif 'routine' in path_str.lower():
            return 'Routines'
        elif 'meeting' in path_str.lower():
            return 'Meetings'
        elif 'integration' in path_str.lower():
            return 'Integrations'
        elif 'report' in path_str.lower():
            return 'Reports'
        elif 'main' in path_str.lower() or 'ecosystem' in path_str.lower():
            return 'Ecosystem'
        else:
            return 'Other'
    
    def _detect_route(self, content: str, html_file: Path) -> str:
        """Tenta detectar a rota da página"""
        # Tentar encontrar comentário com rota
        route_match = re.search(r'Route:\s*([/\w-]+)', content)
        if route_match:
            return route_match.group(1)
        
        # Inferir da estrutura de pastas
        filename = html_file.stem
        module = self._detect_module(html_file).lower()
        
        if filename == 'main':
            return '/main'
        elif filename == 'login':
            return '/login'
        elif 'dashboard' in filename:
            return f'/{module}/dashboard'
        else:
            return f'/{module}/{filename.replace("_", "-")}'
    
    def _detect_page_name(self, content: str, html_file: Path) -> str:
        """Detecta nome da página"""
        # Tentar pegar do título
        title_match = re.search(r'{% block title %}(.+?){% endblock %}', content)
        if title_match:
            title = title_match.group(1).strip()
            # Remover sufixos comuns
            title = re.sub(r'\s*\|.*$', '', title)
            return title
        
        # Usar nome do arquivo formatado
        name = html_file.stem.replace('_', ' ').title()
        return name
    
    def _detect_elements(self, content: str) -> List[Dict]:
        """Detecta elementos principais na página"""
        elements = []
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Botões
            buttons = soup.find_all(['button', 'a'], class_=re.compile(r'btn|button'))
            for btn in buttons[:10]:  # Limitar a 10 principais
                element_id = btn.get('id', '')
                element_class = ' '.join(btn.get('class', []))
                text = btn.get_text(strip=True)[:50]
                
                elements.append({
                    'type': 'button',
                    'name': text or element_id or 'Button',
                    'html_id': element_id,
                    'html_class': element_class
                })
            
            # Campos de input
            inputs = soup.find_all(['input', 'select', 'textarea'])
            for inp in inputs[:10]:
                element_id = inp.get('id', '')
                element_type = inp.get('type', inp.name)
                element_name = inp.get('name', '')
                
                elements.append({
                    'type': 'field',
                    'name': element_id or element_name or f'Field {element_type}',
                    'html_id': element_id,
                    'html_class': ' '.join(inp.get('class', []))
                })
            
            # Tabelas
            tables = soup.find_all('table')
            for i, table in enumerate(tables[:5], 1):
                table_id = table.get('id', '')
                elements.append({
                    'type': 'table',
                    'name': table_id or f'Table {i}',
                    'html_id': table_id,
                    'html_class': ' '.join(table.get('class', []))
                })
            
            # Cards
            cards = soup.find_all(class_=re.compile(r'card|surface-card'))
            for i, card in enumerate(cards[:5], 1):
                card_id = card.get('id', '')
                elements.append({
                    'type': 'card',
                    'name': card_id or f'Card {i}',
                    'html_id': card_id,
                    'html_class': ' '.join(card.get('class', []))
                })
        
        except Exception as e:
            print(f"[ERRO] Erro ao detectar elementos: {e}")
        
        return elements
    
    def populate_database(self, dry_run: bool = False):
        """Popula banco de dados com páginas e elementos"""
        if not self.pages:
            print("[ERRO] Nenhuma página para catalogar")
            return
        
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Catalogando {len(self.pages)} páginas...")
        
        for i, page in enumerate(self.pages, 1):
            # Código sequencial
            page_code = UIReferenceService._increment_code('00') if i == 1 else \
                        UIReferenceService.get_next_page_code()
            
            print(f"\n[{page_code}] {page['name']}")
            print(f"  File: {page['template_file']}")
            print(f"  Route: {page['route']}")
            print(f"  Module: {page['module']}")
            
            if not dry_run:
                try:
                    # Criar página
                    page_id = UIReferenceService.create_page(
                        page_code=page_code,
                        page_name=page['name'],
                        page_route=page['route'],
                        module=page['module'],
                        template_file=page['template_file'],
                        description=f"Auto-catalogado de {page['file_path']}",
                        created_by='catalog_script'
                    )
                    
                    # Criar elementos
                    for j, element in enumerate(page['elements'], 1):
                        element_code = f"{j:02d}"  # 01, 02, 03...
                        
                        UIReferenceService.create_element(
                            page_code=page_code,
                            element_code=element_code,
                            element_type=element['type'],
                            element_name=element['name'],
                            html_id=element.get('html_id'),
                            html_class=element.get('html_class'),
                            description=f"Auto-detectado: {element['type']}",
                            created_by='catalog_script'
                        )
                        
                        print(f"    [{page_code}-{element_code}] {element['type']}: {element['name']}")
                    
                    print(f"  [OK] Criada com {len(page['elements'])} elementos")
                
                except Exception as e:
                    print(f"  [ERRO] Erro: {e}")
            else:
                # Mostrar elementos que seriam criados
                for j, element in enumerate(page['elements'][:5], 1):
                    element_code = f"{j:02d}"
                    print(f"    [{page_code}-{element_code}] {element['type']}: {element['name']}")
                
                if len(page['elements']) > 5:
                    print(f"    ... e mais {len(page['elements']) - 5} elementos")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Catalogar elementos de UI')
    parser.add_argument('--dry-run', action='store_true', help='Apenas simular, não gravar no banco')
    parser.add_argument('--templates-dir', default='templates', help='Diretório de templates')
    
    args = parser.parse_args()
    
    # Caminho absoluto
    base_dir = Path(__file__).parent.parent
    templates_dir = base_dir / args.templates_dir
    
    if not templates_dir.exists():
        print(f"[ERRO] Diretório não encontrado: {templates_dir}")
        return
    
    print("[INFO] Iniciando catalogação de UI...")
    print(f"[INFO] Diretório: {templates_dir}")
    print()
    
    scanner = UICatalogScanner(str(templates_dir))
    scanner.scan_templates()
    scanner.populate_database(dry_run=args.dry_run)
    
    print("\n[INFO] Catalogação concluída!")
    
    if not args.dry_run:
        # Mostrar estatísticas
        all_pages = UIReferenceService.get_all_pages()
        print(f"\n[STATS] Total de páginas cadastradas: {len(all_pages)}")
        
        # Agrupar por módulo
        by_module = {}
        for page in all_pages:
            module = page['module'] or 'Other'
            by_module[module] = by_module.get(module, 0) + 1
        
        print("\n[STATS] Por módulo:")
        for module, count in sorted(by_module.items(), key=lambda x: -x[1]):
            print(f"  {module}: {count} páginas")


if __name__ == '__main__':
    main()
