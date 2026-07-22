from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment

from services.plan_service import PlanService


class QueryList(list):
    def all(self):
        return list(self)


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def test_growth_report_context_builds_executive_governance_read_model():
    plan = ns(
        description="Crescer com rentabilidade e disciplina comercial.",
        progress=78,
        status="active",
        updated_at=datetime(2026, 7, 20, 10, 0),
    )
    drivers = [
        ns(description="Expansão regional", type="driver", priority="high"),
        ns(description="Dependência logística", type="threat", priority="high"),
    ]
    global_okrs = [ns(
        objective="Elevar receita recorrente", type="aceleracao", owner="Diretoria",
        deadline=date(2026, 6, 30),
        key_results=QueryList([ns(
            label="Crescer 20%", metric="Receita", target="20%", owner="Comercial",
            deadline=date(2026, 12, 31),
        )]),
    )]
    area_okrs = [ns(
        objective="Aumentar conversão", department="Comercial", owner=None,
        deadline=date(2026, 12, 31), key_results=QueryList([]),
    )]
    projects = [ns(
        code="TS.J.1", name="Expansão Nordeste", owner="Operações", status="in_progress",
        priority="high", progress=45, deadline=date(2026, 6, 30),
    )]
    participants = [ns(employee=ns(name="Ana Souza"), user=None, role="owner")]

    report = PlanService._build_growth_report_context(
        plan, drivers, global_okrs, area_okrs, projects, participants,
        today=date(2026, 7, 22),
    )

    assert report["status_label"] == "Ativo"
    assert report["stats"] == {
        "drivers": 2,
        "global_okrs": 1,
        "key_results": 1,
        "area_okrs": 1,
        "projects": 1,
        "participants": 1,
    }
    assert report["governance"]["high_risk_count"] == 1
    assert report["governance"]["overdue_count"] == 2
    assert report["governance"]["missing_owner_count"] == 1
    assert report["governance"]["active_projects"] == 1


def test_growth_report_template_is_valid_and_has_no_demo_content():
    template_path = Path(__file__).parents[1] / "templates" / "modules" / "plans" / "growth_report.html"
    source = template_path.read_text(encoding="utf-8")

    Environment().parse(source)

    assert "report_context" in source
    assert "Relatório Executivo" in source
    assert "Projetos estratégicos" in source
    assert "Expansão regional Nordeste" not in source
    assert "Crescimento de 30% no MRR" not in source
