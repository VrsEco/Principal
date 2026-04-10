from __future__ import annotations

import logging

from models import db
from src.intelligence.tools_support import get_active_company_id, sanitize_output

logger = logging.getLogger(__name__)


def create_process_area(name: str, description: str = None, code: str = None):
    """
    Cria uma nova Área de Processo no sistema.
    As Áreas são o nível mais alto da hierarquia de processos.
    """
    from models.process import ProcessArea

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada (Sessão ou ACTIVE_COMPANY_ID)."

    try:
        from api.resources.process import generate_area_code

        new_area = ProcessArea(
            company_id=company_id,
            name=name,
            description=description,
            code=code,
        )
        if code and "." not in str(code):
            new_area.code = generate_area_code(company_id, code)

        db.session.add(new_area)
        db.session.commit()
        return f"Área de Processo '{name}' criada com sucesso. ID: {new_area.id}, Código: {new_area.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar área de processo: {str(e)}"


def create_macro_process(area_id: int, name: str, description: str = None, order_index: int = 1):
    """
    Cria um novo Macroprocesso vinculado a uma Área de Processo.
    """
    from models.process import MacroProcess, ProcessArea

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        area = ProcessArea.query.filter_by(id=area_id, company_id=int(company_id)).first()
        if not area:
            return "Erro: Área de processo não encontrada na empresa ativa."

        from api.resources.process import generate_macro_code

        macro = MacroProcess(
            company_id=company_id,
            area_id=area_id,
            name=name,
            description=description,
            order_index=order_index,
        )
        macro.code = generate_macro_code(area_id, order_index)

        db.session.add(macro)
        db.session.commit()
        return f"Macroprocesso '{name}' criado com sucesso. ID: {macro.id}, Código: {macro.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar macroprocesso: {str(e)}"


def create_process(macro_id: int, name: str, description: str = None, responsible: str = None, order_index: int = 1):
    """
    Cria um novo Processo vinculado a um Macroprocesso.
    Este é o nível onde as rotinas (POPs) serão penduradas.
    """
    from models.process import MacroProcess, Process

    company_id = get_active_company_id()
    if not company_id:
        return "Erro: Nenhuma empresa ativa identificada."

    try:
        macro = MacroProcess.query.filter_by(id=macro_id, company_id=int(company_id)).first()
        if not macro:
            return "Erro: Macroprocesso não encontrado na empresa ativa."

        from api.resources.process import generate_process_code

        process = Process(
            company_id=company_id,
            macro_id=macro_id,
            name=name,
            description=description,
            responsible=responsible,
            order_index=order_index,
        )
        process.code = generate_process_code(macro_id, order_index)

        db.session.add(process)
        db.session.commit()
        return f"Processo '{name}' criado com sucesso. ID: {process.id}, Código: {process.code}"
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar processo: {str(e)}"


def list_process_hierarchy(company_id: int = None):
    """
    Lista toda a hierarquia de processos da empresa (Áreas -> Macros -> Processos).
    Use isto para entender a estrutura atual antes de criar novos itens.
    :param company_id: Opcional ID da empresa. Se não fornecido, usa a empresa ativa da sessão.
    """
    from models.process import MacroProcess, Process, ProcessArea

    active_company_id = get_active_company_id()
    effective_id = company_id or active_company_id
    if not effective_id:
        return "Erro: Empresa nao selecionada e nenhum company_id fornecido."
    if company_id and active_company_id and int(company_id) != int(active_company_id):
        return "Erro: company_id solicitado não pertence ao contexto de empresa ativa."

    try:
        areas = ProcessArea.query.filter_by(company_id=int(effective_id)).all()
        output = []
        for area in areas:
            output.append(f"Área: {area.name} (ID: {area.id}, Código: {area.code})")
            macros = MacroProcess.query.filter_by(area_id=area.id, company_id=int(effective_id)).all()
            for macro in macros:
                output.append(f"  └─ Macro: {macro.name} (ID: {macro.id}, Código: {macro.code})")
                procs = Process.query.filter_by(macro_id=macro.id, company_id=int(effective_id)).all()
                for process in procs:
                    output.append(f"    └─ Processo: {process.name} (ID: {process.id}, Código: {process.code})")

        return sanitize_output("\n".join(output)) if output else "Nenhum processo mapeado ainda."
    except Exception as e:
        return f"Erro ao listar hierarquia: {str(e)}"
