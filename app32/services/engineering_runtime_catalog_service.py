"""Read-only model/list adapter. The RPC transport must be trusted by the caller."""
from datetime import datetime, timezone


def read_codex_catalog(rpc):
    rpc('initialize', {'clientInfo':{'name':'gestao_versus_catalog','version':'1.0.0'}})
    rpc('initialized', {}, notification=True)
    models=[]
    cursor=None
    seen=set()
    for _ in range(10):
        params={'limit':100,'includeHidden':False}
        if cursor is not None:
            params['cursor']=cursor
        page=rpc('model/list',params)
        if not isinstance(page,dict) or not isinstance(page.get('data'),list) or len(page['data'])>100:
            raise ValueError('Invalid catalog page')
        for entry in page['data']:
            if not isinstance(entry,dict):
                raise ValueError('Invalid model')
            name=entry.get('model')
            if not isinstance(name,str) or not name.strip() or len(name)>200 or name in seen:
                raise ValueError('Invalid or duplicate model')
            seen.add(name)
            if entry.get('hidden',False) is not False:
                continue
            efforts=entry.get('supportedReasoningEfforts',[])
            if not isinstance(efforts,list) or len(efforts)>20:
                raise ValueError('Invalid efforts')
            names=[]
            for effort in efforts:
                value=effort.get('reasoningEffort') if isinstance(effort,dict) else None
                if not isinstance(value,str) or not value or len(value)>40:
                    raise ValueError('Invalid effort')
                names.append(value)
            models.append({'model':name,'supported_efforts':names})
        cursor=page.get('nextCursor')
        if cursor is None:
            return {'source':'codex_app_server_model_list','observed_at':datetime.now(timezone.utc).isoformat(),
                    'models':models,'automatic_switch':False,'generation_access_verified':False}
        if not isinstance(cursor,str) or not cursor or len(cursor)>2000:
            raise ValueError('Invalid cursor')
    raise ValueError('Catalog pagination limit exceeded')
