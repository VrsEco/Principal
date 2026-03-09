import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from schemas.user_pydantic import UserCreateSchema


def test_user_create_schema_accepts_company_ids_and_deduplicates():
    payload = UserCreateSchema(
        name="Usuário Teste",
        email="teste@empresa.com",
        password="123456",
        company_ids=[8, "8", 9],
    )

    assert payload.company_ids == [8, 9]


def test_user_create_schema_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        UserCreateSchema(
            name="Usuário Teste",
            email="teste@empresa.com",
            password="123456",
            company_ids=[8],
            extra_field=True,
        )


def test_user_create_schema_rejects_invalid_company_ids_format():
    with pytest.raises(ValidationError):
        UserCreateSchema(
            name="Usuário Teste",
            email="teste@empresa.com",
            password="123456",
            company_ids="8",
        )
