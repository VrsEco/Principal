from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.cadastro_agent_service import CadastroAgentService
from langchain_core.messages import HumanMessage, AIMessage

agents_bp = Blueprint('agents', __name__)
cadastro_service = CadastroAgentService()

@agents_bp.route('/sapiens')
@login_required
def sapiens_page():
    """Interface unificada estilo WhatsApp para todos os agentes de IA"""
    return render_template('sapiens.html')

@agents_bp.route('/agents/board')
@login_required
def ai_board():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', contact='sapiens'))

@agents_bp.route('/agents/logs')
@login_required
def get_agent_logs_page():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', view='logs'))

@agents_bp.route('/agents/engineering')
@login_required
def get_engineering_board():
    from flask import redirect, url_for
    return redirect(url_for('agents.sapiens_page', contact='engineering'))

@agents_bp.route('/api/agents/chat', methods=['POST'])
@login_required
def agents_chat():
    from models import db, AgentMessage
    from src.intelligence.work_agents.graph import work_agent_graph
    from flask import session
    
    data = request.get_json()
    message = data.get('message')
    history = data.get('history', [])
    contact = data.get('contact', 'sapiens') # 'sapiens' ou 'engineering'
    
    company_id = session.get('active_company_id')
    
    # Define o prefixo se for engenharia
    processed_message = message
    agent_type = 'work_agent_squad'
    
    if contact == 'engineering' and '[CANAL ENGENHARIA]' not in message:
        processed_message = f"[CANAL ENGENHARIA] {message}"
        agent_type = 'engineering_squad'

    # 1. Salva a mensagem do usuário (Inbound)
    thread_id = f"user_{current_user.id}_{contact}"
    user_msg = AgentMessage(
        company_id=company_id,
        user_id=current_user.id,
        agent_type=agent_type,
        agent_name='Usuário',
        direction='inbound',
        content=message,
        channel='platform',
        metadata_json={
            "contact": contact,
            "thread_id": thread_id
        }
    )
    db.session.add(user_msg)
    
    # Prepara as mensagens para o LangGraph
    messages = []
    for msg in history:
        role = msg.get('role') or msg.get('type')
        content = msg.get('content') or msg.get('message')
        
        if role in ['user', 'human']:
            messages.append(HumanMessage(content=content))
        elif role in ['assistant', 'ai']:
            messages.append(AIMessage(content=content))
    
    messages.append(HumanMessage(content=processed_message))
    
    try:
        from src.intelligence.memory import get_checkpointer
        from src.intelligence.work_agents.graph import create_work_agent_workflow
        
        # 2. Configura a Memória Persistente (SQL) via Thread ID
        config = {"configurable": {"thread_id": thread_id}}

        with get_checkpointer() as checkpointer:
            graph = create_work_agent_workflow(checkpointer=checkpointer)
            
            # Verifica se já existe um estado no banco para esta thread
            state = graph.get_state(config)
            
            if not state.values or not state.values.get("messages"):
                # Se o banco está vazio, enviamos Historico + Nova para inicializar
                graph_input_messages = messages
                print(f"--- CHAT: Inicializando nova thread SQL para {thread_id} ---")
            else:
                # Se já tem mensagens no DB, enviamos APENAS a nova (evita duplicação)
                graph_input_messages = [HumanMessage(content=processed_message)]
                print(f"--- CHAT: Retomando thread SQL {thread_id} (Histórico no DB) ---")

            inputs = {
                "messages": graph_input_messages,
                "user_id": current_user.id,
                "company_id": company_id,
                "next_node": None
            }
            
            # Invoca o grafo com persistência SQL
            result = graph.invoke(inputs, config=config)
            messages_result = result["messages"]
            
            if messages_result[-1].type == "ai":
                final_text = messages_result[-1].content
            else:
                final_text = "Estou aqui! Planejei os próximos passos, mas não identifiquei uma tarefa específica. Como posso ser útil?"
            
            agent_executor = result.get("next_node", "end")
            
            # 3. Salva a resposta da IA no log de mensagens (Visual apenas)
            ai_msg = AgentMessage(
                company_id=company_id,
                user_id=current_user.id,
                agent_type=agent_type,
                agent_name=agent_executor,
                direction='outbound',
                content=final_text,
                channel='platform',
                metadata_json={
                    "agent": agent_executor, 
                    "contact": contact,
                    "thread_id": thread_id
                }
            )
            db.session.add(ai_msg)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "response": final_text,
                "agent": agent_executor
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@agents_bp.route('/api/agents/actions/pending', methods=['GET'])
@login_required
def get_pending_actions():
    from models.agent_action import AgentAction
    from flask import session
    
    company_id = session.get('active_company_id')
    actions = AgentAction.query.filter_by(
        company_id=company_id, 
        status='pending'
    ).all()
    
    return jsonify({
        "success": True,
        "actions": [a.to_dict() for a in actions]
    })

@agents_bp.route('/api/agents/history', methods=['GET'])
@login_required
def get_chat_history():
    from models import AgentMessage
    from flask import session
    
    company_id = session.get('active_company_id')
    contact = request.args.get('contact', 'sapiens')
    target_user_id = request.args.get('user_id')
    
    # Se não for especificado user_id, usa o atual
    # Se for admin, pode ver de outros, senão, apenas o seu
    if not target_user_id or current_user.role != 'admin':
        target_user_id = current_user.id
    
    agent_type = 'work_agent_squad'
    if contact == 'engineering':
        agent_type = 'engineering_squad'
        from sqlalchemy import or_
        messages = AgentMessage.query.filter(
            AgentMessage.company_id == company_id,
            AgentMessage.user_id == target_user_id,
            or_(
                AgentMessage.agent_type == 'engineering_squad',
                AgentMessage.content.contains('[CANAL ENGENHARIA]')
            )
        ).order_by(AgentMessage.created_at.asc()).limit(100).all()
    else:
        # Padrão: Sapiens ou um usuário específico
        filters = [
            AgentMessage.company_id == company_id,
            AgentMessage.user_id == target_user_id,
            ~AgentMessage.content.contains('[CANAL ENGENHARIA]')
        ]
        
        # Se o "contact" for um ID numérico, estamos vendo a conversa de um usuário específico com o Sapiens
        # Nesse caso, o agent_type deve ser o padrão do Sapiens
        messages = AgentMessage.query.filter(*filters).order_by(AgentMessage.created_at.asc()).limit(100).all()
    
    return jsonify({
        "success": True,
        "history": [m.to_dict() for m in messages]
    })

@agents_bp.route('/api/agents/contacts', methods=['GET'])
@login_required
def get_agents_contacts():
    from models import db, AgentMessage, User
    from flask import session
    from sqlalchemy import func
    
    company_id = session.get('active_company_id')
    
    # 1. Contatos Fixos (Bots)
    contacts = [
        {
            "id": "sapiens",
            "name": "Sapiens",
            "avatar": "🧭",
            "status": "online",
            "description": "Líder Supervisor & Especialistas",
            "type": "bot"
        },
        {
            "id": "engineering",
            "name": "Squad Engenharia",
            "avatar": "🛠️",
            "status": "online",
            "description": "@Arquitetos & @QA Automation",
            "type": "bot"
        }
    ]
    
    # 2. Usuários que interagiram (apenas para Admins)
    if current_user.role == 'admin':
        # Busca subquery de usuários com mensagens
        user_ids_query = db.session.query(AgentMessage.user_id).filter(
            AgentMessage.company_id == company_id
        ).distinct()
        
        users = User.query.filter(User.id.in_(user_ids_query)).all()
        
        for u in users:
            # Pula o próprio usuário admin para não duplicar se ele for o contato principal
            if u.id == current_user.id:
                continue
                
            contacts.append({
                "id": str(u.id),
                "name": u.name,
                "avatar": u.name[0].upper(),
                "status": "recent",
                "description": u.email,
                "type": "user"
            })
            
    return jsonify({
        "success": True,
        "contacts": contacts
    })

@agents_bp.route('/api/agents/actions/approve/<int:action_id>', methods=['POST'])
@login_required
def approve_action(action_id):
    from services.engineering_service import engineering_service
    
    success, message = engineering_service.execute_repair(action_id)
    
    if success:
        return jsonify({
            "success": True, 
            "message": message
        })
    else:
        return jsonify({"success": False, "error": message}), 500

@agents_bp.route('/api/agents/actions/rollback/<int:action_id>', methods=['POST'])
@login_required
def rollback_action(action_id):
    from services.engineering_service import engineering_service
    
    success, message = engineering_service.rollback_repair(action_id)
    
    if success:
        return jsonify({
            "success": True, 
            "message": message
        })
    else:
        return jsonify({"success": False, "error": message}), 500

@agents_bp.route('/agents/planejamento')
@login_required
def agent_planejamento():
    return render_template('cadastro_agent.html', 
                           agent_type='planejamento', 
                           agent_name='Agente de Planejamento',
                           agent_description='Assistente especializado em Planejamento Estratégico e análises de mercado.')

@agents_bp.route('/agents/processos')
@login_required
def agent_processos():
    return render_template('cadastro_agent.html', 
                           agent_type='processos', 
                           agent_name='Agente de Processos',
                           agent_description='Especialista em mapeamento, análise e otimização de processos operacionais.')

@agents_bp.route('/agents/rotina')
@login_required
def agent_rotina():
    return render_template('cadastro_agent.html', 
                           agent_type='rotina', 
                           agent_name='Agente de Rotina',
                           agent_description='Focado em monitoramento, cobrança e follow-up de atividades diárias.')

@agents_bp.route('/agents/performance')
@login_required
def agent_performance():
    return render_template('cadastro_agent.html', 
                           agent_type='performance', 
                           agent_name='Agente de Performance',
                           agent_description='Análise profunda de indicadores de desempenho e resultados organizacionais.')

@agents_bp.route('/agents/estrategico')
@login_required
def agent_estrategico():
    return render_template('cadastro_agent.html', 
                           agent_type='estrategico', 
                           agent_name='Agente Estratégico',
                           agent_description='Suporte à alta gestão no monitoramento da execução da estratégia.')

@agents_bp.route('/agents/cadastro')
@login_required
def agent_cadastro():
    return render_template('cadastro_agent.html', 
                           agent_type='cadastro', 
                           agent_name='Agente de Cadastro',
                           agent_description='Assistente inteligente para cadastro e configuração de empresas e dados mestres.')

# API Routes for Agent
@agents_bp.route('/api/cadastro-agent/empresa/iniciar', methods=['POST'])
@login_required
def iniciar_cadastro():
    data = request.get_json()
    tipo = data.get('tipo', 'real')
    
    if tipo == 'real':
        return jsonify({
            'success': True,
            'data': {
                'mensagem': 'Ótimo! Para começar o cadastro da empresa real, por favor, me informe o CNPJ:',
                'proximo_campo': 'cnpj',
                'progresso': 5,
                'dados_coletados': {}
            }
        })
    else:
        return jsonify({
            'success': True,
            'data': {
                'mensagem': 'Vamos criar uma empresa exemplo. Qual nome deseja dar a ela?',
                'proximo_campo': 'name',
                'progresso': 5,
                'dados_coletados': {}
            }
        })

@agents_bp.route('/api/cadastro-agent/empresa/processar', methods=['POST'])
@login_required
def processar_cadastro():
    data = request.get_json()
    campo = data.get('campo')
    valor = data.get('valor')
    dados_coletados = data.get('dados_coletados', {})
    tipo = data.get('tipo', 'real')
    
    # Atualizar dados
    dados_coletados[campo] = valor
    
    # Se for CNPJ, buscar dados
    if campo == 'cnpj' and tipo == 'real':
        # Remove special chars for search
        cnpj_clean = "".join(filter(str.isdigit, valor))
        dados_api = cadastro_service._buscar_dados_cnpj(cnpj_clean)
        if dados_api:
            # Merge API data
            for k, v in dados_api.items():
                if v: dados_coletados[k] = v
            
            return jsonify({
                'success': True,
                'data': {
                    'mensagem': f"Encontrei os dados da empresa {dados_api.get('name')}! Algumas informações foram preenchidas automaticamente. Podemos continuar?",
                    'proximo_campo': 'segment' if 'segment' not in dados_coletados else 'city',
                    'progresso': 60,
                    'dados_coletados': dados_coletados
                }
            })

    # Sequence of fields
    sequence = ['name', 'client_code', 'cnpj', 'segment', 'city', 'state']
    if tipo == 'exemplo':
        sequence = ['name', 'segment']
        
    try:
        current_idx = sequence.index(campo)
        if current_idx + 1 < len(sequence):
            proximo = sequence[current_idx + 1]
            # Skip if already filled (from API)
            while proximo in dados_coletados and current_idx + 1 < len(sequence):
                current_idx += 1
                if current_idx + 1 < len(sequence):
                    proximo = sequence[current_idx + 1]
                else:
                    proximo = None
                    break
        else:
            proximo = None
    except ValueError:
        proximo = None

    if proximo:
        prompts = {
            'name': 'Qual o nome fantasia da empresa?',
            'client_code': 'Qual o código curto (3 letras/números) para identificação?',
            'segment': 'Qual o segmento de atuação?',
            'city': 'Em qual cidade fica a sede?',
            'state': 'E o estado (UF)?'
        }
        return jsonify({
            'success': True,
            'data': {
                'mensagem': prompts.get(proximo, f"Qual o {proximo}?"),
                'proximo_campo': proximo,
                'progresso': int((sequence.index(proximo) / len(sequence)) * 100),
                'dados_coletados': dados_coletados
            }
        })
    else:
        return jsonify({
            'success': True,
            'data': {
                'mensagem': "Tudo pronto! Já tenho os dados necessários. Podemos finalizar o cadastro?",
                'status': 'pronto_para_criar',
                'progresso': 100,
                'dados_coletados': dados_coletados
            }
        })

@agents_bp.route('/api/cadastro-agent/empresa/finalizar', methods=['POST'])
@login_required
def finalizar_cadastro():
    from models import db, Company, Role, Employee
    data = request.get_json()
    dados = data.get('dados', {})
    
    try:
        # Avoid duplicate client code
        client_code = dados.get('client_code')
        if not client_code:
            client_code = dados.get('name', 'EMP')[:3].upper()
            
        existing = Company.query.filter_by(client_code=client_code).first()
        if existing:
            import time
            client_code = f"{client_code[:2]}{int(time.time()) % 10}"

        company = Company(
            name=dados.get('name'),
            client_code=client_code,
            legal_name=dados.get('legal_name', dados.get('name')),
            cnpj=dados.get('cnpj'),
            segment=dados.get('segment'),
            city=dados.get('city'),
            state=dados.get('state')
        )
        db.session.add(company)
        db.session.commit()
        
        # Create Admin Role
        role = Role.query.filter_by(company_id=company.id, title='Administrador').first()
        if not role:
            role = Role(
                company_id=company.id, 
                title='Administrador', 
                permissions={
                    "projects": ["view", "create", "edit", "delete"],
                    "indicators": ["view", "create", "edit", "delete"],
                    "processes": ["view", "create", "edit", "delete"],
                    "companies": ["view", "edit"],
                    "okrs": ["view", "create", "edit", "delete"]
                }
            )
            db.session.add(role)
            db.session.commit()
            
        emp = Employee(
            user_id=current_user.id,
            company_id=company.id,
            role_id=role.id,
            name=current_user.name,
            email=current_user.email,
            status='active'
        )
        db.session.add(emp)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': {
                'mensagem': f"Empresa '{company.name}' criada com sucesso! Você agora é o administrador desta unidade.",
                'proximos_passos': [
                    "Acessar o módulo de 'Planejamento' para definir OKRs.",
                    "Configurar os primeiros 'Indicadores' de desempenho.",
                    "Mapear os 'Processos' críticos da operação."
                ]
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
