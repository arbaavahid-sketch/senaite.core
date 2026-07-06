# -*- coding: utf-8 -*-
#
# Public "track my request" page (Tandis / TPPC). A customer enters the tracking
# number they received when submitting a complaint / support request / survey,
# plus the client name they used, and sees the current status and the lab's
# response. Read with elevated privileges but only safe fields are exposed, and
# the client name must match to avoid trivial enumeration. Bilingual (fa/en).

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from bika.lims import api
from bika.lims.api import safe_unicode

TYPES = ("Complaint", "SupportRequest", "Survey")

STATE_LABELS = {
    "received": {"fa": u"دریافت‌شده", "en": u"Received"},
    "in_progress": {"fa": u"در حال بررسی", "en": u"In progress"},
    "resolved": {"fa": u"حل‌شده", "en": u"Resolved"},
    "closed": {"fa": u"بسته", "en": u"Closed"},
    "active": {"fa": u"ثبت‌شده", "en": u"Submitted"},
}

TYPE_LABELS = {
    "Complaint": {"fa": u"شکایت", "en": u"Complaint"},
    "SupportRequest": {"fa": u"درخواست پشتیبانی", "en": u"Support request"},
    "Survey": {"fa": u"نظرسنجی رضایت", "en": u"Satisfaction survey"},
}

LABELS = {
    "fa": {
        "title": u"پیگیری درخواست",
        "intro": u"شمارهٔ پیگیری و نام مشتری‌ای که هنگام ثبت وارد کردید را بنویسید.",
        "tracking": u"شمارهٔ پیگیری",
        "client": u"نام مشتری / شرکت",
        "track": u"پیگیری",
        "type": u"نوع",
        "subject": u"موضوع",
        "status": u"وضعیت",
        "response": u"پاسخ آزمایشگاه",
        "no_response": u"هنوز پاسخی ثبت نشده است.",
        "not_found": u"درخواستی با این شمارهٔ پیگیری و نام مشتری یافت نشد.",
        "submit_link": u"ثبت درخواست جدید",
    },
    "en": {
        "title": u"Track your request",
        "intro": u"Enter the tracking number and the client name you used when submitting.",
        "tracking": u"Tracking number",
        "client": u"Client / company name",
        "track": u"Track",
        "type": u"Type",
        "subject": u"Subject",
        "status": u"Status",
        "response": u"Laboratory response",
        "no_response": u"No response has been recorded yet.",
        "not_found": u"No request found for this tracking number and client name.",
        "submit_link": u"Submit a new request",
    },
}


class TrackRequestView(BrowserView):
    template = ViewPageTemplateFile("templates/track.pt")

    def __call__(self):
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        self.result = None
        self.not_found = False
        self.tracking_id = (self.request.get("tracking") or "").strip()
        self.client_name = (self.request.get("client_name") or "").strip()
        if self.request.get("track"):
            self._lookup()
        return self.template()

    def _lang(self):
        try:
            ltool = getToolByName(self.context, "portal_languages")
            lang = (ltool.getPreferredLanguage() or "fa").split("-")[0].lower()
        except Exception:
            lang = "fa"
        return lang if lang in LABELS else "en"

    def _lookup(self):
        if not self.tracking_id:
            return
        try:
            with api.security.as_privileged_user():
                setup = api.get_senaite_setup()
                container = setup.customercare
                obj = container.get(self.tracking_id)
                if obj is None or api.get_portal_type(obj) not in TYPES:
                    self.not_found = True
                    return
                # Normalise both sides to unicode before comparing: request
                # params come back as UTF-8 bytestrings under Py2 while the
                # stored value is unicode, so a naive compare fails for Persian.
                stored_client = safe_unicode(
                    getattr(obj, "client_name", "") or "").strip()
                input_client = safe_unicode(self.client_name or "").strip()
                # Require the client name to match (case-insensitive) unless the
                # stored record has no client name at all.
                if stored_client and input_client.lower() != stored_client.lower():
                    self.not_found = True
                    return
                self.result = self._to_result(obj)
        except Exception:
            self.not_found = True

    def _to_result(self, obj):
        pt = api.get_portal_type(obj)
        state = api.get_review_status(obj)
        if pt == "Complaint":
            response = getattr(obj, "customer_response", "") or ""
        elif pt == "SupportRequest":
            response = getattr(obj, "response", "") or ""
        else:
            response = ""
        return {
            "type": TYPE_LABELS.get(pt, {}).get(self.lang, pt),
            "subject": getattr(obj, "title", "") or api.get_title(obj),
            "status": STATE_LABELS.get(state, {}).get(self.lang, state),
            "response": response,
        }
