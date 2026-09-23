# -*- coding: utf-8 -*-
#
# Manager-only utility to delete sample-intake records (online test requests)
# by id. The submission form is public, so the register can accumulate
# spam/test entries; this gives staff a reliable way to remove them. Deletion
# runs as the privileged system user so it works regardless of the record's
# workflow state and bypasses CSRF for the POST.

from Products.Five.browser import BrowserView
from zope.interface import alsoProvides

from bika.lims import api

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


class SampleIntakeDeleteView(BrowserView):

    def __call__(self):
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)

        ids = self.request.get("ids", "")
        if isinstance(ids, (list, tuple)):
            ids = ",".join(ids)
        wanted = [i.strip() for i in ids.split(",") if i.strip()]

        # The listing posts the selected rows as "uids"; resolve them to ids
        # so the same view serves both the listing button and manual ?ids=.
        uids = self.request.get("uids", [])
        if not isinstance(uids, (list, tuple)):
            uids = [uids]
        for uid in [u for u in uids if u]:
            obj = api.get_object_by_uid(uid, default=None)
            if obj is not None:
                wanted.append(api.get_id(obj))

        deleted = []
        if wanted:
            with api.security.as_privileged_user():
                container = api.get_senaite_setup().get("sampleintake")
                if container is not None:
                    present = [i for i in wanted if container.get(i) is not None]
                    if present:
                        container.manage_delObjects(present)
                        deleted = present
            import transaction
            transaction.commit()

        setup_url = api.get_url(api.get_senaite_setup())
        self.request.response.redirect(
            "%s/sampleintake?deleted=%d" % (setup_url, len(deleted)))
        return u""
