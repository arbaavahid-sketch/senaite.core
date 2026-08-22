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

TYPES = ("Complaint", "SupportRequest", "Survey", "SampleRequest")

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
    "SampleRequest": {"fa": u"درخواست آزمون", "en": u"Test request"},
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
        "sample": u"شناسهٔ نمونهٔ ثبت‌شده",
        "response": u"پاسخ آزمایشگاه",
        "no_response": u"هنوز پاسخی ثبت نشده است.",
        "results_ready": u"نمونهٔ شما ثبت و در حال انجام است. گزارش نتایج پس از "
                         u"تکمیل، از سوی آزمایشگاه ارسال می‌شود.",
        "report_sent": u"گزارش نتایج صادر و برای شما ایمیل شد. اگر آن را "
                       u"دریافت نکردید، با آزمایشگاه تماس بگیرید.",
        "st_testing": u"در حال انجام آزمون",
        "st_published": u"گزارش صادر شد",
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
        "sample": u"Registered sample ID",
        "response": u"Laboratory response",
        "no_response": u"No response has been recorded yet.",
        "results_ready": u"Your sample has been registered and is being "
                         u"processed. The results report will be sent by the "
                         u"laboratory once complete.",
        "report_sent": u"The results report has been issued and emailed to "
                       u"you. If you didn't receive it, please contact the "
                       u"laboratory.",
        "st_testing": u"Testing in progress",
        "st_published": u"Report issued",
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
        self.token = (self.request.get("token") or "").strip()
        if self.token:
            # Direct link: the unguessable token is the credential, no name
            # needed. This is the link the lab emails to the customer.
            self._lookup_by_token()
        elif self.request.get("track"):
            self._lookup()
        return self.template()

    def _containers(self, setup):
        """Customer-care and sample-intake registers (whichever exist)."""
        for name in ("customercare", "sampleintake"):
            container = setup.get(name)
            if container is not None:
                yield container

    def _lookup_by_token(self):
        try:
            with api.security.as_privileged_user():
                setup = api.get_senaite_setup()
                for container in self._containers(setup):
                    for obj in container.objectValues():
                        if api.get_portal_type(obj) not in TYPES:
                            continue
                        stored = safe_unicode(
                            getattr(obj, "access_token", "") or "").strip()
                        if stored and stored == safe_unicode(self.token):
                            self.result = self._to_result(obj)
                            return
                self.not_found = True
        except Exception:
            self.not_found = True

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
                # First treat the entered value as an access token: this works
                # regardless of the object id (which may be non-ascii) and needs
                # no client name, so a customer can paste the code from the link.
                key = safe_unicode(self.tracking_id)
                for container in self._containers(setup):
                    for obj in container.objectValues():
                        if api.get_portal_type(obj) not in TYPES:
                            continue
                        stored = safe_unicode(
                            getattr(obj, "access_token", "") or "").strip()
                        if stored and stored == key:
                            self.result = self._to_result(obj)
                            return
                # Otherwise, look it up by object id (+ client-name check below).
                obj = None
                for container in self._containers(setup):
                    candidate = container.get(self.tracking_id)
                    if candidate is not None:
                        obj = candidate
                        break
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

    def _resolve_sample(self, obj):
        """Return the Sample (AnalysisRequest) created from this request, or
        None. Prefer the stored UID; fall back to a catalog lookup by id for
        older records created before the UID was stored."""
        uid = safe_unicode(getattr(obj, "created_sample_uid", "") or "").strip()
        if uid:
            sample = api.get_object_by_uid(uid, default=None)
            if sample is not None:
                return sample
        sample_id = safe_unicode(getattr(obj, "created_sample_id", "") or "")
        if not sample_id:
            return None
        try:
            from senaite.core.catalog import SAMPLE_CATALOG
            for brain in api.search({"portal_type": "AnalysisRequest"},
                                    SAMPLE_CATALOG):
                if safe_unicode(api.get_id(brain)) == sample_id:
                    return api.get_object(brain)
        except Exception:
            pass
        return None

    def _to_result(self, obj):
        pt = api.get_portal_type(obj)
        state = api.get_review_status(obj)
        if pt == "Complaint":
            response = getattr(obj, "customer_response", "") or ""
        elif pt in ("SupportRequest", "SampleRequest"):
            response = getattr(obj, "response", "") or ""
        else:
            response = ""

        status_label = STATE_LABELS.get(state, {}).get(self.lang, state)

        # For a test request that reception already converted, surface the
        # registered sample id and reflect the *sample's* real state, so the
        # customer sees "report issued" once the lab publishes it (rather than
        # the request's own workflow state, which does not track that).
        sample_id = safe_unicode(getattr(obj, "created_sample_id", "") or "")
        message = u""
        if sample_id:
            message = self.labels["results_ready"]
            status_label = self.labels["st_testing"]
            sample = self._resolve_sample(obj)
            if sample is not None \
                    and api.get_review_status(sample) == "published":
                message = self.labels["report_sent"]
                status_label = self.labels["st_published"]

        return {
            "type": TYPE_LABELS.get(pt, {}).get(self.lang, pt),
            "subject": safe_unicode(getattr(obj, "title", "")
                                    or api.get_title(obj)),
            "status": status_label,
            "response": safe_unicode(response),
            "sample_id": sample_id,
            "message": message,
        }
