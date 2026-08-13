from datetime import date

from sqlalchemy import func

from models import Project, ProjectTask, db


class ProjectTaskStatsService:
    """Entrega contadores agregados de atividades sem N+1 e sem cruzar empresas."""

    @staticmethod
    def empty():
        return {"total": 0, "open": 0, "completed": 0, "delayed": 0, "progress": 0}

    @classmethod
    def build_for_projects(cls, *, company_id, project_ids):
        scoped_ids = [int(project_id) for project_id in project_ids if project_id]
        if not company_id or not scoped_ids:
            return {}

        rows = (
            db.session.query(
                ProjectTask.project_id.label("project_id"),
                func.count(ProjectTask.id).label("total"),
                func.count(ProjectTask.id)
                .filter(ProjectTask.stage == "completed")
                .label("completed"),
                func.count(ProjectTask.id)
                .filter(
                    ProjectTask.stage != "completed",
                    ProjectTask.due_date.isnot(None),
                    ProjectTask.due_date < date.today(),
                )
                .label("delayed"),
            )
            .join(Project, Project.id == ProjectTask.project_id)
            .filter(
                Project.company_id == int(company_id),
                Project.is_deleted.is_(False),
                ProjectTask.project_id.in_(scoped_ids),
                ProjectTask.is_deleted.is_(False),
            )
            .group_by(ProjectTask.project_id)
            .all()
        )

        result = {}
        for row in rows:
            total = int(row.total or 0)
            completed = int(row.completed or 0)
            result[int(row.project_id)] = {
                "total": total,
                "open": total - completed,
                "completed": completed,
                "delayed": int(row.delayed or 0),
                "progress": round((completed / total) * 100) if total else 0,
            }
        return result
