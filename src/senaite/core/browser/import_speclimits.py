# -*- coding: utf-8 -*-
#
# One-off admin tool: import Analysis Specifications (result ranges / محدوده)
# from the reviewed spec-limits sheet. Groups embedded rows by product =
# SampleType, resolves each analysis by Keyword, and creates/updates one
# AnalysisSpec per SampleType (merging into an existing spec if present).
# Dry-run by default; ?apply=1 writes. ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

SPEC_LIMITS = [
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_97955_024', u'min': u'70', u'max': u''},
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_88113_055', u'min': u'', u'max': u'0.05'},
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_89889_057', u'min': u'', u'max': u'0.1'},
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_53446_058', u'min': u'', u'max': u'0.002'},
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_21031_060', u'min': u'', u'max': u'5'},
    {u'product': u'اتیلن گلایکول', u'keyword': u'AS_18021_061', u'min': u'', u'max': u'0.2'},
    {u'product': u'بنزین', u'keyword': u'AS_93348_001', u'min': u'95', u'max': u''},
    {u'product': u'بنزین', u'keyword': u'AS_03506_035', u'min': u'85', u'max': u''},
    {u'product': u'بنزین', u'keyword': u'AS_99532_110', u'min': u'', u'max': u'1'},
    {u'product': u'بنزین', u'keyword': u'AS_76235_123', u'min': u'', u'max': u'10'},
    {u'product': u'بنزین', u'keyword': u'AS_71450_125', u'min': u'', u'max': u'10'},
    {u'product': u'بنزین بدون سرب', u'keyword': u'AS_71450_125', u'min': u'', u'max': u'10'},
    {u'product': u'بیودیزل', u'keyword': u'AS_79390_068', u'min': u'93', u'max': u''},
    {u'product': u'بیودیزل', u'keyword': u'AS_76235_123', u'min': u'', u'max': u'15'},
    {u'product': u'روغن ترانسفورماتور', u'keyword': u'AS_23337_008', u'min': u'', u'max': u'30'},
    {u'product': u'روغن ترانسفورماتور', u'keyword': u'AS_55943_127', u'min': u'135', u'max': u''},
    {u'product': u'روغن ترانسفورماتور', u'keyword': u'AS_48963_129', u'min': u'', u'max': u'-40'},
    {u'product': u'روغن ترانسفورماتور', u'keyword': u'AS_29417_130', u'min': u'', u'max': u'12'},
    {u'product': u'سوخت بیودیزل', u'keyword': u'AS_76235_123', u'min': u'', u'max': u'15'},
    {u'product': u'سوخت توربین', u'keyword': u'AS_79390_068', u'min': u'38', u'max': u''},
    {u'product': u'سوخت جت', u'keyword': u'AS_76235_123', u'min': u'', u'max': u'0.3'},
    {u'product': u'سوخت موتور های توربینی هوایی', u'keyword': u'AS_68870_131', u'min': u'', u'max': u'0.003'},
    {u'product': u'سوخت هواپیما', u'keyword': u'AS_99532_110', u'min': u'', u'max': u'1'},
    {u'product': u'قیر خالص درجه بندی شده براساس درجه نفوذ', u'keyword': u'AS_79799_118', u'min': u'99', u'max': u''},
    {u'product': u'مایعات خنک کننده موتور', u'keyword': u'AS_70565_128', u'min': u'108', u'max': u''},
    {u'product': u'مخلوط های بیودیزل', u'keyword': u'AS_79390_068', u'min': u'52', u'max': u''},
    {u'product': u'نفت سفید', u'keyword': u'AS_79390_068', u'min': u'38', u'max': u''},
    {u'product': u'نفت سفید', u'keyword': u'AS_71182_091', u'min': u'', u'max': u'0.0025'},
    {u'product': u'نفت سفید', u'keyword': u'AS_99532_110', u'min': u'', u'max': u'1'},
    {u'product': u'نفت سفید', u'keyword': u'AS_76235_123', u'min': u'', u'max': u'0.1'},
    {u'product': u'نفت سفید', u'keyword': u'AS_68870_131', u'min': u'', u'max': u'0.0025'},
    {u'product': u'نفت سفید', u'keyword': u'AS_92606_137', u'min': u'', u'max': u'0.0025'},
    {u'product': u'نفت گاز', u'keyword': u'AS_23337_008', u'min': u'', u'max': u'200'},
    {u'product': u'نفت گاز', u'keyword': u'AS_78253_021', u'min': u'', u'max': u'1'},
    {u'product': u'نفت گاز', u'keyword': u'AS_49176_065', u'min': u'', u'max': u'0.01'},
    {u'product': u'نفت گاز', u'keyword': u'AS_79390_068', u'min': u'55', u'max': u''},
    {u'product': u'نفت گاز', u'keyword': u'AS_96932_069', u'min': u'55', u'max': u''},
    {u'product': u'نفت گاز', u'keyword': u'AS_45447_080', u'min': u'820', u'max': u'845'},
    {u'product': u'نفت گاز', u'keyword': u'AS_99532_110', u'min': u'', u'max': u'1'},
    {u'product': u'نفت گاز', u'keyword': u'AS_27082_143', u'min': u'46', u'max': u''},
    {u'product': u'نفت گاز', u'keyword': u'AS_55958_156', u'min': u'2', u'max': u'4.5'},
]


class ImportSpecLimitsView(BrowserView):
    """Create/update AnalysisSpec objects from SPEC_LIMITS (by SampleType)."""

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)")]

        # keyword -> service uid
        kw2uid = {}
        for brain in api.search({"portal_type": "AnalysisService"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            kw = safe_unicode(obj.getKeyword() or u"")
            if kw:
                kw2uid[kw] = api.get_uid(obj)

        # sample type title -> (uid, object)
        st_by_title = {}
        for brain in api.search({"portal_type": "SampleType"}, SETUP_CATALOG):
            obj = api.get_object(brain)
            st_by_title[safe_unicode(api.get_title(obj))] = obj

        # specs container + existing spec per sample type uid
        try:
            container = api.get_bika_setup().bika_analysisspecs
        except Exception:
            container = api.get_portal().bika_setup.bika_analysisspecs
        spec_by_stuid = {}
        for spec in container.objectValues():
            try:
                stuid = spec.getRawSampleType()
            except Exception:
                stuid = None
            if stuid:
                spec_by_stuid[stuid] = spec

        # group rows by product
        groups = {}
        for row in SPEC_LIMITS:
            groups.setdefault(row["product"], []).append(row)

        created = updated = skipped_prod = skipped_kw = 0
        lines = []
        for product in sorted(groups.keys()):
            st = st_by_title.get(product)
            if st is None:
                skipped_prod += 1
                lines.append(u"NO SAMPLE TYPE\t%s" % product)
                continue
            st_uid = api.get_uid(st)
            # build new ranges keyed by service uid
            new_ranges = {}
            for row in groups[product]:
                uid = kw2uid.get(row["keyword"])
                if not uid:
                    skipped_kw += 1
                    lines.append(u"  no service\t%s\t%s" % (
                        product, row["keyword"]))
                    continue
                new_ranges[uid] = {
                    "keyword": row["keyword"], "uid": uid,
                    "min": row["min"], "max": row["max"],
                    "warn_min": row["min"], "warn_max": row["max"],
                    "error": "", "min_operator": "geq", "max_operator": "leq",
                }
            if not new_ranges:
                continue

            spec = spec_by_stuid.get(st_uid)
            n = len(new_ranges)
            if spec is not None:
                lines.append(u"UPDATE\t%s\t(%d ranges)" % (product, n))
                if apply:
                    merged = {}
                    for rr in (spec.getResultsRange() or []):
                        u = rr.get("uid")
                        if u:
                            merged[u] = dict(rr)
                    merged.update(new_ranges)
                    spec.setResultsRange(list(merged.values()))
                    spec.reindexObject()
                updated += 1
            else:
                lines.append(u"CREATE\t%s\t(%d ranges)" % (product, n))
                if apply:
                    api.create(container, "AnalysisSpec", title=product,
                               SampleType=st_uid,
                               ResultsRange=list(new_ranges.values()))
                created += 1

        summary = [
            u"", u"products in sheet: %d" % len(groups),
            u"created: %d" % created, u"updated: %d" % updated,
            u"products with no matching SampleType: %d" % skipped_prod,
            u"rows with no matching service: %d" % skipped_kw,
            u"", u"--- details ---",
        ]
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out + summary + lines).encode("utf-8")
