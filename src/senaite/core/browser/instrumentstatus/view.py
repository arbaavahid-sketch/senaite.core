# -*- coding: utf-8 -*-
#
# Instrument calibration/certification status overview (Tandis / TPPC).
# Lists every instrument with its latest certification, the days remaining
# until it expires, and a status flag (valid / due soon / expired / no
# certificate). This is the cross-instrument "what is expiring soon" view that
# SENAITE lacks natively (it only exposes a per-instrument certifications tab).
# Bilingual: labels switch between Persian (fa, RTL) and English (en, LTR).

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims import api
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.api.instrumentcertification import get_certificate_status


# Default "due soon" window in days when no ?days= is supplied.
DEFAULT_DAYS = 30

LABELS = {
    "fa": {
        "title": u"وضعیت کالیبراسیون دستگاه‌ها",
        "intro": u"وضعیت اعتبار گواهی‌های ثبت‌شدهٔ هر دستگاه و روزهای مانده تا انقضا.",
        "window": u"آستانهٔ هشدار (روز):",
        "apply": u"اعمال",
        "col_instrument": u"دستگاه",
        "col_type": u"نوع",
        "col_serial": u"شمارهٔ سریال",
        "col_validto": u"اعتبار تا",
        "col_days": u"روز مانده",
        "col_status": u"وضعیت",
        "empty": u"دستگاهی ثبت نشده است",
        "st_valid": u"معتبر",
        "st_due": u"نزدیک به انقضا",
        "st_expired": u"منقضی",
        "st_none": u"گواهی ثبت نشده",
        "st_unknown": u"اطلاعات گواهی ناقص یا نامشخص",
        "st_future": u"اعتبار هنوز شروع نشده",
        "sum_total": u"کل دستگاه‌ها",
        "note": (u"این وضعیت بر اساس بازهٔ زمانی ثبت‌شدهٔ گواهی محاسبه می‌شود. "
                 u"صلاحیت دستگاه و دامنهٔ گواهی باید توسط مسئول فنی بررسی شود."),
    },
    "en": {
        "title": u"Instrument Calibration Status",
        "intro": u"Registered certificate validity and days remaining until expiry for each instrument.",
        "window": u"Warning window (days):",
        "apply": u"Apply",
        "col_instrument": u"Instrument",
        "col_type": u"Type",
        "col_serial": u"Serial no.",
        "col_validto": u"Valid to",
        "col_days": u"Days left",
        "col_status": u"Status",
        "empty": u"No instruments registered",
        "st_valid": u"Valid",
        "st_due": u"Due soon",
        "st_expired": u"Expired",
        "st_none": u"No certificate",
        "st_unknown": u"Incomplete or unknown certificate information",
        "st_future": u"Validity has not started",
        "sum_total": u"Total instruments",
        "note": (u'Status is based on the recorded certificate validity interval. '
                 u'Instrument suitability and certificate scope require technical review.'),
    },
}

# CSS colour class per status key, used by the template.
STATUS_CSS = {
    "valid": "text-success",
    "due": "text-warning",
    "expired": "text-danger",
    "none": "text-muted",
    "unknown": "text-warning",
    "future": "text-info",
}


class InstrumentStatusView(BrowserView):
    template = ViewPageTemplateFile("templates/status.pt")

    def __call__(self):
        try:
            self.days = int(self.request.get("days", DEFAULT_DAYS))
        except (TypeError, ValueError):
            self.days = DEFAULT_DAYS
        self.days = max(1, self.days)
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

    def _fmt_date(self, dt):
        if not dt:
            return "-"
        try:
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return str(dt)

    def _type_name(self, obj):
        try:
            itype = obj.getInstrumentType()
        except Exception:
            itype = None
        if itype:
            try:
                return api.get_title(itype)
            except Exception:
                pass
        return "-"

    def get_rows(self):
        catalog = api.get_tool(SETUP_CATALOG)
        brains = catalog({"portal_type": "Instrument"})
        rows = []
        for brain in brains:
            try:
                obj = api.get_object(brain)
            except Exception:
                continue
            certificate = get_certificate_status(obj, self.days)
            valid_to = certificate['valid_to']
            days = certificate['days']
            status = certificate['status']
            try:
                serial = obj.getSerialNo() or "-"
            except Exception:
                serial = "-"
            rows.append({
                "title": api.get_title(obj),
                "url": api.get_url(obj),
                "type": self._type_name(obj),
                "serial": serial,
                "valid_to": self._fmt_date(valid_to),
                "days": days,
                "status": status,
                "status_label": self.labels["st_" + status],
                "status_css": STATUS_CSS[status],
            })
        # Prioritize expired and unresolved records before future/current validity.
        order = {"expired": 0, "unknown": 1, "none": 2,
                 "future": 3, "due": 4, "valid": 5}

        def sort_key(r):
            d = r["days"]
            d = d if d is not None else 10 ** 9
            return (order[r["status"]], d)

        rows.sort(key=sort_key)
        return rows

    def get_summary(self, rows):
        summary = {"total": len(rows), "valid": 0, "due": 0,
                   "expired": 0, "none": 0, "unknown": 0, "future": 0}
        for r in rows:
            summary[r["status"]] += 1
        return summary
