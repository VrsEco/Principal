#!/usr/bin/env python3
import requests

planos_testar = [
    (6, 'evolucao', 'Concepção Empresa de Móveis'),
    (7, 'implantacao', 'Implantação Gas Evolution'),
    (8, 'implantacao', 'Implantação Save Water'),
]

print("="*80)
print("TESTANDO REDIRECIONAMENTOS DE PLANOS")
print("="*80)

for plan_id, tipo_esperado, nome in planos_testar:
    url = f'http://127.0.0.1:5003/plans/{plan_id}'
    
    print(f"\nPlano {plan_id}: {nome}")
    print(f"Tipo esperado: {tipo_esperado}")
    print(f"URL: {url}")
    
    try:
        r = requests.get(url, allow_redirects=False, timeout=10)
        
        print(f"Status: {r.status_code}")
        
        if r.status_code in [301, 302, 303, 307, 308]:
            location = r.headers.get('Location', 'N/A')
            print(f"Redireciona para: {location}")
            
            if tipo_esperado == 'implantacao':
                if f'/pev/implantacao?plan_id={plan_id}' in location:
                    print("✅ CORRETO - Redireciona para implantação")
                else:
                    print(f"❌ ERRO - Deveria redirecionar para /pev/implantacao?plan_id={plan_id}")
            else:
                print(f"❌ ERRO - Plano de evolução não deveria redirecionar")
        else:
            if tipo_esperado == 'evolucao':
                print("✅ CORRETO - Renderiza página (evolução)")
            else:
                print(f"❌ ERRO - Plano de implantação deveria redirecionar")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

print("\n" + "="*80)









