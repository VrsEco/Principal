"""
Serviço de Dependências entre Atividades de Projeto.

Regras de Negócio:
- Tipo: finish_to_start (A concluída → B desbloqueada)
- Escopo: Mesmo projeto apenas
- Bloqueio: Soft (visual, sem impedir ação)
- Segurança: Multi-tenancy por company_id em toda query
- Anti-ciclo: Detecção via DFS (Depth-First Search) antes de persistir
"""

import logging
from typing import Dict, List, Optional, Tuple

from models import db
from models.project import ProjectTask, ProjectTaskDependency

logger = logging.getLogger(__name__)


class TaskDependencyService:
    """Serviço determinístico para gerenciar dependências entre atividades."""

    # ---------------------------------------------------------------------------
    # Validações Internas
    # ---------------------------------------------------------------------------

    @staticmethod
    def _get_task_or_error(
        task_id: int, company_id: int, project_id: int
    ) -> Tuple[Optional[ProjectTask], Optional[str]]:
        """Busca uma tarefa garantindo multi-tenancy e mesmo projeto."""
        task = (
            db.session.query(ProjectTask)
            .join(ProjectTask.project)
            .filter(
                ProjectTask.id == task_id,
                ProjectTask.project_id == project_id,
            )
            .first()
        )
        if not task:
            return None, f"Atividade #{task_id} não encontrada neste projeto."

        # Validação adicional de multi-tenancy via projeto
        from models.project import Project
        project = Project.query.filter_by(id=project_id, company_id=company_id).first()
        if not project:
            return None, "Projeto não encontrado para esta empresa."

        return task, None

    @staticmethod
    def _has_cycle_dfs(
        start_id: int,
        target_id: int,
        project_id: int,
        visited: Optional[set] = None,
    ) -> bool:
        """Detecta ciclo via DFS: verifica se `target_id` é alcançável a partir de `start_id`
        navegando pelas dependências existentes NO MESMO PROJETO.

        Se target_id → start_id existe (direto ou indireto), criar start_id → target_id
        formaria um ciclo.

        Args:
            start_id: A tarefa que seria o NOVO successor (successor_task_id).
            target_id: A tarefa que seria o NOVO predecessor (predecessor_task_id).
        """
        if visited is None:
            visited = set()

        if start_id in visited:
            return False

        visited.add(start_id)

        # Busca todos os predecessores de start_id (isto é, quem start_id depende)
        edges = (
            ProjectTaskDependency.query
            .filter_by(successor_task_id=start_id, project_id=project_id)
            .all()
        )

        for edge in edges:
            pred_id = edge.predecessor_task_id
            if pred_id == target_id:
                # Ciclo detectado: target_id é predecessora (direta ou indireta) de start_id
                # logo criar target_id → start_id (predecessor→successor) fecharia o ciclo
                return True
            if TaskDependencyService._has_cycle_dfs(pred_id, target_id, project_id, visited):
                return True

        return False

    # ---------------------------------------------------------------------------
    # Operações Públicas
    # ---------------------------------------------------------------------------

    @staticmethod
    def add_dependency(
        company_id: int,
        project_id: int,
        predecessor_task_id: int,
        successor_task_id: int,
        created_by_employee_id: Optional[int] = None,
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Adiciona uma dependência finish_to_start entre atividades do mesmo projeto.

        Validações:
        1. Auto-dependência (A→A)
        2. Ambas as tarefas pertencem ao mesmo project_id e company_id
        3. Duplicidade (constraint UNIQUE no banco)
        4. Ciclo via DFS
        """
        # 1. Auto-dependência
        if predecessor_task_id == successor_task_id:
            return None, "Uma atividade não pode depender de si mesma."

        # 2. Validação multi-tenancy + mesmo projeto para ambas as tarefas
        predecessor, err = TaskDependencyService._get_task_or_error(
            predecessor_task_id, company_id, project_id
        )
        if err:
            return None, f"Predecessora inválida: {err}"

        successor, err = TaskDependencyService._get_task_or_error(
            successor_task_id, company_id, project_id
        )
        if err:
            return None, f"Sucessora inválida: {err}"

        # 3. Verificar duplicidade antes de ir ao banco
        existing = ProjectTaskDependency.query.filter_by(
            predecessor_task_id=predecessor_task_id,
            successor_task_id=successor_task_id,
        ).first()
        if existing:
            return None, "Esta dependência já existe."

        # 4. Detecção de ciclo (DFS)
        # Verificamos se o predecessor_task_id é alcançável partindo do successor_task_id
        # (ou seja, se successor já é, direta ou indiretamente, predecessora de predecessor)
        if TaskDependencyService._has_cycle_dfs(
            start_id=predecessor_task_id,
            target_id=successor_task_id,
            project_id=project_id,
        ):
            return None, (
                "Esta dependência criaria um ciclo (A→B→C→A). "
                "Revise o mapa de dependências do projeto."
            )

        # Persistir
        try:
            dep = ProjectTaskDependency(
                company_id=company_id,
                project_id=project_id,
                predecessor_task_id=predecessor_task_id,
                successor_task_id=successor_task_id,
                created_by_employee_id=created_by_employee_id,
            )
            db.session.add(dep)
            db.session.commit()
            logger.info(
                "Dependência criada: predecessor=%s → successor=%s (projeto=%s, empresa=%s)",
                predecessor_task_id, successor_task_id, project_id, company_id,
            )
            return dep.to_dict(), None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao criar dependência de atividade")
            return None, f"Erro ao salvar dependência: {str(exc)}"

    @staticmethod
    def remove_dependency(
        company_id: int,
        dep_id: int,
    ) -> Tuple[bool, Optional[str]]:
        """Remove uma dependência garantindo multi-tenancy."""
        dep = ProjectTaskDependency.query.filter_by(
            id=dep_id,
            company_id=company_id,
        ).first()

        if not dep:
            return False, "Dependência não encontrada para esta empresa."

        try:
            db.session.delete(dep)
            db.session.commit()
            logger.info("Dependência %s removida (empresa=%s)", dep_id, company_id)
            return True, None
        except Exception as exc:
            db.session.rollback()
            logger.exception("Erro ao remover dependência %s", dep_id)
            return False, f"Erro ao remover dependência: {str(exc)}"

    @staticmethod
    def get_task_dependencies(
        company_id: int,
        task_id: int,
    ) -> Dict:
        """Retorna predecessoras e sucessoras de uma atividade.

        Returns:
            {
                "predecessors": [...],  # Tarefas que esta depende
                "successors": [...],    # Tarefas que dependem desta
                "is_blocked": bool,     # True se há predecessora não concluída
                "blocked_by": [...]     # Lista das predecessoras pendentes
            }
        """
        # Predecessoras: deps onde successor_task_id == task_id
        pred_deps = ProjectTaskDependency.query.filter_by(
            successor_task_id=task_id,
            company_id=company_id,
        ).all()

        # Sucessoras: deps onde predecessor_task_id == task_id
        succ_deps = ProjectTaskDependency.query.filter_by(
            predecessor_task_id=task_id,
            company_id=company_id,
        ).all()

        predecessors = [d.to_dict() for d in pred_deps]
        successors = [
            {
                "id": d.id,
                "successor_task_id": d.successor_task_id,
                "successor_what": d.successor.what if d.successor else None,
                "successor_stage": d.successor.stage if d.successor else None,
            }
            for d in succ_deps
        ]

        # Bloqueia se existir pelo menos uma predecessora com stage != 'completed'
        blocked_by = [
            p for p in predecessors
            if p.get("predecessor_stage") != "completed"
        ]

        return {
            "predecessors": predecessors,
            "successors": successors,
            "is_blocked": len(blocked_by) > 0,
            "blocked_by": blocked_by,
        }

    @staticmethod
    def check_task_is_blocked(company_id: int, task_id: int) -> bool:
        """Verificação rápida: retorna True se a tarefa tem predecessoras não concluídas."""
        pred_deps = ProjectTaskDependency.query.filter_by(
            successor_task_id=task_id,
            company_id=company_id,
        ).all()

        for dep in pred_deps:
            if dep.predecessor and dep.predecessor.stage != "completed":
                return True
        return False
