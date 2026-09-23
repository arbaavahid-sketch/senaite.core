# -*- coding: utf-8 -*-
#
# One-off admin tool: let reception staff (LabClerk) drive the sample-request
# workflow through the STANDARD state menu — exactly like a manager — instead
# of custom buttons.
#
# The customerrequest workflow declares "Review portal content" with
# acquired="True" in every state, so it does not override it: granting that
# permission on the sample-intake register is enough and the requests inside
# inherit it. Scoped to the register, so nothing else on the site changes.
#
# Dry-run by default; ?apply=1 writes. ManageBika only.

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode

_PERM = "Review portal content"
_ROLES = ("LabClerk",)


class GrantIntakeWorkflowView(BrowserView):

    def __call__(self):
        apply = bool(self.request.get("apply"))
        out = [u"MODE: %s" % (u"APPLY" if apply else
                              u"DRY-RUN (add ?apply=1 to write)"), u""]

        setup = api.get_senaite_setup()
        container = getattr(setup, "sampleintake", None)
        if container is None:
            out.append(u"ERROR: sample-intake register not found")
            return self._plain(out)

        try:
            current = [r["name"] for r in container.rolesOfPermission(_PERM)
                       if r.get("selected")]
        except Exception as exc:  # noqa
            out.append(u"ERROR reading permission: %s" % safe_unicode(exc))
            return self._plain(out)

        target = sorted(set(current) | set(_ROLES))
        out.append(u"register:   %s" % safe_unicode(api.get_url(container)))
        out.append(u"permission: %s" % _PERM)
        out.append(u"current explicit roles: %s"
                   % (u", ".join(current) or u"(none — fully acquired)"))
        out.append(u"%s roles -> %s   (acquire stays ON)"
                   % (u"SET" if apply else u"would set", u", ".join(target)))

        if apply:
            try:
                container.manage_permission(_PERM, roles=target, acquire=1)
                out.append(u"")
                out.append(u"done. LabClerk now gets the normal workflow menu "
                           u"on sample requests: received -> process -> "
                           u"in_progress -> resolve -> resolved -> close -> "
                           u"closed (and reopen).")
            except Exception as exc:  # noqa
                out.append(u"ERROR applying: %s" % safe_unicode(exc))

        out.append(u"")
        out.append(u"NOTE: scoped to the sample-intake register only; the "
                   u"price/payment stays manager-only (role-based).")
        return self._plain(out)

    def _plain(self, lines):
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines).encode("utf-8")
