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


def test_global_formatter_exposes_indicator_value_and_dynamic_input_contract():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    content = open(os.path.join(root, "static", "js", "input_formatters.js"), encoding="utf-8").read()

    assert "function isCurrencyUnit(unit)" in content
    assert "function formatIndicatorValue(value, unit" in content
    assert "style: 'currency', currency: 'BRL'" in content
    assert "function setFormat(element, format)" in content
    assert "normalizeNumericText(value, { decimals, allowNegative: true" in content
    assert "if (!digits) return negative ? '-' : '';" in content


def test_indicator_goal_and_measurement_masks_preserve_negative_sign():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    for relative_path in (
        "templates/modules/indicators/indicator_goals.html",
        "templates/modules/indicators/indicator_data_list.html",
    ):
        content = open(os.path.join(root, *relative_path.split("/")), encoding="utf-8").read()
        assert 'inputmode="decimal"' in content
        assert 'return negative ? "-" : "";' in content
        assert 'return negative && formatted !== "0,00" ? `-${formatted}` : formatted;' in content


def test_indicator_surfaces_use_brazilian_value_formatting_contract():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    templates = {
        "templates/modules/processes/strategic_management_panel.html": [
            "formatIndicatorValue(item.goal, item.unit)",
            "formatIndicatorValue(item.current_value, item.unit)",
            "formatDate(item.measured_date, 'Sem medição')",
        ],
        "templates/modules/indicators/comparative_analysis.html": [
            "formatIndicatorValue(goal.goal_value, indicator.unit)",
            "formatIndicatorValue(item.averageValue, item.unit)",
        ],
        "templates/modules/processes/process_portal.html": [
            "formatIndicatorValue(item.current_value, item.unit)",
            "formatIndicatorValue(item.goal_value, item.unit)",
        ],
        "templates/modules/processes/process_portal_process_detail.html": [
            "formatIndicatorValue(item.current_value, item.unit)",
            "formatIndicatorValue(item.goal_value, item.unit)",
        ],
    }

    for relative_path, required_tokens in templates.items():
        content = open(os.path.join(root, *relative_path.split("/")), encoding="utf-8").read()
        for token in required_tokens:
            assert token in content


def test_indicator_direct_entry_uses_locale_aware_parsing_and_currency_mask():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    batch = open(
        os.path.join(root, "templates", "modules", "indicators", "indicator_batch_entry.html"),
        encoding="utf-8",
    ).read()
    details = open(
        os.path.join(root, "templates", "modules", "indicators", "indicator_details_v2.html"),
        encoding="utf-8",
    ).read()

    assert 'data-format="currency" class="cell-input val-real"' in batch
    assert "App32InputFormatters.normalizeForSubmit(realInput)" in batch
    assert "formatBatchCurrency" not in batch
    assert "App32InputFormatters?.setFormat" in details
    assert "modalMeasuredValue" in details
    assert "modalGoalValue" in details
