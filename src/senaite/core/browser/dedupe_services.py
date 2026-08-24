# -*- coding: utf-8 -*-
#
# One-off admin tool: find AnalysisServices that are exact duplicates (same
# normalized title) and deactivate all but one per group (keeping the one that
# already carries a curated standard). Conservative: genuinely different tests
# (different temperature/method/%) are NOT grouped. Dry-run by default;
# ?apply=1 deactivates. Deactivation is reversible. ManageBika only.

import re

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

_DIACRITICS = re.compile(u"[ً-ْٰ]")
_PARENS = re.compile(u"\\([^)]*\\)")
_NONWORD = re.compile(u"[^0-9A-Za-z؀-ۿ ]")
_SPACES = re.compile(u"\\s+")


def _norm(title):
    t = safe_unicode(title or u"").lower()
    t = _PARENS.sub(u" ", t)                      # drop "(ASTM ...)" etc.
    t = (t.replace(u"ي", u"ی").replace(u"ك", u"ک")
          .replace(u"ۀ", u"ه").replace(u"ة", u"ه")
          .replace(u"‌", u" "))
    t = _DIACRITICS.sub(u"", t)
    t = _NONWORD.sub(u" ", t)
    t = _SPACES.sub(u" ", t)
    return t.strip()


class DedupeServicesView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY (deactivating)" if apply else
                              u"DRY-RUN (add ?apply=1 to deactivate)")]

        # UIDs referenced by any AnalysisSpec result range: never deactivate
        # the copy a spec points at, or its range would stop matching.
        referenced = set()
        try:
            specs = api.get_bika_setup().bika_analysisspecs
            for spec in specs.objectValues():
                for rr in (spec.getResultsRange() or []):
                    uid = rr.get("uid")
                    if uid:
                        referenced.add(uid)
        except Exception:
            pass

        # active services only, grouped by normalized title
        groups = {}
        for brain in api.search({"portal_type": "AnalysisService",
                                 "is_active": True}, SETUP_CATALOG):
            obj = api.get_object(brain)
            key = _norm(api.get_title(obj))
            if key:
                groups.setdefault(key, []).append(obj)

        deactivated = 0
        dup_groups = 0
        lines = []
        for key, objs in sorted(groups.items()):
            if len(objs) < 2:
                continue
            dup_groups += 1
            # keep preference: (1) referenced by a spec range, (2) has a
            # curated standard, (3) lowest keyword.
            def sortkey(o):
                ref = api.get_uid(o) in referenced
                has_std = bool(safe_unicode(
                    getattr(o, "tppc_method_text", u"") or u"").strip())
                return (0 if ref else 1, 0 if has_std else 1,
                        safe_unicode(o.getKeyword() or u""))
            objs_sorted = sorted(objs, key=sortkey)
            keep = objs_sorted[0]
            lines.append(u"GROUP (%d)\tKEEP: %s | %s" % (
                len(objs), safe_unicode(keep.getKeyword()),
                safe_unicode(api.get_title(keep))))
            for obj in objs_sorted[1:]:
                lines.append(u"    deactivate\t%s\t%s" % (
                    safe_unicode(obj.getKeyword()),
                    safe_unicode(api.get_title(obj))))
                if apply:
                    try:
                        api.do_transition_for(obj, "deactivate")
                    except Exception as exc:  # noqa
                        lines.append(u"      ERROR\t%s" % safe_unicode(exc))
                        continue
                deactivated += 1

        summary = [
            u"", u"active services scanned: %d" % sum(
                len(v) for v in groups.values()),
            u"duplicate groups: %d" % dup_groups,
            u"services to deactivate / deactivated: %d" % deactivated,
            u"", u"--- details (only duplicate groups shown) ---",
        ]
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out + summary + lines).encode("utf-8")
