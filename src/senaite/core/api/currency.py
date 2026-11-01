# -*- coding: utf-8 -*-
"""Display-only currency labels; numeric amounts and codes stay unchanged."""
from zope.i18n.locales import locales


def get_currency_symbol(currency, language="en"):
    if currency == "IRR":
        language = (language or "en").lower().split("-")[0]
        return u"ریال" if language == "fa" else u"IRR"
    return locales.getLocale("en").numbers.currencies[currency].symbol
