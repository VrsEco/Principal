from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from models import Company, Employee
from models.contracts import ContractDocument, ContractFinancialTerm, ContractFiscalTerm
from services.contracts_service import ContractService
from utils.permissions import get_default_company_id, has_permission, permission_required


contracts_bp = Blueprint("contracts", __name__)


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


@contracts_bp.route("/contracts")
@contracts_bp.route("/contracts/dashboard")
@permission_required("contracts", "view")
def contracts_dashboard():
    company = get_active_company()
    company_id = company.id if company else None
    dashboard = ContractService.get_dashboard(company_id) if company_id else {"counts": {}, "latest_contracts": [], "latest_parties": []}
    return render_template("modules/contracts/dashboard.html", company=company, company_id=company_id, dashboard=dashboard)


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
    contracts = ContractService.list_contracts(company.id) if company else []
    return render_template("modules/contracts/contracts_list.html", company=company, company_id=company.id if company else None, contracts=contracts)


@contracts_bp.route("/contracts/new", methods=["GET", "POST"])
@permission_required("contracts", "view")
def contracts_create():
    company = get_active_company()
    if not company:
        abort(400, description="Empresa ativa não localizada.")

    selected_contract_id = request.args.get("contract_id", type=int)
    selected_party_id = request.args.get("party_id", type=int)
    selected_counterparty_id = request.args.get("counterparty_id", type=int)

    if request.method == "POST":
        section = (request.form.get("section") or "create_contract").strip().lower()
        try:
            if section == "create_contract":
                if not has_permission(company.id, "contracts", "create"):
                    abort(403)
                contract = ContractService.create_contract(company_id=company.id, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
                flash("Contrato criado com sucesso.", "success")
                return redirect(url_for("contracts.contracts_create", company_id=company.id, contract_id=contract.id, party_id=contract.party_id))
            if section == "resumo":
                if not has_permission(company.id, "contracts", "edit"):
                    abort(403)
                contract_id = request.form.get("contract_id", type=int)
                contract = ContractService.get_contract(company.id, contract_id) if contract_id else None
                if not contract:
                    abort(404)
                ContractService.update_contract_summary(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
                flash("Resumo do contrato atualizado.", "success")
                return redirect(url_for("contracts.contracts_create", company_id=company.id, contract_id=contract.id, party_id=contract.party_id))
            flash("Ação do workspace de contratos não reconhecida.", "error")
        except Exception as exc:
            action_label = "salvar o contrato" if section == "resumo" else "criar o contrato"
            flash(f"Não foi possível {action_label}: {exc}", "error")

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

    return render_template(
        "modules/contracts/contracts_workspace.html",
        company=company,
        company_id=company.id,
        parties=parties,
        selected_contract=selected_contract,
        selected_party=selected_party,
        contract_tree=ContractService.list_customer_contract_tree(company.id),
        tabs=ContractService.get_tab_registry(),
        contract_status_label=ContractService.get_contract_status_label,
        contract_status_group=ContractService.get_contract_status_group,
        contract_start_date=ContractService.get_contract_start_date,
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

    tab_aliases = {
        "geral": "resumo",
        "financeiro": "cobranca",
        "gatilhos": "periodicidade",
        "anexos": "documentos",
    }
    active_tab = tab_aliases.get((request.args.get("tab") or "resumo").strip().lower(), (request.args.get("tab") or "resumo").strip().lower())

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "edit"):
            abort(403)
        section = (request.form.get("section") or active_tab).strip().lower()
        try:
            if section == "resumo":
                ContractService.update_contract_summary(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
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
                if request.form.get("delete_billing_item_id"):
                    ContractService.delete_billing_item(contract=contract, item_id=int(request.form["delete_billing_item_id"]))
                    flash("Item de faturamento removido.", "success")
                else:
                    ContractService.add_billing_item(contract=contract, payload=request.form.to_dict())
                    flash("Item de faturamento incluído.", "success")
            elif section == "cobranca":
                ContractService.upsert_financial_terms(contract=contract, payload=request.form.to_dict())
                flash("Cobrança e condições financeiras atualizadas.", "success")
            elif section == "fiscal":
                if request.form.get("delete_retention_id"):
                    ContractService.delete_retention(contract=contract, retention_id=int(request.form["delete_retention_id"]))
                    flash("Retenção removida.", "success")
                elif request.form.get("retention_type"):
                    ContractService.add_retention(contract=contract, payload=request.form.to_dict())
                    flash("Retenção adicionada.", "success")
                else:
                    ContractService.upsert_fiscal_terms(contract=contract, payload=request.form.to_dict())
                    flash("Condições fiscais atualizadas.", "success")
            elif section == "periodicidade":
                if request.form.get("delete_trigger_id"):
                    ContractService.delete_trigger(contract=contract, trigger_id=int(request.form["delete_trigger_id"]))
                    flash("Gatilho removido.", "success")
                else:
                    ContractService.update_contract_schedule(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
                    if request.form.get("trigger_type"):
                        ContractService.add_trigger(contract=contract, payload=request.form.to_dict())
                    flash("Periodicidade, datas-base e gatilhos atualizados.", "success")
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
            return redirect(url_for("contracts.contracts_manage", contract_id=contract.id, company_id=company.id, tab=section))
        except Exception as exc:
            flash(f"Falha ao processar a aba '{section}': {exc}", "error")
            active_tab = section

    financial_terms = ContractFinancialTerm.query.filter_by(contract_id=contract.id, company_id=company.id).first()
    fiscal_terms = ContractFiscalTerm.query.filter_by(contract_id=contract.id, company_id=company.id).first()
    references = ContractService.list_financial_references(company.id)
    parties = ContractService.list_customer_parties(company.id)
    if contract.party and not any(item.id == contract.party.id for item in parties):
        parties = [contract.party, *parties]
    documents = ContractDocument.query.filter_by(contract_id=contract.id, company_id=company.id).order_by(ContractDocument.uploaded_at.desc()).all()
    pdf_documents = [item for item in documents if item.document_type == "pdf_gerado"]
    signed_documents = [item for item in documents if item.document_type == "contrato_assinado" or item.is_signed_version]
    generic_documents = [item for item in documents if item.document_type not in {"pdf_gerado", "contrato_assinado"} and not item.is_signed_version]
    return render_template(
        "modules/contracts/contract_manage.html",
        company=company,
        company_id=company.id,
        contract=contract,
        parties=parties,
        financial_terms=financial_terms,
        fiscal_terms=fiscal_terms,
        references=references,
        active_tab=active_tab,
        tabs=ContractService.get_tab_registry(),
        pdf_documents=pdf_documents,
        signed_documents=signed_documents,
        generic_documents=generic_documents,
    )
