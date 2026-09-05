# -*- coding: utf-8 -*-
#
# One-off admin tool: ensure the lab's GC composition services carry the right
# per-component result fields (interim fields, flagged report=True so they
# print on the report). Each GC test has its OWN field set — a PIONA/DHA run
# (ASTM D6730) and a BTEX/aromatics-in-gasoline run (ASTM D5580) are different.
# The full GC instrument PDF is still attached to the sample separately.
#
# For each defined test the tool finds an existing service (by keyword, else by
# a set of title tokens) and stamps its interims; if none is found it creates
# one in the given category. Dry-run by default; ?apply=1 writes. ManageBika.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG


def _norm(text):
    """Fold Arabic yeh/kaf to Persian and drop ZWNJ, for token matching."""
    s = safe_unicode(text or u"")
    return (s.replace(u"ي", u"ی").replace(u"ك", u"ک")
             .replace(u"‌", u" "))


# Each test: keyword (canonical id used on create / primary lookup), title
# (used on create), method (tppc_method_text), category (contains-match),
# unit, match_tokens (ALL must appear in an existing service's title to adopt
# it), and groups = [(field_keyword, field_title), ...].
_TESTS = [
    {
        "keyword": u"PIONA_D6730",
        "title": u"آنالیز کامل هیدروکربنی (PIONA) — ASTM D6730",
        "method": u"ASTM D6730",
        "category": u"هیدروکربن",
        "unit": u"% wt",
        "match_tokens": [u"PIONA"],
        "groups": [
            (u"PAR", u"پارافین‌ها (Paraffins)"),
            (u"ISOP", u"ایزوپارافین‌ها (Iso-paraffins)"),
            (u"OLE", u"اولفین‌ها (Olefins)"),
            (u"NAP", u"نفتن‌ها (Naphthenes)"),
            (u"ARO", u"آروماتیک‌ها (Aromatics)"),
            (u"OXY", u"اکسیژنه‌ها (Oxygenates)"),
            (u"UNK", u"نامشخص (Unknowns)"),
        ],
    },
    {
        "keyword": u"AROM_D5580",
        "title": (u"اندازه‌گیری بنزن، تولوئن، اتیل‌بنزن، زایلن‌ها و کل "
                  u"آروماتیک‌ها در بنزین به روش GC — ASTM D5580"),
        "method": u"ASTM D5580",
        "category": u"هیدروکربن",
        "unit": u"% wt",
        "match_tokens": [u"بنزن", u"آروماتیک", u"کروماتوگراف"],
        "groups": [
            (u"BEN", u"بنزن (Benzene)"),
            (u"TOL", u"تولوئن (Toluene)"),
            (u"ETB", u"اتیل‌بنزن (Ethylbenzene)"),
            (u"PMX", u"پارا/متا-زایلن (p/m-Xylene)"),
            (u"OX", u"ارتو-زایلن (o-Xylene)"),
            (u"C9A", u"آروماتیک‌های ۹ کربنه و سنگین‌تر (C9+ Aromatics)"),
            (u"TAR", u"کل آروماتیک‌ها (Total Aromatics)"),
        ],
    },
    {
        "keyword": u"OXY_D4815",
        "title": (u"تعیین ترکیبات اکسیژنه (متانول، اتانول، MTBE و…) در "
                  u"بنزین به روش GC — ASTM D4815"),
        "method": u"ASTM D4815",
        "category": u"هیدروکربن",
        "unit": u"% wt",
        "match_tokens": [u"اکسیژن", u"بنزین"],
        "groups": [
            (u"MEOH", u"متانول (Methanol)"),
            (u"ETOH", u"اتانول (Ethanol)"),
            (u"MTBE", u"MTBE"),
            (u"TOXY", u"کل ترکیبات اکسیژنه (Total oxygenates)"),
            (u"OXYG", u"کل اکسیژن (Total oxygen)"),
        ],
    },
]


class EnsureGCServicesView(BrowserView):

    def _interims(self, test):
        out = []
        for kw, title in test["groups"]:
            out.append({"keyword": kw, "title": title, "value": "",
                        "unit": test["unit"], "hidden": False, "wide": False,
                        "result_type": "", "report": True})
        return out

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        services = [api.get_object(b) for b in api.search(
            {"portal_type": "AnalysisService"}, SETUP_CATALOG)]
        by_keyword = {}
        for s in services:
            by_keyword[safe_unicode(s.getKeyword() or u"")] = s

        cats = [api.get_object(b) for b in api.search(
            {"portal_type": "AnalysisCategory"}, SETUP_CATALOG)]

        def find_category(name):
            for c in cats:
                t = safe_unicode(api.get_title(c))
                if name in t or t in name:
                    return c
            return None

        try:
            container = api.get_bika_setup().bika_analysisservices
        except Exception:
            container = api.get_portal().bika_setup.bika_analysisservices

        for test in _TESTS:
            out.append(u"")
            out.append(u"=== %s (%s) ===" % (test["keyword"], test["method"]))

            # 1) locate an existing service: by keyword, else by title tokens
            svc = by_keyword.get(test["keyword"])
            if svc is None and test.get("match_tokens"):
                ntoks = [_norm(t) for t in test["match_tokens"]]
                for s in services:
                    if not api.is_active(s):
                        continue
                    nt = _norm(api.get_title(s))
                    if all(tok in nt for tok in ntoks):
                        svc = s
                        break

            interims = self._interims(test)
            if svc is not None:
                out.append(u"%s existing\t%s\t%s" % (
                    u"UPDATE" if apply else u"would update",
                    safe_unicode(svc.getKeyword()),
                    safe_unicode(api.get_title(svc))))
                if apply:
                    svc.setInterimFields(interims)
                    if not getattr(svc, "tppc_method_text", None):
                        svc.tppc_method_text = test["method"]
                    svc.reindexObject()
            else:
                cat = find_category(test["category"])
                if cat is None:
                    out.append(u"ABORT: category '%s' not found"
                               % test["category"])
                    continue
                out.append(u"%s new\t%s\t%s\t[%s]" % (
                    u"CREATE" if apply else u"would create",
                    test["keyword"], test["title"],
                    safe_unicode(api.get_title(cat))))
                if apply:
                    try:
                        svc = api.create(
                            container, "AnalysisService", title=test["title"],
                            Keyword=test["keyword"],
                            Category=api.get_uid(cat), Unit=test["unit"])
                        svc.setInterimFields(interims)
                        svc.tppc_method_text = test["method"]
                        svc.reindexObject()
                    except Exception as exc:  # noqa
                        out.append(u"  ERROR\t%s" % safe_unicode(exc))
                        continue

            for kw, title in test["groups"]:
                out.append(u"    %s\t%s\t%s" % (kw, title, test["unit"]))

        out.append(u"")
        out.append(u"NOTE: attach the full GC PDF to each sample; the report "
                   u"prints this per-component summary. Units default to % wt "
                   u"(mass); change on the service if you report % vol.")
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out).encode("utf-8")
