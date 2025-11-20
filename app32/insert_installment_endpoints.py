#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Script para inserir endpoints de parcelas no arquivo modules/pev/__init__.py"""

endpoints_code = '''

@pev_bp.route('/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments', methods=['DELETE'])
def delete_structure_installments(plan_id: int, structure_id: int):
    """Delete all installments for a structure"""
    try:
        from config_database import get_db
        db = get_db()
        
        # Verificar se estrutura existe
        structures = db.list_plan_structures(plan_id)
        structure = next((s for s in structures if s.get('id') == structure_id), None)
        
        if not structure:
            return jsonify({'success': False, 'error': 'Estrutura não encontrada'}), 404
        
        # Deletar parcelas
        db.delete_plan_structure_installments(structure_id)
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print(f"Error deleting installments: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@pev_bp.route('/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments', methods=['POST'])
def create_structure_installment(plan_id: int, structure_id: int):
    """Create a new installment for a structure"""
    try:
        data = request.get_json() or {}
        
        from config_database import get_db
        db = get_db()
        
        # Verificar se estrutura existe
        structures = db.list_plan_structures(plan_id)
        structure = next((s for s in structures if s.get('id') == structure_id), None)
        
        if not structure:
            return jsonify({'success': False, 'error': 'Estrutura não encontrada'}), 404
        
        # Validar campos obrigatórios
        if not data.get('installment_number'):
            return jsonify({'success': False, 'error': 'Número da parcela é obrigatório'}), 400
        if not data.get('amount'):
            return jsonify({'success': False, 'error': 'Valor da parcela é obrigatório'}), 400
        
        # Criar parcela
        installment_id = db.create_plan_structure_installment(structure_id, data)
        
        if installment_id:
            return jsonify({'success': True, 'id': installment_id}), 201
        else:
            return jsonify({'success': False, 'error': 'Erro ao criar parcela'}), 500
        
    except Exception as e:
        print(f"Error creating installment: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


'''

# Ler arquivo
with open("modules/pev/__init__.py", "r", encoding="utf-8") as f:
    content = f.read()

# Encontrar posição de inserção
marker = "# APIs de Capacidade de Faturamento"
idx = content.find(marker)

if idx == -1:
    print("ERRO: Marcador não encontrado!")
    exit(1)

# Inserir código
new_content = content[:idx] + endpoints_code + "\n" + content[idx:]

# Escrever arquivo
with open("modules/pev/__init__.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("✅ Endpoints de parcelas inseridos com sucesso!")
