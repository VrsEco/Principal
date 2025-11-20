import logging
from flask_login import login_required
from flask import Blueprint, render_template, url_for, request, jsonify, redirect
from datetime import datetime
import json
from typing import Any, Dict, List
from config_database import get_db
from modules.pev.implantation_data import (
    build_final_report_payload,
    build_overview_payload,
    build_persona_segments,
    build_competitive_segments,
    build_value_canvas_segments,
    build_plan_context,
    load_alignment_agenda,
    load_alignment_canvas,
    load_alignment_project,
    load_financial_model,
    load_segments,
    load_structures,
    summarize_structures_for_report,
    calculate_investment_summary_by_block,
    aggregate_structure_investments,
    serialize_structure_investment_summary,
    build_modefin_investment_flow,
    build_modefin_business_flow,
    build_modefin_investor_flow,
    _classify_structure_installment,
    _month_key_from_tuple,
    _month_tuple_from_value,
    _parse_decimal,
)
from modules.pev import products_service
from services.ui_catalog_service import (
    get_screen_attr_map,
    serialize_screen_catalog,
)

MODEFIN_SCREEN_CODE = 314

logger = logging.getLogger(__name__)
pev_bp = Blueprint("pev", __name__, url_prefix="/pev")


def _calcular_tir_newton(fluxos: List[float]) -> float:
    """
    Calcula TIR usando método de Newton-Raphson
    Retorna taxa mensal (ou None se não convergir)
    """
    if not fluxos:
        return None

    # Verificar se há fluxos negativos e positivos
    tem_negativo = any(f < 0 for f in fluxos)
    tem_positivo = any(f > 0 for f in fluxos)

    if not (tem_negativo and tem_positivo):
        return None

    # Newton-Raphson
    taxa = 0.10  # Chute inicial: 10% ao mês
    max_iter = 100
    precisao = 0.0001

    for _ in range(max_iter):
        vpl = 0.0
        derivada = 0.0

        for periodo, fluxo in enumerate(fluxos, start=1):
            vpl += fluxo / ((1 + taxa) ** periodo)
            derivada -= (periodo * fluxo) / ((1 + taxa) ** (periodo + 1))

        # Se VPL próximo de zero, encontramos a TIR
        if abs(vpl) < precisao:
            return taxa

        # Evitar divisão por zero
        if abs(derivada) < 0.000001:
            return None

        # Newton-Raphson
        nova_taxa = taxa - vpl / derivada

        # Limitar taxa entre -50% e 200% ao mês
        if nova_taxa < -0.5:
            nova_taxa = -0.5
        if nova_taxa > 2.0:
            nova_taxa = 2.0

        taxa = nova_taxa

    return taxa


def _resolve_plan_id():
    """Return plan id from query parameters. Raises error if not provided."""
    plan_id = request.args.get("plan_id")
    if plan_id:
        try:
            return int(plan_id)
        except (TypeError, ValueError):
            logger.info(f"[ERROR] plan_id inválido: {plan_id}")
            pass

    view_args = getattr(request, "view_args", None) or {}
    plan_id = view_args.get("plan_id")
    if plan_id:
        try:
            return int(plan_id)
        except (TypeError, ValueError):
            logger.info(f"[ERROR] plan_id inválido em view_args: {plan_id}")
            pass

    # ERRO: plan_id não foi fornecido - isso NÃO deve acontecer!
    logger.info(
        f"[CRITICAL ERROR] plan_id não fornecido na URL! request.url: {request.url}"
    )
    raise ValueError("plan_id é obrigatório e deve ser passado na URL")


def _get_plan_context(plan_id: int):
    """Fetch plan and company information for headers and reports."""
    db = get_db()
    return build_plan_context(db, plan_id)


def _prepare_report_one_payload(db, plan_id: int) -> dict:
    """Aggregate data for the modular report 01 (capa + resumo executivo)."""
    plan = build_plan_context(db, plan_id)
    projeto = load_alignment_project(db, plan_id)
    segmentos = load_segments(db, plan_id)
    estruturas = load_structures(db, plan_id)
    agenda_data = load_alignment_agenda(db, plan_id) or {}
    atividades = agenda_data.get("atividades") or []
    financeiro = load_financial_model(db, plan_id) or {}

    investimento_total = ""
    investimento = financeiro.get("investimento") or {}
    resumo_investimento = investimento.get("resumo") or {}
    investimento_total = (
        resumo_investimento.get("necessidade_total")
        or resumo_investimento.get("necessidade_total_formatado")
        or resumo_investimento.get("necessidade_total_br")
        or investimento.get("total_formatado")
        or "-"
    )

    proximas_atividades = atividades[:4] if atividades else []

    return {
        "plan": plan,
        "projeto": projeto,
        "segmentos_count": len(segmentos),
        "estruturas_count": len(estruturas),
        "atividades_count": len(atividades),
        "investimento_total": investimento_total,
        "proximas_atividades": proximas_atividades,
        "issued_at": datetime.now().strftime("%d/%m/%Y às %H:%M"),
    }


@pev_bp.route("/dashboard")
def pev_dashboard():
    db = get_db()
    companies = db.get_companies()

    companies_with_plans = []
    for company in companies:
        plans = db.get_plans_by_company(company["id"])
        company_with_plans = company.copy()
        company_with_plans["plans"] = [
            {
                "id": plan["id"],
                "name": plan["name"],
                "plan_mode": plan.get("plan_mode", "evolucao"),  # Include plan_mode
            }
            for plan in plans
        ]
        companies_with_plans.append(company_with_plans)

    highlights = [
        {"title": "Planejamentos Ativos", "value": "3", "trend": "+1"},
        {"title": "Participantes", "value": "15", "trend": "+3"},
        {"title": "Projetos em Andamento", "value": "8", "trend": "+2"},
    ]

    timeline = [
        {
            "date": "2025-01-15",
            "event": "Inicio do planejamento estrategico",
            "status": "completed",
        },
        {
            "date": "2025-02-01",
            "event": "Entrevistas com participantes",
            "status": "in_progress",
        },
        {
            "date": "2025-03-15",
            "event": "Definicao de direcionadores",
            "status": "pending",
        },
        {
            "date": "2025-04-30",
            "event": "Aprovacao final do plano",
            "status": "pending",
        },
    ]

    return render_template(
        "plan_selector_compact.html",
        user_name="Fabiano Ferreira",
        companies=companies_with_plans,
        highlights=highlights,
        timeline=timeline,
    )


@pev_bp.route("/implantacao")
def pev_implantacao_overview():
    plan_id = _resolve_plan_id()
    db = get_db()
    payload = build_overview_payload(db, plan_id)
    plan = payload["plan"]

    plan_mode = (plan.get("plan_mode") or "evolucao").lower()
    if plan_mode != "implantacao":
        logger.info(
            f"?? Plano {plan_id} com plan_mode='{plan_mode}' redirecionado para interface clássica."
        )
        return redirect(url_for("plan_dashboard", plan_id=plan_id))

    project_info = load_alignment_project(db, plan_id)

    # Link direto para o projeto GRV criado para este planejamento
    if plan.get("company_id"):
        # Buscar projeto vinculado a este plan
        try:
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM company_projects WHERE plan_id = %s AND plan_type = 'PEV' ORDER BY created_at DESC LIMIT 1",
                (plan_id,),
            )
            project_row = cursor.fetchone()
            conn.close()

            if project_row:
                project_dict = dict(project_row)
                grv_project_id = project_dict.get("id")
                # Link direto para o projeto (Kanban)
                plan["project_link"] = url_for(
                    "grv.grv_project_manage",
                    company_id=plan.get("company_id"),
                    project_id=grv_project_id,
                )
                logger.info(
                    f"? Link direto para projeto GRV ID {grv_project_id} configurado"
                )
            else:
                # Se não tiver projeto, vai para lista de projetos
                plan["project_link"] = url_for(
                    "grv.grv_projects_projects", company_id=plan.get("company_id")
                )
                logger.info(
                    f"?? Nenhum projeto vinculado ao plan {plan_id}, link para lista de projetos"
                )
        except Exception as e:
            logger.info(f"?? Erro ao buscar projeto vinculado: {e}")
            plan["project_link"] = url_for(
                "grv.grv_projects_projects", company_id=plan.get("company_id")
            )
    else:
        plan["project_link"] = url_for("grv.grv_dashboard")
    return render_template(
        "plan_implantacao.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan=plan,
        macro_phases=payload["macro_phases"],
        checkpoints=payload["checkpoints"],
        dashboard=payload["dashboard"],
    )


@pev_bp.route("/implantacao/alinhamento/canvas-expectativas")
def implantacao_canvas_expectativas():
    plan_id = _resolve_plan_id()

    # Log para debug
    logger.info(f"DEBUG: Canvas Expectativas - plan_id resolvido: {plan_id}")
    logger.info(f"DEBUG: request.args: {request.args}")

    db = get_db()
    plan = build_plan_context(db, plan_id)

    # Log do plan
    logger.info(f"DEBUG: plan loaded: {plan.get('id') if plan else 'None'}")

    canvas_data = load_alignment_canvas(db, plan_id)
    return render_template(
        "implantacao/alinhamento_canvas_expectativas.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        plan=plan,  # Passar o plan completo também
        socios=canvas_data.get("socios", []),
        alinhamento=canvas_data.get("alinhamento", {}),
    )


@pev_bp.route("/implantacao/alinhamento/agenda-planejamento")
def implantacao_agenda_planejamento():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    agenda_data = load_alignment_agenda(db, plan_id)
    return render_template(
        "implantacao/alinhamento_agenda_planejamento.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        projeto=agenda_data.get("projeto", {}),
        atividades=agenda_data.get("atividades", []),
    )


@pev_bp.route("/implantacao/modelo/canvas-proposta-valor")
def implantacao_canvas_proposta_valor():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    segments = load_segments(db, plan_id)
    segmentos = build_value_canvas_segments(segments)
    return render_template(
        "implantacao/modelo_canvas_proposta_valor.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        segmentos=segmentos,
    )


@pev_bp.route("/implantacao/modelo/mapa-persona")
def implantacao_mapa_persona():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    segments = load_segments(db, plan_id)
    segmentos = build_persona_segments(segments)
    return render_template(
        "implantacao/modelo_mapa_persona.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        segmentos=segmentos,
    )


@pev_bp.route("/implantacao/modelo/matriz-diferenciais")
def implantacao_matriz_diferenciais():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    segments = load_segments(db, plan_id)
    segmentos = build_competitive_segments(segments)
    return render_template(
        "implantacao/modelo_matriz_diferenciais.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        segmentos=segmentos,
    )


@pev_bp.route("/implantacao/modelo/produtos")
def implantacao_produtos():
    """
    Página de cadastro e gerenciamento de produtos.
    """
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)

    return render_template(
        "implantacao/modelo_produtos.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        plan=plan,
    )


@pev_bp.route("/implantacao/modelo/modelagem-financeira")
def implantacao_modelagem_financeira():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    financeiro = load_financial_model(db, plan_id)
    estruturas = load_structures(db, plan_id)
    resumo_investimentos = calculate_investment_summary_by_block(estruturas)

    estrutura_investimentos_payload = aggregate_structure_investments(estruturas)
    investimentos_estruturas = serialize_structure_investment_summary(
        estrutura_investimentos_payload.get("categories", {})
    )

    products = products_service.fetch_products(plan_id)
    products_totals = products_service.calculate_totals(products)

    # DEBUG: Log dos totais de produtos (sem emojis para evitar encoding issues)
    logger.info("\n" + "=" * 80)
    logger.info(f"DEBUG - MODELAGEM FINANCEIRA - plan_id={plan_id}")
    logger.info("=" * 80)
    logger.info(f"Produtos encontrados: {len(products)}")
    logger.info(f"Products Totals: {products_totals}")
    logger.info("=" * 80 + "\n")

    resumo_totais = next(
        (
            item
            for item in resumo_investimentos
            if item.get("is_total")
            or (item.get("bloco") or "").strip().upper() == "TOTAL"
        ),
        {},
    )
    custos_fixos_mensal = float(resumo_totais.get("custos_fixos_mensal") or 0)
    despesas_fixas_mensal = float(resumo_totais.get("despesas_fixas_mensal") or 0)
    fixed_costs_summary = {
        "custos_fixos_mensal": custos_fixos_mensal,
        "despesas_fixas_mensal": despesas_fixas_mensal,
        "total_gastos_mensal": float(
            resumo_totais.get("total_gastos_mensal")
            or custos_fixos_mensal + despesas_fixas_mensal
        ),
    }

    # DEBUG: Log dos custos fixos
    logger.info(f"Fixed Costs Summary: {fixed_costs_summary}")
    logger.info(f"Resumo Totais Raw: {resumo_totais}")
    logger.info("=" * 80 + "\n")

    return render_template(
        "implantacao/modelo_modelagem_financeira.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        premissas=financeiro.get("premissas", []),
        investimento=financeiro.get("investimento", {}),
        fluxo_negocio=financeiro.get("fluxo_negocio", {}),
        fluxo_investidor=financeiro.get("fluxo_investidor", {}),
        resumo_investimentos=resumo_investimentos,
        investimentos_estruturas=investimentos_estruturas,
        products_totals=products_totals,
        fixed_costs_summary=fixed_costs_summary,
    )


@pev_bp.route("/implantacao/modelo/modefin")
def implantacao_modefin():
    """Nova página ModeFin - Modelagem Financeira Completa"""
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)

    # Carregar dados de produtos e margens
    products = products_service.fetch_products(plan_id)
    products_totals = products_service.calculate_totals(products)

    # Carregar estruturas e calcular custos fixos
    estruturas = load_structures(db, plan_id)
    resumo_investimentos = calculate_investment_summary_by_block(estruturas)

    resumo_totais = next(
        (
            item
            for item in resumo_investimentos
            if item.get("is_total")
            or (item.get("bloco") or "").strip().upper() == "TOTAL"
        ),
        {},
    )

    fixed_costs_summary = {
        "custos_fixos_mensal": float(resumo_totais.get("custos_fixos_mensal") or 0),
        "despesas_fixas_mensal": float(resumo_totais.get("despesas_fixas_mensal") or 0),
        "total_gastos_mensal": float(resumo_totais.get("total_gastos_mensal") or 0),
    }

    # Investimentos das estruturas (imobilizado)
    estrutura_investimentos_payload = aggregate_structure_investments(estruturas)
    investimentos_estruturas = serialize_structure_investment_summary(
        estrutura_investimentos_payload.get("categories", {})
    )

    # Capital de giro
    capital_giro_items = (
        db.list_plan_capital_giro(plan_id)
        if hasattr(db, "list_plan_capital_giro")
        else []
    )

    # Fontes de recursos
    funding_sources = db.list_plan_finance_sources(plan_id)

    # Distribuição de lucros e outras destinações
    profit_distribution_data = (
        db.get_profit_distribution(plan_id)
        if hasattr(db, "get_profit_distribution")
        else None
    )
    profit_distribution = [profit_distribution_data] if profit_distribution_data else []
    result_rules = db.list_plan_finance_result_rules(plan_id)

    # Resumo executivo
    executive_summary = (
        db.get_executive_summary(plan_id)
        if hasattr(db, "get_executive_summary")
        else None
    )

    # Modelo financeiro geral
    financeiro = load_financial_model(db, plan_id)

    # Parcelas das estruturas (para cálculo por data de vencimento)
    parcelas_estruturas = db.list_plan_structure_installments(plan_id)

    def _safe_float(value: Any) -> float:
        if value in (None, "", 0):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text_value = str(value).strip().replace(",", ".")
        try:
            return float(text_value)
        except ValueError:
            return 0.0

    fixed_cost_entries: List[Dict[str, Any]] = []
    for area in estruturas:
        for bloco in area.get("blocos", []):
            bloco_nome = bloco.get("nome") or ""
            for item in bloco.get("itens", []):
                acquisition_info = item.get("data_aquisicao")
                structure_id = item.get("id")
                for parcela in item.get("parcelas", []):
                    classification = _classify_structure_installment(
                        bloco_nome, parcela
                    )
                    class_norm = classification.get("classificacao_norm")
                    if class_norm not in {"custo fixo", "despesa fixa"}:
                        continue
                    repeticao_norm = classification.get("repeticao_norm")
                    if repeticao_norm not in {"mensal", "trimestral", "semestral"}:
                        continue
                    valor_decimal = _parse_decimal(parcela.get("valor"))
                    if valor_decimal is None:
                        continue
                    valor_float = float(valor_decimal)
                    if valor_float <= 0:
                        continue
                    if repeticao_norm == "trimestral":
                        valor_float /= 3.0
                    elif repeticao_norm == "semestral":
                        valor_float /= 6.0

                    start_tuple = None
                    if acquisition_info:
                        start_tuple = _month_tuple_from_value(acquisition_info)
                    if not start_tuple:
                        start_tuple = _month_tuple_from_value(
                            parcela.get("vencimento") or parcela.get("due_info")
                        )
                    if not start_tuple:
                        continue

                    start_month = _month_key_from_tuple(start_tuple)
                    fixed_cost_entries.append(
                        {
                            "structure_id": structure_id,
                            "type": "custo"
                            if class_norm == "custo fixo"
                            else "despesa",
                            "monthly_value": valor_float,
                            "start_month": start_month,
                            "installment_number": parcela.get("numero"),
                        }
                    )

    modefin_ramp: List[Dict[str, Any]] = []
    for product_data in products:
        summary = product_data.get("ramp_up_summary") or {}
        base_revenue = _safe_float(summary.get("base_revenue"))
        base_cost = _safe_float(summary.get("base_cost"))
        base_expense = _safe_float(summary.get("base_expense"))
        base_margin = _safe_float(summary.get("base_margin"))
        if base_margin == 0 and (base_revenue or base_cost or base_expense):
            base_margin = base_revenue - base_cost - base_expense

        ramp_entries = product_data.get("ramp_up_entries") or []
        normalized_entries: List[Dict[str, Any]] = []
        for entry in ramp_entries:
            month_value = entry.get("month") or entry.get("reference_month")
            month_tuple = _month_tuple_from_value(month_value) if month_value else None
            if not month_tuple:
                continue
            month_key = _month_key_from_tuple(month_tuple)
            percentage_raw = (
                entry.get("percentage") or entry.get("percent") or entry.get("value")
            )
            percentage = _safe_float(percentage_raw)
            if percentage < 0:
                percentage = 0.0
            if percentage > 100:
                percentage = 100.0
            normalized_entries.append({"month": month_key, "percentage": percentage})

        normalized_entries.sort(key=lambda item: item["month"])
        modefin_ramp.append(
            {
                "base_revenue": base_revenue,
                "base_cost": base_cost,
                "base_expense": base_expense,
                "base_margin": base_margin,
                "entries": normalized_entries,
                "ramp_up_entries": normalized_entries,  # Compatibilidade com frontend
                "ramp_up_summary": summary,  # Incluir summary completo
            }
        )

    # DEBUG
    logger.info("\n" + "=" * 80)
    logger.info(f"[ModeFin] plan_id={plan_id}")
    logger.info(f"Products Totals: {products_totals}")
    logger.info(f"Fixed Costs: {fixed_costs_summary}")
    logger.info(f"Investimentos Estruturas: {list(investimentos_estruturas.keys())}")
    logger.info(f"Capital Giro Items: {len(capital_giro_items)}")
    logger.info(f"Funding Sources: {len(funding_sources)}")
    logger.info(f"Parcelas Estruturas: {len(parcelas_estruturas)}")
    logger.info("=" * 80 + "\n")

    try:
        ui_attrs = get_screen_attr_map(MODEFIN_SCREEN_CODE)
        ui_catalog_payload = serialize_screen_catalog(MODEFIN_SCREEN_CODE)
    except Exception as exc:  # pylint: disable=broad-except
        logger.info(
            f"[ModeFin] Warning: failed to load UI catalog (code {MODEFIN_SCREEN_CODE}): {exc}"
        )
        ui_attrs = {}
        ui_catalog_payload = {}

    return render_template(
        "implantacao/modelo_modefin.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan_id=plan_id,
        plan=plan,
        products_totals=products_totals,
        fixed_costs_summary=fixed_costs_summary,
        investimentos_estruturas=investimentos_estruturas,
        capital_giro_items=capital_giro_items,
        funding_sources=funding_sources,
        profit_distribution=profit_distribution,
        result_rules=result_rules,
        executive_summary=executive_summary,
        financeiro=financeiro,
        parcelas_estruturas=parcelas_estruturas,
        fixed_cost_entries=fixed_cost_entries,
        modefin_ramp=modefin_ramp,
        ui_screen_code=MODEFIN_SCREEN_CODE,
        ui_attrs=ui_attrs,
        ui_catalog_payload=ui_catalog_payload,
    )


@pev_bp.route("/api/implantacao/<int:plan_id>/products", methods=["GET"])
def get_products(plan_id: int):
    """
    Lista produtos do planejamento e devolve os totais calculados.
    """
    try:
        products = products_service.fetch_products(plan_id)
        totals = products_service.calculate_totals(products)

        # DEBUG
        logger.info(f"\nAPI GET /products - plan_id={plan_id}")
        logger.info(f"   Produtos: {len(products)}")
        logger.info(f"   Totals: {totals}\n")

        return jsonify({"success": True, "products": products, "totals": totals}), 200
    except Exception as exc:
        logger.info(f"[products] Error fetching products for plan {plan_id}: {exc}")
        return jsonify({"success": False, "error": "Erro ao carregar produtos"}), 500


@pev_bp.route("/api/implantacao/<int:plan_id>/products/totals", methods=["GET"])
def get_products_totals(plan_id: int):
    """
    Calcula apenas os totalizados de produtos (faturamento, custos, etc).
    """
    try:
        products = products_service.fetch_products(plan_id)
        totals = products_service.calculate_totals(products)
        return jsonify({"success": True, "totals": totals}), 200
    except Exception as exc:
        logger.info(f"[products] Error calculating totals for plan {plan_id}: {exc}")
        return jsonify({"success": False, "error": "Erro ao calcular totalizados"}), 500


@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/products", methods=["POST"])
def create_product(plan_id: int):
    """Cria novo produto."""
    try:
        data = request.get_json() or {}
        product = products_service.create_product(plan_id, data)
        return jsonify({"success": True, "product": product}), 201
    except products_service.ProductValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.info(f"[products] Error creating product for plan {plan_id}: {exc}")
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": "Erro ao criar produto"}), 500


@pev_bp.route(
    "/api/implantacao/<int:plan_id>/products/<int:product_id>", methods=["GET"]
)
def get_product(plan_id: int, product_id: int):
    """Retorna um produto específico."""
    try:
        product = products_service.fetch_product(plan_id, product_id)
        return jsonify({"success": True, "product": product}), 200
    except products_service.ProductNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except Exception as exc:
        logger.info(
            f"[products] Error fetching product {product_id} for plan {plan_id}: {exc}"
        )
        return jsonify({"success": False, "error": "Erro ao buscar produto"}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/products/<int:product_id>", methods=["PUT"]
)
def update_product(plan_id: int, product_id: int):
    """Atualiza produto existente."""
    try:
        data = request.get_json() or {}
        product = products_service.update_product(plan_id, product_id, data)
        return jsonify({"success": True, "product": product}), 200
    except products_service.ProductNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except products_service.ProductValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.info(
            f"[products] Error updating product {product_id} for plan {plan_id}: {exc}"
        )
        import traceback

        traceback.print_exc()
        return jsonify({"success": False, "error": "Erro ao atualizar produto"}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/products/<int:product_id>", methods=["DELETE"]
)
def delete_product(plan_id: int, product_id: int):
    """Remove produto (soft delete)."""
    try:
        products_service.soft_delete_product(plan_id, product_id)
        return jsonify({"success": True}), 200
    except products_service.ProductNotFoundError as exc:
        return jsonify({"success": False, "error": str(exc)}), 404
    except Exception as exc:
        logger.info(
            f"[products] Error deleting product {product_id} for plan {plan_id}: {exc}"
        )
        return jsonify({"success": False, "error": "Erro ao deletar produto"}), 500


@pev_bp.route("/implantacao/executivo/playbook-comercial")
def implantacao_playbook_comercial():
    pilares = [
        {
            "nome": "Metas trimestrais",
            "descricao": "Crescimento gradual para garantir qualidade de entrega.",
            "detalhes": [
                "Trimestre 1: 120 clientes recorrentes (assinaturas e eventos)",
                "Trimestre 2: 220 clientes recorrentes",
                "Trimestre 3: 320 clientes recorrentes com foco em eventos corporativos",
                "Conversao target: 35% em degustacoes guiadas",
            ],
        },
        {
            "nome": "Processo comercial",
            "descricao": "Etapas padronizadas para garantir consistencia no relacionamento.",
            "detalhes": [
                "Prospecao consultiva (social selling, parcerias locais)",
                "Degustacao guiada com storytelling",
                "Workshop de co-criacao de experiencias",
                "Fechamento com pacotes personalizaveis e onboarding",
            ],
        },
        {
            "nome": "Ferramentas e rotinas",
            "descricao": "Sistemas e rituais para controlar pipeline e relacionamento.",
            "detalhes": [
                "CRM leve integrado ao WhatsApp Business",
                "Dashboard semanal com pipeline e metas",
                "Rituais de follow-up (48h pos degustacao)",
                "Scripts e playbooks de storytelling",
            ],
        },
    ]

    equipe = {
        "estrutura": [
            "1 lider comercial (estrategia e relacionamento B2B)",
            "2 consultores de experiencia (eventos, assinaturas, parcerias)",
            "1 analista de relacionamento (community e fidelizacao)",
        ],
        "capacidades": [
            "Storytelling e degustacao guiada",
            "Negociacao consultiva com clubes e empresas",
            "Gestao de pipeline e indicadores comerciales",
        ],
    }

    return render_template(
        "implantacao/execution_playbook_comercial.html",
        user_name="Fabiano Ferreira",
        pilares=pilares,
        equipe=equipe,
    )


@pev_bp.route("/implantacao/executivo/mapa-processos")
def implantacao_mapa_processos():
    processos = [
        {
            "nome": "Producao diaria",
            "objetivo": "Garantir produtos frescos com padrao artesanal.",
            "macro_etapas": [
                "Planejamento de insumos (D-2)",
                "Preparo e mise en place (D-1)",
                "Execucao de fornadas (D)",
                "Controle de qualidade e ajustes finais",
            ],
            "indicadores": [
                "Aderencia a ficha tecnica 98%",
                "Desperdicio maximo 3%",
                "Satisfacao do cliente (degustacoes) >= 90%",
            ],
        },
        {
            "nome": "Experiencia em loja",
            "objetivo": "Criar jornada memoravel em todas as visitas.",
            "macro_etapas": [
                "Acolhimento e entendimento do momento",
                "Apresentacao guiada dos produtos",
                "Oferta de experiencia complementar",
                "Registro de preferencia no CRM",
            ],
            "indicadores": [
                "Taxa de recomendacao 85%",
                "Ticket medio projetado R$ 65",
                "Clientes recorrentes (30 dias) >= 45%",
            ],
        },
        {
            "nome": "Eventos e catering",
            "objetivo": "Executar eventos premium mantendo padrao da marca.",
            "macro_etapas": [
                "Briefing consultivo",
                "Degustacao e definicao de cardapio",
                "Execucao com embaixador da marca",
                "Feedback e plano de recompra",
            ],
            "indicadores": [
                "Satisfacao do evento >= 92%",
                "Tempo maximo de resposta: 24h",
                "Recompra em ate 90 dias: 40%",
            ],
        },
    ]

    capacidade = {
        "linha_producao": "600 unidades por dia com equipe base; possibilidade de reforco em ate 30%.",
        "turnos": [
            "Madrugada (preparo, fornos)",
            "Manha (acabamento, montagem experiencias)",
            "Tarde (eventos e reposicao)",
        ],
        "planejamento_picos": [
            "Calendario de datas especiais",
            "Banco de talentos para reforcos pontuais",
            "Parcerias logisticas para eventos externos",
        ],
    }

    return render_template(
        "implantacao/execution_mapa_processos.html",
        user_name="Fabiano Ferreira",
        processos=processos,
        capacidade=capacidade,
    )


@pev_bp.route("/implantacao/executivo/modelo-financeiro-base")
def implantacao_modelo_financeiro_base():
    premissas = {
        "ticket_medio": "R$ 65 loja / R$ 220 assinatura / R$ 2.500 eventos",
        "mix_receita": [
            "Loja fisica: 45%",
            "Assinaturas premium: 30%",
            "Eventos corporativos: 20%",
            "Workshops e experiencias: 5%",
        ],
        "margem": {
            "bruta": "Projetada em 48% apos otimizar fornecedores",
            "contribuicao": "35% media com mix ideal de produtos",
        },
    }

    custos = {
        "fixos": [
            "Locacao ponto premium",
            "Folha equipe (operacao, comercial, suporte)",
            "Marketing e conteudo",
            "Tecnologia e licencas",
        ],
        "variaveis": [
            "Ingredientes premium",
            "Embalagens e brindes experienciais",
            "Comissao parcerias corporativas",
        ],
        "investimentos": [
            "Ambientacao e equipamentos",
            "Plataforma digital / CRM",
            "Fundo de contingencia (3 meses de operacao)",
        ],
    }

    indicadores = [
        {
            "nome": "Ponto de equilibrio",
            "valor": "Mes 9 com vendas projetadas",
            "observacao": "Monitorar mix para proteger margem",
        },
        {
            "nome": "Payback",
            "valor": "24 meses (cenario base)",
            "observacao": "Plano de aceleracao reduz para 20 meses",
        },
        {
            "nome": "CAC payback loja",
            "valor": "1,8 meses",
            "observacao": "Campanhas de relacao prolongam ciclo de vida",
        },
        {
            "nome": "LTV / CAC",
            "valor": "3,9",
            "observacao": "Meta de superar 4,5 apos trimestre 2",
        },
    ]

    return render_template(
        "implantacao/execution_modelo_financeiro_base.html",
        user_name="Fabiano Ferreira",
        premissas=premissas,
        custos=custos,
        indicadores=indicadores,
    )


@pev_bp.route("/implantacao/financeiro/plano-investimento")
def implantacao_plano_investimento():
    fases = [
        {
            "nome": "Fase 1 - Implantacao",
            "periodo": "Meses 0 a 3",
            "foco": "Estruturar ponto fisico, equipe base e operacao piloto.",
            "aporte": "R$ 320.000",
            "principais_itens": [
                "Reforma e ambientacao do ponto premium",
                "Equipamentos de producao e vitrine refrigerada",
                "Capital de giro para tres meses",
            ],
        },
        {
            "nome": "Fase 2 - Expansao de experiencias",
            "periodo": "Meses 4 a 9",
            "foco": "Ampliar portfolio de eventos e assinaturas.",
            "aporte": "R$ 120.000",
            "principais_itens": [
                "Montagem de laboratorio de experiencias",
                "Equipe dedicada a eventos corporativos",
                "Campanhas de marketing segmentado",
            ],
        },
        {
            "nome": "Fase 3 - Segunda unidade",
            "periodo": "Meses 12 a 18",
            "foco": "Replicar modelo em bairro estrategico.",
            "aporte": "R$ 280.000",
            "principais_itens": [
                "Estudo de viabilidade e negociacao do ponto",
                "Treinamento de equipe replicadora",
                "Almoxarifado compartilhado e logistica",
            ],
        },
    ]

    fontes = {
        "recursos_proprios": "R$ 220.000 - aporte inicial dos socios",
        "linha_credito": "R$ 200.000 - linha Sebrae com carencia de 12 meses",
        "investidores": "R$ 300.000 - rodada anjo direcionada a expansao",
        "incentivos": "R$ 20.000 - programas regionais para empreendedores",
    }

    return render_template(
        "implantacao/financeiro_plano_investimento.html",
        user_name="Fabiano Ferreira",
        fases=fases,
        fontes=fontes,
    )


@pev_bp.route("/implantacao/financeiro/fluxo-caixa")
def implantacao_fluxo_caixa():
    cenarios = [
        {
            "nome": "Base",
            "descricao": "Vendas previstas com maturacao gradual da base de clientes.",
            "acumulado": "Saldo positivo a partir do mes 8",
            "observacoes": [
                "Receita mensal media R$ 138 mil ao final do ano 1",
                "Margem de contribuicao media 35%",
                "Reserva de emergencia equivalente a dois meses de custos",
            ],
        },
        {
            "nome": "Otimista",
            "descricao": "Conversao acelerada em eventos corporativos e assinaturas.",
            "acumulado": "Ponto de equilibrio antecipado para o mes 6",
            "observacoes": [
                "Incremento de 15% nas vendas de eventos",
                "Aumento do ticket medio para R$ 72",
                "Possibilidade de antecipar abertura da segunda unidade",
            ],
        },
        {
            "nome": "Conservador",
            "descricao": "Adocao gradual com maior dependencia da loja fisica.",
            "acumulado": "Saldo positivo somente no mes 11",
            "observacoes": [
                "Renegociacao de fornecedores para reduzir custos variaveis",
                "Campanhas extras para aquisicao de assinantes",
                "Uso do fundo de contingencia nos tres primeiros meses",
            ],
        },
    ]

    gatilhos = [
        "Revisar precos e margem se fluxo projetado ficar 10% abaixo do estimado por dois meses.",
        "Acionar plano de reducao de custos variaveis se margem de contribuicao cair abaixo de 30%.",
        "Aumentar investimento em marketing se relacao LTV/CAC cair abaixo de 3,5.",
    ]

    return render_template(
        "implantacao/financeiro_fluxo_caixa.html",
        user_name="Fabiano Ferreira",
        cenarios=cenarios,
        gatilhos=gatilhos,
    )


@pev_bp.route("/implantacao/financeiro/matriz-indicadores")
def implantacao_matriz_indicadores_financeiros():
    indicadores = [
        {
            "categoria": "Receita",
            "itens": [
                {
                    "nome": "Ticket medio loja",
                    "meta": "R$ 65",
                    "periodicidade": "Mensal",
                    "responsavel": "Lider comercial",
                },
                {
                    "nome": "Assinaturas ativas",
                    "meta": "200 ate mes 6",
                    "periodicidade": "Semanal",
                    "responsavel": "Analista de relacionamento",
                },
                {
                    "nome": "Eventos corporativos",
                    "meta": "8 por mes a partir do mes 5",
                    "periodicidade": "Mensal",
                    "responsavel": "Consultor de experiencias",
                },
            ],
        },
        {
            "categoria": "Margens",
            "itens": [
                {
                    "nome": "Margem bruta",
                    "meta": "48%",
                    "periodicidade": "Mensal",
                    "responsavel": "Controller",
                },
                {
                    "nome": "Desperdicio producao",
                    "meta": "<= 3%",
                    "periodicidade": "Semanal",
                    "responsavel": "Chef de producao",
                },
                {
                    "nome": "Custo por experiencia",
                    "meta": "<= R$ 18",
                    "periodicidade": "Evento",
                    "responsavel": "Coordenador de eventos",
                },
            ],
        },
        {
            "categoria": "Caixa",
            "itens": [
                {
                    "nome": "Dias de capital de giro",
                    "meta": ">= 45 dias",
                    "periodicidade": "Mensal",
                    "responsavel": "Ana Paula",
                },
                {
                    "nome": "LTV / CAC",
                    "meta": ">= 4,5",
                    "periodicidade": "Trimestral",
                    "responsavel": "Fabiano",
                },
                {
                    "nome": "Inadimplencia assinaturas",
                    "meta": "<= 2%",
                    "periodicidade": "Mensal",
                    "responsavel": "Analista financeiro",
                },
            ],
        },
    ]

    rituais = [
        "Painel financeiro atualizado semanalmente em ferramenta compartilhada.",
        "Reuniao financeira semanal para revisar indicadores criticos.",
        "Comite mensal com socios para validar ajustes estrategicos.",
    ]

    return render_template(
        "implantacao/financeiro_matriz_indicadores.html",
        user_name="Fabiano Ferreira",
        indicadores=indicadores,
        rituais=rituais,
    )


@pev_bp.route("/implantacao/relatorio/01-capa-resumo")
def implantacao_relatorio_capa_resumo():
    plan_id = _resolve_plan_id()
    db = get_db()
    payload = _prepare_report_one_payload(db, plan_id)
    return render_template(
        "implantacao/relatorios/relatorio_1_capa_resumo.html",
        **payload,
    )


@pev_bp.route("/implantacao/entrega/relatorio-final")
def implantacao_relatorio_final():
    try:
        plan_id = _resolve_plan_id()
        db = get_db()
        plan = build_plan_context(db, plan_id)
        canvas_data = load_alignment_canvas(db, plan_id)
        agenda_project = load_alignment_project(db, plan_id)
        agenda_data = load_alignment_agenda(db, plan_id)
        projeto_atividades = agenda_data.get("atividades", [])

        logger.info(f"\n[DEBUG] Atividades carregadas: {len(projeto_atividades)}")
        if projeto_atividades:
            logger.info(f"[DEBUG] Primeira atividade: {projeto_atividades[0]}")
        principles = db.list_alignment_principles(plan_id)
        segments = load_segments(db, plan_id)
        competitive_segments = build_competitive_segments(segments)
        estruturas = load_structures(db, plan_id)
        financeiro = load_financial_model(db, plan_id)

        # ===== DADOS DA MODEFIN =====
        # Produtos e margens
        products = products_service.fetch_products(plan_id)
        products_totals = products_service.calculate_totals(products)

        # Investimentos das estruturas
        resumo_investimentos = calculate_investment_summary_by_block(estruturas)
        estrutura_investimentos_payload = aggregate_structure_investments(estruturas)
        investimentos_estruturas = serialize_structure_investment_summary(
            estrutura_investimentos_payload.get("categories", {})
        )

        # Extrair resumo de custos fixos do resumo_investimentos
        resumo_totais = next(
            (
                item
                for item in resumo_investimentos
                if item.get("is_total")
                or (item.get("bloco") or "").strip().upper() == "TOTAL"
            ),
            {},
        )

        fixed_costs_dict = {
            "custos_fixos_mensal": float(resumo_totais.get("custos_fixos_mensal") or 0),
            "despesas_fixas_mensal": float(
                resumo_totais.get("despesas_fixas_mensal") or 0
            ),
            "total_gastos_mensal": float(resumo_totais.get("total_gastos_mensal") or 0),
        }

        # Capital de giro
        try:
            capital_giro_items = (
                db.list_plan_capital_giro(plan_id)
                if hasattr(db, "list_plan_capital_giro")
                else []
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar capital de giro: {e}")
            capital_giro_items = []

        # Fontes de recursos
        try:
            funding_sources = (
                db.list_plan_finance_sources(plan_id)
                if hasattr(db, "list_plan_finance_sources")
                else []
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar fontes de recursos: {e}")
            funding_sources = []

        # Distribuição de lucros e destinações
        try:
            profit_distribution_data = (
                db.get_profit_distribution(plan_id)
                if hasattr(db, "get_profit_distribution")
                else None
            )
            profit_distribution = (
                [profit_distribution_data] if profit_distribution_data else []
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar distribuição de lucros: {e}")
            profit_distribution = []

        try:
            result_rules = (
                db.list_plan_finance_result_rules(plan_id)
                if hasattr(db, "list_plan_finance_result_rules")
                else []
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar regras de resultado: {e}")
            result_rules = []

        # Resumo executivo
        try:
            executive_summary = (
                db.get_executive_summary(plan_id)
                if hasattr(db, "get_executive_summary")
                else None
            )
        except Exception as e:
            logger.warning(f"Erro ao carregar resumo executivo: {e}")
            executive_summary = None

        # Preparar métricas de análise a partir dos fluxos reais da ModeFin
        analysis_metrics = {
            "total_investimentos": 0.0,
            "resultado_operacional": 0.0,
            "periodo_meses": 60,
            "custo_oportunidade_percent": 12.0,
            "payback_meses": None,
            "payback_inicio": None,
            "payback_fim": None,
            "roi_percent": None,
            "tir_percent": None,
            "vpl": None,
        }

        # Construir fixed_cost_entries (custos fixos por data)
        def _safe_float_local(value):
            if value in (None, "", 0):
                return 0.0
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value).strip().replace(",", "."))
            except (ValueError, TypeError):
                return 0.0

        fixed_cost_entries = []
        for area in estruturas:
            for bloco in area.get("blocos", []):
                bloco_nome = bloco.get("nome") or ""
                for item in bloco.get("itens", []):
                    acquisition_info = item.get("data_aquisicao")
                    structure_id = item.get("id")
                    for parcela in item.get("parcelas", []):
                        classification = _classify_structure_installment(
                            bloco_nome, parcela
                        )
                        class_norm = classification.get("classificacao_norm")
                        if class_norm not in {"custo fixo", "despesa fixa"}:
                            continue
                        repeticao_norm = classification.get("repeticao_norm")
                        if repeticao_norm not in {"mensal", "trimestral", "semestral"}:
                            continue
                        valor_decimal = _parse_decimal(parcela.get("valor"))
                        if valor_decimal is None:
                            continue
                        valor_float = float(valor_decimal)
                        if valor_float <= 0:
                            continue
                        if repeticao_norm == "trimestral":
                            valor_float /= 3.0
                        elif repeticao_norm == "semestral":
                            valor_float /= 6.0

                        start_tuple = None
                        if acquisition_info:
                            start_tuple = _month_tuple_from_value(acquisition_info)
                        if not start_tuple:
                            start_tuple = _month_tuple_from_value(
                                parcela.get("vencimento") or parcela.get("due_info")
                            )
                        if not start_tuple:
                            continue

                        start_month = _month_key_from_tuple(start_tuple)
                        fixed_cost_entries.append(
                            {
                                "structure_id": structure_id,
                                "type": "custo"
                                if class_norm == "custo fixo"
                                else "despesa",
                                "monthly_value": valor_float,
                                "start_month": start_month,
                                "installment_number": parcela.get("numero"),
                            }
                        )

        # Construir Fluxo de Investimento usando função específica
        try:
            investment_flow = build_modefin_investment_flow(
                capital_giro_items, investimentos_estruturas, funding_sources
            )
        except Exception as e:
            logger.warning(f"Erro ao construir fluxo de investimento: {e}")
            investment_flow = {"rows": [], "totals": {}}

        # Construir Fluxo de Caixa do Negócio com dados corretos da ModeFin
        try:
            business_flow = build_modefin_business_flow(
                products,
                products_totals,
                fixed_cost_entries,
                profit_distribution,
                result_rules,
                num_months=60,
            )
        except Exception as e:
            logger.warning(f"Erro ao construir fluxo de caixa do negócio: {e}")
            business_flow = {"rows_full": [], "rows": [], "totals": {}}

        # Construir Fluxo de Caixa do Investidor (combina investment_flow + business_flow)
        try:
            investor_flow = build_modefin_investor_flow(
                investment_flow, business_flow, profit_distribution
            )
        except Exception as e:
            logger.warning(f"Erro ao construir fluxo de caixa do investidor: {e}")
            investor_flow = {"rows": [], "totals": {}}

        # Calcular métricas de análise a partir dos fluxos reais
        # Investimento total
        analysis_metrics["total_investimentos"] = investment_flow.get("totals", {}).get(
            "investimentos", 0.0
        )

        # Resultado operacional (média dos primeiros 12 meses após ramp-up completo)
        business_rows_full = business_flow.get("rows_full", [])
        if business_rows_full and len(business_rows_full) >= 12:
            # Pegar últimos meses com ramp-up em 100%
            resultados_estabilizados = [
                r.get("resultado_operacional", 0) for r in business_rows_full[-12:]
            ]
            analysis_metrics["resultado_operacional"] = sum(
                resultados_estabilizados
            ) / len(resultados_estabilizados)

        # Calcular métricas financeiras a partir do investor_flow
        # Precisamos dos dados COMPLETOS (não condensados) para cálculos precisos

        # Reconstruir investor_flow completo para cálculos
        # Vou processar business_rows_full diretamente
        total_aportes = 0.0
        total_distribuicoes = 0.0
        fluxos_mensais = []  # Para VPL e TIR

        payback_meses = None
        payback_inicio = None
        payback_fim = None
        primeiro_aporte_idx = None
        saldo_acum = 0.0

        # Criar mapa de aportes por período
        aportes_map = {}
        for row in investment_flow.get("rows", []):
            periodo = row.get("period_label", "")
            fontes = row.get("fontes", 0.0)
            if periodo and fontes > 0:
                aportes_map[periodo] = fontes

        # Processar cada mês
        if business_rows_full:
            for idx, bus_row in enumerate(business_rows_full):
                periodo = bus_row.get("periodo", "")
                aporte = aportes_map.get(periodo, 0.0)
                distribuicao = bus_row.get("distribuicao", 0.0)

                # Fluxo do investidor: distribuição - aporte
                fluxo = distribuicao - aporte
                fluxos_mensais.append(fluxo)

                # Acumular totais
                total_aportes += aporte
                total_distribuicoes += distribuicao

                # Calcular saldo acumulado
                saldo_acum += fluxo

                # Detectar pay-back
                if aporte > 0 and primeiro_aporte_idx is None:
                    primeiro_aporte_idx = idx
                    payback_inicio = periodo

                if (
                    primeiro_aporte_idx is not None
                    and payback_fim is None
                    and saldo_acum >= 0
                ):
                    payback_meses = (idx - primeiro_aporte_idx) + 1
                    payback_fim = periodo

        # Calcular ROI
        roi_percent = None
        if total_aportes > 0:
            roi_percent = (total_distribuicoes / total_aportes) * 100

        # Calcular VPL
        vpl = 0.0
        taxa_anual = 12.0  # 12% a.a.
        taxa_mensal = ((1 + (taxa_anual / 100)) ** (1 / 12)) - 1

        for mes, fluxo in enumerate(fluxos_mensais, start=1):
            valor_presente = fluxo / ((1 + taxa_mensal) ** mes)
            vpl += valor_presente

        # Calcular TIR usando Newton-Raphson
        tir_percent = None
        if total_aportes > 0 and total_distribuicoes > 0:
            tir_mensal = _calcular_tir_newton(fluxos_mensais)
            if tir_mensal is not None:
                # Converter para taxa anual
                tir_percent = ((1 + tir_mensal) ** 12 - 1) * 100

        # Atualizar analysis_metrics
        analysis_metrics["payback_meses"] = payback_meses
        analysis_metrics["payback_inicio"] = payback_inicio
        analysis_metrics["payback_fim"] = payback_fim
        analysis_metrics["roi_percent"] = roi_percent
        analysis_metrics["tir_percent"] = tir_percent
        analysis_metrics["vpl"] = vpl

        logger.info(f"\n[DEBUG] Métricas Calculadas:")
        logger.info(f"  Total Aportes: {total_aportes:,.2f}")
        logger.info(f"  Total Distribuições: {total_distribuicoes:,.2f}")
        logger.info(
            f"  Pay-back: {payback_meses} meses ({payback_inicio} a {payback_fim})"
        )
        logger.info(f"  ROI: {roi_percent:.2f}%" if roi_percent else "  ROI: None")
        logger.info(f"  TIR: {tir_percent:.2f}% a.a." if tir_percent else "  TIR: None")
        logger.info(f"  VPL: {vpl:,.2f}")

        # ===== FIM DADOS MODEFIN =====

        report_payload = build_final_report_payload(
            plan,
            canvas_data,
            agenda_project,
            principles,
            competitive_segments,
            summarize_structures_for_report(estruturas),
            financeiro,
        )
        # Adicionar investment_flow ao financeiro para o template
        financeiro_completo = report_payload.get("financeiro", {})
        if investment_flow:
            financeiro_completo["investimento"] = investment_flow

        return render_template(
            "implantacao/entrega_relatorio_final.html",
            user_name=plan.get("consultant", "Consultor responsavel"),
            plan=report_payload.get("plan"),
            alinhamento=report_payload.get("alinhamento"),
            segmentos=report_payload.get("segmentos"),
            estruturas=report_payload.get("estruturas"),
            financeiro=financeiro_completo,
            projeto=agenda_project,
            projeto_atividades=projeto_atividades,
            issued_at=report_payload.get("issued_at"),
            # Dados da ModeFin
            modefin_products=products,
            modefin_products_totals=products_totals,
            modefin_fixed_costs=fixed_costs_dict,
            modefin_investimentos_resumo=resumo_investimentos,
            modefin_capital_giro=capital_giro_items,
            modefin_funding_sources=funding_sources,
            modefin_profit_distribution=profit_distribution,
            modefin_result_rules=result_rules,
            modefin_executive_summary=executive_summary,
            modefin_investment_flow=investment_flow,
            modefin_business_flow=business_flow,
            modefin_investor_flow=investor_flow,
            investment_flow=investment_flow,
            analysis_metrics=analysis_metrics,
        )
    except Exception as e:
        plan_id_str = str(plan_id) if "plan_id" in locals() else "unknown"
        logger.error(
            f"[ERROR] Erro ao gerar relatório final para plan_id={plan_id_str}: {e}",
            exc_info=True,
        )
        import traceback

        traceback.print_exc()
        from flask import abort

        abort(500, description=f"Erro ao gerar relatório final: {str(e)}")


# Rotas antigas removidas - Serão substituídas por 6 relatórios modulares


@pev_bp.route("/implantacao/entrega/projeto-executivo")
def implantacao_projeto_executivo():
    cronograma = [
        {
            "marco": "Kick-off implantacao",
            "periodo": "Semanas 1-2",
            "entregas": ["Planejamento detalhado", "Matriz RACI validada"],
        },
        {
            "marco": "Obra e ambientacao",
            "periodo": "Semanas 3-8",
            "entregas": ["Ponto pronto para operacao", "Testes de infraestrutura"],
        },
        {
            "marco": "Operacao piloto",
            "periodo": "Semanas 9-12",
            "entregas": ["Processos validados", "Feedbacks estruturados"],
        },
        {
            "marco": "Lancamento oficial",
            "periodo": "Semana 13",
            "entregas": ["Evento de lancamento", "Campanha integrada"],
        },
        {
            "marco": "Expansao de experiencias",
            "periodo": "Semanas 14-20",
            "entregas": ["Workshops mensais", "Cliente corporativo ancora"],
        },
    ]

    governance = [
        "PMO leve liderado pelo consultor da implantacao.",
        "Uso de painel Kanban com status das entregas.",
        "Rito semanal com socios para priorizacao e destravamento.",
    ]

    riscos = [
        {
            "risco": "Atraso em fornecedores chaves",
            "mitigacao": "Contratos com backup e estoque minimo estrategico.",
        },
        {
            "risco": "Margem abaixo do planejado nos primeiros meses",
            "mitigacao": "Ajustes rapidos no mix e precificacao dinamica.",
        },
        {
            "risco": "Sobrecarga da equipe piloto",
            "mitigacao": "Banco de horas e profissionais reserva treinados.",
        },
    ]

    return render_template(
        "implantacao/entrega_projeto_executivo.html",
        user_name="Fabiano Ferreira",
        cronograma=cronograma,
        governance=governance,
        riscos=riscos,
    )


@pev_bp.route("/implantacao/entrega/painel-governanca")
def implantacao_painel_governanca():
    indicadores = [
        {
            "categoria": "Cadencia",
            "itens": [
                "Reuniao executiva semanal",
                "Checkpoint operacional semanal",
                "Comite financeiro mensal",
            ],
        },
        {
            "categoria": "Decisoes",
            "itens": [
                "Registro de decisoes em ata",
                "Follow-up em 48h",
                "Atualizacao semanal do RACI",
            ],
        },
        {
            "categoria": "Clima e desempenho",
            "itens": [
                "Pulse check com equipe",
                "Reconhecimento de boas praticas",
                "Plano de apoio em picos",
            ],
        },
    ]

    painels = [
        {
            "nome": "Dashboard de implantacao",
            "descricao": "Visao geral de macro fases, status e responsaveis.",
            "ferramenta": "Notion + Sheets",
        },
        {
            "nome": "Painel financeiro",
            "descricao": "Fluxo de caixa, indicadores e alertas automaticos.",
            "ferramenta": "Looker Studio",
        },
        {
            "nome": "Painel de experiencia",
            "descricao": "NPS, feedbacks e melhorias em andamento.",
            "ferramenta": "Notion + Forms",
        },
    ]

    return render_template(
        "implantacao/entrega_painel_governanca.html",
        user_name="Fabiano Ferreira",
        indicadores=indicadores,
        painels=painels,
    )


@pev_bp.route("/implantacao/executivo/estruturas")
def implantacao_estruturas():
    plan_id = _resolve_plan_id()
    db = get_db()
    plan = build_plan_context(db, plan_id)
    estruturas = load_structures(db, plan_id)
    return render_template(
        "implantacao/execution_estruturas.html",
        user_name=plan.get("consultant", "Consultor responsavel"),
        plan=plan,
        estruturas=estruturas,
    )


# ========== APIs para Canvas de Expectativas ==========


@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/alignment/members", methods=["POST"])
def add_alignment_member(plan_id: int):
    """Add new alignment member (socio)"""
    try:
        data = request.get_json() or {}

        # Validate required fields
        if not data.get("name"):
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400

        from config_database import get_db

        db = get_db()
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO plan_alignment_members (plan_id, name, role, motivation, commitment, risk)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """,
            (
                plan_id,
                data.get("name"),
                data.get("role"),
                data.get("motivation"),
                data.get("commitment"),
                data.get("risk"),
            ),
        )

        member_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return jsonify({"success": True, "id": member_id}), 201

    except Exception as e:
        logger.info(f"Error adding alignment member: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>", methods=["PUT"]
)
def update_alignment_member(plan_id: int, member_id: int):
    """Update alignment member"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plan_alignment_members
            SET name = %s, role = %s, motivation = %s, commitment = %s, risk = %s
            WHERE id = %s AND plan_id = %s
        """,
            (
                data.get("name"),
                data.get("role"),
                data.get("motivation"),
                data.get("commitment"),
                data.get("risk"),
                member_id,
                plan_id,
            ),
        )

        conn.commit()
        conn.close()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.info(f"Error updating alignment member: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/alignment/members/<int:member_id>",
    methods=["DELETE"],
)
def delete_alignment_member(plan_id: int, member_id: int):
    """Delete alignment member"""
    try:
        from config_database import get_db

        db = get_db()
        conn = db._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM plan_alignment_members WHERE id = %s AND plan_id = %s",
            (member_id, plan_id),
        )

        conn.commit()
        conn.close()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.info(f"Error deleting alignment member: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/alignment/overview", methods=["POST", "PUT"]
)
def save_alignment_overview(plan_id: int):
    """Save or update alignment overview"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()
        conn = db._get_connection()
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute(
            "SELECT plan_id FROM plan_alignment_overview WHERE plan_id = %s", (plan_id,)
        )
        exists = cursor.fetchone()

        criterios_json = json.dumps(data.get("criterios_decisao", []))

        if exists:
            # Update
            cursor.execute(
                """
                UPDATE plan_alignment_overview
                SET shared_vision = %s, financial_goals = %s, decision_criteria = %s, notes = %s, updated_at = CURRENT_TIMESTAMP
                WHERE plan_id = %s
            """,
                (
                    data.get("visao_compartilhada"),
                    data.get("metas_financeiras"),
                    criterios_json,
                    data.get("notas"),
                    plan_id,
                ),
            )
        else:
            # Insert
            cursor.execute(
                """
                INSERT INTO plan_alignment_overview (plan_id, shared_vision, financial_goals, decision_criteria, notes)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (
                    plan_id,
                    data.get("visao_compartilhada"),
                    data.get("metas_financeiras"),
                    criterios_json,
                    data.get("notas"),
                ),
            )

        conn.commit()
        conn.close()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.info(f"Error saving alignment overview: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ========== APIs para Modelo & Mercado (Segmentos) ==========


@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/segments", methods=["POST"])
def create_segment(plan_id: int):
    """Create new segment"""
    try:
        data = request.get_json() or {}

        logger.info(f"=== CREATE SEGMENT DEBUG ===")
        logger.info(f"plan_id: {plan_id}")
        logger.info(f"data recebido: {data}")

        # Validate required fields
        if not data.get("name"):
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400

        from config_database import get_db

        db = get_db()

        # Preparar dados para salvar
        segment_data = {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
            "audiences": data.get("audiences", []),
            "differentials": data.get("differentials", []),
            "evidences": data.get("evidences", []),
            "personas": [],
            "competitors_matrix": [],
            "strategy": data.get("strategy", {}),
        }

        logger.info(f"Dados preparados: {segment_data}")

        segment_id = db.create_plan_segment(plan_id, segment_data)

        logger.info(f"Segment ID criado: {segment_id}")

        if segment_id:
            return jsonify({"success": True, "id": segment_id}), 201
        else:
            return (
                jsonify({"success": False, "error": "Erro ao criar segmento no banco"}),
                500,
            )

    except Exception as e:
        import traceback

        logger.info(f"Error creating segment: {e}")
        logger.info(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"Erro no servidor: {str(e)}"}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/segments/<int:segment_id>", methods=["PUT"]
)
def update_segment(plan_id: int, segment_id: int):
    """Update segment"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_segment(segment_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar segmento"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating segment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/segments/<int:segment_id>", methods=["DELETE"]
)
def delete_segment(plan_id: int, segment_id: int):
    """Delete segment"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_segment(segment_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Erro ao deletar segmento"}), 500

    except Exception as e:
        logger.info(f"Error deleting segment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ========== APIs para Estruturas de Execução ==========


@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/<int:structure_id>", methods=["GET"]
)
def get_structure(plan_id: int, structure_id: int):
    """Get single structure item with installments"""
    try:
        from config_database import get_db

        db = get_db()

        # Buscar estrutura
        structures = db.list_plan_structures(plan_id)
        structure = next((s for s in structures if s.get("id") == structure_id), None)

        if not structure:
            return jsonify({"success": False, "error": "Estrutura não encontrada"}), 404

        # Buscar parcelas
        all_installments = db.list_plan_structure_installments(plan_id)
        installments = [
            inst
            for inst in all_installments
            if inst.get("structure_id") == structure_id
        ]

        structure["installments"] = installments

        return jsonify({"success": True, "data": structure}), 200

    except Exception as e:
        logger.info(f"Error getting structure: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/structures", methods=["POST"])
def create_structure(plan_id: int):
    """Create new structure item"""
    try:
        data = request.get_json() or {}

        logger.info(f"\n{'='*60}")
        logger.info(f"?? CREATE STRUCTURE - plan_id={plan_id}")
        logger.info(f"?? Data received: {data}")
        logger.info(f"{'='*60}\n")

        # Validate required fields
        if not data.get("area"):
            return jsonify({"success": False, "error": "Área é obrigatória"}), 400
        if not data.get("block"):
            return jsonify({"success": False, "error": "Bloco é obrigatório"}), 400
        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        logger.info(f"? Validação OK, criando estrutura...")

        # Criar estrutura
        structure_id = db.create_plan_structure(plan_id, data)

        logger.info(f"?? Structure ID retornado: {structure_id}")

        if structure_id:
            # Criar parcelas se fornecidas
            installments = data.get("installments", [])
            logger.info(f"?? Parcelas a criar: {len(installments)}")

            if installments:
                for idx, inst in enumerate(installments):
                    logger.info(
                        f"  Criando parcela {idx+1}/{len(installments)}: {inst}"
                    )
                    inst_id = db.create_plan_structure_installment(structure_id, inst)
                    logger.info(f"  ? Parcela criada com ID: {inst_id}")

            logger.info(f"? Estrutura criada com sucesso! ID={structure_id}\n")
            return jsonify({"success": True, "id": structure_id}), 201
        else:
            logger.info(f"? ERRO: create_plan_structure retornou 0 ou None\n")
            return (
                jsonify(
                    {"success": False, "error": "Erro ao criar estrutura no banco"}
                ),
                500,
            )

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.info(f"\n{'='*60}")
        logger.info(f"? EXCEPTION ao criar estrutura:")
        logger.info(f"Error: {e}")
        logger.info(f"Traceback:\n{error_trace}")
        logger.info(f"{'='*60}\n")
        return jsonify({"success": False, "error": f"Erro no servidor: {str(e)}"}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/<int:structure_id>", methods=["PUT"]
)
def update_structure(plan_id: int, structure_id: int):
    """Update structure item"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        # Atualizar estrutura
        success = db.update_plan_structure(structure_id, plan_id, data)

        if success:
            # Atualizar parcelas se fornecidas
            installments = data.get("installments")
            if installments is not None:  # Pode ser lista vazia
                # Deletar parcelas antigas
                db.delete_plan_structure_installments(structure_id)
                # Criar novas parcelas
                for inst in installments:
                    db.create_plan_structure_installment(structure_id, inst)

            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar estrutura"}),
                500,
            )

    except Exception as e:
        import traceback

        logger.info(f"Error updating structure: {e}")
        logger.info(f"Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/<int:structure_id>", methods=["DELETE"]
)
def delete_structure(plan_id: int, structure_id: int):
    """Delete structure item"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_structure(structure_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao deletar estrutura"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error deleting structure: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# APIs de Capacidade de Faturamento
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/structures/capacities", methods=["POST"])
def create_capacity(plan_id: int):
    """Create revenue capacity entry for structure area"""
    try:
        data = request.get_json() or {}

        # Validação
        if not data.get("area"):
            return jsonify({"success": False, "error": "Área é obrigatória"}), 400

        if not data.get("revenue_capacity"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Capacidade de faturamento é obrigatória",
                    }
                ),
                400,
            )

        from config_database import get_db

        db = get_db()

        capacity_id = db.create_plan_structure_capacity(plan_id, data)

        if capacity_id:
            return jsonify({"success": True, "id": capacity_id}), 201
        else:
            return jsonify({"success": False, "error": "Erro ao criar capacidade"}), 500

    except Exception as e:
        logger.info(f"Error creating capacity: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>",
    methods=["PUT"],
)
def update_capacity(plan_id: int, capacity_id: int):
    """Update revenue capacity entry for structure area"""
    try:
        data = request.get_json() or {}

        # Validação
        if not data.get("area"):
            return jsonify({"success": False, "error": "Área é obrigatória"}), 400

        if not data.get("revenue_capacity"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Capacidade de faturamento é obrigatória",
                    }
                ),
                400,
            )

        from config_database import get_db

        db = get_db()

        success = db.update_plan_structure_capacity(capacity_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar capacidade"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating capacity: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/capacities/<int:capacity_id>",
    methods=["DELETE"],
)
def delete_capacity(plan_id: int, capacity_id: int):
    """Delete revenue capacity entry for structure area"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_structure_capacity(capacity_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao deletar capacidade"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error deleting capacity: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments",
    methods=["DELETE"],
)
def delete_structure_installments(plan_id: int, structure_id: int):
    """Delete all installments for a structure"""
    try:
        divider = "=" * 60
        logger.info(f"\n{divider}")
        logger.info(
            f"[installments] DELETE - plan_id={plan_id}, structure_id={structure_id}"
        )
        logger.info(f"{divider}\n")

        from config_database import get_db

        db = get_db()

        # Verificar se estrutura existe
        structures = db.list_plan_structures(plan_id)
        structure = next((s for s in structures if s.get("id") == structure_id), None)

        if not structure:
            logger.info(
                f"[installments] Estrutura {structure_id} nao encontrada para plan_id {plan_id}"
            )
            return jsonify({"success": False, "error": "Estrutura nao encontrada"}), 404

        logger.info("[installments] Estrutura encontrada, deletando parcelas...")

        # Deletar parcelas
        db.delete_plan_structure_installments(structure_id)

        logger.info("[installments] Parcelas deletadas com sucesso!\n")
        return jsonify({"success": True}), 200

    except Exception as e:
        divider = "=" * 60
        logger.info(f"\n{divider}")
        logger.info("[installments] EXCEPTION ao deletar parcelas:")
        logger.info(f"Error: {e}")
        import traceback

        logger.info(f"Traceback:\n{traceback.format_exc()}")
        logger.info(f"{divider}\n")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/<int:structure_id>/installments",
    methods=["POST"],
)
def create_structure_installment(plan_id: int, structure_id: int):
    """Create a new installment for a structure"""
    try:
        data = request.get_json() or {}

        divider = "=" * 60
        logger.info(f"\n{divider}")
        logger.info(
            f"[installments] CREATE - plan_id={plan_id}, structure_id={structure_id}"
        )
        logger.info(f"[installments] Data received: {data}")
        logger.info(
            "[installments] Data types: "
            f"installment_number={type(data.get('installment_number'))}, "
            f"amount={type(data.get('amount'))}"
        )
        logger.info(f"{divider}\n")

        from config_database import get_db

        db = get_db()

        # Verificar se estrutura existe
        structures = db.list_plan_structures(plan_id)
        structure = next((s for s in structures if s.get("id") == structure_id), None)

        if not structure:
            logger.info(
                f"[installments] Estrutura {structure_id} nao encontrada para plan_id {plan_id}"
            )
            return jsonify({"success": False, "error": "Estrutura nao encontrada"}), 404

        logger.info(
            f"[installments] Estrutura encontrada: {structure.get('description', 'N/A')}"
        )

        # Validar campos obrigatorios
        installment_number = data.get("installment_number")
        amount = data.get("amount")

        if not installment_number or (
            isinstance(installment_number, str) and not installment_number.strip()
        ):
            logger.info(
                "[installments] Validacao falhou: installment_number ausente ou vazio"
            )
            logger.info(f"   Valor recebido: {repr(installment_number)}")
            return (
                jsonify({"success": False, "error": "Numero da parcela e obrigatorio"}),
                400,
            )

        if not amount or (isinstance(amount, str) and not amount.strip()):
            logger.info("[installments] Validacao falhou: amount ausente ou vazio")
            logger.info(f"   Valor recebido: {repr(amount)}")
            return (
                jsonify({"success": False, "error": "Valor da parcela e obrigatorio"}),
                400,
            )

        # Converter amount para string se for numero (banco espera TEXT)
        if isinstance(amount, (int, float)):
            amount = str(amount)
        elif isinstance(amount, str):
            # Garantir que e um numero valido antes de converter
            try:
                float(amount)
            except ValueError:
                logger.info(
                    "[installments] Validacao falhou: amount nao e um numero valido"
                )
                logger.info(f"   Valor recebido: {repr(amount)}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Valor da parcela deve ser um numero valido",
                        }
                    ),
                    400,
                )

        # Preparar dados para insercao (garantir que amount e string)
        insert_data = {
            "installment_number": str(installment_number).strip()
            if installment_number
            else None,
            "amount": str(amount).strip() if amount else None,
            "due_info": data.get("due_info") or None,
            "installment_type": data.get("installment_type") or None,
            "classification": data.get("classification") or None,
            "repetition": data.get("repetition") or None,
        }

        logger.info(f"[installments] Validacao OK, dados preparados: {insert_data}")
        logger.info("[installments] Criando parcela...")

        # Criar parcela
        installment_id = db.create_plan_structure_installment(structure_id, insert_data)

        if installment_id:
            logger.info(
                f"[installments] Parcela criada com sucesso! ID={installment_id}\n"
            )
            return jsonify({"success": True, "id": installment_id}), 201
        else:
            logger.info(
                "[installments] Erro: create_plan_structure_installment retornou 0 ou None\n"
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erro ao criar parcela no banco de dados",
                    }
                ),
                500,
            )

    except Exception as e:
        divider = "=" * 60
        logger.info(f"\n{divider}")
        logger.info("[installments] EXCEPTION ao criar parcela:")
        logger.info(f"Error: {e}")
        import traceback

        logger.info(f"Traceback:\n{traceback.format_exc()}")
        logger.info(f"{divider}\n")
        return (
            jsonify({"success": False, "error": f"Erro ao criar parcela: {str(e)}"}),
            500,
        )


@pev_bp.route(
    "/api/implantacao/<int:plan_id>/structures/fixed-costs-summary", methods=["GET"]
)
def get_fixed_costs_summary(plan_id: int):
    """
    Retorna o resumo de custos e despesas fixas das estruturas.
    """
    try:
        from config_database import get_db
        from modules.pev.implantation_data import (
            load_structures,
            calculate_investment_summary_by_block,
        )

        db = get_db()
        estruturas = load_structures(db, plan_id)
        resumo_investimentos = calculate_investment_summary_by_block(estruturas)

        # Buscar linha de totais
        resumo_totais = next(
            (
                item
                for item in resumo_investimentos
                if item.get("is_total")
                or (item.get("bloco") or "").strip().upper() == "TOTAL"
            ),
            {},
        )

        custos_fixos_mensal = float(resumo_totais.get("custos_fixos_mensal") or 0)
        despesas_fixas_mensal = float(resumo_totais.get("despesas_fixas_mensal") or 0)

        fixed_costs_summary = {
            "custos_fixos_mensal": custos_fixos_mensal,
            "despesas_fixas_mensal": despesas_fixas_mensal,
            "total_gastos_mensal": float(
                resumo_totais.get("total_gastos_mensal")
                or custos_fixos_mensal + despesas_fixas_mensal
            ),
        }

        # DEBUG
        logger.info(f"\nAPI GET /structures/fixed-costs-summary - plan_id={plan_id}")
        logger.info(f"   Estruturas: {len(estruturas)}")
        logger.info(f"   Fixed Costs: {fixed_costs_summary}\n")

        return jsonify({"success": True, "data": fixed_costs_summary}), 200

    except Exception as exc:
        logger.info(
            f"[structures] Error calculating fixed costs summary for plan {plan_id}: {exc}"
        )
        import traceback

        traceback.print_exc()
        return (
            jsonify(
                {"success": False, "error": "Erro ao calcular resumo de custos fixos"}
            ),
            500,
        )


# ==================== FINANCIAL MODEL APIS ====================


# PREMISSAS
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/premises", methods=["POST"])
def create_premise(plan_id: int):
    """Create financial premise"""
    try:
        data = request.get_json() or {}

        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        premise_id = db.create_plan_finance_premise(plan_id, data)

        if premise_id:
            return jsonify({"success": True, "id": premise_id}), 201
        else:
            return jsonify({"success": False, "error": "Erro ao criar premissa"}), 500

    except Exception as e:
        logger.info(f"Error creating premise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>", methods=["PUT"]
)
def update_premise(plan_id: int, premise_id: int):
    """Update financial premise"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_finance_premise(premise_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar premissa"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating premise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/premises/<int:premise_id>",
    methods=["DELETE"],
)
def delete_premise(plan_id: int, premise_id: int):
    """Delete financial premise"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_finance_premise(premise_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Erro ao deletar premissa"}), 500

    except Exception as e:
        logger.info(f"Error deleting premise: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# INVESTIMENTOS
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/investments", methods=["POST"])
def create_investment(plan_id: int):
    """Create investment item"""
    try:
        data = request.get_json() or {}

        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        investment_id = db.create_plan_finance_investment(plan_id, data)

        if investment_id:
            return jsonify({"success": True, "id": investment_id}), 201
        else:
            return (
                jsonify({"success": False, "error": "Erro ao criar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error creating investment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>",
    methods=["PUT"],
)
def update_investment(plan_id: int, investment_id: int):
    """Update investment item"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_finance_investment(investment_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating investment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/investments/<int:investment_id>",
    methods=["DELETE"],
)
def delete_investment(plan_id: int, investment_id: int):
    """Delete investment item"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_finance_investment(investment_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao deletar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error deleting investment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
# FONTES DE RECURSOS
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/sources", methods=["POST"])
def create_source(plan_id: int):
    """Create funding source"""
    try:
        data = request.get_json() or {}

        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        # Usar método correto add_plan_finance_source
        source_id = db.add_plan_finance_source(
            plan_id=plan_id,
            category=data.get("category", ""),
            description=data["description"],
            amount=str(data.get("amount", "")),
            availability=data.get("availability"),
            contribution_date=data.get("contribution_date"),
            notes=data.get("notes"),
        )

        if source_id:
            return jsonify({"success": True, "id": source_id}), 201
        else:
            return jsonify({"success": False, "error": "Erro ao criar fonte"}), 500

    except Exception as e:
        logger.info(f"Error creating source: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>", methods=["PUT"]
)
def update_source(plan_id: int, source_id: int):
    """Update funding source"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        # Usar método correto com parâmetros separados
        success = db.update_plan_finance_source(
            source_id=source_id,
            category=data.get("category"),
            description=data.get("description"),
            amount=data.get("amount"),
            availability=data.get("availability"),
            contribution_date=data.get("contribution_date"),
            notes=data.get("notes"),
        )

        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Erro ao atualizar fonte"}), 500

    except Exception as e:
        logger.info(f"Error updating source: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/sources/<int:source_id>", methods=["DELETE"]
)
def delete_source(plan_id: int, source_id: int):
    """Delete funding source"""
    try:
        from config_database import get_db

        db = get_db()

        # Método correto não precisa de plan_id
        success = db.delete_plan_finance_source(source_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({"success": False, "error": "Erro ao deletar fonte"}), 500

    except Exception as e:
        logger.info(f"Error deleting source: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# CUSTOS VARIÁVEIS
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/variable_costs", methods=["POST"])
def create_variable_cost(plan_id: int):
    """Create variable cost"""
    try:
        data = request.get_json() or {}

        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        cost_id = db.create_plan_finance_variable_cost(plan_id, data)

        if cost_id:
            return jsonify({"success": True, "id": cost_id}), 201
        else:
            return (
                jsonify({"success": False, "error": "Erro ao criar custo variável"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error creating variable cost: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>",
    methods=["PUT"],
)
def update_variable_cost(plan_id: int, cost_id: int):
    """Update variable cost"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_finance_variable_cost(cost_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao atualizar custo variável"}
                ),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating variable cost: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/variable_costs/<int:cost_id>",
    methods=["DELETE"],
)
def delete_variable_cost(plan_id: int, cost_id: int):
    """Delete variable cost"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_finance_variable_cost(cost_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao deletar custo variável"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error deleting variable cost: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# REGRAS DE DESTINAÇÃO
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/result_rules", methods=["POST"])
def create_result_rule(plan_id: int):
    """Create result distribution rule"""
    try:
        data = request.get_json() or {}

        if not data.get("description"):
            return jsonify({"success": False, "error": "Descrição é obrigatória"}), 400

        from config_database import get_db

        db = get_db()

        rule_id = db.create_plan_finance_result_rule(plan_id, data)

        if rule_id:
            return jsonify({"success": True, "id": rule_id}), 201
        else:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao criar regra de destinação"}
                ),
                500,
            )

    except Exception as e:
        logger.info(f"Error creating result rule: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>", methods=["PUT"]
)
def update_result_rule(plan_id: int, rule_id: int):
    """Update result distribution rule"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_finance_result_rule(rule_id, plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao atualizar regra de destinação"}
                ),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating result rule: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/result_rules/<int:rule_id>",
    methods=["DELETE"],
)
def delete_result_rule(plan_id: int, rule_id: int):
    """Delete result distribution rule"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_finance_result_rule(rule_id, plan_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao deletar regra de destinação"}
                ),
                500,
            )

    except Exception as e:
        logger.info(f"Error deleting result rule: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# INVESTMENT CONTRIBUTIONS (Capital de Giro)
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/investment/contributions", methods=["GET"]
)
def get_investment_contributions(plan_id: int):
    """Lista contribuições de investimento por item_id"""
    try:
        from config_database import get_db

        db = get_db()

        item_id = request.args.get("item_id")

        # Por enquanto, retornar lista vazia (implementação futura)
        # Esses dados virão das estruturas
        return jsonify({"success": True, "data": []}), 200

    except Exception as e:
        logger.info(f"Error getting investment contributions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@pev_bp.route("/api/implantacao/<int:plan_id>/finance/funding_sources", methods=["GET"])
def get_funding_sources(plan_id: int):
    """Lista fontes de recursos"""
    try:
        from config_database import get_db

        db = get_db()

        # Buscar fontes cadastradas
        sources = db.list_plan_finance_sources(plan_id)

        return jsonify({"success": True, "data": sources}), 200

    except Exception as e:
        logger.info(f"Error getting funding sources: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# MÉTRICAS
@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/metrics", methods=["PUT"])
def update_metrics(plan_id: int):
    """Update financial metrics (payback, TIR, notes)"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        success = db.update_plan_finance_metrics(plan_id, data)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar métricas"}),
                500,
            )

    except Exception as e:
        logger.info(f"Error updating metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================
# APIs para ModeFin (Modelagem Financeira)
# =========================================


@pev_bp.route("/api/implantacao/<int:plan_id>/finance/capital-giro", methods=["GET"])
def list_capital_giro(plan_id: int):
    """List all capital de giro items for a plan"""
    try:
        from config_database import get_db

        db = get_db()

        items = db.list_plan_capital_giro(plan_id)

        return jsonify({"success": True, "data": items}), 200

    except Exception as e:
        logger.info(f"[API] Error listing capital giro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route("/api/implantacao/<int:plan_id>/finance/capital-giro", methods=["POST"])
def create_capital_giro(plan_id: int):
    """Create new capital de giro item"""
    try:
        data = request.get_json() or {}

        # Validação
        if not data.get("item_type"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Tipo é obrigatório (caixa, recebiveis, estoques)",
                    }
                ),
                400,
            )

        if not data.get("contribution_date"):
            return (
                jsonify({"success": False, "error": "Data do aporte é obrigatória"}),
                400,
            )

        if not data.get("amount"):
            return jsonify({"success": False, "error": "Valor é obrigatório"}), 400

        from config_database import get_db

        db = get_db()

        item_id = db.add_plan_capital_giro(
            plan_id=plan_id,
            item_type=data["item_type"],
            contribution_date=data["contribution_date"],
            amount=float(data["amount"]),
            description=data.get("description"),
            notes=data.get("notes"),
        )

        if item_id:
            return jsonify({"success": True, "id": item_id}), 201
        else:
            return (
                jsonify({"success": False, "error": "Erro ao criar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"[API] Error creating capital giro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>", methods=["PUT"]
)
def update_capital_giro(plan_id: int, item_id: int):
    """Update capital de giro item"""
    try:
        data = request.get_json() or {}

        from config_database import get_db

        db = get_db()

        # Converter amount para float se presente
        if "amount" in data and data["amount"] is not None:
            data["amount"] = float(data["amount"])

        success = db.update_plan_capital_giro(
            item_id=item_id,
            item_type=data.get("item_type"),
            contribution_date=data.get("contribution_date"),
            amount=data.get("amount"),
            description=data.get("description"),
            notes=data.get("notes"),
        )

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"[API] Error updating capital giro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/capital-giro/<int:item_id>",
    methods=["DELETE"],
)
def delete_capital_giro(plan_id: int, item_id: int):
    """Delete capital de giro item"""
    try:
        from config_database import get_db

        db = get_db()

        success = db.delete_plan_capital_giro(item_id)

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao deletar investimento"}),
                500,
            )

    except Exception as e:
        logger.info(f"[API] Error deleting capital giro: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/executive-summary", methods=["GET"]
)
def get_executive_summary_api(plan_id: int):
    """Get executive summary"""
    try:
        from config_database import get_db

        db = get_db()

        summary = db.get_executive_summary(plan_id)

        return jsonify({"success": True, "data": summary or ""}), 200

    except Exception as e:
        logger.info(f"[API] Error getting executive summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/executive-summary", methods=["PUT"]
)
def update_executive_summary_api(plan_id: int):
    """Update executive summary"""
    try:
        data = request.get_json() or {}

        if "executive_summary" not in data:
            return (
                jsonify(
                    {"success": False, "error": "Campo executive_summary é obrigatório"}
                ),
                400,
            )

        from config_database import get_db

        db = get_db()

        success = db.update_executive_summary(plan_id, data["executive_summary"])

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify(
                    {"success": False, "error": "Erro ao atualizar resumo executivo"}
                ),
                500,
            )

    except Exception as e:
        logger.info(f"[API] Error updating executive summary: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/profit-distribution", methods=["GET"]
)
def get_profit_distribution_api(plan_id: int):
    """Get profit distribution"""
    try:
        from config_database import get_db

        db = get_db()

        distribution = (
            db.get_profit_distribution(plan_id)
            if hasattr(db, "get_profit_distribution")
            else None
        )

        return jsonify({"success": True, "data": distribution}), 200

    except Exception as e:
        logger.info(f"[API] Error getting profit distribution: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@login_required
@pev_bp.route(
    "/api/implantacao/<int:plan_id>/finance/profit-distribution", methods=["PUT"]
)
def update_profit_distribution_api(plan_id: int):
    """Update profit distribution"""
    try:
        data = request.get_json() or {}

        if "profit_distribution_percent" not in data:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Campo profit_distribution_percent é obrigatório",
                    }
                ),
                400,
            )

        from config_database import get_db

        db = get_db()

        success = (
            db.update_profit_distribution(
                plan_id=plan_id,
                percentage=float(data["profit_distribution_percent"]),
                start_date=data.get("start_date"),
                notes=data.get("notes"),
            )
            if hasattr(db, "update_profit_distribution")
            else False
        )

        if success:
            return jsonify({"success": True}), 200
        else:
            return (
                jsonify({"success": False, "error": "Erro ao atualizar distribuição"}),
                500,
            )

    except Exception as e:
        logger.info(f"[API] Error updating profit distribution: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
