# -*- coding: utf-8 -*-
#
# Controlled-document review status overview (Tandis / TPPC, ISO 17025 clause
# 8.3). Lists controlled documents with their next review date, days remaining,
# and a status flag (up to date / due soon / overdue / no review date).
# Bilingual: Persian (fa, RTL) / English (en, LTR).

import math
from datetime import date

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims import api
from senaite.core.catalog import SETUP_CATALOG


DEFAULT_DAYS = 30

LABELS = {
    "fa": {
        "title": u"وضعیت بازنگری اسناد کنترل‌شده",
        "intro": u"تاریخ بازنگری بعدی هر سند و روزهای مانده تا سررسید بازنگری.",
        "window": u"آستانهٔ هشدار (روز):",
        "apply": u"اعمال",
        "col_code": u"کد",
        "col_title": u"عنوان",
        "col_type": u"نوع",
        "col_version": u"نسخه",
        "col_state": u"وضعیت سند",
        "col_review": u"بازنگری بعدی",
        "col_days": u"روز مانده",
        "col_status": u"وضعیت بازنگری",
        "empty": u"سندی ثبت نشده است",
        "st_ok": u"به‌روز",
        "st_due": u"نزدیک به بازنگری",
        "st_over": u"سررسید گذشته",
        "st_none": u"بدون تاریخ بازنگری",
        "sum_total": u"کل اسناد",
        "note": (u"«روز مانده» بر اساس «تاریخ بازنگری بعدی» محاسبه می‌شود. طبق "
                 u"ISO/IEC 17025 اسناد باید در بازه‌های معین بازنگری و به‌روز شوند."),
    },
    "en": {
        "title": u"Controlled Document Review Status",
        "intro": u"Next review date of each document and the days remaining until review is due.",
        "window": u"Warning window (days):",
        "apply": u"Apply",
        "col_code": u"Code",
        "col_title": u"Title",
        "col_type": u"Type",
        "col_version": u"Version",
        "col_state": u"Document state",
        "col_review": u"Next review",
        "col_days": u"Days left",
        "col_status": u"Review status",
        "empty": u"No documents registered",
        "st_ok": u"Up to date",
        "st_due": u"Due soon",
        "st_over": u"Overdue",
        "st_none": u"No review date",
        "sum_total": u"Total documents",
        "note": (u'"Days left" is based on the "Next review" date. Under ISO/IEC 17025 '
                 u'documents must be reviewed and kept up to date at defined intervals.'),
    },
}

STATUS_CSS = {
    "ok": "text-success",
    "due": "text-warning",
    "over": "text-danger",
    "none": "text-muted",
}


class DocumentReviewStatusView(BrowserView):
    template = ViewPageTemplateFile("templates/status.pt")

    def __call__(self):
        try:
            self.days = int(self.request.get("days", DEFAULT_DAYS))
        except (TypeError, ValueError):
            self.days = DEFAULT_DAYS
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

    def _days_to(self, review_date):
        if not review_date:
            return None
        try:
            # schema.Date stores a datetime.date
            delta = (review_date - date.today()).days
            return int(math.ceil(delta))
        except Exception:
            return None

    def _status_key(self, days, has_date):
        if not has_date or days is None:
            return "none"
        if days < 0:
            return "over"
        if days <= self.days:
            return "due"
        return "ok"

    def _fmt_date(self, value):
        if not value:
            return "-"
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value)

    def get_rows(self):
        catalog = api.get_tool(SETUP_CATALOG)
        brains = catalog({"portal_type": "ControlledDocument"})
        rows = []
        for brain in brains:
            try:
                obj = api.get_object(brain)
            except Exception:
                continue
            review_date = getattr(obj, "review_date", None)
            days = self._days_to(review_date)
            status = self._status_key(days, review_date is not None)
            rows.append({
                "code": getattr(obj, "document_id", "") or "-",
                "title": getattr(obj, "title", "") or api.get_title(obj),
                "url": api.get_url(obj),
                "type": getattr(obj, "document_type", "") or "-",
                "version": getattr(obj, "version", "") or "-",
                "state": api.get_review_status(obj),
                "review": self._fmt_date(review_date),
                "days": days,
                "status": status,
                "status_label": self.labels["st_%s" % {
                    "ok": "ok", "due": "due",
                    "over": "over", "none": "none"}[status]],
                "status_css": STATUS_CSS[status],
            })
        order = {"over": 0, "due": 1, "ok": 2, "none": 3}

        def sort_key(r):
            d = r["days"]
            d = d if d is not None else 10 ** 9
            return (order[r["status"]], d)

        rows.sort(key=sort_key)
        return rows

    def get_summary(self, rows):
        summary = {"total": len(rows), "ok": 0, "due": 0, "over": 0, "none": 0}
        for r in rows:
            summary[r["status"]] += 1
        return summary
