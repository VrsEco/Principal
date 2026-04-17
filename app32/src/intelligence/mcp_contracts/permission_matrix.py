from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .playbooks import APP32_SURFACE_PLAYBOOKS_MANIFEST, PlaybookSurface
from .profiles import APP32_PROFILE_CONTRACTS_MANIFEST, MCPMutationRisk, MCPProfileName


PermissionAction = Literal["discover", "read", "create", "update", "delete", "analyze", "audit"]
PermissionDomain = Literal[
    "routine",
    "processes",
    "projects",
    "meetings",
    "strategy",
    "finance",
    "governance",
    "analytics",
    "workload",
    "operations",
]


class PermissionDomainRule(_StrictModel):
    domain: PermissionDomain
    allowed_actions: list[PermissionAction] = Field(default_factory=list, min_length=1)
    denied_actions: list[PermissionAction] = Field(default_factory=list)
    max_risk_without_human_gate: MCPMutationRisk = "medium"
    requires_explicit_company_id: bool = False
    human_gate_for_actions: list[PermissionAction] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_rule(self):
        allowed = set(self.allowed_actions)
        denied = set(self.denied_actions)
        if allowed & denied:
            raise ValueError("Ações permitidas e negadas não podem se sobrepor na matriz.")
        if self.domain == "finance":
            if self.max_risk_without_human_gate not in {"low", "medium"}:
                raise ValueError("Matriz financeira deve declarar risco máximo sem gate como low/medium.")
            if not self.requires_explicit_company_id:
                raise ValueError("Domínio financeiro exige company_id explícito na matriz canônica.")
            finance_mutations = {"create", "update", "delete"}
            allowed_finance_mutations = finance_mutations.intersection(allowed)
            if allowed_finance_mutations and not allowed_finance_mutations.issubset(set(self.human_gate_for_actions)):
                raise ValueError("Mutações financeiras permitidas devem exigir gate humano na matriz.")
        if self.domain == "analytics" and any(action in allowed for action in {"create", "update", "delete"}):
            raise ValueError("Domínio analytics na matriz não pode liberar mutação.")
        if self.domain == "operations" and "audit" not in allowed:
            raise ValueError("Domínio operations deve manter trilha auditável explícita na matriz.")
        return self


class ProfilePermissionSurfaceMatrix(_StrictModel):
    profile: MCPProfileName
    surface: PlaybookSurface
    title: str = Field(min_length=8, max_length=160)
    summary: str = Field(min_length=16, max_length=360)
    domains: list[PermissionDomainRule] = Field(default_factory=list, min_length=1)
    default_scope: Literal["active_company", "explicit_company_id"] = "active_company"
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False

    @model_validator(mode="after")
    def _validate_matrix(self):
        if not self.tenant_scope_required:
            raise ValueError("Matriz de permissões exige tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Matriz de permissões não pode liberar SQL livre.")

        profile_contract = APP32_PROFILE_CONTRACTS_MANIFEST.get_profile(self.profile)
        if profile_contract is None:
            raise ValueError(f"Perfil não suportado na matriz: {self.profile}.")
        if self.surface not in profile_contract.allowed_surfaces:
            raise ValueError("Surface da matriz precisa existir no contrato do perfil.")

        playbook = APP32_SURFACE_PLAYBOOKS_MANIFEST.get_surface(self.surface)
        if playbook is None:
            raise ValueError(f"Surface playbook ausente para {self.surface}.")
        if self.default_scope != playbook.default_scope:
            raise ValueError("default_scope da matriz deve seguir o playbook da surface.")

        domains = [rule.domain for rule in self.domains]
        if len(domains) != len(set(domains)):
            raise ValueError("Domínio não pode se repetir na mesma matriz de profile/surface.")
        for rule in self.domains:
            if rule.domain not in set(profile_contract.allowed_domains):
                raise ValueError(f"Domínio {rule.domain} não permitido para o perfil {self.profile}.")
            if rule.domain not in set(playbook.allowed_domains):
                raise ValueError(f"Domínio {rule.domain} não permitido na surface {self.surface}.")
        if self.profile == "cliente":
            for rule in self.domains:
                if any(action in rule.allowed_actions for action in {"create", "update", "delete", "audit"}):
                    raise ValueError("Cliente não pode receber ações de mutação/auditoria na matriz.")
        if self.profile == "colaborador" and self.surface != "user":
            raise ValueError("Colaborador fica restrito à surface user na matriz.")
        if self.surface == "analytics":
            for rule in self.domains:
                if any(action in rule.allowed_actions for action in {"create", "update", "delete"}):
                    raise ValueError("Surface analytics na matriz deve permanecer read-only.")
        if self.surface == "ops" and self.profile != "admin_tecnico":
            raise ValueError("Surface ops na matriz fica restrita ao admin_tecnico.")
        return self


class PermissionMatrixManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.permission-matrix.v1", min_length=1, max_length=80)
    matrices: list[ProfilePermissionSurfaceMatrix] = Field(default_factory=list, min_length=1)

    def get_profile(self, profile: MCPProfileName | str) -> list[ProfilePermissionSurfaceMatrix]:
        normalized = str(profile or "").strip().lower()
        alias = "admin_tecnico" if normalized == "administrador_tecnico" else normalized
        return [matrix for matrix in self.matrices if matrix.profile == alias]

    def get_surface(self, surface: PlaybookSurface | str) -> list[ProfilePermissionSurfaceMatrix]:
        normalized = str(surface or "").strip().lower()
        return [matrix for matrix in self.matrices if matrix.surface == normalized]


PermissionMatrixEnvelope = MCPSuccessEnvelope[
    PermissionMatrixManifest | ProfilePermissionSurfaceMatrix | list[ProfilePermissionSurfaceMatrix]
]


def _rule(
    domain: PermissionDomain,
    allowed: list[PermissionAction],
    *,
    denied: list[PermissionAction] | None = None,
    max_risk_without_human_gate: MCPMutationRisk = "medium",
    requires_explicit_company_id: bool = False,
    human_gate_for_actions: list[PermissionAction] | None = None,
    notes: list[str] | None = None,
) -> PermissionDomainRule:
    return PermissionDomainRule(
        domain=domain,
        allowed_actions=allowed,
        denied_actions=denied or [],
        max_risk_without_human_gate=max_risk_without_human_gate,
        requires_explicit_company_id=requires_explicit_company_id,
        human_gate_for_actions=human_gate_for_actions or [],
        notes=notes or ["Seguir contratos MCP e policy engine como fonte de decisão final."],
    )


def build_permission_matrix_manifest() -> PermissionMatrixManifest:
    return PermissionMatrixManifest(
        matrices=[
            ProfilePermissionSurfaceMatrix(
                profile="colaborador",
                surface="user",
                title="Matriz de permissões MCP - Colaborador / User",
                summary="Colaborador atua na surface user com foco operacional, sem finanças, governança ou superfícies privilegiadas.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Pode operar rotina do tenant ativo sem bypass de escopo."]),
                    _rule("processes", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Processos estruturados seguem surface user com rastreabilidade operacional."]),
                    _rule("projects", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Projetos e tarefas seguem surface user e trilha auditável do sistema."]),
                    _rule("meetings", ["discover", "read", "create", "update"], denied=["delete", "audit"], notes=["Reuniões permitem preparação e atualização operacional."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], notes=["Estratégia para colaborador fica restrita à leitura e análise assistida."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="cliente",
                surface="user",
                title="Matriz de permissões MCP - Cliente / User",
                summary="Cliente atua apenas na surface user, com leitura guiada e sem mutações operacionais ou administrativas.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente consulta rotinas sem alterar dados."]),
                    _rule("processes", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente consulta processos em modo leitura, sem mutação."]),
                    _rule("projects", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Projetos do cliente são somente leitura."]),
                    _rule("meetings", ["discover", "read"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Acesso a reuniões é informativo, sem mutação."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="low", notes=["Cliente pode consultar diagnóstico estratégico sem alterar plano."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="user",
                title="Matriz de permissões MCP - Administrador / User",
                summary="Administrador também pode operar pela surface user quando o fluxo for funcional e não exigir privilégios exclusivos de admin/analytics.",
                default_scope="active_company",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Mutações destrutivas devem migrar para admin com confirmação."]),
                    _rule("processes", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Processos operacionais podem ser geridos na surface user sem admin global."]),
                    _rule("projects", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Projetos operacionais podem ser geridos na surface user."]),
                    _rule("meetings", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Reuniões seguem fluxo operacional comum."]),
                    _rule("strategy", ["discover", "read", "create", "update", "analyze"], denied=["delete"], notes=["Mudanças estratégicas sensíveis podem exigir redirecionamento para admin."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="admin",
                title="Matriz de permissões MCP - Administrador / Admin",
                summary="Administrador usa a surface admin para governança, mutações sensíveis e operações multiempresa com company_id explícito.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("routine", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Delete requer confirmação explícita."]),
                    _rule("processes", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Processos sensíveis exigem confirmação em exclusão e escopo explícito."]),
                    _rule("projects", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Projetos sensíveis pedem gate em exclusão."]),
                    _rule("meetings", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete"], requires_explicit_company_id=True, notes=["Exclusão de reunião deve ser excepcional e auditada."]),
                    _rule("strategy", ["discover", "read", "create", "update", "delete", "analyze", "audit"], human_gate_for_actions=["delete", "update"], requires_explicit_company_id=True, notes=["Mudanças estratégicas relevantes pedem confirmação humana."]),
                    _rule("finance", ["discover", "read", "create", "update", "delete", "analyze", "audit"], denied=[], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["create", "update", "delete"], notes=["Finanças exigem menor privilégio, company_id explícito e gate humano em mutações."]),
                    _rule("governance", ["discover", "read", "create", "update", "delete", "audit"], human_gate_for_actions=["delete", "update"], requires_explicit_company_id=True, notes=["Governança/admin deve preservar trilha de auditoria."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="administrador",
                surface="analytics",
                title="Matriz de permissões MCP - Administrador / Analytics",
                summary="Administrador usa analytics para leitura, diagnóstico e cruzamento permitido, sem mutar dados operacionais.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Analytics é estritamente read-only."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Estratégia analítica usa read models whitelisted."]),
                    _rule("finance", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["analyze"], notes=["Análises financeiras sensíveis podem exigir gate pela política vigente."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete", "audit"], requires_explicit_company_id=True, notes=["Workload é leitura analítica com company_id explícito e sem replanejamento implícito."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="admin_tecnico",
                surface="analytics",
                title="Matriz de permissões MCP - Admin Técnico / Analytics",
                summary="Admin técnico usa analytics para diagnóstico ampliado e observabilidade, sempre em modo leitura.",
                default_scope="explicit_company_id",
                domains=[
                    _rule("analytics", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Sem mutações em analytics."]),
                    _rule("strategy", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Diagnóstico estratégico técnico continua read-only."]),
                    _rule("finance", ["discover", "read", "analyze"], denied=["create", "update", "delete"], max_risk_without_human_gate="medium", requires_explicit_company_id=True, human_gate_for_actions=["analyze"], notes=["Acesso financeiro técnico continua auditado e sem SQL livre."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete"], requires_explicit_company_id=True, notes=["Workload técnico permanece read-only mesmo na analytics."]),
                ],
            ),
            ProfilePermissionSurfaceMatrix(
                profile="admin_tecnico",
                surface="ops",
                title="Matriz de permissões MCP - Admin Técnico / Ops",
                summary="Admin técnico usa a surface ops para incidentes, intervenção e suporte operacional com escopo mínimo e auditoria obrigatória.",
                default_scope="active_company",
                domains=[
                    _rule("operations", ["discover", "read", "create", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Operações devem manter evidência e rollback quando aplicável."]),
                    _rule("routine", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Ajustes operacionais via ops são restritos e auditáveis."]),
                    _rule("processes", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Intervenções em processos via ops são pontuais e auditáveis."]),
                    _rule("projects", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Projetos em ops são intervenções pontuais, não gestão ampla."]),
                    _rule("meetings", ["discover", "read", "update", "audit"], denied=["delete"], human_gate_for_actions=["update"], notes=["Reuniões em ops ocorrem apenas em contexto de incidente ou suporte."]),
                    _rule("workload", ["discover", "read", "analyze"], denied=["create", "update", "delete"], notes=["Ops pode diagnosticar capacidade do time sem alterar alocação pela própria surface."]),
                ],
            ),
        ]
    )


APP32_PERMISSION_MATRIX_MANIFEST = build_permission_matrix_manifest()


__all__ = [
    "APP32_PERMISSION_MATRIX_MANIFEST",
    "PermissionAction",
    "PermissionDomain",
    "PermissionDomainRule",
    "PermissionMatrixEnvelope",
    "PermissionMatrixManifest",
    "ProfilePermissionSurfaceMatrix",
    "build_permission_matrix_manifest",
]
