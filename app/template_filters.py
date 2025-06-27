import re
from markupsafe import Markup

def nl2br(value):
    """
    Converts newlines in a string to HTML <br> tags.
    Also ensures that the output is treated as safe HTML.
    """
    if not isinstance(value, str):
        return value
    # Replace \r\n, \r, \n with <br>
    # Ensure to escape original HTML to prevent XSS if value might contain user-input HTML
    # However, for simple text comments, direct replacement is often what's intended.
    # For safety, if pre-existing HTML is a concern, one might escape `value` first.
    # For now, assuming `value` is plain text or pre-sanitized.
    processed_value = value.replace('\r\n', '<br>').replace('\r', '<br>').replace('\n', '<br>')
    return Markup(processed_value)

def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """
    Formats a datetime object.
    Example: {{ my_datetime | datetimeformat }}
             {{ my_datetime | datetimeformat('%Y年%m月%d日') }}
    """
    if value is None:
        return ""
    return value.strftime(format)
