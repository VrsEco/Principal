"""
======================================================================================
GESTAO VERSUS - MCP TOOLS (Ferramentas do Agente Sapiens)
======================================================================================

LEI DE CONFORMIDADE ARQUITETURAL - REGRA INQUEBRAVEL
------------------------------------------------------
Toda tool neste arquivo DEVE obedecer a seguinte classificacao:

CATEGORIA A - MUTACAO DE DADOS (INSERT / UPDATE / DELETE):
  [OK]  OBRIGATORIO: Usar os mesmos Models SQLAlchemy (ORM) e Services que o Frontend usa.
  [OK]  OBRIGATORIO: O resultado de qualquer acao do Sapiens DEVE ser visivel, editavel
                     e continuavel pelo usuario humano na interface do app.
  [XX]  PROIBIDO: Executar INSERT/UPDATE/DELETE via SQL bruto (text()).
  [XX]  PROIBIDO: Criar logicas de negocio paralelas as do app (ex: gerar ATA fora do
                  campo meeting.meeting_notes, criar projetos em tabela diferente, etc).

  PRINCIPIO: "O Sapiens eh um usuario programatico. Ele faz exatamente o que um usuario
  humano faria clicando nos botoes do sistema - nem mais, nem menos."

CATEGORIA B - ANALISE DE DADOS (SELECT / Cruzamentos / Relatorios Analiticos):
  [OK]  PERMITIDO: Usar query_database() com SQL SELECT customizado para analises.
  [OK]  PERMITIDO: Cruzar multiplas tabelas, calcular metricas, agregar dados.
  [OK]  PERMITIDO: Gerar insights que um humano faria pegando 2-3 relatorios e
                   analisando em planilha.
  [XX]  PROIBIDO: SELECT em tabelas sensiveis: users, roles, employees, companies,
                  sessions, alembic_version, audit_log.

  PRINCIPIO: "Analise livre e aceitavel porque um humano tambem consultaria o banco
  diretamente ou exportaria relatorios para cruzar os dados."

AUDITORIA DE CONFORMIDADE (@QA_AUTOMATION) - Checklist para novas tools:
  [ ] A tool escreve dados? -> Use Model SQLAlchemy da pasta /models.
  [ ] A tool envia mensagem? -> Use services/email_service.py ou whatsapp_service.py.
  [ ] A tool le relatorio? -> Chame a API REST existente ou use query_database().
  [ ] O usuario pode ver, editar e continuar o resultado na interface? -> Sim = OK.
======================================================================================
"""
from langchain_core.tools import tool
from models import db
from src.intelligence.rag import knowledge_base
from sqlalchemy import text
import json
import os
import re

from src.intelligence.tool_context import (
    active_user_id_ctx, 
    active_company_id_ctx,
    get_sapiens_context
)

def get_active_company_id():
    """Recupera o ID da empresa ativa de forma resiliente (@ARQUITETO)."""
    # 1. Prioridade: Contexto Unificado Sapiens
    identity = get_sapiens_context()
    if identity.company_id:
        return identity.company_id
    
    # 2. Legado: Contexto Direto (Thread-safe)
    cid = active_company_id_ctx.get()
    if cid:
        return cid
    
    # 3. Legado: Ambiente
    env_cid = os.environ.get('ACTIVE_COMPANY_ID')
    if env_cid:
        return int(env_cid)

    # 4. Sessão Flask (apenas se estiver em request web)
    try:
        from flask import session, has_request_context
        if has_request_context():
            sess_cid = session.get('active_company_id') or session.get('company_id')
            if sess_cid:
                return sess_cid
    except:
        pass
    
    # 5. Fallback: Lookup por User ID
    uid = get_active_user_id()
    if uid:
        try:
            # Import inline para evitar circular dependency
            from models.employee import Employee
            first_emp = Employee.query.filter_by(user_id=uid).first()
            if first_emp:
                return first_emp.company_id
        except:
            pass
            
    return None


def get_active_user_id():
    """Recupera o ID do usuario logado ou via canal (Telegram/WA/etc) (@ARQUITETO)."""
    # 1. Prioridade: Contexto Unificado Sapiens
    identity = get_sapiens_context()
    if identity.user_id:
        return identity.user_id
        
    # 2. Legado: Contexto Direto
    uid = active_user_id_ctx.get()
    if uid:
        return uid
        
    # 3. Legado: Ambiente
    env_uid = os.environ.get('ACTIVE_USER_ID')
    if env_uid:
        return int(env_uid)

    # 4. Flask-Login (Apenas Web)
    try:
        from flask_login import current_user
        from flask import has_request_context
        if has_request_context() and current_user and getattr(current_user, 'is_authenticated', False):
            return current_user.id
    except:
        pass
    
    return None

def get_active_user():
    """Recupera o objeto User do banco de dados baseado no contexto ativo."""
    uid = get_active_user_id()
    if uid:
        from models.user import User
        # Usar session explicitamente para evitar erros de context
        return db.session.get(User, uid)
    return None
    return None

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
    DICA: Para informações sobre empresas (IDs, Prefixos), use a ferramenta 'list_my_companies'.
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
    
    
    company_id = get_active_company_id()
    user_id = get_active_user_id()
    
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
        user = get_active_user()
        phone = getattr(user, 'phone', None) or "5511999999999" 
        
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
def list_process_hierarchy(company_id: int = None):
    """
    Lista toda a hierarquia de processos da empresa (Áreas -> Macros -> Processos).
    Use isto para entender a estrutura atual antes de criar novos itens.
    :param company_id: Opcional ID da empresa. Se não fornecido, usa a empresa ativa da sessão.
    """
    from models.process import ProcessArea, MacroProcess, Process
    from flask import session
    
    effective_id = company_id or get_active_company_id()
    if not effective_id:
        return "Erro: Empresa nao selecionada e nenhum company_id fornecido."
        
    try:
        areas = ProcessArea.query.filter_by(company_id=effective_id).all()
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
def list_my_companies(search_term: str = None):
    """
    Lista as empresas às quais o usuário tem acesso, incluindo o Prefixo (client_code) e o ID.
    Use isto quando precisar identificar o ID de uma empresa pelo nome ou prefixo.
    :param search_term: Opcional termo de busca (nome ou prefixo).
    """
    from models.company import Company
    from models.employee import Employee
    
    
    user_id = get_active_user_id()
    if not user_id:
        return "Erro: Usuário não autenticado."
        
    try:
        from models.user import User
        user = User.query.get(user_id)
        user_role = getattr(user, 'role', 'collaborator')

        if user_role == 'admin':
            # Admins veem todas as empresas
            query = db.session.query(Company)
        else:
            # Outros veem apenas onde são funcionários
            query = db.session.query(Company).join(Employee, Employee.company_id == Company.id).filter(Employee.user_id == user_id)
        
        if search_term:
            query = query.filter(
                (Company.name.ilike(f'%{search_term}%')) | 
                (Company.client_code.ilike(f'%{search_term}%'))
            )
            
        companies = query.all()
        if not companies:
            return f"Nenhuma empresa encontrada para o termo '{search_term}'." if search_term else "Nenhuma empresa vinculada ao seu usuário."
            
        lines = ["🏢 SUAS EMPRESAS ACESSÍVEIS:", ""]
        for c in companies:
            prefix = c.client_code or "SEM PREFIXO"
            lines.append(f"- ID: {c.id} | Prefixo: {prefix} | Nome: {c.name}")
            
        return sanitize_output("\n".join(lines))
    except Exception as e:
        return f"Erro ao listar empresas: {str(e)}"

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
def get_my_work(scope: str = 'me', company_ids: str = None, search_term: str = None):
    """
    Retorna a lista de atividades (Projetos e Processos) pendentes para o usuário logado.
    :param scope: 'me' para minhas atividades, 'team' para equipe, 'company' para toda a empresa.
    :param company_ids: Opcional, ids de empresas separados por virgula (ex: "31,32"). Se vazio, busca pendências em TODAS as empresas permitidas.
    :param search_term: Opcional, filtra atividades por título, descrição ou nome de empresa. Use para buscar tarefas de um colega específico (ex: "atividades de Caroline").
    """
    from services.my_work_service import get_user_activities, get_user_employees, _get_company_activities_unrestricted
    from models.user import User
    from flask import session
    
    user_id = get_active_user_id()
    print(f"--- TOOL [get_my_work]: user_id={user_id} | scope={scope} | ctx_user={active_user_id_ctx.get()} ---")
    
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
            "sort": "deadline",
            "search": search_term
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

@tool
def get_user_summary(target_user: str = None, range: str = 'today'):
    """
    Gera um relatório consolidado de atividades, processos e REUNIÕES de um usuário.
    Use isto para 'meu resumo' ou para 'resumo do Fulano'.
    :param target_user: ID (inteiro), Email ou Nome do usuário. Se omitido, busca o próprio resumo.
    :param range: 'today' para resumo do dia ou 'week' para resumo da semana (domingo a sábado).
    """
    from services.proactive_service import get_user_summary_report
    from models.user import User
    from models.employee import Employee
    from sqlalchemy import or_

    requesting_user_id = get_active_user_id()
    if not requesting_user_id:
        return "Erro: Usuário não autenticado."

    try:
        req_user = User.query.get(requesting_user_id)
        if not req_user:
            return "Erro: Seu usuário não foi encontrado."
        
        # 1. Identificar o usuário alvo
        if not target_user:
            target = req_user
        else:
            # Busca flexível por ID, Email ou Nome
            if str(target_user).isdigit():
                target = User.query.get(int(target_user))
            else:
                target = User.query.filter(
                    or_(
                        User.email.ilike(f"{target_user}"),
                        User.name.ilike(f"%{target_user}%")
                    )
                ).first()
            
            if not target:
                return f"Erro: Usuário '{target_user}' não encontrado."

        # 2. Verificação de Permissão (RBAC Multi-tenancy)
        if req_user.id != target.id:
            req_role = getattr(req_user, 'role', 'collaborator')
            
            if req_role == 'admin':
                # Admins podem ver usuários de empresas às quais estão vinculados
                # Para simplificar na arquitetura Versus, Admin vê todos se não houver restrição explícita no Employee
                pass # Por enquanto admin tem passe livre se for o papel 'admin' global
            elif req_role == 'client':
                # Cliente vê apenas usuários que pertencem à mesma empresa que ele (vias Employee)
                req_companies = [e.company_id for e in Employee.query.filter_by(user_id=req_user.id).all()]
                target_companies = [e.company_id for e in Employee.query.filter_by(user_id=target.id).all()]
                
                # Check intersection
                if not set(req_companies).intersection(target_companies):
                    return f"Erro: Você não tem permissão para visualizar o resumo de {target.name}. Usuário pertence a outras empresas."
            else:
                return "Erro: Colaboradores podem visualizar apenas o seu próprio resumo. Use 'meu resumo'."

        # 3. Gerar Relatório
        report = get_user_summary_report(target, date_range=range)
        
        prefix = f"📊 RESUMO DE {target.name.upper()} ({range.upper()})\n\n" if req_user.id != target.id and "está 100% em dia" not in report else ""
        return prefix + report
        
    except Exception as e:
        return f"Erro ao gerar resumo: {str(e)}"

@tool
def list_system_users():
    """
    Lista todos os usuários cadastrados no sistema. (Admin Only)
    Retorna nome, email, papel e contatos (WhatsApp/Telegram).
    """
    from models.user import User
    
    user = get_active_user()
    if not user or getattr(user, 'role', 'collaborator') != 'admin':
        return "Erro: Apenas administradores podem listar usuários."
        
    try:
        users = User.query.all()
        if not users:
            return "Nenhum usuário encontrado."
            
        output = ["USUÁRIOS DO SISTEMA:"]
        for u in users:
            wa = u.whatsapp or "N/A"
            tg = u.telegram or "N/A"
            output.append(f"- ID: {u.id} | {u.name} ({u.email}) | Papel: {u.role} | WA: {wa} | TG: {tg}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Erro ao listar usuários: {str(e)}"

@tool
def register_system_user(name: str, email: str, role: str = 'collaborator', whatsapp: str = None, telegram: str = None):
    """
    Cadastra um novo usuário no sistema com dados de contato.
    :param name: Nome completo
    :param email: E-mail único
    :param role: Papel (admin, collaborator, client)
    :param whatsapp: Número de WhatsApp com DDD
    :param telegram: Username ou número do Telegram
    """
    from models.user import User
    from models import db
    
    import secrets
    import string
    
    user = get_active_user()
    if not user or getattr(user, 'role', 'collaborator') != 'admin':
        return "Erro: Acesso restrito a administradores."
        
    try:
        # Verificar se email já existe
        if User.query.filter_by(email=email).first():
            return f"Erro: O e-mail '{email}' já está em uso."
            
        # Gera uma senha aleatória para o primeiro acesso
        alphabet = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        
        user = User(
            name=name,
            email=email,
            role=role,
            whatsapp=whatsapp,
            telegram=telegram
        )
        user.set_password(temp_password)
        
        db.session.add(user)
        db.session.commit()
        
        return (
            f"Usuário '{name}' cadastrado com sucesso! ID: {user.id}\n"
            f"OBS: Uma senha temporária foi gerada. Comunique ao usuário via {whatsapp or email}.\n"
            f"Senha Temporária: {temp_password}"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao cadastrar usuário: {str(e)}"

@tool
def update_user_contacts(user_id: int, whatsapp: str = None, telegram: str = None):
    """
    Atualiza os dados de contato (WhatsApp/Telegram) de um usuário.
    Pode ser usado para atualizar os próprios dados ou por um admin.
    """
    from models.user import User
    from models import db
    
    
    try:
        user_to_update = User.query.get(user_id)
        if not user_to_update:
            return f"Erro: Usuário ID {user_id} não encontrado."
            
        # Segurança: Admin ou o próprio usuário
        current_user_obj = get_active_user()
        if not current_user_obj:
            return "Erro: Usuário não identificado."
            
        if getattr(current_user_obj, 'role', 'collaborator') != 'admin' and current_user_obj.id != user_id:
            return "Erro: Você não tem permissão para alterar os dados deste usuário."
            
        if whatsapp is not None: user_to_update.whatsapp = whatsapp
        if telegram is not None: user_to_update.telegram = telegram
        
        db.session.commit()
        return f"Contatos do usuário '{user_to_update.name}' atualizados com sucesso."
    except Exception as e:
        db.session.rollback()
        return f"Erro ao atualizar contatos: {str(e)}"


# =============================================================================
# FASE 2: TOOLS DE REUNIÃO
# =============================================================================

@tool
def schedule_meeting(title: str, date: str, time: str, guests: str, agenda_items: str = None, notes: str = None):
    """
    Cria e agenda uma nova reunião no sistema enviando convite para os participantes.
    :param title: Título/Assunto da reunião. Ex: 'Revisão de Metas Q1'
    :param date: Data da reunião no formato YYYY-MM-DD. Ex: '2026-03-01'
    :param time: Horário no formato HH:MM. Ex: '14:30'
    :param guests: Lista de e-mails ou nomes dos convidados, separados por vírgula. Ex: 'ana@empresa.com, pedro@empresa.com'
    :param agenda_items: Pautas separadas por ponto-e-vírgula. Ex: 'Revisão de metas; Status dos projetos; Próximos passos'
    :param notes: Observações ou pauta livre para o convite.
    """
    from models.meeting import Meeting
    from models.user import User
    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service
    import json

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        # Monta estrutura de convidados
        guest_list = [g.strip() for g in guests.split(',') if g.strip()]
        guest_dict = {g: g for g in guest_list}  # {email/nome: email/nome}

        # Monta pauta
        agenda = []
        if agenda_items:
            agenda = [{"title": item.strip()} for item in agenda_items.split(';') if item.strip()]

        meeting = Meeting(
            company_id=int(company_id),
            title=title,
            scheduled_date=date,
            scheduled_time=time,
            invite_notes=notes or "",
            guests_json=json.dumps(guest_dict),
            agenda_json=json.dumps(agenda),
            status='draft'
        )
        db.session.add(meeting)
        db.session.commit()

        # Envia convite por e-mail para quem for e-mail válido
        email_guests = [g for g in guest_list if '@' in g]
        if email_guests:
            pauta_texto = "\n".join([f"  • {a['title']}" for a in agenda]) if agenda else "A definir na reunião."
            email_body = (
                f"Prezado(a),\n\n"
                f"Você foi convidado(a) para a reunião:\n\n"
                f"📅 {title}\n"
                f"🗓️  Data: {date} às {time}\n"
                f"📋 Pautas:\n{pauta_texto}\n\n"
                f"{notes or ''}\n\n"
                f"Atenciosamente,\nGestão Versus"
            )
            email_service.send_email(
                to_emails=email_guests,
                subject=f"Convite de Reunião: {title}",
                body=email_body
            )

        return (
            f"✅ Reunião '{title}' criada com sucesso!\n"
            f"   ID: {meeting.id} | Data: {date} às {time}\n"
            f"   Convidados: {', '.join(guest_list)}\n"
            f"   Convite enviado por e-mail para: {', '.join(email_guests) if email_guests else 'Nenhum e-mail válido informado.'}\n"
            f"   Para iniciar a reunião quando chegar a hora, diga: 'Sapiens, inicie a reunião {meeting.id}'."
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao agendar reunião: {str(e)}"


@tool
def start_meeting(meeting_id: int):
    """
    Inicia uma reunião agendada. Marca o horário real de início e vincula/cria um projeto automático.
    :param meeting_id: ID da reunião a ser iniciada (obtido ao criar a reunião).
    """
    from models.meeting import Meeting
    from models.project import Project
    from datetime import datetime

    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return f"Reunião ID {meeting_id} não encontrada."

        now = datetime.now()
        meeting.actual_date = now.date()
        meeting.actual_time = now.strftime("%H:%M")
        meeting.status = 'in_progress'

        # Cria projeto vinculado se não existir
        if not meeting.project_id:
            proj = Project(
                company_id=meeting.company_id,
                name=f"Reunião - {meeting.title} ({now.strftime('%d/%m/%Y')})",
                status="in_progress",
                priority="medium",
                owner="Sapiens",
                deadline=now.date(),
                notes=f"Projeto gerado automaticamente para a reunião ID {meeting.id}: {meeting.title}"
            )
            db.session.add(proj)
            db.session.flush()
            meeting.project_id = proj.id

        db.session.commit()
        return (
            f"🟢 Reunião '{meeting.title}' INICIADA!\n"
            f"   Horário de início: {now.strftime('%d/%m/%Y às %H:%M')}\n"
            f"   Projeto vinculado: ID {meeting.project_id}\n"
            f"   Agora registre os pontos discutidos: 'Sapiens, registre o ponto: [tópico] — decisão: [decisão] — responsável: [nome] — prazo: [data]'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao iniciar reunião: {str(e)}"


@tool
def log_meeting_discussion(meeting_id: int, topic: str, decision: str = None, responsible: str = None, deadline: str = None):
    """
    Registra um ponto discutido, decisão tomada ou atividade criada durante a reunião.
    Use repetidamente para cada ponto discutido durante a reunião.
    :param meeting_id: ID da reunião em andamento.
    :param topic: Assunto/Tópico discutido. Ex: 'Revisão das metas de vendas'
    :param decision: Decisão tomada. Ex: 'Aumentar meta em 15% para Q2'
    :param responsible: Nome do responsável pela ação. Ex: 'Carlos'
    :param deadline: Prazo para conclusão no formato YYYY-MM-DD. Ex: '2026-03-31'
    """
    from models.meeting import Meeting
    from models.project import ProjectTask
    import json

    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return f"Reunião ID {meeting_id} não encontrada."

        # Adiciona à lista de discussões
        discussions = json.loads(meeting.discussions_json or "[]")
        entry = {
            "title": topic,
            "decision": decision or "",
            "responsible": responsible or "",
            "deadline": deadline or "",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        discussions.append(entry)
        meeting.discussions_json = json.dumps(discussions)

        # Se houver responsável e prazo, cria atividade na lista de atividades da reunião
        if responsible and deadline:
            activities = json.loads(meeting.activities_json or "[]")
            activities.append({
                "title": decision or topic,
                "responsible": responsible,
                "deadline": deadline,
                "how": f"Originado da discussão: {topic}"
            })
            meeting.activities_json = json.dumps(activities)

            # Se já existe projeto vinculado, cria a task diretamente
            if meeting.project_id:
                from models.project import ProjectTask
                from datetime import datetime as dt
                try:
                    due = dt.strptime(deadline, '%Y-%m-%d').date()
                except:
                    due = None
                task = ProjectTask(
                    project_id=meeting.project_id,
                    what=decision or topic,
                    how=f"Decisão de reunião: {topic}",
                    who=responsible,
                    due_date=due,
                    status='not_started',
                    priority='medium'
                )
                db.session.add(task)

        db.session.commit()

        resp = f"📝 Ponto registrado na reunião '{meeting.title}':\n   Tópico: {topic}"
        if decision:
            resp += f"\n   Decisão: {decision}"
        if responsible:
            resp += f"\n   Responsável: {responsible}"
        if deadline:
            resp += f"\n   Prazo: {deadline}"
        if responsible and deadline and meeting.project_id:
            resp += f"\n   ✅ Atividade criada automaticamente no projeto ID {meeting.project_id}."
        return resp
    except Exception as e:
        db.session.rollback()
        return f"Erro ao registrar ponto da reunião: {str(e)}"


@tool
def finish_meeting(meeting_id: int):
    """
    Encerra uma reunião em andamento e gera a Ata de Reunião (ATA) completa.
    Após encerrar, use 'send_meeting_minutes' para enviar a ATA aos participantes.
    :param meeting_id: ID da reunião a ser encerrada.
    """
    from models.meeting import Meeting
    import json
    from datetime import datetime

    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return f"Reunião ID {meeting_id} não encontrada."

        meeting.status = 'completed'
        db.session.commit()

        # Monta a ATA
        discussions = json.loads(meeting.discussions_json or "[]")
        activities = json.loads(meeting.activities_json or "[]")
        guests = json.loads(meeting.guests_json or "{}")

        ata_lines = [
            f"ATA DE REUNIÃO",
            f"={'='*50}",
            f"Título: {meeting.title}",
            f"Data: {meeting.actual_date or meeting.scheduled_date}",
            f"Horário: {meeting.actual_time or meeting.scheduled_time}",
            f"Participantes: {', '.join(guests.keys()) if guests else 'Não registrado'}",
            f"",
            f"PONTOS DISCUTIDOS:",
        ]
        for i, d in enumerate(discussions, 1):
            ata_lines.append(f"  {i}. {d.get('title', '')}")
            if d.get('decision'):
                ata_lines.append(f"     Decisão: {d['decision']}")
            if d.get('responsible'):
                ata_lines.append(f"     Responsável: {d['responsible']} | Prazo: {d.get('deadline', 'N/A')}")

        if activities:
            ata_lines += ["", "ATIVIDADES CRIADAS:"]
            for a in activities:
                ata_lines.append(f"  • [{a.get('responsible','?')}] {a.get('title','?')} — Prazo: {a.get('deadline','N/A')}")

        ata_text = "\n".join(ata_lines)
        meeting.meeting_notes = ata_text

        # ✅ ALINHAMENTO COM API OFICIAL (MeetingFinishResource):
        # Cria tarefa-resumo no projeto vinculado — idêntico ao comportamento da interface.
        if meeting.project_id:
            try:
                from models.project import ProjectTask
                task_desc = f"Atas da reunião (ID: {meeting.id})\n\n"
                if discussions:
                    task_desc += "Principais Deliberações:\n"
                    for d in discussions:
                        task_desc += f"- {d.get('title', 'Tópico')}: {d.get('decision', '')}\n"

                summary_task = ProjectTask(
                    project_id=meeting.project_id,
                    what=f"Resumo da Reunião: {meeting.title}",
                    how=task_desc,
                    status="completed",
                    due_date=datetime.utcnow().date(),
                    priority="low"
                )
                db.session.add(summary_task)
            except Exception:
                pass  # Não bloqueia o encerramento se houver erro na task-resumo

        db.session.commit()

        return (
            f"🏁 Reunião '{meeting.title}' ENCERRADA!\n\n"
            f"{ata_text}\n\n"
            f"Para enviar a ATA por e-mail/WhatsApp, diga:\n"
            f"'Sapiens, envie a ATA da reunião {meeting_id}'"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao encerrar reunião: {str(e)}"


@tool
def send_meeting_minutes(meeting_id: int, channel: str = "email"):
    """
    Envia a ATA (Ata de Reunião) para todos os participantes após o encerramento.
    :param meeting_id: ID da reunião já encerrada.
    :param channel: Canal de envio: 'email', 'whatsapp' ou 'ambos'. Padrão: 'email'
    """
    from models.meeting import Meeting
    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service
    import json

    try:
        meeting = Meeting.query.get(meeting_id)
        if not meeting:
            return f"Reunião ID {meeting_id} não encontrada."

        guests = json.loads(meeting.guests_json or "{}")
        ata = meeting.meeting_notes or "ATA não gerada. Encerre a reunião primeiro."

        email_guests = [g for g in guests.keys() if '@' in g]
        wa_guests = [v for v in guests.values() if v and '@' not in v]

        sent_email = sent_wa = 0

        if channel in ('email', 'ambos') and email_guests:
            ok = email_service.send_email(
                to_emails=email_guests,
                subject=f"ATA da Reunião: {meeting.title}",
                body=ata
            )
            if ok:
                sent_email = len(email_guests)

        if channel in ('whatsapp', 'ambos') and wa_guests:
            for phone in wa_guests:
                ok = whatsapp_service.send_message(phone, f"📋 *ATA DA REUNIÃO: {meeting.title}*\n\n{ata}")
                if ok:
                    sent_wa += 1

        return (
            f"📤 ATA da reunião '{meeting.title}' enviada!\n"
            f"   E-mails enviados: {sent_email}\n"
            f"   WhatsApps enviados: {sent_wa}"
        )
    except Exception as e:
        return f"Erro ao enviar ATA: {str(e)}"


# =============================================================================
# FASE 2: TOOLS DE GESTÃO DE TAREFAS
# =============================================================================

@tool
def get_tasks_today(scope: str = "me"):
    """
    Lista as atividades (tarefas e instâncias de processo) do usuário que vencem hoje ou estão atrasadas.
    Ideal para o briefing matinal e cobranças proativas.
    :param scope: 'me' para o usuário logado, 'team' para a equipe, 'company' para toda a empresa.
    """
    
    from datetime import date
    import json

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    today = date.today()
    today_str = today.isoformat()

    try:
        with db.engine.connect() as conn:
            from sqlalchemy import text as sqltext

            # Tarefas de Projetos vencendo hoje ou atrasadas
            q_tasks = sqltext("""
                SELECT pt.id, pt.what as title, pt.due_date, pt.status, pt.who as responsible,
                       p.name as project_name
                FROM project_tasks pt
                JOIN projects p ON p.id = pt.project_id
                WHERE p.company_id = :cid
                  AND pt.status NOT IN ('completed', 'cancelled')
                  AND pt.due_date <= :today
                ORDER BY pt.due_date ASC
            """)
            tasks = [dict(r._mapping) for r in conn.execute(q_tasks, {"cid": company_id, "today": today_str})]

            # Instâncias de Processos vencendo hoje ou atrasadas
            q_proc = sqltext("""
                SELECT pi.id, pr.name as title, pi.due_date, pi.status,
                       e.name as responsible
                FROM process_instances pi
                JOIN process_routines pr ON pr.id = pi.routine_id
                LEFT JOIN employees e ON e.id = pi.employee_id
                WHERE pi.company_id = :cid
                  AND pi.status NOT IN ('completed', 'cancelled')
                  AND pi.due_date <= :today
                ORDER BY pi.due_date ASC
            """)
            procs = [dict(r._mapping) for r in conn.execute(q_proc, {"cid": company_id, "today": today_str})]

        if not tasks and not procs:
            return f"🟢 Nenhuma tarefa vencendo hoje ({today_str}) ou atrasada. Ótimo!"

        result_lines = [f"📋 TAREFAS VENCENDO HOJE ({today_str}) E ATRASADAS:"]

        if tasks:
            result_lines.append("\n🗂️ Atividades de Projetos:")
            for t in tasks:
                emoji = "🔴" if str(t['due_date']) < today_str else "🟡"
                result_lines.append(
                    f"  {emoji} [{t['project_name']}] {t['title']} "
                    f"— Resp: {t['responsible'] or '?'} | Prazo: {t['due_date']}"
                )

        if procs:
            result_lines.append("\n⚙️ Instâncias de Processos:")
            for p in procs:
                emoji = "🔴" if str(p['due_date']) < today_str else "🟡"
                result_lines.append(
                    f"  {emoji} {p['title']} "
                    f"— Resp: {p['responsible'] or '?'} | Prazo: {p['due_date']}"
                )

        return sanitize_output("\n".join(result_lines))
    except Exception as e:
        return f"Erro ao buscar tarefas do dia: {str(e)}"


@tool
def complete_task(task_type: str, task_id: int, evidence_description: str = None, completion_date: str = None, notification_email: str = None, notification_whatsapp: str = None):
    """
    Marca uma tarefa de projeto ou instância de processo como CONCLUÍDA e opcionalmente notifica interessados.
    :param task_type: Tipo da tarefa: 'project_task' ou 'process_instance'
    :param task_id: ID da tarefa ou instância a ser concluída.
    :param evidence_description: Descrição do que foi feito como evidência/observação. Ex: 'Relatório enviado ao cliente via e-mail'
    :param completion_date: Opcional data da conclusão no formato YYYY-MM-DD. Se omitida, usa HOJE.
    :param notification_email: Opcional e-mail para notificar sobre a conclusão.
    :param notification_whatsapp: Opcional número de WhatsApp (com DDD) para notificar.
    """
    from datetime import datetime

    try:
        # Resolve a data de conclusão
        final_date = None
        if completion_date:
            try:
                final_date = datetime.strptime(completion_date, '%Y-%m-%d').date()
            except ValueError:
                return f"Erro: Formato de data inválido '{completion_date}'. Use YYYY-MM-DD."
        else:
            final_date = datetime.utcnow().date()

        if task_type == 'project_task':
            from models.project import ProjectTask
            task = ProjectTask.query.get(task_id)
            if not task:
                return f"Tarefa de projeto ID {task_id} não encontrada."
            
            task.status = 'completed'
            task.stage = 'completed'  # Importante alinhar ambos os campos de status
            task.completion_date = final_date
            
            if evidence_description:
                task.how = (task.how or "") + f"\n\n✅ EVIDÊNCIA DE CONCLUSÃO ({final_date}): {evidence_description}"
            
            db.session.commit()
            
            # Atualiza o progresso do projeto pai
            if task.project:
                try:
                    task.project.update_progress()
                    db.session.commit()
                except:
                    pass

            # 1. Notificações (@ARQUITETO)
            notif_msg = []
            if notification_email:
                from services.email_service import email_service
                body = f"A tarefa '{task.what}' do projeto '{task.project.name}' foi CONCLUÍDA.\nEvidência: {evidence_description or 'N/A'}"
                email_service.send_email(to_emails=[notification_email], subject="Notificação de Conclusão - Gestão Versus", body=body)
                notif_msg.append(f"e-mail enviado para {notification_email}")
            
            if notification_whatsapp:
                from services.whatsapp_service import whatsapp_service
                wa_body = f"✅ *Conclusão de Tarefa*\n\nAtividade: {task.what}\nProjeto: {task.project.name}\nStatus: CONCLUÍDA\nEvidência: {evidence_description or 'N/A'}"
                whatsapp_service.send_message(notification_whatsapp, wa_body)
                notif_msg.append(f"WhatsApp enviado para {notification_whatsapp}")

            notif_status = f" | Notificações: {', '.join(notif_msg)}" if notif_msg else ""

            return (
                f"✅ Tarefa '{task.what}' (ID {task_id}) marcada como concluída!\n"
                f"   Data registrada: {final_date}\n"
                f"   Projeto ID: {task.project_id}\n"
                f"   Evidência registrada: {evidence_description or 'Não informada'}"
                f"{notif_status}"
            )

        elif task_type == 'process_instance':
            from models.process import ProcessInstance
            instance = ProcessInstance.query.get(task_id)
            if not instance:
                return f"Instância de processo ID {task_id} não encontrada."
            
            instance.status = 'completed'
            instance.completed_at = datetime.combine(final_date, datetime.min.time())
            instance.actual_end_date = final_date
            
            if evidence_description:
                instance.notes = (instance.notes or "") + f"\n\n✅ EVIDÊNCIA ({final_date}): {evidence_description}"
            
            db.session.commit()
            return (
                f"✅ Instância de processo ID {task_id} concluída!\n"
                f"   Data registrada: {final_date}\n"
                f"   Evidência registrada: {evidence_description or 'Não informada'}"
            )
        else:
            return f"Tipo de tarefa inválido. Use 'project_task' ou 'process_instance'."
    except Exception as e:
        db.session.rollback()
        return f"Erro ao concluir tarefa: {str(e)}"


@tool
def log_work_hours(task_type: str, task_id: int, hours: float, description: str, work_date: str = None):
    """
    Registra horas trabalhadas em uma tarefa de projeto ou instância de processo.
    :param task_type: 'project_task' ou 'process_instance'
    :param task_id: ID da tarefa ou instância.
    :param hours: Número de horas trabalhadas. Ex: 2.5 (2 horas e 30 minutos)
    :param description: O que foi executado. Ex: 'Elaboração do relatório de vendas Q1'
    :param work_date: Data do trabalho no formato YYYY-MM-DD. Se omitido, usa hoje.
    """
    from datetime import datetime, date
    

    try:
        work_dt = datetime.strptime(work_date, '%Y-%m-%d').date() if work_date else date.today()

        user_id = get_active_user_id()
        company_id = get_active_company_id()

        if task_type == 'project_task':
            from models.project import ProjectTask
            from models.activity_work_log import ActivityWorkLog

            task = ProjectTask.query.get(task_id)
            if not task:
                return f"Tarefa de projeto ID {task_id} não encontrada."

            log = ActivityWorkLog(
                project_task_id=task_id,
                user_id=user_id,
                company_id=int(company_id) if company_id else None,
                hours_worked=hours,
                description=description,
                work_date=work_dt,
                created_at=datetime.utcnow()
            )
            db.session.add(log)

            # Atualiza status para in_progress se estava not_started
            if task.status == 'not_started':
                task.status = 'in_progress'

            db.session.commit()
            return (
                f"⏱️ {hours}h registradas na tarefa '{task.what}'!\n"
                f"   Data: {work_dt} | Descrição: {description}"
            )

        elif task_type == 'process_instance':
            from models.process import ProcessInstance
            from models.activity_work_log import ActivityWorkLog

            instance = ProcessInstance.query.get(task_id)
            if not instance:
                return f"Instância de processo ID {task_id} não encontrada."

            log = ActivityWorkLog(
                process_instance_id=task_id,
                user_id=user_id,
                company_id=int(company_id) if company_id else None,
                hours_worked=hours,
                description=description,
                work_date=work_dt,
                created_at=datetime.utcnow()
            )
            db.session.add(log)

            if instance.status == 'pending':
                instance.status = 'in_progress'
            if not instance.worked_hours:
                instance.worked_hours = 0
            instance.worked_hours = float(instance.worked_hours) + hours

            db.session.commit()
            return (
                f"⏱️ {hours}h registradas na instância de processo ID {task_id}!\n"
                f"   Data: {work_dt} | Descrição: {description}"
            )

        return "Tipo de tarefa inválido. Use 'project_task' ou 'process_instance'."
    except Exception as e:
        db.session.rollback()
        return f"Erro ao registrar horas: {str(e)}"


@tool
def request_deadline_extension(task_type: str, task_id: int, new_deadline: str, reason: str):
    """
    Solicita ao superior hierárquico o adiamento do prazo de uma tarefa.
    O Sapiens pausará o fluxo, notificará o superior e aguardará aprovação antes de alterar o prazo.
    :param task_type: 'project_task' ou 'process_instance'
    :param task_id: ID da tarefa cuja data precisa ser alterada.
    :param new_deadline: Nova data proposta no formato YYYY-MM-DD. Ex: '2026-03-15'
    :param reason: Motivo do adiamento. Ex: 'Cliente solicitou revisão adicional do escopo'
    """
    
    from models.agent_action import AgentAction
    from services.whatsapp_service import whatsapp_service
    from services.email_service import email_service
    import json

    company_id = get_active_company_id()

    try:
        # Busca a tarefa
        task_name = f"Tarefa ID {task_id}"
        current_deadline = "N/A"
        
        user = get_active_user()
        requester_name = user.name if user else "Usuário"

        if task_type == 'project_task':
            from models.project import ProjectTask
            task = ProjectTask.query.get(task_id)
            if task:
                task_name = task.what
                current_deadline = str(task.due_date) if task.due_date else "Sem prazo"
        elif task_type == 'process_instance':
            from models.process import ProcessInstance
            inst = ProcessInstance.query.get(task_id)
            if inst:
                current_deadline = str(inst.due_date) if inst.due_date else "Sem prazo"

        # Cria ticket de aprovação no AgentAction (Human-in-the-loop)
        action = AgentAction(
            type='approval_request',
            status='pending',
            requesting_agent='sapiens',
            handling_agent='operations',
            title=f'Solicitação de Adiamento: {task_name}',
            description=(
                f"Solicitante: {requester_name}\n"
                f"Tarefa: {task_name} (ID {task_id}, tipo: {task_type})\n"
                f"Prazo Atual: {current_deadline}\n"
                f"Novo Prazo Solicitado: {new_deadline}\n"
                f"Motivo: {reason}"
            ),
            payload={
                "task_type": task_type,
                "task_id": task_id,
                "new_deadline": new_deadline,
                "reason": reason,
                "requester": requester_name
            },
            company_id=int(company_id) if company_id else None,
            user_id=get_active_user_id()
        )
        db.session.add(action)
        db.session.commit()

        # Notifica o superior (busca admin/gestor da empresa)
        from models.employee import Employee
        from models.user import User
        managers = (
            db.session.query(User)
            .join(Employee, Employee.user_id == User.id)
            .filter(Employee.company_id == int(company_id), User.role.in_(['admin', 'client']))
            .all()
        ) if company_id else []

        wa_sent = 0
        for mgr in managers:
            if mgr.whatsapp:
                msg = (
                    f"⚠️ *Solicitação de Adiamento de Prazo* (Ticket #{action.id})\n\n"
                    f"📋 Tarefa: *{task_name}*\n"
                    f"👤 Solicitante: {requester_name}\n"
                    f"📅 Prazo Atual: {current_deadline}\n"
                    f"📅 Novo Prazo Pedido: *{new_deadline}*\n"
                    f"💬 Motivo: {reason}\n\n"
                    f"Responda 'APROVAR {action.id}' ou 'RECUSAR {action.id}' para o Sapiens processar."
                )
                whatsapp_service.send_message(mgr.whatsapp, msg)
                wa_sent += 1
            if mgr.email:
                email_service.send_email(
                    to_emails=[mgr.email],
                    subject=f"[Ação Necessária] Adiamento de Prazo: {task_name}",
                    body=(
                        f"Solicitante: {requester_name}\n"
                        f"Tarefa: {task_name}\n"
                        f"Prazo atual: {current_deadline} → Novo prazo: {new_deadline}\n"
                        f"Motivo: {reason}\n\n"
                        f"Acesse o sistema para aprovar ou recusar. Ticket #{action.id}"
                    )
                )

        return (
            f"🕐 Solicitação de adiamento enviada ao seu superior! (Ticket #{action.id})\n"
            f"   Tarefa: {task_name}\n"
            f"   Prazo atual: {current_deadline} → Solicitado: {new_deadline}\n"
            f"   Motivo: {reason}\n"
            f"   {wa_sent} gestor(es) notificado(s) via WhatsApp.\n"
            f"   Aguarde a resposta. Assim que aprovado, o prazo será alterado automaticamente no sistema."
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao solicitar adiamento: {str(e)}"


@tool
def list_team_workload():
    """
    Analisa a carga de trabalho de todos os colaboradores da empresa.
    Identifica quem está sobrecarregado, ocioso ou em equilíbrio, com base nas horas
    disponíveis por semana versus tarefas abertas estimadas.
    Ideal para o supervisor identificar necessidade de redistribuição de tarefas.
    """
    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        from sqlalchemy import text as sqltext

        with db.engine.connect() as conn:
            # Carga de tarefas abertas por colaborador (por nome no campo 'who')
            q = sqltext("""
                SELECT
                    e.name AS collaborator,
                    e.weekly_hours AS capacity_hours,
                    COUNT(pt.id) FILTER (WHERE pt.status NOT IN ('completed','cancelled')) AS open_tasks,
                    COUNT(pi.id) FILTER (WHERE pi.status NOT IN ('completed','cancelled')) AS open_instances
                FROM employees e
                LEFT JOIN project_tasks pt ON pt.who = e.name
                LEFT JOIN process_instances pi ON pi.employee_id = e.id
                WHERE e.company_id = :cid AND e.status = 'active'
                GROUP BY e.id, e.name, e.weekly_hours
                ORDER BY (open_tasks + open_instances) DESC
            """)
            rows = [dict(r._mapping) for r in conn.execute(q, {"cid": company_id})]

        if not rows:
            return "Nenhum colaborador ativo encontrado na empresa."

        lines = ["👥 ANÁLISE DE CARGA DA EQUIPE:", ""]
        for r in rows:
            cap = float(r['capacity_hours']) if r['capacity_hours'] else 40.0
            total_tasks = (r['open_tasks'] or 0) + (r['open_instances'] or 0)
            # Estimativa: cada tarefa = 2h médias
            estimated_hours = total_tasks * 2.0
            pct = (estimated_hours / cap * 100) if cap > 0 else 0

            if pct >= 100:
                emoji = "🔴 Sobrecarregado"
            elif pct >= 70:
                emoji = "🟡 Atenção"
            else:
                emoji = "🟢 OK"

            lines.append(
                f"  {emoji} | {r['collaborator']}: "
                f"{total_tasks} tarefas abertas (~{estimated_hours:.0f}h estimadas) "
                f"de {cap:.0f}h/semana disponíveis ({pct:.0f}%)"
            )

        return sanitize_output("\n".join(lines))
    except Exception as e:
        return f"Erro ao analisar carga da equipe: {str(e)}"


# =============================================================================
# LISTA DE FERRAMENTAS EXPORTADAS (FASE 1 + FASE 2)
# =============================================================================
tools = [
    # Fase 1 — Core Intelligence
    consult_rules,
    query_database,
    escalate_technical_issue,
    # Fase 1 — Process Management
    create_process_area,
    create_macro_process,
    create_process,
    update_company_status,
    list_process_hierarchy,
    # Fase 1 — Planning
    list_plans,
    get_plan_diagnostics,
    update_plan_section,
    # Fase 1 — My Work & Users
    get_my_work,
    list_my_companies,
    list_system_users,
    register_system_user,
    update_user_contacts,
    # Fase 2 — Meetings
    schedule_meeting,
    start_meeting,
    log_meeting_discussion,
    finish_meeting,
    send_meeting_minutes,
    # Fase 2 — Task Management
    get_tasks_today,
    complete_task,
    log_work_hours,
    request_deadline_extension,
    list_team_workload,
]
