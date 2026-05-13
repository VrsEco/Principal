from __future__ import annotations

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.deploy.configr_remote_helper import APP_DIR, connect_ssh


REMOTE_WORKER = r"""
import asyncio
import json
import os
import sys

import requests
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

try:
    from dotenv import load_dotenv
    load_dotenv('/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/www/app32/.env')
except Exception:
    pass

PUBLIC_BASE = os.environ.get('APP32_MCP_PUBLIC_BASE_URL', 'https://app.gestaoversus.com.br').rstrip('/')

token = os.environ.get('APP32_MCP_HTTP_TOKEN')
if not token:
    raw = os.environ.get('APP32_MCP_HTTP_TOKENS_JSON', '').strip()
    if raw:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed:
            token = next(iter(parsed.keys()))

if not token:
    raise RuntimeError('Nenhum token MCP HTTP encontrado no ambiente remoto.')

health = requests.get(f'{PUBLIC_BASE}/mcp/healthz', timeout=20)
unauth = requests.get(f'{PUBLIC_BASE}/mcp/user', timeout=20)

async def _run():
    headers = {'Authorization': f'Bearer {token}'}
    async with streamablehttp_client(f'{PUBLIC_BASE}/mcp/user', headers=headers) as transport:
        if len(transport) == 3:
            read, write, _ = transport
        else:
            read, write = transport
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            if 'describe_app32_implantation_persona_profile_tool' not in tool_names:
                raise RuntimeError('Tool de persona não encontrada na surface user.')
            described = await session.call_tool('describe_app32_implantation_persona_profile_tool', arguments={})
            return {
                'tool_count': len(tool_names),
                'tool_names': tool_names,
                'describe_result': [getattr(item, 'text', None) or getattr(item, 'data', None) for item in described.content],
            }

result = asyncio.run(_run())
print(json.dumps({
    'health_status': health.status_code,
    'health_body': health.json(),
    'unauth_status': unauth.status_code,
    'tool_validation': result,
}, ensure_ascii=False, indent=2))
"""


def main() -> int:
    ssh = connect_ssh()
    try:
        remote_file = f"{APP_DIR}/tmp_sapiens_mcp_prod_smoke.py"
        payload = base64.b64encode(REMOTE_WORKER.encode("utf-8")).decode("ascii")
        ssh.exec_command(f"echo {payload} | base64 -d > {remote_file}")
        command = (
            f"cd {APP_DIR} && "
            "/srv/appgestaoversuscombr.45a4cd4b.configr.cloud/.virtualenv/3.12/bin/python "
            f"{remote_file}"
        )
        stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
        output = stdout.read().decode("utf-8", "ignore")
        error = stderr.read().decode("utf-8", "ignore")
        code = stdout.channel.recv_exit_status()
        if output:
            print(output)
        if error:
            print(error)
        ssh.exec_command(f"rm -f {remote_file}")
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
