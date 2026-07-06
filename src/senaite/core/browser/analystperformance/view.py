# -*- coding: utf-8 -*-
#
# Analyst performance report (Tandis / TPPC).
# Shows, per analyst, how many analyses were performed (result captured) and the
# revenue generated (sum of analysis prices) within an optional date range.
# Bilingual: labels switch between Persian (fa, RTL) and English (en, LTR)
# according to the current site language.

from DateTime import DateTime
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims import api
from senaite.core.catalog import ANALYSIS_CATALOG


LABELS = {
    "fa": {
        "title": u"عملکرد آزمونگرها",
        "intro": u"تعداد آزمون‌های انجام‌شده (نتیجهٔ ثبت‌شده) و درآمد هر آزمونگر.",
        "from": u"از تاریخ:",
        "to": u"تا تاریخ:",
        "apply": u"اعمال فیلتر",
        "all": u"همه",
        "col_analyst": u"آزمونگر",
        "col_count": u"تعداد آزمون انجام‌شده",
        "col_revenue": u"درآمد",
        "total": u"جمع کل",
        "empty": u"داده‌ای برای این بازه موجود نیست",
        "note": (u"«درآمد» جمع قیمت آزمون‌هاست؛ تا زمانی که قیمت آزمون‌ها وارد نشود، "
                 u"صفر نمایش داده می‌شود. «تعداد آزمون» بر اساس تاریخ ثبت نتیجه محاسبه می‌شود."),
    },
    "en": {
        "title": u"Analyst Performance",
        "intro": u"Number of analyses performed (results captured) and revenue generated per analyst.",
        "from": u"From:",
        "to": u"To:",
        "apply": u"Apply filter",
        "all": u"All",
        "col_analyst": u"Analyst",
        "col_count": u"Analyses performed",
        "col_revenue": u"Revenue",
        "total": u"Total",
        "empty": u"No data for this period",
        "note": (u'"Revenue" is the sum of analysis prices; it shows zero until prices '
                 u'are entered. "Analyses performed" is based on the result capture date.'),
    },
}


class AnalystPerformanceView(BrowserView):
    template = ViewPageTemplateFile("templates/performance.pt")

    def __call__(self):
        self.date_from = self.request.get("from", "")
        self.date_to = self.request.get("to", "")
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        return self.template()

    def _lang(self):
        try:
            ltool = getToolByName(self.context, "portal_languages")
            lang = ltool.getPreferredLanguage()
        except Exception:
            lang = "fa"
        # Normalise things like "en-us" -> "en"; fall back to en for anything
        # we do not have labels for.
        lang = (lang or "fa").split("-")[0].lower()
        return lang if lang in LABELS else "en"

    def _fullname(self, username):
        if not username or username == "-":
            return username
        mtool = getToolByName(self.context, "portal_membership")
        member = mtool.getMemberById(username)
        if member is not None:
            fullname = member.getProperty("fullname", "")
            if fullname:
                return fullname
        return username

    def _date_query(self):
        dmin = dmax = None
        try:
            if self.date_from:
                dmin = DateTime(self.date_from)
            if self.date_to:
                dmax = DateTime(self.date_to + " 23:59:59")
        except Exception:
            return None
        if dmin and dmax:
            return {"query": [dmin, dmax], "range": "min:max"}
        if dmin:
            return {"query": dmin, "range": "min"}
        if dmax:
            return {"query": dmax, "range": "max"}
        return None

    def get_rows(self):
        catalog = api.get_tool(ANALYSIS_CATALOG)
        query = {"portal_type": "Analysis"}
        date_query = self._date_query()
        if date_query:
            query["getResultCaptureDate"] = date_query

        stats = {}
        for brain in catalog(query):
            if not brain.getResultCaptureDate:
                continue
            # getAnalyst is an index (not metadata), so read it from the object.
            try:
                obj = brain.getObject()
            except Exception:
                continue
            analyst = obj.getAnalyst() or "-"
            row = stats.setdefault(analyst, {"count": 0, "revenue": 0.0})
            row["count"] += 1
            try:
                row["revenue"] += float(obj.getPrice() or 0)
            except Exception:
                pass

        rows = []
        for analyst, data in stats.items():
            rows.append({
                "analyst": self._fullname(analyst),
                "username": analyst,
                "count": data["count"],
                "revenue": data["revenue"],
            })
        rows.sort(key=lambda r: r["count"], reverse=True)
        return rows

    def get_totals(self, rows):
        return {
            "count": sum([r["count"] for r in rows]),
            "revenue": sum([r["revenue"] for r in rows]),
        }

    def fmt(self, value):
        try:
            return "{:,.0f}".format(float(value))
        except Exception:
            return value
