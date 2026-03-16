import uuid
from flask import Blueprint, request, jsonify
from flask_login import login_required
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from agents.graph import board_intelligence
import json

ai_board_bp = Blueprint('ai_board', __name__)
PUBLIC_ERROR_MESSAGE = 'Erro interno do servidor. Tente novamente ou contate o suporte.'

def extract_evidence_data(messages):
    """
    Extrai o conteúdo das ferramentas executadas para fornecer 'provas' ao frontend.
    """
    evidences = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            try:
                # Tenta parsear o conteúdo se for JSON
                content = json.loads(msg.content)
                evidences.append({
                    "tool": msg.name or "database",
                    "content": content
                })
            except:
                evidences.append({
                    "tool": msg.name or "database",
                    "content": msg.content
                })
    return evidences

@ai_board_bp.route('/api/ai/board/start', methods=['POST'])
@login_required
def start_board():
    """
    Inicia uma nova sessão de reunião estratégica com o Conselho AI.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body is required"}), 400

        strategy_goal = data.get('strategy_goal')
        company_context = data.get('company_context', '')
        
        if not strategy_goal:
            return jsonify({"success": False, "error": "strategy_goal is required"}), 400

        # Gera um thread_id único para esta sessão
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        # Prepara o input inicial
        full_input = f"Contexto: {company_context}\n\nObjetivo: {strategy_goal}"
        input_data = {"messages": [HumanMessage(content=full_input)]}
        
        # Executa o grafo até o primeiro checkpoint ou fim
        final_state = None
        for event in board_intelligence.stream(input_data, config=config, stream_mode="values"):
            final_state = event

        # Verifica se parou em um breakpoint (Human Approval)
        snapshot = board_intelligence.get_state(config)
        status = "WAITING_APPROVAL" if snapshot.next else "COMPLETED"
        
        # Formata o histórico de mensagens para o frontend
        messages = []
        raw_messages = final_state.get("messages", []) if final_state else []
        
        for msg in raw_messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                name = getattr(msg, 'name', 'Board')
                messages.append({
                    "role": role,
                    "name": name,
                    "content": msg.content
                })

        return jsonify({
            "success": True,
            "thread_id": thread_id,
            "status": status,
            "messages": messages,
            "evidence_data": extract_evidence_data(raw_messages),
            "current_plan": final_state.get("operational_kpis", []) if final_state else []
        })

    except Exception as e:
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500

@ai_board_bp.route('/api/ai/board/resume', methods=['POST'])
@login_required
def resume_board():
    """
    Retoma a execução do conselho após aprovação ou feedback humano.
    """
    try:
        data = request.get_json()
        thread_id = data.get('thread_id')
        action = data.get('action') # APPROVE ou REJECT
        feedback = data.get('feedback', '')

        if not thread_id or not action:
            return jsonify({"success": False, "error": "thread_id and action are required"}), 400

        config = {"configurable": {"thread_id": thread_id}}
        
        # Injeta a resposta humana
        human_msg = "APROVADO. Prosseguir." if action == "APPROVE" else f"REVISAR: {feedback}"
        
        # Atualiza o estado do grafo no nó de aprovação humana
        board_intelligence.update_state(
            config, 
            {"messages": [HumanMessage(content=human_msg)]},
            as_node="human_approval"
        )
        
        # Retoma a execução
        final_state = None
        for event in board_intelligence.stream(None, config=config, stream_mode="values"):
            final_state = event

        snapshot = board_intelligence.get_state(config)
        status = "WAITING_APPROVAL" if snapshot.next else "COMPLETED"
        
        # Formata o histórico atualizado
        messages = []
        raw_messages = final_state.get("messages", []) if final_state else []
        
        for msg in raw_messages:
            if isinstance(msg, (HumanMessage, AIMessage)):
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                name = getattr(msg, 'name', 'Board')
                messages.append({
                    "role": role,
                    "name": name,
                    "content": msg.content
                })

        return jsonify({
            "success": True,
            "thread_id": thread_id,
            "status": status,
            "messages": messages,
            "evidence_data": extract_evidence_data(raw_messages)
        })

    except Exception as e:
        return jsonify({"success": False, "error": PUBLIC_ERROR_MESSAGE}), 500
