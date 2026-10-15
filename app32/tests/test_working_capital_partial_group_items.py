from jinja2 import Environment, FileSystemLoader


def test_working_capital_partial_iterates_group_items_key_not_dict_method():
    env = Environment(loader=FileSystemLoader("templates"))
    group = {"code": "1.1", "label": "Caixa", "amount": "10,00", "items": [{"code": "1.1.1", "label": "Banco", "amount": "10,00"}]}
    report = {
        "title": "CCL", "subtitle": "", "report_slug": "capital-circulante-liquido", "generated_at": "", "filters": [], "general_info": [],
        "balance_sheet": {
            "asset": {"title": "Ativo", "current": {"title": "Circulante", "amount": "10,00", "groups": [group]}, "non_current": {"title": "ANC", "amount": "0,00"}},
            "liability": {"title": "Passivo", "current": {"title": "Circulante", "amount": "0,00", "groups": [group]}, "non_current": {"title": "PNC", "amount": "0,00"}, "equity": {"title": "PL", "amount": "0,00"}},
            "working_capital": {"title": "CCL", "amount": "10,00"},
            "patrimonial_status": {"title": "Situação", "amount": "0,00"},
        },
    }
    class Req:
        query_string = b""
    html = env.get_template("modules/financial/partials/report_view_working_capital.html").render(report=report, request=Req(), company_id=1)
    assert "1.1.1 - Banco" in html
