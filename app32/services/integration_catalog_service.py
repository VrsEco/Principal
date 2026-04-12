from __future__ import annotations

from copy import deepcopy
from typing import Any

from database.postgresql_db import list_integrations
from utils.integration_settings import normalize_service, resolve_service_config, SUPPORTED_SERVICES


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

    _SERVICE_SPECS = {
        "ai": {
            "title": "IA (OpenAI / Anthropic)",
            "category": "Inteligência",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "summary": "Conecta provedores de IA para gerar respostas e análises no APP32.",
            "description": "Integração de processamento cognitivo via API para tarefas de análise, síntese e suporte aos módulos.",
            "use_cases": [
                "Gerar análises e sugestões.",
                "Apoiar decisões com insights automatizados.",
                "Ativar modelos externos por webhook quando necessário.",
            ],
            "configuration_steps": [
                "Selecionar o provedor e registrar credenciais.",
                "Definir modelo, timeout e políticas de uso.",
                "Executar teste de conexão no console de IA.",
            ],
            "activation_requirements": [
                "API key válida do provedor.",
                "Políticas de uso e limites definidos.",
                "Perfil administrador autorizado.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Gestor de tecnologia/IA.",
            ],
            "governance": [
                "Evitar envio de dados sensíveis sem base legal.",
                "Auditoria obrigatória para prompts críticos.",
            ],
        },
        "email": {
            "title": "E-mail",
            "category": "Comunicação",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "summary": "Envia e recebe e-mails transacionais e operacionais.",
            "description": "Integração com SMTP/IMAP/POP3 ou webhook para mensagens corporativas.",
            "use_cases": [
                "Disparos operacionais e notificações.",
                "Recebimento de respostas por inbound.",
            ],
            "configuration_steps": [
                "Configurar provedor e credenciais.",
                "Definir remetente padrão e inbound.",
                "Validar envio/recebimento em teste.",
            ],
            "activation_requirements": [
                "Credenciais SMTP/IMAP válidas.",
                "Webhook público quando aplicável.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Operador autorizado.",
            ],
            "governance": [
                "Credenciais armazenadas com masking.",
                "Envios auditados por empresa.",
            ],
        },
        "whatsapp": {
            "title": "WhatsApp",
            "category": "Comunicação",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "summary": "Mensageria WhatsApp para comunicação operacional.",
            "description": "Integração com provedores (Z-API/Twilio) para envio e recebimento de mensagens.",
            "use_cases": [
                "Mensagens proativas e alertas.",
                "Recebimento de respostas por webhook.",
            ],
            "configuration_steps": [
                "Selecionar provedor e registrar credenciais.",
                "Configurar webhook de entrada.",
                "Executar teste de envio/recebimento.",
            ],
            "activation_requirements": [
                "Conta ativa no provedor.",
                "Webhook público.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Operador autorizado.",
            ],
            "governance": [
                "Mensagens auditadas e com opt-in.",
                "Restringir acesso às credenciais.",
            ],
        },
        "telegram": {
            "title": "Telegram",
            "category": "Comunicação",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "summary": "Canal Telegram para operações assistidas.",
            "description": "Integração com Bot API e webhook para comunicação em tempo real.",
            "use_cases": [
                "Notificações de eventos críticos.",
                "Recebimento de comandos/respostas.",
            ],
            "configuration_steps": [
                "Registrar bot e tokens.",
                "Configurar webhook seguro.",
                "Validar envio/recebimento.",
            ],
            "activation_requirements": [
                "Bot ativo com token válido.",
                "Webhook público quando necessário.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Operador autorizado.",
            ],
            "governance": [
                "Limitar uso a usuários autorizados.",
                "Auditar mensagens automatizadas.",
            ],
        },
        "instagram": {
            "title": "Instagram",
            "category": "Comunicação",
            "integration_mode": "bidirectional",
            "technical_channel": "api",
            "summary": "Canal Instagram para mensagens e notificações.",
            "description": "Integração com Graph API e webhooks Meta.",
            "use_cases": [
                "Responder mensagens e eventos.",
                "Fluxos de comunicação assistida.",
            ],
            "configuration_steps": [
                "Registrar credenciais Meta.",
                "Configurar webhook e validação.",
                "Executar teste de conexão.",
            ],
            "activation_requirements": [
                "Access token válido.",
                "Webhook público configurado.",
            ],
            "owner_profiles": [
                "Administrador da empresa.",
                "Operador autorizado.",
            ],
            "governance": [
                "Permissões alinhadas com políticas Meta.",
                "Auditoria de mensagens.",
            ],
        },
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
        # Canais de mensageria agora são listados individualmente via _SERVICE_SPECS.
    )

    @classmethod
    def build_catalog(cls) -> dict[str, Any]:
        items = [cls._decorate_item(deepcopy(item)) for item in cls._ITEMS]
        items = cls._merge_items(items, cls._build_service_items())
        items = cls._merge_items(items, cls._build_db_items(items))
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
        items = cls._merge_items(
            [cls._decorate_item(deepcopy(item)) for item in cls._ITEMS],
            cls._build_service_items(),
        )
        items = cls._merge_items(items, cls._build_db_items(items))
        for item in items:
            if item["key"] == normalized:
                return cls._decorate_item(deepcopy(item))
        return None

    @classmethod
    def _decorate_item(cls, item: dict[str, Any]) -> dict[str, Any]:
        item["integration_mode_label"] = cls._MODE_LABELS.get(item.get("integration_mode"), item.get("integration_mode"))
        item["technical_channel_label"] = cls._CHANNEL_LABELS.get(item.get("technical_channel"), item.get("technical_channel"))
        item["status_label"] = cls._STATUS_LABELS.get(item.get("status"), item.get("status"))
        return item

    @classmethod
    def _merge_items(cls, base: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = {item["key"] for item in base if item.get("key")}
        for item in extra:
            if not item.get("key") or item["key"] in seen:
                continue
            base.append(item)
            seen.add(item["key"])
        return base

    @classmethod
    def _build_service_items(cls) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for service in sorted(SUPPORTED_SERVICES):
            spec = cls._SERVICE_SPECS.get(service)
            if not spec:
                continue
            resolved = resolve_service_config(service)
            status = "available" if cls._is_configured(resolved) else "discovery"
            items.append(
                cls._decorate_item(
                    {
                        "key": f"service_{service}",
                        "status": status,
                        **spec,
                    }
                )
            )
        return items

    @classmethod
    def _build_db_items(cls, existing_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        existing_keys = {item.get("key") for item in existing_items}
        items: list[dict[str, Any]] = []
        try:
            records = list_integrations() or []
        except Exception:
            return items

        for record in records:
            record_id = str(record.get("id") or "").strip().lower()
            if not record_id:
                continue
            service = normalize_service(record.get("type"))
            if service in cls._SERVICE_SPECS:
                continue
            key = record_id if record_id not in existing_keys else f"db_{record_id}"
            provider = str(record.get("provider") or "").strip().lower()
            status = "available" if provider and provider != "disabled" else "discovery"
            items.append(
                cls._decorate_item(
                    {
                        "key": key,
                        "title": record.get("name") or record_id,
                        "category": "Configuração Técnica",
                        "integration_mode": "bidirectional",
                        "technical_channel": "api",
                        "status": status,
                        "summary": "Integração configurada via cadastro técnico.",
                        "description": "Registro importado do catálogo técnico existente.",
                        "use_cases": [],
                        "configuration_steps": [],
                        "activation_requirements": [],
                        "owner_profiles": [],
                        "governance": [],
                    }
                )
            )
        return items

    @staticmethod
    def _is_configured(resolved: dict[str, Any]) -> bool:
        provider = str(resolved.get("provider") or "").strip().lower()
        if not provider or provider == "disabled":
            return False
        if resolved.get("source") == "database":
            return True
        config = resolved.get("config") or {}
        for value in config.values():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return True
        return False
