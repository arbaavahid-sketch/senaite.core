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
from bika.lims.api import safe_unicode

logger = logging.getLogger("senaite.core.customercare")


def _esc(value):
    """Escape text for safe HTML embedding; turn newlines into <br/>."""
    s = safe_unicode(value if value is not None else u"")
    s = (s.replace(u"&", u"&amp;").replace(u"<", u"&lt;")
          .replace(u">", u"&gt;"))
    return s.replace(u"\r\n", u"\n").replace(u"\n", u"<br/>")


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
    # Prefer the configured Site title (registry 'plone.site_title'), which is
    # what the Site control panel edits and what users expect as the lab name.
    # The portal object's own Title() can still be the default "SENAITE LIMS".
    try:
        from plone import api as ploneapi
        title = ploneapi.portal.get_registry_record("plone.site_title")
        if title:
            return title
    except Exception:
        pass
    try:
        return api.get_portal().Title()
    except Exception:
        return u"Tandis Laboratory"


def _build_email(obj):
    """Return (subject, html_body). HTML so Persian renders right-to-left."""
    subject_line = _esc(getattr(obj, "title", None) or api.get_id(obj))
    resp = _response_text(obj)
    response_fa = _esc(resp) or u"(در سامانه قابل مشاهده است)"
    response_en = _esc(resp) or u"(available in the portal)"
    link = _track_link(obj)
    link_e = _esc(link)
    lab = _esc(_lab_title())

    subject = u"پاسخ درخواست شما — %s / Your request has been answered" % \
        _lab_title()

    fa = (
        u'<div dir="rtl" style="text-align:right;'
        u'font-family:Tahoma,Arial,sans-serif;font-size:14px;line-height:1.9;'
        u'color:#1a2230">'
        u'با سلام،<br/>'
        u'درخواست شما با موضوع «%s» بررسی و پاسخ داده شد.<br/><br/>'
        u'<b>پاسخ آزمایشگاه:</b><br/>%s<br/><br/>'
        u'برای مشاهدهٔ جزئیات و وضعیت درخواست، روی لینک زیر کلیک کنید:<br/>'
        u'<a href="%s">%s</a><br/><br/>'
        u'با احترام،<br/>%s'
        u'</div>'
    ) % (subject_line, response_fa, link_e, link_e, lab)

    en = (
        u'<div dir="ltr" style="text-align:left;'
        u'font-family:Arial,sans-serif;font-size:13px;line-height:1.6;'
        u'color:#1a2230">'
        u'Hello,<br/>'
        u'Your request &quot;%s&quot; has been reviewed and answered.<br/><br/>'
        u'<b>Laboratory response:</b><br/>'
        u'<span dir="auto">%s</span><br/><br/>'
        u'To view the details and status, open the link below:<br/>'
        u'<a href="%s">%s</a><br/><br/>'
        u'Regards,<br/>%s'
        u'</div>'
    ) % (subject_line, response_en, link_e, link_e, lab)

    html = (
        u'<html><body style="margin:0;padding:16px;background:#f6f8fb">'
        u'<div style="max-width:640px;margin:0 auto;background:#fff;'
        u'border:1px solid #e3e7ee;border-radius:10px;padding:20px 24px">'
        u'%s<hr style="border:none;border-top:1px solid #e3e7ee;margin:20px 0"/>'
        u'%s</div></body></html>'
    ) % (fa, en)
    return subject, html


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
        from email.mime.text import MIMEText
        subject, html = _build_email(obj)
        # Send as HTML so the Persian text renders right-to-left.
        msg = MIMEText(html.encode("utf-8"), "html", "utf-8")
        ploneapi.portal.send_email(
            recipient=email, subject=subject, body=msg)
        logger.info("Sent close notification for %s to %s",
                    api.get_id(obj), email)
    except Exception:
        # Mail must never break the workflow transition. Log and move on.
        logger.exception("Failed to email close notification for %s",
                         api.get_id(obj))
