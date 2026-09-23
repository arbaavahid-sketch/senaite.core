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
        notified = False
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
            if obj.payment_amount >= 1000:
                notified = self._notify_customer(obj, obj.payment_amount)
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        paid = bool(getattr(obj, "payment_paid", False))
        ref = safe_unicode(getattr(obj, "payment_ref", u"") or u"")
        toman = amount // 10 if amount else 0
        msg = u""
        if saved:
            msg = u'<p style="color:#169b4c">✔ ذخیره شد.%s</p>' % (
                u" ایمیلِ پرداخت به مشتری ارسال شد." if notified else
                u" (ایمیلی ارسال نشد — مشتری ایمیل نداشت یا خطا رخ داد.)")
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

    def _notify_customer(self, obj, amount):
        """Email the customer that a payable amount was set, with a pay link."""
        email = safe_unicode(
            getattr(obj, "contact_email", u"") or u"").strip()
        if not email:
            return False
        try:
            from plone import api as ploneapi
            from email.mime.text import MIMEText
            portal_url = api.get_url(api.get_portal())
            token = safe_unicode(getattr(obj, "access_token", u"") or u"")
            pay_url = u"%s/@@pay?token=%s" % (portal_url, token)
            track_url = u"%s/@@track-request?token=%s" % (portal_url, token)
            code = safe_unicode(getattr(obj, "tracking_code", u"")
                                or api.get_id(obj))
            try:
                lab = ploneapi.portal.get_registry_record(
                    "plone.site_title") or u"آزمایشگاه تندیس پارس"
            except Exception:
                lab = u"آزمایشگاه تندیس پارس"
            html = (
                u'<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;'
                u'font-size:14px;line-height:1.9;color:#1a2230">'
                u'با سلام،<br/>'
                u'هزینهٔ آزمونِ درخواستِ شما با شمارهٔ <b>%s</b> مشخص شد:'
                u'<br/><br/>'
                u'<b>مبلغ قابل پرداخت:</b> %s ریال (%s تومان)<br/><br/>'
                u'برای پرداختِ آنلاین روی دکمهٔ زیر کلیک کنید:<br/>'
                u'<a href="%s" style="display:inline-block;background:#ef7d1a;'
                u'color:#fff;text-decoration:none;padding:10px 22px;'
                u'border-radius:8px;margin:8px 0">پرداخت آنلاین</a><br/><br/>'
                u'یا وضعیت و پرداخت را از صفحهٔ پیگیری ببینید:<br/>'
                u'<a href="%s">%s</a><br/><br/>'
                u'با احترام،<br/>%s</div>'
            ) % (code, u"{:,}".format(amount), u"{:,}".format(amount // 10),
                 pay_url, track_url, track_url, safe_unicode(lab))
            subject = u"هزینهٔ آزمون شما — %s" % code
            m = MIMEText(html.encode("utf-8"), "html", "utf-8")
            ploneapi.portal.send_email(
                recipient=email, subject=subject, body=m)
            return True
        except Exception:
            logger.exception("payment: could not email customer")
            return False


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
                try:
                    from DateTime import DateTime
                    obj.payment_date = DateTime().ISO8601()
                except Exception:
                    pass
                obj.reindexObject()
        except Exception:
            logger.exception("payment: could not store paid state")
        self._notify_lab(obj, amount, ref_id)
        return self._html(_page(
            u"پرداخت موفق ✅",
            u"<p>پرداخت شما با موفقیت انجام شد.</p>"
            u"<p><b>کد رهگیری:</b> %s</p>%s"
            % (safe_unicode(ref_id), link), color="#169b4c"))

    def _notify_lab(self, obj, amount, ref_id):
        """Email the lab that a payment was received."""
        try:
            from plone import api as ploneapi
            from email.mime.text import MIMEText
            try:
                lab_email = ploneapi.portal.get_registry_record(
                    "plone.email_from_address")
            except Exception:
                lab_email = None
            if not lab_email:
                return
            code = safe_unicode(getattr(obj, "tracking_code", u"")
                                or api.get_id(obj))
            who = safe_unicode(getattr(obj, "client_name", u"")
                               or getattr(obj, "contact_name", u"") or u"—")
            html = (
                u'<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;'
                u'font-size:14px;line-height:1.9;color:#1a2230">'
                u'یک <b>پرداختِ جدید</b> در سامانه ثبت شد:<br/><br/>'
                u'<b>درخواست:</b> %s<br/>'
                u'<b>مشتری:</b> %s<br/>'
                u'<b>مبلغ:</b> %s ریال<br/>'
                u'<b>کد رهگیری:</b> %s</div>'
            ) % (code, who, u"{:,}".format(int(amount or 0)),
                 safe_unicode(ref_id))
            m = MIMEText(html.encode("utf-8"), "html", "utf-8")
            ploneapi.portal.send_email(
                recipient=lab_email,
                subject=u"پرداخت جدید — %s" % code, body=m)
        except Exception:
            logger.exception("payment: could not email lab on payment")

    def _html(self, html):
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return html.encode("utf-8")


class PaymentsListView(BrowserView):
    """Staff dashboard: all requests with a payment amount, paid or not."""

    def __call__(self):
        setup = api.get_senaite_setup()
        container = getattr(setup, "sampleintake", None)
        rows = []
        total_all = total_paid = 0
        if container is not None:
            for obj in container.objectValues():
                if api.get_portal_type(obj) not in _TYPES:
                    continue
                amount = int(getattr(obj, "payment_amount", 0) or 0)
                paid = bool(getattr(obj, "payment_paid", False))
                total_all += amount
                if paid:
                    total_paid += amount
                rows.append({
                    "code": safe_unicode(getattr(obj, "tracking_code", u"")
                                         or api.get_id(obj)),
                    "who": safe_unicode(getattr(obj, "client_name", u"")
                                        or getattr(obj, "contact_name", u"")
                                        or u"—"),
                    "amount": amount,
                    "paid": paid,
                    "ref": safe_unicode(getattr(obj, "payment_ref", u"")
                                        or u""),
                    "date": safe_unicode(getattr(obj, "payment_date", u"")
                                         or u"")[:10],
                    "url": safe_unicode(api.get_url(obj)) + u"/@@set-payment",
                })
        # unpaid first (need action), then paid; newest first within each
        rows.sort(key=lambda r: (r["paid"], r["date"]))

        tr = []
        for r in rows:
            if r["paid"]:
                badge = u'<span style="color:#169b4c">پرداخت‌شده ✅</span>'
            elif r["amount"] > 0:
                badge = u'<span style="color:#c47f17">در انتظار پرداخت</span>'
            else:
                badge = (u'<a href="%s" style="color:#1e2f5e">تعیین مبلغ</a>'
                         % r["url"])
            amount_txt = u"{:,}".format(r["amount"]) if r["amount"] else u"—"
            tr.append(
                u'<tr>'
                u'<td><a href="%s">%s</a></td>'
                u'<td>%s</td>'
                u'<td style="text-align:left;direction:ltr">%s</td>'
                u'<td>%s</td><td><code>%s</code></td><td>%s</td></tr>'
                % (r["url"], r["code"], r["who"],
                   amount_txt, badge, r["ref"], r["date"]))

        body = (
            u'<p style="color:#555">جمع کل: <b>%s</b> ریال — '
            u'پرداخت‌شده: <b style="color:#169b4c">%s</b> ریال — '
            u'در انتظار: <b style="color:#c47f17">%s</b> ریال</p>'
            u'<table style="width:100%%;border-collapse:collapse" '
            u'cellpadding="8">'
            u'<thead><tr style="background:#f0f3f8;text-align:right">'
            u'<th>شماره</th><th>مشتری</th><th>مبلغ (ریال)</th>'
            u'<th>وضعیت</th><th>کد رهگیری</th><th>تاریخ</th></tr></thead>'
            u'<tbody>%s</tbody></table>'
        ) % (u"{:,}".format(total_all), u"{:,}".format(total_paid),
             u"{:,}".format(total_all - total_paid),
             (u"".join(tr) or
              u'<tr><td colspan="6" style="color:#777">موردی نیست.</td>'
              u'</tr>'))
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return _page(u"پرداخت‌ها", body).encode("utf-8")
