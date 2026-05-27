import asyncio, json
import requests
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = 'https://app.gestaoversus.com.br'
TOKEN = 'mcpu_lWsy5v5CbjfVaJmSAYw7fYpTus4q_WnOqFnWCArLdac'
WANTED = [
    'bootstrap_session_context',
    'resolve_app32_instruction_bundle_tool',
    'describe_app32_squad_runtime_tool',
    'list_user_app32_capabilities',
    'describe_app32_profile_contracts_tool',
    'describe_app32_surface_playbooks_tool',
    'describe_app32_domain_playbooks_tool',
    'describe_app32_release_checklist_tool',
    'describe_app32_tool_freeze_procedure_tool',
    'describe_app32_external_ai_onboarding_tool',
]

async def main():
    health = requests.get(BASE + '/mcp/healthz', timeout=20)
    print(json.dumps({'health_status': health.status_code, 'health_ok': health.ok}, ensure_ascii=False))
    headers = {'Authorization': f'Bearer {TOKEN}'}
    async with streamablehttp_client(BASE + '/mcp/user/', headers=headers) as transport:
        if len(transport) == 3:
            read, write, _ = transport
        else:
            read, write = transport
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print(json.dumps({'tool_count': len(names), 'has_all': all(x in names for x in WANTED), 'missing': [x for x in WANTED if x not in names]}, ensure_ascii=False))

asyncio.run(main())
