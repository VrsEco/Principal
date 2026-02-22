from langchain_core.tools import tool
from models import db
from src.intelligence.rag import knowledge_base
from sqlalchemy import text
import json
import os
import re

def get_active_company_id():
    """Recupera o ID da empresa ativa de forma resiliente (Sessão, Ambiente ou Contexto)."""
    try:
        from flask import session
        if session.get('company_id'):
            return session.get('company_id')
    except:
        pass
    return os.environ.get('ACTIVE_COMPANY_ID')

def sanitize_output(data):
    """Sanitiza strings para evitar erros de encoding no terminal Windows (Gold Rule)."""
    if isinstance(data, str):
        # Remove ou substitui emojis e caracteres problemáticos que quebram o charmap
        return data.encode('ascii', 'ignore').decode('ascii')
    return data

@tool
def consult_rules(query: str):
    """
    Consulta o manual de regras de negócio e procedimentos da empresa (Base de Conhecimento RAG).
    Use isto sempre que tiver dúvidas sobre políticas internas, limites de aprovação ou processos fiscais.
    """
    try:
        results = knowledge_base.search(query, k=3)
        if not results:
            return "Nenhuma regra encontrada para esta consulta."
        
        formatted_results = "\n\n".join([f"Regra: {doc.page_content}" for doc in results])
        return formatted_results
    except Exception as e:
        return f"Erro ao consultar regras: {str(e)}"

@tool
def query_database(sql_query: str):
    """
    Executa uma consulta SQL SELECT (somente leitura) no banco de dados para buscar dados operacionais.
    SEGURANÇA: Filtros por 'company_id' são injetados AUTOMATICAMENTE.
    ERROS COMUNS: Não tente acessar as tabelas 'users', 'roles', 'employees' ou 'companies'.
    EXEMPLOS:
    - 'SELECT * FROM plans' -> Retorna planos da sua empresa.
    - 'SELECT name, status FROM indicators' -> Lista indicadores.
    - 'SELECT title FROM projects WHERE status = "active"' -> Projetos ativos.
    """
    import re
    
    # 1. Proteção de Comandos
    clean_query = sql_query.strip()
    if not clean_query.lower().startswith("select"):
        return "Erro: Por segurança, apenas consultas SELECT são permitidas."

    # 2. Lista Negra de Tabelas (Prevenção de Exposição de Dados Sensíveis)
    sensitive_tables = [
        "users", "roles", "user_logs", "audit_log", "sessions", 
        "alembic_version", "employees", "companies"
    ]
    for table in sensitive_tables:
        if re.search(rf"\b{table}\b", clean_query.lower()):
            return sanitize_output(f"Erro: Acesso à tabela '{table}' é restrito por motivos de segurança e privacidade.")

    # 3. Injeção de Segurança Multi-tenancy
    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Contexto de empresa nao identificado (Sessão ou ACTIVE_COMPANY_ID ausente)."

    # Injeção Inteligente de Filtro de Empresa
    if "where" in clean_query.lower():
        secure_query = re.sub(r"(?i)where", f"WHERE company_id = {company_id} AND", clean_query)
    else:
        if "order by" in clean_query.lower():
            secure_query = re.sub(r"(?i)order by", f"WHERE company_id = {company_id} ORDER BY", clean_query)
        elif "limit" in clean_query.lower():
            secure_query = re.sub(r"(?i)limit", f"WHERE company_id = {company_id} LIMIT", clean_query)
        else:
            secure_query = f"{clean_query} WHERE company_id = {company_id}"
        
    try:
        with db.engine.connect() as connection:
            result = connection.execute(text(secure_query))
            rows = [dict(row._mapping) for row in result]
            if not rows:
                return "Nenhum resultado encontrado para esta consulta no contexto da sua empresa."
            return sanitize_output(json.dumps(rows, default=str))
    except Exception as e:
        return sanitize_output(f"Erro ao executar query SQL: {str(e)}")

@tool
def escalate_technical_issue(error_description: str, context: str):
    """
    Escalona um erro técnico ou de sistema para o Time de Engenharia. 
    Use isto quando encontrar erros de código (ex: Jinja, Python, DB) que impedem sua operação.
    O Time de Engenharia será notificado para criar uma solução.
    """
    from models.agent_action import AgentAction
    from services.whatsapp_service import whatsapp_service
    from flask import session
    from flask_login import current_user
    
    company_id = get_active_company_id()
    user_id = current_user.id if current_user.is_authenticated else None
    
    try:
        # 1. Cria o registro da ação de auditoria/reparo
        action = AgentAction(
            type='technical_fix',
            status='pending',
            requesting_agent='work_agent_squad',
            handling_agent='engineering_squad',
            title='Correção Técnica Necessária',
            description=f"Erro detectado: {error_description}\nContexto: {context}",
            payload={"error": error_description, "context": context},
            company_id=company_id,
            user_id=user_id
        )
        db.session.add(action)
        db.session.commit()
        
        # 2. Notifica o usuário via WhatsApp (Simulado ou Real)
        # Buscamos o telefone do usuário se disponível, ou usamos um placeholder
        phone = getattr(current_user, 'phone', None) or "5511999999999" 
        
        wa_message = (
            f"🚨 *Gestão Versus: Alerta de Sistema*\n\n"
            f"O Agente Sapiens detectou um erro técnico: _{error_description}_\n\n"
            f"O Time de Engenharia já foi acionado e está preparando um reparo. "
            f"Você receberá uma nova mensagem para aprovar a correção em breve."
        )
        whatsapp_service.send_message(phone, wa_message)
        
        return f"Escalonamento realizado com sucesso. Ticket #{action.id} criado. O usuário foi notificado via WhatsApp."
    except Exception as e:
        return f"Erro ao processar escalonamento: {str(e)}"

@tool
def create_process_area(name: str, description: str = None, code: str = None):
    """
    Cria uma nova Área de Processo no sistema.
    As Áreas são o nível mais alto da hierarquia de processos.
    """
    from models.process import ProcessArea
    from flask import session
    
    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada (Sessão ou ACTIVE_COMPANY_ID)."
        
    try:
        from api.resources.process import generate_area_code
        new_area = ProcessArea(
            company_id=company_id,
            name=name,
            description=description,
            code=code
        )
        
        # Gera o código se fornecido um sequencial simples
        if code and '.' not in str(code):
             new_area.code = generate_area_code(company_id, code)
             
        db.session.add(new_area)
        db.session.commit()
        return f"Área de Processo '{name}' criada com sucesso. ID: {new_area.id}, Código: {new_area.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar área de processo: {str(e)}"

@tool
def create_macro_process(area_id: int, name: str, description: str = None, order_index: int = 1):
    """
    Cria um novo Macroprocesso vinculado a uma Área de Processo.
    """
    from models.process import MacroProcess
    from flask import session
    
    company_id = get_active_company_id()
    try:
        from api.resources.process import generate_macro_code
        macro = MacroProcess(
            company_id=company_id,
            area_id=area_id,
            name=name,
            description=description,
            order_index=order_index
        )
        macro.code = generate_macro_code(area_id, order_index)
        
        db.session.add(macro)
        db.session.commit()
        return f"Macroprocesso '{name}' criado com sucesso. ID: {macro.id}, Código: {macro.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar macroprocesso: {str(e)}"

@tool
def create_process(macro_id: int, name: str, description: str = None, responsible: str = None, order_index: int = 1):
    """
    Cria um novo Processo vinculado a um Macroprocesso.
    Este é o nível onde as rotinas (POPs) serão penduradas.
    """
    from models.process import Process
    from flask import session
    
    company_id = get_active_company_id()
    try:
        from api.resources.process import generate_process_code
        process = Process(
            company_id=company_id,
            macro_id=macro_id,
            name=name,
            description=description,
            responsible=responsible,
            order_index=order_index
        )
        process.code = generate_process_code(macro_id, order_index)
        
        db.session.add(process)
        db.session.commit()
        return f"Processo '{name}' criado com sucesso. ID: {process.id}, Código: {process.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar processo: {str(e)}"

@tool
def update_company_status(company_id: int, is_active: bool, reason: str = None):
    """
    Atualiza o status de atividade (Ativo/Inativo) de uma empresa.
    Use isto quando o usuário pedir para 'desativar', 'inativar' ou 'ativar' uma empresa.
    """
    from models.company import Company
    try:
        company = Company.query.get(company_id)
        if not company:
            return f"Erro: Empresa com ID {company_id} não encontrada."
            
        company.is_active = is_active
        db.session.commit()
        
        status_text = "Inativada" if not is_active else "Ativada"
        return f"Sucesso: A empresa '{company.name}' (ID: {company_id}) foi {status_text}. Motivo: {reason or 'Não informado'}."
    except Exception as e:
        db.session.rollback()
        return f"Erro ao atualizar status da empresa: {str(e)}"

@tool
def list_process_hierarchy():
    """
    Lista toda a hierarquia de processos da empresa (Áreas -> Macros -> Processos).
    Use isto para entender a estrutura atual antes de criar novos itens.
    """
    from models.process import ProcessArea, MacroProcess, Process
    from flask import session
    
    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Empresa nao selecionada."
        
    try:
        areas = ProcessArea.query.filter_by(company_id=company_id).all()
        output = []
        for area in areas:
            output.append(f"Área: {area.name} (ID: {area.id}, Código: {area.code})")
            macros = MacroProcess.query.filter_by(area_id=area.id).all()
            for macro in macros:
                output.append(f"  └─ Macro: {macro.name} (ID: {macro.id}, Código: {macro.code})")
                procs = Process.query.filter_by(macro_id=macro.id).all()
                for p in procs:
                    output.append(f"    └─ Processo: {p.name} (ID: {p.id}, Código: {p.code})")
        
        return "\n".join(output) if output else "Nenhum processo mapeado ainda."
    except Exception as e:
        return f"Erro ao listar hierarquia: {str(e)}"

@tool
def list_plans(mode: str = None):
    """
    Lista todos os planos estratégicos (Growth ou Implantation) da empresa ativa.
    Use isto para descobrir quais planos de ação estão em curso.
    :param mode: Opcional 'growth' ou 'implantation' para filtrar.
    """
    from services.plan_service import PlanService
    from flask import session
    company_id = get_active_company_id()
    if not company_id: return "Erro: Contexto de empresa nao identificado."
    
    try:
        plans = PlanService.list_plans(company_id, mode)
        if not plans: return "Nenhum plano encontrado."
        return "\n".join([f"ID: {p.id} | Título: {p.title} | Modo: {p.mode} | Progresso: {p.progress}%" for p in plans])
    except Exception as e:
        return f"Erro ao listar planos: {str(e)}"

@tool
def get_plan_diagnostics(plan_id: int):
    """
    Retorna um diagnóstico completo de um plano, incluindo status de cada seção e métricas financeiras.
    Use isto para entender gargalos ou o estado atual de uma implantação/crescimento.
    """
    from services.plan_service import PlanService
    from flask import session
    company_id = get_active_company_id()
    if not company_id: return "Erro: Contexto de empresa nao identificado."
    
    try:
        data = PlanService.get_plan_dashboard_data(plan_id, company_id)
        if not data: return f"Plano {plan_id} não encontrado ou sem acesso."
        
        output = [
            f"DIAGNÓSTICO DO PLANO: {data['plan']['title']} (ID: {plan_id}, Modo: {data['plan']['mode']})",
            f"Progresso Geral: {data['stats']['progress_pct']}%",
            "\nSTATUS DAS SEÇÕES:"
        ]
        
        for s in data['sections']:
            status_emoji = "✅" if s['status'] == 'completed' else "⏳" if s['status'] == 'in_progress' else "❌"
            output.append(f"  {status_emoji} {s['title']}: {s['status']}")
            
        if 'finance' in data:
            output.append("\nRESUMO FINANCEIRO (Implantação):")
            output.append(f"  Investimento Total: R$ {data['finance']['total_investment']:,.2f}")
            output.append(f"  Payback Estimado: {data['finance']['payback']} meses")
            
        return sanitize_output("\n".join(output))
    except Exception as e:
        return sanitize_output(f"Erro ao diagnosticar plano: {str(e)}")

@tool
def update_plan_section(plan_id: int, section_key: str, status: str = 'completed'):
    """
    Atualiza o status de uma seção do plano (ex: 'participants', 'finance', 'projects').
    Use isto para marcar etapas como concluídas conforme a IA ou o usuário executam as tarefas.
    """
    from services.plan_service import PlanService
    from flask import session
    company_id = get_active_company_id()
    if not company_id: return "Erro: Contexto de empresa nao identificado."

    try:
        # Check permissions/existence
        plan = PlanService.get_plan(plan_id, company_id)
        if not plan: return f"Plano {plan_id} não encontrado."
        
        PlanService.update_section_status(plan_id, section_key, status)
        return f"Sucesso: Seção '{section_key}' do plano {plan_id} alterada para '{status}'."
    except Exception as e:
        return f"Erro ao atualizar seção: {str(e)}"

@tool
def get_my_work(scope: str = 'me', company_ids: str = None):
    """
    Retorna a lista de atividades (Projetos e Processos) pendentes para o usuário logado.
    :param scope: 'me' para minhas atividades, 'team' para equipe, 'company' para toda a empresa.
    :param company_ids: Opcional, ids de empresas separados por virgula (ex: "31,32"). Se vazio, busca pendências em TODAS as empresas permitidas.
    """
    from services.my_work_service import get_user_activities, get_user_employees, _get_company_activities_unrestricted
    from models.user import User
    from flask import session
    from flask_login import current_user
    
    user_id = getattr(current_user, 'id', None)
    if not user_id:
        return "Erro: Usuário não autenticado."
        
    try:
        user = User.query.get(user_id)
        user_role = getattr(user, 'role', 'collaborator') if user else 'collaborator'
        
        # 1. Definir acesso
        accessible_company_ids = []
        all_employee_ids = []

        if user_role == 'admin':
            from models.company import Company
            all_companies = Company.query.all()
            accessible_company_ids = [c.id for c in all_companies]
            user_employees = get_user_employees(user_id)
            all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]
        else:
            user_employees = get_user_employees(user_id)
            accessible_company_ids = [c['company_id'] for c in user_employees if c.get('company_id')]
            all_employee_ids = [e['employee_id'] for e in user_employees if e.get('employee_id')]

        # 2. Filtrar
        if company_ids:
            requested_ids = [int(i.strip()) for i in company_ids.split(",") if i.strip().isdigit()]
            effective_company_ids = [cid for cid in requested_ids if cid in accessible_company_ids]
        else:
            effective_company_ids = accessible_company_ids

        if not effective_company_ids:
            return "Nenhuma empresa acessível encontrada para este usuário."

        filters = {
            "delivery_tags": ["open"],
            "sort": "deadline"
        }

        # 3. Busca de supervisão vs pessoal
        main_employee_id = all_employee_ids[0] if all_employee_ids else None
        
        if not main_employee_id and user_role in ('admin', 'client'):
            # Supervisão pura
            from database.postgres_helper import connect as pg_connect
            conn = pg_connect()
            cursor = conn.cursor()
            try:
                activities = _get_company_activities_unrestricted(
                    cursor, effective_company_ids, filters=filters
                )
            finally:
                conn.close()
        else:
            # Pessoal / Equipe
            activities = get_user_activities(
                main_employee_id, 
                scope=scope, 
                filters=filters, 
                company_ids=effective_company_ids,
                employee_ids=all_employee_ids
            )
        
        if not activities:
            return f"Nenhuma atividade pendente encontrada no escopo '{scope}' para as empresas selecionadas."
            
        summary = []
        for a in activities:
            deadline = a.get('deadline_label') or a.get('deadline') or 'Sem prazo'
            comp_name = a.get('company_name') or 'Empresa'
            summary.append(
                f"- [{a.get('type', 'tarefa').upper()}] {a.get('title')} "
                f"| Empresa: {comp_name} | ID: {a.get('id')} | Prazo: {deadline} | Status: {a.get('status')}"
            )
            
        return "\n".join(summary)
    except Exception as e:
        return f"Erro ao buscar atividades via MCP: {str(e)}"

# Lista de ferramentas para exportação
tools = [
    consult_rules, 
    query_database, 
    escalate_technical_issue,
    create_process_area,
    create_macro_process,
    create_process,
    update_company_status,
    list_process_hierarchy,
    list_plans,
    get_plan_diagnostics,
    update_plan_section,
    get_my_work
]
