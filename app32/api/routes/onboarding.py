from flask import Blueprint, jsonify, session
from flask_login import login_required, current_user
from models.company import Company

onboarding_bp = Blueprint('onboarding', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'

@onboarding_bp.route('/api/onboarding/status', methods=['GET'])
@login_required
def get_onboarding_status():
    """
    Verifica se os campos críticos da empresa estão preenchidos.
    """
    try:
        # Pega a empresa ativa da sessão
        company_id = session.get('active_company_id')
        if not company_id:
            return jsonify({"success": False, "error": "Nenhuma empresa selecionada"}), 400
            
        company = Company.query.get(company_id)
        if not company:
            return jsonify({"success": False, "error": "Empresa não encontrada"}), 404
            
        missing_fields = []
        if not company.mission: missing_fields.append("mission")
        if not company.vision: missing_fields.append("vision")
        if not company.segment: missing_fields.append("segment")
        
        status = "INCOMPLETE" if missing_fields else "COMPLETE"
        
        return jsonify({
            "success": True,
            "status": status,
            "missing_fields": missing_fields,
            "company_id": company.id,
            "company_name": company.name
        })

    except Exception as e:
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500
