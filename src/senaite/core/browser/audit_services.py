# -*- coding: utf-8 -*-
#
# One-off admin tool: audit AnalysisServices for wrong units and duplicates.
# Dry-run (default) prints every active service with its detected ASTM
# standard, current unit, the expected unit (when known), a UNIT? flag on a
# real mismatch, and groups of likely-duplicate services. ?apply=1 fixes the
# units that are confidently wrong (physical-quantity mismatch). It never
# deletes or merges duplicates — that stays a manual/`@@dedupe-services`
# decision. ManageBika only.

import re

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

_STD_RE = re.compile(r"D\s?-?\s?(\d{1,4})")  # ASTM D-number

# Detected ASTM D-number -> expected unit. Only confident petroleum tests.
_EXPECTED = {
    # flash point
    "D93": u"°C", "D92": u"°C", "D56": u"°C", "D3828": u"°C", "D6450": u"°C",
    # pour / cloud / freeze
    "D97": u"°C", "D5950": u"°C", "D2500": u"°C", "D5773": u"°C",
    "D2386": u"°C", "D1177": u"°C",
    # aniline / drop / softening
    "D611": u"°C",
    # kinematic viscosity
    "D445": u"mm²/s",
    # distillation (temperatures)
    "D86": u"°C", "D1160": u"°C", "D2892": u"°C",
    # ash / carbon residue / sediment (mass %)
    "D482": u"% wt", "D189": u"% wt", "D4530": u"% wt", "D524": u"% wt",
    "D473": u"% wt",
    # acid / base number
    "D664": u"mg KOH/g", "D974": u"mg KOH/g", "D2896": u"mg KOH/g",
    # vapour pressure
    "D323": u"kPa", "D5191": u"kPa", "D6378": u"kPa",
    # water by distillation
    "D95": u"vol %",
    # density
    "D1298": u"kg/m³", "D4052": u"kg/m³",
    # elements (ICP / XRF trace)
    "D5185": u"mg/kg", "D4951": u"mg/kg",
    # heat of combustion
    "D240": u"MJ/kg", "D4809": u"MJ/kg",
}

# Unit synonym canonicalisation: strings that MEAN the same thing must not be
# flagged as a mismatch.
_UNIT_SYNONYMS = {
    u"mass%": u"wt%", u"wt%": u"wt%", u"%wt": u"wt%", u"%m/m": u"wt%",
    u"%(m/m)": u"wt%", u"درصدجرمی": u"wt%",
    u"vol%": u"vol%", u"%vol": u"vol%", u"%v/v": u"vol%", u"درصدحجمی": u"vol%",
    u"mm2/s": u"mm2/s", u"cst": u"mm2/s", u"centistokes": u"mm2/s",
    u"kg/m3": u"kg/m3", u"g/cm3": u"g/cm3", u"g/ml": u"g/cm3",
    u"mgkoh/g": u"mgkoh/g",
    u"mg/kg": u"mg/kg", u"ppm": u"mg/kg",
    u"°c": u"°c", u"c": u"°c", u"celsius": u"°c",
    u"kpa": u"kpa",
}


def _unit_norm(u):
    s = safe_unicode(u or u"").strip().lower()
    s = s.replace(u"²", u"2").replace(u"³", u"3").replace(u" ", u"")
    s = s.replace(u"٪", u"%")
    return _UNIT_SYNONYMS.get(s, s)


def _title_norm(t):
    s = safe_unicode(t or u"")
    s = re.sub(r"\(.*?\)", u" ", s)            # drop parentheticals
    s = s.replace(u"ي", u"ی").replace(u"ك", u"ک").replace(u"‌", u" ")
    s = re.sub(r"\s+", u" ", s).strip().lower()
    return s


def _detect_std(text):
    m = _STD_RE.search(safe_unicode(text or u"").upper().replace(u" ", u""))
    return (u"D" + m.group(1)) if m else u""


class AuditServicesView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY (fix units)" if apply else
                              u"DRY-RUN (add ?apply=1 to fix units)"), u""]

        rows = []
        for brain in api.search({"portal_type": "AnalysisService",
                                 "is_active": True}, SETUP_CATALOG):
            obj = api.get_object(brain)
            kw = safe_unicode(obj.getKeyword() or u"")
            title = safe_unicode(api.get_title(obj))
            unit = safe_unicode(obj.getUnit() or u"")
            method = safe_unicode(getattr(obj, "tppc_method_text", u"") or u"")
            cat = u""
            try:
                c = obj.getCategory()
                cat = safe_unicode(api.get_title(c)) if c else u""
            except Exception:
                cat = u""
            std = _detect_std(title + u" " + method)
            rows.append({"obj": obj, "kw": kw, "title": title, "unit": unit,
                         "cat": cat, "std": std})

        # --- unit audit ---
        fixed = flagged = 0
        out.append(u"=== UNIT AUDIT (keyword | std | current -> expected) ===")
        for r in sorted(rows, key=lambda x: x["title"]):
            exp = _EXPECTED.get(r["std"])
            if not exp:
                continue
            if _unit_norm(r["unit"]) == _unit_norm(exp):
                continue
            flagged += 1
            out.append(u"%s  %s\t%s\t%s -> %s\t%s" % (
                u"FIX" if apply else u"UNIT?", r["kw"], r["std"],
                r["unit"] or u"(empty)", exp, r["title"]))
            if apply:
                r["obj"].setUnit(exp)
                r["obj"].reindexObject()
                fixed += 1

        # --- duplicate groups (by normalised core title) ---
        groups = {}
        for r in rows:
            key = _title_norm(r["title"])
            groups.setdefault(key, []).append(r)
        dup_groups = [g for g in groups.values() if len(g) > 1]
        out.append(u"")
        out.append(u"=== POSSIBLE DUPLICATES (same core title) ===")
        for g in sorted(dup_groups, key=lambda g: g[0]["title"]):
            out.append(u"* %s" % g[0]["title"])
            for r in g:
                out.append(u"    %s\t[%s]\t%s" % (
                    r["kw"], r["cat"], r["unit"] or u"(empty)"))

        out.append(u"")
        out.append(u"--- summary ---")
        out.append(u"services audited: %d" % len(rows))
        out.append(u"unit mismatches %s: %d" % (
            u"fixed" if apply else u"flagged", fixed if apply else flagged))
        out.append(u"duplicate groups: %d" % len(dup_groups))
        out.append(u"")
        out.append(u"NOTE: only confident physical-unit mismatches are fixed; "
                   u"ambiguous ones (e.g. sulfur mg/kg vs %) are left as-is. "
                   u"Duplicates are only listed — deactivate the extras "
                   u"manually or with @@dedupe-services.")

        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out).encode("utf-8")
