# -*- coding: utf-8 -*-
#
# One-shot installer for the Sample Intake module (online customer test
# requests). Registers the FTIs and workflow bindings into the running site and
# creates the "sampleintake" container under senaite setup. Idempotent;
# Manager-only.

from Products.Five.browser import BrowserView

from bika.lims import api
from senaite.core.setuphandlers import add_dexterity_items

PROFILE = "profile-senaite.core:default"
FTIS = ("SampleIntake", "SampleRequest")


class InstallSampleIntakeView(BrowserView):

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
            if senaite_setup.get("sampleintake") is None:
                # Create with elevated privileges so the folder is added
                # regardless of who triggers the (idempotent) install step.
                with api.security.as_privileged_user():
                    add_dexterity_items(senaite_setup, [
                        ("sampleintake", "Sample Intake", "SampleIntake"),
                    ])
                lines.append("container 'sampleintake': CREATED")
            else:
                lines.append("container 'sampleintake': already exists")
        except Exception as exc:  # noqa
            lines.append("container creation: FAILED - %s" % exc)

        pt = api.get_tool("portal_types")
        for tid in FTIS:
            lines.append("FTI '%s': %s" % (
                tid, "present" if pt.getTypeInfo(tid) else "MISSING"))

        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines)
