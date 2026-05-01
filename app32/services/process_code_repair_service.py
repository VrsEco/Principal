from __future__ import annotations

from collections import defaultdict

from models import Company, MacroProcess, Process, ProcessArea, db


def _sanitize_company_code(raw_code: str | None, company_id: int) -> str:
    cleaned = "".join(ch for ch in str(raw_code or "").strip().upper() if ch.isalnum())
    if cleaned:
        return cleaned
    return str(company_id).zfill(2)


def rebuild_process_hierarchy_codes(company_id: int) -> dict:
    company = Company.query.get(company_id)
    if not company:
        raise ValueError(f"Empresa {company_id} não encontrada.")

    company_code = _sanitize_company_code(company.client_code, company_id)

    areas = (
        ProcessArea.query
        .filter_by(company_id=company_id)
        .order_by(ProcessArea.order_index.asc(), ProcessArea.id.asc())
        .all()
    )
    area_position = 0
    area_codes_by_id: dict[int, str] = {}
    updated_areas = 0
    for area in areas:
        area_position += 1
        area_sequence = int(area.order_index or area_position or 1)
        new_code = f"{company_code}.C.{area_sequence}"
        area_codes_by_id[area.id] = new_code
        if area.code != new_code:
            area.code = new_code
            updated_areas += 1

    macros = (
        MacroProcess.query
        .filter_by(company_id=company_id)
        .order_by(MacroProcess.area_id.asc(), MacroProcess.order_index.asc(), MacroProcess.id.asc())
        .all()
    )
    macro_group_positions: dict[int, int] = defaultdict(int)
    macro_codes_by_id: dict[int, str] = {}
    updated_macros = 0
    for macro in macros:
        macro_group_positions[macro.area_id] += 1
        macro_sequence = int(macro.order_index or macro_group_positions[macro.area_id] or 1)
        area_code = area_codes_by_id.get(macro.area_id)
        if not area_code:
            continue
        new_code = f"{area_code}.{macro_sequence}"
        macro_codes_by_id[macro.id] = new_code
        if macro.code != new_code:
            macro.code = new_code
            updated_macros += 1

    processes = (
        Process.query
        .filter_by(company_id=company_id)
        .order_by(Process.macro_id.asc(), Process.order_index.asc(), Process.id.asc())
        .all()
    )
    process_group_positions: dict[int, int] = defaultdict(int)
    updated_processes = 0
    for process in processes:
        process_group_positions[process.macro_id] += 1
        process_sequence = int(process.order_index or process_group_positions[process.macro_id] or 1)
        macro_code = macro_codes_by_id.get(process.macro_id)
        if not macro_code:
            continue
        new_code = f"{macro_code}.{process_sequence}"
        if process.code != new_code:
            process.code = new_code
            updated_processes += 1

    db.session.commit()
    return {
        "company_id": company_id,
        "company_code": company_code,
        "areas_updated": updated_areas,
        "macros_updated": updated_macros,
        "processes_updated": updated_processes,
        "areas_total": len(areas),
        "macros_total": len(macros),
        "processes_total": len(processes),
    }
