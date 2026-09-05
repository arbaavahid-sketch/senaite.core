# -*- coding: utf-8 -*-
#
# One-off admin tool: ensure the PIONA / Detailed Hydrocarbon Analysis
# (ASTM D6730) service exists, carrying the Mass% group results as interim
# fields (flagged report=True so they print on the report). The full GC
# instrument PDF is attached to the sample separately. Dry-run by default;
# ?apply=1 writes. ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

_KEYWORD = u"PIONA_D6730"
_TITLE = u"آنالیز کامل هیدروکربنی (PIONA) — ASTM D6730"
_METHOD = u"ASTM D6730"
_UNIT = u"% wt"
_CATEGORY = u"هیدروکربن"  # matched by contains

# PIONA order (Paraffins, Iso-paraffins, Olefins, Naphthenes, Aromatics)
# plus Oxygenates and Unknowns — Mass% basis. (keyword, title)
_GROUPS = [
    (u"PAR", u"پارافین‌ها (Paraffins)"),
    (u"ISOP", u"ایزوپارافین‌ها (Iso-paraffins)"),
    (u"OLE", u"اولفین‌ها (Olefins)"),
    (u"NAP", u"نفتن‌ها (Naphthenes)"),
    (u"ARO", u"آروماتیک‌ها (Aromatics)"),
    (u"OXY", u"اکسیژنه‌ها (Oxygenates)"),
    (u"UNK", u"نامشخص (Unknowns)"),
]


def _interims():
    out = []
    for kw, title in _GROUPS:
        out.append({"keyword": kw, "title": title, "value": "",
                    "unit": _UNIT, "hidden": False, "wide": False,
                    "result_type": "", "report": True})
    return out


class EnsurePionaServiceView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        # locate an existing service by keyword
        svc = None
        for brain in api.search({"portal_type": "AnalysisService"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            if safe_unicode(obj.getKeyword() or u"") == _KEYWORD:
                svc = obj
                break

        # locate the target category (contains-match)
        cat = None
        for brain in api.search({"portal_type": "AnalysisCategory"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            title = safe_unicode(api.get_title(obj))
            if _CATEGORY in title or title in _CATEGORY:
                cat = obj
                break
        out.append(u"category: %s" % (
            safe_unicode(api.get_title(cat)) if cat else u"(NONE FOUND!)"))

        try:
            container = api.get_bika_setup().bika_analysisservices
        except Exception:
            container = api.get_portal().bika_setup.bika_analysisservices

        if svc is not None:
            out.append(u"%s service\t%s\t%s" % (
                u"UPDATE" if apply else u"would update",
                _KEYWORD, safe_unicode(api.get_title(svc))))
            if apply:
                svc.setInterimFields(_interims())
                if not getattr(svc, "tppc_method_text", None):
                    svc.tppc_method_text = _METHOD
                svc.reindexObject()
        elif cat is None:
            out.append(u"ABORT: category '%s' not found; cannot create"
                       % _CATEGORY)
        else:
            out.append(u"%s service\t%s\t%s\t[%s]" % (
                u"CREATE" if apply else u"would create",
                _KEYWORD, _TITLE, safe_unicode(api.get_title(cat))))
            if apply:
                try:
                    svc = api.create(
                        container, "AnalysisService", title=_TITLE,
                        Keyword=_KEYWORD, Category=api.get_uid(cat),
                        Unit=_UNIT)
                    svc.setInterimFields(_interims())
                    svc.tppc_method_text = _METHOD
                    svc.reindexObject()
                except Exception as exc:  # noqa
                    out.append(u"  ERROR\t%s" % safe_unicode(exc))

        out.append(u"")
        out.append(u"Mass% group fields (report=True):")
        for kw, title in _GROUPS:
            out.append(u"  %s\t%s\t%s" % (kw, title, _UNIT))
        out.append(u"")
        out.append(u"NOTE: attach the full GC/DHA PDF to each sample as an "
                   u"Attachment; the report prints this summary strip.")

        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out).encode("utf-8")
