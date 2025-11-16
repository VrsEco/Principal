"""
TC011: Gerenciamento de Parcelas de Estruturas Operacionais
Testa o fluxo completo de criação, edição e salvamento de parcelas
"""

import pytest
import requests
from test_helpers import get_authenticated_session, create_test_company, create_test_plan

BASE_URL = "http://localhost:5004"
TIMEOUT = 30


def test_structure_installments_management():
    """Testa o fluxo completo de gerenciamento de parcelas de estruturas"""
    
    # 1. Autenticar
    session = get_authenticated_session()
    assert session is not None, "Falha na autenticação"
    
    # 2. Criar empresa e plano
    company_id = create_test_company(session, "Test Company Installments", "TSTINST")
    assert company_id is not None, "Falha ao criar empresa"
    
    plan_id = create_test_plan(session, company_id, "Test Plan Installments", "2025-01-01", "2025-12-31")
    assert plan_id is not None, "Falha ao criar plano"
    
    # 3. Criar estrutura operacional
    structure_url = f"{BASE_URL}/pev/api/implantacao/{plan_id}/structures"
    structure_data = {
        "area": "operacional",
        "block": "instalacoes",
        "item_type": "Aquisição",
        "description": "Teste de Estrutura para Parcelas",
        "value": "R$ 10.000,00",
        "repetition": "Mensal",
        "payment_form": "Conforme parcelas",
        "acquisition_info": "Janeiro/2025",
        "supplier": "Fornecedor Teste",
        "availability_info": "Imediato",
        "status": "pending"
    }
    
    response = session.post(structure_url, json=structure_data, timeout=TIMEOUT)
    assert response.status_code in [200, 201], f"Falha ao criar estrutura: {response.status_code} - {response.text}"
    
    result = response.json()
    assert result.get('success'), f"Erro ao criar estrutura: {result.get('error')}"
    structure_id = result.get('id')
    assert structure_id is not None, "ID da estrutura não retornado"
    
    print(f"✅ Estrutura criada com ID: {structure_id}")
    
    # 4. Testar DELETE de parcelas (deve funcionar mesmo sem parcelas)
    delete_installments_url = f"{BASE_URL}/pev/api/implantacao/{plan_id}/structures/{structure_id}/installments"
    delete_response = session.delete(delete_installments_url, timeout=TIMEOUT)
    
    # Deve aceitar 200 (sucesso) ou 404 (se endpoint não existir)
    if delete_response.status_code == 404:
        pytest.fail(f"❌ Endpoint DELETE /installments não existe! Status: {delete_response.status_code}")
    
    assert delete_response.status_code == 200, f"Falha ao deletar parcelas: {delete_response.status_code} - {delete_response.text}"
    delete_result = delete_response.json()
    assert delete_result.get('success'), f"Erro ao deletar parcelas: {delete_result.get('error')}"
    
    print(f"✅ DELETE de parcelas funcionou")
    
    # 5. Criar parcelas individualmente
    installments = [
        {
            "installment_number": "1/3",
            "amount": "R$ 3.333,33",
            "due_info": "15/01/2025",
            "classification": "Mensalidade",
            "repetition": "Mensal",
            "installment_type": "Mensalidade"
        },
        {
            "installment_number": "2/3",
            "amount": "R$ 3.333,33",
            "due_info": "15/02/2025",
            "classification": "Mensalidade",
            "repetition": "Mensal",
            "installment_type": "Mensalidade"
        },
        {
            "installment_number": "3/3",
            "amount": "R$ 3.333,34",
            "due_info": "15/03/2025",
            "classification": "Mensalidade",
            "repetition": "Mensal",
            "installment_type": "Mensalidade"
        }
    ]
    
    created_installment_ids = []
    for inst in installments:
        create_inst_url = f"{BASE_URL}/pev/api/implantacao/{plan_id}/structures/{structure_id}/installments"
        create_response = session.post(create_inst_url, json=inst, timeout=TIMEOUT)
        
        if create_response.status_code == 404:
            pytest.fail(f"❌ Endpoint POST /installments não existe! Status: {create_response.status_code}")
        
        assert create_response.status_code in [200, 201], f"Falha ao criar parcela: {create_response.status_code} - {create_response.text}"
        create_result = create_response.json()
        assert create_result.get('success'), f"Erro ao criar parcela: {create_result.get('error')}"
        
        inst_id = create_result.get('id')
        if inst_id:
            created_installment_ids.append(inst_id)
            print(f"✅ Parcela criada com ID: {inst_id}")
    
    assert len(created_installment_ids) == len(installments), f"Esperado {len(installments)} parcelas, criadas {len(created_installment_ids)}"
    
    # 6. Verificar se parcelas foram salvas (buscar estrutura completa)
    get_structure_url = f"{BASE_URL}/pev/api/implantacao/{plan_id}/structures/{structure_id}"
    get_response = session.get(get_structure_url, timeout=TIMEOUT)
    assert get_response.status_code == 200, f"Falha ao buscar estrutura: {get_response.status_code}"
    
    structure_result = get_response.json()
    assert structure_result.get('success'), f"Erro ao buscar estrutura: {structure_result.get('error')}"
    
    structure_data = structure_result.get('data', {})
    saved_installments = structure_data.get('installments', [])
    assert len(saved_installments) == len(installments), f"Esperado {len(installments)} parcelas salvas, encontradas {len(saved_installments)}"
    
    print(f"✅ Todas as {len(saved_installments)} parcelas foram salvas corretamente")
    
    # 7. Testar edição: deletar todas e criar novas
    delete_response = session.delete(delete_installments_url, timeout=TIMEOUT)
    assert delete_response.status_code == 200, f"Falha ao deletar parcelas na edição: {delete_response.status_code}"
    
    # Criar novas parcelas editadas
    edited_installments = [
        {
            "installment_number": "1/2",
            "amount": "R$ 5.000,00",
            "due_info": "15/01/2025",
            "classification": "Mensalidade",
            "repetition": "Mensal",
            "installment_type": "Mensalidade"
        },
        {
            "installment_number": "2/2",
            "amount": "R$ 5.000,00",
            "due_info": "15/02/2025",
            "classification": "Mensalidade",
            "repetition": "Mensal",
            "installment_type": "Mensalidade"
        }
    ]
    
    for inst in edited_installments:
        create_response = session.post(create_inst_url, json=inst, timeout=TIMEOUT)
        assert create_response.status_code in [200, 201], f"Falha ao criar parcela editada: {create_response.status_code}"
        assert create_response.json().get('success'), "Erro ao criar parcela editada"
    
    # Verificar parcelas editadas
    get_response = session.get(get_structure_url, timeout=TIMEOUT)
    structure_result = get_response.json()
    saved_installments = structure_result.get('data', {}).get('installments', [])
    assert len(saved_installments) == len(edited_installments), f"Esperado {len(edited_installments)} parcelas após edição, encontradas {len(saved_installments)}"
    
    print(f"✅ Edição de parcelas funcionou corretamente - {len(saved_installments)} parcelas salvas")
    
    print("\n✅ Teste completo: Gerenciamento de parcelas funcionando!")


if __name__ == "__main__":
    test_structure_installments_management()

