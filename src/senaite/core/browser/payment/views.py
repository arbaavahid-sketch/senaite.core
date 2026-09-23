# -*- coding: utf-8 -*-
#
# Online payment (Zarinpal) for customer sample-requests.
#
# @@set-payment  (staff, on a SampleRequest): set the amount to charge (Rial).
# @@pay          (public, ?token=): start a payment, redirect to Zarinpal.
# @@pay-callback (public): Zarinpal returns here; verify and mark as paid.
#
# Payment state is stored as plain attributes on the request:
#   payment_amount (int Rial), payment_paid (bool), payment_ref (str),
#   payment_authority (str).

import logging

from Products.Five.browser import BrowserView
from bika.lims import api
from bika.lims.api import safe_unicode

from . import zarinpal

logger = logging.getLogger("senaite.core.payment")

_TYPES = ("SampleRequest",)


def _digits(value):
    """Keep digits only (accept Persian/Arabic digits too)."""
    s = safe_unicode(value or u"")
    out = []
    for ch in s:
        if ch.isdigit():
            # normalise Persian/Arabic digits to ascii
            out.append(unicode(int(ch)))  # noqa: F821 (py2)
    return u"".join(out)


def _find_by_token(token):
    token = safe_unicode(token or u"").strip()
    if not token:
        return None
    try:
        setup = api.get_senaite_setup()
        container = getattr(setup, "sampleintake", None)
        if container is None:
            return None
        for obj in container.objectValues():
            if api.get_portal_type(obj) not in _TYPES:
                continue
            if safe_unicode(getattr(obj, "access_token", u"") or u"") == token:
                return obj
    except Exception:
        logger.exception("payment: token lookup failed")
    return None


def _page(title, body_html, color="#1e2f5e"):
    return (
        u'<!doctype html><html dir="rtl" lang="fa"><head>'
        u'<meta charset="utf-8"><meta name="viewport" '
        u'content="width=device-width, initial-scale=1">'
        u'<title>%s</title></head>'
        u'<body style="font-family:Tahoma,Arial,sans-serif;background:#f6f8fb;'
        u'margin:0;padding:24px;color:#1a2230">'
        u'<div style="max-width:560px;margin:40px auto;background:#fff;'
        u'border:1px solid #e3e7ee;border-radius:12px;padding:24px 28px">'
        u'<h2 style="margin:0 0 12px;color:%s">%s</h2>%s</div>'
        u'</body></html>'
    ) % (title, color, title, body_html)


class SetPaymentView(BrowserView):
    """Staff view on a SampleRequest to set the amount to charge (Rial)."""

    def __call__(self):
        obj = self.context
        saved = False
        if self.request.get("REQUEST_METHOD") == "POST":
            amount = _digits(self.request.form.get("payment_amount"))
            obj.payment_amount = int(amount) if amount else 0
            # a new/changed amount clears any previous paid flag
            obj.payment_paid = False
            obj.payment_ref = u""
            try:
                obj.reindexObject()
            except Exception:
                pass
            saved = True
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        paid = bool(getattr(obj, "payment_paid", False))
        ref = safe_unicode(getattr(obj, "payment_ref", u"") or u"")
        toman = amount // 10 if amount else 0
        msg = u'<p style="color:#169b4c">✔ ذخیره شد.</p>' if saved else u""
        status = (
            u'<p><b>وضعیت:</b> پرداخت‌شده ✅ (کد رهگیری: %s)</p>' % ref
            if paid else u'<p><b>وضعیت:</b> پرداخت‌نشده</p>')
        body = (
            u'%s%s'
            u'<form method="post">'
            u'<label>مبلغ به ریال:</label><br/>'
            u'<input type="text" name="payment_amount" value="%s" '
            u'style="font-size:16px;padding:8px;width:220px;'
            u'margin:8px 0" inputmode="numeric"/>'
            u'<div style="color:#777;font-size:12px">%s تومان</div>'
            u'<button type="submit" style="margin-top:12px;background:#1e2f5e;'
            u'color:#fff;border:0;border-radius:8px;padding:10px 18px;'
            u'font-size:15px;cursor:pointer">ذخیرهٔ مبلغ</button>'
            u'</form>'
            u'<hr style="margin:18px 0;border:0;border-top:1px solid #eee"/>'
            u'<p style="font-size:13px;color:#555">لینکِ پرداخت (به مشتری در '
            u'صفحهٔ پیگیری نشان داده می‌شود) پس از تعیینِ مبلغ فعال می‌شود.</p>'
        ) % (msg, status, amount or u"", u"{:,}".format(toman))
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return _page(u"تعیین مبلغ پرداخت", body).encode("utf-8")


class PayView(BrowserView):
    """Public: start a Zarinpal payment for the request (?token=...)."""

    def __call__(self):
        token = self.request.get("token")
        obj = _find_by_token(token)
        if obj is None:
            return self._html(_page(u"خطا", u"<p>درخواست پیدا نشد.</p>",
                                    color="#d33"))
        if bool(getattr(obj, "payment_paid", False)):
            return self._html(_page(
                u"قبلاً پرداخت شده",
                u"<p>این درخواست قبلاً پرداخت شده است. کد رهگیری: %s</p>"
                % safe_unicode(getattr(obj, "payment_ref", u"") or u""),
                color="#169b4c"))
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        if amount < 1000:
            return self._html(_page(
                u"مبلغ تعیین نشده",
                u"<p>هنوز مبلغی برای این درخواست تعیین نشده است. لطفاً با "
                u"آزمایشگاه تماس بگیرید.</p>", color="#d33"))
        if not zarinpal.is_configured():
            return self._html(_page(
                u"درگاه پیکربندی نشده",
                u"<p>درگاه پرداخت هنوز تنظیم نشده است.</p>", color="#d33"))
        portal_url = api.get_url(api.get_portal())
        callback = u"%s/@@pay-callback?token=%s" % (
            portal_url, safe_unicode(token))
        desc = u"پرداخت آزمون — %s" % safe_unicode(
            getattr(obj, "tracking_code", u"") or api.get_id(obj))
        authority, err = zarinpal.request_payment(
            amount, callback, desc,
            mobile=safe_unicode(getattr(obj, "contact_phone", u"") or u""),
            email=safe_unicode(getattr(obj, "contact_email", u"") or u""))
        if not authority:
            logger.error("payment request failed: %s", err)
            return self._html(_page(
                u"خطا در اتصال به درگاه",
                u"<p>ایجاد تراکنش ناموفق بود. بعداً دوباره تلاش کنید.</p>",
                color="#d33"))
        try:
            with api.security.as_privileged_user():
                obj.payment_authority = safe_unicode(authority)
        except Exception:
            pass
        self.request.response.redirect(zarinpal.start_pay_url(authority))
        return u""

    def _html(self, html):
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return html.encode("utf-8")


class PayCallbackView(BrowserView):
    """Public: Zarinpal returns the customer here after payment."""

    def __call__(self):
        token = self.request.get("token")
        status = self.request.get("Status") or self.request.get("status")
        authority = self.request.get("Authority") or \
            self.request.get("authority")
        obj = _find_by_token(token)
        if obj is None:
            return self._html(_page(u"خطا", u"<p>درخواست پیدا نشد.</p>",
                                    color="#d33"))
        track = u"%s/@@track-request" % api.get_url(api.get_portal())
        link = (u'<p style="margin-top:16px"><a href="%s">مشاهدهٔ وضعیت '
                u'درخواست</a></p>') % track
        if safe_unicode(status or u"").upper() != u"OK":
            return self._html(_page(
                u"پرداخت لغو شد",
                u"<p>پرداخت انجام نشد یا لغو شد.</p>" + link, color="#d33"))
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        ok, ref_id, err = zarinpal.verify_payment(amount, authority)
        if not ok:
            logger.error("payment verify failed: %s", err)
            return self._html(_page(
                u"تأیید پرداخت ناموفق",
                u"<p>پرداخت تأیید نشد. اگر مبلغ کسر شده، طی ۷۲ ساعت "
                u"بازمی‌گردد.</p>" + link, color="#d33"))
        try:
            with api.security.as_privileged_user():
                obj.payment_paid = True
                obj.payment_ref = safe_unicode(ref_id)
                obj.reindexObject()
        except Exception:
            logger.exception("payment: could not store paid state")
        return self._html(_page(
            u"پرداخت موفق ✅",
            u"<p>پرداخت شما با موفقیت انجام شد.</p>"
            u"<p><b>کد رهگیری:</b> %s</p>%s"
            % (safe_unicode(ref_id), link), color="#169b4c"))

    def _html(self, html):
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return html.encode("utf-8")
