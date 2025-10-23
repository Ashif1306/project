from django import template

register = template.Library()


@register.filter(name='rupiah')
def rupiah(value):
    """Format number as Rupiah with dot separator for thousands"""
    try:
        value = float(value)
        # Format with dot as thousand separator
        formatted = "{:,.0f}".format(value).replace(',', '.')
        return f"Rp {formatted}"
    except (ValueError, TypeError):
        return value


@register.filter(name='dot_separator')
def dot_separator(value):
    """Format number with dot as thousand separator"""
    try:
        value = float(value)
        # Format with dot as thousand separator
        return "{:,.0f}".format(value).replace(',', '.')
    except (ValueError, TypeError):
        return value
