"""Identity/grant lookup doubles; real service authorization and MCP capability policy."""
import asyncio
import sys
from types import SimpleNamespace
import pytest
from services.whatsapp_status_service import authorize
from src.core.mcp_whatsapp_status_tools import STATUS_TOOL_NAMES, _actor
from src.intelligence.tooling.capabilities import infer_tool_capability, infer_tool_action
from src.intelligence.security.tool_policy import ToolPolicyRequest, evaluate_tool_policy

def _run_async(coro):
    """Run in a private thread/loop so a loop leaked by other tests cannot interfere."""
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setitem(sys.modules,'models',SimpleNamespace(db=SimpleNamespace(session=SimpleNamespace(expire_all=lambda:None))))
    state=SimpleNamespace(user=SimpleNamespace(is_active=True),principal=SimpleNamespace(is_active=True),
        grant=SimpleNamespace(is_active=True,mcp_permissions=['whatsapp_status.read','whatsapp_status.publish']),
        runtime={'role':'administrador','accessible_company_ids':[1],'has_full_app32_permissions':True})
    def query(kind):
        return SimpleNamespace(filter_by=lambda **kw:SimpleNamespace(first=lambda:getattr(state,kind)))
    monkeypatch.setitem(sys.modules,'models.user',SimpleNamespace(User=SimpleNamespace(query=query('user'))))
    monkeypatch.setitem(sys.modules,'models.identity_principal',SimpleNamespace(
        IdentityPrincipal=SimpleNamespace(query=query('principal')),PrincipalCompanyGrant=SimpleNamespace(query=query('grant'))))
    monkeypatch.setitem(sys.modules, 'src.intelligence.security.runtime_identity',
        SimpleNamespace(resolve_runtime_identity=lambda **kw:state.runtime))
    return state


def test_current_permission_and_tenant_intersection(auth):
    authorize(1,1,1,'whatsapp_status.publish')
    with pytest.raises(PermissionError): authorize(2,1,1,'whatsapp_status.publish')
    with pytest.raises(PermissionError): authorize(1,1,1,'whatsapp_status.schedule')
    auth.runtime['role']='cliente'
    with pytest.raises(PermissionError): authorize(1,1,1,'whatsapp_status.publish')


@pytest.mark.parametrize('ceiling',[[],['*'],['whatsapp_status'],['whatsapp_status.publish','contacts.read'],True,{},[False],['whatsapp_status.*']])
def test_no_broad_or_malformed_grant(auth,ceiling):
    auth.grant.mcp_permissions=ceiling
    with pytest.raises(PermissionError): authorize(1,1,1,'whatsapp_status.publish')


@pytest.mark.parametrize('kind',['user','principal','grant'])
def test_revocation_is_immediate(auth,kind):
    getattr(auth,kind).is_active=False
    with pytest.raises(PermissionError): authorize(1,1,1,'whatsapp_status.publish')


def test_identity_never_comes_from_payload(monkeypatch):
    monkeypatch.setattr('src.core.mcp_http_auth.get_http_request_identity',lambda:None)
    with pytest.raises(PermissionError): _actor(1)
    monkeypatch.setattr('src.core.mcp_http_auth.get_http_request_identity',lambda:SimpleNamespace(subject_type='AGENT',principal_id=1))
    with pytest.raises(PermissionError): _actor(1)


def test_all_capabilities_are_status_only_and_mutation_classified():
    for name in STATUS_TOOL_NAMES:
        cap=infer_tool_capability(SimpleNamespace(name=name,description='Status'))
        assert cap.domain=='whatsapp_status' and cap.scopes==('mcp_admin',)
        assert len(cap.permissions)==1 and cap.permissions[0].startswith('whatsapp_status.')
        if name.startswith(('publish_','resume_','confirm_','register_','configure_')):
            assert cap.human_gate and cap.risk.value=='high'
            assert infer_tool_action(name,cap.domain) in ('create','update')


def test_publication_requires_persisted_gate_and_rejects_other_surfaces():
    cap=infer_tool_capability(SimpleNamespace(name='publish_whatsapp_status_art',description='Status'))
    principal={'user_id':1,'company_id':1,'role':'administrador','permissions':{'*'},'accessible_company_ids':[1]}
    req=ToolPolicyRequest(tool_name=cap.name,surface='admin',domain=cap.domain,action='update',risk='high',
        requested_company_id=1,accessible_company_ids=(1,),required_permissions=cap.permissions)
    assert not evaluate_tool_policy(principal,req).allowed
    from dataclasses import replace
    assert evaluate_tool_policy(principal,replace(req,confirmed_mutation=True)).allowed
    assert not evaluate_tool_policy(principal,replace(req,surface='analytics',confirmed_mutation=True)).allowed


def test_status_discovery_requires_admin_scope_and_exact_permission(monkeypatch):
    import src.core.mcp_surface_registry as registry
    monkeypatch.setattr(registry,'_has_authenticated_mcp_permission',lambda p:p.startswith('whatsapp_status.'))
    monkeypatch.setattr('src.core.mcp_http_auth.get_http_request_identity',lambda:SimpleNamespace(scopes=('mcp:access','mcp:user','mcp:analytics','mcp:finance')))
    assert not set(STATUS_TOOL_NAMES).intersection(registry._visible_privileged_tool_names(frozenset(STATUS_TOOL_NAMES)))
    monkeypatch.setattr('src.core.mcp_http_auth.get_http_request_identity',lambda:SimpleNamespace(scopes=('mcp:access','mcp:admin')))
    server=registry.build_oauth_unified_mcp_server()
    tools=_run_async(server.list_tools())
    assert set(STATUS_TOOL_NAMES).issubset({t.name for t in tools})
    # No MCP tool can accept an arbitrary media URL/path, token or instance ID.
    for tool in tools:
        if tool.name in STATUS_TOOL_NAMES:
            assert not {'url','image','media_url','path','token','api_key','instance_id'}.intersection(tool.inputSchema.get('properties',{}))


@pytest.mark.parametrize('field,value',[('company_id',True),('company_id','1'),('art_id',True),('command_key',123)])
def test_actual_mcp_input_model_rejects_scalar_coercion(field,value):
    import src.core.mcp_surface_registry as registry
    server=registry.build_oauth_unified_mcp_server()
    tool=server._tool_manager.get_tool('publish_whatsapp_status_art')
    data={'company_id':1,'art_id':1,'command_key':'command:one'}; data[field]=value
    with pytest.raises(ValueError): tool.fn_metadata.arg_model.model_validate(data)
