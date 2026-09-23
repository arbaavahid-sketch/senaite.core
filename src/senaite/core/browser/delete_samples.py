# -*- coding: utf-8 -*-
#
# Manager-only cleanup page for the TEST data created while setting the system
# up: pick samples and/or online requests with checkboxes and delete them.
#
# SENAITE deliberately has no delete for samples (audit trail) — real samples
# must be Cancelled/Invalidated instead. Use this only for test records.
#
# Deletion runs as the privileged user so it works whatever the workflow state
# is. ManageBika only.

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SAMPLE_CATALOG
from zope.interface import alsoProvides

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


def _as_list(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [safe_unicode(v) for v in value if v]
    return [safe_unicode(value)]


class DeleteSamplesView(BrowserView):
    """Checkbox UI to delete test samples and test online requests."""

    template = ViewPageTemplateFile("templates/cleanup.pt")

    def __call__(self):
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)
        self.message = u""
        self.error = u""
        if self.request.get("REQUEST_METHOD") == "POST" \
                and self.request.form.get("do_delete"):
            self.message = self._delete()
        return self.template()

    # --- data -------------------------------------------------------------

    def get_samples(self):
        rows = []
        for brain in api.search({"portal_type": "AnalysisRequest"},
                                SAMPLE_CATALOG):
            try:
                client = safe_unicode(brain.getClientTitle or u"")
            except Exception:
                client = u""
            created = u""
            try:
                created = brain.created.strftime("%Y-%m-%d")
            except Exception:
                pass
            rows.append({
                "id": safe_unicode(api.get_id(brain)),
                "client": client,
                "state": safe_unicode(api.get_review_status(brain)),
                "created": created,
                "url": safe_unicode(api.get_url(brain)),
            })
        rows.sort(key=lambda r: r["created"], reverse=True)
        return rows

    def get_requests(self):
        rows = []
        container = api.get_senaite_setup().get("sampleintake")
        if container is None:
            return rows
        for obj in container.objectValues():
            if api.get_portal_type(obj) != "SampleRequest":
                continue
            created = u""
            try:
                created = api.get_creation_date(obj).strftime("%Y-%m-%d")
            except Exception:
                pass
            rows.append({
                "id": safe_unicode(api.get_id(obj)),
                "subject": safe_unicode(getattr(obj, "title", u"")
                                        or api.get_id(obj)),
                "client": safe_unicode(getattr(obj, "client_name", u"") or u""),
                "state": safe_unicode(api.get_review_status(obj)),
                "created": created,
                "url": safe_unicode(api.get_url(obj)),
            })
        rows.sort(key=lambda r: r["created"], reverse=True)
        return rows

    # --- delete -----------------------------------------------------------

    def _delete(self):
        form = self.request.form
        sids = set(_as_list(form.get("sample_ids")))
        rids = set(_as_list(form.get("request_ids")))
        if not sids and not rids:
            return u"چیزی انتخاب نشده بود."

        n_samples = n_requests = 0
        try:
            with api.security.as_privileged_user():
                if sids:
                    for brain in api.search({"portal_type": "AnalysisRequest"},
                                            SAMPLE_CATALOG):
                        sid = safe_unicode(api.get_id(brain))
                        if sid not in sids:
                            continue
                        try:
                            obj = api.get_object(brain)
                            parent = api.get_parent(obj)
                            parent.manage_delObjects([api.get_id(obj)])
                            n_samples += 1
                        except Exception:
                            pass
                if rids:
                    container = api.get_senaite_setup().get("sampleintake")
                    if container is not None:
                        present = [i for i in rids
                                   if container.get(i) is not None]
                        if present:
                            container.manage_delObjects(present)
                            n_requests = len(present)
            import transaction
            transaction.commit()
        except Exception as exc:  # noqa
            self.error = safe_unicode(exc)
            return u"خطا در حذف: %s" % safe_unicode(exc)

        return u"حذف شد: %d نمونه و %d درخواست." % (n_samples, n_requests)
