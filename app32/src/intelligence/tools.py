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
import logging
from models import db
from src.intelligence.rag import knowledge_base
from sqlalchemy import text
import json
import os
import re
import unicodedata

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


def _normalize_company_text(value: str) -> str:
    """
    Normaliza texto para matching tolerante (acento, pontuacao e caixa).
    """
    text_value = (value or "").strip().lower()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = re.sub(r"[^a-z0-9]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _rank_companies_by_term(companies, search_term: str):
    """
    Classifica empresas por aderencia ao termo de busca (nome/prefixo combinado).
    """
    if not search_term:
        return list(companies)

    search_norm = _normalize_company_text(search_term)
    if not search_norm:
        return list(companies)

    search_tokens = [t for t in search_norm.split(" ") if len(t) >= 2]
    ranked = []

    for company in companies:
        code_norm = _normalize_company_text(company.client_code or "")
        name_norm = _normalize_company_text(company.name or "")
        legal_norm = _normalize_company_text(getattr(company, "legal_name", "") or "")
        haystack = _normalize_company_text(f"{code_norm} {name_norm} {legal_norm}")

        score = 0
        if search_norm in haystack:
            score += 6
        if code_norm and search_norm == code_norm:
            score += 10
        if name_norm and search_norm == name_norm:
            score += 8
        if code_norm and code_norm in search_tokens:
            score += 4

        if search_tokens:
            token_hits = sum(1 for token in search_tokens if token in haystack)
            coverage = token_hits / len(search_tokens)
            score += int(coverage * 5)
        else:
            coverage = 0

        if score >= 6 or coverage >= 0.75:
            ranked.append((score, company))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in ranked]

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

def _get_meeting_in_active_company(meeting_id: int):
    """Recupera reunião estritamente no contexto da empresa ativa."""
    from models.meeting import Meeting

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    meeting = Meeting.query.filter_by(id=meeting_id, company_id=int(company_id)).first()
    if not meeting:
        return None, f"Reunião ID {meeting_id} não encontrada na empresa ativa."

    return meeting, None

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
    Automaticamente cria uma tarefa de Intervenção para o Líder do Squad no projeto da Engenharia.
    """
    def _normalize_issue_text(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip())

    def _build_technical_issue_title(error_text: str, issue_context: str) -> str:
        combined = _normalize_issue_text(f"{error_text} {issue_context}").lower()

        signatures = [
            (
                ("illegalstatechangeerror", "transaction is closed", "this transaction is closed"),
                "[BUG][SQLALCHEMY_TX] Transacao fechada ao concluir atividade",
            ),
            (
                ("relation", "does not exist"),
                "[BUG][SQL] Relacao inexistente em consulta operacional",
            ),
            (
                ("column", "does not exist"),
                "[BUG][SQL] Coluna inexistente em consulta operacional",
            ),
            (
                ("jinja", "undefined"),
                "[BUG][JINJA] Variavel indefinida em renderizacao",
            ),
        ]

        for markers, title in signatures:
            if all(marker in combined for marker in markers):
                return title

        compact_error = _normalize_issue_text(error_text)
        if compact_error:
            return f"[BUG] {compact_error[:120]}"
        return "[BUG] Erro tecnico detectado automaticamente"

    try:
        from datetime import datetime
        
        # Chama a nossa tool de intervenção da Squad internamente
        result = squad_create_intervention.invoke({
            "title": _build_technical_issue_title(error_description, context),
            "due_date": str(datetime.utcnow().date()),
            "how": f"Contexto do erro e logs para análise investigativa.",
            "notes": f"Descrição do Erro:\n{error_description}\n\nContexto da IA:\n{context}",
            "assignee_name": "Agente Sapiens"
        })
        
        return f"Escalonamento realizado com sucesso. A tarefa foi criada no Kanban da Squad de Engenharia: {result}"
    except Exception as e:
        return f"Erro ao processar escalonamento para a Squad: {str(e)}"

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

        companies = query.all()

        if search_term:
            companies = _rank_companies_by_term(companies, search_term)

        if not companies:
            if search_term:
                return f"Nenhuma empresa encontrada para o termo '{search_term}'. Use um prefixo (ex: AA) ou parte do nome."
            return "Nenhuma empresa vinculada ao seu usuário."
            
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
    from sqlalchemy import or_
    from models.user import User
    from models.employee import Employee
    from models.company import Company
    from models.project import ProjectTask, Project
    from models.process import ProcessInstance

    user_id = get_active_user_id()
    print(f"--- TOOL [get_my_work]: user_id={user_id} | scope={scope} | ctx_user={active_user_id_ctx.get()} ---")

    if not user_id:
        return "Erro: Usuario nao autenticado."

    try:
        from datetime import datetime as dt

        user = db.session.get(User, user_id)
        if not user:
            return "Erro: Usuario nao encontrado."

        role = getattr(user, "role", "collaborator")
        scope = (scope or "me").strip().lower()
        if scope not in ("me", "team", "company"):
            scope = "me"

        # Vínculos do usuário
        user_emps = Employee.query.filter_by(user_id=user_id, status="active").all()
        if not user_emps:
            user_emps = Employee.query.filter_by(user_id=user_id).all()

        user_employee_ids = [e.id for e in user_emps]
        user_company_ids = sorted({e.company_id for e in user_emps if e.company_id})

        # Empresas acessíveis
        if role == "admin":
            accessible_companies = Company.query.filter_by(is_active=True).order_by(Company.id.asc()).all()
        else:
            if not user_company_ids:
                return "Nenhuma empresa acessivel encontrada para este usuario."
            accessible_companies = (
                Company.query.filter(Company.id.in_(user_company_ids))
                .order_by(Company.id.asc())
                .all()
            )

        accessible_company_ids = [c.id for c in accessible_companies]
        if not accessible_company_ids:
            return "Nenhuma empresa acessivel encontrada para este usuario."

        # Filtro explícito de company_ids
        if company_ids:
            requested_ids = [int(i.strip()) for i in company_ids.split(",") if i.strip().isdigit()]
            effective_company_ids = [cid for cid in requested_ids if cid in accessible_company_ids]
        else:
            effective_company_ids = list(accessible_company_ids)

        # Detecta empresa citada no texto livre e restringe o filtro por ela.
        matched_companies = []
        if search_term:
            text = search_term.strip()
            lower = text.lower()
            company_fragment = text
            for marker in ("na empresa", "da empresa", "empresa", "no cliente", "cliente"):
                idx = lower.find(marker)
                if idx >= 0:
                    company_fragment = text[idx + len(marker):].strip(" :-,.!?")
                    break

            matched_companies = _rank_companies_by_term(accessible_companies, company_fragment)
            if not matched_companies and company_fragment != text:
                matched_companies = _rank_companies_by_term(accessible_companies, text)

            if matched_companies:
                effective_company_ids = [c.id for c in matched_companies]

        if not effective_company_ids:
            return "Nenhuma empresa acessivel encontrada para o filtro informado."

        # Escopo (me/team) por colaboradores
        team_employee_ids = []
        if scope in ("me", "team"):
            team_rows = (
                Employee.query.filter(
                    Employee.company_id.in_(effective_company_ids),
                    Employee.status == "active",
                    Employee.id.isnot(None),
                )
                .order_by(Employee.id.asc())
                .all()
            )
            team_employee_ids = [e.id for e in team_rows]

        if scope == "me":
            target_employee_ids = set(user_employee_ids)
        elif scope == "team":
            target_employee_ids = set(team_employee_ids) - set(user_employee_ids)
        else:
            target_employee_ids = set()

        # Evita filtrar por texto quando a busca já virou filtro de empresa.
        apply_text_search = bool(search_term and not matched_companies)
        pattern = f"%{search_term.strip()}%" if apply_text_search else None

        # --- Projeto: project_tasks ---
        task_rows = (
            db.session.query(ProjectTask, Project, Company)
            .join(Project, Project.id == ProjectTask.project_id)
            .join(Company, Company.id == Project.company_id)
            .filter(Project.company_id.in_(effective_company_ids))
            .filter(ProjectTask.status.notin_(["completed", "done", "cancelled"]))
            .filter(ProjectTask.stage != "completed")
        )

        if scope == "me":
            if target_employee_ids:
                task_rows = task_rows.filter(ProjectTask.employee_id.in_(list(target_employee_ids)))
            elif user.name:
                task_rows = task_rows.filter(ProjectTask.who.ilike(f"%{user.name}%"))
        elif scope == "team":
            if target_employee_ids:
                task_rows = task_rows.filter(ProjectTask.employee_id.in_(list(target_employee_ids)))
            else:
                task_rows = task_rows.filter(ProjectTask.id == -1)

        if pattern:
            task_rows = task_rows.filter(
                or_(
                    ProjectTask.what.ilike(pattern),
                    ProjectTask.how.ilike(pattern),
                    ProjectTask.notes.ilike(pattern),
                    Project.name.ilike(pattern),
                    Company.name.ilike(pattern),
                    Company.client_code.ilike(pattern),
                )
            )

        task_rows = task_rows.order_by(ProjectTask.due_date.asc().nullslast(), ProjectTask.id.asc()).limit(300).all()

        # --- Processo: process_instances ---
        instance_rows = (
            db.session.query(ProcessInstance, Company)
            .join(Company, Company.id == ProcessInstance.company_id)
            .filter(ProcessInstance.company_id.in_(effective_company_ids))
            .filter(ProcessInstance.status.notin_(["completed", "done", "cancelled"]))
        )
        if pattern:
            instance_rows = instance_rows.filter(
                or_(
                    ProcessInstance.title.ilike(pattern),
                    ProcessInstance.description.ilike(pattern),
                    Company.name.ilike(pattern),
                    Company.client_code.ilike(pattern),
                )
            )

        instance_rows = instance_rows.order_by(
            ProcessInstance.due_date.asc().nullslast(), ProcessInstance.id.asc()
        ).limit(300).all()

        def _instance_belongs_to_scope(instance_obj, employee_ids):
            if not employee_ids:
                return False

            assigned_ids = {
                instance_obj.owner_employee_id,
                instance_obj.responsible_id,
                instance_obj.executor_id,
            }
            if any(aid in employee_ids for aid in assigned_ids if aid):
                return True

            collaborators = instance_obj.collaborators_json or []
            for c in collaborators:
                if not isinstance(c, dict):
                    continue
                cid = c.get("id") or c.get("employee_id")
                try:
                    if cid and int(cid) in employee_ids:
                        return True
                except Exception:
                    continue
            return False

        activities = []

        # Mapa de colaboradores para nomes (usado em instâncias de processo).
        employee_ids_in_instances = set()
        for instance, _company in instance_rows:
            for emp_id in (
                getattr(instance, "owner_employee_id", None),
                getattr(instance, "responsible_id", None),
                getattr(instance, "executor_id", None),
            ):
                if emp_id:
                    employee_ids_in_instances.add(emp_id)

        employee_name_map = {}
        if employee_ids_in_instances:
            rows = (
                Employee.query.filter(Employee.id.in_(list(employee_ids_in_instances)))
                .with_entities(Employee.id, Employee.name)
                .all()
            )
            employee_name_map = {row[0]: row[1] for row in rows}

        for task, project, company in task_rows:
            company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
            project_code = project.code if hasattr(project, "code") else f"{company.client_code or 'CP'}.J.{project.id}"
            task_suffix = f"{int(task.id):02d}" if str(task.id).isdigit() else str(task.id)
            activity_code = f"{project_code}.{task_suffix}"
            activities.append({
                "type": "projeto",
                "title": task.what,
                "project_name": project.name,
                "project_code": project_code,
                "activity_code": activity_code,
                "responsible_name": (task.employee_name or "Nao definido"),
                "company_name": company_label,
                "id": task.id,
                "deadline": task.due_date,
                "status": task.status or task.stage or "planned",
            })

        for instance, company in instance_rows:
            if scope in ("me", "team"):
                if not _instance_belongs_to_scope(instance, target_employee_ids):
                    continue
            company_label = f"{company.client_code} - {company.name}" if company.client_code else company.name
            process_code = (
                instance.instance_code
                or (instance.process_rel.code if getattr(instance, "process_rel", None) else None)
                or f"{company.client_code or 'CP'}.P.{instance.id}"
            )
            process_owner_name = (
                (getattr(instance, "process_rel", None) and getattr(instance.process_rel, "responsible", None))
                or employee_name_map.get(getattr(instance, "owner_employee_id", None))
                or employee_name_map.get(getattr(instance, "responsible_id", None))
                or "Nao definido"
            )
            activities.append({
                "type": "processo",
                "title": instance.title,
                "project_name": getattr(instance.process_rel, "name", None),
                "project_code": process_code,
                "activity_code": process_code,
                "process_owner_name": process_owner_name,
                "company_name": company_label,
                "id": instance.id,
                "deadline": instance.due_date,
                "status": instance.status or "pending",
            })

        def _deadline_sort_value(value):
            if value is None:
                return "9999-12-31"
            if isinstance(value, dt):
                return value.date().isoformat()
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)

        activities.sort(
            key=lambda a: (
                a["deadline"] is None,
                _deadline_sort_value(a["deadline"]),
                a["id"],
            )
        )

        if not activities:
            if matched_companies:
                chosen = matched_companies[0]
                label = f"{chosen.client_code} - {chosen.name}" if chosen.client_code else chosen.name
                return f"Nenhuma atividade pendente encontrada para a empresa '{label}'."
            return f"Nenhuma atividade pendente encontrada no escopo '{scope}' para as empresas selecionadas."

        summary = []
        for item in activities:
            deadline_obj = item["deadline"]
            if isinstance(deadline_obj, dt):
                deadline = deadline_obj.date().isoformat()
            elif hasattr(deadline_obj, "isoformat"):
                deadline = deadline_obj.isoformat()
            else:
                deadline = deadline_obj or "Sem prazo"
            if item["type"] == "projeto":
                summary.append(
                    f"- [PROJETO] {item.get('project_code') or '-'} - {item.get('project_name') or '-'} "
                    f"| [ATIVIDADE] {item.get('activity_code') or '-'} - {item['title']} "
                    f"| Responsavel: {item.get('responsible_name') or 'Nao definido'} "
                    f"| Empresa: {item['company_name']} | ID: {item['id']} | Prazo: {deadline} | Status: {item['status']}"
                )
            else:
                summary.append(
                    f"- [PROCESSO] {item.get('project_code') or '-'} - {item['title']} "
                    f"| [ATIVIDADE] {item.get('activity_code') or '-'} - {item['title']} "
                    f"| Dono do Processo: {item.get('process_owner_name') or 'Nao definido'} "
                    f"| Empresa: {item['company_name']} | ID: {item['id']} | Prazo: {deadline} | Status: {item['status']}"
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
    :param range: 'today', 'week', 'month', 'next_15_days' ou período customizado (DD/MM/AAAA a DD/MM/AAAA).
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
    from models.project import Project
    from datetime import datetime

    try:
        meeting, error_message = _get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

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
    from models.project import ProjectTask
    import json

    try:
        meeting, error_message = _get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

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
    import json
    from datetime import datetime

    try:
        meeting, error_message = _get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

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
    from services.email_service import email_service
    from services.whatsapp_service import whatsapp_service
    import json

    try:
        meeting, error_message = _get_meeting_in_active_company(meeting_id)
        if error_message:
            return error_message

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
    from models.employee import Employee
    from models.process import Process, ProcessInstance, ProcessRoutine
    from models.project import Project, ProjectTask
    from sqlalchemy import func

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    today = date.today()
    today_str = today.isoformat()

    try:
        tasks = [
            dict(row._mapping)
            for row in (
                db.session.query(
                    ProjectTask.id,
                    ProjectTask.what.label("title"),
                    ProjectTask.due_date,
                    ProjectTask.status,
                    ProjectTask.who.label("responsible"),
                    Project.name.label("project_name"),
                )
                .join(Project, Project.id == ProjectTask.project_id)
                .filter(Project.company_id == company_id)
                .filter(ProjectTask.status.notin_(["completed", "cancelled"]))
                .filter(ProjectTask.due_date <= today)
                .order_by(ProjectTask.due_date.asc())
                .all()
            )
        ]

        responsible_employee_id = func.coalesce(
            ProcessInstance.responsible_id,
            ProcessInstance.executor_id,
            ProcessInstance.owner_employee_id,
        )
        process_title = func.coalesce(
            ProcessRoutine.name,
            Process.name,
            ProcessInstance.title,
        )

        procs = [
            dict(row._mapping)
            for row in (
                db.session.query(
                    ProcessInstance.id,
                    process_title.label("title"),
                    ProcessInstance.due_date,
                    ProcessInstance.status,
                    Employee.name.label("responsible"),
                )
                .outerjoin(ProcessRoutine, ProcessRoutine.id == ProcessInstance.routine_id)
                .outerjoin(Process, Process.id == ProcessInstance.process_id)
                .outerjoin(Employee, Employee.id == responsible_employee_id)
                .filter(ProcessInstance.company_id == company_id)
                .filter(ProcessInstance.status.notin_(["completed", "cancelled"]))
                .filter(ProcessInstance.due_date <= today)
                .order_by(ProcessInstance.due_date.asc())
                .all()
            )
        ]

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
def create_project_task(project_code: str, task_name: str, responsible_name: str = None, due_date: str = None, description: str = None, priority: str = "normal", notes: str = None):
    """
    Cria uma nova atividade em um projeto existente, respeitando o contexto multiempresa.
    :param project_code: Código do projeto no formato EMPRESA.J.ID. Ex: 'AB.J.17'
    :param task_name: Nome da atividade. Ex: 'Validar fluxo de WhatsApp'
    :param responsible_name: Opcional nome do responsável. Se omitido, usa o usuário atual.
    :param due_date: Opcional prazo no formato YYYY-MM-DD ou DD/MM/YYYY.
    :param description: Opcional descrição/como executar.
    :param priority: Prioridade da atividade. Ex: 'normal', 'high'
    :param notes: Observações adicionais.
    """
    from models.employee import Employee
    from models.user import User
    from services.project_task_service import ProjectTaskService

    user_id = get_active_user_id()
    if not user_id:
        return "Erro: Usuario nao autenticado."

    active_company_id = get_active_company_id()
    allowed_company_ids = [active_company_id] if active_company_id else []

    if not allowed_company_ids:
        user = User.query.get(user_id)
        if user and str(getattr(user, "role", "")).lower() == "admin":
            allowed_company_ids = None
        else:
            allowed_company_ids = [
                int(emp.company_id)
                for emp in Employee.query.filter(Employee.user_id == user_id).all()
                if getattr(emp, "company_id", None)
            ]
            if not allowed_company_ids:
                return "Erro: Nenhuma empresa vinculada ao usuario para criar a atividade."

    result, error = ProjectTaskService.create_project_task(
        project_code=project_code,
        task_name=task_name,
        user_id=user_id,
        allowed_company_ids=allowed_company_ids,
        responsible_name=responsible_name,
        due_date=due_date,
        description=description,
        priority=priority,
        notes=notes,
    )
    if error:
        return sanitize_output(error)
    if not result:
        return "Erro: Nao foi possivel criar a atividade de projeto."

    task = result["task"]
    project = result["project"]
    responsible = result.get("responsible_name") or "Nao informado"
    project_code_label = project.code if getattr(project, "code", None) else project_code
    activity_code = task.code if getattr(task, "code", None) else f"{project_code_label}.{task.id}"

    return sanitize_output(
        f"Atividade '{task.what}' cadastrada com sucesso no projeto '{project_code_label} - {project.name}'.\n"
        f"Codigo da Atividade: {activity_code}\n"
        f"Responsavel: {responsible}"
    )


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
    from zoneinfo import ZoneInfo

    try:
        # Resolve a data de conclusão
        final_date = None
        if completion_date:
            try:
                final_date = datetime.strptime(completion_date, '%Y-%m-%d').date()
            except ValueError:
                return f"Erro: Formato de data inválido '{completion_date}'. Use YYYY-MM-DD."
        else:
            tz_name = os.environ.get("APP_TIMEZONE") or "America/Bahia"
            final_date = datetime.now(ZoneInfo(tz_name)).date()

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
            
            # Atualiza o progresso do projeto pai no mesmo ciclo transacional
            if task.project:
                try:
                    task.project.update_progress()
                except Exception:
                    db.session.rollback()
                    return "Erro ao concluir tarefa: falha ao atualizar o progresso do projeto."

            db.session.commit()

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
    from decimal import Decimal
    from sqlalchemy import func

    try:
        work_dt = datetime.strptime(work_date, '%Y-%m-%d').date() if work_date else date.today()
        if hours <= 0:
            return "Erro: informe uma quantidade de horas maior que zero."

        user_id = get_active_user_id()
        company_id = get_active_company_id()
        if not user_id:
            return "Erro: usuário não autenticado."

        if task_type == 'project_task':
            from models.project import ProjectTask, ProjectActivityCollaborator, ProjectTaskHoursSummary
            from models.activity_work_log import ActivityWorkLog
            from models.employee import Employee

            task = db.session.get(ProjectTask, task_id)
            if not task:
                return f"Tarefa de projeto ID {task_id} não encontrada."
            if not task.project:
                return f"Erro: a tarefa {task_id} não possui projeto vinculado."
            if company_id and int(company_id) != int(task.project.company_id):
                return "Erro: a tarefa informada não pertence à empresa ativa do contexto."

            employee = (
                Employee.query.filter(
                    Employee.user_id == user_id,
                    Employee.company_id == task.project.company_id,
                    Employee.status == 'active',
                )
                .order_by(Employee.id.asc())
                .first()
            )
            if not employee:
                return "Erro: não encontrei um colaborador ativo vinculado ao usuário na empresa desta tarefa."

            log = ActivityWorkLog(
                activity_type='project',
                activity_id=task_id,
                employee_id=employee.id,
                employee_name=employee.name,
                hours_worked=Decimal(str(hours)),
                description=description,
                work_date=work_dt,
                created_at=datetime.utcnow()
            )
            db.session.add(log)

            collaborator = ProjectActivityCollaborator.query.filter(
                ProjectActivityCollaborator.activity_id == task_id,
                ProjectActivityCollaborator.employee_id == employee.id,
                ProjectActivityCollaborator.is_deleted.is_(False),
            ).first()
            if not collaborator:
                collaborator = ProjectActivityCollaborator(
                    activity_id=task_id,
                    employee_id=employee.id,
                    role='executor',
                    estimated_hours=Decimal('0'),
                    worked_hours=Decimal('0'),
                    notes='Criado automaticamente via log_work_hours.',
                )
                db.session.add(collaborator)
            collaborator.worked_hours = Decimal(str(collaborator.worked_hours or 0)) + Decimal(str(hours))

            # Atualiza status para in_progress quando ainda nao iniciou de fato
            if task.status in (None, '', 'not_started', 'planned'):
                task.status = 'in_progress'
            if task.stage in (None, '', 'inbox', 'todo', 'planned'):
                task.stage = 'executing'

            db.session.flush()
            total_hours = (
                db.session.query(func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0))
                .filter(
                    ActivityWorkLog.activity_type == 'project',
                    ActivityWorkLog.activity_id == task_id,
                )
                .scalar()
            ) or 0
            task.worked_hours = total_hours

            summary = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
            if not summary:
                summary = ProjectTaskHoursSummary(
                    task_id=task_id,
                    total_estimated_hours=task.estimated_hours or Decimal('0'),
                    total_worked_hours=total_hours,
                )
                db.session.add(summary)
            else:
                summary.total_estimated_hours = task.estimated_hours or Decimal('0')
                summary.total_worked_hours = total_hours

            db.session.commit()
            return (
                f"⏱️ {hours}h registradas na tarefa '{task.what}'!\n"
                f"   Data: {work_dt} | Descrição: {description}"
            )

        elif task_type == 'process_instance':
            from models.process import ProcessInstance
            from models.activity_work_log import ActivityWorkLog
            from models.employee import Employee

            instance = db.session.get(ProcessInstance, task_id)
            if not instance:
                return f"Instância de processo ID {task_id} não encontrada."
            if company_id and int(company_id) != int(instance.company_id):
                return "Erro: a instância informada não pertence à empresa ativa do contexto."

            employee = (
                Employee.query.filter(
                    Employee.user_id == user_id,
                    Employee.company_id == instance.company_id,
                    Employee.status == 'active',
                )
                .order_by(Employee.id.asc())
                .first()
            )
            if not employee:
                return "Erro: não encontrei um colaborador ativo vinculado ao usuário na empresa desta instância."

            log = ActivityWorkLog(
                activity_type='process_instance',
                activity_id=task_id,
                employee_id=employee.id,
                employee_name=employee.name,
                hours_worked=Decimal(str(hours)),
                description=description,
                work_date=work_dt,
                created_at=datetime.utcnow()
            )
            db.session.add(log)

            if instance.status == 'pending':
                instance.status = 'in_progress'

            db.session.flush()
            total_hours = (
                db.session.query(func.coalesce(func.sum(ActivityWorkLog.hours_worked), 0))
                .filter(
                    ActivityWorkLog.activity_type == 'process_instance',
                    ActivityWorkLog.activity_id == task_id,
                )
                .scalar()
            ) or 0
            instance.worked_hours = total_hours
            if hasattr(instance, 'actual_hours'):
                instance.actual_hours = float(total_hours)

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
        try:
            from services.agent_action_backlog_service import ensure_backlog_task_for_action

            ensure_backlog_task_for_action(action, autocommit=True)
        except Exception:
            logger.exception(
                "Falha ao espelhar approval_request #%s no backlog AA.J.31",
                action.id,
            )

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


@tool
def squad_create_intervention(title: str, due_date: str, how: str, notes: str = "", assignee_name: str = "Agente Squad"):
    """
    SQUAD DE ENGENHARIA: Cria uma nova atividade de intervenção no projeto 'AA.J.31 Agentes de Work V3'.
    :param title: O que (Título da atividade)
    :param due_date: Quando (Data prevista YYYY-MM-DD)
    :param how: Como (Explicação do que será feito)
    :param notes: Observações e informações adicionais
    :param assignee_name: Quem (Responsável, ex: 'Agente Sapiens' ou 'QA_AUTOMATION')
    """
    from models.project import Project, ProjectTask
    from models.employee import Employee
    from models.user import User
    from services.whatsapp_service import whatsapp_service
    from datetime import datetime, timedelta

    # Forçando ID 31 e contexto AA - Versus Gestão Corporativa
    project = Project.query.filter_by(id=31).first()
    if not project:
        return "Erro: Projeto 'AA.J.31' não encontrado. ID=31."
        
    company_id = project.company_id

    due_dt = None
    if due_date:
        try:
            due_dt = datetime.strptime(due_date.strip()[:10], '%Y-%m-%d').date()
        except:
            pass

    def _append_recurrence(existing_text: str, new_text: str) -> str:
        base = str(existing_text or "").strip()
        payload = str(new_text or "").strip()
        if not payload:
            return base
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        block = f"[RECORRÊNCIA AUTOMÁTICA - {timestamp}]\n{payload}"
        if payload in base:
            return base
        return f"{base}\n\n{block}".strip() if base else block

    # ── GUARDA DE IDEMPOTÊNCIA / RECORRÊNCIA ───────────────────────────────────
    # Se já existe uma intervenção aberta com o mesmo título, reusa o card
    # e anexa a nova evidência em vez de abrir um novo BUG genérico.
    existing_open = ProjectTask.query.filter(
        ProjectTask.project_id == project.id,
        ProjectTask.what == title,
        ProjectTask.stage != 'completed',
    ).order_by(ProjectTask.updated_at.desc(), ProjectTask.id.desc()).first()
    if existing_open:
        merged_notes = _append_recurrence(existing_open.notes, notes)
        if merged_notes != (existing_open.notes or "").strip():
            existing_open.notes = merged_notes
        if how and not existing_open.how:
            existing_open.how = how
        if due_dt and (existing_open.due_date is None or due_dt < existing_open.due_date):
            existing_open.due_date = due_dt
        existing_open.updated_at = datetime.utcnow()
        db.session.commit()
        return (
            f"[REINCIDÊNCIA] Intervenção aberta reutilizada com sucesso. "
            f"Card existente ID: {existing_open.id}."
        )

    # Janela curta para evitar duplicata transacional imediata.
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    existing = ProjectTask.query.filter(
        ProjectTask.project_id == project.id,
        ProjectTask.what == title,
        ProjectTask.created_at >= five_min_ago
    ).first()
    if existing:
        return (
            f"[IDEMPOTÊNCIA] Tarefa '{title}' já foi criada recentemente "
            f"(ID: {existing.id}). Nenhuma duplicata gerada."
        )
    # ───────────────────────────────────────────────────────────────────────────

    # Tenta achar o colaborador ativo 
    emp = Employee.query.filter(Employee.company_id == company_id, Employee.name.ilike(f'%{assignee_name}%')).first()
    emp_id = emp.id if emp else None

    # Tenta achar Fabiano para notificação
    fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
        Employee.company_id == company_id, User.name.ilike('%Fabiano%')
    ).first()

    task = ProjectTask(
        project_id=project.id,
        what=title,
        who=emp.name if emp else assignee_name,
        employee_id=emp_id,
        due_date=due_dt,
        how=how,
        notes=notes,
        status='planned',
        stage='inbox',
        priority='normal',
        score_weight=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(task)
    db.session.commit()

    if fabiano and hasattr(fabiano, 'user') and getattr(fabiano.user, 'whatsapp', None):
        msg = (
            f"🛠️ *Squad de Engenharia - Nova Intervenção!*\n\n"
            f"📌 *O Quê:* {title}\n"
            f"👤 *Quem:* {assignee_name}\n"
            f"📅 *Prazo:* {due_date}\n"
            f"📋 *Como:* {how}\n"
            f"📝 *Obs:* {notes}\n"
        )
        whatsapp_service.send_message(fabiano.user.whatsapp, msg)

    return f"Atividade '{title}' criada com sucesso no projeto AA.J.31. ID criado da tarefa: {task.id}"

@tool
def squad_update_intervention(task_id: int, stage: str, log_history: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: Atualiza o andamento de uma intervenção, movendo de lista, inserindo histórico e lançando horas.
    :param task_id: ID da atividade
    :param stage: Fase (inbox, waiting, executing, pending, suspended, completed)
    :param log_history: Histórico ou comentário para adicionar 
    :param hours_worked: Total de horas trabalhadas na interação (lançadas no usuário Fabiano Diretor)
    """
    from models.project import ProjectTask, ProjectActivityCollaborator, ProjectTaskHoursSummary
    from models.employee import Employee
    from models.user import User
    from models.activity_work_log import ActivityWorkLog
    from services.whatsapp_service import whatsapp_service
    from datetime import datetime
    from sqlalchemy import func
    from decimal import Decimal

    task = ProjectTask.query.get(task_id)
    if not task:
        return f"Erro: Tarefa {task_id} não encontrada."

    task.stage = stage
    if stage == 'completed':
        task.status = 'completed'
    elif stage in ('executing', 'pending', 'waiting'):
        task.status = 'in_progress'

    # Add log
    logs = list(task.logs) if task.logs else []
    logs.append({
        'date': datetime.utcnow().isoformat(),
        'author': 'Squad Bot',
        'text': log_history
    })
    task.logs = logs

    fabiano = None
    if task.project:
        fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
            Employee.company_id == task.project.company_id, User.name.ilike('%Fabiano%')
        ).first()

    if float(hours_worked) > 0 and fabiano:
        # Lançamento de horas manual
        log = ActivityWorkLog(
            activity_type='project',
            activity_id=task_id,
            employee_id=fabiano.id,
            employee_name=fabiano.name,
            hours_worked=Decimal(str(hours_worked)),
            description=log_history[:250],
            work_date=datetime.utcnow().date(),
            created_at=datetime.utcnow()
        )
        db.session.add(log)
        
        collab = ProjectActivityCollaborator.query.filter_by(activity_id=task_id, employee_id=fabiano.id).first()
        if not collab:
            collab = ProjectActivityCollaborator(activity_id=task_id, employee_id=fabiano.id, role='executor')
            db.session.add(collab)
        collab.worked_hours = Decimal(str(collab.worked_hours or 0)) + Decimal(str(hours_worked))
        db.session.flush()

        task.worked_hours = (task.worked_hours or 0) + Decimal(str(hours_worked))
        
        sum_row = ProjectTaskHoursSummary.query.filter_by(task_id=task_id).first()
        if not sum_row:
            sum_row = ProjectTaskHoursSummary(task_id=task_id)
            db.session.add(sum_row)
        sum_row.total_worked_hours = Decimal(str(sum_row.total_worked_hours or 0)) + Decimal(str(hours_worked))

    db.session.commit()

    if stage in ('executing', 'in_progress'):
        if fabiano and hasattr(fabiano, 'user') and getattr(fabiano.user, 'whatsapp', None):
             msg = (
                 f"⚙️ *Squad de Engenharia - Intervenção em Andamento*\n\n"
                 f"📌 *Atividade:* {task.what}\n"
                 f"🔄 *Fase atual:* {stage}\n"
                 f"⏱️ *Tempo investido (agora):* {hours_worked}h\n"
                 f"📝 *Histórico:* {log_history}"
             )
             whatsapp_service.send_message(fabiano.user.whatsapp, msg)

    return f"Status da intervenção {task_id} atualizado para '{stage}'. {hours_worked}h lançadas com sucesso."

@tool
def squad_finish_intervention(task_id: int, remark: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: Conclui a intervenção e notifica o responsável.
    :param task_id: ID da atividade
    :param remark: Observação de conclusão (resultado final)
    :param hours_worked: Quaisquer horas finais para lançamento
    """
    from models.project import ProjectTask
    from models.employee import Employee
    from models.user import User
    from services.whatsapp_service import whatsapp_service
    from datetime import datetime

    task = ProjectTask.query.get(task_id)
    if not task:
        return f"Erro: Tarefa {task_id} não encontrada."
    
    comp_resp = squad_update_intervention.invoke({"task_id": task_id, "stage": "completed", "log_history": remark, "hours_worked": hours_worked})

    task.completion_date = datetime.utcnow().date()
    db.session.commit()

    if task.project:
        fabiano = Employee.query.join(User, User.id == Employee.user_id).filter(
            Employee.company_id == task.project.company_id, User.name.ilike('%Fabiano%')
        ).first()

        if fabiano and hasattr(fabiano, 'user') and getattr(fabiano.user, 'whatsapp', None):
             msg = (
                 f"✅ *Squad de Engenharia - Intervenção Concluída!*\n\n"
                 f"📌 *Atividade:* {task.what}\n"
                 f"💰 *Tempo investido final:* {hours_worked}h\n"
                 f"🏁 *Resultado/Observação:* {remark}"
             )
             whatsapp_service.send_message(fabiano.user.whatsapp, msg)
             
    return f"Atividade {task_id} concluída com sucesso! Detalhes: {comp_resp}"



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
    create_project_task,
    complete_task,
    log_work_hours,
    request_deadline_extension,
    list_team_workload,
]
logger = logging.getLogger(__name__)
