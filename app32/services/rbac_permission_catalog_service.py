from __future__ import annotations

from copy import deepcopy
from typing import Any


class RbacPermissionCatalogService:
    SCHEMA_VERSION = 2
    CATALOG_VERSION = "2026.05"
    META_KEYS = {"__schema_version__", "__catalog_version__"}

    ACTIONS = [
        {"key": "view", "label": "Visualizar", "short_label": "Ver"},
        {"key": "create", "label": "Incluir", "short_label": "Inc"},
        {"key": "edit", "label": "Alterar", "short_label": "Alt"},
        {"key": "delete", "label": "Excluir", "short_label": "Exc"},
        {"key": "approve", "label": "Aprovar", "short_label": "Apr"},
        {"key": "reject", "label": "Reprovar", "short_label": "Rep"},
        {"key": "assign", "label": "Atribuir", "short_label": "Atr"},
        {"key": "change_status", "label": "Alterar status", "short_label": "Status"},
        {"key": "replan", "label": "Replanejar prazo", "short_label": "Prazo"},
        {"key": "close", "label": "Encerrar", "short_label": "Enc"},
        {"key": "reopen", "label": "Reabrir", "short_label": "Reab"},
        {"key": "export", "label": "Exportar", "short_label": "Exp"},
    ]

    CATALOG = [
        {
            "key": "projects",
            "label": "Projetos",
            "description": "Gestão macro de projetos, pipeline, execução e governança.",
            "actions": ["view", "create", "edit", "delete", "approve", "change_status", "replan", "close", "reopen", "export"],
            "children": [
                {
                    "key": "projects.dashboard",
                    "label": "Dashboard",
                    "description": "Visão consolidada do módulo de projetos.",
                    "actions": ["view", "export"],
                },
                {
                    "key": "projects.portfolio",
                    "label": "Portfólio",
                    "description": "Lista, filtros e priorização de projetos.",
                    "actions": ["view", "create", "edit", "change_status", "export"],
                },
                {
                    "key": "projects.planning",
                    "label": "Planejamento",
                    "description": "Escopo, baseline, marcos e cronograma executivo.",
                    "actions": ["view", "create", "edit", "approve", "replan", "export"],
                },
                {
                    "key": "projects.phases",
                    "label": "Etapas / Fases",
                    "description": "Quebra do projeto por entregas, marcos e fases.",
                    "actions": ["view", "create", "edit", "delete", "change_status", "replan"],
                },
                {
                    "key": "projects.tasks",
                    "label": "Tarefas",
                    "description": "Backlog operacional, responsáveis e execução.",
                    "actions": ["view", "create", "edit", "delete", "assign", "change_status", "replan"],
                    "children": [
                        {
                            "key": "projects.tasks.board",
                            "label": "Quadro Kanban",
                            "description": "Gestão visual do fluxo de trabalho.",
                            "actions": ["view", "edit", "assign", "change_status"],
                        },
                        {
                            "key": "projects.tasks.list",
                            "label": "Lista de Tarefas",
                            "description": "Operação tabular e filtros por tarefa.",
                            "actions": ["view", "create", "edit", "delete", "assign", "change_status"],
                        },
                        {
                            "key": "projects.tasks.subtasks",
                            "label": "Subtarefas",
                            "description": "Quebra fina de execução.",
                            "actions": ["view", "create", "edit", "delete", "change_status"],
                        },
                        {
                            "key": "projects.tasks.comments",
                            "label": "Comentários",
                            "description": "Troca operacional na tarefa.",
                            "actions": ["view", "create", "edit", "delete"],
                        },
                    ],
                },
                {
                    "key": "projects.team",
                    "label": "Equipe",
                    "description": "Alocação de colaboradores e papéis no projeto.",
                    "actions": ["view", "create", "edit", "delete", "assign", "export"],
                },
                {
                    "key": "projects.hours",
                    "label": "Apontamentos de Horas",
                    "description": "Registro, validação e aprovação de horas.",
                    "actions": ["view", "create", "edit", "delete", "approve", "reject", "export"],
                },
                {
                    "key": "projects.costs",
                    "label": "Custos",
                    "description": "Lançamentos, aprovação de custos e visão financeira do projeto.",
                    "actions": ["view", "create", "edit", "delete", "approve", "reject", "export"],
                },
                {
                    "key": "projects.documents",
                    "label": "Documentos",
                    "description": "Anexos, evidências e artefatos do projeto.",
                    "actions": ["view", "create", "delete", "export"],
                },
                {
                    "key": "projects.risks",
                    "label": "Riscos / Impedimentos",
                    "description": "Mapeamento e tratamento de riscos do projeto.",
                    "actions": ["view", "create", "edit", "delete", "approve", "change_status", "export"],
                },
                {
                    "key": "projects.approvals",
                    "label": "Aprovações",
                    "description": "Workflow de aprovações operacionais e executivas.",
                    "actions": ["view", "approve", "reject", "export"],
                },
                {
                    "key": "projects.reports",
                    "label": "Relatórios",
                    "description": "Relatórios gerenciais, executivos e operacionais.",
                    "actions": ["view", "export"],
                },
            ],
        },
        {
            "key": "companies",
            "label": "Empresas",
            "description": "Cadastro e configuração das unidades/empresas.",
            "actions": ["view", "create", "edit", "delete"],
        },
        {
            "key": "processes",
            "label": "Processos",
            "description": "Arquitetura processual e BPMN.",
            "actions": ["view", "create", "edit", "delete", "approve", "export"],
        },
        {
            "key": "contracts",
            "label": "Contratos",
            "description": "Gestão de contratos e anexos contratuais.",
            "actions": ["view", "create", "edit", "delete", "approve", "export"],
        },
        {
            "key": "financial",
            "label": "Financeiro",
            "description": "Operação financeira e relatórios.",
            "actions": ["view", "create", "edit", "delete", "approve", "export"],
        },
        {
            "key": "meetings",
            "label": "Reuniões",
            "description": "Pautas, atas e cadência de reuniões.",
            "actions": ["view", "create", "edit", "delete", "export"],
        },
        {
            "key": "routines",
            "label": "Rotinas",
            "description": "Rotinas operacionais e recorrências.",
            "actions": ["view", "create", "edit", "delete", "approve"],
        },
    ]

    @classmethod
    def get_catalog(cls) -> dict[str, Any]:
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "catalog_version": cls.CATALOG_VERSION,
            "actions": deepcopy(cls.ACTIONS),
            "roots": deepcopy(cls.CATALOG),
        }

    @classmethod
    def action_keys(cls) -> set[str]:
        return {item["key"] for item in cls.ACTIONS}

    @classmethod
    def _iter_nodes(cls, nodes: list[dict[str, Any]]):
        for node in nodes or []:
            yield node
            yield from cls._iter_nodes(node.get("children") or [])

    @classmethod
    def node_map(cls) -> dict[str, dict[str, Any]]:
        if not hasattr(cls, "_node_map_cache"):
            cls._node_map_cache = {
                node["key"]: node for node in cls._iter_nodes(cls.CATALOG)
            }
        return cls._node_map_cache

    @classmethod
    def _normalize_actions(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        elif isinstance(value, dict):
            raw_items = [key for key, enabled in value.items() if enabled]
        else:
            return []

        allowed = cls.action_keys()
        normalized: list[str] = []
        for item in raw_items:
            key = str(item or "").strip().lower()
            if key and key in allowed and key not in normalized:
                normalized.append(key)
        return normalized

    @classmethod
    def normalize_payload(cls, payload: Any) -> dict[str, Any]:
        raw = payload if isinstance(payload, dict) else {}
        normalized: dict[str, Any] = {
            "__schema_version__": cls.SCHEMA_VERSION,
            "__catalog_version__": cls.CATALOG_VERSION,
        }

        flat_source = raw.get("permission_flat") if isinstance(raw.get("permission_flat"), dict) else None
        if flat_source:
            raw_items = flat_source.items()
        else:
            raw_items = raw.items()

        for resource_key, actions in raw_items:
            if resource_key in cls.META_KEYS or str(resource_key).startswith("__"):
                continue
            normalized_actions = cls._normalize_actions(actions)
            if normalized_actions:
                normalized[str(resource_key)] = normalized_actions

        return normalized

    @classmethod
    def permission_flat_map(cls, payload: Any) -> dict[str, list[str]]:
        normalized = cls.normalize_payload(payload)
        return {
            key: list(value)
            for key, value in normalized.items()
            if key not in cls.META_KEYS and not str(key).startswith("__")
        }

    @classmethod
    def summarize_permissions(cls, payload: Any) -> dict[str, Any]:
        flat = cls.permission_flat_map(payload)
        resource_count = sum(1 for _, actions in flat.items() if actions)
        granted_actions = sum(len(actions) for actions in flat.values())
        known_labels = []
        node_map = cls.node_map()
        for key in flat.keys():
            node = node_map.get(key)
            if node and node["label"] not in known_labels:
                known_labels.append(node["label"])
        return {
            "resources": resource_count,
            "actions": granted_actions,
            "highlights": known_labels[:4],
        }

    @classmethod
    def has_permission(cls, payload: Any, resource: str, action: str) -> bool:
        resource_key = str(resource or "").strip()
        action_key = str(action or "").strip().lower()
        if not resource_key or not action_key:
            return False
        flat = cls.permission_flat_map(payload)
        return action_key in flat.get(resource_key, [])

    @classmethod
    def tree_for_payload(cls, payload: Any) -> list[dict[str, Any]]:
        flat = cls.permission_flat_map(payload)

        def build(node: dict[str, Any]) -> dict[str, Any]:
            current_actions = flat.get(node["key"], [])
            children = [build(child) for child in node.get("children") or []]
            granted_count = len(current_actions)
            for child in children:
                granted_count += child["granted_count"]

            available_count = len(node.get("actions") or [])
            for child in children:
                available_count += child["available_count"]

            return {
                "key": node["key"],
                "label": node["label"],
                "description": node.get("description"),
                "actions": node.get("actions") or [],
                "selected_actions": current_actions,
                "granted_count": granted_count,
                "available_count": available_count,
                "children": children,
            }

        return [build(root) for root in cls.CATALOG]

    @classmethod
    def serialize_role(cls, role, *, include_tree: bool = False) -> dict[str, Any]:
        payload = role.to_dict()
        payload["permission_flat"] = cls.permission_flat_map(role.permissions)
        payload["permission_summary"] = cls.summarize_permissions(role.permissions)
        payload["permission_catalog_version"] = cls.CATALOG_VERSION
        if include_tree:
            payload["permission_tree"] = cls.tree_for_payload(role.permissions)
        return payload
