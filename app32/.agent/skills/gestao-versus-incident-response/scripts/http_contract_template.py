from __future__ import annotations

import argparse
import json


def main() -> int:
    parser = argparse.ArgumentParser(description='Gera um template de contrato HTTP para reproduzir bugs.')
    parser.add_argument('--method', default='GET')
    parser.add_argument('--url', required=True)
    parser.add_argument('--query', default='')
    parser.add_argument('--payload', default='{}', help='JSON string do payload')
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
    except Exception:
        payload = args.payload

    result = {
        'method': args.method.upper(),
        'url': args.url,
        'query': args.query,
        'payload': payload,
        'capture_required': [
            'status_http',
            'response_body',
            'response_headers_relevantes',
            'usuario',
            'company_id',
            'horario',
        ],
        'notes': 'Use este template para registrar o request real usado pelo frontend ou para reproduzir manualmente o bug.'
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
