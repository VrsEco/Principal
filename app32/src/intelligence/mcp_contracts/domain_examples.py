from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from .base import MCPSuccessEnvelope, _StrictModel
from .profiles import MCPAllowedSurface, MCPMutationRisk, MCPProfileName


ExampleDomain = Literal["routine", "strategy", "finance"]
ExampleMode = Literal["read", "analyze", "mutate"]
ExampleStepKind = Literal["discover", "validate", "execute", "respond", "human_gate"]
CompanyScopeMode = Literal["active_company", "explicit_company_id"]


class MCPDomainExampleStep(_StrictModel):
    order: int = Field(ge=1, le=20)
    kind: ExampleStepKind
    tool_name: str | None = Field(default=None, min_length=3, max_length=120)
    purpose: str = Field(min_length=12, max_length=240)
    required_inputs: list[str] = Field(default_factory=list, min_length=1)
    expected_outcome: str = Field(min_length=12, max_length=240)


class MCPDomainExampleFlow(_StrictModel):
    example_id: str = Field(min_length=8, max_length=80)
    domain: ExampleDomain
    title: str = Field(min_length=8, max_length=140)
    intent: str = Field(min_length=16, max_length=360)
    surface: MCPAllowedSurface
    allowed_profiles: list[MCPProfileName] = Field(default_factory=list, min_length=1)
    mode: ExampleMode
    risk: MCPMutationRisk = "low"
    company_scope: CompanyScopeMode = "active_company"
    preconditions: list[str] = Field(default_factory=list, min_length=1)
    steps: list[MCPDomainExampleStep] = Field(default_factory=list, min_length=2)
    expected_response_shape: list[str] = Field(default_factory=list, min_length=2)
    blocked_by: list[str] = Field(default_factory=list, min_length=1)
    related_contracts: list[str] = Field(default_factory=list, min_length=2)
    related_analysis_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list, min_length=1)
    tenant_scope_required: bool = True
    sql_freeform_allowed: bool = False
    human_gate_required: bool = False

    @model_validator(mode="after")
    def _validate_example(self):
        if not self.tenant_scope_required:
            raise ValueError("Exemplos de domínio MCP exigem tenant_scope_required=True.")
        if self.sql_freeform_allowed:
            raise ValueError("Exemplos de domínio MCP não podem liberar SQL livre.")
        orders = [step.order for step in self.steps]
        if orders != list(range(1, len(self.steps) + 1)):
            raise ValueError("Os steps do exemplo devem usar ordem sequencial iniciando em 1.")
        required_contracts = {
            "src.intelligence.mcp_contracts.domain_playbooks",
            "src.intelligence.mcp_contracts.crud_domains",
        }
        if not required_contracts.issubset(set(self.related_contracts)):
            raise ValueError("Todo exemplo deve referenciar domain_playbooks e crud_domains.")
        if self.domain == "routine":
            if self.surface == "analytics":
                raise ValueError("Exemplo de rotina não deve usar surface analytics como fluxo principal.")
            if any(analysis_id.startswith("finance_") for analysis_id in self.related_analysis_ids):
                raise ValueError("Exemplo de rotina não pode apontar para análise financeira.")
        if self.domain == "strategy":
            if self.mode == "analyze" and self.surface != "analytics":
                raise ValueError("Exemplo analítico de strategy deve usar surface analytics.")
            if "strategy_plan_diagnostics" not in self.related_analysis_ids:
                raise ValueError("Exemplo de strategy deve referenciar strategy_plan_diagnostics.")
        if self.domain == "finance":
            if self.surface not in {"admin", "analytics"}:
                raise ValueError("Fluxos financeiros ficam restritos às surfaces admin/analytics.")
            if not set(self.allowed_profiles).issubset({"administrador", "admin_tecnico"}):
                raise ValueError("Fluxos financeiros ficam restritos a perfis administrativos.")
            if self.company_scope != "explicit_company_id":
                raise ValueError("Fluxos financeiros exigem company_id explícito.")
            if self.mode == "mutate" and not self.human_gate_required:
                raise ValueError("Mutação financeira exige human_gate_required=True.")
        return self


class MCPDomainExamplesManifest(_StrictModel):
    version: str = Field(default="app32.ai-mcp.domain-examples.v1", min_length=1, max_length=80)
    examples: list[MCPDomainExampleFlow] = Field(default_factory=list, min_length=1)

    def get_domain_examples(self, domain: ExampleDomain | str) -> list[MCPDomainExampleFlow]:
        normalized = str(domain or "").strip().lower()
        return [example for example in self.examples if example.domain == normalized]

    def get_example(self, example_id: str) -> MCPDomainExampleFlow | None:
        normalized = str(example_id or "").strip().lower()
        for example in self.examples:
            if example.example_id == normalized:
                return example
        return None

    @model_validator(mode="after")
    def _validate_manifest(self):
        domains = {example.domain for example in self.examples}
        if domains != {"routine", "strategy", "finance"}:
            raise ValueError("Manifesto de exemplos deve cobrir exatamente routine, strategy e finance.")
        example_ids = [example.example_id for example in self.examples]
        if len(example_ids) != len(set(example_ids)):
            raise ValueError("example_id deve ser único no manifesto.")
        return self


DomainExamplesEnvelope = MCPSuccessEnvelope[MCPDomainExamplesManifest | MCPDomainExampleFlow | list[MCPDomainExampleFlow]]


def _step(
    order: int,
    kind: ExampleStepKind,
    purpose: str,
    expected_outcome: str,
    *,
    tool_name: str | None = None,
    required_inputs: list[str] | None = None,
) -> MCPDomainExampleStep:
    return MCPDomainExampleStep(
        order=order,
        kind=kind,
        tool_name=tool_name,
        purpose=purpose,
        required_inputs=required_inputs or ["company_id"],
        expected_outcome=expected_outcome,
    )


def build_domain_examples_manifest() -> MCPDomainExamplesManifest:
    contracts_base = [
        "src.intelligence.mcp_contracts.domain_playbooks",
        "src.intelligence.mcp_contracts.crud_domains",
        "src.intelligence.mcp_contracts.playbooks",
        "src.intelligence.mcp_contracts.profiles",
    ]
    return MCPDomainExamplesManifest(
        examples=[
            MCPDomainExampleFlow(
                example_id="routine_create_work_item",
                domain="routine",
                title="Criar item operacional de rotina",
                intent="Demonstrar como um agente cria uma rotina/processo simples sem sair da surface user e sem perder o escopo do tenant.",
                surface="user",
                allowed_profiles=["colaborador", "administrador"],
                mode="mutate",
                risk="medium",
                company_scope="active_company",
                preconditions=[
                    "Usuário autenticado com empresa ativa válida.",
                    "Domínio routine suportado pela surface user.",
                ],
                steps=[
                    _step(1, "discover", "Listar capabilities disponíveis para confirmar surface e domínio.", "Capabilities user confirmadas.", tool_name="list_app32_capabilities", required_inputs=["surface", "company_id"]),
                    _step(2, "validate", "Consultar o contrato CRUD de routine antes da mutação.", "Operação create/list/read de routine validada.", tool_name="describe_app32_crud_contracts_tool", required_inputs=["domain", "company_id"]),
                    _step(3, "execute", "Executar a tool operacional permitida para criar o item de rotina.", "Item criado no tenant ativo com auditoria.", tool_name="routine.create_work_item", required_inputs=["company_id", "payload_validado"]),
                    _step(4, "respond", "Responder com a ação realizada, identificador criado e próximas pendências.", "Resposta auditável e objetiva entregue.", required_inputs=["result", "company_id"]),
                ],
                expected_response_shape=["acao_executada", "entity_id", "company_id", "pendencias"],
                blocked_by=["Ausência de company_id ativo.", "Perfil sem permissão routine.create.", "Contrato CRUD não encontrado para o domínio."],
                related_contracts=contracts_base,
                related_analysis_ids=[],
                notes=["Não usar finance/admin-only neste fluxo.", "Se houver privilégio técnico, redirecionar para admin ou ops."],
            ),
            MCPDomainExampleFlow(
                example_id="routine_list_processes",
                domain="routine",
                title="Listar processos e rotinas do tenant",
                intent="Demonstrar fluxo read-only para localizar processos e rotinas auditáveis dentro da empresa ativa.",
                surface="user",
                allowed_profiles=["colaborador", "cliente", "administrador"],
                mode="read",
                risk="low",
                company_scope="active_company",
                preconditions=["Empresa ativa confirmada.", "Atores com acesso ao domínio routine."],
                steps=[
                    _step(1, "discover", "Consultar capabilities habilitadas para a surface atual.", "Surface validada para leitura de routine.", tool_name="list_app32_capabilities", required_inputs=["surface", "company_id"]),
                    _step(2, "validate", "Consultar o contrato CRUD para mapear filtros e permissões de list/read.", "Filtros tenant-safe definidos.", tool_name="describe_app32_crud_contracts_tool", required_inputs=["domain", "company_id"]),
                    _step(3, "execute", "Executar listagem oficial do domínio filtrando pelo tenant ativo.", "Lista de processos retornada sem cruzar tenants.", tool_name="routine.list_processes", required_inputs=["company_id", "filters"]),
                    _step(4, "respond", "Responder com contagem, filtros e próximos passos permitidos.", "Resposta de leitura entregue com trilha de filtros.", required_inputs=["items", "filters"]),
                ],
                expected_response_shape=["row_count", "filters", "items", "next_actions"],
                blocked_by=["Empresa ativa ausente.", "Filtro inconsistente com o contrato.", "Tentativa de ampliar escopo além do tenant."],
                related_contracts=contracts_base,
                related_analysis_ids=[],
                notes=["Fluxo estritamente read-only.", "Não usar analytics para contornar ausência de contrato CRUD."],
            ),
            MCPDomainExampleFlow(
                example_id="strategy_plan_diagnostics_analysis",
                domain="strategy",
                title="Diagnóstico estratégico de plano",
                intent="Demonstrar uma análise estratégica oficial baseada em read model whitelisted e envelope com evidências.",
                surface="analytics",
                allowed_profiles=["administrador", "admin_tecnico"],
                mode="analyze",
                risk="medium",
                company_scope="explicit_company_id",
                preconditions=[
                    "company_id explícito informado.",
                    "plan_id conhecido e pertencente ao tenant.",
                    "Surface analytics disponível ao perfil."],
                steps=[
                    _step(1, "discover", "Ler o catálogo de análises permitidas para localizar strategy_plan_diagnostics.", "analysis_id oficial confirmado.", tool_name="describe_app32_allowed_analyses_tool", required_inputs=["company_id", "analysis_id"]),
                    _step(2, "validate", "Confirmar filtros mínimos, surface analytics e perfil autorizado.", "Escopo analítico validado sem mutação.", tool_name="describe_app32_profile_contracts_tool", required_inputs=["profile", "company_id"]),
                    _step(3, "execute", "Executar o read model estratégico autorizado para o plano alvo.", "Diagnóstico retornado com evidências e limitações.", tool_name="get_plan_diagnostics_read_model", required_inputs=["company_id", "plan_id"]),
                    _step(4, "respond", "Responder com diagnóstico, riscos, lacunas e limites do dado retornado.", "Resumo executivo auditável entregue.", required_inputs=["analysis_result", "company_id", "plan_id"]),
                ],
                expected_response_shape=["analysis_id", "filters", "diagnostic", "limitations", "evidence"],
                blocked_by=["company_id não explícito.", "analysis_id não permitido.", "Pedido de mutação pela surface analytics."],
                related_contracts=[*contracts_base, "src.intelligence.mcp_contracts.analysis_catalog"],
                related_analysis_ids=["strategy_plan_diagnostics"],
                notes=["Se o usuário quiser alterar o plano, redirecionar para user/admin.", "Não inventar métricas fora do envelope."],
            ),
            MCPDomainExampleFlow(
                example_id="strategy_analysis_to_mutation_redirect",
                domain="strategy",
                title="Redirecionar de análise estratégica para mutação segura",
                intent="Explicar quando um insight analítico precisa ser convertido em ação de mutação via surface adequada com confirmação explícita.",
                surface="admin",
                allowed_profiles=["administrador", "admin_tecnico"],
                mode="mutate",
                risk="high",
                company_scope="explicit_company_id",
                preconditions=["Diagnóstico estratégico já executado.", "Alteração desejada em plano/seção confirmada pelo responsável."],
                steps=[
                    _step(1, "discover", "Consultar o playbook de strategy para separar análise de mutação.", "Fluxo híbrido compreendido pelo agente.", tool_name="describe_app32_domain_playbooks_tool", required_inputs=["domain", "company_id"]),
                    _step(2, "validate", "Validar perfil admin e contrato CRUD da mutação desejada.", "Permissão e contrato confirmados.", tool_name="describe_app32_crud_contracts_tool", required_inputs=["domain", "company_id", "profile"]),
                    _step(3, "human_gate", "Solicitar confirmação humana antes da alteração estratégica sensível.", "Gate humano registrado.", required_inputs=["change_summary", "owner_confirmation"]),
                    _step(4, "execute", "Executar a mutação oficial do plano/seção pela surface admin.", "Alteração registrada com auditoria.", tool_name="update_plan_section", required_inputs=["company_id", "plan_id", "payload_validado"]),
                    _step(5, "respond", "Responder com mudança aplicada, impacto esperado e referências do diagnóstico original.", "Resposta final com trilha completa entregue.", required_inputs=["result", "analysis_reference"]),
                ],
                expected_response_shape=["acao_executada", "plan_id", "changed_fields", "analysis_reference", "audit"],
                blocked_by=["Ausência de confirmação humana.", "Perfil sem acesso admin.", "Tentativa de mutar sem contrato CRUD válido."],
                related_contracts=[*contracts_base, "src.intelligence.mcp_contracts.analysis_catalog"],
                related_analysis_ids=["strategy_plan_diagnostics"],
                notes=["Análise continua read-only; a mutação ocorre em outra surface.", "Não mutar pela surface analytics."],
                human_gate_required=True,
            ),
            MCPDomainExampleFlow(
                example_id="finance_cash_commitments_analysis",
                domain="finance",
                title="Consultar compromissos e pressão de caixa",
                intent="Demonstrar consulta financeira permitida, sempre com company_id explícito e via surface analytics.",
                surface="analytics",
                allowed_profiles=["administrador", "admin_tecnico"],
                mode="analyze",
                risk="high",
                company_scope="explicit_company_id",
                preconditions=["company_id explícito informado.", "Janela de datas válida.", "Perfil administrativo autenticado."],
                steps=[
                    _step(1, "discover", "Consultar contrato de perfis para confirmar acesso financeiro/analytics.", "Perfil validado para análise financeira.", tool_name="describe_app32_profile_contracts_tool", required_inputs=["profile", "company_id"]),
                    _step(2, "validate", "Ler o catálogo de análises permitidas e localizar finance_cash_commitments.", "analysis_id financeiro confirmado.", tool_name="describe_app32_allowed_analyses_tool", required_inputs=["analysis_id", "company_id"]),
                    _step(3, "human_gate", "Registrar que a análise financeira é sensível e pode exigir aprovação humana conforme política.", "Gate/política financeira registrados.", required_inputs=["company_id", "date_from", "date_to"]),
                    _step(4, "respond", "Responder com filtros, limitações, risco e status da capacidade analítica disponível.", "Retorno financeiro controlado e auditável entregue.", required_inputs=["company_id", "filters", "status"]),
                ],
                expected_response_shape=["analysis_id", "filters", "risk", "status", "limitations"],
                blocked_by=["Uso de surface user.", "Perfil não administrativo.", "company_id implícito ou ausente.", "Tentativa de SQL livre."],
                related_contracts=[*contracts_base, "src.intelligence.mcp_contracts.analysis_catalog"],
                related_analysis_ids=["finance_cash_commitments"],
                notes=["Mesmo planejada, a análise deve ser descrita de forma canônica.", "Nunca expor credenciais bancárias."],
                human_gate_required=True,
            ),
            MCPDomainExampleFlow(
                example_id="finance_mutation_requires_gate",
                domain="finance",
                title="Explicar por que mutação financeira exige gate humano",
                intent="Demonstrar fluxo administrativo de mutação financeira bloqueado até confirmação humana e validação rigorosa de escopo.",
                surface="admin",
                allowed_profiles=["administrador", "admin_tecnico"],
                mode="mutate",
                risk="critical",
                company_scope="explicit_company_id",
                preconditions=["company_id explícito confirmado.", "Operação financeira identificada como high/critical.", "Ator com perfil administrativo válido."],
                steps=[
                    _step(1, "discover", "Consultar contratos de perfil e domínio financeiro antes de qualquer mutação.", "Contexto financeiro sensível identificado.", tool_name="describe_app32_profile_contracts_tool", required_inputs=["profile", "company_id"]),
                    _step(2, "validate", "Ler contrato CRUD financeiro e identificar risco, permissão e gate exigido.", "Obrigatoriedade de gate humano confirmada.", tool_name="describe_app32_crud_contracts_tool", required_inputs=["domain", "company_id"]),
                    _step(3, "human_gate", "Solicitar e registrar aprovação humana antes de prosseguir.", "Gate humano aprovado e auditado.", required_inputs=["change_summary", "approver_id", "company_id"]),
                    _step(4, "execute", "Executar a mutação financeira autorizada pela surface admin.", "Mutação executada com trilha de auditoria.", tool_name="finance.execute_sensitive_change", required_inputs=["company_id", "payload_validado", "approval_reference"]),
                    _step(5, "respond", "Responder com decisão, evidência do gate e efeito da operação.", "Resposta final controlada entregue.", required_inputs=["result", "approval_reference"]),
                ],
                expected_response_shape=["acao_executada", "approval_reference", "risk", "audit", "result"],
                blocked_by=["Sem aprovação humana.", "Perfil fora de administrador/admin_tecnico.", "Tentativa de usar company_id implícito.", "Surface diferente de admin."],
                related_contracts=[*contracts_base, "src.intelligence.mcp_contracts.analysis_catalog"],
                related_analysis_ids=["finance_cash_commitments"],
                notes=["Toda mutação financeira é sensível e auditável.", "Nunca usar este fluxo em provider genérico sem aprovação humana."],
                human_gate_required=True,
            ),
        ]
    )


APP32_DOMAIN_EXAMPLES_MANIFEST = build_domain_examples_manifest()


__all__ = [
    "APP32_DOMAIN_EXAMPLES_MANIFEST",
    "CompanyScopeMode",
    "DomainExamplesEnvelope",
    "ExampleDomain",
    "ExampleMode",
    "ExampleStepKind",
    "MCPDomainExampleFlow",
    "MCPDomainExampleStep",
    "MCPDomainExamplesManifest",
    "build_domain_examples_manifest",
]
