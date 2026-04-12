from __future__ import annotations

from copy import deepcopy
from typing import Any


class IntegrationCatalogService:
    """Catálogo consultivo de integrações API/MCP do APP32."""

    _MODE_LABELS = {
        "consume": "Consome dados",
        "provide": "Fornece dados",
        "bidirectional": "Bidirecional",
    }

    _CHANNEL_LABELS = {
        "api": "API",
        "mcp": "MCP",
        "api_mcp": "API + MCP",
    }

    _STATUS_LABELS = {
        "available": "Disponível",
        "planned": "Planejada",
        "discovery": "Em descoberta",
    }

    _ITEMS: tuple[dict[str, Any], ...] = (
        {
            "key": "open_finance",
            "title": "Open Finance",
            "category": "Financeiro",
            "integration_mode": "consume",
            "technical_channel": "api_mcp",
            "status": "planned",
            "summary": "Consome extratos, saldos e eventos bancários para análise, conciliação e automação financeira.",
            "description": "Integração orientada a ingestão controlada de dados bancários com trilha de auditoria e governança multi-tenant.",
            "use_cases": [
                "Importar extratos bancários para o módulo financeiro.",
                "Cruzar movimentações com lançamentos internos.",
                "Apoiar conciliação e classificação assistida.",
            ],
            "configuration_steps": [
                "Definir instituição/parceiro e objetivo de negócio.",
                "Configurar credenciais, escopo e homologação.",
                "Executar smoke e validar liberação operacional.",
            ],
            "activation_requirements": [
                "Credenciais do parceiro financeiro.",
                "Homologação da instituição e aprovação do escopo de dados.",
                "Perfil com permissão financeira e governança habilitada.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Responsável financeiro com permissão de integração.",
            ],
            "governance": [
                "Dados sensíveis exigem RBAC, auditoria e company_id obrigatório.",
                "Homologação antes da abertura em produção.",
            ],
        },
        {
            "key": "financial_data_api",
            "title": "Dados Financeiros do APP32",
            "category": "Financeiro",
            "integration_mode": "provide",
            "technical_channel": "api",
            "status": "planned",
            "summary": "Fornece dados financeiros autorizados do APP32 para sistemas externos.",
            "description": "Canal controlado para publicação de dados financeiros do tenant com filtros, contrato e observabilidade.",
            "use_cases": [
                "Entregar dados para BI externo.",
                "Disponibilizar relatórios financeiros para parceiros autorizados.",
            ],
            "configuration_steps": [
                "Definir escopo dos dados expostos.",
                "Configurar autenticação e filtros por empresa.",
                "Validar contrato e monitoramento.",
            ],
            "activation_requirements": [
                "Contrato de consumo aprovado.",
                "Definição clara de quais dados podem sair do tenant.",
                "Autenticação e observabilidade habilitadas.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Responsável por dados e compliance.",
            ],
            "governance": [
                "Não expor dados sem segregação multi-tenant.",
                "Exposição externa requer auditoria e política de acesso.",
            ],
        },
        {
            "key": "erp_accounting_bridge",
            "title": "ERP / Contábil",
            "category": "Backoffice",
            "integration_mode": "bidirectional",
            "technical_channel": "api_mcp",
            "status": "discovery",
            "summary": "Sincroniza dados contábeis e operacionais entre APP32 e ERP externo.",
            "description": "Ponte para consumo e fornecimento de dados contábeis com revisão humana em operações sensíveis.",
            "use_cases": [
                "Sincronizar plano de contas e centros de custo.",
                "Enviar lançamentos aprovados para ERP.",
                "Receber referências de documentos e status.",
            ],
            "configuration_steps": [
                "Mapear entidades e eventos envolvidos.",
                "Definir se o fluxo é consumo, fornecimento ou ambos.",
                "Validar chaves, callbacks e governança.",
            ],
            "activation_requirements": [
                "Mapeamento entre entidades do APP32 e do ERP.",
                "Homologação das regras financeiras sensíveis.",
                "Fluxo com trilha de auditoria e human gate quando necessário.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Time contábil/financeiro com autorização operacional.",
            ],
            "governance": [
                "Mutações com impacto financeiro devem manter human gate.",
                "Todo fluxo precisa de trilha origem/destino.",
            ],
        },
        {
            "key": "messaging_channels",
            "title": "Canais de Mensageria",
            "category": "Comunicação",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "status": "available",
            "summary": "Configura Telegram, WhatsApp, E-mail e Instagram para operação assistida.",
            "description": "Integrações já suportadas pelo sistema para entrada e saída de mensagens operacionais.",
            "use_cases": [
                "Enviar mensagens proativas do Sapiens.",
                "Receber respostas via webhook.",
                "Testar conectividade dos canais.",
            ],
            "configuration_steps": [
                "Selecionar o canal e o provider.",
                "Informar credenciais e endpoints necessários.",
                "Executar teste pelo console.",
            ],
            "activation_requirements": [
                "Credenciais válidas do provider.",
                "Webhook público quando exigido pelo canal.",
                "Perfil administrador ou operador autorizado.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Operador autorizado para canais de comunicação.",
            ],
            "governance": [
                "Credenciais devem ficar mascaradas e auditáveis.",
                "Somente perfis autorizados podem alterar canais ativos.",
            ],
        },
    )

    @classmethod
    def build_catalog(cls) -> dict[str, Any]:
        items = [cls._decorate_item(deepcopy(item)) for item in cls._ITEMS]
        return {
            "summary": {
                "total": len(items),
                "available": sum(1 for item in items if item["status"] == "available"),
                "planned": sum(1 for item in items if item["status"] == "planned"),
                "discovery": sum(1 for item in items if item["status"] == "discovery"),
            },
            "integrations": items,
        }

    @classmethod
    def get_integration(cls, key: str) -> dict[str, Any] | None:
        normalized = str(key or "").strip().lower()
        for item in cls._ITEMS:
            if item["key"] == normalized:
                return cls._decorate_item(deepcopy(item))
        return None

    @classmethod
    def _decorate_item(cls, item: dict[str, Any]) -> dict[str, Any]:
        item["integration_mode_label"] = cls._MODE_LABELS.get(item.get("integration_mode"), item.get("integration_mode"))
        item["technical_channel_label"] = cls._CHANNEL_LABELS.get(item.get("technical_channel"), item.get("technical_channel"))
        item["status_label"] = cls._STATUS_LABELS.get(item.get("status"), item.get("status"))
        return item
