from __future__ import annotations

from typing import Any

from services.process_ai_execution_service import normalize_ai_contract_config


EXECUTION_MODE_ALIASES = {
    "manual_external": "manual_external",
    "human_task": "human_task",
    "automatic": "automatic",
    "external_rest": "api_task",
    "external_mcp": "mcp_task",
    "api_task": "api_task",
    "mcp_task": "mcp_task",
    "open_form": "open_form",
    "open_app32_page": "open_app32_page",
    "ai_task": "ai_task",
    "ai_decision": "ai_decision",
}

EXECUTION_MODE_CATALOG: dict[str, dict[str, Any]] = {
    "manual_external": {
        "label": "Controle manual externo",
        "group": "task",
        "handler_key": "process.manual_external",
        "interaction_mode": "shell",
    },
    "human_task": {
        "label": "Tarefa humana no APP",
        "group": "task",
        "handler_key": "process.human_task",
        "interaction_mode": "drawer",
    },
    "automatic": {
        "label": "Execução automática",
        "group": "task",
        "handler_key": "process.automatic",
        "interaction_mode": "headless",
    },
    "open_form": {
        "label": "Abrir formulário",
        "group": "task",
        "handler_key": "process.open_form",
        "interaction_mode": "drawer",
    },
    "open_app32_page": {
        "label": "Abrir tela do APP32",
        "group": "task",
        "handler_key": "process.open_app32_page",
        "interaction_mode": "page",
    },
    "api_task": {
        "label": "Chamar API",
        "group": "task",
        "handler_key": "process.api_task",
        "interaction_mode": "headless",
    },
    "mcp_task": {
        "label": "Executar MCP Tool",
        "group": "task",
        "handler_key": "process.mcp_task",
        "interaction_mode": "headless",
    },
    "ai_task": {
        "label": "AI Task",
        "group": "task",
        "handler_key": "process.ai.execute",
        "interaction_mode": "drawer",
    },
    "ai_decision": {
        "label": "AI Gateway",
        "group": "gateway",
        "handler_key": "process.ai.route",
        "interaction_mode": "shell",
    },
}

EXECUTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "approval_form_drawer",
        "label": "Abrir formulário de aprovação",
        "execution_mode": "open_form",
        "scope": "task",
        "summary": "Abre formulário APP32 em drawer com submit concluindo a activity.",
        "objective": "Abrir formulário de aprovação com dados do processo pré-preenchidos.",
        "ui_schema_json": {
            "form_code": "approval_review",
            "open_in": "drawer",
            "submit_action": "complete_task",
            "prefill_mapping": {
                "process_instance_id": "{instance_id}",
                "company_id": "{company_id}",
            },
        },
    },
    {
        "key": "finance_page_editor",
        "label": "Abrir tela financeira do APP32",
        "execution_mode": "open_app32_page",
        "scope": "task",
        "summary": "Abre editor de pré-lançamento financeiro com parâmetros do runtime.",
        "objective": "Abrir a tela financeira contextual do APP32 para continuidade operacional.",
        "ui_schema_json": {
            "page_code": "finance_prelaunch_editor",
            "open_in": "page",
            "params_mapping": {
                "document_id": "{document_id}",
                "company_id": "{company_id}",
            },
        },
    },
    {
        "key": "erp_api_post",
        "label": "Chamar API do ERP",
        "execution_mode": "api_task",
        "scope": "task",
        "summary": "Executa integração REST/HTTP para ERP com request mapping e retry padrão.",
        "objective": "Enviar dados operacionais para o ERP e registrar o retorno estruturado.",
        "rest_config_json": {
            "connection_key": "erp_financeiro",
            "method": "POST",
            "path": "/documents/prelaunch",
            "timeout_seconds": 20,
            "retry_policy": "default",
            "request_mapping": {
                "company_id": "{company_id}",
                "document_id": "{document_id}",
            },
            "response_schema": {"type": "object"},
        },
    },
    {
        "key": "mcp_register_document",
        "label": "Executar tool MCP de registro",
        "execution_mode": "mcp_task",
        "scope": "task",
        "summary": "Executa tool MCP do APP32 com input mapping governado.",
        "objective": "Executar tool MCP operacional para registrar ou movimentar o documento no APP32.",
        "mcp_config_json": {
            "tool_name": "finance.insert_prelaunch",
            "surface": "admin",
            "confirmation_mode": "auto",
            "input_mapping": {
                "company_id": "{company_id}",
                "document_id": "{document_id}",
            },
        },
    },
    {
        "key": "ai_extract_document",
        "label": "Extrair documento com IA",
        "execution_mode": "ai_task",
        "scope": "task",
        "summary": "Configura AI Task para leitura e extração estruturada de documentos.",
        "objective": "Leia o documento e extraia valor, data, fornecedor e histórico em JSON.",
        "ai_config_json": {
            "instruction": "Leia o documento e extraia valor, data, fornecedor e histórico em JSON válido.",
            "model_role": "expert",
            "tool_source": "mcp",
            "allowed_tools": ["documents.read"],
            "min_confidence": 0.85,
            "fallback_action": "human_review",
            "output_schema": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "issue_date": {"type": "string"},
                    "supplier_name": {"type": "string"},
                    "history": {"type": "string"},
                },
            },
        },
    },
    {
        "key": "ai_route_gateway",
        "label": "Roteamento com AI Gateway",
        "execution_mode": "ai_decision",
        "scope": "gateway",
        "summary": "Configura gateway com decisões fechadas e fallback humano.",
        "objective": "Classifique a rota do gateway entre as saídas permitidas com confiança mínima.",
        "ai_config_json": {
            "instruction": "Escolha exatamente uma rota entre as decisões permitidas.",
            "model_role": "expert",
            "tool_source": "none",
            "min_confidence": 0.8,
            "fallback_action": "human_review",
        },
    },
]


def normalize_execution_mode(value: str | None, *, default: str = "manual_external") -> str:
    normalized = str(value or default).strip().lower()
    canonical = EXECUTION_MODE_ALIASES.get(normalized)
    if not canonical:
        raise ValueError("Modo de execução inválido para a atividade.")
    return canonical


def get_execution_mode_catalog() -> dict[str, Any]:
    return {
        "task_modes": [
            _catalog_entry("human_task"),
            _catalog_entry("open_form"),
            _catalog_entry("open_app32_page"),
            _catalog_entry("api_task"),
            _catalog_entry("mcp_task"),
            _catalog_entry("ai_task"),
            _catalog_entry("manual_external"),
            _catalog_entry("automatic"),
        ],
        "gateway_modes": [
            _catalog_entry("ai_decision"),
            _catalog_entry("manual_external"),
        ],
        "interaction_modes": ["drawer", "modal", "page", "shell", "headless"],
        "api_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
        "form_targets": ["drawer", "modal", "page"],
        "page_targets": ["page", "drawer", "modal"],
        "submit_actions": ["complete_task", "stay_open", "trigger_next_step"],
        "retry_policies": ["none", "default", "aggressive"],
        "mcp_surfaces": ["user", "admin", "analytics"],
        "templates": get_execution_templates(),
    }


def get_execution_templates(*, scope: str | None = None) -> list[dict[str, Any]]:
    if not scope:
        return [dict(item) for item in EXECUTION_TEMPLATES]
    normalized_scope = str(scope).strip().lower()
    return [dict(item) for item in EXECUTION_TEMPLATES if item.get("scope") == normalized_scope]


def normalize_contract_configs(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload or {})
    execution_mode = normalize_execution_mode(data.get("execution_mode"))
    data["execution_mode"] = execution_mode

    catalog_entry = EXECUTION_MODE_CATALOG.get(execution_mode, {})
    if not data.get("auto_service_key") and catalog_entry.get("handler_key"):
        data["auto_service_key"] = catalog_entry["handler_key"]
    if not data.get("interaction_mode") and catalog_entry.get("interaction_mode"):
        data["interaction_mode"] = catalog_entry["interaction_mode"]

    data["ui_schema_json"] = normalize_ui_schema_config(
        data.get("ui_schema_json"),
        execution_mode=execution_mode,
        interaction_mode=data.get("interaction_mode"),
    )
    data["rest_config_json"] = normalize_rest_contract_config(
        data.get("rest_config_json"),
        execution_mode=execution_mode,
    )
    data["mcp_config_json"] = normalize_mcp_contract_config(
        data.get("mcp_config_json"),
        execution_mode=execution_mode,
    )
    data["ai_config_json"] = normalize_ai_contract_config(
        data.get("ai_config_json"),
        execution_mode=execution_mode,
    )
    return data


def normalize_ui_schema_config(
    value: dict[str, Any] | None,
    *,
    execution_mode: str | None = None,
    interaction_mode: str | None = None,
) -> dict[str, Any]:
    mode = normalize_execution_mode(execution_mode) if execution_mode else None
    raw = dict(value or {})
    if not raw and mode not in {"open_form", "open_app32_page"}:
        return {}

    normalized = {
        "interaction_mode": str(interaction_mode or raw.get("interaction_mode") or "").strip().lower() or None,
        "form_code": _optional_text(raw.get("form_code")),
        "page_code": _optional_text(raw.get("page_code")),
        "internal_url": _optional_text(raw.get("internal_url") or raw.get("url_template")),
        "submit_action": _optional_text(raw.get("submit_action")) or "complete_task",
        "prefill_mapping": _normalize_dict(raw.get("prefill_mapping")),
        "params_mapping": _normalize_dict(raw.get("params_mapping")),
        "readonly": bool(raw.get("readonly", False)),
        "open_in": _optional_text(raw.get("open_in")) or normalized_target(mode, interaction_mode, raw),
    }
    if mode == "open_form" and not normalized["form_code"]:
        raise ValueError("Configuração open_form exige form_code.")
    if mode == "open_app32_page" and not (normalized["page_code"] or normalized["internal_url"]):
        raise ValueError("Configuração open_app32_page exige page_code ou internal_url.")
    return {key: value for key, value in normalized.items() if value not in (None, {}, [])}


def normalize_rest_contract_config(
    value: dict[str, Any] | None,
    *,
    execution_mode: str | None = None,
) -> dict[str, Any]:
    mode = normalize_execution_mode(execution_mode) if execution_mode else None
    raw = dict(value or {})
    if not raw and mode != "api_task":
        return {}

    method = str(raw.get("method") or "POST").strip().upper()
    if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError("method da API deve ser GET, POST, PUT, PATCH ou DELETE.")

    normalized = {
        "connection_key": _optional_text(raw.get("connection_key")),
        "url": _optional_text(raw.get("url")),
        "path": _optional_text(raw.get("path")),
        "method": method,
        "timeout_seconds": _coerce_positive_int(raw.get("timeout_seconds"), default=20),
        "retry_policy": _optional_text(raw.get("retry_policy")) or "default",
        "headers": _normalize_dict(raw.get("headers")),
        "request_mapping": _normalize_dict(raw.get("request_mapping")),
        "response_schema": _normalize_dict(raw.get("response_schema")),
    }
    if mode == "api_task" and not (normalized["connection_key"] and (normalized["path"] or normalized["url"])):
        raise ValueError("Configuração api_task exige connection_key e path/url.")
    return {key: value for key, value in normalized.items() if value not in (None, {}, [])}


def normalize_mcp_contract_config(
    value: dict[str, Any] | None,
    *,
    execution_mode: str | None = None,
) -> dict[str, Any]:
    mode = normalize_execution_mode(execution_mode) if execution_mode else None
    raw = dict(value or {})
    if not raw and mode != "mcp_task":
        return {}

    normalized = {
        "tool_name": _optional_text(raw.get("tool_name")),
        "surface": _optional_text(raw.get("surface")) or "admin",
        "input_mapping": _normalize_dict(raw.get("input_mapping")),
        "confirmation_mode": _optional_text(raw.get("confirmation_mode")) or "auto",
    }
    if mode == "mcp_task" and not normalized["tool_name"]:
        raise ValueError("Configuração mcp_task exige tool_name.")
    return {key: value for key, value in normalized.items() if value not in (None, {}, [])}


def summarize_execution_mode_config(
    execution_mode: str | None,
    *,
    ui_schema_json: dict[str, Any] | None = None,
    rest_config_json: dict[str, Any] | None = None,
    mcp_config_json: dict[str, Any] | None = None,
    ai_config_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode = normalize_execution_mode(execution_mode)
    summary = {
        "execution_mode": mode,
        "label": EXECUTION_MODE_CATALOG.get(mode, {}).get("label", mode),
        "handler_key": EXECUTION_MODE_CATALOG.get(mode, {}).get("handler_key"),
        "open_form": mode == "open_form",
        "open_app32_page": mode == "open_app32_page",
        "api_task": mode == "api_task",
        "mcp_task": mode == "mcp_task",
        "ai_enabled": mode in {"ai_task", "ai_decision"},
    }
    if mode == "open_form":
        summary["form_code"] = (ui_schema_json or {}).get("form_code")
    if mode == "open_app32_page":
        summary["page_code"] = (ui_schema_json or {}).get("page_code")
        summary["internal_url"] = (ui_schema_json or {}).get("internal_url")
    if mode == "api_task":
        summary["connection_key"] = (rest_config_json or {}).get("connection_key")
        summary["method"] = (rest_config_json or {}).get("method")
        summary["path"] = (rest_config_json or {}).get("path") or (rest_config_json or {}).get("url")
    if mode == "mcp_task":
        summary["tool_name"] = (mcp_config_json or {}).get("tool_name")
        summary["surface"] = (mcp_config_json or {}).get("surface")
    if mode in {"ai_task", "ai_decision"}:
        summary["ai"] = {
            "tool_source": (ai_config_json or {}).get("tool_source"),
            "min_confidence": (ai_config_json or {}).get("min_confidence"),
        }
    return summary


def _catalog_entry(mode: str) -> dict[str, Any]:
    entry = dict(EXECUTION_MODE_CATALOG[mode])
    entry["key"] = mode
    return entry


def normalized_target(mode: str | None, interaction_mode: str | None, raw: dict[str, Any]) -> str:
    explicit = _optional_text(raw.get("open_in"))
    if explicit:
        return explicit
    if interaction_mode:
        return str(interaction_mode).strip().lower()
    if mode == "open_app32_page":
        return "page"
    return "drawer"


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_dict(value: Any) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        raise ValueError("Estrutura JSON inválida na configuração do executor.")
    return dict(value)


def _coerce_positive_int(value: Any, *, default: int) -> int:
    if value in (None, ""):
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Valor inteiro inválido na configuração do executor.") from exc
    if number <= 0:
        raise ValueError("Valor inteiro deve ser maior que zero.")
    return number
