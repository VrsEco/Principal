from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import OnboardingDiagnoseInput, OnboardingStartInput


class OnboardingStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class OnboardingStatusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class OnboardingGoLiveCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class OnboardingGoLiveCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class OnboardingStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class OnboardingStartResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class OnboardingDiagnoseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: Dict[str, Any] = Field(default_factory=dict)
    active_company_id: Optional[int] = None
    user_id: int


class OnboardingDiagnoseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str


class OnboardingStatusExecutionHandler:
    def __init__(
        self,
        *,
        resolve_single_company_for_operation: Callable[[Dict[str, Any], Optional[int], int, bool], Tuple[Optional[int], Optional[str]]],
        load_company_by_id: Callable[[int], Any],
    ):
        self._resolve_single_company_for_operation = resolve_single_company_for_operation
        self._load_company_by_id = load_company_by_id

    def execute(self, request: OnboardingStatusRequest) -> OnboardingStatusResult:
        payload = dict(request.payload or {})
        selected_company_id, err = self._resolve_single_company_for_operation(
            payload,
            request.active_company_id,
            request.user_id,
            False,
        )
        if not selected_company_id:
            return OnboardingStatusResult(
                response_text=err or "Nao foi possivel identificar a empresa para o onboarding."
            )

        company = self._load_company_by_id(int(selected_company_id))
        if not company:
            return OnboardingStatusResult(response_text="Empresa nao encontrada.")

        field_map = [
            ("client_code", "Codigo da Empresa"),
            ("name", "Nome da Empresa"),
            ("segment", "Segmento"),
            ("city", "Cidade"),
            ("state", "Estado (UF)"),
            ("mission", "Missao"),
            ("vision", "Visao"),
            ("values", "Valores"),
        ]
        missing_labels = [label for field, label in field_map if not getattr(company, field, None)]
        total_fields = len(field_map)
        completed_fields = total_fields - len(missing_labels)
        progress_pct = int(round((completed_fields / total_fields) * 100)) if total_fields else 0

        label = (
            f"{getattr(company, 'client_code', '')} - {getattr(company, 'name', '')}"
            if getattr(company, "client_code", None)
            else str(getattr(company, "name", "") or "").strip()
        )
        if missing_labels:
            lines = [
                f"Status de onboarding da empresa {label}: INCOMPLETO",
                f"Progresso: {completed_fields}/{total_fields} campos ({progress_pct}%).",
                "",
                "Campos pendentes:",
            ]
            for idx, item in enumerate(missing_labels, start=1):
                lines.append(f"{idx}. {item}")
            lines.append("")
            lines.append("Sugestoes:")
            lines.append("1. Use menu 5.1 para diagnostico completo por objetivo.")
            lines.append("2. Use menu 5.3 para iniciar onboarding assistido (cadastro guiado).")
            return OnboardingStatusResult(response_text="\n".join(lines))

        return OnboardingStatusResult(
            response_text=(
                f"Status de onboarding da empresa {label}: COMPLETO.\n"
                f"Progresso: {completed_fields}/{total_fields} campos ({progress_pct}%).\n"
                "Os principais campos cadastrais estao preenchidos."
            )
        )


class OnboardingGoLiveCheckExecutionHandler:
    def __init__(
        self,
        *,
        resolve_single_company_for_operation: Callable[[Dict[str, Any], Optional[int], int, bool], Tuple[Optional[int], Optional[str]]],
        load_company_by_id: Callable[[int], Any],
        load_operational_metrics: Callable[[int], Dict[str, int]],
    ):
        self._resolve_single_company_for_operation = resolve_single_company_for_operation
        self._load_company_by_id = load_company_by_id
        self._load_operational_metrics = load_operational_metrics

    def execute(self, request: OnboardingGoLiveCheckRequest) -> OnboardingGoLiveCheckResult:
        payload = dict(request.payload or {})
        selected_company_id, err = self._resolve_single_company_for_operation(
            payload,
            request.active_company_id,
            request.user_id,
            False,
        )
        if not selected_company_id:
            return OnboardingGoLiveCheckResult(
                response_text=err or "Nao foi possivel identificar a empresa para o checklist de producao."
            )

        company = self._load_company_by_id(int(selected_company_id))
        if not company:
            return OnboardingGoLiveCheckResult(response_text="Empresa nao encontrada.")

        metrics = dict(self._load_operational_metrics(int(selected_company_id)) or {})
        active_employees = int(metrics.get("active_employees", 0) or 0)
        employees_with_any_contact = int(metrics.get("employees_with_any_contact", 0) or 0)
        projects_count = int(metrics.get("projects_count", 0) or 0)
        open_tasks_count = int(metrics.get("open_tasks_count", 0) or 0)
        processes_count = int(metrics.get("processes_count", 0) or 0)
        open_instances_count = int(metrics.get("open_instances_count", 0) or 0)
        meetings_count = int(metrics.get("meetings_count", 0) or 0)

        field_map = [
            ("client_code", "Codigo da Empresa"),
            ("name", "Nome da Empresa"),
            ("segment", "Segmento"),
            ("city", "Cidade"),
            ("state", "Estado (UF)"),
            ("mission", "Missao"),
            ("vision", "Visao"),
        ]
        missing_core = [label for field, label in field_map if not getattr(company, field, None)]

        blockers: List[str] = []
        warnings: List[str] = []

        if missing_core:
            blockers.append("Campos cadastrais essenciais pendentes: " + ", ".join(missing_core))
        if active_employees == 0:
            blockers.append("Nao ha colaboradores ativos vinculados a empresa.")
        if employees_with_any_contact == 0:
            blockers.append("Nenhum colaborador ativo possui contato para notificacoes.")
        elif active_employees > 0:
            coverage = employees_with_any_contact / active_employees
            if coverage < 0.4:
                warnings.append(f"Cobertura de contatos baixa ({employees_with_any_contact}/{active_employees}).")

        if projects_count == 0 and processes_count == 0:
            blockers.append("Nao ha projetos nem processos cadastrados para operacao.")
        else:
            if open_tasks_count == 0 and open_instances_count == 0:
                warnings.append("Nao ha atividades ou instancias em aberto para acompanhamento.")
            if meetings_count == 0:
                warnings.append("Nao ha reunioes cadastradas para registro de decisoes.")

        if blockers:
            go_live_status = "NAO PRONTO"
        elif warnings:
            go_live_status = "PRONTO COM ALERTAS"
        else:
            go_live_status = "PRONTO"

        company_label = (
            f"{getattr(company, 'client_code', '')} - {getattr(company, 'name', '')}"
            if getattr(company, "client_code", None)
            else str(getattr(company, "name", "") or "").strip()
        )
        lines = [
            f"Checklist de prontidao para producao - {company_label}",
            f"Status: {go_live_status}",
            "",
            "Resumo operacional:",
            f"- Colaboradores ativos: {active_employees}",
            f"- Colaboradores com contato: {employees_with_any_contact}",
            f"- Projetos: {projects_count} | Atividades abertas: {open_tasks_count}",
            f"- Processos: {processes_count} | Instancias abertas: {open_instances_count}",
            f"- Reunioes cadastradas: {meetings_count}",
        ]

        if blockers:
            lines.append("")
            lines.append("Bloqueadores:")
            for idx, item in enumerate(blockers, start=1):
                lines.append(f"{idx}. {item}")

        if warnings:
            lines.append("")
            lines.append("Alertas:")
            for idx, item in enumerate(warnings, start=1):
                lines.append(f"{idx}. {item}")

        lines.append("")
        if go_live_status == "PRONTO":
            lines.append("Conclusao: empresa apta para subir em producao e iniciar monitoramento.")
        elif go_live_status == "PRONTO COM ALERTAS":
            lines.append("Conclusao: pode subir em producao, mas com plano de ajuste fino durante estabilizacao.")
        else:
            lines.append("Conclusao: resolver bloqueadores antes da subida para producao.")

        return OnboardingGoLiveCheckResult(response_text="\n".join(lines))


class OnboardingStartExecutionHandler:
    def __init__(
        self,
        *,
        resolve_single_company_for_operation: Callable[[Dict[str, Any], Optional[int], int, bool], Tuple[Optional[int], Optional[str]]],
        create_session: Callable[[int, str, Optional[int]], Any],
    ):
        self._resolve_single_company_for_operation = resolve_single_company_for_operation
        self._create_session = create_session

    def execute(self, request: OnboardingStartRequest) -> OnboardingStartResult:
        payload = dict(request.payload or {})
        execution_input, input_error = OnboardingStartInput.build_from_legacy_payload(payload)
        if input_error:
            return OnboardingStartResult(response_text=input_error)
        if not execution_input:
            return OnboardingStartResult(response_text="Nao consegui interpretar o tipo do onboarding.")

        selected_company_id, _ = self._resolve_single_company_for_operation(
            payload,
            request.active_company_id,
            request.user_id,
            True,
        )

        session = self._create_session(
            request.user_id,
            execution_input.onboarding_type,
            selected_company_id,
        )

        if execution_input.onboarding_type == "real":
            prompt = "Para comecar o cadastro da empresa real, informe o CNPJ."
        else:
            prompt = "Vamos criar uma empresa modelo. Informe o nome da empresa exemplo."

        return OnboardingStartResult(
            response_text=(
                f"Sessao de onboarding iniciada com sucesso (ID {getattr(session, 'id', '-')}).\n"
                f"Tipo: {execution_input.onboarding_type}\n"
                f"{prompt}\n"
                "Quando quiser cancelar, responda: nao."
            )
        )


class OnboardingDiagnoseExecutionHandler:
    def __init__(
        self,
        *,
        resolve_single_company_for_operation: Callable[[Dict[str, Any], Optional[int], int, bool], Tuple[Optional[int], Optional[str]]],
        load_company_by_id: Callable[[int], Any],
        normalize_objective: Callable[[str], str],
        format_objective_label: Callable[[str], str],
        load_diagnostic_metrics: Callable[[int], Dict[str, int]],
    ):
        self._resolve_single_company_for_operation = resolve_single_company_for_operation
        self._load_company_by_id = load_company_by_id
        self._normalize_objective = normalize_objective
        self._format_objective_label = format_objective_label
        self._load_diagnostic_metrics = load_diagnostic_metrics

    def execute(self, request: OnboardingDiagnoseRequest) -> OnboardingDiagnoseResult:
        payload = dict(request.payload or {})
        selected_company_id, err = self._resolve_single_company_for_operation(
            payload,
            request.active_company_id,
            request.user_id,
            False,
        )
        if not selected_company_id:
            return OnboardingDiagnoseResult(
                response_text=err or "Nao foi possivel identificar a empresa para diagnostico."
            )

        company = self._load_company_by_id(int(selected_company_id))
        if not company:
            return OnboardingDiagnoseResult(response_text="Empresa nao encontrada.")

        execution_input, _ = OnboardingDiagnoseInput.build_from_legacy_payload(payload)
        objective_raw = execution_input.objective_raw
        objective = self._normalize_objective(objective_raw)
        metrics = dict(self._load_diagnostic_metrics(int(selected_company_id)) or {})

        active_employees = int(metrics.get("active_employees", 0) or 0)
        roles_count = int(metrics.get("roles_count", 0) or 0)
        projects_count = int(metrics.get("projects_count", 0) or 0)
        open_tasks_count = int(metrics.get("open_tasks_count", 0) or 0)
        processes_count = int(metrics.get("processes_count", 0) or 0)
        open_instances_count = int(metrics.get("open_instances_count", 0) or 0)
        meetings_count = int(metrics.get("meetings_count", 0) or 0)
        employees_with_telegram = int(metrics.get("employees_with_telegram", 0) or 0)
        employees_with_whatsapp = int(metrics.get("employees_with_whatsapp", 0) or 0)
        employees_with_email = int(metrics.get("employees_with_email", 0) or 0)
        employees_with_any_contact = int(metrics.get("employees_with_any_contact", 0) or 0)

        pending: List[str] = []
        suggestions: List[str] = []

        if not getattr(company, "client_code", None):
            pending.append("Definir codigo da empresa (client_code).")
        if not getattr(company, "segment", None):
            pending.append("Preencher segmento da empresa.")
        if not getattr(company, "city", None) or not getattr(company, "state", None):
            pending.append("Preencher cidade/estado da empresa.")
        if not getattr(company, "mission", None) or not getattr(company, "vision", None):
            pending.append("Preencher missao e visao.")

        if objective in {"afazeres", "projetos", "trabalho"}:
            if projects_count == 0:
                pending.append("Nao ha projetos cadastrados.")
                suggestions.append("Use menu 1.1 para criar o primeiro projeto.")
            if open_tasks_count == 0:
                pending.append("Nao ha atividades de projeto em aberto.")
                suggestions.append("Use menu 1.4 para cadastrar atividades.")

        if objective in {"processos"}:
            if processes_count == 0:
                pending.append("Nao ha processos cadastrados.")
                suggestions.append("Cadastre processos e rotinas antes de abrir instancias.")
            if open_instances_count == 0:
                pending.append("Nao ha instancias de processo em aberto.")
                suggestions.append("Use menu 2.1 para iniciar instancias.")

        if objective in {"reunioes"}:
            if meetings_count == 0:
                pending.append("Nao ha reunioes cadastradas.")
                suggestions.append("Use menu 4.1 para agendar reunioes.")
            if employees_with_any_contact == 0:
                pending.append("Nenhum colaborador possui contato (email/whatsapp/telegram) para convites.")
                suggestions.append("Atualize contatos no cadastro de colaboradores.")
            else:
                min_recommended = max(1, int(active_employees * 0.6)) if active_employees else 1
                if employees_with_any_contact < min_recommended:
                    pending.append(
                        f"Cobertura de contatos baixa para reunioes: {employees_with_any_contact}/{active_employees} colaboradores ativos com contato."
                    )
                    suggestions.append(
                        "Completar email/whatsapp/telegram dos colaboradores para melhorar convites e notificacoes."
                    )

        if objective in {"telegram"} and employees_with_telegram == 0:
            pending.append("Nenhum colaborador ativo possui Telegram cadastrado.")
            suggestions.append("Atualize o Telegram no perfil dos colaboradores.")

        if objective in {"whatsapp"} and employees_with_whatsapp == 0:
            pending.append("Nenhum colaborador ativo possui WhatsApp cadastrado.")
            suggestions.append("Atualize o WhatsApp no perfil dos colaboradores.")

        if objective in {"onboarding", "geral"}:
            if roles_count == 0:
                pending.append("Nao ha cargos/funcoes cadastrados.")
                suggestions.append("Cadastre ao menos um cargo para estruturar a equipe.")
            if active_employees == 0:
                pending.append("Nao ha colaboradores ativos vinculados.")
                suggestions.append("Vincule colaboradores ativos a empresa.")

        company_label = (
            f"{getattr(company, 'client_code', '')} - {getattr(company, 'name', '')}"
            if getattr(company, "client_code", None)
            else str(getattr(company, "name", "") or "").strip()
        )
        objective_label = self._format_objective_label(objective_raw or "geral")
        lines = [
            f"Diagnostico de funcionamento ({objective_label}) - {company_label}",
            "",
            "Resumo atual:",
            f"- Colaboradores ativos: {active_employees}",
            f"- Cargos: {roles_count}",
            f"- Projetos: {projects_count} | Atividades em aberto: {open_tasks_count}",
            f"- Processos: {processes_count} | Instancias em aberto: {open_instances_count}",
            f"- Reunioes: {meetings_count}",
            f"- Contatos: Telegram={employees_with_telegram}, WhatsApp={employees_with_whatsapp}, Email={employees_with_email}",
            "",
        ]

        if not pending:
            lines.append("Status: pronto para operacao no objetivo informado.")
            return OnboardingDiagnoseResult(response_text="\n".join(lines))

        lines.append("Pendencias para funcionar melhor:")
        for idx, item in enumerate(pending, start=1):
            lines.append(f"{idx}. {item}")

        if suggestions:
            lines.append("")
            lines.append("Proximos passos sugeridos:")
            for idx, item in enumerate(suggestions, start=1):
                lines.append(f"{idx}. {item}")

        return OnboardingDiagnoseResult(response_text="\n".join(lines))
