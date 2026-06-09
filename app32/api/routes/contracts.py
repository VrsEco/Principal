from __future__ import annotations

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from models import Company, Employee
from models.contracts import ContractDocument, ContractFinancialTerm, ContractFiscalTerm, ContractNativeBilling
from services.contract_financial_service import ContractFinancialService
from services.contracts_catalog_service import ContractsCatalogService
from services.contracts_service import ContractService
from utils.permissions import get_default_company_id, has_permission, permission_required


contracts_bp = Blueprint("contracts", __name__)
TAB_ALIASES = {
    "geral": "cliente",
    "resumo": "cliente",
    "cobranca": "financeiro",
    "gatilhos": "periodicidade",
    "anexos": "documentos",
}
CONTRACTS_LIST_TABS = (
    {"key": "geral", "label": "Geral"},
    {"key": "itens_valores", "label": "Itens e Valores do Contrato"},
    {"key": "faturamento", "label": "Dados para Faturamento"},
    {"key": "fiscal", "label": "Dados Fiscal / Emissão de NF"},
    {"key": "observacoes", "label": "Observações"},
)
CONTRACTS_LIST_TAB_ALIASES = {
    "resumo": "geral",
    "cliente": "geral",
    "itens": "itens_valores",
    "itens_valores": "itens_valores",
    "dados_faturamento": "faturamento",
    "cobranca": "faturamento",
    "financeiro": "faturamento",
    "dados_financeiro": "faturamento",
    "dados_fiscal": "fiscal",
    "nf": "fiscal",
}


def get_active_company():
    company_id = request.args.get("company_id", type=int) or session.get("active_company_id")
    if not company_id and current_user.is_authenticated:
        employee = Employee.query.filter_by(user_id=current_user.id, status="active").first()
        if employee and employee.company_id:
            company_id = employee.company_id
        else:
            company_id = get_default_company_id()
    if company_id:
        if not has_permission(company_id, "contracts", "view"):
            abort(403, description="Acesso negado ao contexto de contratos desta empresa.")
        session["active_company_id"] = company_id
        return Company.query.get(company_id)
    return None


def _normalize_contract_tab(tab_name: str | None) -> str:
    raw_tab = (tab_name or "cliente").strip().lower()
    return TAB_ALIASES.get(raw_tab, raw_tab)


def _normalize_contracts_list_tab(tab_name: str | None) -> str:
    raw_tab = (tab_name or "geral").strip().lower()
    normalized = CONTRACTS_LIST_TAB_ALIASES.get(raw_tab, raw_tab)
    allowed = {item["key"] for item in CONTRACTS_LIST_TABS}
    return normalized if normalized in allowed else "geral"


def _parse_int_list(values) -> list[int]:
    raw_values = values if isinstance(values, (list, tuple)) else [values]
    parsed: list[int] = []
    for raw_value in raw_values:
        for part in str(raw_value or "").replace(";", ",").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                value = int(part)
            except ValueError:
                continue
            if value not in parsed:
                parsed.append(value)
    return parsed


def _current_user_id() -> int | None:
    return current_user.id if current_user.is_authenticated else None


def _contracts_billing_filters_from_request() -> dict:
    return {
        "status": request.args.get("status"),
        "party_id": request.args.get("party_id", type=int),
        "manager_employee_id": request.args.get("manager_employee_id", type=int),
        "contracting_legal_entity_id": request.args.get("contracting_legal_entity_id", type=int),
        "search": request.args.get("search"),
        "billing_state": request.args.get("billing_state") or "eligible",
    }


def _billing_done_filters_from_request() -> dict:
    return {
        "status": request.args.get("status"),
        "party_id": request.args.get("party_id", type=int),
        "search": request.args.get("search"),
        "competence_from": request.args.get("competence_from"),
        "competence_to": request.args.get("competence_to"),
    }


def _fiscal_invoice_filters_from_request() -> dict:
    return {
        "search": request.args.get("search"),
        "party_id": request.args.get("party_id", type=int),
        "issuer_legal_entity_id": request.args.get("issuer_legal_entity_id", type=int),
        "fiscal_status": request.args.get("fiscal_status") or "active",
        "batch_code": request.args.get("batch_code"),
    }


def _build_billing_review_overrides(contract_ids: list[int]) -> dict[int, dict]:
    overrides: dict[int, dict] = {}
    for contract_id in contract_ids:
        overrides[contract_id] = {
            "competence_start": request.form.get(f"competence_start_{contract_id}"),
            "competence_end": request.form.get(f"competence_end_{contract_id}"),
            "issue_date": request.form.get(f"issue_date_{contract_id}"),
            "due_date": request.form.get(f"due_date_{contract_id}"),
            "review_notes": request.form.get(f"review_notes_{contract_id}"),
            "contract_item_ids": request.form.getlist(f"item_ids_{contract_id}"),
            "reviewed_from": "contracts_billing_review",
        }
    return overrides


def _build_billing_confirmation_payloads(contract_ids: list[int]) -> list[dict]:
    overrides = _build_billing_review_overrides(contract_ids)
    payloads: list[dict] = []
    for contract_id in contract_ids:
        payload = dict(overrides.get(contract_id) or {})
        payload["contract_id"] = contract_id
        payloads.append(payload)
    return payloads


def _normalize_contract_form_payload(form_data) -> dict:
    payload = dict(form_data)
    due_rule = ContractService.build_due_rule(
        reference=payload.get("due_rule_reference"),
        day=payload.get("due_rule_day"),
    )
    if due_rule:
        payload["due_rule"] = due_rule
    payload.pop("due_rule_reference", None)
    payload.pop("due_rule_day", None)
    payload.pop("competence_rule", None)
    return payload


def _normalize_contracts_list_form_payload(form_data) -> dict:
    payload = dict(form_data)
    due_rule = ContractService.build_due_rule(
        reference=payload.get("due_rule_reference"),
        day=payload.get("due_rule_day"),
    )
    if due_rule or "due_rule_reference" in payload or "due_rule_day" in payload:
        payload["due_rule"] = due_rule
    payload.pop("due_rule_reference", None)
    payload.pop("due_rule_day", None)
    payload.pop("section", None)
    payload.pop("return_tab", None)
    payload.pop("form_action", None)
    return payload


def _process_contracts_list_submission(company: Company, contract, active_tab: str) -> str:
    tab = _normalize_contracts_list_tab(request.form.get("section") or active_tab)
    return_tab = _normalize_contracts_list_tab(request.form.get("return_tab") or tab)
    user_id = current_user.id if current_user.is_authenticated else None
    form_action = (request.form.get("form_action") or "").strip().lower()

    if tab == "geral":
        ContractService.update_contract_general(
            contract=contract,
            payload=_normalize_contracts_list_form_payload(request.form),
            user_id=user_id,
        )
        flash("Dados gerais do contrato atualizados.", "success")
    elif tab == "itens_valores":
        if request.form.get("delete_item_id"):
            ContractService.delete_contract_item(contract=contract, item_id=int(request.form["delete_item_id"]))
            flash("Item do contrato removido.", "success")
        elif request.form.get("edit_item_id"):
            ContractService.update_contract_item(
                contract=contract,
                item_id=int(request.form["edit_item_id"]),
                payload=request.form.to_dict(),
            )
            flash("Item do contrato atualizado.", "success")
        else:
            ContractService.add_contract_item(contract=contract, payload=request.form.to_dict())
            flash("Item e valor do contrato incluídos.", "success")
    elif tab == "faturamento":
        if request.form.get("delete_billing_item_id"):
            ContractService.delete_billing_item(contract=contract, item_id=int(request.form["delete_billing_item_id"]))
            flash("Item de faturamento removido.", "success")
        elif request.form.get("generate_native_billing"):
            native_billing = ContractService.generate_native_billing(contract=contract, payload=request.form.to_dict(), user_id=user_id)
            flash(f"Faturamento nativo {native_billing.billing_code} gerado com sucesso.", "success")
        elif form_action == "save_contract_billing_rules":
            ContractService.update_contract_general(
                contract=contract,
                payload=_normalize_contracts_list_form_payload(request.form),
                user_id=user_id,
            )
            flash("Regras de faturamento do contrato atualizadas.", "success")
        else:
            ContractService.add_billing_item(
                contract=contract,
                payload=_normalize_contracts_list_form_payload(request.form),
            )
            flash("Item de faturamento incluído.", "success")
    elif tab == "fiscal":
        if request.form.get("delete_retention_id") or request.form.get("retention_id") or request.form.get("retention_type"):
            _process_contract_section_submission(company, contract, "fiscal")
        else:
            ContractService.upsert_fiscal_terms(contract=contract, payload=request.form.to_dict(), user_id=user_id)
            flash("Dados fiscais e de emissão de NF atualizados.", "success")
    elif tab == "observacoes":
        ContractService.update_contract_notes(contract=contract, payload=request.form.to_dict(), user_id=user_id)
        flash("Observações do contrato atualizadas.", "success")
    else:
        flash("Aba do contrato não reconhecida.", "error")
    return return_tab


def _build_commercial_counterparty_page() -> dict:
    return {
        "api_type": "counterparties",
        "title": "Clientes",
        "new_label": "Novo cliente",
        "eyebrow": "Cadastros comerciais",
        "description": "Cadastro mestre comercial compartilhado com contratos e financeiro. Marque Cliente para habilitar a abertura contratual.",
    }


def _build_customer_portfolio_page() -> dict:
    return {
        "api_type": "customer_portfolios",
        "title": "Carteira de Clientes",
        "new_label": "Nova carteira",
        "eyebrow": "Cadastros comerciais",
        "description": "Estruture a carteira comercial em árvore e vincule apenas carteiras analíticas aos clientes.",
    }


def _is_contract_catalog_structure_item(item) -> bool:
    return bool(item) and ContractsCatalogService.get_level_label(item) in {"Grupo", "Sub-Grupo"}


def _build_contract_detail_context(company: Company, contract, active_tab: str) -> dict:
    financial_terms = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=company.id).first()
    fiscal_terms = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=company.id).first()
    references = ContractService.list_financial_references(company.id)
    parties = ContractService.list_customer_parties(company.id)
    contract_catalog_items = ContractsCatalogService.list_selectable_items(company.id)
    managers = Employee.query.filter_by(company_id=company.id, status="active").order_by(Employee.name.asc()).all()
    if contract.party and not any(item.id == contract.party.id for item in parties):
        parties = [contract.party, *parties]
    documents = ContractDocument.query.filter_by(contract_id=contract.id, company_id=company.id).order_by(ContractDocument.uploaded_at.desc()).all()
    pdf_documents = [item for item in documents if item.document_type == "pdf_gerado"]
    signed_documents = [item for item in documents if item.document_type == "contrato_assinado" or item.is_signed_version]
    generic_documents = [item for item in documents if item.document_type not in {"pdf_gerado", "contrato_assinado"} and not item.is_signed_version]
    native_billings = ContractService.list_native_billings(contract)
    visible_tabs = ContractService.get_visible_tabs(contract)
    return {
        "parties": parties,
        "contract_catalog_items": contract_catalog_items,
        "financial_terms": financial_terms,
        "fiscal_terms": fiscal_terms,
        "references": references,
        "active_tab": ContractService.resolve_active_tab(contract, active_tab),
        "tabs": visible_tabs,
        "all_tabs": ContractService.get_tab_registry(),
        "operational_profile_options": ContractService.get_operational_profile_options(),
        "selected_operational_profile": ContractService.get_contract_operational_profile(contract),
        "pdf_documents": pdf_documents,
        "signed_documents": signed_documents,
        "generic_documents": generic_documents,
        "managers": managers,
        "review_flags": ContractService.build_contract_review_flags(contract),
        "contract_summary": ContractService.get_contract_workspace_summary(contract),
        "contract_history": ContractService.list_contract_history(contract),
        "selected_contract_next_action": ContractService.get_contract_next_action(contract),
        "native_billings": native_billings,
        "native_billing_preview": ContractService.preview_native_billing(contract, {}),
        "native_schedule": ContractService.get_native_schedule_overview(contract),
        "contract_automations": ContractService.list_contract_automations(contract),
        "automation_template_options": ContractService.get_contract_automation_template_options(),
        "contract_financial_titles": ContractFinancialService.list_contract_financial_titles(contract),
        "contract_financial_summary": ContractFinancialService.build_contract_financial_summary(contract),
        "satellite_policy_templates": ContractFinancialService.get_satellite_policy_template_options(),
        "contract_satellite_policies": ContractFinancialService.list_contract_satellite_policies(contract),
        "contracting_legal_entities": ContractService.list_contracting_legal_entities(company.id),
        "native_billing_export_payloads": {item.id: ContractService.build_native_billing_fiscal_export_payload(item) for item in native_billings},
        "trigger_type_options": ContractService.get_native_trigger_type_options(),
        "trigger_type_map": dict(ContractService.get_native_trigger_type_options()),
        "reference_date_type_options": ContractService.get_reference_date_type_options(),
        "reference_date_type_map": dict(ContractService.get_reference_date_type_options()),
        "contract_type_options": ContractService.get_contract_type_options(),
        "currency_options": ContractService.get_currency_options(),
        "periodicity_options": ContractService.get_periodicity_options(),
        "competence_rule_options": ContractService.get_competence_rule_options(),
        "renewal_rule_options": ContractService.get_renewal_rule_options(),
        "due_rule_reference_options": ContractService.get_due_rule_reference_options(),
        "due_rule_state": ContractService.parse_due_rule(contract.due_rule if contract else None),
    }


def _process_contract_section_submission(company: Company, contract, active_tab: str) -> str:
    section = _normalize_contract_tab(request.form.get("section") or active_tab)
    if section == "resumo":
        ContractService.update_contract_summary(contract=contract, payload=_normalize_contract_form_payload(request.form), user_id=current_user.id if current_user.is_authenticated else None)
        flash("Resumo do contrato atualizado.", "success")
    elif section == "cliente":
        ContractService.update_contract_customer(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
        flash("Cliente do contrato atualizado.", "success")
    elif section == "itens":
        if request.form.get("delete_item_id"):
            ContractService.delete_contract_item(contract=contract, item_id=int(request.form["delete_item_id"]))
            flash("Item do contrato removido.", "success")
        else:
            ContractService.add_contract_item(contract=contract, payload=request.form.to_dict())
            flash("Item do contrato incluído.", "success")
    elif section == "faturamento":
        if request.form.get("generate_native_billing"):
            native_billing = ContractService.generate_native_billing(
                contract=contract,
                payload=request.form.to_dict(),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash(f"Faturamento nativo {native_billing.billing_code} gerado com sucesso.", "success")
        elif request.form.get("delete_billing_item_id"):
            ContractService.delete_billing_item(contract=contract, item_id=int(request.form["delete_billing_item_id"]))
            flash("Item de faturamento removido.", "success")
        else:
            ContractService.add_billing_item(contract=contract, payload=_normalize_contract_form_payload(request.form))
            flash("Item de faturamento incluído.", "success")
    elif section in {"cobranca", "financeiro"}:
        section = "financeiro"
        if request.form.get("delete_satellite_policy_id"):
            ContractFinancialService.delete_contract_satellite_policy(
                contract=contract,
                policy_id=int(request.form["delete_satellite_policy_id"]),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Regra automática do satélite removida.", "success")
        elif request.form.get("generate_financial_titles_for_billing_id"):
            native_billing = next(
                (item for item in ContractService.list_native_billings(contract) if item.id == int(request.form["generate_financial_titles_for_billing_id"])),
                None,
            )
            if not native_billing:
                raise ValueError("Competência nativa não localizada para gerar os títulos.")
            ContractFinancialService.ensure_financial_titles_for_native_billing(
                contract=contract,
                native_billing=native_billing,
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Títulos financeiros gerados a partir da competência.", "success")
        elif request.form.get("satellite_policy_template_key") or request.form.get("satellite_nature"):
            ContractFinancialService.upsert_contract_satellite_policy(
                contract=contract,
                payload=request.form.to_dict(),
                user_id=current_user.id if current_user.is_authenticated else None,
                policy_id=request.form.get("satellite_policy_id", type=int),
            )
            flash("Regra automática do satélite salva.", "success")
        else:
            ContractService.upsert_financial_terms(
                contract=contract,
                payload=request.form.to_dict(),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Financeiro do contrato atualizado.", "success")
    elif section == "fiscal":
        if request.form.get("delete_retention_id"):
            ContractService.delete_retention(contract=contract, retention_id=int(request.form["delete_retention_id"]))
            flash("Retenção removida.", "success")
        elif request.form.get("retention_id"):
            ContractService.update_retention(
                contract=contract,
                retention_id=int(request.form["retention_id"]),
                payload=request.form.to_dict(),
            )
            flash("Retenção atualizada.", "success")
        elif request.form.get("retention_type"):
            ContractService.add_retention(contract=contract, payload=request.form.to_dict())
            flash("Retenção adicionada.", "success")
        else:
            ContractService.upsert_fiscal_terms(
                contract=contract,
                payload=request.form.to_dict(),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Condições fiscais atualizadas.", "success")
    elif section == "periodicidade":
        if request.form.get("delete_trigger_id"):
            ContractService.delete_trigger(contract=contract, trigger_id=int(request.form["delete_trigger_id"]))
            flash("Gatilho nativo removido.", "success")
        else:
            normalized_payload = _normalize_contract_form_payload(request.form)
            ContractService.update_contract_schedule(contract=contract, payload=normalized_payload, user_id=current_user.id if current_user.is_authenticated else None)
            if request.form.get("trigger_type"):
                ContractService.add_trigger(contract=contract, payload=normalized_payload)
            flash("Agenda nativa do contrato atualizada.", "success")
    elif section == "clausulas":
        if request.form.get("delete_clause_id"):
            ContractService.delete_contract_clause(contract=contract, clause_id=int(request.form["delete_clause_id"]), user_id=current_user.id if current_user.is_authenticated else None)
            flash("Cláusula removida.", "success")
        else:
            ContractService.upsert_contract_clause(contract=contract, payload=request.form.to_dict(), clause_id=request.form.get("clause_id", type=int), user_id=current_user.id if current_user.is_authenticated else None)
            flash("Cláusula salva.", "success")
    elif section == "automacoes":
        if request.form.get("pause_automation_id"):
            ContractService.update_contract_automation_status(
                contract=contract,
                automation_id=int(request.form["pause_automation_id"]),
                activate=False,
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Automação pausada.", "success")
        elif request.form.get("activate_automation_id"):
            ContractService.update_contract_automation_status(
                contract=contract,
                automation_id=int(request.form["activate_automation_id"]),
                activate=True,
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Automação ativada.", "success")
        else:
            automation = ContractService.create_contract_automation(
                contract=contract,
                template_key=request.form.get("automation_template_key"),
                user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash(f"Automação '{automation.name}' criada.", "success")
    elif section == "observacoes":
        ContractService.update_contract_notes(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
        flash("Observações do contrato atualizadas.", "success")
    elif section == "validar":
        ContractService.update_contract_validation(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
        flash("Validação operacional do contrato atualizada.", "success")
    elif section == "revisao":
        flash("A aba de revisão é somente leitura neste MVP.", "info")
    elif section == "gerar_pdf":
        if request.form.get("delete_document_id"):
            ContractService.delete_document(contract=contract, document_id=int(request.form["delete_document_id"]))
            flash("PDF gerado removido.", "success")
        else:
            ContractService.save_document(
                contract=contract,
                document_type="pdf_gerado",
                document_version=request.form.get("document_version"),
                is_signed_version=False,
                file=request.files.get("file"),
                uploaded_by_user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("PDF do contrato registrado.", "success")
    elif section == "contrato_assinado":
        if request.form.get("delete_document_id"):
            ContractService.delete_document(contract=contract, document_id=int(request.form["delete_document_id"]))
            flash("Documento assinado removido.", "success")
        else:
            ContractService.save_document(
                contract=contract,
                document_type="contrato_assinado",
                document_version=request.form.get("document_version"),
                is_signed_version=True,
                file=request.files.get("file"),
                uploaded_by_user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Contrato assinado anexado.", "success")
    elif section == "documentos":
        if request.form.get("delete_document_id"):
            ContractService.delete_document(contract=contract, document_id=int(request.form["delete_document_id"]))
            flash("Documento removido.", "success")
        else:
            ContractService.save_document(
                contract=contract,
                document_type=request.form.get("document_type"),
                document_version=request.form.get("document_version"),
                is_signed_version=bool(request.form.get("is_signed_version")),
                file=request.files.get("file"),
                uploaded_by_user_id=current_user.id if current_user.is_authenticated else None,
            )
            flash("Documento anexado ao contrato.", "success")
    else:
        flash("Seção do contrato não reconhecida.", "error")
    return section


@contracts_bp.route("/contracts", methods=["GET", "POST"])
@contracts_bp.route("/contracts/dashboard", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_dashboard():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    active_tab = _normalize_contract_tab(request.args.get("tab") or "cliente")
    selected_contract_id = request.args.get("contract_id", type=int)
    selected_party_id = request.args.get("party_id", type=int)
    selected_counterparty_id = request.args.get("counterparty_id", type=int)
    parties = ContractService.list_customer_parties(company.id)
    selected_contract = ContractService.get_contract(company.id, selected_contract_id) if selected_contract_id else None
    if selected_contract:
        active_tab = ContractService.resolve_active_tab(selected_contract, active_tab)
    if selected_contract and selected_contract.party:
        selected_party = selected_contract.party
    elif selected_counterparty_id:
        selected_party = ContractService.get_party_by_counterparty_id(company.id, selected_counterparty_id)
    elif selected_party_id:
        selected_party = ContractService.get_party(company.id, selected_party_id)
    else:
        selected_party = parties[0] if parties else None

    if request.method == "POST":
        if selected_contract:
            if not has_permission(company.id, "contracts", "edit"):
                abort(403)
            section = _normalize_contract_tab(request.form.get("section") or active_tab)
            try:
                section = _process_contract_section_submission(company, selected_contract, active_tab)
                return redirect(url_for("contracts.contracts_dashboard", company_id=company.id, contract_id=selected_contract.id, tab=section))
            except Exception as exc:
                flash(f"Falha ao processar a aba '{section}': {exc}", "error")
                active_tab = section
        else:
            try:
                if not has_permission(company.id, "contracts", "create"):
                    abort(403)
                contract = ContractService.create_contract(
                    company_id=company.id,
                    payload=_normalize_contract_form_payload(request.form),
                    user_id=current_user.id if current_user.is_authenticated else None,
                )
                flash("Contrato criado com sucesso. Agora complete o workspace operacional.", "success")
                return redirect(url_for("contracts.contracts_dashboard", company_id=company.id, contract_id=contract.id, tab="cliente"))
            except Exception as exc:
                flash(f"Não foi possível criar o contrato: {exc}", "error")

    context = {
        "company": company,
        "company_id": company.id,
        "contract": selected_contract,
        "selected_contract": selected_contract,
        "selected_contract_summary": ContractService.get_contract_workspace_summary(selected_contract) if selected_contract else None,
        "selected_party": selected_party,
        "contract_tree": ContractService.list_customer_contract_tree(company.id),
        "tabs": ContractService.get_visible_tabs(selected_contract) if selected_contract else ContractService.get_tab_registry(),
        "all_tabs": ContractService.get_tab_registry(),
        "contract_status_label": ContractService.get_contract_status_label,
        "contract_status_group": ContractService.get_contract_status_group,
        "contract_start_date": ContractService.get_contract_start_date,
        "contract_next_action": ContractService.get_contract_next_action,
        "contract_type_options": ContractService.get_contract_type_options(),
        "currency_options": ContractService.get_currency_options(),
        "periodicity_options": ContractService.get_periodicity_options(),
        "competence_rule_options": ContractService.get_competence_rule_options(),
        "renewal_rule_options": ContractService.get_renewal_rule_options(),
        "due_rule_reference_options": ContractService.get_due_rule_reference_options(),
        "operational_profile_options": ContractService.get_operational_profile_options(),
        "parties": parties,
        "active_tab": active_tab,
    }
    if selected_contract:
        context.update(_build_contract_detail_context(company, selected_contract, active_tab))
    return render_template(
        "modules/contracts/contracts_workspace.html",
        **context,
    )


@contracts_bp.route("/contracts/customers/portfolio")
@permission_required("contracts", "view")
def contracts_customer_portfolio():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    return render_template(
        "modules/financial/catalog_detail.html",
        company=company,
        company_id=company.id,
        catalog_slug="customer-portfolios",
        catalog_pages={"customer-portfolios": _build_customer_portfolio_page()},
        catalog_page=_build_customer_portfolio_page(),
        workspace_origin_label="Gestão Comercial",
        workspace_origin_href=f"/contracts?company_id={company.id}",
        workspace_section_label="Cadastros",
        workspace_section_href=f"/contracts/customers/portfolio?company_id={company.id}",
        workspace_current_label="Carteira de Clientes",
    )


@contracts_bp.route("/contracts/customers")
@permission_required("contracts", "view")
def contracts_customers_workspace():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    return render_template(
        "modules/financial/counterparties_workspace.html",
        company=company,
        company_id=company.id,
        catalog_slug="counterparties",
        catalog_pages={"counterparties": _build_commercial_counterparty_page()},
        catalog_page=_build_commercial_counterparty_page(),
        selected_counterparty_id=request.args.get("counterparty_id", type=int),
        workspace_origin_label="Gestão Comercial",
        workspace_origin_href=f"/contracts?company_id={company.id}",
        workspace_section_label="Cadastros",
        workspace_section_href=f"/contracts/customers/portfolio?company_id={company.id}",
        workspace_current_label="Clientes",
        workspace_back_href=f"/contracts/customers/portfolio?company_id={company.id}",
        workspace_back_label="Carteira de Clientes",
        workspace_subtitle="Lista simples dos favorecidos habilitados como cliente. A classificação Cliente/Fornecedor permanece bloqueada aqui e só pode ser alterada no cadastro de favorecidos.",
        workspace_new_enabled=False,
        workspace_list_label="Clientes",
        customer_only_mode=True,
        lock_operational_classification=True,
    )


@contracts_bp.route("/contracts/parties")
@permission_required("contracts", "view")
def contracts_parties_list():
    company = get_active_company()
    parties = ContractService.list_parties(company.id) if company else []
    return render_template("modules/contracts/parties_list.html", company=company, company_id=company.id if company else None, parties=parties)


@contracts_bp.route("/contracts/parties/new", methods=["GET", "POST"])
@contracts_bp.route("/contracts/parties/<int:party_id>", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_party_manage(party_id: int | None = None):
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    selected_counterparty_id = request.args.get("counterparty_id", type=int)
    if party_id:
        party = ContractService.get_party(company.id, party_id)
        if not party:
            abort(404)
        if party.financial_counterparty_id:
            selected_counterparty_id = party.financial_counterparty_id
    return redirect(
        url_for(
            "financial.financial_catalog_detail_page",
            catalog_slug="counterparties",
            company_id=company.id,
            counterparty_id=selected_counterparty_id,
        )
    )


@contracts_bp.route("/contracts/list", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_list():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    active_list_tab = _normalize_contracts_list_tab(request.args.get("tab"))
    selected_contract_id = request.args.get("contract_id", type=int)
    selected_edit_item_id = request.args.get("edit_item_id", type=int)
    mode = (request.args.get("mode") or "").strip().lower()
    filters = {
        "status": request.args.get("status"),
        "party_id": request.args.get("party_id", type=int),
        "manager_employee_id": request.args.get("manager_employee_id", type=int),
        "search": request.args.get("search"),
    }
    contracts = ContractService.list_contracts_filtered(company.id, filters)
    selected_contract = None
    if mode != "new":
        if selected_contract_id:
            selected_contract = ContractService.get_contract(company.id, selected_contract_id)
            if not selected_contract:
                abort(404)
        elif contracts:
            selected_contract = contracts[0]

    if request.method == "POST":
        form_action = (request.form.get("form_action") or "").strip().lower()
        if form_action == "create_contract" or mode == "new":
            if not has_permission(company.id, "contracts", "create"):
                abort(403)
            try:
                contract = ContractService.create_contract(
                    company_id=company.id,
                    payload=_normalize_contracts_list_form_payload(request.form),
                    user_id=current_user.id if current_user.is_authenticated else None,
                )
                flash("Contrato criado com sucesso.", "success")
                return redirect(url_for("contracts.contracts_list", company_id=company.id, contract_id=contract.id, tab="geral"))
            except Exception as exc:
                flash(f"Não foi possível criar o contrato: {exc}", "error")
                selected_contract = None
                mode = "new"
        else:
            if not selected_contract:
                abort(404)
            if not has_permission(company.id, "contracts", "edit"):
                abort(403)
            try:
                if form_action == "delete_contract":
                    ContractService.delete_contract(
                        contract=selected_contract,
                        user_id=current_user.id if current_user.is_authenticated else None,
                        reason=request.form.get("action_reason") or "manual_delete",
                    )
                    flash("Contrato excluído com sucesso.", "success")
                    return redirect(url_for("contracts.contracts_list", company_id=company.id))
                if form_action == "suspend_contract":
                    ContractService.suspend_contract(
                        contract=selected_contract,
                        user_id=current_user.id if current_user.is_authenticated else None,
                        reason=request.form.get("action_reason") or "manual_suspend",
                    )
                    flash("Contrato suspenso com sucesso.", "success")
                    return redirect(url_for("contracts.contracts_list", company_id=company.id, contract_id=selected_contract.id, tab=active_list_tab))
                if form_action == "close_contract":
                    ContractService.close_contract(
                        contract=selected_contract,
                        user_id=current_user.id if current_user.is_authenticated else None,
                        reason=request.form.get("action_reason") or "manual_close",
                    )
                    flash("Contrato encerrado com sucesso.", "success")
                    return redirect(url_for("contracts.contracts_list", company_id=company.id, contract_id=selected_contract.id, tab=active_list_tab))
                active_list_tab = _process_contracts_list_submission(company, selected_contract, active_list_tab)
                return redirect(url_for("contracts.contracts_list", company_id=company.id, contract_id=selected_contract.id, tab=active_list_tab))
            except Exception as exc:
                flash(f"Falha ao processar a aba '{active_list_tab}': {exc}", "error")

    managers = Employee.query.filter_by(company_id=company.id, status="active").order_by(Employee.name.asc()).all()
    parties = ContractService.list_customer_parties(company.id)
    context = {
        "company": company,
        "company_id": company.id,
        "contracts": contracts,
        "contract": selected_contract,
        "selected_contract": selected_contract,
        "selected_contract_summary": ContractService.get_contract_workspace_summary(selected_contract) if selected_contract else None,
        "contract_tree": ContractService.build_contract_list_tree(company.id, filters),
        "contracts_list_tabs": CONTRACTS_LIST_TABS,
        "active_list_tab": active_list_tab,
        "is_new_contract": mode == "new" or selected_contract is None,
        "parties": parties,
        "managers": managers,
        "filters": filters,
        "kpis": ContractService.get_contracts_kpis(company.id),
        "contract_status_group": ContractService.get_contract_status_group,
        "contract_status_label": ContractService.get_contract_status_label,
        "contract_next_action": ContractService.get_contract_next_action,
        "contract_type_options": ContractService.get_contract_type_options(),
        "currency_options": ContractService.get_currency_options(),
        "periodicity_options": ContractService.get_periodicity_options(),
        "competence_rule_options": ContractService.get_competence_rule_options(),
        "renewal_rule_options": ContractService.get_renewal_rule_options(),
        "due_rule_reference_options": ContractService.get_due_rule_reference_options(),
        "retention_trigger_options": ContractService.get_retention_trigger_options(),
        "item_retention_options": ContractService.get_item_retention_options(),
        "item_retention_deduction_mode_options": ContractService.get_item_retention_deduction_mode_options(),
        "item_retention_value_mode_options": ContractService.get_item_retention_value_mode_options(),
        "operational_profile_options": ContractService.get_operational_profile_options(),
        "selected_operational_profile": ContractService.OPERATIONAL_PROFILE_FULL,
        "contract_catalog_items": ContractsCatalogService.list_selectable_items(company.id),
        "references": ContractService.list_financial_references(company.id),
        "financial_terms": None,
        "fiscal_terms": None,
        "native_billings": [],
        "native_billing_preview": None,
        "contracting_legal_entities": ContractService.list_contracting_legal_entities(company.id),
        "due_rule_state": {"reference": None, "day": None, "label": "-", "is_structured": False},
    }
    if selected_contract:
        detail_context = _build_contract_detail_context(company, selected_contract, "resumo")
        context.update(detail_context)
        context["active_list_tab"] = active_list_tab
        context["contracts_list_tabs"] = CONTRACTS_LIST_TABS
        context["is_new_contract"] = False
        edit_item = None
        if active_list_tab == "itens_valores" and selected_edit_item_id:
            edit_item = ContractService.get_contract_item(company.id, selected_contract.id, selected_edit_item_id)
            if not edit_item:
                abort(404)
        context["editing_contract_item"] = edit_item
        context["editing_contract_item_state"] = ContractService.build_contract_item_form_state(edit_item)
    return render_template("modules/contracts/contracts_list.html", **context)


@contracts_bp.route("/contracts/catalogs/items", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_items_catalog():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    selected_item_id = request.args.get("item_id", type=int)
    selected_parent_id = request.args.get("parent_id", type=int)
    catalog_view = (request.args.get("catalog_view") or "structure").strip().lower()

    def _build_structure_option_label(item):
        if not item:
            return ""
        parent = item.parent
        if parent and parent.parent:
            return f"{parent.parent.code} · {parent.parent.name} → {parent.code} · {parent.name}"
        if parent:
            return f"{parent.code} · {parent.name}"
        return f"{item.code} · {item.name}"

    if request.method == "POST":
        action = (request.form.get("action") or "save").strip().lower()
        try:
            if action == "save":
                payload = {
                    "company_id": company.id,
                    "parent_id": request.form.get("parent_id", type=int),
                    "code_suffix": request.form.get("code_suffix"),
                    "name": request.form.get("name"),
                    "item_kind": request.form.get("item_kind"),
                    "description": request.form.get("description"),
                    "unit_code": request.form.get("unit_code"),
                    "is_active": bool(request.form.get("is_active")),
                    "metadata_json": {
                        "sku": request.form.get("sku") or None,
                        "service_code": request.form.get("service_code") or None,
                        "service_list_code": request.form.get("service_list_code") or None,
                        "nbs": request.form.get("nbs") or None,
                        "cindop": request.form.get("cindop") or None,
                        "ncm": request.form.get("ncm") or None,
                        "cest": request.form.get("cest") or None,
                        "cfop": request.form.get("cfop") or None,
                        "cst_ibs_cbs": request.form.get("cst_ibs_cbs") or None,
                        "cclasstrib": request.form.get("cclasstrib") or None,
                        "cpres": request.form.get("cpres") or None,
                        "aliq_cbs": request.form.get("aliq_cbs") or None,
                        "aliq_ibs_uf": request.form.get("aliq_ibs_uf") or None,
                        "aliq_ibs_mun": request.form.get("aliq_ibs_mun") or None,
                        "is_subject": bool(request.form.get("is_subject")),
                        "cst_is": request.form.get("cst_is") or None,
                        "cclasstrib_is": request.form.get("cclasstrib_is") or None,
                        "stock_control": bool(request.form.get("stock_control")),
                        "fiscal_notes": request.form.get("fiscal_notes") or None,
                    },
                }
                if catalog_view == "items":
                    parent_item = ContractsCatalogService.get_item(company.id, payload["parent_id"]) if payload.get("parent_id") else None
                    if not parent_item or ContractsCatalogService.get_level_label(parent_item) != "Sub-Grupo":
                        raise ValueError("Selecione um Sub-Grupo da árvore comercial para vincular o produto/serviço.")
                item_id = request.form.get("item_id", type=int)
                if item_id:
                    item = ContractsCatalogService.get_item(company.id, item_id)
                    if not item:
                        abort(404)
                    ContractsCatalogService.update_item(item=item, payload=payload)
                    flash("Item mestre atualizado com sucesso.", "success")
                    selected_item_id = item.id
                else:
                    item = ContractsCatalogService.create_item(payload=payload)
                    flash("Item mestre criado com sucesso.", "success")
                    selected_item_id = item.id
                return redirect(url_for("contracts.contracts_items_catalog", company_id=company.id, item_id=selected_item_id, catalog_view=catalog_view))

            target_item_id = request.form.get("item_id", type=int)
            item = ContractsCatalogService.get_item(company.id, target_item_id) if target_item_id else None
            if not item:
                abort(404)
            if action == "toggle":
                ContractsCatalogService.toggle_item(item=item, is_active=not item.is_active)
                flash("Status do item mestre atualizado.", "success")
            elif action == "delete":
                ContractsCatalogService.delete_item(item=item)
                flash("Item mestre excluído.", "success")
            return redirect(url_for("contracts.contracts_items_catalog", company_id=company.id, catalog_view=catalog_view))
        except Exception as exc:
            flash(f"Falha ao processar catálogo de itens: {exc}", "error")

    items = ContractsCatalogService.list_items(company.id)
    catalog_tree = ContractsCatalogService.build_tree(company.id)
    selected_item = ContractsCatalogService.get_item(company.id, selected_item_id) if selected_item_id else None
    if selected_item and selected_item.parent_id:
        selected_parent_id = selected_item.parent_id
    selected_parent = ContractsCatalogService.get_item(company.id, selected_parent_id) if selected_parent_id else None

    if catalog_view == "structure":
        if selected_item and not _is_contract_catalog_structure_item(selected_item):
            selected_item = None
        if selected_parent and ContractsCatalogService.get_level_label(selected_parent) != "Grupo":
            selected_parent = None

        def _filter_structure_tree(nodes):
            filtered = []
            for node in nodes:
                if not _is_contract_catalog_structure_item(node.get("item")):
                    continue
                clone = dict(node)
                clone["children"] = _filter_structure_tree(node.get("children") or [])
                filtered.append(clone)
            return filtered

        structure_items = [item for item in items if _is_contract_catalog_structure_item(item)]
        structure_tree = _filter_structure_tree(catalog_tree)
        structure_parent_candidates = [
            item
            for item in items
            if ContractsCatalogService.get_level_label(item) == "Grupo" and (not selected_item or item.id != selected_item.id)
        ]
        return render_template(
            "modules/contracts/contracts_items_catalog_structure.html",
            company=company,
            company_id=company.id,
            catalog_tree=structure_tree,
            items=structure_items,
            parent_candidates=structure_parent_candidates,
            selected_item=selected_item,
            selected_parent=selected_parent,
            level_label=ContractsCatalogService.get_level_label,
            level_label_by_parent=ContractsCatalogService.get_level_label_by_parent,
            catalog_view=catalog_view,
        )

    if catalog_view == "items":
        if selected_item and ContractsCatalogService.get_level_label(selected_item) != "Item":
            if ContractsCatalogService.get_level_label(selected_item) == "Sub-Grupo":
                selected_parent = selected_item
            selected_item = None
        if selected_parent and ContractsCatalogService.get_level_label(selected_parent) != "Sub-Grupo":
            selected_parent = None

        leaf_items = ContractsCatalogService.list_leaf_items(company.id)
        leaf_parent_candidates = ContractsCatalogService.list_leaf_parent_candidates(
            company.id,
            selected_item.id if selected_item else None,
        )
        parent_options = [
            {
                "id": item.id,
                "label": f"{_build_structure_option_label(item)} → {item.code} · {item.name}",
            }
            for item in leaf_parent_candidates
        ]
        return render_template(
            "modules/contracts/contracts_items_catalog_items.html",
            company=company,
            company_id=company.id,
            items=leaf_items,
            parent_candidates=leaf_parent_candidates,
            parent_options=parent_options,
            selected_item=selected_item,
            selected_parent=selected_parent,
            level_label=ContractsCatalogService.get_level_label,
            level_label_by_parent=ContractsCatalogService.get_level_label_by_parent,
            catalog_view=catalog_view,
        )

    return render_template(
        "modules/contracts/contracts_items_catalog.html",
        company=company,
        company_id=company.id,
        catalog_tree=catalog_tree,
        items=items,
        parent_candidates=ContractsCatalogService.list_parent_candidates(company.id, selected_item.id if selected_item else None),
        selected_item=selected_item,
        selected_parent=selected_parent,
        level_label=ContractsCatalogService.get_level_label,
        level_label_by_parent=ContractsCatalogService.get_level_label_by_parent,
        catalog_view=catalog_view,
    )


@contracts_bp.route("/contracts/legal-entities", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_legal_entities():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    selected_entity_id = request.args.get("entity_id", type=int)
    if request.method == "POST":
        try:
            if not has_permission(company.id, "contracts", "edit"):
                abort(403)
            entity_id = request.form.get("entity_id", type=int)
            if entity_id:
                entity = ContractService.get_contracting_legal_entity(company.id, entity_id)
                if not entity:
                    abort(404)
                ContractService.update_contracting_legal_entity(entity=entity, payload=request.form.to_dict())
                flash("PJ contratada atualizada com sucesso.", "success")
                selected_entity_id = entity.id
            else:
                entity = ContractService.create_contracting_legal_entity(company_id=company.id, payload=request.form.to_dict())
                flash("PJ contratada criada com sucesso.", "success")
                selected_entity_id = entity.id
            return redirect(url_for("contracts.contracts_legal_entities", company_id=company.id, entity_id=selected_entity_id))
        except Exception as exc:
            flash(f"Falha ao salvar PJ contratada: {exc}", "error")

    legal_entities = ContractService.list_contracting_legal_entities(company.id)
    selected_entity = ContractService.get_contracting_legal_entity(company.id, selected_entity_id) if selected_entity_id else None
    return render_template(
        "modules/contracts/legal_entities.html",
        company=company,
        company_id=company.id,
        legal_entities=legal_entities,
        selected_entity=selected_entity,
        selected_iss_rule=(
            ContractService.get_contracting_legal_entity_active_iss_rule(selected_entity)
            or ContractService.get_contracting_legal_entity_latest_iss_rule(selected_entity)
        ) if selected_entity else None,
        selected_iss_rules=ContractService.list_contracting_legal_entity_iss_rules(selected_entity) if selected_entity else [],
        next_code_preview=ContractService.preview_next_contracting_legal_entity_code(company.id),
        page_origin_label="Gestão Comercial",
        page_section_label="Cadastros",
        page_title="PJs Emissoras",
        page_subtitle="Cadastre as pessoas jurídicas emissoras que poderão ser usadas na operação fiscal e contratual.",
    )


@contracts_bp.route("/contracts/billing", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_billing_workspace():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "create"):
            abort(403)
        contract_ids = _parse_int_list(request.form.getlist("contract_ids"))
        if not contract_ids:
            flash("Selecione ao menos um contrato apto para faturar.", "error")
            return redirect(url_for("contracts.contracts_billing_workspace", company_id=company.id))
        return redirect(
            url_for(
                "contracts.contracts_billing_review",
                company_id=company.id,
                contract_ids=",".join(str(item) for item in contract_ids),
            )
        )

    filters = _contracts_billing_filters_from_request()
    billing_rows = ContractService.list_contracts_billing_view(company.id, filters)
    return render_template(
        "modules/contracts/contracts_billing.html",
        company=company,
        company_id=company.id,
        billing_rows=billing_rows,
        parties=ContractService.list_customer_parties(company.id),
        legal_entities=ContractService.list_contracting_legal_entities(company.id),
        managers=Employee.query.filter_by(company_id=company.id, status="active").order_by(Employee.name.asc()).all(),
        filters=filters,
        kpis=ContractService.get_contracts_kpis(company.id),
    )


@contracts_bp.route("/contracts/billing/review", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_billing_review():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "create"):
            abort(403)
        contract_ids = _parse_int_list(request.form.getlist("contract_ids"))
        if not contract_ids:
            flash("Nenhum contrato ficou selecionado para faturamento.", "error")
            return redirect(url_for("contracts.contracts_billing_workspace", company_id=company.id))
        if request.form.get("form_action") == "confirm":
            result = ContractService.confirm_native_billing_review(
                company_id=company.id,
                review_payloads=_build_billing_confirmation_payloads(contract_ids),
                user_id=_current_user_id(),
            )
            if result["created"]:
                flash(f"{len(result['created'])} faturamento(s) gerado(s) com sucesso.", "success")
            for error in result["errors"]:
                flash(error, "error")
            if result["created"] and not result["errors"]:
                return redirect(url_for("contracts.contracts_billing_done", company_id=company.id))
        overrides = _build_billing_review_overrides(contract_ids)
    else:
        contract_id_args = request.args.getlist("contract_ids") or [request.args.get("contract_ids")]
        contract_ids = _parse_int_list(contract_id_args)
        overrides = None

    review_rows = ContractService.build_billing_review_rows(company.id, contract_ids, overrides)
    return render_template(
        "modules/contracts/contracts_billing_review.html",
        company=company,
        company_id=company.id,
        review_rows=review_rows,
        contract_ids=contract_ids,
    )


@contracts_bp.route("/contracts/billing/done", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_billing_done():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "create"):
            abort(403)
        try:
            form_action = (request.form.get("form_action") or "").strip()
            native_billing_id = request.form.get("native_billing_id", type=int)
            if not native_billing_id:
                raise ValueError("Faturamento não informado.")
            if form_action == "generate_financial_titles":
                native_billing = ContractNativeBilling.query.filter(
                    ContractNativeBilling.company_id == company.id,
                    ContractNativeBilling.id == native_billing_id,
                    ContractNativeBilling.status != "cancelled",
                ).first()
                if not native_billing:
                    raise ValueError("Faturamento não localizado para integração financeira.")
                contract = native_billing.contract
                if not contract:
                    raise ValueError("Contrato do faturamento não localizado para integração financeira.")
                ContractFinancialService.ensure_financial_titles_for_native_billing(
                    contract=contract,
                    native_billing=native_billing,
                    user_id=_current_user_id(),
                )
                flash("Integração financeira do faturamento executada com sucesso.", "success")
            else:
                ContractService.cancel_native_billing(
                    company_id=company.id,
                    native_billing_id=native_billing_id,
                    user_id=_current_user_id(),
                    reason=request.form.get("cancel_reason"),
                )
                flash("Faturamento cancelado e vínculos financeiros satélites marcados para auditoria.", "success")
        except Exception as exc:
            flash(f"Não foi possível processar o faturamento: {exc}", "error")
        return redirect(url_for("contracts.contracts_billing_done", company_id=company.id))

    filters = _billing_done_filters_from_request()
    billing_rows = ContractService.list_native_billings_done(company.id, filters)
    return render_template(
        "modules/contracts/contracts_billing_done.html",
        company=company,
        company_id=company.id,
        billing_rows=billing_rows,
        parties=ContractService.list_customer_parties(company.id),
        filters=filters,
    )


@contracts_bp.route("/contracts/invoices", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_fiscal_invoices():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "create"):
            abort(403)
        action = (request.form.get("form_action") or "").strip()
        selected_ids = _parse_int_list(request.form.getlist("billing_ids"))
        try:
            if action == "create_batch":
                result = ContractService.assign_fiscal_invoice_batch(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    batch_code=None,
                    user_id=_current_user_id(),
                )
                flash(f"Lote {result['batch_code']} criado com {result['updated']} nota(s).", "success")
            elif action == "assign_batch":
                result = ContractService.assign_fiscal_invoice_batch(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    batch_code=request.form.get("target_batch_code"),
                    user_id=_current_user_id(),
                )
                flash(f"{result['updated']} nota(s) incluída(s) no lote {result['batch_code']}.", "success")
            elif action == "remove_batch":
                result = ContractService.remove_fiscal_invoice_batch(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    user_id=_current_user_id(),
                )
                flash(f"{result['updated']} nota(s) removida(s) do lote.", "success")
            elif action == "export_integration":
                export = ContractService.build_fiscal_invoice_integration_spreadsheet(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    user_id=_current_user_id(),
                )
                return Response(
                    export["content"],
                    mimetype=export.get("mimetype") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={export['filename']}"},
                )
            elif action == "mark_emitted":
                result = ContractService.update_fiscal_invoice_status(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    status="emitted",
                    payload=request.form.to_dict(),
                    user_id=_current_user_id(),
                )
                flash(f"{result['updated']} nota(s) marcada(s) como emitida(s).", "success")
            elif action == "mark_cancelled":
                result = ContractService.update_fiscal_invoice_status(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    status="cancelled",
                    payload=request.form.to_dict(),
                    user_id=_current_user_id(),
                )
                flash(f"{result['updated']} nota(s) marcada(s) como cancelada(s).", "success")
            elif action == "delete_invoice":
                result = ContractService.update_fiscal_invoice_status(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    status="deleted",
                    payload=request.form.to_dict(),
                    user_id=_current_user_id(),
                )
                flash(f"{result['updated']} nota(s) excluída(s) da fila fiscal.", "success")
            elif action == "update_fiscal_data":
                billing_id = request.form.get("billing_id", type=int)
                if not billing_id:
                    raise ValueError("Registro fiscal não informado.")
                ContractService.update_fiscal_invoice_data(
                    company_id=company.id,
                    billing_id=billing_id,
                    payload=request.form.to_dict(),
                    user_id=_current_user_id(),
                )
                flash("Dados fiscais atualizados.", "success")
            elif action == "upload_files":
                files = request.files.getlist("invoice_files")
                result = ContractService.upload_fiscal_invoice_files(
                    company_id=company.id,
                    billing_ids=selected_ids,
                    files=files,
                    user_id=_current_user_id(),
                )
                flash(f"Upload processado: {result['updated']} vínculo(s), {result['unmatched']} arquivo(s) sem correspondência.", "success")
            else:
                flash("Ação fiscal não reconhecida.", "error")
        except Exception as exc:
            flash(f"Falha na operação fiscal: {exc}", "error")
        return redirect(url_for("contracts.contracts_fiscal_invoices", company_id=company.id))

    filters = _fiscal_invoice_filters_from_request()
    workspace = ContractService.list_fiscal_invoice_workspace(company.id, filters)
    return render_template(
        "modules/contracts/contracts_fiscal_invoices.html",
        company=company,
        company_id=company.id,
        invoice_rows=workspace["rows"],
        invoice_batches=workspace["batches"],
        invoice_kpis=workspace["kpis"],
        filters=filters,
        parties=ContractService.list_customer_parties(company.id),
        issuing_legal_entities=ContractService.list_contracting_legal_entities(company.id),
    )


@contracts_bp.route("/contracts/new", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_create():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    selected_party_id = request.args.get("party_id", type=int)

    if request.method == "GET":
        return redirect(url_for("contracts.contracts_dashboard", company_id=company.id, party_id=selected_party_id))

    if request.method == "POST":
        try:
            if not has_permission(company.id, "contracts", "create"):
                abort(403)
            contract = ContractService.create_contract(company_id=company.id, payload=_normalize_contract_form_payload(request.form), user_id=current_user.id if current_user.is_authenticated else None)
            flash("Contrato criado com sucesso. Agora complete o workspace operacional.", "success")
            return redirect(url_for("contracts.contracts_dashboard", contract_id=contract.id, company_id=company.id, tab="cliente"))
        except Exception as exc:
            flash(f"Não foi possível criar o contrato: {exc}", "error")

    parties = ContractService.list_customer_parties(company.id)
    if selected_party_id:
        selected_party = ContractService.get_party(company.id, selected_party_id)
    else:
        selected_party = parties[0] if parties else None
    return render_template(
        "modules/contracts/contract_create.html",
        company=company,
        company_id=company.id,
        parties=parties,
        selected_party=selected_party,
        tabs=ContractService.get_tab_registry(),
        managers=Employee.query.filter_by(company_id=company.id, status="active").order_by(Employee.name.asc()).all(),
        contract_type_options=ContractService.get_contract_type_options(),
        currency_options=ContractService.get_currency_options(),
        periodicity_options=ContractService.get_periodicity_options(),
        competence_rule_options=ContractService.get_competence_rule_options(),
        due_rule_reference_options=ContractService.get_due_rule_reference_options(),
    )


@contracts_bp.route("/contracts/<int:contract_id>", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_manage(contract_id: int):
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    contract = ContractService.get_contract(company.id, contract_id)
    if not contract:
        abort(404)
    active_tab = _normalize_contract_tab(request.args.get("tab") or "cliente")

    if request.method == "GET":
        return redirect(url_for("contracts.contracts_dashboard", contract_id=contract.id, company_id=company.id, tab=active_tab))

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "edit"):
            abort(403)
        section = _normalize_contract_tab(request.form.get("section") or active_tab)
        try:
            section = _process_contract_section_submission(company, contract, active_tab)
            return redirect(url_for("contracts.contracts_dashboard", contract_id=contract.id, company_id=company.id, tab=section))
        except Exception as exc:
            flash(f"Falha ao processar a aba '{section}': {exc}", "error")
            active_tab = section
    return render_template(
        "modules/contracts/contracts_workspace.html",
        company=company,
        company_id=company.id,
        contract=contract,
        selected_contract=contract,
        selected_contract_summary=ContractService.get_contract_workspace_summary(contract) if contract else None,
        selected_party=contract.party,
        contract_tree=ContractService.list_customer_contract_tree(company.id),
        contract_status_label=ContractService.get_contract_status_label,
        contract_status_group=ContractService.get_contract_status_group,
        contract_start_date=ContractService.get_contract_start_date,
        contract_next_action=ContractService.get_contract_next_action,
        **_build_contract_detail_context(company, contract, active_tab),
    )
