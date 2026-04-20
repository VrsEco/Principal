from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def format_date_br(value, include_time=False):
    """
    Formats a date or string to Brazilian format (DD/MM/YYYY)
    Usage in template: {{ my_date | format_date_br }} or {{ my_date | format_date_br(True) }}
    """
    if not value:
        return ""
        
    # If it's a string, try to parse it
    if isinstance(value, str):
        try:
            # Try ISO format
            if 'T' in value:
                # Remove Z and use +00:00 for fromisoformat compatibility in Python < 3.11
                clean_value = value.replace('Z', '+00:00')
                dt = datetime.fromisoformat(clean_value)
            else:
                # Try common SQL format
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except Exception:
            try:
                dt = datetime.strptime(value, '%Y-%m-%d')
            except Exception:
                return value # Return as is if parsing fails
    else:
        dt = value
                
    if not hasattr(dt, 'strftime'):
        return str(dt)

    if include_time:
        return dt.strftime('%d/%m/%Y %H:%M')
    return dt.strftime('%d/%m/%Y')

def format_currency_br(value):
    """
    Formats a number to Brazilian format (XX.XXX,XX)
    Usage in template: {{ my_value | format_currency_br }}
    """
    if value is None:
        return "0,00"
    try:
        raw = str(value).strip()
        if not raw:
            return "0,00"
        if "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        amount = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        signal = "-" if amount < 0 else ""
        amount = abs(amount)
        integer_part, decimal_part = f"{amount:.2f}".split(".")
        groups = []
        while integer_part:
            groups.insert(0, integer_part[-3:])
            integer_part = integer_part[:-3]
        return f"{signal}{'.'.join(groups)},{decimal_part}"
    except (ValueError, TypeError, InvalidOperation):
        return value

def register_filters(app):
    """Registers the custom filters in the Flask app"""
    app.jinja_env.filters['format_date_br'] = format_date_br
    app.jinja_env.filters['format_currency_br'] = format_currency_br
