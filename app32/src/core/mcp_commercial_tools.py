from __future__ import annotations

from typing import Any, Optional


def register_commercial_mcp_tools(mcp: Any) -> None:
    """Registra tools MCP da frente comercial/contratos."""

    def _run_action(callback, *args, **kwargs):
        from app import create_app

        app = create_app()
        with app.app_context():
            return callback(*args, **kwargs)

    def _ok(**payload):
        return {"success": True, **payload}

    def _fail(message: str):
        return {"success": False, "error": message}

    def _normalize_counterparty_update_payload(payload: dict | None) -> dict:
        normalized = dict(payload or {})
        normalized.pop("is_customer", None)
        normalized.pop("is_supplier", None)
        return normalized

    @mcp.tool()
    def list_commercial_customer_portfolios(company_id: int) -> dict:
        """Lista a árvore de Carteira de Clientes da empresa."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.list_items,
            catalog_type="customer_portfolios",
            company_id=company_id,
        )
        if error:
            return _fail(error)
        return _ok(items=result or [], count=len(result or []))

    @mcp.tool()
    def create_commercial_customer_portfolio(payload: dict) -> dict:
        """Cria um nó da Carteira de Clientes."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.create_item,
            catalog_type="customer_portfolios",
            payload=payload,
        )
        if error:
            return _fail(error)
        return _ok(item=result)

    @mcp.tool()
    def update_commercial_customer_portfolio(company_id: int, portfolio_id: int, payload: dict) -> dict:
        """Atualiza um nó da Carteira de Clientes."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.update_item,
            catalog_type="customer_portfolios",
            item_id=portfolio_id,
            company_id=company_id,
            payload=payload,
        )
        if error:
            return _fail(error)
        return _ok(item=result)

    @mcp.tool()
    def toggle_commercial_customer_portfolio(company_id: int, portfolio_id: int, is_active: bool) -> dict:
        """Ativa ou inativa um nó da Carteira de Clientes."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.toggle_item,
            catalog_type="customer_portfolios",
            item_id=portfolio_id,
            company_id=company_id,
            is_active=is_active,
        )
        if error:
            return _fail(error)
        return _ok(item=result)

    @mcp.tool()
    def list_commercial_customers(company_id: int, search: Optional[str] = None, customer_portfolio_id: Optional[int] = None) -> dict:
        """Lista clientes comerciais (favorecidos marcados como cliente)."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.list_items,
            catalog_type="counterparties",
            company_id=company_id,
        )
        if error:
            return _fail(error)
        items = [item for item in (result or []) if bool(item.get("is_customer"))]
        if customer_portfolio_id:
            items = [item for item in items if int(item.get("customer_portfolio_id") or 0) == int(customer_portfolio_id)]
        if search:
            needle = str(search or "").strip().lower()
            items = [
                item
                for item in items
                if needle in str(item.get("code") or "").lower()
                or needle in str(item.get("name") or "").lower()
                or needle in str(item.get("legal_name") or "").lower()
                or needle in str(item.get("document_number") or "").lower()
            ]
        return _ok(items=items, count=len(items))

    @mcp.tool()
    def update_commercial_customer(company_id: int, customer_id: int, payload: dict) -> dict:
        """Atualiza dados cadastrais do cliente sem alterar flags cliente/fornecedor."""
        from services.financial_catalog_service import FinancialCatalogService

        result, error = _run_action(
            FinancialCatalogService.update_item,
            catalog_type="counterparties",
            item_id=customer_id,
            company_id=company_id,
            payload=_normalize_counterparty_update_payload(payload),
        )
        if error:
            return _fail(error)
        return _ok(item=result)

    @mcp.tool()
    def list_commercial_issuers(company_id: int) -> dict:
        """Lista PJs emissoras/NF da frente comercial."""
        from services.contracts_service import ContractService

        entities = _run_action(ContractService.list_contracting_legal_entities, company_id)
        items = [entity.to_dict() for entity in entities]
        return _ok(items=items, count=len(items), next_code=_run_action(ContractService.preview_next_contracting_legal_entity_code, company_id))

    @mcp.tool()
    def create_commercial_issuer(company_id: int, payload: dict) -> dict:
        """Cria uma PJ emissora de NF/contratada."""
        from services.contracts_service import ContractService

        try:
            entity = _run_action(ContractService.create_contracting_legal_entity, company_id=company_id, payload=payload)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=entity.to_dict())

    @mcp.tool()
    def update_commercial_issuer(company_id: int, issuer_id: int, payload: dict) -> dict:
        """Atualiza uma PJ emissora de NF/contratada."""
        from models import db
        from services.contracts_service import ContractService

        def _callback():
            entity = ContractService.get_contracting_legal_entity(company_id, issuer_id)
            if not entity:
                raise ValueError("PJ emissora não localizada para a empresa ativa.")
            ContractService.update_contracting_legal_entity(entity=entity, payload=payload)
            db.session.commit()
            return entity

        try:
            entity = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=entity.to_dict())

    @mcp.tool()
    def list_commercial_catalog_structure(company_id: int) -> dict:
        """Lista a árvore de Grupo/Sub-Grupo comercial."""
        from services.contracts_catalog_service import ContractsCatalogService

        tree = _run_action(ContractsCatalogService.build_tree, company_id)
        items = _run_action(ContractsCatalogService.list_items, company_id)
        structure = [item.to_dict() for item in items if not bool(item.accepts_contracting)]
        return _ok(tree=tree, items=structure, count=len(structure))

    @mcp.tool()
    def create_commercial_catalog_structure_item(payload: dict) -> dict:
        """Cria Grupo/Sub-Grupo comercial."""
        from services.contracts_catalog_service import ContractsCatalogService

        try:
            item = _run_action(ContractsCatalogService.create_item, payload=payload)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def update_commercial_catalog_structure_item(company_id: int, item_id: int, payload: dict) -> dict:
        """Atualiza Grupo/Sub-Grupo comercial."""
        from services.contracts_catalog_service import ContractsCatalogService

        def _callback():
            item = ContractsCatalogService.get_item(company_id, item_id)
            if not item:
                raise ValueError("Estrutura comercial não localizada para a empresa ativa.")
            return ContractsCatalogService.update_item(item=item, payload=payload)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def toggle_commercial_catalog_structure_item(company_id: int, item_id: int, is_active: bool) -> dict:
        """Ativa ou inativa Grupo/Sub-Grupo comercial."""
        from services.contracts_catalog_service import ContractsCatalogService

        def _callback():
            item = ContractsCatalogService.get_item(company_id, item_id)
            if not item:
                raise ValueError("Estrutura comercial não localizada para a empresa ativa.")
            return ContractsCatalogService.toggle_item(item=item, is_active=is_active)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def list_commercial_products_services(company_id: int) -> dict:
        """Lista produtos/serviços folha com seus grupos comerciais."""
        from services.contracts_catalog_service import ContractsCatalogService

        items = _run_action(ContractsCatalogService.list_leaf_items, company_id)
        parents = _run_action(ContractsCatalogService.list_leaf_parent_candidates, company_id)
        return _ok(
            items=[item.to_dict() for item in items],
            parent_candidates=[item.to_dict() for item in parents],
            count=len(items),
        )

    @mcp.tool()
    def create_commercial_product_service(payload: dict) -> dict:
        """Cria um produto/serviço comercial folha."""
        from services.contracts_catalog_service import ContractsCatalogService

        try:
            item = _run_action(ContractsCatalogService.create_item, payload=payload)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def update_commercial_product_service(company_id: int, item_id: int, payload: dict) -> dict:
        """Atualiza um produto/serviço comercial folha."""
        from services.contracts_catalog_service import ContractsCatalogService

        def _callback():
            item = ContractsCatalogService.get_item(company_id, item_id)
            if not item:
                raise ValueError("Produto/serviço não localizado para a empresa ativa.")
            return ContractsCatalogService.update_item(item=item, payload=payload)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def toggle_commercial_product_service(company_id: int, item_id: int, is_active: bool) -> dict:
        """Ativa ou inativa um produto/serviço comercial."""
        from services.contracts_catalog_service import ContractsCatalogService

        def _callback():
            item = ContractsCatalogService.get_item(company_id, item_id)
            if not item:
                raise ValueError("Produto/serviço não localizado para a empresa ativa.")
            return ContractsCatalogService.toggle_item(item=item, is_active=is_active)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def list_commercial_contracts(company_id: int, filters: Optional[dict] = None) -> dict:
        """Lista contratos da gestão comercial com árvore cliente->contratos."""
        from services.contracts_service import ContractService

        rows = _run_action(ContractService.list_contracts_filtered, company_id, filters or {})
        tree = _run_action(ContractService.build_contract_list_tree, company_id, filters or {})
        return _ok(items=[row.to_dict() for row in rows], tree=tree, count=len(rows))

    @mcp.tool()
    def get_commercial_contract_workspace(company_id: int, contract_id: int) -> dict:
        """Retorna o workspace simplificado do contrato comercial."""
        from models.contracts import ContractItem
        from models.contracts import ContractFinancialTerm, ContractFiscalTerm
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            financial_terms = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=company_id).first()
            fiscal_terms = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=company_id).first()
            items = ContractItem.query.filter_by(
                company_id=company_id,
                contract_id=contract.id,
            ).order_by(ContractItem.order_index.asc(), ContractItem.id.asc()).all()
            return {
                "contract": contract.to_dict(),
                "workspace": ContractService.get_contract_workspace_summary(contract),
                "next_action": ContractService.get_contract_next_action(contract),
                "schedule_overview": ContractService.get_native_schedule_overview(contract),
                "history": {
                    key: [item.to_dict() for item in value]
                    for key, value in ContractService.list_contract_history(contract).items()
                },
                "items": [item.to_dict() for item in items],
                "financial_terms": financial_terms.to_dict() if financial_terms else None,
                "fiscal_terms": fiscal_terms.to_dict() if fiscal_terms else None,
                "visible_tabs": ContractService.get_visible_tabs(contract),
            }

        try:
            result = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(**result)

    @mcp.tool()
    def create_commercial_contract(company_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Cria um contrato comercial simplificado."""
        from services.contracts_service import ContractService

        try:
            contract = _run_action(ContractService.create_contract, company_id=company_id, payload=payload, user_id=user_id)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=contract.to_dict())

    @mcp.tool()
    def update_commercial_contract_general(company_id: int, contract_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Atualiza a aba Geral/Observações do contrato comercial."""
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            return ContractService.update_contract_general(contract=contract, payload=payload, user_id=user_id)

        try:
            contract = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=contract.to_dict())

    @mcp.tool()
    def upsert_commercial_contract_financial_terms(company_id: int, contract_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Atualiza as regras financeiras do contrato comercial."""
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            return ContractService.upsert_financial_terms(contract=contract, payload=payload, user_id=user_id)

        try:
            record = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=record.to_dict())

    @mcp.tool()
    def upsert_commercial_contract_fiscal_terms(company_id: int, contract_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Atualiza os dados fiscais/NFS-e do contrato comercial."""
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            return ContractService.upsert_fiscal_terms(contract=contract, payload=payload, user_id=user_id)

        try:
            record = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=record.to_dict())

    @mcp.tool()
    def add_commercial_contract_item(company_id: int, contract_id: int, payload: dict) -> dict:
        """Inclui um item/serviço no contrato comercial."""
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            return ContractService.add_contract_item(contract=contract, payload=payload)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def update_commercial_contract_item(company_id: int, contract_id: int, item_id: int, payload: dict) -> dict:
        """Atualiza um item/serviço do contrato comercial."""
        from services.contracts_service import ContractService

        def _callback():
            contract = ContractService.get_contract(company_id, contract_id)
            if not contract:
                raise ValueError("Contrato não localizado para a empresa ativa.")
            return ContractService.update_contract_item(contract=contract, item_id=item_id, payload=payload)

        try:
            item = _run_action(_callback)
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=item.to_dict())

    @mcp.tool()
    def list_commercial_billing_queue(company_id: int, filters: Optional[dict] = None) -> dict:
        """Lista contratos aptos/bloqueados para faturar."""
        from services.contracts_service import ContractService

        rows = _run_action(ContractService.list_contracts_billing_view, company_id, filters or {})
        normalized = []
        for row in rows:
            normalized.append(
                {
                    "contract": row["contract"].to_dict(),
                    "billing_item_count": row["billing_item_count"],
                    "native_billing_count": row["native_billing_count"],
                    "last_native_billing": row["last_native_billing"].to_dict() if row.get("last_native_billing") else None,
                    "next_period": {
                        key: value.isoformat() if hasattr(value, "isoformat") else value
                        for key, value in (row.get("next_period") or {}).items()
                    },
                    "preview": {
                        key: value.isoformat() if hasattr(value, "isoformat") else value
                        for key, value in (row.get("preview") or {}).items()
                    },
                    "eligibility": row.get("eligibility") or {},
                }
            )
        return _ok(items=normalized, count=len(normalized))

    @mcp.tool()
    def preview_commercial_billing_batch(company_id: int, review_payloads: list[dict]) -> dict:
        """Pré-visualiza um lote de faturamento comercial antes de gerar."""
        from services.contracts_service import ContractService

        preview_rows = []
        for payload in review_payloads or []:
            contract_id = int(payload.get("contract_id") or 0)
            if not contract_id:
                continue
            try:
                def _callback():
                    contract = ContractService.get_contract(company_id, contract_id)
                    if not contract:
                        raise ValueError(f"Contrato {contract_id} não localizado para a empresa ativa.")
                    preview = ContractService.preview_native_billing(contract, payload)
                    eligibility = ContractService.get_contract_billing_eligibility(contract, preview)
                    return contract, preview, eligibility
                contract, preview, eligibility = _run_action(_callback)
                preview_rows.append(
                    {
                        "contract": contract.to_dict(),
                        "preview": {
                            key: value.isoformat() if hasattr(value, "isoformat") else value
                            for key, value in preview.items()
                        },
                        "eligibility": eligibility,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                preview_rows.append({"contract_id": contract_id, "error": str(exc), "eligible": False})
        return _ok(items=preview_rows, count=len(preview_rows))

    @mcp.tool()
    def generate_commercial_billing_batch(company_id: int, review_payloads: list[dict], user_id: Optional[int] = None) -> dict:
        """Gera um lote de faturamento comercial nativo."""
        from services.contracts_service import ContractService

        result = _run_action(
            ContractService.generate_native_billing_batch,
            company_id=company_id,
            review_payloads=review_payloads or [],
            user_id=user_id,
        )
        return _ok(
            created=[item.to_dict() for item in result.get("created") or []],
            errors=result.get("errors") or [],
            created_count=len(result.get("created") or []),
        )

    @mcp.tool()
    def list_commercial_billings_done(company_id: int, filters: Optional[dict] = None) -> dict:
        """Lista faturamentos comerciais já gerados."""
        from services.contracts_service import ContractService

        rows = _run_action(ContractService.list_native_billings_done, company_id, filters or {})
        normalized = []
        for row in rows:
            normalized.append(
                {
                    "billing": row["billing"].to_dict(),
                    "contract": row["contract"].to_dict() if row.get("contract") else None,
                    "party": row["party"].to_dict() if row.get("party") else None,
                    "retention_amount": float(row.get("retention_amount") or 0),
                    "financial_integration": row.get("financial_integration") or {},
                    "item_count": row.get("item_count") or 0,
                    "financial_required": bool(row.get("financial_required")),
                    "financial_anomaly": bool(row.get("financial_anomaly")),
                }
            )
        return _ok(items=normalized, count=len(normalized))

    @mcp.tool()
    def cancel_commercial_billing(company_id: int, billing_id: int, user_id: Optional[int] = None, reason: Optional[str] = None) -> dict:
        """Cancela um faturamento comercial gerado."""
        from services.contracts_service import ContractService

        try:
            billing = _run_action(
                ContractService.cancel_native_billing,
                company_id=company_id,
                native_billing_id=billing_id,
                user_id=user_id,
                reason=reason,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=billing.to_dict())

    @mcp.tool()
    def list_commercial_fiscal_workspace(company_id: int, filters: Optional[dict] = None) -> dict:
        """Lista o workspace de Notas Fiscais do comercial."""
        from services.contracts_service import ContractService

        workspace = _run_action(ContractService.list_fiscal_invoice_workspace, company_id, filters or {})
        rows = []
        for row in workspace.get("rows") or []:
            rows.append(
                {
                    "billing": row["billing"].to_dict(),
                    "contract": row["contract"].to_dict() if row.get("contract") else None,
                    "party": row["party"].to_dict() if row.get("party") else None,
                    "fiscal_invoice": row.get("fiscal_invoice") or {},
                    "fiscal_data": row.get("fiscal_data") or {},
                    "batch_code": row.get("batch_code"),
                    "retention_amount": float(row.get("retention_amount") or 0),
                    "item_count": row.get("item_count") or 0,
                }
            )
        return _ok(rows=rows, batches=workspace.get("batches") or [], kpis=workspace.get("kpis") or {}, status_counts=workspace.get("status_counts") or {})

    @mcp.tool()
    def update_commercial_fiscal_entry(company_id: int, billing_id: int, payload: dict, user_id: Optional[int] = None) -> dict:
        """Atualiza os dados fiscais editáveis de um faturamento."""
        from services.contracts_service import ContractService

        try:
            billing = _run_action(
                ContractService.update_fiscal_invoice_data,
                company_id=company_id,
                billing_id=billing_id,
                payload=payload,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(item=billing.to_dict())

    @mcp.tool()
    def assign_commercial_fiscal_batch(company_id: int, billing_ids: list[int], batch_code: Optional[str] = None, user_id: Optional[int] = None) -> dict:
        """Inclui registros fiscais em um lote sequencial ou existente."""
        from services.contracts_service import ContractService

        try:
            result = _run_action(
                ContractService.assign_fiscal_invoice_batch,
                company_id=company_id,
                billing_ids=billing_ids,
                batch_code=batch_code,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(**result)

    @mcp.tool()
    def remove_commercial_fiscal_batch(company_id: int, billing_ids: list[int], user_id: Optional[int] = None) -> dict:
        """Remove registros fiscais do lote atual."""
        from services.contracts_service import ContractService

        try:
            result = _run_action(
                ContractService.remove_fiscal_invoice_batch,
                company_id=company_id,
                billing_ids=billing_ids,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(**result)

    @mcp.tool()
    def update_commercial_fiscal_status(company_id: int, billing_ids: list[int], status: str, payload: Optional[dict] = None, user_id: Optional[int] = None) -> dict:
        """Marca notas fiscais como pendentes, emitidas, canceladas ou excluídas."""
        from services.contracts_service import ContractService

        try:
            result = _run_action(
                ContractService.update_fiscal_invoice_status,
                company_id=company_id,
                billing_ids=billing_ids,
                status=status,
                payload=payload or {},
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(**result)

    @mcp.tool()
    def export_commercial_fiscal_integration_spreadsheet(company_id: int, billing_ids: list[int], user_id: Optional[int] = None) -> dict:
        """Gera a planilha XLSX de integração de NFS-e da frente comercial."""
        import base64
        from services.contracts_service import ContractService

        try:
            result = _run_action(
                ContractService.build_fiscal_invoice_integration_spreadsheet,
                company_id=company_id,
                billing_ids=billing_ids,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001
            return _fail(str(exc))
        return _ok(
            filename=result.get("filename"),
            mimetype=result.get("mimetype"),
            row_count=result.get("row_count") or 0,
            file_base64=base64.b64encode(result.get("content") or b"").decode("ascii"),
        )


__all__ = ["register_commercial_mcp_tools"]
