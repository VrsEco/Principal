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
from models.company import Company
from src.intelligence.rag import knowledge_base
from sqlalchemy import text
import json
import os
import re
import unicodedata

from services.engineering_suggestion_request_service import EngineeringSuggestionRequestService
from src.intelligence.tool_context import (
    active_user_id_ctx, 
    active_company_id_ctx,
    get_sapiens_context
)
from src.intelligence.tools_domains import task_ops as task_ops_domain
from src.intelligence.tools_domains import meeting_ops as meeting_ops_domain
from src.intelligence.tools_domains import process_ops as process_ops_domain
from src.intelligence.tools_domains import work_ops as work_ops_domain
from src.intelligence.tools_domains import strategy_ops as strategy_ops_domain
from src.intelligence.tools_domains import analytics_ops as analytics_ops_domain
from src.intelligence.tools_domains import system_ops as system_ops_domain
from src.intelligence.tools_domains import company_ops as company_ops_domain
from src.intelligence.tools_domains import user_ops as user_ops_domain

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


def _sanitize_json_payload(payload):
    return sanitize_output(json.dumps(payload, ensure_ascii=False, default=str))


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
    return system_ops_domain.consult_rules(query=query)
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


def _get_project_task_in_active_company(task_id: int):
    """Recupera tarefa de projeto estritamente no contexto da empresa ativa."""
    from models.project import ProjectTask

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    task = ProjectTask.query.filter_by(id=task_id, company_id=int(company_id)).first()
    if not task:
        return None, f"Tarefa de projeto ID {task_id} não encontrada na empresa ativa."

    return task, None


def _get_process_instance_in_active_company(instance_id: int):
    """Recupera instância de processo estritamente no contexto da empresa ativa."""
    from models.process import ProcessInstance

    company_id = get_active_company_id()
    if not company_id:
        return None, "Erro: Nenhuma empresa ativa identificada."

    instance = ProcessInstance.query.filter_by(id=instance_id, company_id=int(company_id)).first()
    if not instance:
        return None, f"Instância de processo ID {instance_id} não encontrada na empresa ativa."

    return instance, None

@tool
def query_database(sql_query: str):
    """
    Executa uma consulta SQL SELECT (somente leitura) no banco de dados para buscar dados operacionais.
    SEGURANÇA: Filtros por 'company_id' são injetados AUTOMATICAMENTE.
    """
    return system_ops_domain.query_database(sql_query=sql_query)
@tool
def escalate_technical_issue(error_description: str, context: str):
    """
    Escalona um erro técnico ou de sistema para o Time de Engenharia.
    """
    return system_ops_domain.escalate_technical_issue(error_description=error_description, context=context)


@tool
def request_engineering_suggestion(
    title: str,
    objective: str,
    suggestion_type: str = "improvement",
    scope_label: str = "Operação Geral",
    evidence_summary: str = None,
    notes: str = None,
    urgency: str = "medium",
    company_id: int = None,
    requester_name: str = None,
):
    """
    Registra uma sugestão, observação ou relato de bug como card formal no backlog da Engenharia (AA.J.1).
    Use esta tool quando o usuário pedir para encaminhar uma melhoria, observação funcional ou bug ao Squad.
    :param title: Título curto da solicitação.
    :param objective: Problema, impacto ou resultado esperado.
    :param suggestion_type: bug, improvement ou observation.
    :param scope_label: Escopo funcional da solicitação.
    :param evidence_summary: Evidências, passos, contexto ou empresa afetada.
    :param notes: Observações adicionais.
    :param urgency: low, medium, high ou critical.
    :param company_id: Opcional. Se omitido, usa a empresa ativa do contexto.
    :param requester_name: Opcional. Se omitido, tenta usar o nome do usuário autenticado.
    """
    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()
    requester_user_id = get_active_user_id()
    requester_user = get_active_user()

    if not requester_user_id:
        return {"success": False, "error": "Nenhum usuário ativo identificado para registrar a sugestão."}
    if not selected_company_id:
        return {"success": False, "error": "Nenhuma empresa ativa identificada para registrar a sugestão."}

    company = db.session.get(Company, int(selected_company_id))
    resolved_requester_name = (
        str(requester_name).strip()
        if requester_name and str(requester_name).strip()
        else (str(getattr(requester_user, "name", "")).strip() or None)
    )

    try:
        record = EngineeringSuggestionRequestService.create_request(
            {
                "title": title,
                "objective": objective,
                "suggestion_type": suggestion_type,
                "scope_label": scope_label,
                "evidence_summary": evidence_summary,
                "notes": notes,
                "urgency": urgency,
                "source_channel": "mcp",
            },
            company_id=int(selected_company_id),
            company_name=getattr(company, "name", None),
            requester_user_id=int(requester_user_id),
            requester_name=resolved_requester_name,
        )
    except ValueError as exc:
        return {"success": False, "error": str(exc)}

    return {"success": True, "request": record}


@tool
def list_my_engineering_suggestions(limit: int = 10, company_id: int = None):
    """
    Lista as sugestões de engenharia já registradas pelo usuário autenticado no backlog AA.J.1.
    Use para responder perguntas como 'quais tickets eu já abri?'.
    :param limit: Quantidade máxima de cards retornados (1 a 50).
    :param company_id: Opcional. Se omitido, usa a empresa ativa do contexto.
    """
    requester_user_id = get_active_user_id()
    selected_company_id = int(company_id) if company_id is not None else get_active_company_id()

    if not requester_user_id:
        return {"success": False, "error": "Nenhum usuário ativo identificado para listar sugestões."}

    records = EngineeringSuggestionRequestService.list_requests(
        company_id=int(selected_company_id) if selected_company_id is not None else None,
        requester_user_id=int(requester_user_id),
        limit=limit,
    )
    return {
        "success": True,
        "count": len(records),
        "requests": records,
    }
@tool
def create_process_area(name: str, description: str = None, code: str = None, company_id: int = None):
    """
    Cria uma nova Área de Processo no sistema.
    As Áreas são o nível mais alto da hierarquia de processos.
    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    """
    return process_ops_domain.create_process_area(
        name=name,
        description=description,
        code=code,
        company_id=company_id,
    )


@tool
def create_macro_process(
    area_id: int,
    name: str,
    description: str = None,
    order_index: int = 1,
    company_id: int = None,
    responsible: str = None,
):
    """
    Cria um novo Macroprocesso vinculado a uma Área de Processo.
    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    :param responsible: Opcional. Alias MCP para o dono do macroprocesso.
    """
    return process_ops_domain.create_macro_process(
        area_id=area_id,
        name=name,
        description=description,
        order_index=order_index,
        company_id=company_id,
        responsible=responsible,
    )


@tool
def update_macro_process(
    macro_id: int,
    name: str = None,
    responsible: str = None,
    description: str = None,
    order_index: int = None,
    area_id: int = None,
    company_id: int = None,
):
    """
    Atualiza um macroprocesso existente com suporte aos campos responsible, description e order_index.
    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    """
    return process_ops_domain.update_macro_process(
        macro_id=macro_id,
        name=name,
        responsible=responsible,
        description=description,
        order_index=order_index,
        area_id=area_id,
        company_id=company_id,
    )


@tool
def create_process(
    macro_id: int,
    name: str,
    description: str = None,
    responsible: str = None,
    order_index: int = 1,
    company_id: int = None,
):
    """
    Cria um novo Processo vinculado a um Macroprocesso.
    Este é o nível onde as rotinas (POPs) serão penduradas.
    :param company_id: Obrigatório quando o canal não tiver contexto tenant autenticado.
    """
    return process_ops_domain.create_process(
        macro_id=macro_id,
        name=name,
        description=description,
        responsible=responsible,
        order_index=order_index,
        company_id=company_id,
    )


@tool
def update_company_status(company_id: int, is_active: bool, reason: str = None):
    """
    Atualiza o status de atividade (Ativo/Inativo) de uma empresa.
    Use isto quando o usuário pedir para 'desativar', 'inativar' ou 'ativar' uma empresa.
    """
    return company_ops_domain.update_company_status(company_id=company_id, is_active=is_active, reason=reason)


@tool
def get_company_profile(company_id: int = None):
    """
    Retorna o cadastro detalhado da empresa ativa ou de uma empresa acessível ao usuário.
    Use para consultar dados cadastrais antes de corrigir ou complementar o cadastro.
    """
    return company_ops_domain.get_company_profile(company_id=company_id)


@tool
def update_company_profile(changes: dict, company_id: int = None):
    """
    Atualiza parcialmente o cadastro da empresa com whitelist de campos editáveis.
    Use para corrigir nome, prefixo, segmento, porte, cidade, MVV, logos e demais campos do cadastro.
    """
    return company_ops_domain.update_company_profile(changes=changes, company_id=company_id)


@tool
def get_company_registration_diagnostics(company_id: int = None):
    """
    Analisa a completude do cadastro da empresa e aponta lacunas prioritárias para organização do cadastro.
    """
    return company_ops_domain.get_company_registration_diagnostics(company_id=company_id)


@tool
def list_process_hierarchy(company_id: int = None):
    """
    Lista toda a hierarquia de processos da empresa (Áreas -> Macros -> Processos).
    Use isto para entender a estrutura atual antes de criar novos itens.
    :param company_id: Opcional ID da empresa. Se não fornecido, usa a empresa ativa da sessão.
    """
    return process_ops_domain.list_process_hierarchy(company_id=company_id)


@tool
def list_my_companies(search_term: str = None):
    """
    Lista as empresas às quais o usuário tem acesso, incluindo o Prefixo (client_code) e o ID.
    Use isto quando precisar identificar o ID de uma empresa pelo nome ou prefixo.
    """
    return company_ops_domain.list_my_companies(search_term=search_term)
@tool
def list_plans(company_id: int = None, mode: str = None):
    """
    Lista todos os planos estratégicos (Growth ou Implantation) da empresa ativa ou da empresa explicitamente informada.
    Use isto para descobrir quais planos de ação estão em curso.
    :param company_id: Opcional. Se informado, força o filtro tenant-safe nessa empresa.
    :param mode: Opcional 'growth' ou 'implantation' para filtrar.
    """
    return strategy_ops_domain.list_plans(company_id=company_id, mode=mode)


@tool
def get_plan_diagnostics(plan_id: int):
    """
    Retorna um diagnóstico completo de um plano, incluindo status de cada seção e métricas financeiras.
    Use isto para entender gargalos ou o estado atual de uma implantação/crescimento.
    """
    return strategy_ops_domain.get_plan_diagnostics(plan_id=plan_id)


@tool
def list_meetings(company_id: int = None, status: str = None, limit: int = 20):
    """
    Lista reuniões da empresa ativa ou da empresa explicitamente informada.
    Use para leitura segura do domínio meetings sem criar ou alterar reuniões.
    """
    return meeting_ops_domain.list_meetings(company_id=company_id, status=status, limit=limit)


@tool
def get_plan_diagnostics_read_model(company_id: int, plan_id: int):
    """
    Retorna o read model whitelisted do diagnóstico de um plano estratégico.
    Use para analytics MCP sem SQL livre.
    """
    return analytics_ops_domain.get_plan_diagnostics_read_model(company_id=company_id, plan_id=plan_id)


@tool
def update_plan_section(plan_id: int, section_key: str, status: str = 'completed', company_id: int = None):
    """
    Atualiza o status de uma seção do plano (ex: 'participants', 'finance', 'projects').
    Use isto para marcar etapas como concluídas conforme a IA ou o usuário executam as tarefas.
    :param company_id: Opcional. Se informado, força a validação tenant-safe nessa empresa.
    """
    return strategy_ops_domain.update_plan_section(
        plan_id=plan_id,
        section_key=section_key,
        status=status,
        company_id=company_id,
    )


@tool
def get_my_work(scope: str = 'me', company_ids: str = None, search_term: str = None):
    """
    Retorna a lista de atividades (Projetos e Processos) pendentes para o usuário logado.
    :param scope: 'me' para minhas atividades, 'team' para equipe, 'company' para toda a empresa.
    :param company_ids: Opcional, ids de empresas separados por virgula (ex: "31,32").
    :param search_term: Opcional, filtra atividades por título, descrição ou nome de empresa.
    """
    return work_ops_domain.get_my_work(scope=scope, company_ids=company_ids, search_term=search_term)


@tool
def get_user_summary(target_user: str = None, range: str = 'today'):
    """
    Gera um relatório consolidado de atividades, processos e REUNIÕES de um usuário.
    Use isto para 'meu resumo' ou para 'resumo do Fulano'.
    """
    return user_ops_domain.get_user_summary(target_user=target_user, range=range)
@tool
def list_system_users():
    """
    Lista todos os usuários cadastrados no sistema. (Admin Only)
    Retorna nome, email, papel e contatos (WhatsApp/Telegram).
    """
    return user_ops_domain.list_system_users()
@tool
def register_system_user(name: str, email: str, role: str = 'collaborator', whatsapp: str = None, telegram: str = None):
    """
    Cadastra um novo usuário no sistema com dados de contato.
    """
    return user_ops_domain.register_system_user(name=name, email=email, role=role, whatsapp=whatsapp, telegram=telegram)
@tool
def update_user_contacts(user_id: int, whatsapp: str = None, telegram: str = None):
    """
    Atualiza os dados de contato (WhatsApp/Telegram) de um usuário.
    Pode ser usado para atualizar os próprios dados ou por um admin.
    """
    return user_ops_domain.update_user_contacts(user_id=user_id, whatsapp=whatsapp, telegram=telegram)
@tool
def schedule_meeting(title: str, date: str, time: str, guests: str, agenda_items: str = None, notes: str = None):
    """
    Cria e agenda uma nova reunião no sistema enviando convite para os participantes.
    :param title: Título/Assunto da reunião. Ex: 'Revisão de Metas Q1'
    :param date: Data da reunião no formato YYYY-MM-DD. Ex: '2026-03-01'
    :param time: Horário no formato HH:MM. Ex: '14:30'
    :param guests: Lista de e-mails ou nomes dos convidados, separados por vírgula.
    :param agenda_items: Pautas separadas por ponto-e-vírgula.
    :param notes: Observações ou pauta livre para o convite.
    """
    return meeting_ops_domain.schedule_meeting(
        title=title,
        date=date,
        time=time,
        guests=guests,
        agenda_items=agenda_items,
        notes=notes,
    )


@tool
def start_meeting(meeting_id: int):
    """
    Inicia uma reunião agendada. Marca o horário real de início e vincula/cria um projeto automático.
    :param meeting_id: ID da reunião a ser iniciada.
    """
    return meeting_ops_domain.start_meeting(meeting_id=meeting_id)


@tool
def log_meeting_discussion(meeting_id: int, topic: str, decision: str = None, responsible: str = None, deadline: str = None):
    """
    Registra um ponto discutido em uma reunião em andamento.
    """
    return meeting_ops_domain.log_meeting_discussion(
        meeting_id=meeting_id,
        topic=topic,
        decision=decision,
        responsible=responsible,
        deadline=deadline,
    )


@tool
def finish_meeting(meeting_id: int):
    """
    Encerra uma reunião em andamento e gera a ATA completa.
    """
    return meeting_ops_domain.finish_meeting(meeting_id=meeting_id)


@tool
def send_meeting_minutes(meeting_id: int, channel: str = "email"):
    """
    Envia a ATA para todos os participantes após o encerramento.
    :param channel: Canal de envio: 'email', 'whatsapp' ou 'ambos'.
    """
    return meeting_ops_domain.send_meeting_minutes(meeting_id=meeting_id, channel=channel)


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
    return task_ops_domain.get_tasks_today(scope=scope)


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
    return task_ops_domain.create_project_task(
        project_code=project_code,
        task_name=task_name,
        responsible_name=responsible_name,
        due_date=due_date,
        description=description,
        priority=priority,
        notes=notes,
    )


@tool
def list_project_tasks_secure(project_id: int = None, company_id: int = None, include_deleted: bool = False, limit: int = 50):
    """
    Lista atividades de projeto com filtro tenant-safe e suporte opcional a itens soft-deletados.
    """
    return task_ops_domain.list_project_tasks_secure(
        project_id=project_id,
        company_id=company_id,
        include_deleted=include_deleted,
        limit=limit,
    )


@tool
def create_project_task_secure(project_code: str, task_name: str, responsible_name: str = None, due_date: str = None, description: str = None, priority: str = "normal", notes: str = None, company_id: int = None):
    """
    Cria atividade de projeto via MCP com política, quota de mutação e auditoria reforçada.
    """
    return task_ops_domain.create_project_task_secure(
        project_code=project_code,
        task_name=task_name,
        responsible_name=responsible_name,
        due_date=due_date,
        description=description,
        priority=priority,
        notes=notes,
        company_id=company_id,
    )


@tool
def update_project_task_secure(task_id: int, changes: dict, company_id: int = None):
    """
    Atualiza atividade de projeto via MCP com whitelist de campos e limite de alterações.
    """
    return task_ops_domain.update_project_task_secure(
        task_id=task_id,
        changes=changes,
        company_id=company_id,
    )


@tool
def delete_project_task_secure(task_id: int, reason: str, confirm: bool = False, company_id: int = None):
    """
    Executa soft delete de atividade de projeto via MCP. Exige confirmação explícita.
    """
    return task_ops_domain.delete_project_task_secure(
        task_id=task_id,
        reason=reason,
        confirm=confirm,
        company_id=company_id,
    )


@tool
def restore_project_task_secure(task_id: int, confirm: bool = False, company_id: int = None):
    """
    Restaura atividade de projeto previamente removida logicamente. Exige confirmação explícita.
    """
    return task_ops_domain.restore_project_task_secure(
        task_id=task_id,
        confirm=confirm,
        company_id=company_id,
    )


@tool
def get_project_task_analytics_report(project_id: int = None, company_id: int = None, include_deleted: bool = True, limit: int = 200):
    """
    Consolida leitura ampla das atividades de projeto para análise e relatórios tenant-safe.
    """
    return task_ops_domain.get_project_task_analytics_report(
        project_id=project_id,
        company_id=company_id,
        include_deleted=include_deleted,
        limit=limit,
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
    return task_ops_domain.complete_task(
        task_type=task_type,
        task_id=task_id,
        evidence_description=evidence_description,
        completion_date=completion_date,
        notification_email=notification_email,
        notification_whatsapp=notification_whatsapp,
    )


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
    return task_ops_domain.log_work_hours(
        task_type=task_type,
        task_id=task_id,
        hours=hours,
        description=description,
        work_date=work_date,
    )


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
    
    return task_ops_domain.request_deadline_extension(
        task_type=task_type,
        task_id=task_id,
        new_deadline=new_deadline,
        reason=reason,
    )


@tool
def list_team_workload():
    """
    Analisa a carga de trabalho de todos os colaboradores da empresa.
    Identifica quem está sobrecarregado, ocioso ou em equilíbrio, com base nas horas
    disponíveis por semana versus tarefas abertas estimadas.
    Ideal para o supervisor identificar necessidade de redistribuição de tarefas.
    """
    return task_ops_domain.list_team_workload()


@tool
def get_team_workload_read_model(company_id: int, department: str = None, employee_id: int = None):
    """
    Retorna o read model whitelisted de workload por empresa/departamento/colaborador.
    """
    return analytics_ops_domain.get_team_workload_read_model(
        company_id=company_id,
        department=department,
        employee_id=employee_id,
    )


@tool
def get_projects_execution_risk_read_model(
    company_id: int,
    project_id: int = None,
    employee_id: int = None,
    status: str = None,
    limit: int = 50,
):
    """
    Retorna o read model whitelisted de risco de execução de projetos.
    """
    return analytics_ops_domain.get_projects_execution_risk_read_model(
        company_id=company_id,
        project_id=project_id,
        employee_id=employee_id,
        status=status,
        limit=limit,
    )


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
    return task_ops_domain.squad_create_intervention(
        title=title,
        due_date=due_date,
        how=how,
        notes=notes,
        assignee_name=assignee_name,
    )

@tool
def squad_update_intervention(task_id: int, stage: str, log_history: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: Atualiza o andamento de uma intervenção, movendo de lista, inserindo histórico e lançando horas.
    :param task_id: ID da atividade
    :param stage: Fase (inbox, waiting, executing, pending, suspended, completed)
    :param log_history: Histórico ou comentário para adicionar 
    :param hours_worked: Total de horas trabalhadas na interação (lançadas no usuário Fabiano Diretor)
    """
    return task_ops_domain.squad_update_intervention(
        task_id=task_id,
        stage=stage,
        log_history=log_history,
        hours_worked=hours_worked,
    )

@tool
def squad_finish_intervention(task_id: int, remark: str, hours_worked: float = 0.0):
    """
    SQUAD DE ENGENHARIA: Conclui a intervenção e notifica o responsável.
    :param task_id: ID da atividade
    :param remark: Observação de conclusão (resultado final)
    :param hours_worked: Quaisquer horas finais para lançamento
    """
    return task_ops_domain.squad_finish_intervention(
        task_id=task_id,
        remark=remark,
        hours_worked=hours_worked,
    )

@tool
def get_financial_results(period_start: str = "", period_end: str = "", company_id: int = 0):
    """
    Consulta read-only os resultados financeiros consolidados da empresa ativa.
    Use para resumir caixa, DRE líquida e painéis executivos sem expor SQL livre.
    """
    from services.financial_results_query_service import FinancialResultsQueryService

    selected_company_id = int(company_id) if int(company_id or 0) > 0 else get_active_company_id()
    if not selected_company_id:
        return "Erro: Nenhuma empresa ativa identificada para consulta financeira."

    payload, error = FinancialResultsQueryService.get_company_financial_results(
        company_id=int(selected_company_id),
        allowed_company_ids=[int(selected_company_id)],
        period_start=(period_start or None),
        period_end=(period_end or None),
    )
    if error:
        return f"Erro ao consultar resultados financeiros: {error}"
    return _sanitize_json_payload(payload or {})




tools = [
    # Fase 1 — Core Intelligence
    consult_rules,
    query_database,
    escalate_technical_issue,
    request_engineering_suggestion,
    list_my_engineering_suggestions,
    # Fase 1 — Process Management
    create_process_area,
    create_macro_process,
    update_macro_process,
    create_process,
    get_company_profile,
    update_company_profile,
    get_company_registration_diagnostics,
    update_company_status,
    list_process_hierarchy,
    # Fase 1 — Planning
    list_plans,
    get_plan_diagnostics,
    get_plan_diagnostics_read_model,
    update_plan_section,
    # Fase 1 — My Work & Users
    get_my_work,
    list_my_companies,
    list_system_users,
    register_system_user,
    update_user_contacts,
    # Fase 2 — Meetings
    list_meetings,
    schedule_meeting,
    start_meeting,
    log_meeting_discussion,
    finish_meeting,
    send_meeting_minutes,
    # Fase 2 — Task Management
    get_tasks_today,
    create_project_task,
    list_project_tasks_secure,
    create_project_task_secure,
    update_project_task_secure,
    delete_project_task_secure,
    restore_project_task_secure,
    get_project_task_analytics_report,
    complete_task,
    log_work_hours,
    request_deadline_extension,
    list_team_workload,
    get_team_workload_read_model,
    get_projects_execution_risk_read_model,
    # Fase 3 — Finance
    get_financial_results,
]
logger = logging.getLogger(__name__)
