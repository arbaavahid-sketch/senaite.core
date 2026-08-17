# -*- coding: utf-8 -*-
#
# Manager-only utility to delete customer-care records (complaints, surveys,
# support requests) by id. Because the submission form is public, the register
# will accumulate spam/test entries; this gives staff a reliable way to remove
# them. Deletion runs as the privileged system user so it works regardless of
# the record's workflow state (e.g. closed) and bypasses CSRF for the POST.

from Products.Five.browser import BrowserView
from zope.interface import alsoProvides

from bika.lims import api

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


class CustomerCareDeleteView(BrowserView):

    def __call__(self):
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)

        ids = self.request.get("ids", "")
        if isinstance(ids, (list, tuple)):
            ids = ",".join(ids)
        wanted = [i.strip() for i in ids.split(",") if i.strip()]

        deleted = []
        if wanted:
            with api.security.as_privileged_user():
                container = api.get_senaite_setup().get("customercare")
                if container is not None:
                    present = [i for i in wanted if container.get(i) is not None]
                    if present:
                        container.manage_delObjects(present)
                        deleted = present
            import transaction
            transaction.commit()

        # Redirect back to the register.
        setup_url = api.get_url(api.get_senaite_setup())
        self.request.response.redirect(
            "%s/customercare?deleted=%d" % (setup_url, len(deleted)))
        return u""
