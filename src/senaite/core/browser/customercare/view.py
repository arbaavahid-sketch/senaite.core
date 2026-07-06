# -*- coding: utf-8 -*-
#
# Customer-care overview dashboard (Tandis / TPPC). Summarises open complaints
# (ISO/IEC 17025 clause 7.9), open support requests and customer satisfaction
# survey scores. Bilingual: Persian (fa, RTL) / English (en, LTR).

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims import api
from senaite.core.catalog import SETUP_CATALOG

OPEN_STATES = ("received", "in_progress")

LABELS = {
    "fa": {
        "title": u"داشبورد امور مشتریان",
        "intro": u"خلاصهٔ شکایات، درخواست‌های پشتیبانی و رضایت مشتری.",
        "complaints": u"شکایات (ISO 7.9)",
        "support": u"درخواست‌های پشتیبانی",
        "surveys": u"نظرسنجی رضایت",
        "total": u"کل",
        "open": u"باز",
        "closed": u"بسته/حل‌شده",
        "avg_overall": u"میانگین رضایت کلی",
        "avg_time": u"میانگین به‌موقع‌بودن",
        "avg_quality": u"میانگین کیفیت نتایج",
        "avg_comm": u"میانگین ارتباطات",
        "responses": u"تعداد پاسخ‌ها",
        "col_subject": u"موضوع",
        "col_client": u"مشتری",
        "col_severity": u"شدت",
        "col_state": u"وضعیت",
        "open_complaints": u"شکایات باز",
        "none": u"موردی نیست",
        "of5": u"از ۵",
        "note": u"شکایات باز باید طبق بند ۷.۹ استاندارد ISO/IEC 17025 پیگیری و بسته شوند.",
    },
    "en": {
        "title": u"Customer Care Dashboard",
        "intro": u"Summary of complaints, support requests and customer satisfaction.",
        "complaints": u"Complaints (ISO 7.9)",
        "support": u"Support requests",
        "surveys": u"Satisfaction survey",
        "total": u"Total",
        "open": u"Open",
        "closed": u"Closed/resolved",
        "avg_overall": u"Avg overall satisfaction",
        "avg_time": u"Avg timeliness",
        "avg_quality": u"Avg result quality",
        "avg_comm": u"Avg communication",
        "responses": u"Responses",
        "col_subject": u"Subject",
        "col_client": u"Client",
        "col_severity": u"Severity",
        "col_state": u"State",
        "open_complaints": u"Open complaints",
        "none": u"Nothing to show",
        "of5": u"of 5",
        "note": u"Open complaints must be tracked and closed per ISO/IEC 17025 clause 7.9.",
    },
}


class CustomerCareStatusView(BrowserView):
    template = ViewPageTemplateFile("templates/status.pt")

    def __call__(self):
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        return self.template()

    def _lang(self):
        try:
            ltool = getToolByName(self.context, "portal_languages")
            lang = (ltool.getPreferredLanguage() or "fa").split("-")[0].lower()
        except Exception:
            lang = "fa"
        return lang if lang in LABELS else "en"

    def _brains(self, portal_type):
        catalog = api.get_tool(SETUP_CATALOG)
        return catalog({"portal_type": portal_type})

    def _count_states(self, portal_type):
        total = open_ = 0
        for brain in self._brains(portal_type):
            total += 1
            if brain.review_state in OPEN_STATES:
                open_ += 1
        return {"total": total, "open": open_, "closed": total - open_}

    def complaints_summary(self):
        return self._count_states("Complaint")

    def support_summary(self):
        return self._count_states("SupportRequest")

    def open_complaints(self):
        rows = []
        for brain in self._brains("Complaint"):
            if brain.review_state not in OPEN_STATES:
                continue
            obj = api.get_object(brain)
            rows.append({
                "subject": getattr(obj, "title", "") or api.get_title(obj),
                "url": api.get_url(obj),
                "client": getattr(obj, "client_name", "") or "-",
                "severity": getattr(obj, "severity", "") or "-",
                "state": api.get_review_status(obj),
            })
        return rows

    def surveys_summary(self):
        fields = ["rating_overall", "rating_timeliness",
                  "rating_quality", "rating_communication"]
        sums = dict((f, 0) for f in fields)
        counts = dict((f, 0) for f in fields)
        n = 0
        for brain in self._brains("Survey"):
            obj = api.get_object(brain)
            n += 1
            for f in fields:
                val = getattr(obj, f, None)
                try:
                    if val is not None:
                        sums[f] += int(val)
                        counts[f] += 1
                except Exception:
                    pass

        def avg(f):
            if counts[f]:
                return round(float(sums[f]) / counts[f], 1)
            return None

        return {
            "responses": n,
            "overall": avg("rating_overall"),
            "timeliness": avg("rating_timeliness"),
            "quality": avg("rating_quality"),
            "communication": avg("rating_communication"),
        }
