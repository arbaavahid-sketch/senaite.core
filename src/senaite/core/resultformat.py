# -*- coding: utf-8 -*-
"""Display-only formatting for numeric detailed report results."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

NUMBER = re.compile(r'^[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?$')
try:
    text_type = unicode
except NameError:
    text_type = str


def format_numeric_detail(value, precision=3, decimal_mark='.'):
    """Return fixed decimals, or None to retain the original formatting.

    Text, inequalities and non-finite values are preserved by the caller.
    A non-zero measurement must never become an apparent zero.
    """
    if value is None or isinstance(value, bool):
        return None
    text = text_type(value).strip()
    if not NUMBER.match(text):
        return None
    try:
        digits = int(precision)
        if digits < 0 or digits > 12:
            return None
        with localcontext() as ctx:
            ctx.prec = max(28, len(text) + digits + 4)
            number = Decimal(text)
            rounded = number.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
            if number and not rounded:
                return None
            if not rounded:
                rounded = abs(rounded)
            result = format(rounded, '.%df' % digits)
        return result.replace('.', decimal_mark)
    except (ValueError, TypeError, InvalidOperation, OverflowError):
        return None
