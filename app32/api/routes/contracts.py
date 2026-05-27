from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from models import Company, Employee
from models.contracts import ContractDocument, ContractFinancialTerm, ContractFiscalTerm
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
    return {
        "parties": parties,
        "contract_catalog_items": contract_catalog_items,
        "financial_terms": financial_terms,
        "fiscal_terms": fiscal_terms,
        "references": references,
        "active_tab": active_tab,
        "tabs": ContractService.get_tab_registry(),
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
        "selected_contract": selected_contract,
        "selected_contract_summary": ContractService.get_contract_workspace_summary(selected_contract) if selected_contract else None,
        "selected_party": selected_party,
        "contract_tree": ContractService.list_customer_contract_tree(company.id),
        "tabs": ContractService.get_tab_registry(),
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
        "parties": parties,
        "active_tab": active_tab,
    }
    if selected_contract:
        context.update(_build_contract_detail_context(company, selected_contract, active_tab))
    return render_template(
        "modules/contracts/contracts_workspace.html",
        **context,
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


@contracts_bp.route("/contracts/list")
@permission_required("contracts", "view")
def contracts_list():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")
    filters = {
        "status": request.args.get("status"),
        "party_id": request.args.get("party_id", type=int),
        "manager_employee_id": request.args.get("manager_employee_id", type=int),
        "search": request.args.get("search"),
    }
    contracts = ContractService.list_contracts_filtered(company.id, filters)
    managers = Employee.query.filter_by(company_id=company.id, status="active").order_by(Employee.name.asc()).all()
    return render_template(
        "modules/contracts/contracts_list.html",
        company=company,
        company_id=company.id,
        contracts=contracts,
        parties=ContractService.list_customer_parties(company.id),
        managers=managers,
        filters=filters,
        kpis=ContractService.get_contracts_kpis(company.id),
        contract_status_group=ContractService.get_contract_status_group,
        contract_next_action=ContractService.get_contract_next_action,
    )


@contracts_bp.route("/contracts/catalogs/items", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_items_catalog():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    selected_item_id = request.args.get("item_id", type=int)
    selected_parent_id = request.args.get("parent_id", type=int)

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
                return redirect(url_for("contracts.contracts_items_catalog", company_id=company.id, item_id=selected_item_id))

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
                return redirect(url_for("contracts.contracts_items_catalog", company_id=company.id))
        except Exception as exc:
            flash(f"Falha ao processar catálogo de itens: {exc}", "error")

    items = ContractsCatalogService.list_items(company.id)
    selected_item = ContractsCatalogService.get_item(company.id, selected_item_id) if selected_item_id else None
    if selected_item and selected_item.parent_id:
        selected_parent_id = selected_item.parent_id
    selected_parent = ContractsCatalogService.get_item(company.id, selected_parent_id) if selected_parent_id else None
    return render_template(
        "modules/contracts/contracts_items_catalog.html",
        company=company,
        company_id=company.id,
        catalog_tree=ContractsCatalogService.build_tree(company.id),
        items=items,
        parent_candidates=ContractsCatalogService.list_parent_candidates(company.id, selected_item.id if selected_item else None),
        selected_item=selected_item,
        selected_parent=selected_parent,
        level_label=ContractsCatalogService.get_level_label,
        level_label_by_parent=ContractsCatalogService.get_level_label_by_parent,
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
