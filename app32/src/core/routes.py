from flask import Blueprint, render_template, request, jsonify
import logging

logger = logging.getLogger(__name__)

# Criação do Blueprint para as rotas do núcleo (Core/Body)
core_bp = Blueprint('core', __name__, template_folder='../templates')

@core_bp.route('/chat', methods=['GET'])
def chat_view():
    """
    Renderiza a interface web do chat.
    """
    return render_template('chat.html')

@core_bp.route('/api/v2/chat', methods=['POST'])
def chat_api():
    """
    Endpoint principal para interagir com o cérebro (LangGraph).
    """
    from src.intelligence.graphs.main_graph import run_agent_interaction
    
    data = request.json
    message = data.get("message")
    thread_id = data.get("thread_id", "default_user")

    if not message:
        return jsonify({"error": "Mensagem é obrigatória"}), 400

    try:
        logger.info(f"Interface Web enviando para thread {thread_id}: {message}")
        result = run_agent_interaction(message, thread_id)
        
        # Extrai a última mensagem da resposta
        last_message = result["messages"][-1]
        
        return jsonify({
            "status": "success",
            "response": last_message.content,
            "thread_id": thread_id
        })
    except Exception as e:
        logger.error(f"Erro no chat via API: {e}")
        return jsonify({"error": str(e)}), 500
