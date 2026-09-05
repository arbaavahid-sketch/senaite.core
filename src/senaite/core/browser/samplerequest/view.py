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
from bika.lims.api import safe_unicode
from senaite.core.catalog import SETUP_CATALOG

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


LABELS = {
    "fa": {
        "title": u"درخواست آزمون / ارسال نمونه",
        "intro": u"لطفاً فرم را تکمیل کنید. پس از ثبت، شمارهٔ پیگیری و یک لینک "
                 u"دریافت می‌کنید. سپس نمونهٔ فیزیکی را برای آزمایشگاه ارسال کنید.",
        "client": u"نام شرکت / دانشگاه",
        "contact": u"نام و نام خانوادگی متقاضی",
        "email": u"ایمیل (برای دریافت نتیجه)",
        "email_hint": u"نتیجه و لینک پیگیری به این ایمیل ارسال می‌شود.",
        "phone": u"تلفن تماس",
        "address": u"آدرس",
        "economic_code": u"شناسه ملی / کد اقتصادی (برای صورتحساب)",
        "referral": u"نحوهٔ آشنایی با آزمایشگاه",
        "subject": u"موضوع / هدف آزمون",
        "sec_client": u"اطلاعات متقاضی",
        "sec_sample": u"مشخصات نمونه",
        "sec_safety": u"شرایط نگهداری و ایمنی",
        "sec_terms": u"تعهد و شرایط",
        "sec_tests": u"آزمون و تحویل",
        "sample_type": u"نوع نمونه (مثلاً نفت خام، بنزین، گازوئیل)",
        "nature": u"ماهیت نمونه (طبیعی یا سنتزی)",
        "matrix": u"نوع نمونه (معدنی یا آلی)",
        "sampling_date": u"تاریخ نمونه‌برداری",
        "sampling_point": u"محل / منبع نمونه‌برداری",
        "condition": u"وضعیت نمونه هنگام تحویل",
        "condition_hint": u"وضعیت ظاهری و سلامت نمونه هنگام تحویل را بنویسید — "
                          u"مثلاً: سالم و پلمب‌شده، درِ باز، نشتی، شکسته، "
                          u"آلوده، یا ته‌نشین‌شده.",
        "condition_ph": u"مثلاً: سالم و پلمب‌شده",
        "storage": u"شرایط نگهداری (در صورت وجود)",
        "opt_storage": [u"حساس به نور", u"حساس به رطوبت",
                        u"نگهداری در اتمسفر خاص", u"نگهداری در دمای پایین"],
        "hazards": u"موارد ایمنی و خطر",
        "opt_safety": [u"سمی", u"فرّار", u"قابل اشتعال",
                       u"محرک دستگاه تنفسی", u"قابل جذب از طریق پوست",
                       u"نانو سایز", u"بیماری‌زا", u"ندارد"],
        "safety_notes": u"توضیحات ایمنی / برگهٔ اطلاعات ایمنی (MSDS)",
        "safety_notes_hint": u"در صورت وجود MSDS آن را همراه نمونه ارسال کنید؛ "
                             u"در غیر این صورت اقدامات ایمنی لازم را بنویسید.",
        "terms_title": u"شرایط و قوانین آزمایشگاه",
        "terms_items": [
            u"حداقل مقدار نمونهٔ پودری ۳ تا ۵ گرم است؛ نمونه‌برداری باید توسط "
            u"خود متقاضی و در ظرف مناسب انجام شود.",
            u"متقاضی متعهد می‌شود نمونه رادیواکتیو یا انفجاری نیست؛ در غیر این "
            u"صورت هرگونه خسارت جانی و مالی بر عهدهٔ متقاضی است.",
            u"نمونه‌ها تا یک ماه پس از انجام آزمون نگهداری می‌شوند؛ پس از آن "
            u"آزمایشگاه مسئولیتی در قبال نمونه ندارد.",
            u"انجام آزمون و ارسال نتیجه منوط به پرداخت کامل هزینهٔ آزمون است.",
            u"در صورت بروز حوادث پیش‌بینی‌نشده یا تعمیر دستگاه، به زمان "
            u"جوابدهی افزوده می‌شود.",
            u"هزینهٔ پست یا پیک برای برگشت نمونه بر عهدهٔ مشتری است.",
            u"حداکثر مسئولیت مالی آزمایشگاه در قبال نمونه معادل هزینهٔ آنالیز "
            u"است.",
        ],
        "declaration": u"شرایط و قوانین بالا را خوانده و می‌پذیرم و تعهد می‌کنم "
                       u"که نمونه رادیواکتیو یا انفجاری نیست.",
        "tests": u"آزمون‌های موردنظر (انتخاب کنید)",
        "tests_search": u"جستجوی آزمون…",
        "tests_none": u"فعلاً آزمونی برای انتخاب تعریف نشده است.",
        "other_tests": u"سایر آزمون‌ها / توضیحات (اگر در فهرست نبود)",
        "tests_hint": u"می‌توانید از فهرست انتخاب کنید و/یا موارد دیگر را "
                      u"اینجا بنویسید.",
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
        "err_declaration": u"برای ثبت درخواست، باید شرایط و تعهدنامه را "
                           u"بپذیرید.",
        "err_client_name": u"لطفاً نام شرکت/مشتری را وارد کنید.",
        "err_contact_name": u"لطفاً نام تماس را وارد کنید.",
        "err_contact_email": u"لطفاً ایمیل تماس را وارد کنید.",
        "err_contact_email_bad": u"ایمیل واردشده معتبر نیست.",
        "err_contact_phone": u"لطفاً تلفن تماس را وارد کنید.",
    },
    "en": {
        "title": u"Request a test / submit a sample",
        "intro": u"Fill in the form. You will receive a tracking number and a "
                 u"link, then send your physical sample to the laboratory.",
        "client": u"Company / university name",
        "contact": u"Applicant full name",
        "email": u"Email (to receive the result)",
        "email_hint": u"The result and tracking link are sent to this email.",
        "phone": u"Phone",
        "address": u"Address",
        "economic_code": u"National ID / economic code (for invoicing)",
        "referral": u"How did you hear about the laboratory?",
        "subject": u"Subject / purpose",
        "sec_client": u"Applicant information",
        "sec_sample": u"Sample specifications",
        "sec_safety": u"Storage & safety",
        "sec_terms": u"Declaration & terms",
        "sec_tests": u"Tests & delivery",
        "sample_type": u"Sample type (e.g. crude oil, gasoline, diesel)",
        "nature": u"Sample nature (natural or synthetic)",
        "matrix": u"Sample matrix (mineral or organic)",
        "sampling_date": u"Sampling date",
        "sampling_point": u"Sampling point / source",
        "condition": u"Sample condition on receipt",
        "condition_hint": u"Describe the visual state and integrity of the "
                          u"sample on delivery — e.g. sealed and intact, "
                          u"opened, leaking, broken, contaminated, or settled.",
        "condition_ph": u"e.g. sealed and intact",
        "storage": u"Storage conditions (if any)",
        "opt_storage": [u"Light sensitive", u"Moisture sensitive",
                        u"Special atmosphere", u"Low temperature"],
        "hazards": u"Safety & hazards",
        "opt_safety": [u"Toxic", u"Volatile", u"Flammable",
                       u"Respiratory irritant", u"Skin-absorbable",
                       u"Nano-sized", u"Pathogenic", u"None"],
        "safety_notes": u"Safety notes / Material Safety Data Sheet (MSDS)",
        "safety_notes_hint": u"If an MSDS exists, send it with the sample; "
                             u"otherwise describe the required safety measures.",
        "terms_title": u"Laboratory terms & conditions",
        "terms_items": [
            u"Minimum powder sample amount is 3-5 g; sampling must be done by "
            u"the applicant and placed in a suitable container.",
            u"The applicant declares the sample is not radioactive or "
            u"explosive; otherwise all personal and material damages are the "
            u"applicant's responsibility.",
            u"Samples are kept for up to one month after testing; afterwards "
            u"the laboratory holds no responsibility for the sample.",
            u"Testing and the release of results are subject to full payment "
            u"of the test fee.",
            u"Unforeseen events or instrument repairs may extend the turnaround "
            u"time.",
            u"Return shipping/courier costs are the customer's responsibility.",
            u"The lab's maximum financial liability for the sample equals the "
            u"analysis fee.",
        ],
        "declaration": u"I have read and accept the terms above and declare "
                       u"the sample is not radioactive or explosive.",
        "tests": u"Requested tests (select)",
        "tests_search": u"Search tests…",
        "tests_none": u"No tests are available to select yet.",
        "other_tests": u"Other tests / notes (if not in the list)",
        "tests_hint": u"You can select from the list and/or write other items "
                      u"here.",
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
        "err_declaration": u"You must accept the terms and declaration to "
                           u"submit the request.",
        "err_client_name": u"Please enter the company / client name.",
        "err_contact_name": u"Please enter the contact name.",
        "err_contact_email": u"Please enter the contact email.",
        "err_contact_email_bad": u"The email address is not valid.",
        "err_contact_phone": u"Please enter the contact phone.",
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

    def _active_services(self):
        """Brains of active analysis services, sorted by title. Read with
        elevated privileges because the public form is served to Anonymous,
        who cannot otherwise see setup objects through the catalog."""
        with api.security.as_privileged_user():
            return api.search({"portal_type": "AnalysisService",
                               "is_active": True,
                               "sort_on": "sortable_title"}, SETUP_CATALOG)

    def service_groups(self):
        """Active services grouped by analysis category, for the picker."""
        cats = {}
        try:
            with api.security.as_privileged_user():
                for brain in api.search({"portal_type": "AnalysisCategory"},
                                        SETUP_CATALOG):
                    cats[api.get_uid(brain)] = api.get_title(brain)
        except Exception:
            pass
        groups = {}
        for brain in self._active_services():
            cuid = getattr(brain, "getCategoryUID", None)
            ctitle = cats.get(cuid) or u"—"
            groups.setdefault(ctitle, []).append(
                {"uid": api.get_uid(brain), "title": api.get_title(brain)})
        return [{"category": c, "services": s}
                for c, s in sorted(groups.items(), key=lambda x: x[0])]

    def _service_titles(self, uids):
        """Map selected service UIDs back to their titles for a readable list."""
        if not uids:
            return []
        wanted = set(uids)
        out = []
        for brain in self._active_services():
            if api.get_uid(brain) in wanted:
                out.append(safe_unicode(api.get_title(brain)))
        return out

    def _handle_submit(self):
        form = self.request.form
        # Honeypot: a hidden field humans never see but bots fill in. If it has
        # any value, silently drop the submission (no record, no error).
        if (form.get("website") or "").strip():
            return
        subject = (form.get("subject") or "").strip()
        if not subject:
            self.error = self.labels["err_subject"]
            return

        # Required contact information: name, phone, email and client name, so
        # every request carries who submitted it and how to reach them.
        client_name = (form.get("client_name") or "").strip()
        contact_name = (form.get("contact_name") or "").strip()
        contact_email = (form.get("contact_email") or "").strip()
        contact_phone = (form.get("contact_phone") or "").strip()
        if not client_name:
            self.error = self.labels["err_client_name"]
            return
        if not contact_name:
            self.error = self.labels["err_contact_name"]
            return
        if not contact_phone:
            self.error = self.labels["err_contact_phone"]
            return
        if not contact_email:
            self.error = self.labels["err_contact_email"]
            return
        if "@" not in contact_email or "." not in contact_email.split("@")[-1]:
            self.error = self.labels["err_contact_email_bad"]
            return

        # The customer must accept the terms / hazard declaration.
        if not form.get("declaration"):
            self.error = self.labels["err_declaration"]
            return

        kwargs = {
            "title": subject,
            "client_name": (form.get("client_name") or "").strip(),
            "contact_name": (form.get("contact_name") or "").strip(),
            "contact_email": (form.get("contact_email") or "").strip(),
            "contact_phone": (form.get("contact_phone") or "").strip(),
            "address": (form.get("address") or "").strip(),
            "economic_code": (form.get("economic_code") or "").strip(),
            "referral_source": (form.get("referral_source") or "").strip(),
            "sample_type": (form.get("sample_type") or "").strip(),
            "sample_nature": (form.get("sample_nature") or "").strip(),
            "sample_matrix": (form.get("sample_matrix") or "").strip(),
            "sampling_point": (form.get("sampling_point") or "").strip(),
            "sample_condition": (form.get("sample_condition") or "").strip(),
            "sample_description": (form.get("sample_description") or "").strip(),
            "safety_notes": (form.get("safety_notes") or "").strip(),
            "quantity": (form.get("quantity") or "").strip(),
            "hazard_declaration": True,
        }

        # Multi-select declarations: keep only non-empty, coerce to a list.
        for field in ("storage_conditions", "safety_hazards"):
            vals = form.get(field) or []
            if isinstance(vals, basestring):  # noqa: F821 (py2)
                vals = [vals]
            kwargs[field] = [safe_unicode(v) for v in vals if v]

        # Tests: selected from the active-services picker (UIDs) plus any
        # free-text "other" entry. Store the UIDs for conversion and a
        # human-readable list in requested_tests.
        service_uids = form.get("service_uids") or []
        if isinstance(service_uids, basestring):  # noqa: F821 (py2)
            service_uids = [service_uids]
        service_uids = [u for u in service_uids if u]
        titles = self._service_titles(service_uids)
        other = safe_unicode((form.get("other_tests") or "").strip())
        readable = u"، ".join(titles) if self.lang == "fa" \
            else u", ".join(titles)
        if other:
            readable = (readable + u"\n" + other) if readable else other
        kwargs["requested_service_uids"] = service_uids
        kwargs["requested_tests"] = readable
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
                # Replace the default id (derived from the Persian subject,
                # which is ugly and not ascii-safe) with a clean, human
                # tracking code like TR-0001.
                obj = self._rename_clean(container, obj)
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

    def _rename_clean(self, container, obj):
        """Rename the request to a clean sequential id (TR-0001). Best effort:
        if the rename fails the original object is returned unchanged (the
        tokenised tracking link works regardless of the id)."""
        try:
            existing = set(container.objectIds())
            n = 1
            while ("TR-%04d" % n) in existing:
                n += 1
            new_id = "TR-%04d" % n
            old_id = api.get_id(obj)
            if old_id != new_id:
                container.manage_renameObject(old_id, new_id)
                return container[new_id]
        except Exception:
            pass
        return obj
