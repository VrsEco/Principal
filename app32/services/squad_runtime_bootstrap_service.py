from __future__ import annotations

from typing import Any

from src.intelligence.security.runtime_profiles import get_runtime_profile_spec


OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS = (
    "harness_coordenador_cliente_v1",
    "harness_comercial_cliente_v1",
    "harness_operacional_cliente_v1",
    "harness_admfin_cliente_v1",
)

OFFICIAL_SQUAD_CLIENTE_AGENTS = (
    {
        "key": "SC-COORD",
        "label": "Agente Coordenador",
        "mission": "Receber a demanda, preservar contexto, responder de forma simples quando possível e rotear apenas quando necessário.",
        "summary": "Entrada oficial, triagem e roteamento econômico do Squad Cliente.",
        "leads_when": [
            "a demanda ainda não está classificada",
            "o pedido pode ser resolvido sem especialista",
            "há necessidade de síntese final entre especialistas",
        ],
        "escalates_when": [
            "a demanda sai da operação local e vira revisão estrutural",
            "há bloqueio técnico ou defeito do APP32",
            "o custo de erro justifica deliberação especial",
        ],
    },
    {
        "key": "SC-COM",
        "label": "Agente Comercial",
        "mission": "Apoiar a relação da empresa com o mercado, a carteira, propostas, negociação, preço e oportunidades comerciais.",
        "summary": "Mercado, carteira, proposta, negociação e preço com ação comercial útil.",
        "leads_when": [
            "o usuário fala de clientes, propostas, funil ou negociação",
            "há leitura de oportunidades, churn, renovação ou expansão",
            "é preciso organizar contexto comercial para agir",
        ],
        "escalates_when": [
            "o tema vira posicionamento, portfólio ou estratégia comercial estrutural",
            "a decisão comercial afeta governança ou política corporativa",
        ],
    },
    {
        "key": "SC-OPS",
        "label": "Agente Operacional",
        "mission": "Apoiar execução assistida, rotina, backlog, tarefas, projetos, prioridades e cadência do dia a dia.",
        "summary": "Rotina, backlog, tarefas, projetos e execução assistida com objetividade.",
        "leads_when": [
            "o pedido é de organização, prioridade ou próximo passo",
            "há necessidade de cadência operacional e acompanhamento",
            "a demanda pede execução curta e direta",
        ],
        "escalates_when": [
            "o problema sai da rotina e exige redesenho estrutural",
            "há impedimento técnico do sistema",
        ],
    },
    {
        "key": "SC-ADM",
        "label": "Agente Adm/Financeiro",
        "mission": "Apoiar alertas, vencimentos, inadimplência, organização administrativa e leitura financeira segura sem operar mutação sensível.",
        "summary": "Alertas, vencimentos, inadimplência e contexto administrativo seguro.",
        "leads_when": [
            "o pedido fala de vencimento, cobrança, alerta ou organização administrativa",
            "é preciso preparar contexto financeiro seguro para decisão humana",
        ],
        "escalates_when": [
            "há mutação financeira sensível",
            "há necessidade de controladoria, auditoria ou governança privilegiada",
        ],
    },
)


class SquadRuntimeBootstrapService:
    """Serializa um bootstrap operacional curto e executável para runtimes externos."""

    @staticmethod
    def list_official_squad_cliente_agents() -> list[dict[str, Any]]:
        return [dict(item) for item in OFFICIAL_SQUAD_CLIENTE_AGENTS]

    @staticmethod
    def filter_official_squad_cliente_harnesses(harnesses: list[Any] | tuple[Any, ...]) -> list[Any]:
        allowed = set(OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS)
        filtered = [harness for harness in harnesses if getattr(harness, "key", None) in allowed]
        filtered.sort(
            key=lambda harness: OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS.index(getattr(harness, "key", ""))
            if getattr(harness, "key", None) in OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS
            else 999,
        )
        return filtered

    @classmethod
    def build_squad_cliente_bootstrap(
        cls,
        *,
        startup_tools: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        runtime_spec = get_runtime_profile_spec("squad_cliente")
        if runtime_spec is None:
            raise ValueError("Runtime profile squad_cliente não encontrado.")

        harnesses = cls.filter_official_squad_cliente_harnesses(list(runtime_spec.harnesses))
        startup = list(startup_tools or ())
        agents = cls.list_official_squad_cliente_agents()
        entry_agent = next((item for item in agents if item["key"] == "SC-COORD"), agents[0])

        return {
            "runtime_profile": "squad_cliente",
            "experience_label": "Sapiens Cliente",
            "canonical_label": "Squad Cliente",
            "official_phase_label": "Fase 1 oficial",
            "surface": runtime_spec.default_surface,
            "entry_agent": entry_agent,
            "startup_tools": startup,
            "token_policy": "economia de tokens por padrão",
            "routing_policy": {
                "default_order": [
                    "resposta_direta_segura",
                    "um_especialista",
                    "multiagente_por_excecao",
                    "modo_conselho_por_excecao",
                ],
                "guidance": [
                    "Responder diretamente quando o pedido for simples e seguro.",
                    "Acionar um único especialista antes de qualquer composição multiagente.",
                    "Usar multiagente apenas quando houver interdependência real.",
                    "Usar Modo Conselho somente quando o custo de erro for alto.",
                ],
            },
            "escalation_policy": {
                "squad_versus": [
                    "quando a demanda vira revisão estrutural, método, governança ou estratégia",
                    "quando o assunto sai da operação local e exige camada consultiva",
                ],
                "engineering": [
                    "quando houver erro técnico, limitação do APP32, falha de MCP ou defeito operacional",
                ],
            },
            "agents": agents,
            "harnesses": [
                {
                    "key": harness.key,
                    "label": harness.label,
                    "business_role": harness.business_role,
                }
                for harness in harnesses
            ],
            "guardrails": [
                "Operar apenas na surface user.",
                "Respeitar company_id explícito quando fornecido e nunca cruzar tenant.",
                "Não acessar admin, analytics ou ops a partir do Squad Cliente.",
                "Não tentar contornar restrições financeiras sensíveis.",
            ],
        }


__all__ = [
    "OFFICIAL_SQUAD_CLIENTE_AGENTS",
    "OFFICIAL_SQUAD_CLIENTE_HARNESS_KEYS",
    "SquadRuntimeBootstrapService",
]
