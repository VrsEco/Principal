import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from models.agent_menu import AgentMenuOption
from src.intelligence import menu_engine
from src.intelligence.workflows.contracts import WorkflowDiscoveryRequest, WorkflowMatch
from src.intelligence.workflows.registry import WorkflowRegistry
from src.intelligence.workflows.reranker import HeuristicWorkflowReranker


@dataclass
class DummySession:
    option: AgentMenuOption
    user_id: int = 10
    company_id: Optional[int] = None
    channel: str = 'whatsapp'
    thread_id: str = 'thread-regression'
    status: str = 'idle'
    selected_option_id: Optional[int] = None
    collected_data: Optional[Dict[str, Any]] = None
    missing_fields: Optional[List[Dict[str, Any]]] = None
    last_user_message: Optional[str] = None

    def __post_init__(self):
        self.collected_data = dict(self.collected_data or {})
        self.missing_fields = list(self.missing_fields or [])
        self._options = {self.option.id: self.option}

    @property
    def selected_option(self):
        return self._options.get(self.selected_option_id)


def build_option(*, option_id: int, code: str, title: str, action_key: str, required_fields=None, keywords=None):
    option = AgentMenuOption(
        code=code,
        title=title,
        action_key=action_key,
        required_fields=list(required_fields or []),
        keywords=list(keywords or []),
        is_active=True,
        sort_order=option_id,
    )
    option.id = option_id
    return option


def install_menu_patches(monkeypatch, session: DummySession, option: AgentMenuOption, *, company_choices=None, selection_payload=None):
    monkeypatch.setattr(menu_engine, '_ensure_default_menu_seed', lambda: None)
    monkeypatch.setattr(menu_engine, '_get_or_create_session', lambda **kwargs: session)
    monkeypatch.setattr(
        menu_engine,
        '_find_option_by_code',
        lambda company_id, code, include_inactive=False: option if code == option.code else None,
    )
    monkeypatch.setattr(menu_engine, '_list_children', lambda company_id, parent_id: [])
    monkeypatch.setattr(
        menu_engine,
        '_load_summary_company_choices',
        lambda user_id: company_choices or [
            {
                'index': 1,
                'company_id': 7,
                'company_name': 'Gandu Investimentos e Participações',
                'company_code': 'AU',
                'label': 'AU - Gandu Investimentos e Participações',
            },
            {
                'index': 2,
                'company_id': 6,
                'company_name': 'Ventana',
                'company_code': 'AV',
                'label': 'AV - Ventana',
            },
        ],
    )
    monkeypatch.setattr(
        menu_engine,
        '_resolve_explicit_company_id_from_payload',
        lambda payload, user_id: payload.get('_selected_company_id') or payload.get('_summary_company_id'),
    )
    monkeypatch.setattr(menu_engine, '_user_can_access_company', lambda user_id, company_id: True)
    monkeypatch.setattr(
        menu_engine,
        '_load_assisted_field_selection',
        lambda action, field_key, company_id, user_id: selection_payload,
    )
    monkeypatch.setattr(menu_engine, '_format_project_choice_line', lambda project_code: f'{project_code} - Projeto')
    monkeypatch.setattr(menu_engine.db.session, 'commit', lambda: None)
    monkeypatch.setattr(menu_engine.db.session, 'rollback', lambda: None)
    monkeypatch.setattr(menu_engine, '_format_root_menu', lambda company_id: 'ROOT MENU')


def run_whatsapp_turns(*, monkeypatch, option, turns, direct_executor, selection_payload=None, company_choices=None):
    session = DummySession(option=option)
    install_menu_patches(
        monkeypatch,
        session,
        option,
        company_choices=company_choices,
        selection_payload=selection_payload,
    )
    monkeypatch.setattr(menu_engine, '_try_execute_direct_option', direct_executor)
    results = []
    for message in turns:
        results.append(
            menu_engine.handle_menu_message(
                user_id=session.user_id,
                company_id=session.company_id,
                channel='whatsapp',
                thread_id=session.thread_id,
                message=message,
            )
        )
    return session, results


def discover_action(text: str, options):
    registry = WorkflowRegistry.from_menu_options(list(options))
    reranker = HeuristicWorkflowReranker()
    matches = [
        WorkflowMatch(workflow=workflow, score=10, reasons=[])
        for workflow in registry.list()
    ]
    reranked = reranker.rerank(
        WorkflowDiscoveryRequest(text=text, top_k=3, channel='whatsapp'),
        matches,
        registry,
    )
    if not reranked:
        return None, {"selected_action_key": None, "ranked_action_keys": []}
    telemetry = {
        "selected_action_key": reranked[0].workflow.action_key,
        "ranked_action_keys": [match.workflow.action_key for match in reranked],
        "selected_reasons": list(reranked[0].reasons),
    }
    return reranked[0].workflow.action_key, telemetry
