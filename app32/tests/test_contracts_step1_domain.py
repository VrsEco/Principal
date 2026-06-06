from datetime import date, datetime

from decimal import Decimal
from types import SimpleNamespace

from models.contracts import Contract, ContractCatalogItem, ContractClause, ContractEvent, ContractFiscalTerm, ContractItem, ContractNativeBilling, ContractNote, ContractTrigger, ContractingLegalEntity
from services.contracts_service import ContractService


def test_contract_to_dict_exposes_step1_contract_fields():
    contract = Contract(
        id=1,
        company_id=9,
        party_id=11,
        code="AA.N.001",
        title="Contrato Base",
        status="draft",
        manager_employee_id=77,
        renewal_date=date(2026, 7, 1),
        adjustment_date=date(2026, 8, 1),
        termination_date=date(2026, 12, 31),
        previous_contract_id=5,
        end_reason="renewal",
        created_at=datetime(2026, 5, 26, 10, 0, 0),
        updated_at=datetime(2026, 5, 26, 10, 30, 0),
    )

    payload = contract.to_dict()

    assert payload["manager_employee_id"] == 77
    assert payload["renewal_date"] == "2026-07-01"
    assert payload["adjustment_date"] == "2026-08-01"
    assert payload["termination_date"] == "2026-12-31"
    assert payload["previous_contract_id"] == 5
    assert payload["end_reason"] == "renewal"


def test_contracting_legal_entity_and_fiscal_term_to_dict_expose_compliance_fields():
    legal_entity = ContractingLegalEntity(
        id=12,
        company_id=9,
        code="PJ01",
        legal_name="Empresa Grupo A Ltda",
        cnpj="00.000.000/0001-00",
        nfs_provider="prefeitura_salvador",
        integration_mode="api",
        api_profile_id=5,
        metadata_json={"iss_rate_rules": [{"effective_from": "2026-06-01", "percent": "2.73"}]},
        is_active=True,
    )
    fiscal_term = ContractFiscalTerm(
        id=8,
        company_id=9,
        contract_id=1,
        contracting_legal_entity_id=12,
        integration_mode="api",
        service_code="1401",
        service_list_item="17.05",
        operation_nature="Prestação de serviço",
        withholding_flags={"iss_withheld": True},
    )

    assert legal_entity.to_dict()["cnpj"] == "00.000.000/0001-00"
    assert legal_entity.to_dict()["metadata_json"]["iss_rate_rules"][0]["percent"] == "2.73"
    assert fiscal_term.to_dict()["contracting_legal_entity_id"] == 12
    assert fiscal_term.to_dict()["withholding_flags"]["iss_withheld"] is True


def test_get_contracting_legal_entity_active_iss_rule_prefers_current_vigencia():
    legal_entity = ContractingLegalEntity(
        metadata_json={
            "iss_rate_rules": [
                {"effective_from": "2026-06-01", "effective_to": "2026-06-30", "percent": "2.73"},
                {"effective_from": "2026-07-01", "percent": "3.10"},
            ]
        }
    )

    june_rule = ContractService.get_contracting_legal_entity_active_iss_rule(legal_entity, date(2026, 6, 5))
    july_rule = ContractService.get_contracting_legal_entity_active_iss_rule(legal_entity, date(2026, 7, 5))

    assert june_rule["percent"] == "2.73"
    assert july_rule["percent"] == "3.1"


def test_build_native_billing_item_snapshot_prefers_issuer_iss_rate_over_item_rate():
    legal_entity = ContractingLegalEntity(
        metadata_json={
            "iss_rate_rules": [
                {"effective_from": "2026-06-01", "effective_to": "2026-06-30", "percent": "2.73"}
            ]
        }
    )
    contract = Contract(company_id=1, contracting_legal_entity=legal_entity, billing_start_at=date(2026, 1, 1))
    catalog_item = ContractCatalogItem(metadata_json={"iss_rate_percent": "5"})
    item = ContractItem(
        id=88,
        total_price=Decimal("1000.00"),
        quantity=Decimal("1.00"),
        unit_price=Decimal("1000.00"),
        description="Serviço recorrente",
        metadata_json={
            "retention_details": [
                {
                    "kind": "iss",
                    "base_deduction_mode": "percent",
                    "base_deduction_value": 0,
                    "retention_value_mode": "percent",
                    "retention_value": 5,
                    "retention_amount": 50,
                }
            ]
        },
    )
    item.contract = contract
    item.contract_catalog_item = catalog_item

    snapshot = ContractService._build_native_billing_item_snapshot(item, reference_date=date(2026, 6, 5))

    assert snapshot["retention_amount"] == 27.3
    assert snapshot["net_amount"] == 972.7
    assert snapshot["retention_details"][0]["rate_source"] == "issuer"
    assert snapshot["retention_details"][0]["retention_value"] == 2.73


def test_build_native_billing_item_snapshot_ignores_malformed_retention_metadata():
    item = ContractItem(
        id=89,
        total_price=Decimal("250.00"),
        quantity=Decimal("1.00"),
        unit_price=Decimal("250.00"),
        description="Serviço com metadado legado",
        metadata_json={
            "allocation": "invalid",
            "retention_details": "invalid",
        },
    )

    snapshot = ContractService._build_native_billing_item_snapshot(item, reference_date=date(2026, 6, 5))

    assert snapshot["gross_amount"] == 250.0
    assert snapshot["net_amount"] == 250.0
    assert snapshot["retention_amount"] == 0.0
    assert snapshot["allocation"] == {}
    assert snapshot["retention_details"] == []


def test_contract_clause_note_and_event_to_dict_are_tenant_safe():
    clause = ContractClause(
        id=2,
        company_id=9,
        contract_id=1,
        clause_type="billing",
        title="Faturamento",
        content="Cobrança mensal.",
        order_index=1,
    )
    note = ContractNote(
        id=3,
        company_id=9,
        contract_id=1,
        note_type="general",
        note_text="Cliente pediu reajuste anual.",
    )
    event = ContractEvent(
        id=4,
        company_id=9,
        contract_id=1,
        event_type="contract.created",
        description="Contrato criado.",
        event_payload={"status": "draft"},
    )

    assert clause.to_dict()["company_id"] == 9
    assert note.to_dict()["note_text"] == "Cliente pediu reajuste anual."
    assert event.to_dict()["event_payload"] == {"status": "draft"}


def test_contract_tab_registry_includes_clause_and_history_views():
    tabs = ContractService.get_tab_registry()
    keys = {tab["key"] for tab in tabs}

    assert "clausulas" in keys
    assert "historico" in keys
    assert "automacoes" in keys
    assert "financeiro" in keys


def test_contract_next_action_prioritizes_renewal_and_adjustment_dates():
    class _FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

        def count(self):
            return 0

    class _FakeContract:
        def __init__(self, **kwargs):
            self.status = "active"
            self.last_billing_at = None
            self.termination_date = None
            self.renewal_date = None
            self.adjustment_date = None
            self.billing_start_at = None
            self.signed_at = None
            self.service_start_at = None
            self.triggers = _FakeQuery()
            for key, value in kwargs.items():
                setattr(self, key, value)

    renewing = _FakeContract(renewal_date=date.today())
    adjusting = _FakeContract(adjustment_date=date.today(), last_billing_at=date.today())

    assert ContractService.get_contract_next_action(renewing)["label"] == "Renovar contrato"
    assert ContractService.get_contract_next_action(adjusting)["label"] == "Aplicar reajuste"


def test_native_schedule_overview_uses_contract_dates_and_future_trigger():
    class _FakeQuery:
        def __init__(self, items):
            self._items = items

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self._items

        def count(self):
            return len(self._items)

    class _FakeContract:
        def __init__(self):
            self.billing_start_at = date.today()
            self.renewal_date = date.today().replace(year=date.today().year + 1)
            self.adjustment_date = None
            self.termination_date = None
            self.signed_at = None
            self.service_start_at = None

    trigger = ContractTrigger(
        id=99,
        company_id=9,
        contract_id=1,
        trigger_type="billing",
        reference_date_type="billing_start_at",
        offset_days=5,
        periodicity="monthly",
        alert_before_days=2,
        is_active=True,
    )
    contract = _FakeContract()
    contract.triggers = _FakeQuery([trigger])

    overview = ContractService.get_native_schedule_overview(contract)

    assert overview["trigger_count"] == 1
    assert any(item["event_type"] == "billing" for item in overview["events"])
    assert overview["next_event"]["date"] >= date.today()


def test_native_billing_preview_and_idempotency_key_are_stable():
    class _FakeItemsQuery:
        def __init__(self, items):
            self._items = items

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return self._items

    class _FakeBillingItem:
        def __init__(self, amount):
            self.amount = amount

    class _FakeContract:
        def __init__(self):
            self.company_id = 9
            self.id = 55
            self.billing_start_at = date(2026, 5, 1)
            self.billing_items = _FakeItemsQuery([
                _FakeBillingItem(Decimal("100.00")),
                _FakeBillingItem(Decimal("50.50")),
            ])

    contract = _FakeContract()
    preview = ContractService.preview_native_billing(contract, {})
    key = ContractService.build_native_billing_idempotency_key(
        contract=contract,
        competence_start=preview["competence_start"],
        competence_end=preview["competence_end"],
    )

    assert preview["item_count"] == 2
    assert preview["gross_amount"] == Decimal("150.50")
    assert key == "contract:9:55:2026-05-01:2026-05-01"


def test_contract_automation_templates_include_monthly_billing():
    templates = ContractService.get_contract_automation_template_options()
    keys = {item["key"] for item in templates}

    assert "generate_billing_monthly" in keys
    assert "renewal_alert_before_date" in keys


def test_native_billing_fiscal_export_payload_reads_snapshot_metadata():
    class _FakeItemsQuery:
        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return []

    class _FakeParty:
        name = "Cliente XPTO"
        document_number = "11.111.111/0001-11"

    class _FakeContract:
        code = "AA.N.001"
        party = _FakeParty()

    class _FakeBilling:
        billing_code = "AA.B.001"
        issue_date = None
        gross_amount = Decimal("100.00")
        net_amount = Decimal("100.00")
        metadata_json = {
            "fiscal_snapshot": {
                "contracting_legal_entity_id": 12,
                "issuer_cnpj": "00.000.000/0001-00",
                "issuer_legal_name": "Empresa Grupo A Ltda",
                "integration_mode": "api",
                "service_code": "1401",
                "service_list_item": "17.05",
            }
        }
        contract = _FakeContract()
        items = _FakeItemsQuery()

    billing = _FakeBilling()
    payload = ContractService.build_native_billing_fiscal_export_payload(billing)

    assert payload["issuer_cnpj"] == "00.000.000/0001-00"
    assert payload["contracting_legal_entity_id"] == 12
    assert payload["service_code"] == "1401"


def test_fiscal_invoice_workspace_filters_by_issuer_legal_entity(monkeypatch):
    class _FakeItems:
        def count(self):
            return 0

    billing_a = SimpleNamespace(
        id=1,
        gross_amount=Decimal("100.00"),
        net_amount=Decimal("90.00"),
        contract=SimpleNamespace(id=10, code="AA.N.001", title="Contrato A"),
        party=SimpleNamespace(id=20, name="Cliente A"),
        items=_FakeItems(),
        issuer_legal_entity_id=12,
    )
    billing_b = SimpleNamespace(
        id=2,
        gross_amount=Decimal("200.00"),
        net_amount=Decimal("180.00"),
        contract=SimpleNamespace(id=11, code="AA.N.002", title="Contrato B"),
        party=SimpleNamespace(id=21, name="Cliente B"),
        items=_FakeItems(),
        issuer_legal_entity_id=13,
    )

    monkeypatch.setattr(
        ContractService,
        "_list_fiscal_invoice_billings",
        staticmethod(lambda company_id, filters: [billing_a, billing_b]),
    )
    monkeypatch.setattr(
        ContractService,
        "_get_fiscal_invoice_state",
        staticmethod(
            lambda billing: {
                "status": "pending",
                "batch_code": None,
                "fiscal_data": {"contracting_legal_entity_id": billing.issuer_legal_entity_id},
                "attachments": [],
            }
        ),
    )

    workspace = ContractService.list_fiscal_invoice_workspace(1, {"issuer_legal_entity_id": 12})

    assert [row["billing"].id for row in workspace["rows"]] == [1]
    assert workspace["kpis"]["total"] == 1
    assert workspace["kpis"]["pending"] == 1
def test_build_fiscal_invoice_nfse_row_prioritizes_catalog_for_service_code_and_normalizes_nbs():
    class _FakeItemsQuery:
        def __init__(self, items):
            self._items = items

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeCatalogItem:
        metadata_json = {
            "service_code": "702",
            "tipo_operacao": "Tributado Integralmente",
            "nbs": "1.1803.29.00",
            "cindop": "050101",
            "cclasstrib": "000001",
        }

    class _FakeContractItem:
        metadata_json = {}
        contract_catalog_item = _FakeCatalogItem()

    class _FakeBillingItem:
        metadata_json = {}
        contract_item = _FakeContractItem()
        description = "Tratamento de água industrial"
        amount = Decimal("6285.60")

    class _FakeParty:
        legal_name = "BOMIX INDUSTRIA DE EMBALAGENS LTDA"
        name = "BOMIX INDUSTRIA DE EMBALAGENS LTDA"
        document_number = "01.561.279/0001-45"
        email = "fiscal@bomix.com.br"
        metadata_json = {}
        financial_counterparty_id = None

    class _FakeContract:
        party = _FakeParty()
        code = "AA.BOMIX.001"

    class _FakeBilling:
        billing_code = "AA.BOMIX.FAT.001"
        issue_date = None
        gross_amount = Decimal("6285.60")
        net_amount = Decimal("6285.60")
        metadata_json = {
            "fiscal_snapshot": {
                "service_code": "1401001",
                "service_list_item": "1401101",
                "issuer_cnae": "4322302",
            },
            "fiscal_invoice": {
                "fiscal_data": {
                    "customer_name": "BOMIX INDUSTRIA DE EMBALAGENS LTDA",
                    "customer_document": "01.561.279/0001-45",
                    "service_code": "1401001",
                    "service_list_item": "1401101",
                    "issuer_cnae": "4322302",
                }
            },
        }
        party = _FakeParty()
        contract = _FakeContract()
        items = _FakeItemsQuery([_FakeBillingItem()])

    row = ContractService._build_fiscal_invoice_nfse_row(company_id=1, native_billing=_FakeBilling())

    assert row["Codigo_Servico"] == "702"
    assert row["IBSCBS_Indicador_Operacao"] == "050101"
    assert row["IBSCBS_Codigo_Classificacao"] == "000001"
    assert row["IBSCBS_Tipo_Operacao"] == "1401101"
    assert row["NBS"] == "118032900"
    assert row["CNAE"] == "4322302"


def test_build_fiscal_invoice_nfse_row_keeps_iss_and_duplicates_to_outros_for_non_salvador():
    class _FakeItemsQuery:
        def __init__(self, items):
            self._items = items

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeCatalogItem:
        metadata_json = {}

    class _FakeContractItem:
        metadata_json = {}
        contract_catalog_item = _FakeCatalogItem()

    class _FakeBillingItem:
        metadata_json = {
            "retention_details": [
                {
                    "kind": "iss",
                    "retention_value_mode": "percent",
                    "retention_value": 5,
                    "calculated_amount": 314.28,
                }
            ]
        }
        contract_item = _FakeContractItem()
        description = "Tratamento dos Sistemas de Refrigeração."
        amount = Decimal("6285.60")

    class _FakeParty:
        legal_name = "BOMIX INDUSTRIA DE EMBALAGENS LTDA"
        name = "BOMIX INDUSTRIA DE EMBALAGENS LTDA"
        document_number = "01.561.279/0001-45"
        email = "fiscal@bomix.com.br"
        metadata_json = {"city_code_ibge": "2930709"}
        financial_counterparty_id = None

    class _FakeContract:
        party = _FakeParty()
        code = "AA.BOMIX.001"

    class _FakeBilling:
        billing_code = "AA.BOMIX.FAT.001"
        issue_date = None
        gross_amount = Decimal("6285.60")
        net_amount = Decimal("5971.32")
        metadata_json = {
            "fiscal_snapshot": {
                "service_city": "Simões Filho",
                "iss_city": "Simões Filho",
                "service_state": "BA",
                "service_city_code_ibge": "2930709",
                "tax_iss_at_service_location": True,
            },
            "fiscal_invoice": {
                "fiscal_data": {
                    "customer_name": "BOMIX INDUSTRIA DE EMBALAGENS LTDA",
                    "customer_document": "01.561.279/0001-45",
                    "service_city": "Simões Filho",
                    "iss_city": "Simões Filho",
                    "service_state": "BA",
                    "service_city_code_ibge": "2930709",
                    "tax_iss_at_service_location": True,
                }
            },
        }
        party = _FakeParty()
        contract = _FakeContract()
        items = _FakeItemsQuery([_FakeBillingItem()])

    row = ContractService._build_fiscal_invoice_nfse_row(company_id=1, native_billing=_FakeBilling())

    assert row["Aliquota_ISS"] == "5"
    assert row["Valor_ISS"] == "314,28"
    assert row["Retencao_OUTROS"] == "314,28"
    assert row.get("Retencao_ISS") is None
    assert row["Pais_Prestacao_Servico"] == "BRA"
    assert row["Estado_Prestacao_Servico"] == "BA"
    assert row["Cidade_Prestacao_Servico"] == "Simões Filho"
    assert row["Codigo_Cidade_Prestacao_Servico"] == "2930709"


def test_build_fiscal_invoice_nfse_row_exports_iss_retention_for_salvador():
    class _FakeItemsQuery:
        def __init__(self, items):
            self._items = items

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeCatalogItem:
        metadata_json = {}

    class _FakeContractItem:
        metadata_json = {}
        contract_catalog_item = _FakeCatalogItem()

    class _FakeBillingItem:
        metadata_json = {
            "retention_details": [
                {
                    "kind": "iss",
                    "retention_value_mode": "percent",
                    "retention_value": 2.73,
                    "calculated_amount": 131.07,
                }
            ]
        }
        contract_item = _FakeContractItem()
        description = "Tratamento de água"
        amount = Decimal("4801.15")

    class _FakeParty:
        legal_name = "REDE BAHIA"
        name = "REDE BAHIA"
        document_number = "13.425.269/0001-61"
        email = "fiscal@redebahia.com.br"
        metadata_json = {"city_code_ibge": "2927408"}
        financial_counterparty_id = None

    class _FakeContract:
        party = _FakeParty()
        code = "AL.N.005"

    class _FakeBilling:
        billing_code = "AL.B.003"
        issue_date = None
        gross_amount = Decimal("4801.15")
        net_amount = Decimal("4670.08")
        metadata_json = {
            "fiscal_snapshot": {
                "service_city": "Salvador",
                "iss_city": "Salvador",
            },
            "fiscal_invoice": {
                "fiscal_data": {
                    "customer_name": "REDE BAHIA",
                    "customer_document": "13.425.269/0001-61",
                    "service_city": "Salvador",
                    "iss_city": "Salvador",
                }
            },
        }
        party = _FakeParty()
        contract = _FakeContract()
        items = _FakeItemsQuery([_FakeBillingItem()])

    row = ContractService._build_fiscal_invoice_nfse_row(company_id=1, native_billing=_FakeBilling())

    assert row["Aliquota_ISS"] == "2.73"
    assert row["Valor_ISS"] == "131,07"
    assert row["Retencao_ISS"] == "131,07"
    assert row.get("Retencao_OUTROS") is None
    assert "Estado_Prestacao_Servico" not in row
    assert "Cidade_Prestacao_Servico" not in row
    assert "Codigo_Cidade_Prestacao_Servico" not in row


def test_build_fiscal_invoice_nfse_row_normalizes_codes_and_address_defaults():
    class _FakeItemsQuery:
        def __init__(self, items):
            self._items = items

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            return list(self._items)

    class _FakeCatalogItem:
        metadata_json = {
            "service_code": "14.01.001",
            "tipo_operacao": "Tributado Integralmente",
            "nbs": "1.200.11.000",
            "cindop": "05.01.01",
            "cclasstrib": "00.00.01",
        }

    class _FakeContractItem:
        metadata_json = {}
        contract_catalog_item = _FakeCatalogItem()

    class _FakeBillingItem:
        metadata_json = {}
        contract_item = _FakeContractItem()
        description = "Tratamento e monitoramento do sistema de água."
        amount = Decimal("9250.00")

    class _FakeParty:
        legal_name = "CONDOMINIO DO NORTH WAY SHOPPING"
        name = "CONDOMINIO DO NORTH WAY SHOPPING"
        document_number = "22.424.335/0001-70"
        email = "flavio@aclf.com.br"
        metadata_json = {
            "cep": "53.401-445",
            "street": "Rod. PE-15 S/N, KM:16.5",
            "district": "Paulista",
            "city_code_ibge": "2611606",
            "city_name": "Recife",
            "state": "pe",
        }
        financial_counterparty_id = None

    class _FakeContract:
        party = _FakeParty()
        code = "AA.NORTHWAY.001"

    class _FakeBilling:
        billing_code = "AA.NORTHWAY.FAT.001"
        issue_date = None
        gross_amount = Decimal("9250.00")
        net_amount = Decimal("8787.50")
        metadata_json = {
            "fiscal_snapshot": {
                "service_code": "14.01.001",
                "service_list_item": "14.01.101",
                "issuer_cnae": "43.22-3/02",
            },
            "fiscal_invoice": {
                "fiscal_data": {
                    "customer_name": "CONDOMINIO DO NORTH WAY SHOPPING",
                    "customer_document": "22.424.335/0001-70",
                    "service_code": "14.01.001",
                    "service_list_item": "14.01.101",
                    "issuer_cnae": "43.22-3/02",
                    "service_city": "Recife",
                }
            },
        }
        party = _FakeParty()
        contract = _FakeContract()
        items = _FakeItemsQuery([_FakeBillingItem()])

    row = ContractService._build_fiscal_invoice_nfse_row(company_id=1, native_billing=_FakeBilling())

    assert row["Codigo_Servico"] == "1401001"
    assert row["IBSCBS_Indicador_Operacao"] == "050101"
    assert row["IBSCBS_Codigo_Classificacao"] == "000001"
    assert row["IBSCBS_Tipo_Operacao"] == "1401101"
    assert row["NBS"] == "120011000"
    assert row["CNAE"] == "4322302"
    assert row["Endereco_Numero"] == "s/n"
    assert row["Endereco_Cidade_Codigo"] == "2611606"
    assert row["Endereco_Estado"] == "PE"
