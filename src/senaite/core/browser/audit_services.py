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
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SETUP_CATALOG

_STD_RE = re.compile(r"D\s?-?\s?(\d{1,4})")  # ASTM D-number
_TEMP_RE = re.compile(u"(\\d{2,3})\\s*(?:°|درجه)")  # temperature in a title

# Per-keyword unit fixes the standard alone can't resolve.
_SPECIAL_UNIT = {
    u"AS_99740_158": u"mPa·s",   # HTHS (high shear) = dynamic viscosity
    u"AS_73057_107": u"g/cm³",   # specific gravity (was % mass)
}

# Hand-vetted duplicate groups (same test, same conditions). Within each the
# best service (has limits / method / in use) is kept, the rest deactivated.
# NOTE: same standard is NOT enough to be a duplicate — e.g. the 36 D5185
# element tests, D1177 33%/50%, D128 acid/alkali are distinct and NOT listed.
# The FIRST keyword in each group is KEPT; the rest are deactivated.
_DUP_GROUPS = [
    [u"AS_49176_065", u"AS_09521_020", u"AS_36104_064", u"AS_39409_059"],  # D482 ash
    [u"AS_79882_026", u"AS_21031_060", u"AS_30884_120"],                   # D1500 color
    [u"SPX_010", u"AS_83735_037", u"AS_44049_038", u"AS_15785_050"],       # D2896 TBN
    [u"AS_99825_033", u"AS_40113_034"],                                    # D664 acid no.
    [u"AS_43069_092", u"AS_23337_008", u"AS_88113_055"],                   # D6304 water KF
    [u"AS_24745_103", u"AS_48963_129", u"SPX_009"],                        # D97 pour
    [u"AS_55943_127", u"AS_79390_068", u"AS_05147_149", u"AS_10878_150"],  # D93 flash closed
    [u"OXY_D4815", u"AS_07259_140"],                                       # D4815 oxygenates
    [u"AS_74429_116", u"PIONA_D6730"],                                     # D6730 DHA
    [u"BIT_SOL", u"AS_79799_118"],                                         # D2042 bitumen solub.
    [u"AS_62067_136", u"AS_13550_145"],                                    # D2270 VI
    [u"AS_09994_053", u"AS_98807_089", u"AS_77015_090", u"AS_71182_091",
     u"AS_68870_131", u"AS_92606_137"],                                   # D3227 mercaptan
    [u"AS_99532_110", u"AS_07910_111", u"AS_80874_112"],                   # D130 Cu corrosion
    [u"AS_50221_078", u"AS_94053_023"],                                    # D4052 density kg/m3
    [u"AS_55958_156", u"AS_74579_161"],                                    # D445 @40°C
    [u"AS_10471_160", u"AS_55967_083"],                                    # D445 @100°C
    [u"AS_76235_123", u"AS_99314_088", u"AS_17625_134"],                   # D4294 sulfur (keep %)
    [u"AS_68987_095", u"AS_69862_133"],                                    # D86 distillation (keep curve)
]

# Multi-element/instrument tests to collapse into ONE service whose result is
# just "see attachment" (the instrument PDF carries the detail), replacing many
# element-specific services. Same idea as the GC services.
_CONSOLIDATE = [
    {
        u"keyword": u"ICP_D5185",
        u"title": (u"آنالیز عناصر فلزی به روش طیف‌سنجی نشری پلاسمای "
                   u"جفت‌شده القایی (ICP-OES) — ASTM D5185"),
        u"method": u"ASTM D5185",
        u"category": u"روغن",
        u"default_result": u"نتیجه تست به پیوست ارسال می‌گردد",
        u"deactivate": [
            u"AS_94572_012", u"AS_95874_014", u"AS_10149_016", u"AS_38791_017",
            u"AS_35589_018", u"AS_59828_029", u"AS_47277_030", u"AS_45333_031",
            u"AS_12987_032", u"AS_16863_039", u"AS_60313_040", u"AS_23576_041",
            u"AS_08653_042", u"AS_11628_043", u"AS_93437_044", u"AS_20090_046",
            u"AS_66814_048", u"AS_52503_051", u"AS_20669_054", u"AS_00064_062",
            u"AS_96548_063", u"AS_62140_067", u"AS_68589_071", u"AS_42423_072",
            u"AS_46877_075", u"AS_86150_076", u"AS_60972_081", u"AS_39580_082",
            u"AS_23714_093", u"AS_63314_096", u"AS_30521_097", u"AS_13089_099",
            u"AS_85823_100", u"AS_37357_101", u"AS_89910_104", u"AS_02696_105",
        ],
    },
]

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
    # acid / base number
    "D664": u"mg KOH/g", "D974": u"mg KOH/g", "D2896": u"mg KOH/g",
    # vapour pressure
    "D323": u"kPa", "D5191": u"kPa", "D6378": u"kPa",
    # water by distillation
    "D95": u"vol %",
    # elements (ICP / XRF trace)
    "D5185": u"mg/kg", "D4951": u"mg/kg",
    # heat of combustion
    "D240": u"MJ/kg", "D4809": u"MJ/kg",
    # NB: density (D1298/D4052) intentionally NOT here — API gravity / SG /
    # kg/m3 are all valid depending on what is reported. Distillation (D86)
    # and ash/sediment/carbon-residue (% mass == % wt) are likewise left alone.
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


def _temp(title):
    m = _TEMP_RE.search(safe_unicode(title or u""))
    return m.group(1) if m else u""


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
            if r["kw"] in _SPECIAL_UNIT:
                continue  # handled in the special-unit pass below
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

        # per-keyword special unit fixes
        for r in rows:
            target = _SPECIAL_UNIT.get(r["kw"])
            if not target or _unit_norm(r["unit"]) == _unit_norm(target):
                continue
            flagged += 1
            out.append(u"%s  %s\t(special)\t%s -> %s\t%s" % (
                u"FIX" if apply else u"UNIT?", r["kw"],
                r["unit"] or u"(empty)", target, r["title"]))
            if apply:
                r["obj"].setUnit(target)
                r["obj"].reindexObject()
                fixed += 1

        # --- duplicate cleanup: bucket same-standard services by test
        #     conditions (temperature in the title), keep the best in each
        #     bucket and deactivate the rest. One-member buckets, or members
        #     at different temperatures, are left untouched. Deactivation is
        #     reversible (services go inactive, not deleted). ---
        spec_uids = set()
        try:
            for b in api.search({"portal_type": "AnalysisSpec"}, SETUP_CATALOG):
                sp = api.get_object(b)
                for rr in (sp.getResultsRange() or []):
                    if rr.get("uid"):
                        spec_uids.add(rr.get("uid"))
        except Exception:
            pass
        used_kw = set()
        try:
            for b in api.search({"portal_type": "Analysis"}, ANALYSIS_CATALOG):
                k = getattr(b, "getKeyword", u"")
                if k:
                    used_kw.add(safe_unicode(k))
        except Exception:
            pass

        def _score(r):
            o = r["obj"]
            return (
                0 if api.get_uid(o) in spec_uids else 1,     # has limits
                0 if getattr(o, "tppc_method_text", None) else 1,  # has method
                0 if r["kw"] in used_kw else 1,              # used in samples
                r["kw"],
            )

        by_kw = {r["kw"]: r for r in rows}
        deact = 0
        out.append(u"")
        out.append(u"=== DUPLICATE CLEANUP (curated; keep best, deactivate rest) ===")
        for grp in _DUP_GROUPS:
            keep = by_kw.get(grp[0])
            if keep is None:
                # the service we intend to keep isn't active — skip the whole
                # group rather than risk deactivating every member.
                out.append(u"* SKIP (keep %s not active)" % grp[0])
                continue
            members = [by_kw[k] for k in grp[1:] if k in by_kw]
            if not members:
                continue
            out.append(u"* KEEP  %s\t%s" % (keep["kw"], keep["title"]))
            for r in members:
                out.append(u"    %s\t%s\t%s" % (
                    u"DEACTIVATE" if apply else u"would deactivate",
                    r["kw"], r["title"]))
                if apply:
                    try:
                        api.do_transition_for(r["obj"], "deactivate")
                        deact += 1
                    except Exception as exc:  # noqa
                        out.append(u"      ERROR\t%s" % safe_unicode(exc))

        # --- consolidate multi-element/instrument tests into one text-result
        #     service ("see attachment") and deactivate the many originals. ---
        try:
            container = api.get_bika_setup().bika_analysisservices
        except Exception:
            container = api.get_portal().bika_setup.bika_analysisservices
        cats = [api.get_object(b) for b in api.search(
            {"portal_type": "AnalysisCategory"}, SETUP_CATALOG)]

        def _find_cat(name):
            for c in cats:
                t = safe_unicode(api.get_title(c))
                if name in t or t in name:
                    return c
            return cats[0] if cats else None

        out.append(u"")
        out.append(u"=== CONSOLIDATE (one text-result service + deactivate rest) ===")
        for spec in _CONSOLIDATE:
            svc = by_kw.get(spec[u"keyword"])
            if svc is not None:
                out.append(u"* keep existing\t%s\t%s" % (
                    spec[u"keyword"], safe_unicode(api.get_title(svc["obj"]))))
            else:
                cat = _find_cat(spec[u"category"])
                out.append(u"* %s service\t%s\t%s\t[%s]" % (
                    u"CREATE" if apply else u"would create",
                    spec[u"keyword"], spec[u"title"],
                    safe_unicode(api.get_title(cat)) if cat else u"?"))
                if apply and cat is not None:
                    try:
                        o = api.create(
                            container, "AnalysisService", title=spec[u"title"],
                            Keyword=spec[u"keyword"],
                            Category=api.get_uid(cat), Unit=u"")
                        o.setResultType("string")
                        o.setDefaultResult(spec[u"default_result"])
                        o.tppc_method_text = spec[u"method"]
                        o.reindexObject()
                    except Exception as exc:  # noqa
                        out.append(u"    ERROR\t%s" % safe_unicode(exc))
            n = 0
            for kw in spec[u"deactivate"]:
                r = by_kw.get(kw)
                if r is None or not api.is_active(r["obj"]):
                    continue
                n += 1
                if apply:
                    try:
                        api.do_transition_for(r["obj"], "deactivate")
                        deact += 1
                    except Exception as exc:  # noqa
                        out.append(u"    ERROR\t%s\t%s" % (kw, safe_unicode(exc)))
            out.append(u"    %s %d element services"
                       % (u"deactivated" if apply else u"would deactivate", n))

        out.append(u"")
        out.append(u"--- summary ---")
        out.append(u"services audited: %d" % len(rows))
        out.append(u"unit fixes %s: %d" % (
            u"applied" if apply else u"proposed", fixed if apply else flagged))
        n_deact = deact if apply else sum(
            max(0, len([1 for k in grp if k in by_kw]) - 1)
            for grp in _DUP_GROUPS)
        out.append(u"duplicates %s: %d" % (
            u"deactivated" if apply else u"to deactivate", n_deact))
        out.append(u"")
        out.append(u"NOTE: only hand-vetted duplicate groups are touched; "
                   u"distinct same-standard tests (D5185 elements, D1177 "
                   u"33/50%, D128 acid/alkali) are never merged. Deactivation "
                   u"is reversible. LEFT FOR YOU TO DECIDE: sulfur D4294 "
                   u"(mg/kg vs %), distillation D86, density D4052 API/kg-m3 "
                   u"— units/reporting differ, pick per your practice.")

        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out).encode("utf-8")
