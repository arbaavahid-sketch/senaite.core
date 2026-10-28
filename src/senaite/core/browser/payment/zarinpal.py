# -*- coding: utf-8 -*-
#
# Minimal Zarinpal (v4) client for the online payment flow. The merchant id is
# read from the ZARINPAL_MERCHANT_ID environment variable (set in .env on the
# server, passed to the container via docker-compose) so it never lives in the
# code. Amounts are in RIAL (currency IRR). Set ZARINPAL_SANDBOX=1 to test.

import json
import os
import ssl
import hashlib
import re
from six import integer_types, string_types, text_type

try:  # Py2 runtime
    import urllib2 as _urllib
    from urllib2 import Request as _Request
except ImportError:  # pragma: no cover (Py3, only for local linters)
    import urllib.request as _urllib
    from urllib.request import Request as _Request

_PROD = "https://payment.zarinpal.com/pg"
_SANDBOX = "https://sandbox.zarinpal.com/pg"


def _sandbox():
    return (os.environ.get("ZARINPAL_SANDBOX") or "").strip() in ("1", "true", "True", "yes")


def _base():
    return _SANDBOX if _sandbox() else _PROD


def merchant_id():
    return (os.environ.get("ZARINPAL_MERCHANT_ID") or "").strip()


def is_configured():
    return bool(merchant_id())


def payment_scope():
    """Bind attempts to their merchant and environment without storing the key."""
    fingerprint = hashlib.sha256(merchant_id().encode('utf-8')).hexdigest()
    return ('sandbox:' if _sandbox() else 'live:') + fingerprint


def valid_authority(value):
    return isinstance(value, string_types) and bool(re.match(r'^[A-Za-z0-9]{1,128}\Z', value))


def start_pay_url(authority):
    return "%s/StartPay/%s" % (_base(), authority)


def _post(path, payload):
    url = _base() + path
    data = json.dumps(payload).encode("utf-8")
    req = _Request(url, data, {
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    try:
        ctx = ssl.create_default_context()
        resp = _urllib.urlopen(req, timeout=20, context=ctx)
    except TypeError:  # older urlopen without context kwarg
        resp = _urllib.urlopen(req, timeout=20)
    try:
        body = resp.read()
    finally:
        resp.close()
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body)


def request_payment(amount_rial, callback_url, description=u"", mobile=u"",
                    email=u""):
    """Create a payment request. Returns (authority, error_message)."""
    if not is_configured() or int(amount_rial) < 1000:
        return None, u'gateway_not_configured_or_invalid_amount'
    payload = {
        "merchant_id": merchant_id(),
        "amount": int(amount_rial),
        "currency": "IRR",
        "callback_url": callback_url,
        "description": (description or u"پرداخت آزمون")[:255],
    }
    meta = {}
    if mobile:
        meta["mobile"] = mobile
    if email:
        meta["email"] = email
    if meta:
        payload["metadata"] = meta
    try:
        res = _post("/v4/payment/request.json", payload)
    except Exception as exc:  # noqa
        return None, u"connection_error:%s" % type(exc).__name__
    data = res.get('data') if isinstance(res, dict) else None
    if not isinstance(data, dict):
        return None, u'invalid_gateway_response'
    if data.get("code") == 100 and valid_authority(data.get("authority")):
        return data["authority"], None
    return None, u"request_failed code=%s" % data.get('code')


def verify_payment(amount_rial, authority):
    """Verify a returned payment. Returns (ok, ref_id, error_message)."""
    if not is_configured() or int(amount_rial) < 1000 or not valid_authority(authority):
        return False, None, u'gateway_not_configured_or_invalid_attempt'
    payload = {
        "merchant_id": merchant_id(),
        "amount": int(amount_rial),
        "authority": authority,
    }
    try:
        res = _post("/v4/payment/verify.json", payload)
    except Exception as exc:  # noqa
        return False, None, u"connection_error:%s" % type(exc).__name__
    data = res.get('data') if isinstance(res, dict) else None
    if not isinstance(data, dict):
        return False, None, u'invalid_gateway_response'
    # 100 = verified now, 101 = already verified before
    ref = data.get('ref_id')
    ref = text_type(ref) if isinstance(ref, integer_types + string_types) and not isinstance(ref, bool) else u''
    if data.get("code") in (100, 101) and re.match(r'^[0-9]+\Z', ref) and int(ref) > 0:
        return True, ref, None
    return False, None, u"verify_failed code=%s" % data.get('code')
