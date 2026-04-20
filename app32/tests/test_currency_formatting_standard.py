import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.jinja_filters import format_currency_br


def test_format_currency_br_uses_brazilian_grouping():
    assert format_currency_br(1234.5) == "1.234,50"
    assert format_currency_br("1234567.891") == "1.234.567,89"
    assert format_currency_br("-1234.5") == "-1.234,50"


def test_format_currency_br_accepts_already_localized_input():
    assert format_currency_br("1.234,56") == "1.234,56"
    assert format_currency_br("0,1") == "0,10"


def test_base_templates_load_global_input_formatters():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for template in ("templates/base.html", "templates/layouts/base.html"):
        content = open(os.path.join(root, template), encoding="utf-8").read()
        assert "js/input_formatters.js" in content
