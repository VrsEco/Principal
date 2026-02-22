#!/usr/bin/env python3
import requests

print("\nTestando acesso ao plano 6...")
print("URL: http://127.0.0.1:5003/plans/6\n")

try:
    # Sem seguir redirects
    r = requests.get("http://127.0.0.1:5003/plans/6", allow_redirects=False, timeout=10)

    print(f"Status: {r.status_code}")

    if r.status_code in [301, 302, 303, 307, 308]:
        location = r.headers.get("Location", "N/A")
        print(f"Redirecionamento para: {location}")
    else:
        print("Sem redirecionamento - página renderizada")
        print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")

    # Agora seguindo redirects para ver onde termina
    print("\n---")
    r2 = requests.get("http://127.0.0.1:5003/plans/6", allow_redirects=True, timeout=10)
    print(f"URL final: {r2.url}")
    print(f"Status final: {r2.status_code}")

except Exception as e:
    print(f"Erro: {e}")
