# -*- coding: utf-8 -*-
#
# Online payment (Zarinpal) for customer sample-requests.
#
# @@set-payment  (staff, on a SampleRequest): set the amount to charge (Rial).
# @@pay          (public, ?token=): confirm by GET, start by CSRF-checked POST.
# @@pay-callback (public): Zarinpal returns here; verify and mark as paid.
#
# Payment state is stored as plain attributes on the request:
#   payment_amount (int Rial), payment_paid (bool), payment_ref (str),
#   payment_authority (str). Frozen attempts and unique references live in
#   the setup annotation ledger; old unbound authorities are not accepted.

import logging
import re
import transaction
from DateTime import DateTime
from ZODB.POSException import ConflictError
from plone.protect import CheckAuthenticator, PostOnly
from plone.protect.authenticator import createToken
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from six.moves.urllib.parse import urlencode
from xml.sax.saxutils import escape

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from bika.lims import api
from bika.lims.api import safe_unicode

from . import zarinpal
from .state import get_ledger, add_attempt, bound_attempt, claim_paid, PaymentStateError

logger = logging.getLogger("senaite.core.payment")

_TYPES = ("SampleRequest",)


def _digits(value):
    """Parse a non-negative whole Rial amount, without dropping minus/decimal signs."""
    s = safe_unicode(value or u"").strip().replace(u'٬', u',')
    if not s:
        return u''
    if len(s) > 32:
        raise ValueError('invalid_amount')
    out = []
    for ch in s:
        if ch.isdecimal():
            # normalise Persian/Arabic digits to ascii
            out.append(unicode(int(ch)))  # noqa: F821 (py2)
        elif ch == u',':
            out.append(ch)
        else:
            raise ValueError('invalid_amount')
    normalized = u''.join(out)
    if not re.match(r'^(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)$', normalized):
        raise ValueError('invalid_amount')
    return normalized.replace(u',', u'')


def _h(value):
    return escape(safe_unicode(value or u''), {'"': '&quot;', "'": '&#x27;'})


def _after_commit(success, callback, args):
    if success:
        try:
            callback(*args)
        except Exception:
            logger.exception('payment: notification after commit failed')


def is_price_manager(context):
    """True only for real managers (LabManager/Manager). NOTE: the ManageBika
    permission is ALSO granted to LabClerk, so we check the role explicitly to
    keep price/payment away from reception clerks."""
    from AccessControl import getSecurityManager
    try:
        roles = getSecurityManager().getUser().getRolesInContext(context)
    except Exception:
        roles = []
    return bool(set(roles) & {"LabManager", "Manager"})


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
    except ConflictError:
        raise
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
        if not is_price_manager(obj):
            self.request.response.setStatus(403)
            self.request.response.setHeader(
                "Content-Type", "text/html; charset=utf-8")
            return _page(u"دسترسی ندارید",
                         u"<p>این بخش فقط برای مدیر است.</p>",
                         color="#d33").encode("utf-8")
        saved = False
        notified = False
        if self.request.get("REQUEST_METHOD") == "POST":
            PostOnly(self.request)
            CheckAuthenticator(self.request)
            try:
                amount = _digits(self.request.form.get("payment_amount"))
            except ValueError:
                self.request.response.setStatus(400)
                return _page(u'مبلغ نامعتبر', u'<p>مبلغ را به صورت عدد صحیح و غیرمنفی به ریال وارد کنید.</p>').encode('utf-8')
            new_amount = int(amount) if amount else 0
            old_amount = int(getattr(obj, 'payment_amount', 0) or 0)
            if bool(getattr(obj, 'payment_paid', False)) and new_amount != old_amount:
                self.request.response.setStatus(409)
                return _page(u'پرداخت قبلاً ثبت شده', u'<p>مبلغ درخواست پرداخت‌شده از این بخش قابل تغییر نیست.</p>').encode('utf-8')
            changed = new_amount != old_amount
            if changed:
                obj.payment_amount = new_amount
                obj.payment_authority = u''
                obj.payment_requested_amount = 0
                obj.reindexObject()
            saved = True
            if (changed and new_amount >= 1000 and zarinpal.is_configured()
                    and safe_unicode(getattr(obj, 'contact_email', '') or '').strip()):
                transaction.get().addAfterCommitHook(_after_commit,
                    args=(self._notify_customer, (obj, new_amount)))
                notified = True
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        paid = bool(getattr(obj, "payment_paid", False))
        ref = safe_unicode(getattr(obj, "payment_ref", u"") or u"")
        toman = amount // 10 if amount else 0
        msg = u""
        if saved:
            msg = u'<p style="color:#169b4c">✔ ذخیره شد.%s</p>' % (
                u" درخواست ارسال اعلان پرداخت ثبت شد." if notified else
                u" اعلان پرداخت ارسال نشد.")
        status = (
            u'<p><b>وضعیت:</b> پرداخت‌شده ✅ (کد رهگیری: %s)</p>' % _h(ref)
            if paid else u'<p><b>وضعیت:</b> پرداخت‌نشده</p>')
        body = (
            u'%s%s'
            u'<form method="post">'
            u'<input type="hidden" name="_authenticator" value="%s"/>'
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
        ) % (msg, status, createToken(), amount or u"", u"{:,}".format(toman))
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
            ) % (_h(code), u"{:,}".format(amount), u"{:,}".format(amount // 10),
                 _h(pay_url), _h(track_url), _h(track_url), _h(lab))
            subject = u"هزینهٔ آزمون شما — %s" % code
            m = MIMEText(html.encode("utf-8"), "html", "utf-8")
            ploneapi.portal.send_email(
                recipient=email, subject=subject, body=m, immediate=True)
            return True
        except Exception:
            logger.exception("payment: could not email customer")
            return False


class PayView(BrowserView):
    """Public confirmation and explicit POST to start a bound payment attempt."""

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
                % _h(getattr(obj, "payment_ref", u"") or u""),
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
        # Opening a link only displays a confirmation. A token-bearing POST
        # starts a gateway request, so crawlers/GETs cannot create attempts.
        if self.request.get('REQUEST_METHOD', 'GET') == 'GET':
            body = (u'<p>مبلغ قابل پرداخت: <b>%s ریال</b></p>'
                    u'<form method="post"><input type="hidden" name="token" value="%s"/>'
                    u'<input type="hidden" name="_authenticator" value="%s"/>'
                    u'<button type="submit">ورود به درگاه پرداخت</button></form>') % (
                        u'{:,}'.format(amount), _h(token), createToken())
            return self._html(_page(u'تأیید پرداخت', body))
        PostOnly(self.request)
        CheckAuthenticator(self.request)
        portal_url = api.get_url(api.get_portal())
        callback = u"%s/@@pay-callback?%s" % (
            portal_url, urlencode({'token': safe_unicode(token)}))
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
        savepoint = transaction.savepoint(optimistic=True)
        try:
            with api.security.as_privileged_user():
                ledger = get_ledger(api.get_senaite_setup(), create=True)
                add_attempt(ledger, zarinpal.payment_scope(), safe_unicode(authority),
                            api.get_uid(obj), amount, DateTime().ISO8601())
                obj.payment_authority = safe_unicode(authority)
                obj.payment_requested_amount = amount
        except ConflictError:
            raise
        except Exception:
            savepoint.rollback()
            logger.exception('payment: could not bind gateway attempt')
            self.request.response.setStatus(503)
            return self._html(_page(u'ثبت تراکنش کامل نشد',
                u'<p>انتقال به درگاه انجام نشد. بعداً دوباره تلاش کنید.</p>', color='#d33'))
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
        track = u"%s/@@track-request?%s" % (api.get_url(api.get_portal()),
                                         urlencode({'token': safe_unicode(token)}))
        link = (u'<p style="margin-top:16px"><a href="%s">مشاهدهٔ وضعیت '
                u'درخواست</a></p>') % _h(track)
        if safe_unicode(status or u"").upper() != u"OK":
            return self._html(_page(
                u"پرداخت لغو شد",
                u"<p>پرداخت انجام نشد یا لغو شد.</p>" + link, color="#d33"))
        amount = int(getattr(obj, "payment_amount", 0) or 0)
        authority = safe_unicode(authority or u'').strip()
        if not zarinpal.valid_authority(authority) or amount < 1000:
            self.request.response.setStatus(400)
            return self._html(_page(u'اطلاعات تراکنش نامعتبر است', link, color='#d33'))
        ledger = get_ledger(api.get_senaite_setup())
        scope = zarinpal.payment_scope()
        uid = api.get_uid(obj)
        try:
            attempt = bound_attempt(ledger, scope, authority, uid, amount)
        except PaymentStateError:
            self.request.response.setStatus(400)
            return self._html(_page(u'تراکنش با این درخواست و مبلغ مطابقت ندارد',
                u'<p>تراکنش ثبت نشد. برای بررسی با آزمایشگاه تماس بگیرید.</p>' + link, color='#d33'))
        if bool(getattr(obj, 'payment_paid', False)):
            if (attempt['state'] == 'paid' and attempt['ref']
                    and attempt['ref'] == getattr(obj, 'payment_ref', '')
                    and ledger['references'].get('%s|%s' % (scope, attempt['ref']))
                        == '%s|%s' % (scope, authority)):
                return self._html(_page(u'پرداخت قبلاً ثبت شده',
                    u'<p>کد رهگیری: %s</p>%s' % (_h(attempt['ref']), link), color='#169b4c'))
            self.request.response.setStatus(409)
            return self._html(_page(u'این درخواست قبلاً پرداخت شده است',
                u'<p>برای بررسی تراکنش دیگر با آزمایشگاه تماس بگیرید.</p>' + link, color='#d33'))
        if not zarinpal.is_configured():
            self.request.response.setStatus(503)
            return self._html(_page(u'درگاه پیکربندی نشده', link, color='#d33'))
        ok, ref_id, err = zarinpal.verify_payment(amount, authority)
        if not ok:
            logger.error("payment verify failed: %s", err)
            return self._html(_page(
                u"تأیید پرداخت ناموفق",
                u"<p>پرداخت تأیید نشد. اگر مبلغ کسر شده، برای پیگیری "
                u"با آزمایشگاه تماس بگیرید.</p>" + link, color="#d33"))
        savepoint = transaction.savepoint(optimistic=True)
        try:
            # A gateway callback cannot carry our browser CSRF token. Exempt
            # only after binding the attempt and successful server-side verify.
            alsoProvides(self.request, IDisableCSRFProtection)
            with api.security.as_privileged_user():
                newly_paid = claim_paid(ledger, scope, authority, uid, amount,
                                       safe_unicode(ref_id), obj, DateTime().ISO8601())
        except ConflictError:
            raise
        except Exception:
            savepoint.rollback()
            logger.exception("payment: could not store paid state")
            self.request.response.setStatus(503)
            return self._html(_page(u'ثبت داخلی پرداخت کامل نشد',
                u'<p>ثبت نهایی انجام نشد. با همین اطلاعات دوباره پیگیری کنید یا با آزمایشگاه تماس بگیرید.</p>'
                + link, color='#d33'))
        if newly_paid:
            transaction.get().addAfterCommitHook(_after_commit,
                args=(self._notify_lab, (obj, amount, ref_id)))
        return self._html(_page(
            u"پرداخت موفق ✅",
            u"<p>پرداخت شما با موفقیت انجام شد.</p>"
            u"<p><b>کد رهگیری:</b> %s</p>%s"
            % (_h(ref_id), link), color="#169b4c"))

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
            ) % (_h(code), _h(who), u"{:,}".format(int(amount or 0)),
                 _h(ref_id))
            m = MIMEText(html.encode("utf-8"), "html", "utf-8")
            ploneapi.portal.send_email(
                recipient=lab_email,
                subject=u"پرداخت جدید — %s" % code, body=m, immediate=True)
        except Exception:
            logger.exception("payment: could not email lab on payment")

    def _html(self, html):
        self.request.response.setHeader("Content-Type",
                                        "text/html; charset=utf-8")
        return html.encode("utf-8")


class PaymentsListView(BrowserView):
    """Staff dashboard (in the app chrome): all requests + payment status."""

    template = ViewPageTemplateFile("templates/payments.pt")

    def __call__(self):
        if not is_price_manager(api.get_portal()):
            self.request.response.setHeader(
                "Content-Type", "text/html; charset=utf-8")
            return _page(u"دسترسی ندارید",
                         u"<p>این بخش فقط برای مدیر است.</p>",
                         color="#d33").encode("utf-8")
        return self.template()

    def get_rows(self):
        setup = api.get_senaite_setup()
        container = getattr(setup, "sampleintake", None)
        rows = []
        if container is not None:
            for obj in container.objectValues():
                if api.get_portal_type(obj) not in _TYPES:
                    continue
                amount = int(getattr(obj, "payment_amount", 0) or 0)
                rows.append({
                    "code": safe_unicode(getattr(obj, "tracking_code", u"")
                                         or api.get_id(obj)),
                    "who": safe_unicode(getattr(obj, "client_name", u"")
                                        or getattr(obj, "contact_name", u"")
                                        or u"—"),
                    "amount": amount,
                    "amount_fmt": (u"{:,}".format(amount) if amount else u"—"),
                    "paid": bool(getattr(obj, "payment_paid", False)),
                    "ref": safe_unicode(getattr(obj, "payment_ref", u"")
                                        or u""),
                    "date": safe_unicode(getattr(obj, "payment_date", u"")
                                         or u"")[:10],
                    "url": safe_unicode(api.get_url(obj)) + u"/@@set-payment",
                })
        # unpaid first (need action), then paid
        rows.sort(key=lambda r: (r["paid"], r["date"]))
        return rows

    def get_totals(self, rows):
        total_all = sum(r["amount"] for r in rows)
        total_paid = sum(r["amount"] for r in rows if r["paid"])
        return {
            "all": u"{:,}".format(total_all),
            "paid": u"{:,}".format(total_paid),
            "pending": u"{:,}".format(total_all - total_paid),
        }
