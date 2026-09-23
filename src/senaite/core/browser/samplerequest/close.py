# -*- coding: utf-8 -*-
#
# Staff action to close an online sample-request. The customerrequest workflow
# only allows close from the "resolved" state, so we walk the request forward
# (process -> resolve -> close) as needed. Runs privileged so a LabClerk can
# close it without the "Review portal content" permission; the view itself is
# guarded (AddAnalysisRequest) so only staff reach it.

from Products.Five.browser import BrowserView
from bika.lims import api


class CloseRequestView(BrowserView):

    def __call__(self):
        obj = self.context
        try:
            with api.security.as_privileged_user():
                for tid in ("process", "resolve", "close"):
                    if api.get_review_status(obj) == "closed":
                        break
                    try:
                        api.do_transition_for(obj, tid)
                    except Exception:
                        pass
        except Exception:
            pass
        # back to the sample-intake register
        try:
            back = api.get_url(api.get_parent(obj))
        except Exception:
            back = api.get_url(api.get_portal())
        self.request.response.redirect(back)
        return u""
