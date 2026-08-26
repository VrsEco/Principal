from types import SimpleNamespace

from utils.catalog_sort import natural_text_key, sort_catalog_entries


def test_natural_text_key_orders_numeric_code_segments_numerically():
    codes = ["AV.I.1.1.10", "AV.I.1.1.2", "AV.I.1.1.1"]

    assert sorted(codes, key=natural_text_key) == [
        "AV.I.1.1.1",
        "AV.I.1.1.2",
        "AV.I.1.1.10",
    ]


def test_catalog_entries_use_code_then_alphabetical_fallback():
    entries = [
        SimpleNamespace(id=4, code=None, name="Zulu"),
        SimpleNamespace(id=3, code="AV.I.1.1.10", name="Décimo"),
        SimpleNamespace(id=2, code="AV.I.1.1.2", name="Segundo"),
        SimpleNamespace(id=1, code="", name="Árvore"),
    ]

    ordered = sort_catalog_entries(entries)

    assert [item.id for item in ordered] == [2, 3, 1, 4]


def test_catalog_entries_accept_dicts_and_custom_accessors():
    entries = [
        {"id": 2, "indicator_code": "AV.I.2", "label": "Beta"},
        {"id": 1, "indicator_code": "AV.I.1", "label": "Alfa"},
    ]

    ordered = sort_catalog_entries(
        entries,
        code="indicator_code",
        name="label",
    )

    assert [item["id"] for item in ordered] == [1, 2]
