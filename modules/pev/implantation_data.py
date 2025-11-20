from __future__ import annotations
import logging

"""
Helper functions to assemble Implantação (new venture) data structures
for templates and reports.
"""

logger = logging.getLogger(__name__)


import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Tuple

# Order in which macro phases should appear
PHASE_ORDER = ["alignment", "model", "execution", "delivery"]

PHASE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "alignment": {
        "title": "Alinhamento EstratÃ©gico",
        "tagline": "Garantir visÃ£o, ritmo compartilhado e responsabilidades antes de evoluir para modelo e execuÃ§Ã£o.",
        "pulse": None,
    },
    "model": {
        "title": "Modelo & Mercado",
        "tagline": "Transformar hipÃ³teses em propostas fundamentadas para cada segmento do negÃ³cio.",
        "pulse": None,
    },
    "execution": {
        "title": "Estruturas de ExecuÃ§Ã£o",
        "tagline": "Ancorar operaÃ§Ã£o, comercial e finanÃ§as para suportar o plano.",
        "pulse": None,
    },
    "delivery": {
        "title": "RelatÃ³rio Final",
        "tagline": "Consolidar narrativa, indicadores e entrega final do planejamento.",
        "pulse": None,
    },
}

DEFAULT_DELIVERABLES: Dict[str, List[Dict[str, str]]] = {
    "alignment": [
        {
            "label": "Canvas de expectativas dos sÃ³cios",
            "endpoint": "pev.implantacao_canvas_expectativas",
        },
    ],
    "model": [
        {
            "label": "Canvas de proposta de valor",
            "endpoint": "pev.implantacao_canvas_proposta_valor",
        },
        {
            "label": "Mapa de persona e jornada",
            "endpoint": "pev.implantacao_mapa_persona",
        },
        {
            "label": "Matriz de diferenciais",
            "endpoint": "pev.implantacao_matriz_diferenciais",
        },
        {"label": "Produtos e Margens", "endpoint": "pev.implantacao_produtos"},
    ],
    "execution": [
        {"label": "Estruturas por Ã¡rea", "endpoint": "pev.implantacao_estruturas"},
    ],
    "delivery": [
        {"label": "RelatÃ³rio final", "endpoint": "pev.implantacao_relatorio_final"},
    ],
}

MONTH_LABELS_PT: Dict[int, str] = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

AREA_LABELS = {
    "comercial": "EstruturaÃ§Ã£o Comercial",
    "comÃ©rcio": "EstruturaÃ§Ã£o Comercial",
    "operacional": "EstruturaÃ§Ã£o Operacional",
    "operacao": "EstruturaÃ§Ã£o Operacional",
    "adm_fin": "EstruturaÃ§Ã£o Adm / Fin",
    "administrativo_financeiro": "EstruturaÃ§Ã£o Adm / Fin",
    "administrativo": "EstruturaÃ§Ã£o Adm / Fin",
}

AREA_ORDER = [
    "EstruturaÃ§Ã£o Comercial",
    "EstruturaÃ§Ã£o Operacional",
    "EstruturaÃ§Ã£o Adm / Fin",
]

BLOCK_LABELS = {
    "pessoas": "Pessoas",
    "imoveis": "ImÃ³veis",
    "imÃ³veis": "ImÃ³veis",
    "instalacoes": "InstalaÃ§Ãµes",
    "instalaÃ§Ãµes": "InstalaÃ§Ãµes",
    "maquinas_equipamentos": "MÃ¡quinas e Equipamentos",
    "maquinas": "MÃ¡quinas e Equipamentos",
    "equipamentos": "MÃ¡quinas e Equipamentos",
    "moveis_utensilios": "MÃ³veis e UtensÃ­lios",
    "mÃ³veis_utensÃ­lios": "MÃ³veis e UtensÃ­lios",
    "moveis": "MÃ³veis e UtensÃ­lios",
    "mÃ³veis": "MÃ³veis e UtensÃ­lios",
    "utensilios": "MÃ³veis e UtensÃ­lios",
    "utensÃ­lios": "MÃ³veis e UtensÃ­lios",
    "ti_comunicacao": "TI e ComunicaÃ§Ã£o",
    "ti_e_comunicaÃ§Ã£o": "TI e ComunicaÃ§Ã£o",
    "ti": "TI e ComunicaÃ§Ã£o",
    "comunicacao": "TI e ComunicaÃ§Ã£o",
    "comunicaÃ§Ã£o": "TI e ComunicaÃ§Ã£o",
    "outros": "Outros",
}

STRUCTURE_BLOCK_CATEGORY_MAP = {
    "instalacoes": "instalacoes",
    "instalacao": "instalacoes",
    "imoveis": "instalacoes",
    "imovel": "instalacoes",
    "maquinas": "maquinas_equipamentos",
    "maquina": "maquinas_equipamentos",
    "equipamentos": "maquinas_equipamentos",
    "maquinas_equipamentos": "maquinas_equipamentos",
    "moveis": "outros",
    "moveis_utensilios": "outros",
    "moveis_e_utensilios": "outros",
    "utensilios": "outros",
    "utensilio": "outros",
    "ti": "outros",
    "ti_comunicacao": "outros",
    "ti_e_comunicacao": "outros",
    "comunicacao": "outros",
    "outros": "outros",
    "pessoas": "outros",
}

STRUCTURE_INVESTMENT_BLOCK_SLUGS = {
    "imoveis",
    "instalacoes",
    "maquinas",
    "maquinas_equipamentos",
    "equipamentos",
    "moveis",
    "moveis_utensilios",
    "moveis_e_utensilios",
    "utensilios",
    "utensilio",
    "ti",
    "ti_comunicacao",
    "ti_e_comunicacao",
    "comunicacao",
}

STRUCTURE_PEOPLE_BLOCK_SLUGS = {"pessoas"}

STRUCTURE_RECURRING_KEYWORDS = {
    "mensal",
    "mensalidade",
    "mensalmente",
    "assinatura",
    "salario",
    "folha",
    "folha de pagamento",
    "manutencao",
    "manutencao mensal",
    "locacao",
    "locacao mensal",
    "aluguel",
    "servico",
    "servico recorrente",
    "servicos",
    "honorarios",
    "contabilidade",
    "juridico",
}


MONTH_NAMES_FULL = [
    "Janeiro",
    "Fevereiro",
    "Mar\u00e7o",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

MONTH_NAMES_SHORT = [
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
]

MONTH_NAME_ALIASES = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
    "sep": 9,
    "sept": 9,
    "dec": 12,
    "december": 12,
}

INVESTMENT_GROUP_LABELS = {
    "capital_giro": "Capital de Giro",
    "imobilizado": "Imobilizado",
}

INVESTMENT_CATEGORY_TO_GROUP = {
    "caixa": "capital_giro",
    "recebiveis": "capital_giro",
    "estoques": "capital_giro",
    "instalacoes": "imobilizado",
    "maquinas_equipamentos": "imobilizado",
    "outros": "imobilizado",
}

INVESTMENT_CATEGORY_LABELS = {
    "caixa": "Caixa",
    "recebiveis": "Receb\u00edveis",
    "estoques": "Estoques",
    "instalacoes": "Instala\u00e7\u00f5es",
    "maquinas_equipamentos": "M\u00e1quinas e Equipamentos",
    "outros": "Outros Investimentos",
}

INVESTMENT_CATEGORY_ORDER = {
    "capital_giro": ["caixa", "recebiveis", "estoques"],
    "imobilizado": ["instalacoes", "maquinas_equipamentos", "outros"],
}

INVESTMENT_CATEGORY_ALIASES = {
    "estoque": "estoques",
    "estoque_inicial": "estoques",
    "recebivel": "recebiveis",
    "contas_a_receber": "recebiveis",
    "maquinas": "maquinas_equipamentos",
    "equipamentos": "maquinas_equipamentos",
    "maquinas_e_equipamentos": "maquinas_equipamentos",
    "instalacao": "instalacoes",
    "obras": "instalacoes",
    "outros_investimentos": "outros",
}

SOURCE_TYPE_LABELS = {
    "fornecedores": "Fornecedores",
    "emprestimos_financiamentos": "Empr\u00e9stimos e Financiamentos",
    "socios": "S\u00f3cios",
}

SOURCE_TYPE_ORDER = ["fornecedores", "emprestimos_financiamentos", "socios"]

SOURCE_TYPE_ALIASES = {
    "fornecedor": "fornecedores",
    "forn": "fornecedores",
    "emprestimos": "emprestimos_financiamentos",
    "emprestimo": "emprestimos_financiamentos",
    "financiamento": "emprestimos_financiamentos",
    "financiamentos": "emprestimos_financiamentos",
    "socios": "socios",
    "socio": "socios",
    "aporte_socios": "socios",
}


def _format_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if value is None:
        return ""
    return str(value)


def _ensure_list(value: Any, default: Optional[List[Any]] = None) -> List[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return list(default or [])
    return list(default or [])


def _ensure_dict(
    value: Any, default: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return dict(default or {})


def _parse_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9,.\-]", "", value.strip())
        if not cleaned:
            return None
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def _format_currency_br(value: Any) -> str:
    decimal_value = _parse_decimal(value)
    if decimal_value is None:
        return ""
    quantized = decimal_value.quantize(Decimal("0.01"))
    formatted = (
        f"{quantized:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return f"R$ {formatted}"


def _format_number_br(value: Any) -> str:
    decimal_value = _parse_decimal(value)
    if decimal_value is None:
        return ""
    if decimal_value == decimal_value.to_integral():
        formatted = f"{int(decimal_value):,}".replace(",", ".")
        return formatted
    quantized = decimal_value.quantize(Decimal("0.01"))
    formatted = (
        f"{quantized:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return formatted


def _format_percentage_br(value: Any) -> str:
    decimal_value = _parse_decimal(value)
    if decimal_value is None:
        return ""
    quantized = decimal_value.quantize(Decimal("0.01"))
    formatted = (
        f"{quantized:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    )
    return f"{formatted}%"


def _compute_value_percent(
    value_decimal: Optional[Decimal],
    percent_decimal: Optional[Decimal],
    base_decimal: Optional[Decimal],
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    if (
        value_decimal is None
        and percent_decimal is not None
        and base_decimal is not None
    ):
        value_decimal = (base_decimal * percent_decimal) / Decimal("100")
    if (
        percent_decimal is None
        and value_decimal is not None
        and base_decimal not in (None, Decimal("0"))
    ):
        percent_decimal = (value_decimal / base_decimal) * Decimal("100")
    return value_decimal, percent_decimal


def _strip_accents(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    normalized = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _slugify_key(value: Any) -> str:
    if value is None:
        return ""
    cleaned = _strip_accents(value).lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def _normalize_ascii_lower(value: Any) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    return ascii_text.lower().strip()


def _map_block_to_structure_category(block_name: Any) -> str:
    slug = _slugify_key(block_name)
    if not slug:
        return "outros"
    mapped = STRUCTURE_BLOCK_CATEGORY_MAP.get(slug)
    if mapped:
        return mapped
    # Try removing connector variations such as "_e_"
    normalized = slug.replace("_e_", "_").replace("__", "_")
    return STRUCTURE_BLOCK_CATEGORY_MAP.get(normalized, "outros")


def _classify_structure_installment(
    block_name: str, installment: Dict[str, Any]
) -> Dict[str, Any]:
    block_slug = _slugify_key(block_name)
    classificacao_raw = (
        installment.get("classificacao") or installment.get("classification") or ""
    ).strip()
    repeticao_raw = (
        installment.get("repeticao") or installment.get("repetition") or ""
    ).strip()
    tipo_raw = installment.get("tipo") or installment.get("installment_type") or ""

    classificacao_norm = _normalize_ascii_lower(classificacao_raw)
    repeticao_norm = _normalize_ascii_lower(repeticao_raw)
    tipo_norm = _normalize_ascii_lower(tipo_raw)

    if not classificacao_norm:
        if (
            block_slug in STRUCTURE_PEOPLE_BLOCK_SLUGS
            or tipo_norm in STRUCTURE_RECURRING_KEYWORDS
        ):
            classificacao_raw = "Despesa Fixa"
            classificacao_norm = "despesa fixa"
        elif block_slug in STRUCTURE_INVESTMENT_BLOCK_SLUGS:
            classificacao_raw = "Investimento"
            classificacao_norm = "investimento"
        else:
            classificacao_raw = "Investimento"
            classificacao_norm = "investimento"

    if not repeticao_norm:
        if tipo_norm in STRUCTURE_RECURRING_KEYWORDS or classificacao_norm in {
            "despesa fixa",
            "custo fixo",
        }:
            repeticao_raw = "Mensal"
            repeticao_norm = "mensal"
        elif classificacao_norm == "investimento":
            repeticao_raw = "Unica"
            repeticao_norm = "unica"

    category_slug = _map_block_to_structure_category(block_name)
    group_slug = INVESTMENT_CATEGORY_TO_GROUP.get(category_slug, "imobilizado")

    return {
        "classificacao": classificacao_raw,
        "classificacao_norm": classificacao_norm,
        "repeticao": repeticao_raw,
        "repeticao_norm": repeticao_norm,
        "category": category_slug,
        "group": group_slug,
    }


def _normalize_investment_category(value: Any) -> str:
    slug = _slugify_key(value)
    if slug in INVESTMENT_CATEGORY_TO_GROUP:
        return slug
    alias = INVESTMENT_CATEGORY_ALIASES.get(slug)
    if alias:
        return alias
    return slug


def _normalize_investment_group(
    value: Any, fallback_category: Optional[str] = None
) -> str:
    slug = _slugify_key(value)
    if slug in INVESTMENT_GROUP_LABELS:
        return slug
    if fallback_category:
        fallback_category = _normalize_investment_category(fallback_category)
        mapped = INVESTMENT_CATEGORY_TO_GROUP.get(fallback_category)
        if mapped:
            return mapped
    if slug:
        return slug
    if fallback_category:
        return INVESTMENT_CATEGORY_TO_GROUP.get(fallback_category, "")
    return ""


def _normalize_source_type(value: Any) -> str:
    slug = _slugify_key(value)
    if slug in SOURCE_TYPE_LABELS:
        return slug
    alias = SOURCE_TYPE_ALIASES.get(slug)
    if alias:
        return alias
    return slug


def _parse_month_from_label(label: Any) -> Optional[Tuple[int, int]]:
    if label is None:
        return None
    if isinstance(label, datetime):
        return label.year, label.month
    if isinstance(label, date):
        return label.year, label.month
    text = _strip_accents(label).lower()
    if not text:
        return None
    tokens = re.split(r"[^a-z0-9]+", text)
    tokens = [token for token in tokens if token]
    if not tokens:
        return None
    year: Optional[int] = None
    month: Optional[int] = None
    for token in tokens:
        if len(token) == 4 and token.isdigit():
            year = int(token)
            break
    if year is None:
        return None
    for token in tokens:
        if token == str(year):
            continue
        if token.isdigit() and len(token) <= 2:
            candidate = int(token)
            if 1 <= candidate <= 12:
                month = candidate
                break
        normalized_month = MONTH_NAME_ALIASES.get(token)
        if normalized_month:
            month = normalized_month
            break
    if month is None:
        for idx, token in enumerate(tokens):
            if token == str(year) and idx > 0:
                previous = tokens[idx - 1]
                if previous.isdigit() and len(previous) <= 2:
                    candidate = int(previous)
                    if 1 <= candidate <= 12:
                        month = candidate
                        break
                normalized_month = MONTH_NAME_ALIASES.get(previous)
                if normalized_month:
                    month = normalized_month
                    break
    if month and year:
        return year, month
    return None


def _coerce_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    month_tuple = _parse_month_from_label(text)
    if month_tuple:
        year, month = month_tuple
        try:
            return date(year, month, 1)
        except ValueError:
            return None
    return None


def _month_tuple_from_value(value: Any) -> Optional[Tuple[int, int]]:
    if isinstance(value, datetime):
        return value.year, value.month
    if isinstance(value, date):
        return value.year, value.month
    if value is None:
        return None
    coerced = _coerce_date(value)
    if coerced:
        return coerced.year, coerced.month
    return _parse_month_from_label(value)


def _month_key_from_tuple(month_tuple: Tuple[int, int]) -> str:
    year, month = month_tuple
    return f"{year:04d}-{month:02d}"


def _format_month_full(month_tuple: Tuple[int, int]) -> str:
    year, month = month_tuple
    if 1 <= month <= 12:
        return f"{MONTH_NAMES_FULL[month - 1]}/{year}"
    return f"{month:02d}/{year}"


def _format_month_short(month_tuple: Tuple[int, int]) -> str:
    year, month = month_tuple
    if 1 <= month <= 12:
        return f"{MONTH_NAMES_SHORT[month - 1]}/{year}"
    return f"{month:02d}/{year}"


def _build_fallback_key(label: str, prefix: str = "periodo") -> str:
    slug = _slugify_key(label)
    if not slug:
        slug = prefix
    return f"{prefix}::{slug}"


def _format_currency_cell(amount: Optional[Decimal]) -> str:
    if amount is None:
        return "-"
    return _format_currency_br(amount)


def _accumulate_decimal(
    target: Dict[str, Decimal], key: str, amount: Optional[Decimal]
) -> None:
    if amount is None:
        return
    target[key] = target.get(key, Decimal("0")) + amount


def _build_month_columns(
    month_tuples: List[Tuple[int, int]],
    fallback_labels: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    unique_months = sorted({tuple(item) for item in month_tuples if item})
    columns: List[Dict[str, Any]] = [
        {
            "key": _month_key_from_tuple(month_tuple),
            "year": month_tuple[0],
            "month": month_tuple[1],
            "label_full": _format_month_full(month_tuple),
            "label_short": _format_month_short(month_tuple),
            "is_fallback": False,
        }
        for month_tuple in unique_months
    ]
    seen_fallback = set()
    for entry in fallback_labels:
        label = entry.get("label") or ""
        key = entry.get("key") or _build_fallback_key(label, prefix="periodo")
        if key in seen_fallback:
            continue
        seen_fallback.add(key)
        columns.append(
            {
                "key": key,
                "label_full": label or key,
                "label_short": label or key,
                "is_fallback": True,
            }
        )
    return columns


def _build_matrix_line(
    description: str,
    values_map: Dict[str, Decimal],
    columns: List[Dict[str, Any]],
    total_strategy: str = "sum",
) -> Dict[str, Any]:
    column_outputs: List[str] = []
    total_decimal = Decimal("0")
    last_value: Optional[Decimal] = None
    for column in columns:
        key = column["key"]
        amount = values_map.get(key)
        column_outputs.append(_format_currency_cell(amount))
        if amount is None:
            continue
        if total_strategy == "last":
            last_value = amount
        else:
            total_decimal += amount
    total_amount: Optional[Decimal]
    if total_strategy == "last":
        total_amount = last_value
    else:
        total_amount = total_decimal
    total_display = _format_currency_cell(total_amount)
    return {
        "descricao": description,
        "valores": column_outputs,
        "total": total_display,
        "total_decimal": float(total_amount) if total_amount is not None else None,
    }


def _prepare_investment_dataset(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    month_tuples: List[Tuple[int, int]] = []
    fallback_labels: List[Dict[str, str]] = []
    per_group_category: Dict[str, Dict[str, Dict[str, Any]]] = {}
    totals_per_month: Dict[str, Decimal] = {}
    totals_por_grupo: Dict[str, Decimal] = {}
    grand_total = Decimal("0")

    for raw in investments:
        category_slug = _normalize_investment_category(raw.get("category"))
        group_slug = _normalize_investment_group(
            raw.get("investment_group"), category_slug
        )
        group_label = INVESTMENT_GROUP_LABELS.get(
            group_slug, raw.get("investment_group") or group_slug or "Outros"
        )
        category_label = INVESTMENT_CATEGORY_LABELS.get(
            category_slug, raw.get("category") or category_slug or "Outros"
        )
        contribution_raw = raw.get("contribution_date")
        contribution_date = _coerce_date(contribution_raw)
        month_tuple = _month_tuple_from_value(contribution_date or contribution_raw)
        month_key = _month_key_from_tuple(month_tuple) if month_tuple else None
        amount_decimal = _parse_decimal(raw.get("amount"))

        entry = {
            "id": raw.get("id"),
            "descricao": raw.get("description"),
            "valor": _format_currency_br(raw.get("amount")),
            "valor_decimal": float(amount_decimal)
            if amount_decimal is not None
            else None,
            "grupo": group_slug,
            "grupo_label": group_label,
            "categoria": category_slug,
            "categoria_label": category_label,
            "data_aporte": _format_date(contribution_date) if contribution_date else "",
            "data_aporte_iso": contribution_date.isoformat()
            if contribution_date
            else "",
            "observacoes": raw.get("notes") or "",
            "mes_chave": month_key or "",
        }
        entries.append(entry)

        if month_tuple:
            month_tuples.append(month_tuple)
        else:
            if contribution_raw:
                label = str(contribution_raw)
                fallback_key = _build_fallback_key(label, prefix="aporte")
                fallback_labels.append({"label": label, "key": fallback_key})
                month_key = fallback_key

        if amount_decimal is None:
            continue
        grand_total += amount_decimal
        totals_por_grupo[group_slug] = (
            totals_por_grupo.get(group_slug, Decimal("0")) + amount_decimal
        )
        if month_key:
            _accumulate_decimal(totals_per_month, month_key, amount_decimal)

        group_entry = per_group_category.setdefault(group_slug, {})
        category_entry = group_entry.setdefault(
            category_slug,
            {
                "total": Decimal("0"),
                "per_month": {},
            },
        )
        category_entry["total"] = category_entry["total"] + amount_decimal
        if month_key:
            _accumulate_decimal(category_entry["per_month"], month_key, amount_decimal)

    return {
        "entries": entries,
        "month_tuples": month_tuples,
        "fallback_labels": fallback_labels,
        "per_group_category": per_group_category,
        "totals_per_month": totals_per_month,
        "totals_por_grupo": totals_por_grupo,
        "grand_total": grand_total,
    }


def _prepare_sources_dataset(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    month_tuples: List[Tuple[int, int]] = []
    fallback_labels: List[Dict[str, str]] = []
    per_type_map: Dict[str, Dict[str, Any]] = {}
    totals_per_month: Dict[str, Decimal] = {}
    totals_por_tipo: Dict[str, Decimal] = {}
    grand_total = Decimal("0")

    for raw in sources:
        tipo_slug = _normalize_source_type(raw.get("category"))
        tipo_label = SOURCE_TYPE_LABELS.get(
            tipo_slug, raw.get("category") or tipo_slug or "Outros"
        )
        contribution_raw = raw.get("contribution_date")
        contribution_date = _coerce_date(contribution_raw)
        month_tuple = _month_tuple_from_value(contribution_date or contribution_raw)
        month_key = _month_key_from_tuple(month_tuple) if month_tuple else None
        amount_decimal = _parse_decimal(raw.get("amount"))

        entry = {
            "id": raw.get("id"),
            "tipo": tipo_slug,
            "tipo_label": tipo_label,
            "descricao": raw.get("description"),
            "valor": _format_currency_br(raw.get("amount")),
            "valor_decimal": float(amount_decimal)
            if amount_decimal is not None
            else None,
            "disponibilidade": raw.get("availability") or "",
            "data_aporte": _format_date(contribution_date) if contribution_date else "",
            "data_aporte_iso": contribution_date.isoformat()
            if contribution_date
            else "",
            "observacoes": raw.get("notes") or "",
            "mes_chave": month_key or "",
        }
        entries.append(entry)

        if month_tuple:
            month_tuples.append(month_tuple)
        else:
            if contribution_raw:
                label = str(contribution_raw)
                fallback_key = _build_fallback_key(label, prefix="fonte")
                fallback_labels.append({"label": label, "key": fallback_key})
                month_key = fallback_key

        if amount_decimal is None:
            continue
        grand_total += amount_decimal
        totals_por_tipo[tipo_slug] = (
            totals_por_tipo.get(tipo_slug, Decimal("0")) + amount_decimal
        )
        if month_key:
            _accumulate_decimal(totals_per_month, month_key, amount_decimal)

        tipo_entry = per_type_map.setdefault(
            tipo_slug,
            {
                "total": Decimal("0"),
                "per_month": {},
            },
        )
        tipo_entry["total"] = tipo_entry["total"] + amount_decimal
        if month_key:
            _accumulate_decimal(tipo_entry["per_month"], month_key, amount_decimal)

    return {
        "entries": entries,
        "month_tuples": month_tuples,
        "fallback_labels": fallback_labels,
        "per_tipo": per_type_map,
        "totals_per_month": totals_per_month,
        "totals_por_tipo": totals_por_tipo,
        "grand_total": grand_total,
    }


def _normalize_sections(
    sections: Any, fallback: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    raw_list = sections if isinstance(sections, list) else fallback or []
    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        normalized.append(
            {
                "title": entry.get("title") or entry.get("nome") or entry.get("header"),
                "description": entry.get("description") or entry.get("descricao"),
                "highlights": _ensure_list(
                    entry.get("highlights") or entry.get("pontos") or []
                ),
            }
        )
    return normalized


def _resolve_deliverables(
    phase_key: str, raw_deliverables: Any
) -> List[Dict[str, str]]:
    deliverables: List[Dict[str, str]] = []
    if isinstance(raw_deliverables, list):
        for item in raw_deliverables:
            if isinstance(item, dict):
                label = item.get("label") or item.get("nome") or item.get("titulo")
                endpoint = item.get("endpoint")
                url = item.get("url")
                if label:
                    deliverables.append(
                        {"label": label, "endpoint": endpoint, "url": url}
                    )
            elif isinstance(item, str):
                deliverables.append({"label": item, "endpoint": None, "url": None})
    if not deliverables:
        deliverables = list(DEFAULT_DELIVERABLES.get(phase_key, []))
    return deliverables


def _compute_status_summary(phases: List[Dict[str, Any]]) -> Tuple[str, str, str]:
    statuses = [phase.get("status") or "sem_registros" for phase in phases]
    total = len(phases)
    concluded = sum(1 for status in statuses if status == "concluida")
    if concluded == total and total > 0:
        total_status_text = "Todas as fases concluÃ­das"
        progress_message = "ImplantaÃ§Ã£o pronta para apresentaÃ§Ã£o final."
    elif concluded > 0:
        total_status_text = f"{concluded} de {total} fases concluÃ­das"
        progress_message = (
            "Continue concluindo as prÃ³ximas macro fases para evoluir a implantaÃ§Ã£o."
        )
    else:
        total_status_text = "Nenhuma fase concluÃ­da"
        progress_message = (
            "Inicie pela fase de alinhamento para dar ritmo ao planejamento."
        )
    return total_status_text, progress_message, statuses


def build_plan_context(db, plan_id: int) -> Dict[str, Any]:
    plan_record = db.get_plan_with_company(plan_id) or {}
    dashboard_record = db.get_implantation_dashboard(plan_id) or {}

    last_update_reference = (
        dashboard_record.get("updated_at")
        or plan_record.get("updated_at")
        or datetime.now()
    )
    status = plan_record.get("status") or "Em andamento"

    actual_plan_id = plan_record.get("id") or plan_id
    return {
        "id": actual_plan_id,  # Adicionar id tambÃ©m (usado em templates)
        "plan_id": actual_plan_id,
        "company_id": plan_record.get("company_id"),
        "plan_name": plan_record.get("name") or "ImplantaÃ§Ã£o do NegÃ³cio",
        "company_name": plan_record.get("company_name") or "Empresa nÃ£o informada",
        "status": status.capitalize() if isinstance(status, str) else status,
        "version": plan_record.get("version") or "v1.0",
        "consultant": plan_record.get("owner") or "Consultor responsÃ¡vel",
        "sponsor": plan_record.get("sponsor") or "Patrocinador",
        "last_update": _format_date(last_update_reference),
        "next_checkpoint": dashboard_record.get("next_focus") or "Checkpoint a definir",
        "plan_mode": (plan_record.get("plan_mode") or "evolucao").lower(),
        "project_link": None,
    }


def _generate_model_summary_sections(db, plan_id: int) -> List[Dict[str, Any]]:
    """Generate dynamic summary sections for Model & Market phase based on actual data"""
    segments = db.list_plan_segments(plan_id)

    if not segments:
        return []

    total_segments = len(segments)
    total_personas = sum(len(seg.get("personas", [])) for seg in segments)
    total_competitors = sum(len(seg.get("competitors_matrix", [])) for seg in segments)

    sections = []

    # Resumo geral
    sections.append(
        {
            "title": "Resumo Geral",
            "description": f"{total_segments} segmento(s) de negÃ³cio mapeado(s) com propostas de valor definidas.",
            "highlights": [
                f"{total_personas} persona(s) detalhada(s)",
                f"{total_competitors} critÃ©rio(s) competitivo(s) analisado(s)",
                "EstratÃ©gia de posicionamento por segmento",
            ],
        }
    )

    # Detalhes por segmento
    for segment in segments[:3]:  # Mostrar atÃ© 3 segmentos no resumo
        seg_personas = len(segment.get("personas", []))
        seg_differentials = len(segment.get("differentials", []))

        highlights = []
        if seg_personas > 0:
            highlights.append(f"{seg_personas} persona(s)")
        if seg_differentials > 0:
            highlights.append(f"{seg_differentials} diferencial(is)")

        strategy = segment.get("strategy", {})
        value_prop = strategy.get("value_proposition", {})
        if value_prop.get("solution"):
            highlights.append("Proposta de valor definida")

        sections.append(
            {
                "title": segment.get("name", "Segmento"),
                "description": segment.get("description", ""),
                "highlights": highlights if highlights else ["Em desenvolvimento"],
            }
        )

    if total_segments > 3:
        sections.append(
            {
                "title": "Outros Segmentos",
                "description": f"+ {total_segments - 3} segmento(s) adicional(is)",
                "highlights": [],
            }
        )

    return sections


def build_overview_payload(db, plan_id: int) -> Dict[str, Any]:
    plan = build_plan_context(db, plan_id)
    dashboard_record = db.get_implantation_dashboard(plan_id) or {}

    phases_raw = {
        row.get("phase_key"): row for row in db.list_implantation_phases(plan_id)
    }
    macro_phases: List[Dict[str, Any]] = []

    for key in PHASE_ORDER:
        stored = phases_raw.get(key, {}) or {}
        defaults = PHASE_DEFAULTS.get(key, {})
        normalized_sections = _normalize_sections(
            stored.get("sections"), defaults.get("sections")
        )

        # Gerar resumo dinÃ¢mico para fase "model" baseado em dados reais
        if key == "model" and not normalized_sections:
            normalized_sections = _generate_model_summary_sections(db, plan_id)

        macro_phases.append(
            {
                "id": key,
                "phase_key": key,
                "title": stored.get("title") or defaults.get("title"),
                "status": stored.get("status") or "sem_registros",
                "tagline": stored.get("tagline") or defaults.get("tagline"),
                "pulse": stored.get("pulse") or defaults.get("pulse"),
                "sections": normalized_sections,
                "deliverables": _resolve_deliverables(key, stored.get("deliverables")),
            }
        )

    checkpoints = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "status": item.get("status") or "upcoming",
            "date": item.get("date") or item.get("date_label"),
        }
        for item in db.list_implantation_checkpoints(plan_id)
    ]

    total_status_text, computed_progress_message, statuses = _compute_status_summary(
        macro_phases
    )

    next_focus_phase = next(
        (phase for phase in macro_phases if phase.get("status") != "concluida"), None
    )
    next_focus = dashboard_record.get("next_focus") or (
        next_focus_phase["title"] if next_focus_phase else "ImplantaÃ§Ã£o concluÃ­da"
    )
    next_focus_details = dashboard_record.get("next_focus_details") or (
        next_focus_phase.get("tagline")
        if next_focus_phase
        else "Todas as macro fases foram finalizadas."
    )

    dashboard = {
        "total_status": total_status_text,
        "progress_message": dashboard_record.get("progress_message")
        or computed_progress_message,
        "next_focus": next_focus,
        "next_focus_details": next_focus_details,
        "general_note": dashboard_record.get("general_note")
        or "Status geral atualizado",
        "general_details": dashboard_record.get("general_details")
        or "Utilize os botÃµes de conclusÃ£o para registrar o andamento de cada macro fase.",
        "statuses": statuses,
    }

    return {
        "plan": plan,
        "macro_phases": macro_phases,
        "checkpoints": checkpoints,
        "dashboard": dashboard,
    }


def load_alignment_canvas(db, plan_id: int) -> Dict[str, Any]:
    members = db.list_alignment_members(plan_id)
    overview = db.get_alignment_overview(plan_id) or {}
    principles_records = db.list_alignment_principles(plan_id)

    socios = [
        {
            "id": member.get("id"),
            "nome": member.get("name"),
            "papel": member.get("role"),
            "motivacao": member.get("motivation"),
            "compromisso": member.get("commitment"),
            "risco": member.get("risk"),
        }
        for member in members
    ]

    criterios = overview.get("decision_criteria") or []
    if isinstance(principles_records, list) and not criterios:
        criterios = [
            item.get("principle")
            for item in principles_records
            if item.get("principle")
        ]

    alinhamento = {
        "visao_compartilhada": overview.get("shared_vision"),
        "metas_financeiras": overview.get("financial_goals"),
        "criterios_decisao": criterios,
        "notas": overview.get("notes"),
    }

    return {
        "socios": socios,
        "alinhamento": alinhamento,
    }


def load_alignment_project(db, plan_id: int) -> Dict[str, Any]:
    """
    Carrega informaÃ§Ãµes do projeto de alinhamento
    Busca projeto GRV vinculado atravÃ©s do plan_id
    """
    import json
    from database.postgres_helper import connect as pg_connect

    project = db.get_alignment_project(plan_id) or {}
    observacoes = project.get("observations") or []
    if isinstance(observacoes, dict):
        observacoes = observacoes.get("itens") or list(observacoes.values())
    if not isinstance(observacoes, list):
        observacoes = [observacoes] if observacoes else []

    nome = project.get("project_name") or "PEV - Planejamento | Agenda do Planejamento"
    descricao = project.get("description")
    codigo = None
    atividades_grv = []
    grv_project_id = None
    company_id = None

    # Buscar projeto GRV vinculado (onde plan_id = este plan_id e plan_type = 'PEV')
    try:
        conn = pg_connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, title, description, activities, company_id
            FROM company_projects
            WHERE plan_id = %s AND plan_type = 'PEV'
            LIMIT 1
        """,
            (plan_id,),
        )

        grv_row = cursor.fetchone()
        conn.close()

        if grv_row:
            grv_project = dict(grv_row)
            grv_project_id = grv_project.get("id")
            company_id = grv_project.get("company_id")
            codigo = grv_project.get("code")
            nome = grv_project.get("title") or nome
            descricao = grv_project.get("description") or descricao

            # Buscar atividades do projeto GRV
            activities_json = grv_project.get("activities")
            if activities_json:
                if isinstance(activities_json, str):
                    try:
                        atividades_grv = json.loads(activities_json)
                    except Exception as exc:
                        atividades_grv = []
                elif isinstance(activities_json, list):
                    atividades_grv = activities_json

    except Exception as e:
        logger.info(
            f"[load_alignment_project] Erro ao buscar projeto GRV para plan_id {plan_id}: {e}"
        )
        import traceback

        traceback.print_exc()

    return {
        "nome": nome,
        "codigo": codigo,
        "descricao": descricao,
        "observacoes": observacoes,
        "grv_project_id": grv_project_id,
        "company_id": company_id,
        "atividades_grv": atividades_grv,
    }


def load_alignment_agenda(db, plan_id: int) -> Dict[str, Any]:
    project = load_alignment_project(db, plan_id)
    agenda_records = db.list_alignment_agenda(plan_id)
    atividades = [
        {
            "oque": item.get("action_title"),
            "quem": item.get("owner_name"),
            "quando": item.get("schedule_info"),
            "como": item.get("execution_info"),
        }
        for item in agenda_records
    ]
    return {"projeto": project, "atividades": atividades}


def load_segments(db, plan_id: int) -> List[Dict[str, Any]]:
    segments = db.list_plan_segments(plan_id)
    prepared: List[Dict[str, Any]] = []
    for record in segments:
        strategy = _ensure_dict(record.get("strategy"))
        value_prop = _ensure_dict(strategy.get("value_proposition"))
        monetization = _ensure_dict(strategy.get("monetization"))
        personas = _ensure_list(record.get("personas"))
        for persona in personas:
            if isinstance(persona, dict):
                persona.setdefault(
                    "jornada", persona.get("jornada") or persona.get("journey") or []
                )
        prepared.append(
            {
                "id": record.get("id"),
                "nome": record.get("name"),
                "descricao": record.get("description"),
                "audiences": _ensure_list(record.get("audiences")),
                "differentials": _ensure_list(record.get("differentials")),
                "evidences": _ensure_list(record.get("evidences")),
                "personas": personas,
                "strategy": strategy,
                "value_proposition": value_prop,
                "monetization": monetization,
                "competitive_matrix": _ensure_list(
                    record.get("competitors_matrix")
                    or strategy.get("competitive_matrix")
                ),
                "journey_triggers": _ensure_dict(strategy.get("journey_triggers")),
                "persona_overview": strategy.get("persona_overview")
                or strategy.get("persona_description"),
                "positioning": _ensure_dict(strategy.get("positioning")),
            }
        )
    return prepared


def build_value_canvas_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for segment in segments:
        value_prop = segment.get("value_proposition", {})
        monetization = segment.get("monetization", {})
        data.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "descricao": segment.get("descricao"),
                "proposta": {
                    "segmentos": segment.get("audiences") or [],
                    "problemas": value_prop.get("problems")
                    or value_prop.get("dor")
                    or [],
                    "solucao": value_prop.get("solution") or value_prop.get("solucao"),
                    "diferenciais": segment.get("differentials") or [],
                    "provas": segment.get("evidences") or [],
                },
                "monetizacao": {
                    "fontes_receita": monetization.get("revenue_streams")
                    or monetization.get("receitas")
                    or [],
                    "estrutura_custos": monetization.get("cost_structure")
                    or monetization.get("custos")
                    or [],
                    "parcerias_chave": monetization.get("key_partners")
                    or monetization.get("parcerias")
                    or [],
                },
            }
        )
    return data


def build_persona_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    persona_segments: List[Dict[str, Any]] = []
    for segment in segments:
        triggers = segment.get("journey_triggers") or {}
        persona_segments.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "persona_descricao": segment.get("persona_overview"),
                "personas": segment.get("personas") or [],
                "gatilhos": triggers,
            }
        )
    return persona_segments


def _prepare_segment_products(
    raw_products: List[Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    total_units = Decimal("0")
    total_revenue = Decimal("0")
    total_cost_value = Decimal("0")
    total_expense_value = Decimal("0")
    total_margin_value = Decimal("0")
    total_goal_units = Decimal("0")

    units_has_data = False
    revenue_has_data = False
    cost_has_data = False
    expense_has_data = False
    margin_has_data = False
    goal_units_has_data = False

    goal_percent_sum = Decimal("0")
    goal_percent_weight = Decimal("0")

    def _extract_decimal_from(source: Any, keys: List[str]) -> Optional[Decimal]:
        if not isinstance(source, dict):
            return None
        for key in keys:
            if key not in source:
                continue
            decimal_candidate = _parse_decimal(source.get(key))
            if decimal_candidate is not None:
                return decimal_candidate
        return None

    def _extract_text_from(source: Any, keys: List[str]) -> Optional[str]:
        if not isinstance(source, dict):
            return None
        for key in keys:
            if key not in source:
                continue
            value = source.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
            elif value is not None:
                cleaned = str(value).strip()
                if cleaned:
                    return cleaned
        return None

    for product in raw_products:
        if not isinstance(product, dict):
            continue

        nome_produto = product.get("name") or product.get("nome") or "Produto"

        sale_price_raw = (
            product.get("sale_price")
            or product.get("preco_venda")
            or product.get("price")
            or {}
        )
        price_value = None
        price_notes = None
        if isinstance(sale_price_raw, dict):
            price_value = _extract_decimal_from(
                sale_price_raw, ["valor", "value", "amount", "price"]
            )
            price_notes = _extract_text_from(
                sale_price_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            price_value = _parse_decimal(sale_price_raw)
        if price_value is None:
            price_value = _parse_decimal(
                product.get("sale_price_value")
                or product.get("preco_venda_valor")
                or product.get("precoVendaValor")
            )
        if price_notes is None:
            price_notes = _extract_text_from(
                product,
                [
                    "preco_venda_observacoes",
                    "sale_price_notes",
                    "preco_venda_obs",
                    "sale_price_obs",
                ],
            )

        cost_raw = (
            product.get("variable_costs")
            or product.get("custos_variaveis")
            or product.get("custosVariaveis")
            or {}
        )
        cost_value = None
        cost_percent = None
        cost_notes = None
        if isinstance(cost_raw, dict):
            cost_value = _extract_decimal_from(cost_raw, ["valor", "value", "amount"])
            cost_percent = _extract_decimal_from(
                cost_raw, ["percentual", "percent", "percentage"]
            )
            cost_notes = _extract_text_from(
                cost_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            cost_value = _parse_decimal(cost_raw)
        if cost_value is None:
            cost_value = _parse_decimal(
                product.get("custos_variaveis_valor")
                or product.get("variable_costs_value")
                or product.get("custosVariaveisValor")
            )
        if cost_percent is None:
            cost_percent = _parse_decimal(
                product.get("custos_variaveis_percentual")
                or product.get("variable_costs_percent")
                or product.get("custosVariaveisPercentual")
            )
        if cost_notes is None:
            cost_notes = _extract_text_from(
                product,
                [
                    "custos_variaveis_observacoes",
                    "variable_costs_notes",
                    "custosVariaveisObs",
                ],
            )
        cost_value, cost_percent = _compute_value_percent(
            cost_value, cost_percent, price_value
        )

        expense_raw = (
            product.get("variable_expenses")
            or product.get("despesas_variaveis")
            or product.get("despesasVariaveis")
            or {}
        )
        expense_value = None
        expense_percent = None
        expense_notes = None
        if isinstance(expense_raw, dict):
            expense_value = _extract_decimal_from(
                expense_raw, ["valor", "value", "amount"]
            )
            expense_percent = _extract_decimal_from(
                expense_raw, ["percentual", "percent", "percentage"]
            )
            expense_notes = _extract_text_from(
                expense_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            expense_value = _parse_decimal(expense_raw)
        if expense_value is None:
            expense_value = _parse_decimal(
                product.get("despesas_variaveis_valor")
                or product.get("variable_expenses_value")
                or product.get("despesasVariaveisValor")
            )
        if expense_percent is None:
            expense_percent = _parse_decimal(
                product.get("despesas_variaveis_percentual")
                or product.get("variable_expenses_percent")
                or product.get("despesasVariaveisPercentual")
            )
        if expense_notes is None:
            expense_notes = _extract_text_from(
                product,
                [
                    "despesas_variaveis_observacoes",
                    "variable_expenses_notes",
                    "despesasVariaveisObs",
                ],
            )
        expense_value, expense_percent = _compute_value_percent(
            expense_value, expense_percent, price_value
        )

        margin_raw = (
            product.get("contribution_margin")
            or product.get("margem_contribuicao")
            or {}
        )
        margin_value = None
        margin_percent = None
        margin_notes = None
        if isinstance(margin_raw, dict):
            margin_value = _extract_decimal_from(
                margin_raw, ["valor", "value", "amount"]
            )
            margin_percent = _extract_decimal_from(
                margin_raw, ["percentual", "percent", "percentage"]
            )
            margin_notes = _extract_text_from(
                margin_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            margin_value = _parse_decimal(margin_raw)
        if margin_value is None:
            margin_value = _parse_decimal(
                product.get("margem_contribuicao_valor")
                or product.get("contribution_margin_value")
                or product.get("margemContribuicaoValor")
            )
        if margin_percent is None:
            margin_percent = _parse_decimal(
                product.get("margem_contribuicao_percentual")
                or product.get("contribution_margin_percent")
                or product.get("margemContribuicaoPercentual")
            )
        if margin_notes is None:
            margin_notes = _extract_text_from(
                product,
                [
                    "margem_contribuicao_observacoes",
                    "contribution_margin_notes",
                    "margemContribuicaoObs",
                ],
            )
        margin_value, margin_percent = _compute_value_percent(
            margin_value, margin_percent, price_value
        )
        if margin_value is None and price_value is not None:
            subtotal = Decimal("0")
            if cost_value is not None:
                subtotal += cost_value
            if expense_value is not None:
                subtotal += expense_value
            margin_value = price_value - subtotal
        if (
            margin_percent is None
            and margin_value is not None
            and price_value not in (None, Decimal("0"))
        ):
            margin_percent = (margin_value / price_value) * Decimal("100")

        market_raw = (
            product.get("market_size")
            or product.get("mercado")
            or product.get("market")
            or {}
        )
        market_units = None
        market_revenue = None
        market_notes = None
        if isinstance(market_raw, dict):
            market_units = _extract_decimal_from(
                market_raw, ["unidades_mensais", "monthly_units", "units"]
            )
            market_revenue = _extract_decimal_from(
                market_raw, ["faturamento_mensal", "monthly_revenue", "revenue"]
            )
            market_notes = _extract_text_from(
                market_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            market_units = _parse_decimal(market_raw)
        if market_units is None:
            market_units = _parse_decimal(
                product.get("mercado_unidades_mensais")
                or product.get("market_monthly_units")
                or product.get("monthly_units")
            )
        if market_revenue is None:
            market_revenue = _parse_decimal(
                product.get("mercado_faturamento_mensal")
                or product.get("market_monthly_revenue")
                or product.get("monthly_revenue")
            )
        if market_notes is None:
            market_notes = _extract_text_from(
                product,
                [
                    "mercado_observacoes",
                    "market_size_notes",
                    "mercadoObs",
                ],
            )
        if (
            market_revenue is None
            and market_units is not None
            and price_value is not None
        ):
            market_revenue = price_value * market_units

        share_raw = (
            product.get("marketing_share_goal")
            or product.get("market_share_goal")
            or product.get("meta_market_share")
            or {}
        )
        share_units = None
        share_percent = None
        share_notes = None
        if isinstance(share_raw, dict):
            share_units = _extract_decimal_from(
                share_raw, ["unidades_mensais", "monthly_units", "units"]
            )
            share_percent = _extract_decimal_from(
                share_raw, ["percentual", "percent", "percentage", "market_share"]
            )
            share_notes = _extract_text_from(
                share_raw, ["observacoes", "observacao", "obs", "notes"]
            )
        else:
            share_units = _parse_decimal(share_raw)
        if share_units is None:
            share_units = _parse_decimal(
                product.get("meta_market_share_unidades_mensais")
                or product.get("market_share_monthly_units")
            )
        if share_percent is None:
            share_percent = _parse_decimal(
                product.get("meta_market_share_percentual")
                or product.get("market_share_percent")
            )
        if share_notes is None:
            share_notes = _extract_text_from(
                product,
                [
                    "meta_market_share_observacoes",
                    "market_share_notes",
                    "metaMarketShareObs",
                ],
            )
        if (
            share_units is None
            and share_percent is not None
            and market_units
            not in (
                None,
                Decimal("0"),
            )
        ):
            share_units = (share_percent / Decimal("100")) * market_units
        if (
            share_percent is None
            and share_units is not None
            and market_units
            not in (
                None,
                Decimal("0"),
            )
        ):
            share_percent = (share_units / market_units) * Decimal("100")

        product_notes = _extract_text_from(product, ["observacoes", "notes"])

        cost_monthly_value = None
        if cost_value is not None and market_units is not None:
            cost_monthly_value = cost_value * market_units
            cost_has_data = True
        expense_monthly_value = None
        if expense_value is not None and market_units is not None:
            expense_monthly_value = expense_value * market_units
            expense_has_data = True
        margin_monthly_value = None
        if margin_value is not None and market_units is not None:
            margin_monthly_value = margin_value * market_units
            margin_has_data = True

        if market_units is not None:
            total_units += market_units
            units_has_data = True
        if market_revenue is not None:
            total_revenue += market_revenue
            revenue_has_data = True
        if cost_monthly_value is not None:
            total_cost_value += cost_monthly_value
        if expense_monthly_value is not None:
            total_expense_value += expense_monthly_value
        if margin_monthly_value is not None:
            total_margin_value += margin_monthly_value
        if share_units is not None:
            total_goal_units += share_units
            goal_units_has_data = True
        if share_percent is not None:
            if market_units is not None and market_units > 0:
                goal_percent_sum += share_percent * market_units
                goal_percent_weight += market_units
            else:
                goal_percent_sum += share_percent
                goal_percent_weight += Decimal("1")

        prepared.append(
            {
                "nome": nome_produto,
                "observacoes": product_notes,
                "preco_venda": {
                    "valor": price_value,
                    "valor_formatado": _format_currency_br(price_value),
                    "observacoes": price_notes,
                },
                "custos_variaveis": {
                    "valor": cost_value,
                    "valor_formatado": _format_currency_br(cost_value),
                    "percentual": cost_percent,
                    "percentual_formatado": _format_percentage_br(cost_percent),
                    "total_mensal": cost_monthly_value,
                    "total_mensal_formatado": _format_currency_br(cost_monthly_value),
                    "observacoes": cost_notes,
                },
                "despesas_variaveis": {
                    "valor": expense_value,
                    "valor_formatado": _format_currency_br(expense_value),
                    "percentual": expense_percent,
                    "percentual_formatado": _format_percentage_br(expense_percent),
                    "total_mensal": expense_monthly_value,
                    "total_mensal_formatado": _format_currency_br(
                        expense_monthly_value
                    ),
                    "observacoes": expense_notes,
                },
                "margem_contribuicao": {
                    "valor": margin_value,
                    "valor_formatado": _format_currency_br(margin_value),
                    "percentual": margin_percent,
                    "percentual_formatado": _format_percentage_br(margin_percent),
                    "total_mensal": margin_monthly_value,
                    "total_mensal_formatado": _format_currency_br(margin_monthly_value),
                    "observacoes": margin_notes,
                },
                "mercado": {
                    "unidades_mensais": market_units,
                    "unidades_mensais_formatado": _format_number_br(market_units),
                    "faturamento_mensal": market_revenue,
                    "faturamento_mensal_formatado": _format_currency_br(market_revenue),
                    "observacoes": market_notes,
                },
                "meta_market_share": {
                    "unidades_mensais": share_units,
                    "unidades_mensais_formatado": _format_number_br(share_units),
                    "percentual": share_percent,
                    "percentual_formatado": _format_percentage_br(share_percent),
                    "observacoes": share_notes,
                },
            }
        )

    totals_units_value: Optional[Decimal] = total_units if units_has_data else None
    totals_revenue_value: Optional[Decimal] = (
        total_revenue if revenue_has_data else None
    )
    totals_cost_value: Optional[Decimal] = total_cost_value if cost_has_data else None
    totals_expense_value: Optional[Decimal] = (
        total_expense_value if expense_has_data else None
    )
    totals_margin_value: Optional[Decimal] = (
        total_margin_value if margin_has_data else None
    )
    totals_goal_units_value: Optional[Decimal] = (
        total_goal_units if goal_units_has_data else None
    )

    if totals_margin_value is None and revenue_has_data:
        inferred_margin = total_revenue
        if cost_has_data:
            inferred_margin -= total_cost_value
        if expense_has_data:
            inferred_margin -= total_expense_value
        totals_margin_value = inferred_margin
        margin_has_data = True

    cost_percent_total: Optional[Decimal] = None
    if (
        totals_revenue_value not in (None, Decimal("0"))
        and totals_cost_value is not None
    ):
        cost_percent_total = (totals_cost_value / totals_revenue_value) * Decimal("100")

    expense_percent_total: Optional[Decimal] = None
    if (
        totals_revenue_value not in (None, Decimal("0"))
        and totals_expense_value is not None
    ):
        expense_percent_total = (totals_expense_value / totals_revenue_value) * Decimal(
            "100"
        )

    margin_percent_total: Optional[Decimal] = None
    if (
        totals_revenue_value not in (None, Decimal("0"))
        and totals_margin_value is not None
    ):
        margin_percent_total = (totals_margin_value / totals_revenue_value) * Decimal(
            "100"
        )

    goal_percent_total: Optional[Decimal] = None
    if totals_goal_units_value is not None and totals_units_value not in (
        None,
        Decimal("0"),
    ):
        goal_percent_total = (totals_goal_units_value / totals_units_value) * Decimal(
            "100"
        )
    elif goal_percent_weight not in (None, Decimal("0")):
        goal_percent_total = goal_percent_sum / goal_percent_weight

    totals = {
        "produtos_registrados": len(prepared),
        "unidades_mensais": {
            "valor": totals_units_value,
            "valor_formatado": _format_number_br(totals_units_value),
        },
        "faturamento_mensal": {
            "valor": totals_revenue_value,
            "valor_formatado": _format_currency_br(totals_revenue_value),
        },
        "custos_variaveis": {
            "valor": totals_cost_value,
            "valor_formatado": _format_currency_br(totals_cost_value),
            "percentual": cost_percent_total,
            "percentual_formatado": _format_percentage_br(cost_percent_total),
        },
        "despesas_variaveis": {
            "valor": totals_expense_value,
            "valor_formatado": _format_currency_br(totals_expense_value),
            "percentual": expense_percent_total,
            "percentual_formatado": _format_percentage_br(expense_percent_total),
        },
        "margem_contribuicao": {
            "valor": totals_margin_value,
            "valor_formatado": _format_currency_br(totals_margin_value),
            "percentual": margin_percent_total,
            "percentual_formatado": _format_percentage_br(margin_percent_total),
        },
        "meta_market_share": {
            "unidades_mensais": {
                "valor": totals_goal_units_value,
                "valor_formatado": _format_number_br(totals_goal_units_value),
            },
            "percentual": goal_percent_total,
            "percentual_formatado": _format_percentage_br(goal_percent_total),
        },
    }

    return prepared, totals


def build_competitive_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    comp_segments: List[Dict[str, Any]] = []
    for segment in segments:
        positioning = segment.get("positioning") or {}
        raw_products_source = segment.get("strategy") or {}
        raw_products = []
        if isinstance(raw_products_source, dict):
            raw_products = _ensure_list(
                raw_products_source.get("products")
                or raw_products_source.get("produtos")
                or []
            )
        if not raw_products:
            raw_products = _ensure_list(segment.get("products"))
        prepared_products, products_totals = _prepare_segment_products(raw_products)
        comp_segments.append(
            {
                "id": segment.get("id"),
                "nome": segment.get("nome"),
                "descricao": segment.get("descricao"),
                "matriz": segment.get("competitive_matrix") or [],
                "estrategia": {
                    "posicionamento": positioning.get("narrative")
                    or positioning.get("posicionamento"),
                    "promessa": positioning.get("promise")
                    or positioning.get("promessa"),
                    "proximos_passos": positioning.get("next_steps")
                    or positioning.get("proximos_passos")
                    or [],
                },
                "proposta": {
                    "publico": segment.get("audiences") or [],
                    "diferenciais": segment.get("differentials") or [],
                    "comprobacoes": segment.get("evidences") or [],
                },
                "personas": segment.get("personas") or [],
                "produtos": prepared_products,
                "produtos_totais": products_totals,
            }
        )
    return comp_segments


def load_structures(db, plan_id: int) -> List[Dict[str, Any]]:
    rows = db.list_plan_structures(plan_id)
    installments = db.list_plan_structure_installments(plan_id)
    capacities = db.list_plan_structure_capacities(plan_id)

    installments_map: Dict[int, List[Dict[str, Any]]] = {}
    for inst in installments:
        structure_id = inst.get("structure_id")
        installments_map.setdefault(structure_id, []).append(
            {
                "numero": inst.get("installment_number"),
                "valor": inst.get("amount"),
                "vencimento": inst.get("due_info"),
                "tipo": inst.get("installment_type"),
                "classificacao": inst.get("classification"),
                "repeticao": inst.get("repetition"),
            }
        )

    area_map: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        area_key_raw = (row.get("area") or "").lower()
        area_name = AREA_LABELS.get(area_key_raw, row.get("area") or "Outros")

        block_key_raw = (row.get("block") or "").lower().replace(" ", "_")
        block_name = BLOCK_LABELS.get(block_key_raw, row.get("block") or "Outros")

        area_entry = area_map.setdefault(
            area_name,
            {
                "id": area_key_raw or area_name.lower().replace(" ", "_"),
                "codigo": area_key_raw or area_name.lower().replace(" ", "_"),
                "nome": area_name,
                "blocos": {},
            },
        )

        blocos = area_entry["blocos"]
        bloco_entry = blocos.setdefault(
            block_name,
            {
                "nome": block_name,
                "itens": [],
            },
        )

        structure_id = row.get("id")
        parcelas = installments_map.get(structure_id, [])
        payment_form = row.get("payment_form") or (
            "Conforme parcelas" if parcelas else "A definir"
        )
        bloco_entry["itens"].append(
            {
                "id": structure_id,
                "tipo": row.get("item_type"),
                "descricao": row.get("description"),
                "valor": row.get("value"),
                "repeticao": row.get("repetition"),
                "forma_pagamento": payment_form,
                "data_aquisicao": row.get("acquisition_info"),
                "fornecedor": row.get("supplier"),
                "data_disponibilizacao": row.get("availability_info"),
                "observacoes": row.get("observations"),
                "status": row.get("status"),
                "parcelas": parcelas,
            }
        )

    for cap in capacities:
        area_key_raw = (cap.get("area") or "").lower()
        area_name = AREA_LABELS.get(area_key_raw, cap.get("area") or "Outros")
        area_entry = area_map.get(area_name)
        if not area_entry:
            area_entry = {
                "id": area_key_raw or area_name.lower().replace(" ", "_"),
                "codigo": area_key_raw or area_name.lower().replace(" ", "_"),
                "nome": area_name,
                "blocos": {},
            }
            area_map[area_name] = area_entry
        raw_capacity = cap.get("revenue_capacity")
        area_entry["capacidade"] = raw_capacity
        area_entry["capacidade_formatada"] = _format_currency_br(raw_capacity)
        area_entry["capacidade_observacoes"] = cap.get("observations")
        area_entry["capacidade_id"] = cap.get("id")
        decimal_value = _parse_decimal(raw_capacity)
        area_entry["capacidade_valor_decimal"] = (
            float(decimal_value) if decimal_value is not None else None
        )
        if area_key_raw:
            area_entry["codigo"] = area_key_raw
            area_entry["id"] = area_key_raw

    # Garante que as principais areas aparecam mesmo sem itens cadastrados
    for default_area_key in ("comercial", "operacional", "adm_fin"):
        area_name = AREA_LABELS.get(default_area_key)
        if area_name and area_name not in area_map:
            area_map[area_name] = {
                "id": default_area_key,
                "codigo": default_area_key,
                "nome": area_name,
                "blocos": {},
            }

    ordered_areas: List[Dict[str, Any]] = []
    for area_name in AREA_ORDER:
        if area_name in area_map:
            ordered_areas.append(area_map.pop(area_name))
    ordered_areas.extend(area_map.values())

    # Convert bloco dicts to sorted lists
    for area in ordered_areas:
        blocos_dict = area.get("blocos", {})
        blocos_list = list(blocos_dict.values())
        area["blocos"] = blocos_list

    return ordered_areas


def calculate_investment_summary_by_block(
    structures: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Calcula resumo de investimentos agrupados por bloco estruturante.

    Usa as classificaÃ§Ãµes das parcelas para categorizar:
    - Investimentos (classificaÃ§Ã£o = "Investimento")
    - Custos Fixos Mensais/Anuais (classificaÃ§Ã£o = "Custo Fixo")
    - Despesas Fixas Mensais/Anuais (classificaÃ§Ã£o = "Despesa Fixa")
    """
    from decimal import Decimal

    # Inicializar totais por bloco
    blocos_totais: Dict[str, Dict[str, Decimal]] = {}

    # Lista de blocos na ordem desejada
    blocos_ordem = [
        "Pessoas",
        "ImÃ³veis",
        "InstalaÃ§Ãµes",
        "MÃ¡quinas e Equipamentos",
        "MÃ³veis e UtensÃ­lios",
        "TI e ComunicaÃ§Ã£o",
        "Outros",
    ]

    for area in structures:
        for bloco in area.get("blocos", []):
            bloco_nome = bloco.get("nome", "Outros")

            if bloco_nome not in blocos_totais:
                blocos_totais[bloco_nome] = {
                    "investimentos": Decimal("0"),
                    "custos_fixos_mensal": Decimal("0"),
                    "despesas_fixas_mensal": Decimal("0"),
                    "custos_fixos_anual": Decimal("0"),
                    "despesas_fixas_anual": Decimal("0"),
                }

            for item in bloco.get("itens", []):
                parcelas = item.get("parcelas", [])

                # Processar cada parcela individualmente
                for parcela in parcelas:
                    valor_str = parcela.get("valor", "")
                    valor = _parse_decimal(valor_str) or Decimal("0")
                    classification = _classify_structure_installment(
                        bloco_nome, parcela
                    )
                    classificacao_norm = classification["classificacao_norm"]
                    repeticao = classification["repeticao_norm"]

                    # Classificar baseado na classificaÃ§Ã£o da parcela
                    if classificacao_norm == "investimento":
                        # Investimentos (independente da repetiÃ§Ã£o)
                        blocos_totais[bloco_nome]["investimentos"] += valor

                    elif classificacao_norm == "custo fixo":
                        # Custos Fixos
                        if repeticao == "mensal":
                            blocos_totais[bloco_nome]["custos_fixos_mensal"] += valor
                        elif repeticao == "anual":
                            blocos_totais[bloco_nome]["custos_fixos_anual"] += valor
                        elif repeticao == "trimestral":
                            # Converter trimestral para mensal (divide por 3)
                            blocos_totais[bloco_nome][
                                "custos_fixos_mensal"
                            ] += valor / Decimal("3")
                        elif repeticao == "semestral":
                            # Converter semestral para mensal (divide por 6)
                            blocos_totais[bloco_nome][
                                "custos_fixos_mensal"
                            ] += valor / Decimal("6")
                        elif repeticao in ["unica", ""]:
                            # Se for Ãºnica ou sem repetiÃ§Ã£o, nÃ£o conta como recorrente
                            pass

                    elif classificacao_norm == "despesa fixa":
                        # Despesas Fixas
                        if repeticao == "mensal":
                            blocos_totais[bloco_nome]["despesas_fixas_mensal"] += valor
                        elif repeticao == "anual":
                            blocos_totais[bloco_nome]["despesas_fixas_anual"] += valor
                        elif repeticao == "trimestral":
                            # Converter trimestral para mensal (divide por 3)
                            blocos_totais[bloco_nome][
                                "despesas_fixas_mensal"
                            ] += valor / Decimal("3")
                        elif repeticao == "semestral":
                            # Converter semestral para mensal (divide por 6)
                            blocos_totais[bloco_nome][
                                "despesas_fixas_mensal"
                            ] += valor / Decimal("6")
                        elif repeticao in ["unica", ""]:
                            # Se for Ãºnica ou sem repetiÃ§Ã£o, nÃ£o conta como recorrente
                            pass

    # Preparar lista de resultados ordenada
    resultado = []

    # Primeiro, adicionar blocos na ordem especificada
    for bloco_nome in blocos_ordem:
        if bloco_nome in blocos_totais:
            totais = blocos_totais[bloco_nome]

            # Calcular totais
            total_gastos_mensal = (
                totais["custos_fixos_mensal"] + totais["despesas_fixas_mensal"]
            )
            total_gastos_anual = (
                totais["custos_fixos_anual"]
                + totais["despesas_fixas_anual"]
                + (total_gastos_mensal * Decimal("12"))
            )

            resultado.append(
                {
                    "bloco": bloco_nome,
                    "investimentos": totais["investimentos"],
                    "investimentos_formatado": _format_currency_br(
                        totais["investimentos"]
                    ),
                    "custos_fixos_mensal": totais["custos_fixos_mensal"],
                    "custos_fixos_mensal_formatado": _format_currency_br(
                        totais["custos_fixos_mensal"]
                    ),
                    "despesas_fixas_mensal": totais["despesas_fixas_mensal"],
                    "despesas_fixas_mensal_formatado": _format_currency_br(
                        totais["despesas_fixas_mensal"]
                    ),
                    "total_gastos_mensal": total_gastos_mensal,
                    "total_gastos_mensal_formatado": _format_currency_br(
                        total_gastos_mensal
                    ),
                    "custos_fixos_anual": totais["custos_fixos_anual"],
                    "custos_fixos_anual_formatado": _format_currency_br(
                        totais["custos_fixos_anual"]
                    ),
                    "despesas_fixas_anual": totais["despesas_fixas_anual"],
                    "despesas_fixas_anual_formatado": _format_currency_br(
                        totais["despesas_fixas_anual"]
                    ),
                    "total_gastos_anual": total_gastos_anual,
                    "total_gastos_anual_formatado": _format_currency_br(
                        total_gastos_anual
                    ),
                }
            )
            blocos_totais.pop(bloco_nome)

    # Adicionar blocos restantes (se houver)
    for bloco_nome, totais in sorted(blocos_totais.items()):
        total_gastos_mensal = (
            totais["custos_fixos_mensal"] + totais["despesas_fixas_mensal"]
        )
        total_gastos_anual = (
            totais["custos_fixos_anual"]
            + totais["despesas_fixas_anual"]
            + (total_gastos_mensal * Decimal("12"))
        )

        resultado.append(
            {
                "bloco": bloco_nome,
                "investimentos": totais["investimentos"],
                "investimentos_formatado": _format_currency_br(totais["investimentos"]),
                "custos_fixos_mensal": totais["custos_fixos_mensal"],
                "custos_fixos_mensal_formatado": _format_currency_br(
                    totais["custos_fixos_mensal"]
                ),
                "despesas_fixas_mensal": totais["despesas_fixas_mensal"],
                "despesas_fixas_mensal_formatado": _format_currency_br(
                    totais["despesas_fixas_mensal"]
                ),
                "total_gastos_mensal": total_gastos_mensal,
                "total_gastos_mensal_formatado": _format_currency_br(
                    total_gastos_mensal
                ),
                "custos_fixos_anual": totais["custos_fixos_anual"],
                "custos_fixos_anual_formatado": _format_currency_br(
                    totais["custos_fixos_anual"]
                ),
                "despesas_fixas_anual": totais["despesas_fixas_anual"],
                "despesas_fixas_anual_formatado": _format_currency_br(
                    totais["despesas_fixas_anual"]
                ),
                "total_gastos_anual": total_gastos_anual,
                "total_gastos_anual_formatado": _format_currency_br(total_gastos_anual),
            }
        )

    # Adicionar linha de totais
    total_investimentos = sum(r["investimentos"] for r in resultado)
    total_custos_mensal = sum(r["custos_fixos_mensal"] for r in resultado)
    total_despesas_mensal = sum(r["despesas_fixas_mensal"] for r in resultado)
    total_gastos_mensal = total_custos_mensal + total_despesas_mensal
    total_custos_anual = sum(r["custos_fixos_anual"] for r in resultado)
    total_despesas_anual = sum(r["despesas_fixas_anual"] for r in resultado)
    # Soma os totais anuais jÃ¡ calculados de cada bloco (que jÃ¡ incluem mensais Ã— 12)
    total_gastos_anual = sum(r["total_gastos_anual"] for r in resultado)

    resultado.append(
        {
            "bloco": "TOTAL",
            "investimentos": total_investimentos,
            "investimentos_formatado": _format_currency_br(total_investimentos),
            "custos_fixos_mensal": total_custos_mensal,
            "custos_fixos_mensal_formatado": _format_currency_br(total_custos_mensal),
            "despesas_fixas_mensal": total_despesas_mensal,
            "despesas_fixas_mensal_formatado": _format_currency_br(
                total_despesas_mensal
            ),
            "total_gastos_mensal": total_gastos_mensal,
            "total_gastos_mensal_formatado": _format_currency_br(total_gastos_mensal),
            "custos_fixos_anual": total_custos_anual,
            "custos_fixos_anual_formatado": _format_currency_br(total_custos_anual),
            "despesas_fixas_anual": total_despesas_anual,
            "despesas_fixas_anual_formatado": _format_currency_br(total_despesas_anual),
            "total_gastos_anual": total_gastos_anual,
            "total_gastos_anual_formatado": _format_currency_br(total_gastos_anual),
            "is_total": True,
        }
    )

    return resultado


def aggregate_structure_investments(structures: List[Dict[str, Any]]) -> Dict[str, Any]:
    from decimal import Decimal

    categories_summary: Dict[str, Dict[str, Any]] = {
        "instalacoes": {"total": Decimal("0"), "per_month": {}},
        "maquinas": {"total": Decimal("0"), "per_month": {}},
        "outros": {"total": Decimal("0"), "per_month": {}},
    }
    per_month_total: Dict[str, Decimal] = {}
    entries: List[Dict[str, Any]] = []

    for area in structures:
        area_nome = area.get("nome") or "Area"
        for bloco in area.get("blocos", []):
            bloco_nome = bloco.get("nome", "Outros")
            for item in bloco.get("itens", []):
                parcelas = item.get("parcelas", [])
                item_desc = item.get("descricao") or "Item"
                item_id = item.get("id")

                for idx, parcela in enumerate(parcelas, 1):
                    classificacao = _classify_structure_installment(bloco_nome, parcela)
                    if classificacao["classificacao_norm"] != "investimento":
                        continue

                    valor_decimal = _parse_decimal(parcela.get("valor"))
                    if not valor_decimal or valor_decimal <= 0:
                        continue

                    category_slug = classificacao["category"]
                    template_key = (
                        "maquinas"
                        if category_slug == "maquinas_equipamentos"
                        else category_slug
                    )
                    if template_key not in categories_summary:
                        categories_summary[template_key] = {
                            "total": Decimal("0"),
                            "per_month": {},
                        }

                    categories_summary[template_key]["total"] += valor_decimal

                    due_info = parcela.get("vencimento") or parcela.get("due_info")
                    month_tuple = _month_tuple_from_value(due_info)
                    contribution_date = None
                    if month_tuple:
                        contribution_date = date(month_tuple[0], month_tuple[1], 1)
                        month_key = _month_key_from_tuple(month_tuple)
                        _accumulate_decimal(
                            categories_summary[template_key]["per_month"],
                            month_key,
                            valor_decimal,
                        )
                        _accumulate_decimal(per_month_total, month_key, valor_decimal)
                    else:
                        contribution_date = due_info

                    parcela_numero = parcela.get("numero") or idx
                    description = (
                        f"{bloco_nome} - {item_desc} (Parcela {parcela_numero})"
                    )

                    entries.append(
                        {
                            "id": f"struct::{item_id or 'item'}::{parcela_numero}",
                            "description": description,
                            "amount": valor_decimal,
                            "investment_group": classificacao["group"],
                            "category": category_slug,
                            "contribution_date": contribution_date,
                            "notes": f"Estruturas de Execucao - {area_nome} - {bloco_nome}",
                            "source": "structures",
                        }
                    )

    grand_total = sum(summary["total"] for summary in categories_summary.values())

    return {
        "entries": entries,
        "categories": categories_summary,
        "per_month_total": per_month_total,
        "grand_total": grand_total,
    }


def serialize_structure_investment_summary(
    categories_summary: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    serialized: Dict[str, Dict[str, Any]] = {}
    for key, data in categories_summary.items():
        total_decimal = data.get("total")
        per_month = data.get("per_month", {})
        total_float = float(total_decimal) if total_decimal is not None else 0.0
        formatted_total = (
            _format_currency_br(total_decimal)
            if total_decimal is not None
            else _format_currency_br(0)
        )
        serialized[key] = {
            "total": total_float,
            "total_formatado": formatted_total or _format_currency_br(0),
            "por_mes": {month: float(amount) for month, amount in per_month.items()},
        }
    return serialized


def _normalize_month_reference(value: Any) -> Tuple[str, Optional[datetime], str]:
    """Normalize different date formats into a YYYY-MM key + human label."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return ("__sem_data__", None, "Sem data")

    text = str(value).strip()
    if not text:
        return ("__sem_data__", None, "Sem data")

    cleaned = text.replace("/", "-")
    candidates = [text]
    if cleaned not in candidates:
        candidates.append(cleaned)
    if len(cleaned) >= 7 and cleaned[4] == "-":
        base = cleaned[:7]
        if base not in candidates:
            candidates.append(base)
        base_iso = f"{base}-01"
        if base_iso not in candidates:
            candidates.append(base_iso)

    parsed: Optional[datetime] = None
    for candidate in candidates:
        for fmt in ("%Y-%m-%d", "%Y-%m", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                parsed_candidate = datetime.strptime(candidate, fmt)
                parsed = parsed_candidate.replace(day=1)
                break
            except ValueError:
                continue
        if parsed:
            break

    if parsed:
        month_key = parsed.strftime("%Y-%m")
        label = (
            f"{MONTH_LABELS_PT.get(parsed.month, parsed.strftime('%b'))}/{parsed.year}"
        )
        return (month_key, parsed, label)

    fallback_key = cleaned[:7] if len(cleaned) >= 7 and cleaned[4] == "-" else cleaned
    if not fallback_key:
        fallback_key = "__sem_data__"
    label = "Sem data" if fallback_key == "__sem_data__" else text
    return (fallback_key, None, label)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_modefin_business_flow(
    products: List[Dict[str, Any]],
    products_totals: Dict[str, Any],
    fixed_cost_entries: List[Dict[str, Any]],
    profit_distribution: List[Dict[str, Any]],
    result_rules: List[Dict[str, Any]],
    num_months: int = 60,
) -> Dict[str, Any]:
    """Build business cash flow with ramp-up, fixed costs timeline, and profit distribution."""
    from decimal import Decimal

    # Construir dataset de ramp-up
    base_revenue = 0.0
    base_cost = 0.0
    base_expense = 0.0
    ramp_entries_combined = []

    for product in products:
        summary = product.get("ramp_up_summary") or {}
        base_revenue += _safe_float(summary.get("base_revenue", 0))
        base_cost += _safe_float(summary.get("base_cost", 0))
        base_expense += _safe_float(summary.get("base_expense", 0))

        entries = product.get("ramp_up_entries") or []
        for entry in entries:
            month = entry.get("month") or entry.get("reference_month")
            if month:
                ramp_entries_combined.append(
                    {
                        "month": month,
                        "percentage": _safe_float(entry.get("percentage", 100)),
                    }
                )

    # Se nÃ£o hÃ¡ ramp-up, usar totais dos produtos
    if base_revenue == 0:
        margem = products_totals.get("margem_contribuicao", {})
        base_revenue = _safe_float(margem.get("valor", 0))
        custos_var = products_totals.get("custos_variaveis", {})
        base_cost = _safe_float(custos_var.get("valor", 0))
        despesas_var = products_totals.get("despesas_variaveis", {})
        base_expense = _safe_float(despesas_var.get("valor", 0))
        base_revenue = base_revenue + base_cost + base_expense  # Reconstituir receita

    # Determinar mÃªs inicial (sempre comeÃ§ar em janeiro para relatÃ³rio)
    start_month = "2026-01"

    # Gerar sequÃªncia de meses
    meses = _generate_month_sequence(start_month, num_months)

    # Construir fluxo mÃªs a mÃªs
    rows = []

    # DistribuiÃ§Ã£o de lucros
    dist_percent = 0.0
    dist_start_month = None
    if profit_distribution:
        dist_percent = _safe_float(profit_distribution[0].get("percentage", 0))
        dist_start_month = profit_distribution[0].get("start_date")

    for mes in meses:
        # Receita com ramp-up
        ramp_pct = _get_ramp_percentage(mes, ramp_entries_combined) / 100.0
        receita = base_revenue * ramp_pct
        custo_var = base_cost * ramp_pct
        despesa_var = base_expense * ramp_pct
        margem = receita - custo_var - despesa_var

        # Custos fixos por data
        custo_fixo = _get_fixed_cost_for_month(mes, fixed_cost_entries, "custo")
        despesa_fixa = _get_fixed_cost_for_month(mes, fixed_cost_entries, "despesa")

        resultado_op = margem - custo_fixo - despesa_fixa

        # DistribuiÃ§Ãµes (sÃ³ se resultado positivo e apÃ³s data de inÃ­cio)
        distribuicao = 0.0
        if resultado_op > 0:
            if dist_start_month:
                if mes >= dist_start_month:
                    distribuicao = resultado_op * (dist_percent / 100.0)
            else:
                distribuicao = resultado_op * (dist_percent / 100.0)

            # Outras destinaÃ§Ãµes
            for rule in result_rules:
                rule_start = rule.get("start_date")
                if rule_start and mes < rule_start:
                    continue
                rule_pct = _safe_float(rule.get("percentage", 0))
                distribuicao += resultado_op * (rule_pct / 100.0)

        resultado_periodo = resultado_op - distribuicao

        rows.append(
            {
                "periodo": _format_month_label(mes),
                "receita": receita,
                "custo_variavel": custo_var,
                "despesa_variavel": despesa_var,
                "margem": margem,
                "custo_fixo": custo_fixo,
                "despesa_fixa": despesa_fixa,
                "fixos_total": custo_fixo + despesa_fixa,
                "resultado_operacional": resultado_op,
                "distribuicao": distribuicao,
                "resultado_periodo": resultado_periodo,
            }
        )

    # Condensar fluxo para formato compacto
    logger.info(
        f"[DEBUG] Business Flow - Total de linhas antes de condensar: {len(rows)}"
    )

    value_fields = [
        "receita",
        "custo_variavel",
        "despesa_variavel",
        "margem",
        "custo_fixo",
        "despesa_fixa",
        "fixos_total",
        "resultado_operacional",
        "distribuicao",
        "resultado_periodo",
    ]
    condensed_rows = condense_cash_flow_rows(rows, value_fields)

    logger.info(
        f"[DEBUG] Business Flow - Total de linhas apÃ³s condensar: {len(condensed_rows)}"
    )
    if condensed_rows:
        logger.info(
            f"[DEBUG] Primeiros 3 perÃ­odos: {[r['periodo'] for r in condensed_rows[:3]]}"
        )
        logger.info(
            f"[DEBUG] Ãšltimos 3 perÃ­odos: {[r['periodo'] for r in condensed_rows[-3:]]}"
        )

    return {
        "rows": condensed_rows,
        "rows_full": rows,  # Retornar tambÃ©m dados completos para investor_flow
        "has_rows": bool(condensed_rows),
    }


def _get_ramp_percentage(month: str, ramp_entries: List[Dict[str, Any]]) -> float:
    """Get ramp-up percentage for a given month."""
    if not ramp_entries:
        return 100.0

    # Ordenar por mÃªs
    sorted_entries = sorted(ramp_entries, key=lambda e: e["month"])

    # Se antes do primeiro mÃªs, retorna 0
    if month < sorted_entries[0]["month"]:
        return 0.0

    # Procurar percentual exato ou interpolar
    for entry in sorted_entries:
        if month == entry["month"]:
            return entry["percentage"]
        if month < entry["month"]:
            break

    # Se passou do Ãºltimo, retorna 100%
    return 100.0


def _get_fixed_cost_for_month(
    month: str, fixed_cost_entries: List[Dict[str, Any]], cost_type: str
) -> float:
    """Get fixed cost/expense for a given month."""
    total = 0.0
    for entry in fixed_cost_entries:
        if entry.get("type") != cost_type:
            continue
        start_month = entry.get("start_month")
        if start_month and month >= start_month:
            total += _safe_float(entry.get("monthly_value", 0))
    return total


def _format_month_label(month_key: str) -> str:
    """Format month key (YYYY-MM) to label (Mmm/YYYY)."""
    try:
        year, month_num = month_key.split("-")
        month_num = int(month_num)
        return f"{MONTH_LABELS_PT.get(month_num, 'Jan')}/{year}"
    except (ValueError, AttributeError):
        return month_key


def _generate_month_sequence(start_month: str, num_months: int) -> List[str]:
    """Generate sequence of month keys (YYYY-MM) starting from start_month."""
    try:
        year, month = map(int, start_month.split("-"))
    except (ValueError, AttributeError):
        year, month = 2026, 1

    months = []
    for _ in range(num_months):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1

    return months


def condense_cash_flow_rows(
    rows: List[Dict[str, Any]], value_fields: List[str]
) -> List[Dict[str, Any]]:
    """
    Condensa fluxo de caixa para formato compacto:
    - 12 primeiros meses (detalhado)
    - 13Âº mÃªs atÃ© fim do ano (agregado)
    - Anos seguintes (agregado por ano)

    value_fields: lista de campos numÃ©ricos para somar na agregaÃ§Ã£o
    """
    if not rows:
        return []

    logger.info(f"[DEBUG condense] Condensando {len(rows)} linhas...")

    condensed = []

    # Primeiros 12 meses (detalhado)
    for i in range(min(12, len(rows))):
        condensed.append(rows[i].copy())

    if len(rows) <= 12:
        logger.info(f"[DEBUG condense] Menos de 12 linhas, retornando {len(condensed)}")
        return condensed

    # Agrupar restante por ano usando dicionÃ¡rio
    anos_agregados = {}

    for i in range(12, len(rows)):
        row = rows[i]
        periodo = row.get("periodo", "")

        # Extrair ano do perÃ­odo (formato: "Mmm/YYYY" ou "YYYY-MM")
        try:
            if "/" in periodo:
                year = int(periodo.split("/")[-1])
            else:
                year = int(periodo.split("-")[0])
        except (ValueError, IndexError, AttributeError):
            logger.info(f"[DEBUG condense] Ignorando perÃ­odo invÃ¡lido: {periodo}")
            continue

        # Criar agregado do ano se nÃ£o existir
        if year not in anos_agregados:
            anos_agregados[year] = {
                "periodo": f"Ano {year}",
                **{field: 0.0 for field in value_fields},
            }

        # Somar valores ao agregado do ano
        for field in value_fields:
            anos_agregados[year][field] += _safe_float(row.get(field, 0))

    # Adicionar anos na ordem
    for year in sorted(anos_agregados.keys()):
        condensed.append(anos_agregados[year])

    logger.info(f"[DEBUG condense] Anos encontrados: {sorted(anos_agregados.keys())}")
    logger.info(f"[DEBUG condense] Total de linhas condensadas: {len(condensed)}")

    return condensed


def build_modefin_investor_flow(
    investment_flow: Dict[str, Any],
    business_flow: Dict[str, Any],
    profit_distribution: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build investor cash flow combining investments and profit distributions."""

    # Pegar TODOS os meses do business_flow (usar rows_full para nÃ£o pegar condensado)
    business_rows = business_flow.get("rows_full") or business_flow.get("rows", [])
    logger.info(
        f"[DEBUG] Investor Flow - business_rows recebidos: {len(business_rows)}"
    )
    if not business_rows:
        return {"rows": [], "has_rows": False}

    # Criar mapa de aportes por perÃ­odo
    aportes_map = {}
    for row in investment_flow.get("rows", []):
        periodo = row.get("period_label", "")
        fontes = row.get("fontes", 0.0)
        if periodo:
            aportes_map[periodo] = fontes

    # Construir fluxo completo (todos os meses do business_flow)
    rows = []
    saldo_acumulado = 0.0

    for bus_row in business_rows:
        periodo = bus_row.get("periodo", "")

        # Buscar aporte deste perÃ­odo (se houver)
        aporte = aportes_map.get(periodo, 0.0)

        # DistribuiÃ§Ã£o vem do business_flow
        distribuicao = bus_row.get("distribuicao", 0.0)

        # Saldo do perÃ­odo (perspectiva do investidor: recebe - coloca)
        saldo_periodo = distribuicao - aporte
        saldo_acumulado += saldo_periodo

        rows.append(
            {
                "periodo": periodo,
                "aporte": aporte,
                "distribuicao": distribuicao,
                "saldo_periodo": saldo_periodo,
                "saldo_acumulado": saldo_acumulado,
            }
        )

    # Condensar fluxo para formato compacto
    logger.info(
        f"[DEBUG] Investor Flow - Total de linhas antes de condensar: {len(rows)}"
    )

    condensed = []

    # Primeiros 12 meses (detalhado)
    for i in range(min(12, len(rows))):
        condensed.append(rows[i].copy())

    logger.info(
        f"[DEBUG] Adicionados primeiros 12 meses. Total condensed: {len(condensed)}"
    )

    if len(rows) > 12:
        # Agrupar restante por ano
        anos_agregados = {}

        for i in range(12, len(rows)):
            row = rows[i]
            periodo = row.get("periodo", "")

            # Extrair ano
            try:
                if "/" in periodo:
                    year = int(periodo.split("/")[-1])
                else:
                    year = int(periodo.split("-")[0])
            except (ValueError, IndexError, AttributeError):
                logger.info(f"[DEBUG] NÃ£o conseguiu extrair ano de: {periodo}")
                continue

            # Criar ou atualizar agregado do ano
            if year not in anos_agregados:
                anos_agregados[year] = {
                    "periodo": f"Ano {year}",
                    "aporte": 0.0,
                    "distribuicao": 0.0,
                    "saldo_periodo": 0.0,
                    "saldo_acumulado": 0.0,
                    "ultimo_saldo": 0.0,
                }

            # Acumular valores do ano
            anos_agregados[year]["aporte"] += row.get("aporte", 0.0)
            anos_agregados[year]["distribuicao"] += row.get("distribuicao", 0.0)
            anos_agregados[year]["saldo_periodo"] += row.get("saldo_periodo", 0.0)
            # Guardar o Ãºltimo saldo acumulado deste ano
            anos_agregados[year]["ultimo_saldo"] = row.get("saldo_acumulado", 0.0)

        # Adicionar anos na ordem
        for year in sorted(anos_agregados.keys()):
            year_data = anos_agregados[year]
            year_data["saldo_acumulado"] = year_data["ultimo_saldo"]
            condensed.append(
                {
                    "periodo": year_data["periodo"],
                    "aporte": year_data["aporte"],
                    "distribuicao": year_data["distribuicao"],
                    "saldo_periodo": year_data["saldo_periodo"],
                    "saldo_acumulado": year_data["saldo_acumulado"],
                }
            )

        logger.info(f"[DEBUG] Anos agregados: {sorted(anos_agregados.keys())}")
        logger.info(f"[DEBUG] Total de linhas condensadas: {len(condensed)}")

    return {"rows": condensed, "has_rows": bool(condensed)}


def build_modefin_investment_flow(
    capital_giro_items: Optional[Iterable[Dict[str, Any]]],
    investimentos_estruturas: Optional[Dict[str, Dict[str, Any]]],
    funding_sources: Optional[Iterable[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Aggregate cash flow for investments (capital de giro + imobilizado vs fontes)."""
    entries: Dict[str, Dict[str, Any]] = {}

    def ensure_entry(key: str, dt: Optional[datetime], label: str) -> Dict[str, Any]:
        entry = entries.get(key)
        if entry is None:
            entry = {
                "key": key,
                "date": dt,
                "label": label or key or "Sem data",
                "capital_giro": 0.0,
                "imobilizado": 0.0,
                "fontes": 0.0,
            }
            entries[key] = entry
        else:
            if entry.get("date") is None and dt is not None:
                entry["date"] = dt
            if entry.get("label") in (entry.get("key"), "Sem data") and label:
                entry["label"] = label
        return entry

    for item in capital_giro_items or []:
        amount = _safe_float((item or {}).get("amount"))
        if not amount:
            continue
        key, dt, label = _normalize_month_reference(
            (item or {}).get("contribution_date")
        )
        entry = ensure_entry(key, dt, label)
        entry["capital_giro"] += amount

    for categoria in (investimentos_estruturas or {}).values():
        por_mes = (categoria or {}).get("por_mes") or {}
        for month_key, value in por_mes.items():
            amount = _safe_float(value)
            if not amount:
                continue
            key, dt, label = _normalize_month_reference(month_key)
            entry = ensure_entry(key, dt, label)
            entry["imobilizado"] += amount

    for source in funding_sources or []:
        amount = _safe_float((source or {}).get("amount"))
        if not amount:
            continue
        key, dt, label = _normalize_month_reference(
            (source or {}).get("contribution_date")
        )
        entry = ensure_entry(key, dt, label)
        entry["fontes"] += amount

    sorted_entries = sorted(
        entries.values(),
        key=lambda entry: (
            entry.get("date") is None,
            entry.get("date") or datetime.max,
            entry.get("label"),
        ),
    )

    rows: List[Dict[str, Any]] = []
    totals = {
        "capital_giro": 0.0,
        "imobilizado": 0.0,
        "investimentos": 0.0,
        "fontes": 0.0,
        "saldo_periodo": 0.0,
    }
    saldo_acumulado = 0.0

    for entry in sorted_entries:
        capital = entry.get("capital_giro", 0.0)
        imobilizado = entry.get("imobilizado", 0.0)
        fontes = entry.get("fontes", 0.0)
        investimentos = capital + imobilizado
        saldo_periodo = fontes - investimentos
        saldo_acumulado += saldo_periodo

        rows.append(
            {
                "period_label": entry.get("label"),
                "capital_giro": capital,
                "imobilizado": imobilizado,
                "investimentos": investimentos,
                "fontes": fontes,
                "saldo_periodo": saldo_periodo,
                "saldo_acumulado": saldo_acumulado,
            }
        )

        totals["capital_giro"] += capital
        totals["imobilizado"] += imobilizado
        totals["investimentos"] += investimentos
        totals["fontes"] += fontes
        totals["saldo_periodo"] += saldo_periodo

    # Condensar fluxo para formato compacto (se houver muitas linhas)
    condensed_rows = rows
    if len(rows) > 12:
        value_fields = [
            "capital_giro",
            "imobilizado",
            "investimentos",
            "fontes",
            "saldo_periodo",
        ]
        # Para investment flow, precisamos lÃ³gica especial para saldo_acumulado
        condensed = []

        # Primeiros 12 registros (detalhado)
        for i in range(min(12, len(rows))):
            condensed.append(rows[i].copy())

        # Agrupar restante por ano
        current_year = None
        year_aggregate = None
        last_saldo_acumulado = condensed[-1]["saldo_acumulado"] if condensed else 0.0

        for i in range(12, len(rows)):
            row = rows[i]
            periodo = row.get("period_label", "")

            # Extrair ano
            try:
                if "/" in periodo:
                    year = int(periodo.split("/")[-1])
                else:
                    year = int(periodo.split("-")[0])
            except (ValueError, IndexError, AttributeError):
                continue

            if current_year is None:
                current_year = year
                year_aggregate = {
                    "period_label": f"Ano {year}",
                    **{field: 0.0 for field in value_fields},
                    "saldo_acumulado": 0.0,
                }

            if year != current_year:
                year_aggregate["saldo_acumulado"] = last_saldo_acumulado
                condensed.append(year_aggregate)

                current_year = year
                year_aggregate = {
                    "period_label": f"Ano {year}",
                    **{field: 0.0 for field in value_fields},
                    "saldo_acumulado": 0.0,
                }

            # Somar valores
            for field in value_fields:
                year_aggregate[field] += _safe_float(row.get(field, 0))
            last_saldo_acumulado = row.get("saldo_acumulado", last_saldo_acumulado)

        # Adicionar Ãºltimo ano
        if year_aggregate:
            year_aggregate["saldo_acumulado"] = last_saldo_acumulado
            condensed.append(year_aggregate)

        condensed_rows = condensed

    return {
        "rows": condensed_rows,
        "totals": totals,
        "saldo_final": saldo_acumulado,
        "has_rows": bool(condensed_rows),
    }


def _parse_percentage_value(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    normalized = text.replace("%", "").replace(",", ".")
    try:
        return float(normalized)
    except (TypeError, ValueError):
        return default


def calculate_modefin_analysis_metrics(
    products_totals: Optional[Dict[str, Any]],
    fixed_costs_summary: Optional[Dict[str, Any]],
    investment_flow: Optional[Dict[str, Any]],
    financeiro: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Approximate ModeFin analytic indicators (payback, ROI, VPL, etc.)."""
    products_totals = products_totals or {}
    fixed_costs_summary = fixed_costs_summary or {}
    investment_flow = investment_flow or {}
    financeiro = financeiro or {}

    margem_data = products_totals.get("margem_contribuicao") or {}
    margem_valor = _safe_float(margem_data.get("valor"))

    custos_fixos = _safe_float(fixed_costs_summary.get("custos_fixos_mensal"))
    despesas_fixas = _safe_float(fixed_costs_summary.get("despesas_fixas_mensal"))

    resultado_operacional = margem_valor - custos_fixos - despesas_fixas

    totals = investment_flow.get("totals") or {}
    total_investimentos = _safe_float(totals.get("investimentos"))

    fluxo_analises = (financeiro.get("fluxo_investidor") or {}).get("analises") or {}
    periodo_meses = (
        fluxo_analises.get("periodo_meses") or fluxo_analises.get("periodo") or 60
    )
    try:
        periodo_meses = int(periodo_meses)
    except (TypeError, ValueError):
        periodo_meses = 60
    if periodo_meses <= 0:
        periodo_meses = 60

    custo_oportunidade = fluxo_analises.get("opportunity_cost")
    if custo_oportunidade is None:
        custo_oportunidade = (financeiro.get("investimento") or {}).get(
            "custo_oportunidade"
        )
    custo_oportunidade_percent = _parse_percentage_value(
        custo_oportunidade, default=1.0
    )

    payback = None
    if resultado_operacional > 0 and total_investimentos > 0:
        payback = total_investimentos / resultado_operacional

    roi_percent = None
    if total_investimentos > 0 and resultado_operacional != 0:
        roi_percent = (
            resultado_operacional * periodo_meses / total_investimentos
        ) * 100

    tir_percent = None
    if payback and payback > 0:
        tir_percent = (1 / payback) * 100

    vpl = 0.0
    if resultado_operacional > 0 and total_investimentos > 0:
        taxa_mensal = (1 + (custo_oportunidade_percent / 100.0)) ** (1 / 12) - 1
        vpl = -total_investimentos
        for mes in range(1, periodo_meses + 1):
            valor_presente = resultado_operacional / ((1 + taxa_mensal) ** mes)
            vpl += valor_presente

    return {
        "resultado_operacional": resultado_operacional,
        "total_investimentos": total_investimentos,
        "periodo_meses": periodo_meses,
        "custo_oportunidade_percent": custo_oportunidade_percent,
        "payback_meses": payback,
        "roi_percent": roi_percent,
        "tir_percent": tir_percent,
        "vpl": vpl,
    }


def summarize_structures_for_report(
    structures: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for area in structures:
        area_summary = {
            "area": area.get("nome"),
            "codigo": area.get("codigo"),
            "capacidade": area.get("capacidade"),
            "capacidade_formatada": area.get("capacidade_formatada"),
            "capacidade_observacoes": area.get("capacidade_observacoes"),
            "resumo": [],
        }
        for bloco in area.get("blocos", []):
            pontos = [
                item.get("descricao")
                for item in bloco.get("itens", [])
                if item.get("descricao")
            ]
            if not pontos:
                continue
            area_summary["resumo"].append(
                {"escopo": bloco.get("nome"), "pontos": pontos[:5]}
            )
        summary.append(area_summary)
    return summary


def load_financial_model(db, plan_id: int) -> Dict[str, Any]:
    premises = db.list_plan_finance_premises(plan_id)
    investments = db.list_plan_finance_investments(plan_id)
    sources = db.list_plan_finance_sources(plan_id)
    business_periods = db.list_plan_finance_business_periods(plan_id)
    distribution = db.list_plan_finance_business_distribution(plan_id)
    variable_costs = db.list_plan_finance_variable_costs(plan_id)
    result_rules = db.list_plan_finance_result_rules(plan_id)
    investor_periods = db.list_plan_finance_investor_periods(plan_id)
    metrics = db.get_plan_finance_metrics(plan_id) or {}
    opportunity_cost = metrics.get("opportunity_cost")
    if not opportunity_cost or str(opportunity_cost).strip() == "":
        opportunity_cost = "1%"
    tir_horizon_raw = metrics.get("tir_horizon_years")
    try:
        tir_horizon_years = (
            int(tir_horizon_raw) if tir_horizon_raw not in (None, "") else None
        )
    except (TypeError, ValueError):
        tir_horizon_years = None
    if tir_horizon_years not in (2, 3, 5):
        tir_horizon_years = 5
    metrics["opportunity_cost"] = opportunity_cost
    metrics["tir_horizon_years"] = tir_horizon_years
    profit_distribution = db.get_plan_profit_distribution(plan_id) or {}
    structure_capacities = db.list_plan_structure_capacities(plan_id)

    distribution_map: Dict[int, List[Dict[str, Any]]] = {}
    for item in distribution:
        period_id = item.get("period_id")
        distribution_map.setdefault(period_id, []).append(
            {
                "descricao": item.get("description"),
                "valor": item.get("amount"),
            }
        )

    structures_full = load_structures(db, plan_id)
    structure_investments_payload = aggregate_structure_investments(structures_full)
    investments_combined = list(investments) + structure_investments_payload["entries"]
    investment_dataset = _prepare_investment_dataset(investments_combined)
    structure_investments_serialized = serialize_structure_investment_summary(
        structure_investments_payload["categories"]
    )
    sources_dataset = _prepare_sources_dataset(sources)

    business_periods_prepared: List[Dict[str, Any]] = []
    business_month_tuples: List[Tuple[int, int]] = []
    business_fallback_labels: List[Dict[str, str]] = []
    business_fallback_seen: set[str] = set()
    business_line_maps: Dict[str, Dict[str, Decimal]] = {
        "receita": {},
        "custos_variaveis": {},
        "despesas_variaveis": {},
        "margem_contribuicao": {},
        "custos_fixos": {},
        "despesas_fixas": {},
        "resultado_operacional": {},
        "destinacao": {},
        "resultado_periodo": {},
    }

    for index, period in enumerate(business_periods):
        pid = period.get("id")
        period_label = period.get("period_label") or ""
        month_tuple = _month_tuple_from_value(period_label)
        if month_tuple:
            business_month_tuples.append(month_tuple)
            period_key = _month_key_from_tuple(month_tuple)
            period_label_short = _format_month_short(month_tuple)
            period_label_full = _format_month_full(month_tuple)
        else:
            label_display = period_label or f"Per\u00edodo {index + 1}"
            period_key = _build_fallback_key(label_display, prefix="negocio")
            if period_key not in business_fallback_seen:
                business_fallback_labels.append(
                    {"label": label_display, "key": period_key}
                )
                business_fallback_seen.add(period_key)
            period_label_short = label_display
            period_label_full = label_display

        receita_decimal = _parse_decimal(period.get("revenue"))
        variaveis_decimal = _parse_decimal(period.get("variables"))
        margem_decimal = _parse_decimal(period.get("contribution_margin"))
        fixos_decimal = _parse_decimal(period.get("fixed_costs"))
        despesas_variaveis_decimal = _parse_decimal(period.get("variable_expenses"))
        despesas_fixas_decimal = _parse_decimal(period.get("fixed_expenses"))
        resultado_operacional_decimal = _parse_decimal(period.get("operating_result"))
        resultado_periodo_decimal = _parse_decimal(period.get("result_period"))

        if receita_decimal is not None:
            business_line_maps["receita"][period_key] = receita_decimal
        if variaveis_decimal is not None:
            business_line_maps["custos_variaveis"][period_key] = variaveis_decimal
        if despesas_variaveis_decimal is not None:
            business_line_maps["despesas_variaveis"][
                period_key
            ] = despesas_variaveis_decimal
        if margem_decimal is not None:
            business_line_maps["margem_contribuicao"][period_key] = margem_decimal
        if fixos_decimal is not None:
            business_line_maps["custos_fixos"][period_key] = fixos_decimal
        if despesas_fixas_decimal is not None:
            business_line_maps["despesas_fixas"][period_key] = despesas_fixas_decimal
        if resultado_operacional_decimal is not None:
            business_line_maps["resultado_operacional"][
                period_key
            ] = resultado_operacional_decimal
        if resultado_periodo_decimal is not None:
            business_line_maps["resultado_periodo"][
                period_key
            ] = resultado_periodo_decimal

        destinacao_itens = distribution_map.get(pid, [])
        destinacao_total_decimal = Decimal("0")
        destinacao_tem_valor = False
        for destino in destinacao_itens:
            destino_decimal = _parse_decimal(destino.get("valor"))
            if destino_decimal is not None:
                destinacao_total_decimal += destino_decimal
                destinacao_tem_valor = True
        if destinacao_tem_valor:
            business_line_maps["destinacao"][period_key] = destinacao_total_decimal
            destinacao_total_str = _format_currency_br(destinacao_total_decimal)
        else:
            destinacao_total_str = ""

        business_periods_prepared.append(
            {
                "periodo": period_label,
                "periodo_completo": period_label_full,
                "periodo_curto": period_label_short,
                "periodo_chave": period_key,
                "receita": period.get("revenue"),
                "variaveis": period.get("variables"),
                "margem_contribuicao": period.get("contribution_margin"),
                "fixos": period.get("fixed_costs"),
                "despesas_variaveis": period.get("variable_expenses"),
                "despesas_fixas": period.get("fixed_expenses"),
                "resultado_operacional": period.get("operating_result"),
                "destinacao": destinacao_itens,
                "destinacao_total": destinacao_total_str,
                "resultado_periodo": period.get("result_period"),
            }
        )

    investor_periods_prepared: List[Dict[str, Any]] = []
    investor_month_tuples: List[Tuple[int, int]] = []
    investor_fallback_labels: List[Dict[str, str]] = []
    investor_fallback_seen: set[str] = set()
    investor_line_maps: Dict[str, Dict[str, Decimal]] = {
        "aportes": {},
        "distribuicoes": {},
        "resultado_liquido": {},
        "saldo_acumulado": {},
    }

    for index, item in enumerate(investor_periods):
        period_label = item.get("period_label") or ""
        month_tuple = _month_tuple_from_value(period_label)
        if month_tuple:
            investor_month_tuples.append(month_tuple)
            period_key = _month_key_from_tuple(month_tuple)
            period_label_short = _format_month_short(month_tuple)
        else:
            label_display = period_label or f"Per\u00edodo {index + 1}"
            period_key = _build_fallback_key(label_display, prefix="investidor")
            if period_key not in investor_fallback_seen:
                investor_fallback_labels.append(
                    {"label": label_display, "key": period_key}
                )
                investor_fallback_seen.add(period_key)
            period_label_short = label_display

        aporte_decimal = _parse_decimal(item.get("contribution"))
        distribuicao_decimal = _parse_decimal(item.get("distribution"))
        saldo_decimal = _parse_decimal(item.get("balance"))
        acumulado_decimal = _parse_decimal(item.get("cumulative"))

        if aporte_decimal is not None:
            investor_line_maps["aportes"][period_key] = aporte_decimal
        if distribuicao_decimal is not None:
            investor_line_maps["distribuicoes"][period_key] = distribuicao_decimal
        if saldo_decimal is not None:
            investor_line_maps["resultado_liquido"][period_key] = saldo_decimal
        if acumulado_decimal is not None:
            investor_line_maps["saldo_acumulado"][period_key] = acumulado_decimal

        investor_periods_prepared.append(
            {
                "periodo": period_label,
                "periodo_curto": period_label_short,
                "periodo_chave": period_key,
                "aporte": item.get("contribution"),
                "distribuicao": item.get("distribution"),
                "saldo": item.get("balance"),
                "acumulado": item.get("cumulative"),
            }
        )

    investment_columns = _build_month_columns(
        investment_dataset["month_tuples"],
        investment_dataset["fallback_labels"],
    )
    investment_matrix_rows: List[Dict[str, Any]] = []
    totals_per_column: Dict[str, Decimal] = {
        column["key"]: Decimal("0") for column in investment_columns
    }
    group_data = investment_dataset["per_group_category"]

    for group in ["capital_giro", "imobilizado"]:
        group_label = INVESTMENT_GROUP_LABELS.get(
            group, group.replace("_", " ").title()
        )
        investment_matrix_rows.append(
            {
                "descricao": group_label,
                "tipo": "grupo",
                "grupo": group,
            }
        )
        category_order = INVESTMENT_CATEGORY_ORDER.get(group, [])
        seen_categories = set(category_order)
        for category in category_order:
            category_info = group_data.get(group, {}).get(
                category,
                {
                    "per_month": {},
                    "total": Decimal("0"),
                },
            )
            per_month_map: Dict[str, Decimal] = category_info.get("per_month", {})
            values_map = {
                column["key"]: per_month_map.get(column["key"])
                for column in investment_columns
            }
            line = _build_matrix_line(
                INVESTMENT_CATEGORY_LABELS.get(
                    category, category.replace("_", " ").title()
                ),
                values_map,
                investment_columns,
            )
            line.update({"tipo": "categoria", "grupo": group, "categoria": category})
            investment_matrix_rows.append(line)
            for column in investment_columns:
                value_decimal = per_month_map.get(column["key"])
                if value_decimal is not None:
                    _accumulate_decimal(totals_per_column, column["key"], value_decimal)
        for category, category_info in group_data.get(group, {}).items():
            if category in seen_categories:
                continue
            per_month_map = category_info.get("per_month", {})
            values_map = {
                column["key"]: per_month_map.get(column["key"])
                for column in investment_columns
            }
            line = _build_matrix_line(
                INVESTMENT_CATEGORY_LABELS.get(
                    category, category.replace("_", " ").title()
                ),
                values_map,
                investment_columns,
            )
            line.update(
                {"tipo": "categoria_extra", "grupo": group, "categoria": category}
            )
            investment_matrix_rows.append(line)
            for column in investment_columns:
                value_decimal = per_month_map.get(column["key"])
                if value_decimal is not None:
                    _accumulate_decimal(totals_per_column, column["key"], value_decimal)

    total_line_map = {
        column["key"]: totals_per_column.get(column["key"])
        for column in investment_columns
    }
    investment_total_row = _build_matrix_line(
        "Total Geral", total_line_map, investment_columns
    )
    investment_total_row.update({"tipo": "total"})

    investment_matrix = {
        "columns": investment_columns,
        "column_labels_full": [column["label_full"] for column in investment_columns],
        "column_labels_short": [column["label_short"] for column in investment_columns],
        "rows": investment_matrix_rows,
        "total": investment_total_row,
    }

    investment_summary_por_grupo = {
        group: {
            "label": INVESTMENT_GROUP_LABELS.get(
                group, group.replace("_", " ").title()
            ),
            "total": _format_currency_br(total),
        }
        for group, total in investment_dataset["totals_por_grupo"].items()
    }
    fontes_summary_por_tipo = {
        tipo: {
            "label": SOURCE_TYPE_LABELS.get(tipo, tipo.replace("_", " ").title()),
            "total": _format_currency_br(total),
        }
        for tipo, total in sources_dataset["totals_por_tipo"].items()
    }
    necessidade_total_decimal = (
        investment_dataset["grand_total"] if investment_dataset["entries"] else None
    )
    fontes_total_decimal = (
        sources_dataset["grand_total"] if sources_dataset["entries"] else None
    )
    necessidade_total_str = (
        _format_currency_br(necessidade_total_decimal)
        if necessidade_total_decimal is not None
        else ""
    )
    fontes_total_str = (
        _format_currency_br(fontes_total_decimal)
        if fontes_total_decimal is not None
        else ""
    )

    combined_month_tuples = (
        investment_dataset["month_tuples"]
        + sources_dataset["month_tuples"]
        + business_month_tuples
        + investor_month_tuples
    )
    combined_fallback_labels = (
        investment_dataset["fallback_labels"]
        + sources_dataset["fallback_labels"]
        + business_fallback_labels
        + investor_fallback_labels
    )
    fluxo_columns = _build_month_columns(
        combined_month_tuples, combined_fallback_labels
    )

    fontes_rows: List[Dict[str, Any]] = []
    per_tipo_map = sources_dataset["per_tipo"]
    for tipo_slug in SOURCE_TYPE_ORDER:
        tipo_info = per_tipo_map.get(
            tipo_slug,
            {
                "per_month": {},
            },
        )
        per_month_map = tipo_info.get("per_month", {})
        values_map = {
            column["key"]: per_month_map.get(column["key"]) for column in fluxo_columns
        }
        line = _build_matrix_line(
            SOURCE_TYPE_LABELS.get(tipo_slug, tipo_slug.replace("_", " ").title()),
            values_map,
            fluxo_columns,
        )
        line.update({"slug": tipo_slug})
        fontes_rows.append(line)
    for tipo_slug, tipo_info in per_tipo_map.items():
        if tipo_slug in SOURCE_TYPE_ORDER:
            continue
        per_month_map = tipo_info.get("per_month", {})
        values_map = {
            column["key"]: per_month_map.get(column["key"]) for column in fluxo_columns
        }
        line = _build_matrix_line(
            SOURCE_TYPE_LABELS.get(tipo_slug, tipo_slug.replace("_", " ").title()),
            values_map,
            fluxo_columns,
        )
        line.update({"slug": tipo_slug})
        fontes_rows.append(line)

    aplicacao_rows: List[Dict[str, Any]] = []
    capital_giro_map = group_data.get("capital_giro", {})
    for categoria_slug in ["caixa", "estoques", "recebiveis"]:
        categoria_info = capital_giro_map.get(
            categoria_slug,
            {
                "per_month": {},
            },
        )
        per_month_map = categoria_info.get("per_month", {})
        values_map = {
            column["key"]: per_month_map.get(column["key"]) for column in fluxo_columns
        }
        line = _build_matrix_line(
            INVESTMENT_CATEGORY_LABELS.get(
                categoria_slug, categoria_slug.replace("_", " ").title()
            ),
            values_map,
            fluxo_columns,
        )
        line.update({"grupo": "capital_giro", "categoria": categoria_slug})
        aplicacao_rows.append(line)

    ativo_map: Dict[str, Decimal] = {}
    for categoria_slug in INVESTMENT_CATEGORY_ORDER.get("imobilizado", []):
        categoria_info = group_data.get("imobilizado", {}).get(
            categoria_slug,
            {
                "per_month": {},
            },
        )
        per_month_map = categoria_info.get("per_month", {})
        for key, amount in per_month_map.items():
            _accumulate_decimal(ativo_map, key, amount)
    ativo_values_map = {
        column["key"]: ativo_map.get(column["key"]) for column in fluxo_columns
    }
    ativo_line = _build_matrix_line(
        "Ativo Imobilizado", ativo_values_map, fluxo_columns
    )
    ativo_line.update({"grupo": "imobilizado", "categoria": "ativo_imobilizado"})
    aplicacao_rows.append(ativo_line)

    negocio_rows: List[Dict[str, Any]] = []
    negocio_order = [
        ("receita", "Receita"),
        ("custos_variaveis", "Custos Vari\u00e1veis"),
        ("despesas_variaveis", "Despesas Vari\u00e1veis"),
        ("margem_contribuicao", "Margem de Contribui\u00e7\u00e3o"),
        ("custos_fixos", "Custos Fixos"),
        ("despesas_fixas", "Despesas Fixas"),
        ("resultado_operacional", "Resultado Operacional"),
        ("destinacao", "Destina\u00e7\u00e3o de Resultados"),
        ("resultado_periodo", "Resultado do Per\u00edodo"),
    ]
    for slug, label in negocio_order:
        valores_map = business_line_maps.get(slug, {})
        mapped_values = {
            column["key"]: valores_map.get(column["key"]) for column in fluxo_columns
        }
        line = _build_matrix_line(label, mapped_values, fluxo_columns)
        line.update({"slug": slug})
        negocio_rows.append(line)

    investidor_rows: List[Dict[str, Any]] = []
    investidor_order = [
        ("aportes", "Aporte dos S\u00f3cios no M\u00eas", "sum"),
        ("distribuicoes", "Distribui\u00e7\u00e3o Recebida no M\u00eas", "sum"),
        ("resultado_liquido", "Resultado L\u00edquido Acumulado no M\u00eas", "sum"),
        ("saldo_acumulado", "Saldo Acumulado", "last"),
    ]
    for slug, label, strategy in investidor_order:
        valores_map = investor_line_maps.get(slug, {})
        mapped_values = {
            column["key"]: valores_map.get(column["key"]) for column in fluxo_columns
        }
        line = _build_matrix_line(
            label, mapped_values, fluxo_columns, total_strategy=strategy
        )
        line.update({"slug": slug})
        investidor_rows.append(line)

    fluxo_financeiro = {
        "columns": fluxo_columns,
        "column_labels_full": [column["label_full"] for column in fluxo_columns],
        "column_labels_short": [column["label_short"] for column in fluxo_columns],
        "sections": [
            {"titulo": "Fontes de Recursos", "slug": "fontes", "linhas": fontes_rows},
            {
                "titulo": "Montagem / Aplica\u00e7\u00e3o do Investimento",
                "slug": "aplicacao",
                "linhas": aplicacao_rows,
            },
            {
                "titulo": "Resultado do Neg\u00f3cio",
                "slug": "negocio",
                "linhas": negocio_rows,
            },
            {
                "titulo": "Fluxo de Caixa dos S\u00f3cios / Investidores",
                "slug": "investidores",
                "linhas": investidor_rows,
            },
        ],
    }

    capacities_prepared: List[Dict[str, Any]] = []
    total_capacity_decimal = Decimal("0")
    capacity_count = 0
    bottleneck: Optional[Dict[str, Any]] = None

    for item in structure_capacities:
        area_code = (item.get("area") or "").lower()
        area_name = AREA_LABELS.get(area_code, item.get("area") or "Outros")
        decimal_value = _parse_decimal(item.get("revenue_capacity"))

        if decimal_value is not None:
            capacity_count += 1
            total_capacity_decimal += decimal_value
            if not bottleneck or decimal_value < bottleneck["valor_decimal"]:
                bottleneck = {
                    "area": area_name,
                    "area_codigo": area_code,
                    "valor_decimal": decimal_value,
                }

        capacities_prepared.append(
            {
                "id": item.get("id"),
                "area_codigo": area_code,
                "area": area_name,
                "valor": item.get("revenue_capacity"),
                "valor_formatado": _format_currency_br(item.get("revenue_capacity")),
                "valor_decimal": float(decimal_value)
                if decimal_value is not None
                else None,
                "observacoes": item.get("observations"),
            }
        )

    total_decimal_final = total_capacity_decimal if capacity_count > 0 else None
    resumo_capacidades = {
        "total_decimal": float(total_decimal_final)
        if total_decimal_final is not None
        else None,
        "total_formatado": _format_currency_br(total_decimal_final)
        if total_decimal_final is not None
        else "",
        "gargalo_area": bottleneck["area"] if bottleneck else "",
        "gargalo_area_codigo": bottleneck["area_codigo"] if bottleneck else "",
        "gargalo_valor_decimal": float(bottleneck["valor_decimal"])
        if bottleneck
        else None,
        "gargalo_valor_formatado": _format_currency_br(bottleneck["valor_decimal"])
        if bottleneck
        else "",
    }

    investimento_section = {
        "investimento": investment_dataset["entries"],
        "fontes": sources_dataset["entries"],
        "matriz": investment_matrix,
        "resumo": {
            "necessidade_total": necessidade_total_str,
            "fontes_total": fontes_total_str,
            "por_grupo": investment_summary_por_grupo,
            "por_tipo": fontes_summary_por_tipo,
        },
        "estruturas_automaticas": {
            "categorias": structure_investments_serialized,
            "total_decimal": float(structure_investments_payload["grand_total"])
            if structure_investments_payload["grand_total"] is not None
            else 0.0,
            "total_formatado": _format_currency_br(
                structure_investments_payload["grand_total"]
            )
            if structure_investments_payload["grand_total"] is not None
            else _format_currency_br(0),
            "por_mes_total": {
                month: float(amount)
                for month, amount in structure_investments_payload[
                    "per_month_total"
                ].items()
            },
        },
    }

    fluxo_negocio_payload = {
        "periodos": business_periods_prepared,
        "variaveis": [
            {
                "id": item.get("id"),
                "descricao": item.get("description"),
                "percentual": item.get("percentage"),
            }
            for item in variable_costs
        ],
        "distribuicao_lucros": {
            "percentual": profit_distribution.get("percentage", ""),
            "start_date": profit_distribution.get("start_date", ""),
            "observacoes": profit_distribution.get("notes", ""),
        },
        "destinacao_regras": [
            {
                "id": item.get("id"),
                "descricao": item.get("description"),
                "percentual": item.get("percentage"),
                "periodicidade": item.get("periodicity"),
            }
            for item in result_rules
        ],
    }

    tir_value = metrics.get("tir")
    tir_label = (
        f"TIR {metrics['tir_horizon_years']} anos"
        if metrics.get("tir_horizon_years")
        else "TIR"
    )
    fluxo_investidor_payload = {
        "periodos": investor_periods_prepared,
        "analises": {
            "payback": metrics.get("payback"),
            "tir": tir_value,
            "tir_label": tir_label,
            "tir_horizon_years": metrics.get("tir_horizon_years"),
            "opportunity_cost": metrics.get("opportunity_cost"),
            "comentarios": metrics.get("notes") or "",
            "tir_5_anos": tir_value if metrics.get("tir_horizon_years") == 5 else "",
        },
    }

    return {
        "premissas": [
            {
                "id": item.get("id"),
                "indicador": item.get("description"),
                "sugestao": item.get("suggestion"),
                "ajustado": item.get("adjusted"),
                "observacoes": item.get("observations"),
                "memoria": item.get("memory"),
            }
            for item in premises
        ],
        "capacidades": capacities_prepared,
        "resumo_capacidades": resumo_capacidades,
        "investimento": investimento_section,
        "fluxo_negocio": fluxo_negocio_payload,
        "fluxo_investidor": fluxo_investidor_payload,
        "fluxo_financeiro": fluxo_financeiro,
    }


def build_final_report_payload(
    plan: Dict[str, Any],
    alignment_canvas: Dict[str, Any],
    alignment_project: Dict[str, Any],
    principles: List[Dict[str, Any]],
    segments_for_report: List[Dict[str, Any]],
    structures_summary: List[Dict[str, Any]],
    financial_model: Dict[str, Any],
) -> Dict[str, Any]:
    principles_list = [
        item.get("principle") for item in principles if item.get("principle")
    ]
    alignment_section = {
        "socios": alignment_canvas.get("socios", []),
        "agenda": alignment_canvas.get("proximos_passos", []),
        "principios": principles_list,
        "visao": alignment_canvas.get("alinhamento", {}).get("visao_compartilhada"),
        "metas": alignment_canvas.get("alinhamento", {}).get("metas_financeiras"),
    }

    return {
        "plan": plan,
        "alinhamento": alignment_section,
        "segmentos": segments_for_report,
        "estruturas": structures_summary,
        "financeiro": financial_model,
        "issued_at": datetime.now().strftime("%d/%m/%Y Ã s %H:%M"),
        "projeto": alignment_project,
    }
