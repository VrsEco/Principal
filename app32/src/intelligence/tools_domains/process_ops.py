from __future__ import annotations

import logging

from models import db
from src.intelligence.tools_support import get_active_company_id, sanitize_output

logger = logging.getLogger(__name__)


def _resolve_effective_company_id(requested_company_id: int | None = None) -> tuple[int | None, str | None]:
    active_company_id = get_active_company_id()

    if requested_company_id is not None:
        try:
            requested_company_id = int(requested_company_id)
        except (TypeError, ValueError):
            return None, "Erro: company_id informado é inválido."

    if active_company_id and requested_company_id and int(active_company_id) != int(requested_company_id):
        return None, "Erro: company_id solicitado não pertence ao contexto de empresa ativa."

    effective_company_id = requested_company_id or active_company_id
    if not effective_company_id:
        return None, "Erro: Nenhuma empresa ativa identificada (sessão, contexto Sapiens ou company_id explícito)."

    return int(effective_company_id), None


def _build_scope_reconciliation(company_id: int) -> str:
    from models.process import MacroProcess, Process, ProcessArea

    areas_count = ProcessArea.query.filter_by(company_id=company_id).count()
    macros_count = MacroProcess.query.filter_by(company_id=company_id).count()
    processes_count = Process.query.filter_by(company_id=company_id).count()
    return (
        f"Validação tenant-safe: empresa {company_id} agora possui "
        f"{areas_count} área(s), {macros_count} macroprocesso(s) e {processes_count} processo(s)."
    )


def create_process_area(name: str, description: str = None, code: str = None, company_id: int | None = None):
    """
    Cria uma nova Área de Processo no sistema.
    As Áreas são o nível mais alto da hierarquia de processos.
    """
    from models.process import ProcessArea

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return error

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
        persisted_area = ProcessArea.query.filter_by(id=new_area.id, company_id=company_id).first()
        if not persisted_area:
            db.session.rollback()
            return "Erro: falha na validação pós-escrita da área de processo no tenant informado."

        return (
            f"Área de Processo '{name}' criada com sucesso. "
            f"ID: {new_area.id}, Código: {new_area.code}. {_build_scope_reconciliation(company_id)}"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar área de processo: {str(e)}"


def create_macro_process(
    area_id: int,
    name: str,
    description: str = None,
    order_index: int = 1,
    company_id: int | None = None,
):
    """
    Cria um novo Macroprocesso vinculado a uma Área de Processo.
    """
    from models.process import MacroProcess, ProcessArea

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return error

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
        persisted_macro = MacroProcess.query.filter_by(id=macro.id, company_id=company_id, area_id=area_id).first()
        if not persisted_macro:
            db.session.rollback()
            return "Erro: falha na validação pós-escrita do macroprocesso no tenant informado."

        return (
            f"Macroprocesso '{name}' criado com sucesso. "
            f"ID: {macro.id}, Código: {macro.code}. {_build_scope_reconciliation(company_id)}"
        )
    except Exception as e:
        db.session.rollback()
        return f"Erro ao criar macroprocesso: {str(e)}"


def create_process(
    macro_id: int,
    name: str,
    description: str = None,
    responsible: str = None,
    order_index: int = 1,
    company_id: int | None = None,
):
    """
    Cria um novo Processo vinculado a um Macroprocesso.
    Este é o nível onde as rotinas (POPs) serão penduradas.
    """
    from models.process import MacroProcess, Process

    company_id, error = _resolve_effective_company_id(company_id)
    if error:
        return error

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
        persisted_process = Process.query.filter_by(id=process.id, company_id=company_id, macro_id=macro_id).first()
        if not persisted_process:
            db.session.rollback()
            return "Erro: falha na validação pós-escrita do processo no tenant informado."

        return (
            f"Processo '{name}' criado com sucesso. "
            f"ID: {process.id}, Código: {process.code}. {_build_scope_reconciliation(company_id)}"
        )
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
