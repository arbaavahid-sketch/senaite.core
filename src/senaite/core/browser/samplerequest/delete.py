# -*- coding: utf-8 -*-
#
# Manager-only utility to delete sample-intake records (online test requests)
# by id. The submission form is public, so the register can accumulate
# spam/test entries; this gives staff a reliable way to remove them. Deletion
# runs as the privileged system user so it works regardless of the record's
# workflow state, after validating the staff member's permission and POST.

from Products.Five.browser import BrowserView
from AccessControl import Unauthorized
from plone.protect import CheckAuthenticator, PostOnly

from bika.lims import api
from senaite.core.permissions import ManageBika


class SampleIntakeDeleteView(BrowserView):

    def __call__(self):
        PostOnly(self.request)
        CheckAuthenticator(self.request)
        if not api.security.check_permission(ManageBika, self.context):
            raise Unauthorized("Managing sample intake is not permitted")

        ids = self.request.get("ids", "")
        if isinstance(ids, (list, tuple)):
            ids = ",".join(ids)
        wanted = [i.strip() for i in ids.split(",") if i.strip()]

        # The listing posts the selected rows as "uids"; resolve them to ids
        # so the same view serves both the listing button and direct POSTs.
        container = api.get_senaite_setup().get("sampleintake")
        uids = self.request.get("uids", [])
        if not isinstance(uids, (list, tuple)):
            uids = [uids]
        for uid in [u for u in uids if u]:
            obj = api.get_object_by_uid(uid, default=None)
            if (obj is not None and container is not None
                    and api.get_path(api.get_parent(obj))
                    == api.get_path(container)):
                wanted.append(api.get_id(obj))

        deleted = []
        if wanted:
            with api.security.as_privileged_user():
                if container is not None:
                    present = [i for i in wanted if container.get(i) is not None]
                    if present:
                        container.manage_delObjects(present)
                        deleted = present

        setup_url = api.get_url(api.get_senaite_setup())
        self.request.response.redirect(
            "%s/sampleintake?deleted=%d" % (setup_url, len(deleted)))
        return u""
