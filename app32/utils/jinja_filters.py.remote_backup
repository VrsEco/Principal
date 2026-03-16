from datetime import datetime

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
        except:
            try:
                dt = datetime.strptime(value, '%Y-%m-%d')
            except:
                return value # Return as is if parsing fails
    else:
        dt = value
                
    if not hasattr(dt, 'strftime'):
        return str(dt)

    if include_time:
        return dt.strftime('%d/%m/%Y %H:%M')
    return dt.strftime('%d/%m/%Y')

def register_filters(app):
    """Registers the custom filters in the Flask app"""
    app.jinja_env.filters['format_date_br'] = format_date_br
