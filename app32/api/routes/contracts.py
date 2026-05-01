from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from models import Company, Employee
from models.contracts import ContractFinancialTerm, ContractFiscalTerm
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

    party = ContractService.get_party(company.id, party_id) if party_id else None
    if party_id and not party:
        abort(404)

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "edit"):
            abort(403)
        payload = request.form.to_dict()
        try:
            if party is None:
                party = ContractService.create_party(company_id=company.id, payload=payload, user_id=current_user.id if current_user.is_authenticated else None)
                flash("Favorecido criado com sucesso.", "success")
            else:
                ContractService.update_party(party=party, payload=payload, user_id=current_user.id if current_user.is_authenticated else None)
                flash("Favorecido atualizado com sucesso.", "success")
            return redirect(url_for("contracts.contracts_party_manage", party_id=party.id, company_id=company.id))
        except Exception as exc:
            flash(f"Não foi possível salvar o favorecido: {exc}", "error")

    counterparties = ContractService.list_financial_counterparties(company.id)
    return render_template("modules/contracts/party_manage.html", company=company, company_id=company.id, party=party, counterparties=counterparties)


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

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "create"):
            abort(403)
        try:
            contract = ContractService.create_contract(company_id=company.id, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
            flash("Contrato criado com sucesso.", "success")
            return redirect(url_for("contracts.contracts_manage", contract_id=contract.id, company_id=company.id))
        except Exception as exc:
            flash(f"Não foi possível criar o contrato: {exc}", "error")

    return render_template(
        "modules/contracts/contract_create.html",
        company=company,
        company_id=company.id,
        parties=ContractService.list_parties(company.id),
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

    active_tab = (request.args.get("tab") or "geral").strip().lower()

    if request.method == "POST":
        if not has_permission(company.id, "contracts", "edit"):
            abort(403)
        section = (request.form.get("section") or active_tab).strip().lower()
        try:
            if section == "geral":
                ContractService.update_contract_general(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
                flash("Dados gerais do contrato atualizados.", "success")
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
            elif section == "financeiro":
                ContractService.upsert_financial_terms(contract=contract, payload=request.form.to_dict())
                flash("Condições financeiras atualizadas.", "success")
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
            elif section == "gatilhos":
                if request.form.get("delete_trigger_id"):
                    ContractService.delete_trigger(contract=contract, trigger_id=int(request.form["delete_trigger_id"]))
                    flash("Gatilho removido.", "success")
                else:
                    ContractService.update_contract_general(contract=contract, payload=request.form.to_dict(), user_id=current_user.id if current_user.is_authenticated else None)
                    if request.form.get("trigger_type"):
                        ContractService.add_trigger(contract=contract, payload=request.form.to_dict())
                    flash("Datas e gatilhos atualizados.", "success")
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
    return render_template(
        "modules/contracts/contract_manage.html",
        company=company,
        company_id=company.id,
        contract=contract,
        parties=ContractService.list_parties(company.id),
        financial_terms=financial_terms,
        fiscal_terms=fiscal_terms,
        references=references,
        active_tab=active_tab,
    )
