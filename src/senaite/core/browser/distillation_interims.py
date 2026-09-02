# -*- coding: utf-8 -*-
#
# One-off admin tool: add the ASTM D86 distillation-curve interim fields
# (IBP, 10%..90%, FBP) to the atmospheric-distillation analysis services, so a
# full boiling curve can be recorded instead of a single result. Matches
# active services whose standard/name mentions D86. Dry-run by default;
# ?apply=1 writes. ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

# (keyword, title) — keyword must be a valid identifier, title is the label.
_POINTS = [
    (u"IBP", u"IBP"),
    (u"D10", u"10%"), (u"D20", u"20%"), (u"D30", u"30%"),
    (u"D40", u"40%"), (u"D50", u"50%"), (u"D60", u"60%"),
    (u"D70", u"70%"), (u"D80", u"80%"), (u"D90", u"90%"),
    (u"FBP", u"FBP"),
]


def _interims():
    out = []
    for kw, title in _POINTS:
        out.append({
            "keyword": kw, "title": title, "value": "", "unit": u"°C",
            "hidden": False, "wide": False, "result_type": "",
        })
    return out


class AddDistillationInterimsView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        updated = skipped = 0
        lines = []
        for brain in api.search({"portal_type": "AnalysisService",
                                 "is_active": True}, SETUP_CATALOG):
            obj = api.get_object(brain)
            std = safe_unicode(getattr(obj, "tppc_method_text", u"") or u"")
            title = safe_unicode(api.get_title(obj))
            hay = (std + u" " + title).upper()
            # atmospheric distillation = ASTM D86
            if u"D86" not in hay.replace(u" ", u""):
                continue
            existing = obj.getInterimFields() or []
            has_ibp = any(safe_unicode(i.get("keyword", "")) == u"IBP"
                          for i in existing)
            if has_ibp:
                skipped += 1
                lines.append(u"already has interims\t%s\t%s" % (
                    obj.getKeyword(), title))
                continue
            lines.append(u"%s\t%s\t%s\t(+%d fields)" % (
                u"UPDATE" if apply else u"would update",
                obj.getKeyword(), title, len(_POINTS)))
            if apply:
                obj.setInterimFields(_interims())
                obj.reindexObject()
            updated += 1

        summary = [
            u"", u"distillation (D86) services updated: %d" % updated,
            u"already had interims (skipped): %d" % skipped,
            u"", u"--- details ---",
        ]
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out + summary + lines).encode("utf-8")
