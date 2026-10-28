# -*- coding: utf-8 -*-
#
# Manager-only utility to delete customer-care records (complaints, surveys,
# support requests) by id. Because the submission form is public, the register
# will accumulate spam/test entries; this gives staff a reliable way to remove
# them. Deletion runs as the privileged system user so it works regardless of
# the record's workflow state, after permission and POST validation.

from Products.Five.browser import BrowserView
from AccessControl import Unauthorized
from plone.protect import CheckAuthenticator, PostOnly

from bika.lims import api
from senaite.core.permissions import ManageBika


class CustomerCareDeleteView(BrowserView):

    def __call__(self):
        PostOnly(self.request)
        CheckAuthenticator(self.request)
        if not api.security.check_permission(ManageBika, self.context):
            raise Unauthorized("Managing customer care is not permitted")

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

        # Redirect back to the register.
        setup_url = api.get_url(api.get_senaite_setup())
        self.request.response.redirect(
            "%s/customercare?deleted=%d" % (setup_url, len(deleted)))
        return u""
