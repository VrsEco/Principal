import asyncio, json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

BASE = 'https://app.gestaoversus.com.br/mcp/user/'
TOKEN = 'mcpu_lWsy5v5CbjfVaJmSAYw7fYpTus4q_WnOqFnWCArLdac'

CALLS = [
    ('bootstrap_session_context', {}),
    ('resolve_app32_instruction_bundle_tool', {'runtime_profile': 'squad_cliente'}),
    ('describe_app32_squad_runtime_tool', {'runtime_profile': 'squad_cliente'}),
    ('list_user_app32_capabilities', {}),
    ('describe_app32_profile_contracts_tool', {'runtime_profile': 'squad_cliente'}),
    ('describe_app32_surface_playbooks_tool', {'surface': 'user'}),
    ('describe_app32_domain_playbooks_tool', {}),
    ('describe_app32_release_checklist_tool', {}),
    ('describe_app32_tool_freeze_procedure_tool', {}),
    ('describe_app32_external_ai_onboarding_tool', {'surface': 'user'}),
]


def unpack(result):
    items = []
    for item in result.content:
        data = getattr(item, 'data', None)
        text = getattr(item, 'text', None)
        if data is not None:
            items.append(data)
            continue
        if isinstance(text, str):
            t = text.strip()
            if t.startswith('{') or t.startswith('['):
                try:
                    items.append(json.loads(t))
                    continue
                except Exception:
                    pass
            items.append(t)
    if len(items) == 1:
        return items[0]
    return items

async def main():
    headers = {'Authorization': f'Bearer {TOKEN}'}
    summary = {}
    async with streamablehttp_client(BASE, headers=headers) as transport:
        if len(transport) == 3:
            read, write, _ = transport
        else:
            read, write = transport
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name, args in CALLS:
                result = await session.call_tool(name, arguments=args)
                summary[name] = unpack(result)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

asyncio.run(main())
