"""Status-only MCP adapters; registered through existing APP32 policy wrappers."""
from typing import Any
from pydantic import StrictInt, StrictBool, StrictStr

STATUS_TOOL_NAMES = (
    'get_whatsapp_status_setup', 'configure_whatsapp_status_account', 'register_whatsapp_status_approved_bundle',
    'list_whatsapp_status_arts', 'verify_whatsapp_status_account',
    'publish_whatsapp_status_art', 'publish_whatsapp_status_kit', 'publish_whatsapp_status_test',
    'create_whatsapp_status_schedule', 'update_whatsapp_status_schedule',
    'list_whatsapp_status_schedules', 'pause_whatsapp_status_schedule',
    'resume_whatsapp_status_schedule', 'list_whatsapp_status_results', 'confirm_whatsapp_status_mobile',
)


def _actor(company_id):
    from src.core.mcp_http_auth import get_http_request_identity
    from src.intelligence.tool_context import get_sapiens_context
    identity = get_http_request_identity()
    context = get_sapiens_context()
    if (identity is None or identity.subject_type != 'USER' or not identity.principal_id
        or context.company_id != company_id or not context.user_id):
        raise PermissionError('status_authenticated_human_required')
    return company_id, context.user_id, identity.principal_id


def register_whatsapp_status_tools(mcp: Any):
    from services import whatsapp_status_service as service

    @mcp.tool()
    def get_whatsapp_status_setup(company_id: StrictInt) -> dict:
        """Inspeciona referências de integração/solicitações existentes, sem tokens ou conteúdo de conversas."""
        return service.inspect_setup(*_actor(company_id))

    @mcp.tool()
    def configure_whatsapp_status_account(company_id: StrictInt, integration_id: StrictStr, expected_phone: StrictStr, allow_global: StrictBool = False) -> dict:
        """Vincula explicitamente integração EXISTENTE; não altera tokens, instância ou dispositivos."""
        return service.bind_existing_account(*_actor(company_id), integration_id, expected_phone, allow_global=allow_global)

    @mcp.tool()
    def register_whatsapp_status_approved_bundle(company_id: StrictInt, bundle_code: StrictStr = 'versus_20261007') -> dict:
        """Importa somente o manifesto fixo aprovado de 12 artes; sem paths/URLs livres do cliente."""
        return service.register_approved_bundle(*_actor(company_id), bundle_code)

    @mcp.tool()
    def list_whatsapp_status_arts(company_id: StrictInt) -> dict:
        """Lista kits/versionamentos e artes aprovadas sem URLs, arquivos ou credenciais."""
        return service.list_arts(*_actor(company_id))

    @mcp.tool()
    def verify_whatsapp_status_account(company_id: StrictInt) -> dict:
        """Confere somente o número do dispositivo vinculado, sem alterar a instância."""
        return service.verify_account(*_actor(company_id))

    @mcp.tool()
    def publish_whatsapp_status_art(company_id: StrictInt, art_id: StrictInt, command_key: StrictStr) -> dict:
        """Publica arte aprovada por ID, após gate humano e teste no celular; nunca URL livre."""
        return service.publish(*_actor(company_id), [art_id], command_key)

    @mcp.tool()
    def publish_whatsapp_status_test(company_id: StrictInt, art_id: StrictInt, command_key: StrictStr) -> dict:
        """Publicação REAL única para homologação; exige gate humano e conta verificada."""
        return service.publish(*_actor(company_id), [art_id], command_key, test=True)

    @mcp.tool()
    def publish_whatsapp_status_kit(company_id: StrictInt, kit_code: StrictStr, version: StrictInt, command_key: StrictStr) -> dict:
        """Publica kit aprovado em ordem; para na primeira falha/incerteza, sem reenvio."""
        return service.publish_kit(*_actor(company_id), kit_code, version, command_key)

    @mcp.tool()
    def create_whatsapp_status_schedule(company_id: StrictInt, plan: dict) -> dict:
        """Cria agenda DESATIVADA. plan: name, hour, minute, timezone, weekly_arts 0..6."""
        return service.save_schedule(*_actor(company_id), plan)

    @mcp.tool()
    def update_whatsapp_status_schedule(company_id: StrictInt, schedule_id: StrictInt, plan: dict) -> dict:
        """Edita agenda, sempre pausando. Apenas IDs aprovados; não recebe código/URL."""
        return service.save_schedule(*_actor(company_id), plan, schedule_id)

    @mcp.tool()
    def list_whatsapp_status_schedules(company_id: StrictInt) -> dict:
        """Consulta agendas, revisão mensal e resultado da última ocorrência."""
        return service.list_schedules(*_actor(company_id))

    @mcp.tool()
    def pause_whatsapp_status_schedule(company_id: StrictInt, schedule_id: StrictInt) -> dict:
        """Pausa imediatamente os próximos itens; uma chamada já em voo não pode ser desfeita."""
        return service.set_schedule_active(*_actor(company_id), schedule_id, False)

    @mcp.tool()
    def resume_whatsapp_status_schedule(company_id: StrictInt, schedule_id: StrictInt, reviewed: StrictBool = False) -> dict:
        """Retoma com gate humano, conta homologada e permissões vigentes; revisão opcional."""
        return service.set_schedule_active(*_actor(company_id), schedule_id, True, reviewed=reviewed)

    @mcp.tool()
    def list_whatsapp_status_results(company_id: StrictInt, limit: StrictInt = 30) -> dict:
        """Distingue aceite Z-API, falha, incerteza e conferência no celular."""
        return service.list_results(*_actor(company_id), limit)

    @mcp.tool()
    def confirm_whatsapp_status_mobile(company_id: StrictInt, publication_id: StrictInt) -> dict:
        """Registra conferência HUMANA no celular de publicação aceita pelo fornecedor."""
        return service.confirm_mobile(*_actor(company_id), publication_id)
