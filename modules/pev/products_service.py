"""Service layer for Modelo & Mercado products."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import inspect

from models import db
from models.product import Product

TWOPLACES = Decimal("0.01")


class ProductValidationError(ValueError):
    """Raised when incoming payload is invalid."""


class ProductNotFoundError(ValueError):
    """Raised when a product cannot be located for the given plan."""


def ensure_products_table() -> None:
    """Ensure plan_products exists before running any queries."""
    inspector = inspect(db.engine)
    if Product.__tablename__ not in inspector.get_table_names():
        Product.__table__.create(bind=db.engine, checkfirst=True)


def fetch_products(plan_id: int) -> List[Dict[str, Any]]:
    """Return serialized products for a plan."""
    ensure_products_table()

    query = (
        Product.query.filter_by(plan_id=plan_id, is_deleted=False)
        .order_by(Product.created_at.asc(), Product.id.asc())
    )
    return [serialize_product(product) for product in query.all()]


def fetch_product(plan_id: int, product_id: int) -> Dict[str, Any]:
    """Return a single product or raise not found."""
    ensure_products_table()

    product = Product.query.filter_by(
        id=product_id,
        plan_id=plan_id,
        is_deleted=False,
    ).first()

    if not product:
        raise ProductNotFoundError("Produto não encontrado.")

    return serialize_product(product)


def create_product(plan_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new product for a plan."""
    ensure_products_table()

    product = Product()
    _assign_product_fields(product, plan_id, payload)

    db.session.add(product)
    db.session.commit()
    return serialize_product(product)


def update_product(plan_id: int, product_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing product."""
    ensure_products_table()

    product = Product.query.filter_by(
        id=product_id,
        plan_id=plan_id,
        is_deleted=False,
    ).first()

    if not product:
        raise ProductNotFoundError("Produto não encontrado.")

    _assign_product_fields(product, plan_id, payload)
    db.session.commit()
    return serialize_product(product)


def soft_delete_product(plan_id: int, product_id: int) -> None:
    """Soft delete a product (keeps history but hides from UI)."""
    ensure_products_table()

    product = Product.query.filter_by(
        id=product_id,
        plan_id=plan_id,
        is_deleted=False,
    ).first()

    if not product:
        raise ProductNotFoundError("Produto não encontrado.")

    product.is_deleted = True
    product.updated_at = datetime.utcnow()
    db.session.commit()


def calculate_totals(products: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate totals for products dashboards and reports."""
    items = list(products)
    count = len(items)

    def _as_decimal(value: Any) -> Decimal:
        """Coerce incoming numeric-ish values to a decimal with two places."""
        return Decimal(str(_to_float(value))).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    if count == 0:
        zero = 0.0
        return {
            "count": 0,
            "market_revenue": zero,
            "average_margin_percent": zero,
            "share_goal_units": zero,
            "faturamento": {"valor": zero, "percentual": zero},
            "custos_variaveis": {"valor": zero, "percentual": zero},
            "despesas_variaveis": {"valor": zero, "percentual": zero},
            "margem_contribuicao": {"valor": zero, "percentual": zero},
            "meta_market_share": {"unidades": zero, "percentual": zero},
        }

    decimal_zero = Decimal("0.00")
    total_market_revenue = Decimal("0.00")
    total_units_goal = Decimal("0.00")
    total_revenue_goal = Decimal("0.00")
    total_cost_value = Decimal("0.00")
    total_expense_value = Decimal("0.00")
    total_margin_value = Decimal("0.00")
    margin_percent_sum = Decimal("0.00")
    share_percent_weighted = Decimal("0.00")
    share_weight = Decimal("0.00")

    for item in items:
        total_market_revenue += _as_decimal(item.get("market_size_monthly_revenue"))

        share_percent = _as_decimal(item.get("market_share_goal_percent"))
        market_units = _as_decimal(item.get("market_size_monthly_units"))

        units_goal = _as_decimal(item.get("market_share_goal_monthly_units"))
        if units_goal == decimal_zero and share_percent > decimal_zero and market_units > decimal_zero:
            units_goal = ((share_percent / Decimal("100")) * market_units).quantize(
                TWOPLACES, rounding=ROUND_HALF_UP
            )
        total_units_goal += units_goal

        price = _as_decimal(item.get("sale_price"))
        revenue_goal = (price * units_goal).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        total_revenue_goal += revenue_goal

        cost_unit = _as_decimal(item.get("variable_costs_value"))
        expense_unit = _as_decimal(item.get("variable_expenses_value"))
        margin_unit = _as_decimal(item.get("unit_contribution_margin_value"))

        cost_total = (cost_unit * units_goal).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        expense_total = (expense_unit * units_goal).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        margin_total = (margin_unit * units_goal).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

        if margin_total == decimal_zero and revenue_goal > decimal_zero:
            margin_total = (revenue_goal - cost_total - expense_total).quantize(
                TWOPLACES, rounding=ROUND_HALF_UP
            )

        total_cost_value += cost_total
        total_expense_value += expense_total
        total_margin_value += margin_total

        margin_percent_sum += _as_decimal(item.get("unit_contribution_margin_percent"))

        if share_percent > decimal_zero:
            if market_units > decimal_zero:
                share_percent_weighted += share_percent * market_units
                share_weight += market_units
            else:
                share_percent_weighted += share_percent
                share_weight += Decimal("1.00")

    def _percent(part: Decimal, whole: Decimal) -> float:
        if whole <= decimal_zero:
            return 0.0
        return float((part / whole * Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP))

    average_margin = (
        (margin_percent_sum / Decimal(count)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if count
        else decimal_zero
    )

    share_percent_overall = (
        (share_percent_weighted / share_weight).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        if share_weight > decimal_zero
        else decimal_zero
    )

    market_revenue_float = float(total_market_revenue.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    units_goal_float = float(total_units_goal.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    revenue_goal_float = float(total_revenue_goal.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    cost_float = float(total_cost_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    expense_float = float(total_expense_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    margin_float = float(total_margin_value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))

    return {
        "count": count,
        "market_revenue": market_revenue_float,
        "average_margin_percent": float(average_margin),
        "share_goal_units": units_goal_float,
        "faturamento": {
            "valor": revenue_goal_float,
            "percentual": 100.0 if revenue_goal_float > 0 else 0.0,
        },
        "custos_variaveis": {
            "valor": cost_float,
            "percentual": _percent(total_cost_value, total_revenue_goal),
        },
        "despesas_variaveis": {
            "valor": expense_float,
            "percentual": _percent(total_expense_value, total_revenue_goal),
        },
        "margem_contribuicao": {
            "valor": margin_float,
            "percentual": _percent(total_margin_value, total_revenue_goal),
        },
        "meta_market_share": {
            "unidades": units_goal_float,
            "percentual": float(share_percent_overall),
        },
    }


def adapt_legacy_products(raw_products: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize legacy dictionaries (e.g. fallback data) into the new schema."""
    normalized = []
    for raw in raw_products:
        normalized.append(
            {
                "id": raw.get("id"),
                "plan_id": raw.get("plan_id"),
                "name": raw.get("name", ""),
                "description": raw.get("description", ""),
                "sale_price": _to_float(raw.get("sale_price")),
                "sale_price_notes": raw.get("sale_price_notes"),
                "variable_costs_percent": _to_float(raw.get("variable_costs_percent")),
                "variable_costs_value": _to_float(raw.get("variable_costs_value")),
                "variable_costs_notes": raw.get("variable_costs_notes"),
                "variable_expenses_percent": _to_float(raw.get("variable_expenses_percent")),
                "variable_expenses_value": _to_float(raw.get("variable_expenses_value")),
                "variable_expenses_notes": raw.get("variable_expenses_notes"),
                "unit_contribution_margin_percent": _to_float(raw.get("unit_contribution_margin_percent")),
                "unit_contribution_margin_value": _to_float(raw.get("unit_contribution_margin_value")),
                "unit_contribution_margin_notes": raw.get("unit_contribution_margin_notes"),
                "market_size_monthly_units": _to_float(raw.get("market_size_monthly_units")),
                "market_size_monthly_revenue": _to_float(raw.get("market_size_monthly_revenue")),
                "market_size_notes": raw.get("market_size_notes"),
                "market_share_goal_monthly_units": _to_float(raw.get("market_share_goal_monthly_units")),
                "market_share_goal_percent": _to_float(raw.get("market_share_goal_percent")),
                "market_share_goal_notes": raw.get("market_share_goal_notes"),
            }
        )
    return normalized


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assign_product_fields(product: Product, plan_id: int, payload: Dict[str, Any]) -> None:
    """Mutate a SQLAlchemy product instance with validated payload values."""
    clean = _build_clean_product_data(plan_id, payload)

    product.plan_id = plan_id
    product.name = clean["name"]
    product.description = clean["description"]
    product.sale_price = clean["sale_price"]
    product.sale_price_notes = clean["sale_price_notes"]
    product.variable_costs_percent = clean["variable_costs_percent"]
    product.variable_costs_value = clean["variable_costs_value"]
    product.variable_costs_notes = clean["variable_costs_notes"]
    product.variable_expenses_percent = clean["variable_expenses_percent"]
    product.variable_expenses_value = clean["variable_expenses_value"]
    product.variable_expenses_notes = clean["variable_expenses_notes"]
    product.unit_contribution_margin_percent = clean["unit_contribution_margin_percent"]
    product.unit_contribution_margin_value = clean["unit_contribution_margin_value"]
    product.unit_contribution_margin_notes = clean["unit_contribution_margin_notes"]
    product.market_size_monthly_units = clean["market_size_monthly_units"]
    product.market_size_monthly_revenue = clean["market_size_monthly_revenue"]
    product.market_size_notes = clean["market_size_notes"]
    product.market_share_goal_monthly_units = clean["market_share_goal_monthly_units"]
    product.market_share_goal_percent = clean["market_share_goal_percent"]
    product.market_share_goal_notes = clean["market_share_goal_notes"]
    product.is_deleted = False
    product.updated_at = datetime.utcnow()


def _build_clean_product_data(plan_id: int, payload: Dict[str, Any]) -> Dict[str, Decimal]:
    """Validate and normalize incoming payload into Decimal-based structure."""
    name = _normalize_text(payload.get("name"))
    if not name:
        raise ProductValidationError("Nome do produto é obrigatório.")

    sale_price = _parse_decimal(payload.get("sale_price"), allow_zero=False, field="Preço de venda")
    description = _normalize_text(payload.get("description"), allow_blank=True)
    sale_price_notes = _normalize_text(payload.get("sale_price_notes"), allow_blank=True)

    raw_cost_percent = _parse_decimal(payload.get("variable_costs_percent"), allow_zero=True)
    raw_cost_value = _parse_decimal(payload.get("variable_costs_value"), allow_zero=True)

    raw_expense_percent = _parse_decimal(payload.get("variable_expenses_percent"), allow_zero=True)
    raw_expense_value = _parse_decimal(payload.get("variable_expenses_value"), allow_zero=True)

    # Derive costs
    costs_value = raw_cost_value
    costs_percent = raw_cost_percent
    if costs_value == Decimal("0.00") and costs_percent != Decimal("0.00"):
        costs_value = _quantize(sale_price * costs_percent / Decimal("100"))
    elif costs_value != Decimal("0.00") and sale_price > Decimal("0.00"):
        costs_percent = _quantize((costs_value / sale_price) * Decimal("100"))
    else:
        costs_percent = _quantize(costs_percent)
        costs_value = _quantize(costs_value)

    # Derive expenses
    expenses_value = raw_expense_value
    expenses_percent = raw_expense_percent
    if expenses_value == Decimal("0.00") and expenses_percent != Decimal("0.00"):
        expenses_value = _quantize(sale_price * expenses_percent / Decimal("100"))
    elif expenses_value != Decimal("0.00") and sale_price > Decimal("0.00"):
        expenses_percent = _quantize((expenses_value / sale_price) * Decimal("100"))
    else:
        expenses_percent = _quantize(expenses_percent)
        expenses_value = _quantize(expenses_value)

    margin_value = _quantize(sale_price - costs_value - expenses_value)
    margin_percent = (
        _quantize((margin_value / sale_price) * Decimal("100")) if sale_price > Decimal("0.00") else Decimal("0.00")
    )

    market_units = _parse_decimal(payload.get("market_size_monthly_units"), allow_zero=True)
    market_revenue = _quantize(market_units * sale_price)
    market_notes = _normalize_text(payload.get("market_size_notes"), allow_blank=True)

    share_units = _parse_decimal(payload.get("market_share_goal_monthly_units"), allow_zero=True)
    share_percent = _parse_decimal(payload.get("market_share_goal_percent"), allow_zero=True)
    share_notes = _normalize_text(payload.get("market_share_goal_notes"), allow_blank=True)

    if share_percent == Decimal("0.00") and market_units > Decimal("0.00") and share_units > Decimal("0.00"):
        share_percent = _quantize((share_units / market_units) * Decimal("100"))
    else:
        share_percent = _quantize(share_percent)

    return {
        "plan_id": plan_id,
        "name": name,
        "description": description,
        "sale_price": _quantize(sale_price),
        "sale_price_notes": sale_price_notes,
        "variable_costs_percent": costs_percent,
        "variable_costs_value": costs_value,
        "variable_costs_notes": _normalize_text(payload.get("variable_costs_notes"), allow_blank=True),
        "variable_expenses_percent": expenses_percent,
        "variable_expenses_value": expenses_value,
        "variable_expenses_notes": _normalize_text(payload.get("variable_expenses_notes"), allow_blank=True),
        "unit_contribution_margin_percent": margin_percent,
        "unit_contribution_margin_value": margin_value,
        "unit_contribution_margin_notes": _normalize_text(payload.get("unit_contribution_margin_notes"), allow_blank=True),
        "market_size_monthly_units": _quantize(market_units),
        "market_size_monthly_revenue": market_revenue,
        "market_size_notes": market_notes,
        "market_share_goal_monthly_units": _quantize(share_units),
        "market_share_goal_percent": share_percent,
        "market_share_goal_notes": share_notes,
    }


def serialize_product(product: Product) -> Dict[str, Any]:
    """Return a JSON-serializable representation of a product."""
    return {
        "id": product.id,
        "plan_id": product.plan_id,
        "name": product.name,
        "description": product.description,
        "sale_price": _to_float(product.sale_price),
        "sale_price_notes": product.sale_price_notes,
        "variable_costs_percent": _to_float(product.variable_costs_percent),
        "variable_costs_value": _to_float(product.variable_costs_value),
        "variable_costs_notes": product.variable_costs_notes,
        "variable_expenses_percent": _to_float(product.variable_expenses_percent),
        "variable_expenses_value": _to_float(product.variable_expenses_value),
        "variable_expenses_notes": product.variable_expenses_notes,
        "unit_contribution_margin_percent": _to_float(product.unit_contribution_margin_percent),
        "unit_contribution_margin_value": _to_float(product.unit_contribution_margin_value),
        "unit_contribution_margin_notes": product.unit_contribution_margin_notes,
        "market_size_monthly_units": _to_float(product.market_size_monthly_units),
        "market_size_monthly_revenue": _to_float(product.market_size_monthly_revenue),
        "market_size_notes": product.market_size_notes,
        "market_share_goal_monthly_units": _to_float(product.market_share_goal_monthly_units),
        "market_share_goal_percent": _to_float(product.market_share_goal_percent),
        "market_share_goal_notes": product.market_share_goal_notes,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
    }


def _parse_decimal(value: Any, *, allow_zero: bool, field: str = "") -> Decimal:
    """Parse input into Decimal while handling blanks and thousand separators."""
    if value is None:
        result = Decimal("0.00")
    elif isinstance(value, Decimal):
        result = value
    elif isinstance(value, (int, float)):
        result = Decimal(str(value))
    elif isinstance(value, str):
        trimmed = value.strip()
        if trimmed == "":
            result = Decimal("0.00")
        else:
            normalized = trimmed.replace(".", "").replace(",", ".")
            try:
                result = Decimal(normalized)
            except InvalidOperation as exc:
                label = f" ({field})" if field else ""
                raise ProductValidationError(f"Valor inválido{label}.") from exc
    else:
        raise ProductValidationError(f"Valor numérico inválido para {field or 'campo numérico'}.")

    if not allow_zero and result <= Decimal("0.00"):
        label = f" ({field})" if field else ""
        raise ProductValidationError(f"O valor deve ser maior que zero{label}.")

    if result < Decimal("0.00"):
        return Decimal("0.00")

    return _quantize(result)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _normalize_text(value: Optional[str], *, allow_blank: bool = False) -> str:
    if value is None:
        return "" if allow_blank else ""
    stripped = str(value).strip()
    if not stripped and not allow_blank:
        return ""
    return stripped


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value.quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        return 0.0
