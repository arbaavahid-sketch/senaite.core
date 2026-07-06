# -*- coding: utf-8 -*-
#
# Public, customer-facing feedback form (Tandis / TPPC). Lets a customer submit
# a complaint (ISO/IEC 17025 clause 7.9), a support request, or a satisfaction
# survey without access to the internal setup screens. The record is created in
# the customer-care register with elevated privileges and the customer receives
# a tracking number. Bilingual: Persian (fa, RTL) / English (en, LTR).

from datetime import date

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.interface import alsoProvides

from bika.lims import api

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


KINDS = {
    "complaint": "Complaint",
    "support": "SupportRequest",
    "survey": "Survey",
}

LABELS = {
    "fa": {
        "title": u"ثبت شکایت / نظرسنجی / پشتیبانی",
        "intro": u"لطفاً نوع درخواست را انتخاب و فرم را تکمیل کنید. پس از ثبت، شمارهٔ پیگیری دریافت می‌کنید.",
        "kind": u"نوع درخواست",
        "k_complaint": u"شکایت",
        "k_support": u"درخواست پشتیبانی",
        "k_survey": u"نظرسنجی رضایت",
        "client": u"نام مشتری / شرکت",
        "contact": u"نام تماس",
        "subject": u"موضوع",
        "sample": u"شناسهٔ نمونه/گزارش مرتبط (اختیاری)",
        "category": u"دسته",
        "severity": u"شدت",
        "description": u"شرح",
        "rating_overall": u"رضایت کلی (۱ تا ۵)",
        "rating_time": u"به‌موقع‌بودن (۱ تا ۵)",
        "rating_quality": u"کیفیت نتایج (۱ تا ۵)",
        "rating_comm": u"ارتباطات (۱ تا ۵)",
        "submit": u"ثبت",
        "thanks_title": u"با تشکر — درخواست شما ثبت شد",
        "thanks": u"شمارهٔ پیگیری شما:",
        "thanks_more": u"آزمایشگاه درخواست شما را بررسی و پیگیری خواهد کرد.",
        "again": u"ثبت درخواست دیگر",
        "err_subject": u"لطفاً موضوع را وارد کنید.",
        "sev_low": u"کم", "sev_medium": u"متوسط", "sev_high": u"زیاد",
        "choose": u"— انتخاب —",
    },
    "en": {
        "title": u"Submit a complaint / survey / support request",
        "intro": u"Please choose the type and fill in the form. You will receive a tracking number after submitting.",
        "kind": u"Request type",
        "k_complaint": u"Complaint",
        "k_support": u"Support request",
        "k_survey": u"Satisfaction survey",
        "client": u"Client / company name",
        "contact": u"Contact name",
        "subject": u"Subject",
        "sample": u"Related sample/report ID (optional)",
        "category": u"Category",
        "severity": u"Severity",
        "description": u"Description",
        "rating_overall": u"Overall satisfaction (1-5)",
        "rating_time": u"Timeliness (1-5)",
        "rating_quality": u"Result quality (1-5)",
        "rating_comm": u"Communication (1-5)",
        "submit": u"Submit",
        "thanks_title": u"Thank you - your request has been registered",
        "thanks": u"Your tracking number:",
        "thanks_more": u"The laboratory will review and follow up on your request.",
        "again": u"Submit another request",
        "err_subject": u"Please enter a subject.",
        "sev_low": u"Low", "sev_medium": u"Medium", "sev_high": u"High",
        "choose": u"— select —",
    },
}

COMPLAINT_CATEGORIES = [
    ("result", {"fa": u"نتیجهٔ آنالیز", "en": u"Analysis result"}),
    ("turnaround", {"fa": u"زمان‌بندی / تأخیر", "en": u"Turnaround / delay"}),
    ("report", {"fa": u"خطای گزارش", "en": u"Report error"}),
    ("service", {"fa": u"خدمات / پرسنل", "en": u"Service / staff"}),
    ("sampling", {"fa": u"نمونه‌برداری", "en": u"Sampling"}),
    ("other", {"fa": u"سایر", "en": u"Other"}),
]


class CustomerFeedbackView(BrowserView):
    template = ViewPageTemplateFile("templates/form.pt")

    def __call__(self):
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        self.error = ""
        self.tracking = ""
        if self.request.get("REQUEST_METHOD", "GET") == "POST" \
                and self.request.form.get("submit"):
            self._handle_submit()
        return self.template()

    def _lang(self):
        try:
            ltool = getToolByName(self.context, "portal_languages")
            lang = (ltool.getPreferredLanguage() or "fa").split("-")[0].lower()
        except Exception:
            lang = "fa"
        return lang if lang in LABELS else "en"

    def categories(self):
        return [(val, txt[self.lang]) for val, txt in COMPLAINT_CATEGORIES]

    def _handle_submit(self):
        form = self.request.form
        subject = (form.get("subject") or "").strip()
        if not subject:
            self.error = self.labels["err_subject"]
            return

        kind = form.get("kind", "complaint")
        portal_type = KINDS.get(kind, "Complaint")
        today = date.today()

        common = {
            "title": subject,
            "client_name": (form.get("client_name") or "").strip(),
            "contact_name": (form.get("contact_name") or "").strip(),
        }

        if portal_type == "Complaint":
            kwargs = dict(common)
            kwargs["description"] = (form.get("description") or "").strip()
            kwargs["related_sample"] = (form.get("related_sample") or "").strip()
            if form.get("category"):
                kwargs["category"] = form.get("category")
            if form.get("severity"):
                kwargs["severity"] = form.get("severity")
            kwargs["received_date"] = today
        elif portal_type == "SupportRequest":
            kwargs = dict(common)
            kwargs["description"] = (form.get("description") or "").strip()
            kwargs["received_date"] = today
        else:  # Survey
            kwargs = dict(common)
            kwargs["comments"] = (form.get("description") or "").strip()
            kwargs["related_report"] = (form.get("related_sample") or "").strip()
            kwargs["survey_date"] = today
            for f, key in (("rating_overall", "rating_overall"),
                           ("rating_timeliness", "rating_timeliness"),
                           ("rating_quality", "rating_quality"),
                           ("rating_communication", "rating_communication")):
                val = form.get(key)
                if val:
                    try:
                        kwargs[f] = int(val)
                    except (TypeError, ValueError):
                        pass
            kwargs.setdefault("rating_overall", 5)

        # Allow the (possibly low-privilege / anonymous) submitter to write.
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)
        try:
            with api.security.as_privileged_user():
                container = self._container()
                obj = api.create(container, portal_type, **kwargs)
                self.tracking = api.get_id(obj)
        except Exception as exc:  # noqa
            self.error = u"%s" % exc

    def _container(self):
        setup = api.get_senaite_setup()
        return setup.customercare
