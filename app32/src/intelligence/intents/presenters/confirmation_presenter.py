from __future__ import annotations

from ..schemas.operational_form import OperationalIntentForm


class OperationalIntentConfirmationPresenter:
    def build_confirmation_text(self, form: OperationalIntentForm) -> str:
        company_label = form.company_scope.company_labels[0] if form.company_scope.company_labels else None
        collaborator = form.subject_scope.responsible_names[0] if form.subject_scope.responsible_names else None
        period_label = form.filter_scope.period_label
        status = form.filter_scope.status or "consultar"
        entity = form.entity_type

        entity_label = {
            "project_task": "atividades",
            "process_instance": "instancias de processo",
            "meeting": "reunioes",
            "mixed": "itens operacionais",
        }.get(entity, "itens")

        parts = [f"Entendi que voce quer consultar {entity_label}"]
        if status == "open":
            parts[-1] += " em aberto"
        elif status == "overdue":
            parts[-1] += " atrasados"
        elif status == "completed":
            parts[-1] += " concluidos"
        elif status == "due_range":
            parts[-1] += " com foco no periodo solicitado"

        if collaborator:
            parts.append(f"do colaborador {collaborator}")
        if company_label:
            parts.append(f"na empresa {company_label}")
        if period_label:
            parts.append(f"considerando o periodo {period_label}")

        sentence = " ".join(parts).strip()
        return f"{sentence}. Posso continuar?"
