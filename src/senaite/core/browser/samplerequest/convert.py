# -*- coding: utf-8 -*-
#
# Reception "Convert to Sample" view for an online test request (SampleRequest).
# Shows the customer's request details and lets reception pick the real Client,
# Contact, SampleType and analysis services, then creates a proper Sample
# (AnalysisRequest) via bika.lims.utils.analysisrequest.create_analysisrequest.
# Manager/LabManager only. Bilingual (fa/en).

from datetime import date

from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.interface import alsoProvides

from bika.lims import api
from bika.lims.utils.analysisrequest import create_analysisrequest
from senaite.core.catalog import SETUP_CATALOG

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


LABELS = {
    "fa": {
        "title": u"تبدیل درخواست به نمونه",
        "request": u"مشخصات درخواست مشتری",
        "client": u"شرکت / دانشگاه",
        "new_client": u"— ساخت مشتری جدید از نام بالا —",
        "contact": u"نام و نام خانوادگی متقاضی",
        "email": u"ایمیل",
        "phone": u"تلفن",
        "cust_sample_type": u"نوع نمونه (گفتهٔ مشتری)",
        "cust_nature": u"ماهیت / نوع نمونه",
        "cust_storage": u"شرایط نگهداری",
        "cust_hazards": u"⚠ موارد ایمنی و خطر",
        "cust_safety_notes": u"توضیحات ایمنی / MSDS",
        "cust_tests": u"آزمون‌های درخواستی (گفتهٔ مشتری)",
        "pick_client": u"انتخاب مشتری",
        "pick_sampletype": u"نوع نمونه (تنظیم‌شده)",
        "pick_services": u"آزمون‌ها (سرویس‌ها)",
        "sampling_date": u"تاریخ نمونه‌برداری",
        "create": u"ساخت نمونه",
        "cancel": u"انصراف",
        "no_sampletypes": u"هیچ «نوع نمونه»‌ای تعریف نشده. ابتدا از تنظیمات، "
                          u"نوع نمونه اضافه کنید.",
        "no_services": u"هیچ «آزمونی» تعریف نشده. ابتدا از تنظیمات، آزمون "
                       u"(Analysis Service) اضافه کنید.",
        "choose": u"— انتخاب —",
        "err_sampletype": u"لطفاً نوع نمونه را انتخاب کنید.",
        "err_services": u"لطفاً حداقل یک آزمون را انتخاب کنید.",
        "ok": u"نمونه ساخته شد:",
    },
    "en": {
        "title": u"Convert request to Sample",
        "request": u"Customer request details",
        "client": u"Company / university",
        "new_client": u"— create a new client from the name above —",
        "contact": u"Applicant full name",
        "email": u"Email",
        "phone": u"Phone",
        "cust_sample_type": u"Sample type (customer)",
        "cust_nature": u"Nature / matrix",
        "cust_storage": u"Storage conditions",
        "cust_hazards": u"⚠ Safety hazards",
        "cust_safety_notes": u"Safety notes / MSDS",
        "cust_tests": u"Requested tests (customer)",
        "pick_client": u"Select client",
        "pick_sampletype": u"Sample type (configured)",
        "pick_services": u"Tests (services)",
        "sampling_date": u"Sampling date",
        "create": u"Create Sample",
        "cancel": u"Cancel",
        "no_sampletypes": u"No sample types are defined. Add one from Setup "
                          u"first.",
        "no_services": u"No analysis services are defined. Add one from Setup "
                       u"first.",
        "choose": u"— select —",
        "err_sampletype": u"Please select a sample type.",
        "err_services": u"Please select at least one test.",
        "ok": u"Sample created:",
    },
}


class ConvertToSampleView(BrowserView):
    template = ViewPageTemplateFile("templates/convert.pt")

    def __call__(self):
        self.lang = self._lang()
        self.labels = LABELS.get(self.lang, LABELS["en"])
        self.is_rtl = self.lang == "fa"
        self.error = ""
        self.created = ""
        self.created_url = ""
        if self.request.get("REQUEST_METHOD", "GET") == "POST" \
                and self.request.form.get("create"):
            self._convert()
        return self.template()

    def _lang(self):
        try:
            ltool = getToolByName(self.context, "portal_languages")
            lang = (ltool.getPreferredLanguage() or "fa").split("-")[0].lower()
        except Exception:
            lang = "fa"
        return lang if lang in LABELS else "en"

    # --- data for the form -------------------------------------------------

    def request_info(self):
        obj = self.context
        sep = u"، " if self.lang == "fa" else u", "
        return {
            "subject": getattr(obj, "title", "") or api.get_id(obj),
            "client_name": getattr(obj, "client_name", "") or "",
            "contact_name": getattr(obj, "contact_name", "") or "",
            "contact_email": getattr(obj, "contact_email", "") or "",
            "contact_phone": getattr(obj, "contact_phone", "") or "",
            "sample_type": getattr(obj, "sample_type", "") or "",
            "sample_nature": getattr(obj, "sample_nature", "") or "",
            "sample_matrix": getattr(obj, "sample_matrix", "") or "",
            "storage_conditions": sep.join(
                getattr(obj, "storage_conditions", None) or []),
            "safety_hazards": sep.join(
                getattr(obj, "safety_hazards", None) or []),
            "safety_notes": getattr(obj, "safety_notes", "") or "",
            "requested_tests": getattr(obj, "requested_tests", "") or "",
            "quantity": getattr(obj, "quantity", "") or "",
        }

    def _search_setup(self, portal_type):
        out = []
        try:
            brains = api.search({"portal_type": portal_type,
                                 "is_active": True,
                                 "sort_on": "sortable_title"}, SETUP_CATALOG)
            for brain in brains:
                out.append({"uid": api.get_uid(brain),
                            "title": api.get_title(brain)})
        except Exception:
            pass
        return out

    def clients(self):
        out = []
        try:
            portal = api.get_portal()
            for client in portal.clients.objectValues("Client"):
                out.append({"uid": api.get_uid(client),
                            "title": api.get_title(client)})
        except Exception:
            pass
        return sorted(out, key=lambda x: x["title"].lower())

    def sample_types(self):
        return self._search_setup("SampleType")

    def services(self):
        return self._search_setup("AnalysisService")

    def requested_uids(self):
        """UIDs the customer pre-selected, to pre-check in the picker."""
        return set(getattr(self.context, "requested_service_uids", None) or [])

    def today(self):
        return date.today().strftime("%Y-%m-%d")

    # --- conversion --------------------------------------------------------

    def _convert(self):
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)

        form = self.request.form
        sampletype_uid = (form.get("sampletype_uid") or "").strip()
        service_uids = form.get("service_uids") or []
        if isinstance(service_uids, basestring):  # noqa: F821 (py2)
            service_uids = [service_uids]
        service_uids = [u for u in service_uids if u]
        sampling_date = (form.get("sampling_date") or self.today()).strip()

        if not sampletype_uid:
            self.error = self.labels["err_sampletype"]
            return
        if not service_uids:
            self.error = self.labels["err_services"]
            return

        try:
            with api.security.as_privileged_user():
                client = self._resolve_client(form)
                contact = self._resolve_contact(client)
                values = {
                    "Client": api.get_uid(client),
                    "Contact": api.get_uid(contact),
                    "SamplingDate": sampling_date,
                    "SampleType": sampletype_uid,
                }
                ar = create_analysisrequest(
                    client, self.request, values, service_uids)
                sample_id = api.get_id(ar)
                # Link back and move the request forward (received -> in_progress).
                self.context.created_sample_id = sample_id
                if api.get_review_status(self.context) == "received":
                    try:
                        api.do_transition_for(self.context, "process")
                    except Exception:
                        pass
                self.created = sample_id
                self.created_url = api.get_url(ar)
        except Exception as exc:  # noqa
            self.error = u"%s" % exc

    def _resolve_client(self, form):
        client_uid = (form.get("client_uid") or "").strip()
        if client_uid and client_uid != "new":
            client = api.get_object_by_uid(client_uid, default=None)
            if client is not None:
                return client
        # Create a new client from the request's client name.
        portal = api.get_portal()
        name = (getattr(self.context, "client_name", "") or "").strip() \
            or api.get_id(self.context)
        return api.create(portal.clients, "Client", title=name, Name=name)

    def _resolve_contact(self, client):
        # Reuse the first existing contact, else create one from the request.
        try:
            contacts = client.getContacts()
        except Exception:
            contacts = []
        if contacts:
            return contacts[0]
        full = (getattr(self.context, "contact_name", "") or "").strip()
        email = (getattr(self.context, "contact_email", "") or "").strip()
        if full:
            parts = full.split(None, 1)
            first = parts[0]
            last = parts[1] if len(parts) > 1 else u"-"
        else:
            first, last = u"Customer", u"-"
        return api.create(client, "Contact", Firstname=first, Surname=last,
                          EmailAddress=email)
