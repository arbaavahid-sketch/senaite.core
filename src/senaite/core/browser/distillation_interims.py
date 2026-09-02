# -*- coding: utf-8 -*-
#
# One-off admin tool: add the ASTM D86 distillation-curve interim fields
# (IBP, 10%..90%, FBP) to the atmospheric-distillation analysis services, so a
# full boiling curve can be recorded and printed on the report instead of a
# single result. Matches active services whose standard/name mentions D86.
#
# Interims are flagged report=True so the impress report renders them (see
# reportview.get_result_variables, which skips interims without that flag).
#
# The tool also patches in-progress *analyses* that already carry these
# interims, adding report=True while PRESERVING any values already entered, so
# existing samples need not be re-created. Dry-run by default; ?apply=1 writes.
# ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import ANALYSIS_CATALOG
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
            "report": True,
        })
    return out


class AddDistillationInterimsView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        svc_updated = 0
        dist_keywords = set()
        lines = []

        # --- 1) services: (re)stamp the 11 interims with report=True ---
        for brain in api.search({"portal_type": "AnalysisService",
                                 "is_active": True}, SETUP_CATALOG):
            obj = api.get_object(brain)
            std = safe_unicode(getattr(obj, "tppc_method_text", u"") or u"")
            title = safe_unicode(api.get_title(obj))
            hay = (std + u" " + title).upper().replace(u" ", u"")
            if u"D86" not in hay:
                continue

            kw = safe_unicode(obj.getKeyword() or u"")
            if kw:
                dist_keywords.add(kw)

            existing = obj.getInterimFields() or []
            has_ibp = any(safe_unicode(i.get("keyword", "")) == u"IBP"
                          for i in existing)
            all_report = has_ibp and all(
                bool(i.get("report", False)) for i in existing
                if safe_unicode(i.get("keyword", "")) in
                {p[0] for p in _POINTS})
            if has_ibp and all_report:
                lines.append(u"service ok (already report=True)\t%s\t%s"
                             % (kw, title))
                continue

            lines.append(u"%s service\t%s\t%s\t(11 curve fields, report=True)"
                         % (u"UPDATE" if apply else u"would update", kw, title))
            if apply:
                obj.setInterimFields(_interims())
                obj.reindexObject()
            svc_updated += 1

        # --- 2) in-progress analyses: set report=True, keep entered values ---
        an_updated = 0
        if dist_keywords:
            query = {"portal_type": "Analysis",
                     "getKeyword": list(dist_keywords)}
            for brain in api.search(query, ANALYSIS_CATALOG):
                obj = api.get_object(brain)
                interims = obj.getInterimFields() or []
                if not any(safe_unicode(i.get("keyword", "")) == u"IBP"
                           for i in interims):
                    continue
                changed = False
                new = []
                for i in interims:
                    d = dict(i)
                    if not d.get("report", False):
                        d["report"] = True
                        changed = True
                    new.append(d)
                if not changed:
                    continue
                lines.append(u"%s analysis\t%s\t(keep values, report=True)"
                             % (u"UPDATE" if apply else u"would update",
                                safe_unicode(api.get_id(obj))))
                if apply:
                    obj.setInterimFields(new)
                    obj.reindexObject()
                an_updated += 1

        summary = [
            u"", u"distillation (D86) services updated: %d" % svc_updated,
            u"in-progress analyses fixed (values kept): %d" % an_updated,
            u"matched service keywords: %s" % (
                u", ".join(sorted(dist_keywords)) or u"(none)"),
            u"", u"--- details ---",
        ]
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out + summary + lines).encode("utf-8")
