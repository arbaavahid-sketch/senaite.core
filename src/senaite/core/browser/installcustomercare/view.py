# -*- coding: utf-8 -*-
#
# One-shot installer for the Customer Care module (complaints, surveys, support
# requests). Registers the FTIs and workflow into the running site and creates
# the "customercare" container under senaite setup. Idempotent; Manager-only.

from Products.Five.browser import BrowserView

from bika.lims import api
from senaite.core.setuphandlers import add_dexterity_items

PROFILE = "profile-senaite.core:default"
FTIS = ("CustomerCare", "Complaint", "SupportRequest", "Survey")


class InstallCustomerCareView(BrowserView):

    def __call__(self):
        lines = []
        setup = api.get_tool("portal_setup")

        for step in ("typeinfo", "workflow", "rolemap"):
            try:
                setup.runImportStepFromProfile(PROFILE, step)
                lines.append("import step '%s': OK" % step)
            except Exception as exc:  # noqa
                lines.append("import step '%s': FAILED - %s" % (step, exc))

        try:
            senaite_setup = api.get_senaite_setup()
            if senaite_setup.get("customercare") is None:
                add_dexterity_items(senaite_setup, [
                    ("customercare", "Customer Care", "CustomerCare"),
                ])
                lines.append("container 'customercare': CREATED")
            else:
                lines.append("container 'customercare': already exists")
        except Exception as exc:  # noqa
            lines.append("container creation: FAILED - %s" % exc)

        pt = api.get_tool("portal_types")
        for tid in FTIS:
            lines.append("FTI '%s': %s" % (
                tid, "present" if pt.getTypeInfo(tid) else "MISSING"))

        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines)
