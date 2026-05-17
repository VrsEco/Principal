from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel


CRUDDomain = Literal["routine", "projects", "processes", "meetings", "finance", "strategy"]
CRUDAction = Literal["create", "read", "update", "delete", "list", "analyze", "execute"]
CRUDRole = Literal["colaborador", "cliente", "administrador", "admin_tecnico"]
CRUDSurface = Literal["mcp_user", "mcp_admin", "mcp_analytics", "mcp_ops"]
CRUDImplementationStatus = Literal["contract", "implemented", "partial"]
CRUDRisk = Literal["low", "medium", "high", "critical"]


class CRUDOperationContract(_StrictModel):
    """Contrato canônico de uma operação CRUD MCP por domínio APP32."""

    domain: CRUDDomain
    action: CRUDAction
    operation: str = Field(min_length=1, max_length=160)
    entity: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=360)
    allowed_roles: list[CRUDRole] = Field(default_factory=list, min_length=1)
    required_permissions: list[str] = Field(default_factory=list, min_length=1)
    surface: CRUDSurface = "mcp_user"
    risk: CRUDRisk = "low"
    implementation_status: CRUDImplementationStatus = "contract"
    tenant_scope_required: bool = True
    read_only: bool | None = None
    human_gate_required: bool = False
    audit_required: bool = True

    @model_validator(mode="after")
    def _validate_contract_consistency(self):
        if not self.tenant_scope_required:
            raise ValueError("Operações MCP APP32 devem exigir tenant_scope_required=True.")
        expected_read_only = self.action in {"read", "list", "analyze"}
        if self.read_only is None:
            self.read_only = expected_read_only
        if self.read_only != expected_read_only:
            raise ValueError("read_only incompatível com a ação CRUD informada.")
        if self.action in {"delete", "execute"} and not self.human_gate_required:
            raise ValueError("delete/execute exigem human_gate_required=True.")
        if self.risk in {"high", "critical"} and not self.human_gate_required:
            raise ValueError("Operações high/critical devem exigir gate humano.")
        if self.domain == "finance" and self.action in {"create", "update"}:
            if self.risk not in {"medium", "high", "critical"}:
                raise ValueError("Mutações financeiras via MCP exigem ao menos risco medium.")
            if "cliente" in self.allowed_roles:
                raise ValueError("Cliente não deve receber mutação financeira direta via MCP.")
        if self.domain == "finance" and self.action in {"delete", "execute"}:
            if not self.human_gate_required:
                raise ValueError("Delete/execute financeiro exigem gate humano.")
            if self.risk not in {"high", "critical"}:
                raise ValueError("Delete/execute financeiro exigem risco high/critical.")
            if "cliente" in self.allowed_roles or "colaborador" in self.allowed_roles:
                raise ValueError("Delete/execute financeiro continuam restritos a perfis administrativos.")
        return self


class CRUDDomainContract(_StrictModel):
    """Manifesto de instrução por domínio para agentes MCP."""

    domain: CRUDDomain
    title: str = Field(min_length=1, max_length=140)
    description: str = Field(min_length=1, max_length=720)
    surface: CRUDSurface = "mcp_user"
    tenant_scope_required: bool = True
    operations: list[CRUDOperationContract] = Field(default_factory=list, min_length=1)

    @model_validator(mode="after")
    def _validate_domain_contract(self):
        if not self.tenant_scope_required:
            raise ValueError("Contratos CRUD MCP devem exigir tenant_scope_required=True.")
        for operation in self.operations:
            if operation.domain != self.domain:
                raise ValueError("Operação CRUD com domínio diferente do manifesto.")
        actions = {operation.action for operation in self.operations}
        missing = {"create", "read", "update", "delete", "list"} - actions
        if missing:
            raise ValueError(f"Manifesto CRUD incompleto para {self.domain}: {sorted(missing)}")
        return self


class CRUDContractsManifest(_StrictModel):
    """Manifesto consolidado dos contratos CRUD MCP do APP32."""

    version: str = Field(default="app32.mcp.crud-contracts.v1", min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=900)
    domains: list[CRUDDomainContract] = Field(default_factory=list, min_length=1)

    def get_domain(self, domain: CRUDDomain) -> CRUDDomainContract | None:
        normalized = str(domain).strip().lower()
        for contract in self.domains:
            if contract.domain == normalized:
                return contract
        return None


CRUDContractsResponseEnvelope = MCPSuccessEnvelope[CRUDContractsManifest]


def _operation(
    *,
    domain: CRUDDomain,
    action: CRUDAction,
    entity: str,
    description: str,
    roles: list[CRUDRole],
    permission: str,
    risk: CRUDRisk = "low",
    surface: CRUDSurface = "mcp_user",
    human_gate_required: bool = False,
    implementation_status: CRUDImplementationStatus = "contract",
) -> CRUDOperationContract:
    return CRUDOperationContract(
        domain=domain,
        action=action,
        operation=f"{domain}.{entity}.{action}",
        entity=entity,
        description=description,
        allowed_roles=roles,
        required_permissions=[permission],
        surface=surface,
        risk=risk,
        implementation_status=implementation_status,
        tenant_scope_required=True,
        human_gate_required=human_gate_required,
        audit_required=True,
    )


def _domain_contract(
    *,
    domain: CRUDDomain,
    title: str,
    description: str,
    entity: str,
    mutation_roles: list[CRUDRole],
    read_roles: list[CRUDRole],
    finance_sensitive: bool = False,
) -> CRUDDomainContract:
    admin_roles: list[CRUDRole] = ["administrador", "admin_tecnico"]
    mutating_roles = (
        ["colaborador", "administrador", "admin_tecnico"] if finance_sensitive else mutation_roles
    )
    reading_roles = (
        ["colaborador", "administrador", "admin_tecnico"] if finance_sensitive else read_roles
    )
    create_update_risk: CRUDRisk = "medium" if finance_sensitive else "medium"
    delete_risk: CRUDRisk = "critical" if finance_sensitive else "high"
    surface: CRUDSurface = "mcp_user"

    operations = [
        _operation(
            domain=domain,
            action="list",
            entity=entity,
            description=f"Lista registros de {title} filtrados pelo company_id acessível ao ator.",
            roles=reading_roles,
            permission=f"{domain}.read",
            surface=surface,
            implementation_status="partial",
        ),
        _operation(
            domain=domain,
            action="read",
            entity=entity,
            description=f"Lê um registro de {title} sem cruzar tenants.",
            roles=reading_roles,
            permission=f"{domain}.read",
            surface=surface,
            implementation_status="partial",
        ),
        _operation(
            domain=domain,
            action="create",
            entity=entity,
            description=f"Cria registro de {title} com validação strict e auditoria MCP.",
            roles=mutating_roles,
            permission=f"{domain}.create",
            risk=create_update_risk,
            surface=surface,
            human_gate_required=False,
            implementation_status="partial",
        ),
        _operation(
            domain=domain,
            action="update",
            entity=entity,
            description=f"Atualiza registro de {title} preservando escopo por company_id.",
            roles=mutating_roles,
            permission=f"{domain}.update",
            risk=create_update_risk,
            surface=surface,
            human_gate_required=False,
            implementation_status="partial",
        ),
        _operation(
            domain=domain,
            action="delete",
            entity=entity,
            description=f"Inativa ou remove registro de {title}; requer confirmação humana.",
            roles=admin_roles,
            permission=f"{domain}.delete",
            risk=delete_risk,
            surface="mcp_admin",
            human_gate_required=True,
        ),
        _operation(
            domain=domain,
            action="analyze",
            entity=entity,
            description=f"Cruza dados de {title} para análise read-only com filtros tenant-safe.",
            roles=reading_roles,
            permission=f"{domain}.analyze",
            risk="medium" if finance_sensitive else "low",
            surface="mcp_analytics" if finance_sensitive else surface,
        ),
    ]
    return CRUDDomainContract(
        domain=domain,
        title=title,
        description=description,
        surface=surface,
        tenant_scope_required=True,
        operations=operations,
    )


def build_app32_crud_contracts_manifest() -> CRUDContractsManifest:
    all_roles: list[CRUDRole] = ["colaborador", "cliente", "administrador", "admin_tecnico"]
    operational_roles: list[CRUDRole] = ["colaborador", "administrador", "admin_tecnico"]
    return CRUDContractsManifest(
        description=(
            "Contratos CRUD MCP por domínio para instruir agentes de IA sobre escopo, "
            "perfis, permissões, gates humanos e segurança multi-tenant no APP32."
        ),
        domains=[
            _domain_contract(
                domain="routine",
                title="Rotina / Processos",
                description="Rotinas, processos, instâncias de workflow e trabalho operacional.",
                entity="routine_process",
                mutation_roles=operational_roles,
                read_roles=all_roles,
            ),
            CRUDDomainContract(
                domain="projects",
                title="Projetos",
                description="Projetos e atividades com CRUD tenant-safe, auditoria MCP e soft delete para exclusões.",
                surface="mcp_user",
                tenant_scope_required=True,
                operations=[
                    _operation(
                        domain="projects",
                        action="list",
                        entity="project",
                        description="Lista projetos do tenant filtrando status e soft delete por company_id.",
                        roles=all_roles,
                        permission="project.read",
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="read",
                        entity="project",
                        description="Lê projetos do tenant sem cruzar empresas.",
                        roles=all_roles,
                        permission="project.read",
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="create",
                        entity="project",
                        description="Cria projeto com código EMPRESA.J.ID, validação strict e auditoria MCP.",
                        roles=operational_roles,
                        permission="project.create",
                        risk="medium",
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="update",
                        entity="project",
                        description="Atualiza projeto com whitelist de campos preservando o tenant.",
                        roles=operational_roles,
                        permission="project.update",
                        risk="medium",
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="delete",
                        entity="project",
                        description="Executa soft delete de projeto com gate humano explícito e trilha auditável.",
                        roles=["administrador", "admin_tecnico"],
                        permission="project.delete",
                        risk="high",
                        surface="mcp_admin",
                        human_gate_required=True,
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="delete",
                        entity="project_task",
                        description="Executa soft delete de atividade de projeto com gate humano e auditoria MCP.",
                        roles=["administrador", "admin_tecnico"],
                        permission="project.task.delete",
                        risk="high",
                        surface="mcp_admin",
                        human_gate_required=True,
                        implementation_status="implemented",
                    ),
                    _operation(
                        domain="projects",
                        action="analyze",
                        entity="project",
                        description="Cruza projetos e atividades para análise read-only com filtros tenant-safe.",
                        roles=all_roles,
                        permission="project.task.analyze",
                        implementation_status="implemented",
                    ),
                ],
            ),
            _domain_contract(
                domain="processes",
                title="Processos",
                description="Processos, fluxos, instâncias operacionais e cadastros associados ao domínio canônico de processos.",
                entity="process",
                mutation_roles=operational_roles,
                read_roles=all_roles,
            ),
            _domain_contract(
                domain="meetings",
                title="Reuniões",
                description="Agendamento, pauta, discussões, encerramento e atas de reunião.",
                entity="meeting",
                mutation_roles=operational_roles,
                read_roles=all_roles,
            ),
            _domain_contract(
                domain="finance",
                title="Finanças",
                description="Catálogos, lançamentos, orçamento, ingestão, conciliação e análises financeiras.",
                entity="financial_entry",
                mutation_roles=operational_roles,
                read_roles=all_roles,
                finance_sensitive=True,
            ),
            _domain_contract(
                domain="strategy",
                title="Estratégia",
                description="Planos, seções, diagnósticos, indicadores e cruzamentos estratégicos.",
                entity="strategy_plan",
                mutation_roles=operational_roles,
                read_roles=all_roles,
            ),
        ],
    )


APP32_CRUD_CONTRACTS_MANIFEST = build_app32_crud_contracts_manifest()


# Aliases de compatibilidade com a nomenclatura mais explícita usada no roadmap IA/MCP.
MCPCRUDDomain = CRUDDomain
MCPCRUDAction = CRUDAction
MCPActorRole = CRUDRole
MCPMutationRisk = CRUDRisk
MCPCRUDPermissionRule = CRUDOperationContract
MCPDomainCRUDManifest = CRUDDomainContract
MCPDomainCRUDManifestEnvelope = MCPSuccessEnvelope[CRUDDomainContract]
CRUD_DOMAIN_MANIFESTS = {
    contract.domain: contract for contract in APP32_CRUD_CONTRACTS_MANIFEST.domains
}


__all__ = [
    "APP32_CRUD_CONTRACTS_MANIFEST",
    "CRUDAction",
    "CRUDContractsManifest",
    "CRUDContractsResponseEnvelope",
    "CRUDDomain",
    "CRUDDomainContract",
    "CRUDImplementationStatus",
    "CRUDOperationContract",
    "CRUDRole",
    "CRUDSurface",
    "build_app32_crud_contracts_manifest",
    "MCPCRUDDomain",
    "MCPCRUDAction",
    "MCPActorRole",
    "MCPMutationRisk",
    "MCPCRUDPermissionRule",
    "MCPDomainCRUDManifest",
    "MCPDomainCRUDManifestEnvelope",
    "CRUD_DOMAIN_MANIFESTS",
]
