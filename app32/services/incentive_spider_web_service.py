from __future__ import annotations

from typing import Any
import re
import unicodedata

from models import (
    db,
    Employee,
    Indicator,
    IndicatorGoal,
    OKRArea,
    OKRGlobal,
    Process,
    ProcessInstance,
    ProcessInstanceCollaborator,
    Project,
    ProjectActivityCollaborator,
    ProjectTask,
    Routine,
    RoutineCollaborator,
    RoutineJourneyBinding,
    WorkJourneyBlock,
)


class IncentiveSpiderWebService:
    """Monta a Teia de Governança do módulo de Incentivos com escopo tenant-safe."""

    @classmethod
    def build_graph(cls, company_id: int) -> dict[str, Any]:
        company_id = int(company_id)
        nodes: dict[str, dict[str, Any]] = {}
        links: list[dict[str, Any]] = []
        link_counter: dict[str, int] = {}

        def add_node(nid: str, label: str, ntype: str, meta: dict[str, Any] | None = None) -> None:
            if nid not in nodes:
                nodes[nid] = {"id": nid, "label": label, "type": ntype, "degree": 0, **(meta or {})}
            link_counter.setdefault(nid, 0)

        def add_link(src: str | None, tgt: str | None, label: str = "", strength: str = "normal") -> None:
            if not src or not tgt:
                return
            if src not in nodes or tgt not in nodes:
                return
            if any(l["source"] == src and l["target"] == tgt for l in links):
                return
            links.append({"source": src, "target": tgt, "label": label, "strength": strength})
            link_counter[src] = link_counter.get(src, 0) + 1
            link_counter[tgt] = link_counter.get(tgt, 0) + 1

        employees = Employee.query.filter_by(company_id=company_id, status="active").all()
        def normalize_name(value: str) -> str:
            folded = unicodedata.normalize("NFKD", str(value or ""))
            ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
            return re.sub(r"\s+", " ", ascii_value.casefold()).strip()

        employee_ids_by_name: dict[str, list[int]] = {}
        for emp in employees:
            add_node(f"colab_{emp.id}", emp.name, "collaborator", {"department": emp.department})
            employee_ids_by_name.setdefault(normalize_name(emp.name), []).append(emp.id)

        processes = Process.query.filter_by(company_id=company_id, is_active=True).all()
        for proc in processes:
            add_node(f"proc_{proc.id}", proc.name, "process", {"kanban_stage": proc.kanban_stage})
            if proc.owner_employee_id:
                add_link(f"colab_{proc.owner_employee_id}", f"proc_{proc.id}", "dono", "direct")
            elif proc.responsible_id:
                add_link(f"colab_{proc.responsible_id}", f"proc_{proc.id}", "responsável", "direct")

        projects = Project.query.filter_by(company_id=company_id).all()
        for proj in projects:
            add_node(
                f"proj_{proj.id}",
                proj.name,
                "project",
                {"status": proj.status, "progress": proj.progress},
            )

        area_okrs = OKRArea.query.filter_by(company_id=company_id).all()
        global_okrs = OKRGlobal.query.filter_by(company_id=company_id).all()
        area_okr_ids = {okr.id for okr in area_okrs}
        global_okr_ids = {okr.id for okr in global_okrs}
        for okr in area_okrs:
            add_node(f"okr_area_{okr.id}", okr.objective, "area_okr", {"department": okr.department})
        for okr in global_okrs:
            add_node(f"okr_global_{okr.id}", okr.objective, "global_okr")

        for proj in projects:
            owner_ids = employee_ids_by_name.get(normalize_name(proj.owner), [])
            if len(owner_ids) == 1:
                add_link(f"colab_{owner_ids[0]}", f"proj_{proj.id}", "responsável", "direct")
            for raw_okr_id in proj.okr_links or []:
                try:
                    okr_id = int(raw_okr_id)
                except (TypeError, ValueError):
                    continue
                # Na tela de Projetos, ``okr_links`` referencia prioritariamente
                # OKRs de Área. O fallback global preserva registros legados.
                if okr_id in area_okr_ids:
                    add_link(f"proj_{proj.id}", f"okr_area_{okr_id}", "iniciativa do OKR", "direct")
                elif okr_id in global_okr_ids:
                    add_link(f"proj_{proj.id}", f"okr_global_{okr_id}", "iniciativa do OKR", "direct")

        for area in area_okrs:
            for raw_global_id in area.linked_okr_ids or []:
                try:
                    global_id = int(raw_global_id)
                except (TypeError, ValueError):
                    continue
                if global_id in global_okr_ids:
                    add_link(
                        f"okr_area_{area.id}",
                        f"okr_global_{global_id}",
                        "desdobra OKR Global",
                        "direct",
                    )

        routines = Routine.query.filter_by(company_id=company_id, is_active=True).all()
        for routine in routines:
            add_node(
                f"routine_{routine.id}",
                routine.name,
                "routine",
                {
                    "schedule_type": routine.schedule_type,
                    "start_time": routine.start_time,
                    "deadline_days": routine.deadline_days,
                    "deadline_hours": routine.deadline_hours,
                    "score_weight": float(routine.score_weight or 0),
                },
            )
            if routine.process_id:
                add_link(f"routine_{routine.id}", f"proc_{routine.process_id}", "rotina do processo", "direct")

        routine_collaborators = (
            db.session.query(RoutineCollaborator)
            .join(Routine, Routine.id == RoutineCollaborator.routine_id)
            .join(Employee, Employee.id == RoutineCollaborator.employee_id)
            .filter(
                Routine.company_id == company_id,
                Routine.is_active.is_(True),
                Employee.company_id == company_id,
            )
            .all()
        )
        for rc in routine_collaborators:
            add_link(f"colab_{rc.employee_id}", f"routine_{rc.routine_id}", "atua na rotina", "direct")

        journey_blocks = (
            WorkJourneyBlock.query.join(Employee, Employee.id == WorkJourneyBlock.employee_id)
            .filter(
                WorkJourneyBlock.company_id == company_id,
                WorkJourneyBlock.is_active.is_(True),
                Employee.company_id == company_id,
            )
            .all()
        )
        for block in journey_blocks:
            add_node(
                f"capacity_{block.id}",
                block.name,
                "capacity",
                {
                    "employee_id": block.employee_id,
                    "block_mode": block.block_mode,
                    "start_time": block.start_time.strftime("%H:%M") if block.start_time else None,
                    "end_time": block.end_time.strftime("%H:%M") if block.end_time else None,
                    "accepted_item_types": list(block.accepted_item_types or []),
                },
            )
            add_link(f"colab_{block.employee_id}", f"capacity_{block.id}", "jornada", "direct")

        routine_bindings = (
            RoutineJourneyBinding.query.join(Routine, Routine.id == RoutineJourneyBinding.routine_id)
            .join(Employee, Employee.id == RoutineJourneyBinding.employee_id)
            .outerjoin(WorkJourneyBlock, WorkJourneyBlock.id == RoutineJourneyBinding.block_id)
            .filter(
                RoutineJourneyBinding.company_id == company_id,
                Routine.company_id == company_id,
                Employee.company_id == company_id,
            )
            .all()
        )
        for binding in routine_bindings:
            if binding.block_id:
                add_link(f"routine_{binding.routine_id}", f"capacity_{binding.block_id}", "alocada em bloco", "direct")

        indicators = Indicator.query.filter_by(company_id=company_id, is_active=True).all()
        ind_map_by_name = {ind.name.lower(): ind.id for ind in indicators}

        for ind in indicators:
            ind_node_id = f"ind_{ind.id}"
            add_node(ind_node_id, ind.name, "indicator", {"subtype": ind.indicator_type})

            if ind.responsible_id:
                add_link(f"colab_{ind.responsible_id}", ind_node_id, "responsável", "direct")

            if ind.collaborators and isinstance(ind.collaborators, list):
                for c_id in ind.collaborators:
                    try:
                        add_link(f"colab_{int(c_id)}", ind_node_id, "colaborador", "indirect")
                    except (ValueError, TypeError):
                        continue

            if ind.process_id:
                add_link(ind_node_id, f"proc_{ind.process_id}", "mede processo", "direct")
            elif ind.source_module == "process" and ind.source_id:
                add_link(ind_node_id, f"proc_{ind.source_id}", "fonte processo", "direct")

            if ind.project_id:
                add_link(ind_node_id, f"proj_{ind.project_id}", "mede projeto", "direct")
            elif ind.source_module == "project" and ind.source_id:
                add_link(ind_node_id, f"proj_{ind.source_id}", "fonte projeto", "direct")

            if ind.routine_id:
                add_link(ind_node_id, f"routine_{ind.routine_id}", "mede rotina", "direct")
            elif ind.source_module == "routine" and ind.source_id:
                add_link(ind_node_id, f"routine_{ind.source_id}", "fonte rotina", "direct")

        indicator_goals = (
            IndicatorGoal.query.join(Indicator, Indicator.id == IndicatorGoal.indicator_id)
            .filter(
                Indicator.company_id == company_id,
                IndicatorGoal.company_id == company_id,
                IndicatorGoal.status == "active",
            )
            .all()
        )
        for goal in indicator_goals:
            for routine_id in goal.routine_ids:
                add_link(f"ind_{goal.indicator_id}", f"routine_{routine_id}", "meta alimentada por rotina", "indirect")

        for proj in projects:
            if proj.kpis and isinstance(proj.kpis, list):
                for kpi_name in proj.kpis:
                    target_ind_id = ind_map_by_name.get(str(kpi_name).lower())
                    if target_ind_id:
                        add_link(f"ind_{target_ind_id}", f"proj_{proj.id}", "kpi projeto", "indirect")

        proc_execs = (
            db.session.query(ProcessInstanceCollaborator, ProcessInstance.process_id)
            .join(ProcessInstance, ProcessInstance.id == ProcessInstanceCollaborator.process_instance_id)
            .join(Employee, Employee.id == ProcessInstanceCollaborator.employee_id)
            .filter(
                Employee.company_id == company_id,
                ProcessInstance.company_id == company_id,
                ProcessInstanceCollaborator.is_deleted.isnot(True),
            )
            .all()
        )
        added_exec_links: set[str] = set()
        for exec_link, process_id in proc_execs:
            link_key = f"c{exec_link.employee_id}_p{process_id}"
            if link_key not in added_exec_links:
                add_link(f"colab_{exec_link.employee_id}", f"proc_{process_id}", "executor", "indirect")
                added_exec_links.add(link_key)

        proj_execs = (
            db.session.query(ProjectActivityCollaborator, ProjectTask.project_id)
            .join(ProjectTask, ProjectTask.id == ProjectActivityCollaborator.activity_id)
            .join(Project, Project.id == ProjectTask.project_id)
            .join(Employee, Employee.id == ProjectActivityCollaborator.employee_id)
            .filter(
                Project.company_id == company_id,
                Employee.company_id == company_id,
                ProjectActivityCollaborator.is_deleted.isnot(True),
            )
            .all()
        )
        added_proj_links: set[str] = set()
        for exec_link, project_id in proj_execs:
            link_key = f"c{exec_link.employee_id}_p{project_id}"
            if link_key not in added_proj_links:
                add_link(f"colab_{exec_link.employee_id}", f"proj_{project_id}", "membro", "indirect")
                added_proj_links.add(link_key)

        nodes_list = list(nodes.values())
        for node in nodes_list:
            degree = link_counter.get(node["id"], 0)
            node["degree"] = degree
            if degree == 0:
                node["health"] = "orphan"
            elif degree == 1:
                node["health"] = "fragile"
            else:
                node["health"] = "connected"

        return {
            "nodes": nodes_list,
            "links": links,
            "summary": {
                "total": len(nodes_list),
                "orphans": sum(1 for n in nodes_list if n["health"] == "orphan"),
                "fragile": sum(1 for n in nodes_list if n["health"] == "fragile"),
                "connected": sum(1 for n in nodes_list if n["health"] == "connected"),
                "by_type": {
                    ntype: sum(1 for n in nodes_list if n["type"] == ntype)
                    for ntype in sorted({n["type"] for n in nodes_list})
                },
            },
        }
