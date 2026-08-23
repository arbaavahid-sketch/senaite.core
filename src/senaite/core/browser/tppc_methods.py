# -*- coding: utf-8 -*-
#
# One-off admin view to stamp each AnalysisService with its final method /
# standard string (shown in the analysis report's "Test Method" column).
# Matches services by Keyword (AS_xxxxx). Dry-run by default; apply with
# ?apply=1. ManageBika only. Safe to run repeatedly (idempotent).

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

METHOD_STANDARDS = {
    u'AS_93348_001': u'ASTM D2699 / ASTM D2700',
    u'AS_45859_002': u'ASTM D5968 / INSO 22260 / INSO 22260-A1',
    u'AS_80528_003': u'ASTM D6594 / INSO 22260 / INSO 22260-A1',
    u'AS_89969_004': u'ISO 6614',
    u'AS_74465_005': u'AASHTO T102-83',
    u'AS_30633_006': u'INSO 18033',
    u'AS_67685_007': u'INSO 199 / INSO 22260-A1 / INSO 3299',
    u'AS_23337_008': u'ASTM D6304 / IEC 60296 / IEC 60814',
    u'AS_02327_009': u'ASTM D4006 / ASTM D95 / ISIRI 4081 / ISIRI 8139',
    u'AS_71882_010': u'ASTM D6304',
    u'AS_36513_011': u'ASTM D4007',
    u'AS_94572_012': u'INSO 14451 / INSO 21565',
    u'AS_47030_013': u'ISIRI 154',
    u'AS_95874_014': u'INSO 14451',
    u'AS_91033_015': u'ASTM D128 / INSO 565',
    u'AS_10149_016': u'INSO 14451 / INSO 21565 / INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_38791_017': u'INSO 21565 / INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_35589_018': u'INSO 14451 / INSO 21565',
    u'AS_66643_019': u'INSO 15722',
    u'AS_09521_020': u'ASTM D482 / INSO 12480 / INSO 17142 / INSO 2940',
    u'AS_78253_021': u'INSO 3299 / ISIRI 336',
    u'AS_98760_022': u'ASTM D1481',
    u'AS_94053_023': u'ASTM D4052',
    u'AS_97955_024': u'ASTM E2193',
    u'AS_87712_025': u'ASTM D473',
    u'AS_79882_026': u'ASTM D1500 / INSO 203',
    u'AS_63324_027': u'ASTM D156 / INSO 2932',
    u'AS_76436_028': u'INSO 2544',
    u'AS_59828_029': u'INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_47277_030': u'INSO 14451 / INSO 21565',
    u'AS_45333_031': u'INSO 14451 / INSO 21565',
    u'AS_12987_032': u'INSO 14451 / INSO 21565',
    u'AS_99825_033': u'INSO 18030 / INSO 199 / INSO 22260 / INSO 22261 / INSO 6423',
    u'AS_40113_034': u'ASTM D664',
    u'AS_03506_035': u'ASTM D2700',
    u'AS_13570_036': u'INSO 22260 / INSO 22261 / INSO 2772 / INSO 3299',
    u'AS_83735_037': u'ASTM D2896 / INSO 2772',
    u'AS_44049_038': u'ASTM D2896 / INSO 2772',
    u'AS_16863_039': u'INSO 14451',
    u'AS_60313_040': u'INSO 14451 / INSO 21565',
    u'AS_23576_041': u'INSO 14451',
    u'AS_08653_042': u'INSO 14451',
    u'AS_11628_043': u'INSO 14451',
    u'AS_93437_044': u'INSO 14451',
    u'AS_30561_045': u'INSO 11541',
    u'AS_20090_046': u'INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_85250_047': u'ASTM D323 / INSO 5439 / ISIRI 5439',
    u'AS_66814_048': u'INSO 14451 / INSO 21565',
    u'AS_97511_049': u'ASTM D128 / INSO 565',
    u'AS_15785_050': u'INSO 22260-A1',
    u'AS_52503_051': u'INSO 14451',
    u'AS_43069_052': u'ASTM D1078',
    u'AS_09994_053': u'ASTM UOP 163',
    u'AS_20669_054': u'INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_88113_055': u'ASTM D6304 / ASTM E1064 / INSO 3299',
    u'AS_29929_056': u'ASTM E2313',
    u'AS_89889_057': u'ASTM E1615',
    u'AS_53446_058': u'ASTM D1613',
    u'AS_39409_059': u'ASTM D482 / INSO 3299',
    u'AS_21031_060': u'ASTM D1209',
    u'AS_18021_061': u'ASTM E2469',
    u'AS_00064_062': u'INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_96548_063': u'INSO 14451 / INSO 21565 / INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_36104_064': u'INSO 2940',
    u'AS_49176_065': u'ASTM D482 / INSO 2940',
    u'AS_14674_066': u'INSO 194 / INSO 22260',
    u'AS_62140_067': u'INSO 14451 / INSO 21565',
    u'AS_79390_068': u'ASTM D93 / INSO 19695',
    u'AS_96932_069': u'ASTM D93 / INSO 19695',
    u'AS_81768_070': u'ASTM D3828',
    u'AS_68589_071': u'INSO 14451 / INSO 21565',
    u'AS_42423_072': u'INSO 14451 / INSO 21565',
    u'AS_79247_073': u'ASTM D445 / ASTM D446',
    u'AS_43124_074': u'ASTM D7279',
    u'AS_46877_075': u'INSO 14451',
    u'AS_86150_076': u'INSO 14451',
    u'AS_45240_077': u'INSO 197 / INSO 3299 / ISIRI 197',
    u'AS_50221_078': u'ASTM D4052',
    u'AS_13598_079': u'ASTM D4052',
    u'AS_45447_080': u'ASTM D1298 / INSO 197',
    u'AS_60972_081': u'INSO 14451 / INSO 21565',
    u'AS_39580_082': u'INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 9377',
    u'AS_55967_083': u'INSO 3299 / INSO 340',
    u'AS_47794_084': u'INSO 8575',
    u'AS_33184_085': u'ASTM D445 / INSO 340',
    u'AS_45235_086': u'INSO 340',
    u'AS_30387_087': u'ASTM D4052',
    u'AS_99314_088': u'ASTM D4294 / INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 3299 / INSO 8402 / INSO 9377',
    u'AS_98807_089': u'ASTM D3227',
    u'AS_77015_090': u'ASTM D3227 / INSO 9379',
    u'AS_71182_091': u'ASTM D3227 / INSO 9397',
    u'AS_43069_092': u'ASTM D6304 / INSO 2975 / INSO 6423',
    u'AS_23714_093': u'INSO 21565',
    u'AS_17219_094': u'INSO 17268',
    u'AS_68987_095': u'ASTM D86 / INSO 6261 / ISIRI 4081',
    u'AS_63314_096': u'INSO 21565 / INSO 9377',
    u'AS_30521_097': u'INSO 21565 / INSO 9377',
    u'AS_86966_098': u'INSO 18030',
    u'AS_13089_099': u'INSO 14451 / INSO 21565 / INSO 9377',
    u'AS_85823_100': u'INSO 21565 / INSO 9377',
    u'AS_37357_101': u'INSO 21565 / INSO 9377',
    u'AS_58943_102': u'ASTM D93 / INSO 19695',
    u'AS_24745_103': u'ASTM D5853 / ASTM D97 / INSO 1218 / INSO 17142 / INSO 201 / INSO 22260-A1 / INSO 22261 / INSO 2975 / INSO 3299 / INSO 6423',
    u'AS_89910_104': u'INSO 14451 / INSO 21565',
    u'AS_02696_105': u'INSO 14451 / INSO 21565 / INSO 9377',
    u'AS_89052_106': u'INSO 1218 / INSO 340',
    u'AS_73057_107': u'ASTM D4052',
    u'AS_56620_108': u'INSO 19451',
    u'AS_59922_109': u'ASTM D130',
    u'AS_99532_110': u'ASTM D130 / INSO 1218 / INSO 2975 / ISIRI 336',
    u'AS_07910_111': u'ASTM D130 / ASTM D4048 / INSO 11291',
    u'AS_80874_112': u'ASTM D130 / ISIRI 336',
    u'AS_90066_113': u'ASTM D6729 / ASTM D6730',
    u'AS_10666_114': u'ASTM D6730 / INSO 22888',
    u'AS_30166_115': u'ASTM D6729 / ASTM D6730',
    u'AS_74429_116': u'ASTM D6730',
    u'AS_86548_117': u'INSO 16037 / ISO 3838',
    u'AS_79799_118': u'INSO 12505-1',
    u'AS_12667_119': u'ASTM D1404 / INSO 1095',
    u'AS_30884_120': u'ASTM D1500 / INSO 203 / INSO 3299 / INSO 4903 / INSO 6423',
    u'AS_37898_121': u'ASTM D7946 / INSO 20273',
    u'AS_24154_122': u'IEC 60666',
    u'AS_76235_123': u'ASTM D4294 / INSO 8402 / ISIRI 336',
    u'AS_69402_124': u'ASTM D4294 / INSO 8402',
    u'AS_71450_125': u'ASTM D4294 / INSO 8402',
    u'AS_53330_126': u'ASTM D2500 / INSO 5438',
    u'AS_55943_127': u'IEC 60296 / ISO 2719',
    u'AS_70565_128': u'ASTM D1120 / INSO 1213',
    u'AS_48963_129': u'IEC 60296 / INSO 22260 / ISO 3016',
    u'AS_29417_130': u'IEC 60296 / ISO 3104',
    u'AS_68870_131': u'ASTM D3227 / INSO 9379',
    u'AS_38527_132': u'ASTM D86 / INSO 6261',
    u'AS_69862_133': u'ASTM D86 / INSO 6261',
    u'AS_17625_134': u'ASTM D4294 / ASTM D7039 / INSO 17142',
    u'AS_05891_135': u'INSO 6423 / ISIRI 336',
    u'AS_62067_136': u'INSO 195 / INSO 2975 / INSO 3299 / INSO 6423',
    u'AS_92606_137': u'ASTM D3227',
    u'AS_21818_138': u'ASTM E2412',
    u'AS_58729_139': u'INSO 199 / INSO 2772 / INSO 2975',
    u'AS_07259_140': u'ASTM D4815',
    u'AS_77332_141': u'INSO 17761',
    u'AS_24337_142': u'ASTM D4737 / INSO 8525',
    u'AS_27082_143': u'INSO 8525',
    u'AS_27764_144': u'ASTM D976',
    u'AS_13550_145': u'ASTM D2270 / INSO 195',
    u'AS_42807_146': u'INSO 19534',
    u'AS_71964_147': u'IEC 60296 / ISO 3104',
    u'AS_59447_148': u'ASTM D893 / INSO 2975',
    u'AS_05147_149': u'ASTM D93 / INSO 17142 / INSO 198 / INSO 22260 / INSO 22260-A1 / INSO 22261 / INSO 2975 / INSO 3299',
    u'AS_10878_150': u'IGS-C-TP-016(0)',
    u'AS_67907_151': u'ASTM D4057 / INSO 4189',
    u'AS_84661_152': u'Oil Analysis Noria Tribolo',
    u'AS_97917_153': u'INSO 22260-A1',
    u'AS_55110_154': u'INSO 17764 / INSO 22260 / INSO 22260-A1 / INSO 22261',
    u'AS_62644_155': u'ASTM D1298 / ASTM D4052 / INSO 17142 / INSO 197',
    u'AS_55958_156': u'ASTM D445 / INSO 3299 / INSO 340',
    u'AS_03300_157': u'INSO 22260 / INSO 22261 / INSO 340',
    u'AS_99740_158': u'ASTM D5481 / INSO 22260 / INSO 22261',
    u'AS_90904_159': u'ASTM D445 / ASTM D7042 / INSO 17142',
    u'AS_10471_160': u'INSO 2975 / INSO 340 / INSO 6423',
    u'AS_74579_161': u'INSO 2975 / INSO 340 / INSO 6423',
}


class ApplyMethodStandardsView(BrowserView):
    """Stamp AnalysisService.tppc_method_text from METHOD_STANDARDS by Keyword."""

    def __call__(self):
        apply = bool(self.request.get("apply"))
        matched = updated = 0
        unmatched = []
        seen_keywords = set()
        lines = []

        for brain in api.search({"portal_type": "AnalysisService"},
                                SETUP_CATALOG):
            obj = api.get_object(brain)
            kw = obj.getKeyword() or ""
            seen_keywords.add(kw)
            std = METHOD_STANDARDS.get(kw)
            if not std:
                unmatched.append(u"%s | %s" % (kw, safe_unicode(api.get_title(obj))))
                continue
            matched += 1
            current = safe_unicode(getattr(obj, "tppc_method_text", u"") or u"")
            if current != std:
                if apply:
                    obj.tppc_method_text = std
                    obj.reindexObject()
                updated += 1
                lines.append(u"%s\t%s\t%s" % (kw, safe_unicode(api.get_title(obj)), std))

        missing = [k for k in METHOD_STANDARDS if k not in seen_keywords]

        out = []
        out.append(u"MODE: %s" % (u"APPLIED" if apply else u"DRY-RUN (add ?apply=1 to write)"))
        out.append(u"services on server: %d" % len(seen_keywords))
        out.append(u"matched to mapping: %d" % matched)
        out.append(u"to update / updated: %d" % updated)
        out.append(u"server services NOT in mapping: %d" % len(unmatched))
        out.append(u"mapping keys NOT on server: %d" % len(missing))
        out.append(u"")
        out.append(u"--- server services without a mapping (keyword | title) ---")
        out.extend(unmatched)
        out.append(u"")
        out.append(u"--- mapping keys not found on server ---")
        out.extend(missing)
        out.append(u"")
        out.append(u"--- changes (keyword \t title \t standard) ---")
        out.extend(lines)

        self.request.response.setHeader("Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(out).encode("utf-8")
