# -*- coding: utf-8 -*-
#
# One-off admin tool: permanently delete TEST samples (AnalysisRequests) by id.
# SENAITE deliberately has no delete for samples (audit trail) — real samples
# should be cancelled/invalidated instead. This exists only to clean up the
# test data created while setting the system up.
#
#   @@delete-samples?ids=TR-26-0014,ST36-26-0009          -> preview
#   @@delete-samples?ids=TR-26-0014,ST36-26-0009&apply=1  -> delete
#
# ManageBika only. Deletion runs as the privileged user so it works whatever
# the sample's workflow state is.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode
from senaite.core.catalog import SAMPLE_CATALOG
from zope.interface import alsoProvides

try:
    from plone.protect.interfaces import IDisableCSRFProtection
except Exception:  # pragma: no cover
    IDisableCSRFProtection = None


class DeleteSamplesView(BrowserView):

    def __call__(self):
        if IDisableCSRFProtection is not None:
            alsoProvides(self.request, IDisableCSRFProtection)

        apply = bool(self.request.get("apply"))
        raw = self.request.get("ids", "")
        if isinstance(raw, (list, tuple)):
            raw = ",".join(raw)
        wanted = set(i.strip() for i in raw.split(",") if i.strip())

        out = [u"MODE: %s" % (u"APPLY (deleting)" if apply else
                              u"DRY-RUN (add &apply=1 to delete)"), u""]
        if not wanted:
            out.append(u"No ids given. Use: "
                       u"@@delete-samples?ids=TR-26-0014,TR-26-0015")
            return self._plain(out)

        found = {}
        for brain in api.search({"portal_type": "AnalysisRequest"},
                                SAMPLE_CATALOG):
            sid = safe_unicode(api.get_id(brain))
            if sid in wanted:
                found[sid] = brain

        for sid in sorted(wanted):
            brain = found.get(sid)
            if brain is None:
                out.append(u"NOT FOUND\t%s" % sid)
                continue
            try:
                client = safe_unicode(brain.getClientTitle or u"")
            except Exception:
                client = u""
            state = safe_unicode(api.get_review_status(brain))
            out.append(u"%s\t%s\t[%s]\t%s"
                       % (u"DELETE" if apply else u"would delete",
                          sid, state, client))

        deleted = 0
        if apply and found:
            with api.security.as_privileged_user():
                for sid, brain in found.items():
                    try:
                        obj = api.get_object(brain)
                        parent = api.get_parent(obj)
                        parent.manage_delObjects([api.get_id(obj)])
                        deleted += 1
                    except Exception as exc:  # noqa
                        out.append(u"  ERROR\t%s\t%s"
                                   % (sid, safe_unicode(exc)))
            import transaction
            transaction.commit()

        out.append(u"")
        out.append(u"matched: %d / requested: %d" % (len(found), len(wanted)))
        if apply:
            out.append(u"deleted: %d" % deleted)
        out.append(u"")
        out.append(u"NOTE: for real (non-test) samples use Cancel/Invalidate "
                   u"instead — deleting destroys the audit trail.")
        return self._plain(out)

    def _plain(self, lines):
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines).encode("utf-8")
