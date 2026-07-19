from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from typing import Any


class McpOperationRouterService:
    """Roteamento determinístico e econômico de pedidos operacionais do Sapiens."""

    ROUTES: tuple[dict[str, Any], ...] = (
        {
            "intent": "finance.payables_due",
            "domain": "finance",
            "harness_key": "harness_admfin_cliente_v1",
            "tool": "get_financial_payables_due_summary",
            "keywords": ("contas a pagar", "conta a pagar", "titulos a pagar", "titulo a pagar", "pagamentos a vencer", "fornecedores a pagar", "payables"),
        },
        {
            "intent": "finance.receivables_due",
            "domain": "finance",
            "harness_key": "harness_admfin_cliente_v1",
            "tool": "list_financial_entries",
            "keywords": ("contas a receber", "conta a receber", "titulos a receber", "titulo a receber", "recebimentos", "inadimplencia", "receivables"),
        },
        {
            "intent": "processes.hierarchy",
            "domain": "processes",
            "harness_key": "harness_operacional_cliente_v1",
            "tool": "list_process_hierarchy",
            "keywords": ("arquitetura de processos", "hierarquia de processos", "macroprocessos", "macroprocesso", "mapa de processos", "processos da empresa"),
        },
        {
            "intent": "processes.operations",
            "domain": "processes",
            "harness_key": "harness_operacional_cliente_v1",
            "tool": "get_my_work",
            "keywords": ("instancias de processo", "instancia de processo", "processos atrasados", "processos em andamento", "processos estao em andamento", "rotinas de processo"),
        },
        {
            "intent": "projects.list",
            "domain": "projects",
            "harness_key": "harness_operacional_cliente_v1",
            "tool": "list_projects",
            "keywords": ("projetos", "projeto", "programas de projetos", "projetos atrasados", "projetos criticos"),
        },
        {
            "intent": "routine.tasks",
            "domain": "routine",
            "harness_key": "harness_operacional_cliente_v1",
            "tool": "get_tasks_today",
            "keywords": ("minhas tarefas", "tarefas de hoje", "tarefas atrasadas", "atividades de hoje", "pendencias de hoje", "prioridades de hoje"),
        },
        {
            "intent": "strategy.plans",
            "domain": "strategy",
            "harness_key": "harness_coordenador_cliente_v1",
            "tool": "list_plans",
            "keywords": ("planejamento estrategico", "plano estrategico", "planos estrategicos", "planejamento de crescimento", "plano de crescimento"),
        },
        {
            "intent": "strategy.identity",
            "domain": "strategy",
            "harness_key": "harness_coordenador_cliente_v1",
            "tool": "get_strategy_identity_tool",
            "keywords": ("missao", "visao", "valores", "identidade organizacional", "posicionamento", "organograma"),
        },
        {
            "intent": "strategy.indicators",
            "domain": "strategy",
            "harness_key": "harness_coordenador_cliente_v1",
            "tool": "get_strategic_connection_metrics",
            "keywords": ("indicadores", "indicador", "metas", "okrs", "okr", "gestao estrategica", "teia de conexoes"),
        },
        {
            "intent": "commercial.dashboard",
            "domain": "commercial",
            "harness_key": "harness_comercial_cliente_v1",
            "tool": "get_commercial_dashboard",
            "keywords": ("vendas", "clientes", "funil comercial", "pipeline comercial", "propostas comerciais", "faturamento comercial"),
        },
        {
            "intent": "meetings.list",
            "domain": "meetings",
            "harness_key": "harness_operacional_cliente_v1",
            "tool": "list_meetings",
            "keywords": ("reunioes", "reuniao", "agenda de reunioes", "atas"),
        },
        {
            "intent": "consultive.front",
            "domain": "consultive",
            "harness_key": "harness_coordenador_cliente_v1",
            "tool": "consultive_get_front_context",
            "keywords": ("cockpit do consultor", "estruturacao empresarial", "maturidade da empresa", "frente consultiva", "necessidade urgente", "business review"),
        },
        {
            "intent": "identity.company",
            "domain": "identity_self_service",
            "harness_key": "harness_coordenador_cliente_v1",
            "tool": "get_company_profile",
            "keywords": ("dados da empresa", "cadastro da empresa", "perfil da empresa", "qual empresa", "empresa ativa"),
        },
    )

    DOMAIN_FALLBACKS: tuple[dict[str, Any], ...] = (
        {"domain": "finance", "harness_key": "harness_admfin_cliente_v1", "keywords": ("financeiro", "fluxo de caixa", "caixa", "saldo bancario", "banco", "orcamento", "dre", "receita", "despesa", "conciliacao", "pagamento", "recebimento", "faturamento")},
        {"domain": "processes", "harness_key": "harness_operacional_cliente_v1", "keywords": ("processo", "macroprocesso", "bpmn", "pop", "procedimento", "fluxo operacional", "auditoria de processo")},
        {"domain": "projects", "harness_key": "harness_operacional_cliente_v1", "keywords": ("projeto", "programa", "portfolio", "marco", "cronograma")},
        {"domain": "strategy", "harness_key": "harness_coordenador_cliente_v1", "keywords": ("estrategia", "estrategico", "planejamento", "meta", "indicador", "okr", "missao", "visao", "valor organizacional")},
        {"domain": "commercial", "harness_key": "harness_comercial_cliente_v1", "keywords": ("comercial", "venda", "cliente", "crm", "proposta", "pipeline", "funil", "negociacao")},
        {"domain": "routine", "harness_key": "harness_operacional_cliente_v1", "keywords": ("tarefa", "atividade", "pendencia", "prioridade", "rotina", "agenda")},
        {"domain": "meetings", "harness_key": "harness_operacional_cliente_v1", "keywords": ("reuniao", "ata", "pauta")},
        {"domain": "consultive", "harness_key": "harness_coordenador_cliente_v1", "keywords": ("consultivo", "consultoria", "maturidade", "estruturacao empresarial", "business review")},
    )
    @staticmethod
    def _normalize(value: str) -> str:
        folded = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = "".join(char for char in folded if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_value.lower()).strip()

    @staticmethod
    def _next_week(reference: date) -> tuple[date, date]:
        next_monday = reference + timedelta(days=(7 - reference.weekday()))
        return next_monday, next_monday + timedelta(days=6)

    @staticmethod
    def _current_week(reference: date) -> tuple[date, date]:
        monday = reference - timedelta(days=reference.weekday())
        return monday, monday + timedelta(days=6)

    @classmethod
    def _period_arguments(cls, normalized: str, reference: date) -> dict[str, str]:
        if "proxima semana" in normalized or "semana que vem" in normalized:
            start, end = cls._next_week(reference)
        elif "esta semana" in normalized or "semana atual" in normalized:
            start, end = cls._current_week(reference)
        elif "hoje" in normalized:
            start = end = reference
        else:
            return {}
        return {"date_from": start.isoformat(), "date_to": end.isoformat()}

    @classmethod
    def resolve(
        cls,
        *,
        request_text: str,
        company_id: int,
        current_harness_key: str | None = None,
        reference_date: date | None = None,
    ) -> dict[str, Any]:
        if not isinstance(company_id, int) or isinstance(company_id, bool) or company_id <= 0:
            raise ValueError("company_id deve ser um inteiro positivo.")
        normalized = cls._normalize(request_text)
        if len(normalized) < 3:
            raise ValueError("request_text deve descrever a solicitação operacional.")

        selected = None
        selected_score = 0
        for route in cls.ROUTES:
            score = max((len(keyword) for keyword in route["keywords"] if keyword in normalized), default=0)
            if score > selected_score:
                selected = route
                selected_score = score

        if selected is None:
            fallback = None
            fallback_score = 0
            for candidate in cls.DOMAIN_FALLBACKS:
                score = max((len(keyword) for keyword in candidate["keywords"] if keyword in normalized), default=0)
                if score > fallback_score:
                    fallback = candidate
                    fallback_score = score
            if fallback is not None:
                target_harness = fallback["harness_key"]
                switch_required = current_harness_key != target_harness
                return {
                    "route_status": "specialist_discovery",
                    "company_id": company_id,
                    "request_text": request_text,
                    "domain": fallback["domain"],
                    "intent": None,
                    "action": "discover",
                    "risk": "low",
                    "human_gate_required": False,
                    "target_harness_key": target_harness,
                    "harness_switch_required": switch_required,
                    "preferred_tool": None,
                    "arguments": {"company_id": company_id},
                    "execution_sequence": ["select_app32_session_harness_tool"] if switch_required else [],
                    "user_message": "Domínio identificado. Ative o especialista indicado e escolha uma tool executável no tools/list atualizado.",
                    "discovery_policy": "Atualizar tools/list uma única vez; não pesquisar catálogos planejados ou outros domínios.",
                }
            return {
                "route_status": "unsupported_fast_fallback",
                "company_id": company_id,
                "request_text": request_text,
                "domain": None,
                "intent": None,
                "action": "clarify",
                "risk": "low",
                "human_gate_required": False,
                "target_harness_key": current_harness_key or "harness_coordenador_cliente_v1",
                "harness_switch_required": False,
                "preferred_tool": None,
                "arguments": {"company_id": company_id},
                "user_message": "Não identifiquei uma operação MCP determinística para este pedido. Informe o objeto e o resultado desejado em uma frase.",
                "discovery_policy": "Não varrer catálogos nem capabilities planejadas.",
            }

        reference = reference_date or date.today()
        period = cls._period_arguments(normalized, reference)
        arguments: dict[str, Any] = {"company_id": company_id}
        if selected["intent"] == "finance.payables_due":
            arguments.update(
                {
                    "due_date_from": period.get("date_from"),
                    "due_date_to": period.get("date_to"),
                }
            )
        elif selected["intent"] == "finance.receivables_due":
            arguments.update(
                {
                    "entry_type": "receivable",
                    "due_date_from": period.get("date_from"),
                    "due_date_to": period.get("date_to"),
                }
            )
        elif selected["intent"] == "routine.tasks":
            arguments = {"scope": "me"}
        elif selected["intent"] == "processes.operations":
            arguments = {"scope": "company", "company_ids": str(company_id)}

        target_harness = selected["harness_key"]
        missing_arguments = [key for key, value in arguments.items() if key != "company_id" and value in (None, "")]
        route_status = "needs_input" if missing_arguments else "ready"
        sequence = []
        if current_harness_key != target_harness:
            sequence.append("select_app32_session_harness_tool")
        if route_status == "ready":
            sequence.append(selected["tool"])
        return {
            "route_status": route_status,
            "company_id": company_id,
            "request_text": request_text,
            "domain": selected["domain"],
            "intent": selected["intent"],
            "action": "read",
            "risk": "low",
            "human_gate_required": False,
            "target_harness_key": target_harness,
            "harness_switch_required": current_harness_key != target_harness,
            "preferred_tool": selected["tool"],
            "arguments": arguments,
            "period_interpretation": period or None,
            "missing_arguments": missing_arguments,
            "user_message": (
                "Informe o período desejado para concluir a consulta." if route_status == "needs_input" else None
            ),
            "execution_sequence": sequence,
            "discovery_policy": "Executar a tool preferencial; não pesquisar catálogos adjacentes.",
        }
