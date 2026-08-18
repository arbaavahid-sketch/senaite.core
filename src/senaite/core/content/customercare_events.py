# -*- coding: utf-8 -*-
#
# Event handlers for customer-care records (Complaint / SupportRequest / Survey).
#
# 1) assign_access_token: on creation, assign an unguessable access token that
#    backs the customer's direct tracking link (@@track-request?token=...), so a
#    customer can open their answer with a single click.
#
# 2) notify_customer_on_close: when a request is *closed* by staff, email the
#    customer (if they left an address) the lab's response plus the tracking
#    link. Bilingual (fa/en). Requires SMTP configured in the mail control panel
#    (@@mail-controlpanel). Never raises out of the transition: a mail failure
#    must not block the workflow.

import logging
import uuid

from bika.lims import api

logger = logging.getLogger("senaite.core.customercare")


def assign_access_token(obj, event):
    """Assign a random access token on creation if not already set."""
    try:
        token = getattr(obj, "access_token", None)
    except Exception:
        token = None
    if not token:
        obj.access_token = uuid.uuid4().hex


def _response_text(obj):
    """Return the customer-facing response text, whatever the type calls it."""
    for attr in ("customer_response", "response"):
        val = getattr(obj, attr, None)
        if val:
            return val
    return u""


def _track_link(obj):
    portal = api.get_portal()
    base = api.get_url(portal)
    token = getattr(obj, "access_token", None)
    if token:
        return u"%s/@@track-request?token=%s" % (base, token)
    return base


def _lab_title():
    try:
        return api.get_portal().Title()
    except Exception:
        return u"Tandis Laboratory"


def _build_email(obj):
    """Return (subject, body) as a bilingual (fa + en) plain-text message."""
    subject_line = getattr(obj, "title", None) or api.get_id(obj)
    response = _response_text(obj)
    link = _track_link(obj)
    lab = _lab_title()

    subject = u"پاسخ درخواست شما — {lab} / Your request has been answered".format(
        lab=lab)

    fa = (
        u"با سلام،\n"
        u"درخواست شما با موضوع «{subject}» بررسی و پاسخ داده شد.\n\n"
        u"پاسخ آزمایشگاه:\n{response}\n\n"
        u"برای مشاهدهٔ جزئیات و وضعیت درخواست روی لینک زیر کلیک کنید:\n{link}\n\n"
        u"با احترام،\n{lab}"
    ).format(subject=subject_line,
             response=response or u"(در سامانه قابل مشاهده است)",
             link=link, lab=lab)

    en = (
        u"Hello,\n"
        u"Your request \"{subject}\" has been reviewed and answered.\n\n"
        u"Laboratory response:\n{response}\n\n"
        u"To view the details and status, open the link below:\n{link}\n\n"
        u"Regards,\n{lab}"
    ).format(subject=subject_line,
             response=response or u"(available in the portal)",
             link=link, lab=lab)

    sep = u"\n\n" + (u"-" * 56) + u"\n\n"
    return subject, fa + sep + en


def notify_customer_on_close(obj, event):
    """Email the customer their answer + tracking link when a request closes."""
    transition = getattr(event, "transition", None)
    if transition is None or getattr(transition, "id", None) != "close":
        return

    email = (getattr(obj, "contact_email", None) or u"").strip()
    if not email:
        logger.info("No contact email on %s; skipping close notification",
                    api.get_id(obj))
        return

    try:
        from plone import api as ploneapi
        subject, body = _build_email(obj)
        ploneapi.portal.send_email(
            recipient=email, subject=subject, body=body)
        logger.info("Sent close notification for %s to %s",
                    api.get_id(obj), email)
    except Exception:
        # Mail must never break the workflow transition. Log and move on.
        logger.exception("Failed to email close notification for %s",
                         api.get_id(obj))
