"""
Route Audit Service
Discovers and audits all routes in the application to check logging coverage
"""

from flask import Flask, current_app
from typing import Dict, List, Any, Optional
import re
import inspect
from collections import defaultdict


class RouteAuditService:
    """Service for auditing route logging coverage"""
    
    @staticmethod
    def discover_all_routes(app: Optional[Flask] = None) -> List[Dict[str, Any]]:
        """
        Descobre todas as rotas da aplicação
        
        Returns:
            Lista de dicionários com informações das rotas
        """
        if app is None:
            app = current_app
        
        routes = []
        
        for rule in app.url_map.iter_rules():
            # Pular rotas estáticas
            if rule.endpoint == 'static':
                continue
            
            # Obter informações da rota
            route_info = {
                'endpoint': rule.endpoint,
                'path': rule.rule,
                'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
                'blueprint': None,
                'function': None,
                'function_name': None,
                'has_auto_log': False,
                'has_manual_log': False,
                'entity_type': None,
                'is_crud': False,
                'needs_logging': False
            }
            
            # Extrair nome do blueprint
            if '.' in rule.endpoint:
                route_info['blueprint'] = rule.endpoint.split('.')[0]
            
            # Obter função view
            try:
                view_func = app.view_functions.get(rule.endpoint)
                if view_func:
                    route_info['function'] = view_func
                    route_info['function_name'] = view_func.__name__
                    
                    # Verificar se tem decorador auto_log_crud
                    if hasattr(view_func, '__wrapped__'):
                        # Função foi decorada
                        route_info['has_auto_log'] = 'auto_log_crud' in str(view_func)
                    
                    # Verificar se tem chamadas manuais de log_service no código
                    try:
                        source = inspect.getsource(view_func)
                        if 'log_service' in source or 'log_create' in source or 'log_update' in source or 'log_delete' in source:
                            route_info['has_manual_log'] = True
                    except:
                        pass
            except Exception as e:
                pass
            
            # Determinar se é rota CRUD
            crud_methods = {'POST', 'PUT', 'PATCH', 'DELETE'}
            if any(method in crud_methods for method in route_info['methods']):
                route_info['is_crud'] = True
            
            # Tentar inferir tipo de entidade da URL
            route_info['entity_type'] = RouteAuditService._infer_entity_type(rule.rule)
            
            # Determinar se precisa de logging
            route_info['needs_logging'] = (
                route_info['is_crud'] and 
                not route_info['endpoint'].startswith('logs.') and
                not route_info['endpoint'].startswith('static') and
                route_info['endpoint'] not in ['login', 'auth.login', 'auth.logout']
            )
            
            routes.append(route_info)
        
        return routes
    
    @staticmethod
    def _infer_entity_type(path: str) -> Optional[str]:
        """Infere o tipo de entidade de uma URL"""
        entity_patterns = {
            r'/companies?': 'company',
            r'/plans?': 'plan',
            r'/participants?': 'participant',
            r'/projects?': 'project',
            r'/indicators?': 'indicator',
            r'/indicator-groups?': 'indicator_group',
            r'/indicator-data': 'indicator_data',
            r'/okrs?': 'okr',
            r'/meetings?': 'meeting',
            r'/processes?': 'process',
            r'/employees?': 'employee',
            r'/departments?': 'department',
            r'/portfolios?': 'portfolio',
            r'/drivers?': 'driver',
            r'/routines?': 'routine',
            r'/routine-tasks?': 'routine_task',
            r'/process-instances?': 'process_instance',
            r'/process-activities?': 'process_activity',
        }
        
        for pattern, entity_type in entity_patterns.items():
            if re.search(pattern, path):
                return entity_type
        
        return None
    
    @staticmethod
    def get_routes_without_logging(app: Optional[Flask] = None) -> List[Dict[str, Any]]:
        """
        Retorna rotas CRUD que não têm logging configurado
        
        Returns:
            Lista de rotas sem logging
        """
        all_routes = RouteAuditService.discover_all_routes(app)
        
        routes_without_logging = [
            route for route in all_routes
            if route['needs_logging'] and not route['has_auto_log'] and not route['has_manual_log']
        ]
        
        return routes_without_logging
    
    @staticmethod
    def get_routes_with_logging(app: Optional[Flask] = None) -> List[Dict[str, Any]]:
        """
        Retorna rotas que têm logging configurado
        
        Returns:
            Lista de rotas com logging
        """
        all_routes = RouteAuditService.discover_all_routes(app)
        
        routes_with_logging = [
            route for route in all_routes
            if (route['has_auto_log'] or route['has_manual_log']) and route['is_crud']
        ]
        
        return routes_with_logging
    
    @staticmethod
    def get_audit_summary(app: Optional[Flask] = None) -> Dict[str, Any]:
        """
        Retorna resumo da auditoria de logging
        
        Returns:
            Dicionário com estatísticas da auditoria
        """
        all_routes = RouteAuditService.discover_all_routes(app)
        
        crud_routes = [r for r in all_routes if r['is_crud']]
        routes_with_logging = [r for r in crud_routes if r['has_auto_log'] or r['has_manual_log']]
        routes_without_logging = [r for r in crud_routes if r['needs_logging'] and not r['has_auto_log'] and not r['has_manual_log']]
        
        # Agrupar por blueprint
        by_blueprint = defaultdict(lambda: {'total': 0, 'with_logging': 0, 'without_logging': 0})
        
        for route in crud_routes:
            blueprint = route['blueprint'] or 'main'
            by_blueprint[blueprint]['total'] += 1
            
            if route['has_auto_log'] or route['has_manual_log']:
                by_blueprint[blueprint]['with_logging'] += 1
            elif route['needs_logging']:
                by_blueprint[blueprint]['without_logging'] += 1
        
        # Agrupar por tipo de entidade
        by_entity = defaultdict(lambda: {'total': 0, 'with_logging': 0, 'without_logging': 0})
        
        for route in crud_routes:
            if route['entity_type']:
                entity = route['entity_type']
                by_entity[entity]['total'] += 1
                
                if route['has_auto_log'] or route['has_manual_log']:
                    by_entity[entity]['with_logging'] += 1
                elif route['needs_logging']:
                    by_entity[entity]['without_logging'] += 1
        
        # Calcular cobertura
        total_crud = len(crud_routes)
        total_with_logging = len(routes_with_logging)
        total_without_logging = len(routes_without_logging)
        
        coverage_percentage = 0
        if total_crud > 0:
            coverage_percentage = round((total_with_logging / total_crud) * 100, 2)
        
        return {
            'total_routes': len(all_routes),
            'total_crud_routes': total_crud,
            'routes_with_logging': total_with_logging,
            'routes_without_logging': total_without_logging,
            'routes_needing_logging': len([r for r in crud_routes if r['needs_logging']]),
            'coverage_percentage': coverage_percentage,
            'by_blueprint': dict(by_blueprint),
            'by_entity': dict(by_entity),
            'critical_missing': routes_without_logging[:10]  # Top 10 rotas críticas sem log
        }
    
    @staticmethod
    def get_route_details(endpoint: str, app: Optional[Flask] = None) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de uma rota específica
        
        Args:
            endpoint: Nome do endpoint Flask
            app: Instância Flask (opcional)
        
        Returns:
            Dicionário com detalhes da rota ou None
        """
        all_routes = RouteAuditService.discover_all_routes(app)
        
        for route in all_routes:
            if route['endpoint'] == endpoint:
                return route
        
        return None
    
    @staticmethod
    def generate_decorator_code(route: Dict[str, Any]) -> str:
        """
        Gera código do decorador para uma rota
        
        Args:
            route: Dicionário com informações da rota
        
        Returns:
            String com código do decorador
        """
        entity_type = route.get('entity_type', 'unknown')
        
        decorator_code = f"@auto_log_crud('{entity_type}')"
        
        return decorator_code
    
    @staticmethod
    def get_implementation_guide(route: Dict[str, Any]) -> Dict[str, str]:
        """
        Gera guia de implementação para adicionar logs a uma rota
        
        Args:
            route: Dicionário com informações da rota
        
        Returns:
            Dicionário com instruções de implementação
        """
        entity_type = route.get('entity_type', 'unknown')
        endpoint = route.get('endpoint', '')
        path = route.get('path', '')
        
        guide = {
            'decorator_import': 'from middleware.auto_log_decorator import auto_log_crud',
            'decorator_code': f"@auto_log_crud('{entity_type}')",
            'example': f"""
# Adicione o import no topo do arquivo:
from middleware.auto_log_decorator import auto_log_crud

# Adicione o decorador antes da definição da rota:
@blueprint.route('{path}', methods={route.get('methods', [])})
@auto_log_crud('{entity_type}')
def {route.get('function_name', 'function')}():
    # ... seu código aqui
    pass
""",
            'entity_type': entity_type,
            'endpoint': endpoint
        }
        
        return guide


# Instância global do serviço
route_audit_service = RouteAuditService()

