import logging
import re
from datetime import date, datetime
from typing import Any, Dict, Optional, Sequence, Tuple

from models import db
from models.company import Company
from models.employee import Employee
from models.project import Project, ProjectTask
from models.user import User

logger = logging.getLogger(__name__)


class ProjectTaskService:
    """Serviço determinístico para atividades de projeto."""

    @staticmethod
    def extract_id_from_code(code_value: str) -> Optional[int]:
        tokens = re.findall(r"\d+", code_value or "")
        if not tokens:
            return None
        try:
            return int(tokens[-1])
        except ValueError:
            return None

    @staticmethod
    def _sanitize_company_code(raw_value: Optional[str], company_id: Optional[int] = None) -> str:
        cleaned = "".join(ch for ch in str(raw_value or "").strip().upper() if ch.isalnum())
        if cleaned:
            return cleaned
        return str(company_id or "").zfill(2) or "00"

    @staticmethod
    def parse_project_code(code_value: str) -> Tuple[Optional[str], Optional[int]]:
        raw = str(code_value or "").strip()
        parts = raw.split(".")
        if len(parts) != 3 or parts[1] != "J":
            return None, None
        try:
            return parts[0].strip().upper(), int(parts[2])
        except (TypeError, ValueError):
            return parts[0].strip().upper(), None

    @staticmethod
    def parse_due_date(value: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
        raw = str(value or "").strip()
        if not raw:
            return None, None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).date(), None
            except ValueError:
                continue

        return None, "Data de prazo inválida. Use DD/MM/AAAA ou AAAA-MM-DD."

    @staticmethod
    def resolve_project_by_code(
        project_code: str,
        allowed_company_ids: Optional[Sequence[int]] = None,
    ) -> Tuple[Optional[Project], Optional[str]]:
        company_prefix, code_sequence = ProjectTaskService.parse_project_code(project_code)
        if not company_prefix or not code_sequence:
            return None, f"Não consegui identificar o projeto no código '{project_code}'."

        if allowed_company_ids is not None:
            normalized_company_ids = [int(cid) for cid in allowed_company_ids if cid]
            if not normalized_company_ids:
                return None, "Nenhuma empresa autorizada encontrada para criar a atividade."
        else:
            normalized_company_ids = None

        company_query = Company.query
        if normalized_company_ids is not None:
            company_query = company_query.filter(Company.id.in_(normalized_company_ids))

        companies = company_query.all()
        matched_company_ids = [
            company.id
            for company in companies
            if ProjectTaskService._sanitize_company_code(company.client_code or company.name[:2], company.id) == company_prefix
        ]

        if not matched_company_ids:
            return None, f"Empresa do código '{project_code}' não encontrada no contexto informado."

        query = Project.query.filter(
            Project.company_id.in_(matched_company_ids),
            Project.code_sequence == code_sequence,
        )

        project = query.first()
        if not project:
            return None, f"Projeto com código '{project_code}' não encontrado no contexto informado."

        return project, None

    @staticmethod
    def resolve_default_responsible(
        user_id: int,
        company_id: int,
    ) -> Tuple[Optional[int], str]:
        employee = (
            Employee.query.filter(
                Employee.user_id == user_id,
                Employee.company_id == company_id,
            )
            .order_by(Employee.id.asc())
            .first()
        )
        if employee and employee.name:
            return employee.id, str(employee.name).strip()

        user = User.query.get(user_id)
        if user and user.name:
            return None, str(user.name).strip()

        return None, "Não informado"

    @staticmethod
    def create_project_task(
        *,
        project_code: str,
        task_name: str,
        user_id: int,
        allowed_company_ids: Optional[Sequence[int]] = None,
        responsible_name: Optional[str] = None,
        due_date: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[str] = None,
        status: str = "planned",
        stage: str = "inbox",
        priority: str = "normal",
        notes: Optional[str] = None,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        normalized_name = str(task_name or "").strip()
        if not normalized_name:
            return None, "Não encontrei o nome da atividade. Informe no formato: nome_atividade: Nome da Atividade"

        project, error = ProjectTaskService.resolve_project_by_code(
            project_code=project_code,
            allowed_company_ids=allowed_company_ids,
        )
        if error:
            return None, error
        if not project:
            return None, "Projeto não encontrado para criar a atividade."

        parsed_due_date, due_date_error = ProjectTaskService.parse_due_date(due_date)
        if due_date_error:
            return None, due_date_error

        employee_id = None
        final_responsible_name = str(responsible_name or "").strip()
        if not final_responsible_name:
            employee_id, final_responsible_name = ProjectTaskService.resolve_default_responsible(
                user_id=user_id,
                company_id=project.company_id,
            )

        try:
            task = ProjectTask(
                project_id=project.id,
                what=normalized_name,
                who=final_responsible_name or None,
                employee_id=employee_id,
                due_date=parsed_due_date,
                how=(str(description).strip() if description else None),
                amount=(str(amount).strip() if amount else None),
                status=(str(status or "planned").strip() or "planned"),
                stage=(str(stage or "inbox").strip() or "inbox"),
                priority=(str(priority or "normal").strip() or "normal"),
                notes=(str(notes).strip() if notes else None),
            )
            db.session.add(task)
            db.session.flush()

            try:
                project.update_progress()
                db.session.flush()
            except Exception:
                logger.exception(
                    "Falha ao atualizar progresso do projeto %s após criar atividade %s",
                    project.id,
                    normalized_name,
                )

            company = Company.query.get(project.company_id)
            db.session.commit()
            return {
                "task": task,
                "project": project,
                "company": company,
                "responsible_name": final_responsible_name or "Não informado",
            }, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar atividade de projeto %s", normalized_name)
            return None, f"Erro ao cadastrar atividade de projeto: {str(exc)}"
