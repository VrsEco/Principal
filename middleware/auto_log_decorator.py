"""
Auto-logging decorator system
Automatically logs CRUD operations with intelligent entity detection
"""

from functools import wraps
from flask import request, g
from flask_login import current_user
from services.log_service import log_service
import json
import re
from typing import Optional, Dict, Any, Callable


class AutoLogConfig:
    """Configuration for auto-logging"""
    # Rotas que devem ser ignoradas automaticamente
    SKIP_ENDPOINTS = [
        'static',
        'favicon',
        'logs.list_logs',
        'logs.get_log_stats',
        'logs.logs_dashboard',
        'logs.export_logs',
        'login',
        'auth.login',
        'auth.logout'
    ]
    
    # Mapeamento de padrões de URL para tipos de entidade
    ENTITY_TYPE_PATTERNS = {
        r'/companies/(\d+)': 'company',
        r'/plans/([^/]+)': 'plan',
        r'/participants/(\d+)': 'participant',
        r'/projects/(\d+)': 'project',
        r'/indicators/(\d+)': 'indicator',
        r'/indicator-groups/(\d+)': 'indicator_group',
        r'/indicator-data/(\d+)': 'indicator_data',
        r'/okrs?/(\d+)': 'okr',
        r'/meetings/(\d+)': 'meeting',
        r'/processes/(\d+)': 'process',
        r'/employees/(\d+)': 'employee',
        r'/departments/(\d+)': 'department',
        r'/portfolios/(\d+)': 'portfolio',
        r'/drivers/(\d+)': 'driver',
        r'/routines/(\d+)': 'routine',
        r'/routine-tasks/(\d+)': 'routine_task',
        r'/process-instances/(\d+)': 'process_instance',
        r'/process-activities/(\d+)': 'process_activity',
    }
    
    # Entidades que devem ser registradas
    ENABLED_ENTITIES = set()  # Vazio = todas habilitadas
    DISABLED_ENTITIES = set()  # Entidades desabilitadas explicitamente


def extract_entity_info(path: str, method: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Extrai informações sobre a entidade da URL e dados
    
    Args:
        path: Caminho da URL
        method: Método HTTP
        data: Dados da requisição
    
    Returns:
        Dict com entity_type, entity_id, entity_name
    """
    entity_info = {
        'entity_type': None,
        'entity_id': None,
        'entity_name': None,
        'company_id': None,
        'plan_id': None
    }
    
    # Tentar extrair company_id da URL
    company_match = re.search(r'/company/(\d+)', path)
    if company_match:
        entity_info['company_id'] = int(company_match.group(1))
    
    # Tentar extrair tipo de entidade e ID
    for pattern, entity_type in AutoLogConfig.ENTITY_TYPE_PATTERNS.items():
        match = re.search(pattern, path)
        if match:
            entity_info['entity_type'] = entity_type
            entity_info['entity_id'] = match.group(1)
            break
    
    # Se não encontrou na URL, tentar inferir do endpoint
    if not entity_info['entity_type']:
        path_parts = path.strip('/').split('/')
        for part in path_parts:
            if part in ['companies', 'company']:
                entity_info['entity_type'] = 'company'
            elif part in ['plans', 'plan']:
                entity_info['entity_type'] = 'plan'
            elif part in ['projects', 'project']:
                entity_info['entity_type'] = 'project'
            elif part in ['indicators', 'indicator']:
                entity_info['entity_type'] = 'indicator'
            elif part in ['meetings', 'meeting']:
                entity_info['entity_type'] = 'meeting'
    
    # Tentar extrair nome da entidade dos dados
    if data:
        if isinstance(data, dict):
            entity_info['entity_name'] = (
                data.get('name') or 
                data.get('title') or 
                data.get('description', '')[:50]
            )
            
            # Tentar extrair IDs adicionais dos dados
            if not entity_info['company_id'] and 'company_id' in data:
                entity_info['company_id'] = data.get('company_id')
            if not entity_info['plan_id'] and 'plan_id' in data:
                entity_info['plan_id'] = data.get('plan_id')
    
    return entity_info


def should_log_route(endpoint: str, entity_type: Optional[str]) -> bool:
    """
    Verifica se a rota deve ser registrada em log
    
    Args:
        endpoint: Nome do endpoint Flask
        entity_type: Tipo da entidade
    
    Returns:
        True se deve registrar log
    """
    # Verificar se está na lista de skip
    if endpoint in AutoLogConfig.SKIP_ENDPOINTS:
        return False
    
    # Se há tipo de entidade, verificar se está habilitado/desabilitado
    if entity_type:
        if AutoLogConfig.DISABLED_ENTITIES and entity_type in AutoLogConfig.DISABLED_ENTITIES:
            return False
        if AutoLogConfig.ENABLED_ENTITIES and entity_type not in AutoLogConfig.ENABLED_ENTITIES:
            return False
    
    return True


def auto_log_crud(
    entity_type: Optional[str] = None,
    get_entity_name: Optional[Callable] = None,
    custom_description: Optional[str] = None
):
    """
    Decorador universal para logging automático de operações CRUD
    
    Args:
        entity_type: Tipo da entidade (opcional, será inferido da URL se não fornecido)
        get_entity_name: Função para extrair o nome da entidade do resultado
        custom_description: Descrição customizada para o log
    
    Exemplo:
        @app.route('/api/company/<int:company_id>/indicators', methods=['POST'])
        @auto_log_crud('indicator')
        def create_indicator(company_id):
            # ... criar indicador
            return jsonify(result)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar se deve registrar log
            endpoint = request.endpoint or ''
            
            # Extrair informações da requisição
            path = request.path
            method = request.method
            
            # Pegar dados da requisição
            request_data = None
            try:
                if request.is_json:
                    request_data = request.get_json(silent=True)
                elif request.form:
                    request_data = request.form.to_dict()
            except:
                pass
            
            # Extrair informações da entidade
            entity_info = extract_entity_info(path, method, request_data)
            
            # Usar entity_type fornecido ou inferido
            final_entity_type = entity_type or entity_info['entity_type']
            
            # Verificar se deve registrar
            if not should_log_route(endpoint, final_entity_type):
                return f(*args, **kwargs)
            
            # Guardar informações antes da execução (para DELETE e UPDATE)
            old_values = None
            if method in ['PUT', 'PATCH', 'DELETE'] and entity_info['entity_id']:
                # Aqui poderíamos buscar os valores antigos do banco
                # Por enquanto, deixaremos None
                pass
            
            # Executar a função original
            try:
                result = f(*args, **kwargs)
                
                # Determinar ação baseada no método HTTP
                action = None
                if method == 'POST':
                    action = 'CREATE'
                elif method in ['PUT', 'PATCH']:
                    action = 'UPDATE'
                elif method == 'DELETE':
                    action = 'DELETE'
                elif method == 'GET':
                    action = 'VIEW'
                
                if action and action != 'VIEW':  # Não logar todas as visualizações
                    # Extrair valores novos do resultado
                    new_values = None
                    if hasattr(result, 'get_json'):
                        try:
                            response_data = result.get_json(silent=True)
                            if isinstance(response_data, dict):
                                new_values = response_data.get('data', response_data)
                        except:
                            pass
                    
                    # Extrair nome da entidade
                    entity_name = entity_info['entity_name']
                    if get_entity_name and new_values:
                        try:
                            entity_name = get_entity_name(new_values)
                        except:
                            pass
                    
                    # Criar descrição
                    description = custom_description
                    if not description:
                        action_pt = {
                            'CREATE': 'Criação',
                            'UPDATE': 'Atualização',
                            'DELETE': 'Exclusão'
                        }.get(action, action)
                        
                        entity_type_pt = final_entity_type or 'entidade'
                        description = f"{action_pt} de {entity_type_pt}"
                        if entity_name:
                            description += f": {entity_name}"
                    
                    # Registrar log
                    try:
                        log_service.create_log(
                            action=action,
                            entity_type=final_entity_type or 'unknown',
                            entity_id=entity_info['entity_id'],
                            entity_name=entity_name,
                            old_values=old_values,
                            new_values=new_values,
                            description=description,
                            company_id=entity_info['company_id'],
                            plan_id=entity_info['plan_id']
                        )
                    except Exception as log_error:
                        # Não deixar erros de log quebrarem a aplicação
                        print(f"Erro ao registrar log: {log_error}")
                
                return result
                
            except Exception as e:
                # Se houver erro, registrar também
                try:
                    log_service.create_log(
                        action='ERROR',
                        entity_type=final_entity_type or 'unknown',
                        entity_id=entity_info['entity_id'],
                        entity_name=entity_info['entity_name'],
                        description=f"Erro em operação: {str(e)[:200]}",
                        company_id=entity_info['company_id'],
                        plan_id=entity_info['plan_id']
                    )
                except:
                    pass
                raise e
        
        return decorated_function
    return decorator


def enable_auto_logging_for_entity(entity_type: str):
    """Habilita logging automático para um tipo de entidade"""
    if entity_type in AutoLogConfig.DISABLED_ENTITIES:
        AutoLogConfig.DISABLED_ENTITIES.remove(entity_type)
    AutoLogConfig.ENABLED_ENTITIES.add(entity_type)


def disable_auto_logging_for_entity(entity_type: str):
    """Desabilita logging automático para um tipo de entidade"""
    AutoLogConfig.DISABLED_ENTITIES.add(entity_type)
    if entity_type in AutoLogConfig.ENABLED_ENTITIES:
        AutoLogConfig.ENABLED_ENTITIES.remove(entity_type)


def get_auto_logging_config() -> Dict[str, Any]:
    """Retorna a configuração atual de auto-logging"""
    return {
        'enabled_entities': list(AutoLogConfig.ENABLED_ENTITIES),
        'disabled_entities': list(AutoLogConfig.DISABLED_ENTITIES),
        'skip_endpoints': AutoLogConfig.SKIP_ENDPOINTS,
        'entity_patterns': list(AutoLogConfig.ENTITY_TYPE_PATTERNS.keys())
    }

