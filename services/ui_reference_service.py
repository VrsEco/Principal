"""
UI Reference Service
Gerencia códigos de referência para páginas e elementos da UI
Formato: XX-XX (página-objeto)
Exemplo: 01-01, 01-02, A5-B3
"""

from database.postgres_helper import connect
from typing import Optional, List, Dict, Tuple
import re


class UIReferenceService:
    """Serviço para gerenciar referências de UI"""
    
    @staticmethod
    def _validate_code(code: str) -> bool:
        """
        Valida formato do código (XX)
        Aceita: 01-99, A0-ZZ (alfanumérico de 2 caracteres)
        """
        pattern = r'^[0-9A-Z]{2}$'
        return bool(re.match(pattern, code.upper()))
    
    @staticmethod
    def _increment_code(code: str) -> str:
        """
        Incrementa código sequencialmente
        01 -> 02 -> ... -> 99 -> A0 -> A1 -> ... -> ZZ
        """
        code = code.upper()
        
        # Converte para número base 36 (0-9, A-Z)
        def to_base36(s):
            return int(s, 36)
        
        def from_base36(n):
            if n < 0 or n > 1295:  # 36^2 - 1
                raise ValueError("Código fora do range")
            chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            result = ''
            result = chars[n % 36] + result
            n //= 36
            result = chars[n % 36] + result
            return result
        
        try:
            num = to_base36(code)
            num += 1
            return from_base36(num)
        except:
            return '01'
    
    @staticmethod
    def get_next_page_code() -> str:
        """Retorna próximo código de página disponível"""
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT page_code 
                FROM ui_pages 
                ORDER BY page_code DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                last_code = result[0]
                return UIReferenceService._increment_code(last_code)
            else:
                return '01'  # Primeiro código
        finally:
            conn.close()
    
    @staticmethod
    def get_next_element_code(page_code: str) -> str:
        """Retorna próximo código de elemento disponível para uma página"""
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.element_code 
                FROM ui_elements e
                JOIN ui_pages p ON e.page_id = p.id
                WHERE p.page_code = %s
                ORDER BY e.element_code DESC 
                LIMIT 1
            """, (page_code,))
            result = cursor.fetchone()
            
            if result:
                last_code = result[0]
                return UIReferenceService._increment_code(last_code)
            else:
                return '01'  # Primeiro elemento da página
        finally:
            conn.close()
    
    @staticmethod
    def create_page(
        page_code: str,
        page_name: str,
        page_route: Optional[str] = None,
        module: Optional[str] = None,
        template_file: Optional[str] = None,
        description: Optional[str] = None,
        created_by: str = 'system'
    ) -> int:
        """Cria nova página no catálogo"""
        
        if not UIReferenceService._validate_code(page_code):
            raise ValueError(f"Código inválido: {page_code}. Use formato XX (ex: 01, A5, ZZ)")
        
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ui_pages 
                (page_code, page_name, page_route, module, template_file, description, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (page_code.upper(), page_name, page_route, module, template_file, description, created_by, created_by))
            
            page_id = cursor.fetchone()[0]
            conn.commit()
            return page_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def create_element(
        page_code: str,
        element_code: str,
        element_type: str,
        element_name: Optional[str] = None,
        html_id: Optional[str] = None,
        html_class: Optional[str] = None,
        css_selector: Optional[str] = None,
        xpath: Optional[str] = None,
        description: Optional[str] = None,
        created_by: str = 'system'
    ) -> int:
        """Cria novo elemento no catálogo"""
        
        if not UIReferenceService._validate_code(element_code):
            raise ValueError(f"Código inválido: {element_code}. Use formato XX (ex: 01, B3, F9)")
        
        conn = connect()
        try:
            cursor = conn.cursor()
            
            # Buscar page_id
            cursor.execute("SELECT id FROM ui_pages WHERE page_code = %s", (page_code.upper(),))
            result = cursor.fetchone()
            if not result:
                raise ValueError(f"Página não encontrada: {page_code}")
            page_id = result[0]
            
            # Inserir elemento
            cursor.execute("""
                INSERT INTO ui_elements 
                (page_id, element_code, element_type, element_name, html_id, html_class, 
                 css_selector, xpath, description, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (page_id, element_code.upper(), element_type, element_name, html_id, 
                  html_class, css_selector, xpath, description, created_by, created_by))
            
            element_id = cursor.fetchone()[0]
            conn.commit()
            return element_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def get_by_full_code(full_code: str) -> Optional[Dict]:
        """
        Busca elemento por código completo
        Exemplo: get_by_full_code('01-B3')
        """
        if '-' not in full_code:
            raise ValueError("Código deve estar no formato XX-XX (ex: 01-B3)")
        
        page_code, element_code = full_code.split('-')
        
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM v_ui_elements_full
                WHERE page_code = %s AND element_code = %s
            """, (page_code.upper(), element_code.upper()))
            
            result = cursor.fetchone()
            if result:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, result))
            return None
        finally:
            conn.close()
    
    @staticmethod
    def get_page_elements(page_code: str) -> List[Dict]:
        """Retorna todos os elementos de uma página"""
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM v_ui_elements_full
                WHERE page_code = %s
                ORDER BY element_code
            """, (page_code.upper(),))
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        finally:
            conn.close()
    
    @staticmethod
    def get_all_pages() -> List[Dict]:
        """Retorna todas as páginas cadastradas"""
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    page_code,
                    page_name,
                    page_route,
                    module,
                    template_file,
                    (SELECT COUNT(*) FROM ui_elements WHERE page_id = ui_pages.id) as element_count
                FROM ui_pages
                ORDER BY page_code
            """)
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        finally:
            conn.close()
    
    @staticmethod
    def search_elements(
        element_type: Optional[str] = None,
        element_name: Optional[str] = None,
        module: Optional[str] = None
    ) -> List[Dict]:
        """Busca elementos por filtros"""
        conn = connect()
        try:
            cursor = conn.cursor()
            
            query = "SELECT * FROM v_ui_elements_full WHERE 1=1"
            params = []
            
            if element_type:
                query += " AND element_type = %s"
                params.append(element_type)
            
            if element_name:
                query += " AND element_name ILIKE %s"
                params.append(f"%{element_name}%")
            
            if module:
                query += " AND module = %s"
                params.append(module)
            
            query += " ORDER BY page_code, element_code"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
        finally:
            conn.close()
    
    @staticmethod
    def delete_page(page_code: str) -> bool:
        """Remove página e todos seus elementos (CASCADE)"""
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ui_pages WHERE page_code = %s", (page_code.upper(),))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def delete_element(full_code: str) -> bool:
        """Remove elemento por código completo"""
        if '-' not in full_code:
            raise ValueError("Código deve estar no formato XX-XX")
        
        page_code, element_code = full_code.split('-')
        
        conn = connect()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM ui_elements 
                WHERE page_id = (SELECT id FROM ui_pages WHERE page_code = %s)
                AND element_code = %s
            """, (page_code.upper(), element_code.upper()))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()


# Funções de conveniência
def get_next_page_code() -> str:
    """Atalho para obter próximo código de página"""
    return UIReferenceService.get_next_page_code()


def get_next_element_code(page_code: str) -> str:
    """Atalho para obter próximo código de elemento"""
    return UIReferenceService.get_next_element_code(page_code)


def create_page(page_code: str, page_name: str, **kwargs) -> int:
    """Atalho para criar página"""
    return UIReferenceService.create_page(page_code, page_name, **kwargs)


def create_element(page_code: str, element_code: str, element_type: str, **kwargs) -> int:
    """Atalho para criar elemento"""
    return UIReferenceService.create_element(page_code, element_code, element_type, **kwargs)


def find(full_code: str) -> Optional[Dict]:
    """Atalho para buscar por código completo"""
    return UIReferenceService.get_by_full_code(full_code)
