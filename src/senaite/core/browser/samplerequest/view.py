# -*- coding: utf-8 -*-
#
# Public, customer-facing "request a test / submit a sample" form (Tandis /
# TPPC). A customer describes the sample they will send and the tests they want,
# then receives a tracking number and a direct tracking link. Reception later
# converts the request into a real Sample (AnalysisRequest). The record is
# created in the sample-intake register with elevated privileges. Bilingual:
# Persian (fa, RTL) / English (en, LTR).

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


LABELS = {
    "fa": {
        "title": u"درخواست آزمون / ارسال نمونه",
        "intro": u"لطفاً فرم را تکمیل کنید. پس از ثبت، شمارهٔ پیگیری و یک لینک "
                 u"دریافت می‌کنید. سپس نمونهٔ فیزیکی را برای آزمایشگاه ارسال کنید.",
        "client": u"نام مشتری / شرکت",
        "contact": u"نام تماس",
        "email": u"ایمیل (برای دریافت نتیجه)",
        "email_hint": u"نتیجه و لینک پیگیری به این ایمیل ارسال می‌شود.",
        "phone": u"تلفن تماس",
        "address": u"آدرس",
        "economic_code": u"شناسه ملی / کد اقتصادی (برای صورتحساب)",
        "subject": u"موضوع / هدف آزمون",
        "sec_client": u"اطلاعات مشتری",
        "sec_sample": u"اطلاعات نمونه",
        "sec_tests": u"آزمون و تحویل",
        "sample_type": u"نوع نمونه (مثلاً نفت خام، بنزین، گازوئیل)",
        "sampling_date": u"تاریخ نمونه‌برداری",
        "sampling_point": u"محل / منبع نمونه‌برداری",
        "condition": u"وضعیت نمونه هنگام تحویل",
        "tests": u"آزمون‌های موردنظر",
        "tests_hint": u"آزمون‌هایی که می‌خواهید انجام شود را بنویسید "
                      u"(مثلاً گوگرد، دانسیته، نقطهٔ اشتعال).",
        "quantity": u"تعداد / مقدار نمونه",
        "priority": u"اولویت",
        "prio_normal": u"عادی", "prio_urgent": u"فوری",
        "delivery": u"نحوهٔ دریافت گزارش",
        "del_email": u"ایمیل", "del_inperson": u"حضوری", "del_post": u"پست",
        "description": u"توضیحات نمونه",
        "submit": u"ثبت درخواست",
        "choose": u"— انتخاب —",
        "thanks_title": u"با تشکر — درخواست شما ثبت شد",
        "thanks": u"شمارهٔ پیگیری شما:",
        "thanks_more": u"لطفاً نمونهٔ فیزیکی را همراه این شماره برای آزمایشگاه "
                       u"ارسال کنید. وضعیت را از طریق لینک زیر می‌توانید ببینید.",
        "again": u"ثبت درخواست دیگر",
        "track_link": u"پیگیری این درخواست",
        "your_link": u"لینک پیگیری شما:",
        "save_link": u"این لینک را ذخیره کنید تا هر زمان وضعیت را ببینید.",
        "err_subject": u"لطفاً موضوع را وارد کنید.",
    },
    "en": {
        "title": u"Request a test / submit a sample",
        "intro": u"Fill in the form. You will receive a tracking number and a "
                 u"link, then send your physical sample to the laboratory.",
        "client": u"Client / company name",
        "contact": u"Contact name",
        "email": u"Email (to receive the result)",
        "email_hint": u"The result and tracking link are sent to this email.",
        "phone": u"Phone",
        "address": u"Address",
        "economic_code": u"National ID / economic code (for invoicing)",
        "subject": u"Subject / purpose",
        "sec_client": u"Client information",
        "sec_sample": u"Sample information",
        "sec_tests": u"Tests & delivery",
        "sample_type": u"Sample type (e.g. crude oil, gasoline, diesel)",
        "sampling_date": u"Sampling date",
        "sampling_point": u"Sampling point / source",
        "condition": u"Sample condition on receipt",
        "tests": u"Requested tests",
        "tests_hint": u"List the tests you want (e.g. sulfur, density, "
                      u"flash point).",
        "quantity": u"Number / quantity of samples",
        "priority": u"Priority",
        "prio_normal": u"Normal", "prio_urgent": u"Urgent",
        "delivery": u"Preferred report delivery",
        "del_email": u"Email", "del_inperson": u"In person", "del_post": u"Post",
        "description": u"Sample description",
        "submit": u"Submit request",
        "choose": u"— select —",
        "thanks_title": u"Thank you - your request has been registered",
        "thanks": u"Your tracking number:",
        "thanks_more": u"Please send your physical sample to the laboratory "
                       u"quoting this number. You can check the status via the "
                       u"link below.",
        "again": u"Submit another request",
        "track_link": u"Track this request",
        "your_link": u"Your tracking link:",
        "save_link": u"Save this link to check the status anytime.",
        "err_subject": u"Please enter a subject.",
    },
}


class SampleRequestView(BrowserView):
    template = ViewPageTemplateFile("templates/form.pt")

    def __call__(self):
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        self.error = ""
        self.tracking = ""
        self.track_link = ""
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

    def _handle_submit(self):
        form = self.request.form
        subject = (form.get("subject") or "").strip()
        if not subject:
            self.error = self.labels["err_subject"]
            return

        kwargs = {
            "title": subject,
            "client_name": (form.get("client_name") or "").strip(),
            "contact_name": (form.get("contact_name") or "").strip(),
            "contact_email": (form.get("contact_email") or "").strip(),
            "contact_phone": (form.get("contact_phone") or "").strip(),
            "address": (form.get("address") or "").strip(),
            "economic_code": (form.get("economic_code") or "").strip(),
            "sample_type": (form.get("sample_type") or "").strip(),
            "sampling_point": (form.get("sampling_point") or "").strip(),
            "sample_condition": (form.get("sample_condition") or "").strip(),
            "requested_tests": (form.get("requested_tests") or "").strip(),
            "sample_description": (form.get("sample_description") or "").strip(),
            "quantity": (form.get("quantity") or "").strip(),
        }
        if form.get("priority"):
            kwargs["priority"] = form.get("priority")
        if form.get("report_delivery"):
            kwargs["report_delivery"] = form.get("report_delivery")
        # Optional sampling date (YYYY-MM-DD).
        raw_date = (form.get("sampling_date") or "").strip()
        if raw_date:
            try:
                y, m, d = [int(x) for x in raw_date.split("-")]
                kwargs["sampling_date"] = date(y, m, d)
            except (ValueError, TypeError):
                pass

        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)
        try:
            with api.security.as_privileged_user():
                container = self._container()
                obj = api.create(container, "SampleRequest", **kwargs)
                self.tracking = api.get_id(obj)
                token = getattr(obj, "access_token", None)
                if token:
                    self.track_link = "%s/@@track-request?token=%s" % (
                        api.get_url(api.get_portal()), token)
        except Exception as exc:  # noqa
            self.error = u"%s" % exc

    def _container(self):
        setup = api.get_senaite_setup()
        return setup.sampleintake
