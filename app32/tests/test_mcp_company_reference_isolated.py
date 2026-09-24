"""Pure reference matching tests: no app bootstrap, DB or network."""
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "services/mcp_company_reference_service.py"
spec = importlib.util.spec_from_file_location("company_reference_unit", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("reference", ["8", "AW", "aw", "Meu Chapa", "AW - Meu Chapa", "AW — Meu Chapa"])
def test_authorized_company_reference(reference):
    assert module.select_company_reference(reference, [
        {"id": 8, "code": "AW", "name": "Meu Chapa"}]) == 8


def test_no_candidate_does_not_reveal_unauthorized_company():
    with pytest.raises(PermissionError, match="entre as autorizadas"):
        module.select_company_reference("Empresa secreta", [])


def test_ambiguous_name_requires_choice():
    with pytest.raises(ValueError, match="ambígua"):
        module.select_company_reference("Meu Chapa", [
            {"id": 8, "code": "AW", "name": "Meu Chapa"},
            {"id": 9, "code": "AX", "name": "Meu Chapa"},
        ])


def test_conflicting_id_is_rejected():
    with pytest.raises(ValueError, match="diferentes"):
        module.select_company_reference("AW", [{"id": 8, "code": "AW", "name": "Meu Chapa"}], 9)


@pytest.mark.parametrize("reference", ["", " ", None, "%", "Meu"])
def test_invalid_or_partial_reference_does_not_select_silently(reference):
    with pytest.raises((ValueError, PermissionError)):
        module.select_company_reference(reference, [{"id": 8, "code": "AW", "name": "Meu Chapa"}])
