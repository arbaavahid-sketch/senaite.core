# -*- coding: utf-8 -*-
#
# One-shot installer for the Controlled Documents module. Registers the new
# content types (typeinfo) and the controlled-document workflow into the running
# site, then creates the "controlleddocuments" container under senaite setup.
# Idempotent: safe to call more than once. Manager-only (cmf.ManagePortal).

from Products.Five.browser import BrowserView

from bika.lims import api
from senaite.core.setuphandlers import add_dexterity_items

PROFILE = "profile-senaite.core:default"


class InstallDocumentsView(BrowserView):

    def __call__(self):
        lines = []
        setup = api.get_tool("portal_setup")

        # 1. (Re)import the FTIs and the workflow definition/bindings.
        for step in ("typeinfo", "workflow", "rolemap"):
            try:
                setup.runImportStepFromProfile(PROFILE, step)
                lines.append("import step '%s': OK" % step)
            except Exception as exc:  # noqa
                lines.append("import step '%s': FAILED - %s" % (step, exc))

        # 2. Create the container under senaite setup if missing.
        try:
            senaite_setup = api.get_senaite_setup()
            existing = senaite_setup.get("controlleddocuments")
            if existing is None:
                add_dexterity_items(senaite_setup, [
                    ("controlleddocuments", "Controlled Documents",
                     "ControlledDocuments"),
                ])
                lines.append("container 'controlleddocuments': CREATED")
            else:
                lines.append("container 'controlleddocuments': already exists")
        except Exception as exc:  # noqa
            lines.append("container creation: FAILED - %s" % exc)

        # 3. Report FTI availability.
        pt = api.get_tool("portal_types")
        for tid in ("ControlledDocument", "ControlledDocuments"):
            lines.append("FTI '%s': %s" % (
                tid, "present" if pt.getTypeInfo(tid) else "MISSING"))

        self.request.response.setHeader("Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines)
