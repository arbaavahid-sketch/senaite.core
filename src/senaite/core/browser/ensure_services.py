# -*- coding: utf-8 -*-
#
# One-off admin tool: ensure the lab's priority analyses exist. Creates a few
# missing AnalysisServices (with category + unit + standard) and stamps the
# standard on a few existing ones. Dry-run by default; ?apply=1 writes.
# ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

# keyword: existing service -> just set tppc_method_text.
# create=True: build a new AnalysisService in the given category.
ENSURE = [
    {u"keyword": u"SPX_006", u"method": u"ASTM D1287"},
    {u"keyword": u"SPX_001", u"method": u"ASTM D1122"},
    {u"keyword": u"AS_89969_004", u"method": u"ISO 6614 / ASTM D1401"},
    {u"keyword": u"ANTI_CHLORIDE", u"create": True, u"category": u"ضدیخ",
     u"unit": u"mg/kg", u"method": u"ASTM D3634",
     u"title": u"اندازه‌گیری کلر در ضدیخ"},
    {u"keyword": u"OIL_ELEMENTAL_RDE", u"create": True, u"category": u"روغن",
     u"unit": u"mg/kg", u"method": u"ASTM D6595",
     u"title": u"آنالیز عنصری روغن به روش نشر اتمی (RDE-OES)"},
    {u"keyword": u"HC_PONA_FIA", u"create": True, u"category": u"هیدروکربن",
     u"unit": u"% vol", u"method": u"ASTM D1319",
     u"title": u"تعیین آروماتیک، اولفین و اشباع (پونا) به روش FIA"},
    {u"keyword": u"BIT_SG_D70", u"create": True, u"category": u"قیر",
     u"unit": u"", u"method": u"ASTM D70",
     u"title": u"وزن مخصوص قیر"},
]


class EnsurePriorityServicesView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        kw2svc = {}
        for brain in api.search({"portal_type": "AnalysisService"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            kw2svc[safe_unicode(obj.getKeyword() or u"")] = obj

        cats = {}
        for brain in api.search({"portal_type": "AnalysisCategory"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            cats[safe_unicode(api.get_title(obj))] = obj

        def find_category(name):
            if name in cats:
                return cats[name]
            for title, obj in cats.items():
                if name in title or title in name:
                    return obj
            return None

        try:
            container = api.get_bika_setup().bika_analysisservices
        except Exception:
            container = api.get_portal().bika_setup.bika_analysisservices

        set_method = created = errors = 0
        lines = []
        for item in ENSURE:
            kw = item["keyword"]
            svc = kw2svc.get(kw)
            if svc is not None:
                lines.append(u"SET METHOD\t%s\t%s\t%s" % (
                    kw, safe_unicode(api.get_title(svc)), item["method"]))
                if apply:
                    svc.tppc_method_text = item["method"]
                    svc.reindexObject()
                set_method += 1
                continue
            if not item.get("create"):
                lines.append(u"MISSING (not creating)\t%s" % kw)
                continue
            cat = find_category(item["category"])
            if cat is None:
                errors += 1
                lines.append(u"NO CATEGORY\t%s\t(%s)" % (kw, item["category"]))
                continue
            lines.append(u"CREATE\t%s\t%s\t[%s]\t%s" % (
                kw, item["title"], safe_unicode(api.get_title(cat)),
                item["method"]))
            if apply:
                try:
                    obj = api.create(
                        container, "AnalysisService", title=item["title"],
                        Keyword=kw, Category=api.get_uid(cat),
                        Unit=item.get("unit", u""))
                    obj.tppc_method_text = item["method"]
                    obj.reindexObject()
                    created += 1
                except Exception as exc:  # noqa
                    errors += 1
                    lines.append(u"  ERROR\t%s\t%s" % (kw, safe_unicode(exc)))

        summary = [
            u"", u"existing services stamped: %d" % set_method,
            u"new services created: %d" % created,
            u"errors: %d" % errors, u"", u"--- details ---",
        ]
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out + summary + lines).encode("utf-8")
