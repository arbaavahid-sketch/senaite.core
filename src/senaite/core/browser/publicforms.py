# -*- coding: utf-8 -*-
"""Bounded public form input and process-local throttling, before privileged writes."""
import hashlib
import re
import threading
import time
from collections import OrderedDict
from datetime import date

class InvalidInput(ValueError): pass

LISTS = {'service_uids': 200, 'storage_conditions': 16, 'safety_hazards': 16}
LONG_TEXT = {'address', 'sample_description', 'safety_notes', 'other_tests', 'description'}
ENUMS = {'priority': ('normal', 'urgent'), 'report_delivery': ('email', 'inperson', 'post'),
         'kind': ('complaint', 'support', 'survey'), 'severity': ('low', 'medium', 'high'),
         'category': ('result', 'turnaround', 'report', 'service', 'sampling', 'other')}

def text(value, limit):
    if value is None: return u''
    if not isinstance(value, basestring): raise InvalidInput('shape')
    if isinstance(value, str):
        try: value = value.decode('utf-8')
        except UnicodeError: raise InvalidInput('encoding')
    if len(value) > limit or any(ord(c) < 32 and c not in u'\n\r\t' for c in value):
        raise InvalidInput('length')
    return value.strip()

def validate_form(form, choices=None):
    if len(form) > 64: raise InvalidInput('fields')
    out = {}
    for key, value in form.items():
        if key in LISTS:
            values = value if isinstance(value, (list, tuple)) else [value]
            if len(values) > LISTS[key]: raise InvalidInput('list_length')
            values = [text(item, 128) for item in values]
            out[key] = list(OrderedDict((item, None) for item in values if item))
        else:
            limit = 10000 if key in LONG_TEXT else (254 if key == 'contact_email' else 512)
            out[key] = text(value, limit)
    for key, allowed in ENUMS.items():
        if out.get(key) and out[key] not in allowed: raise InvalidInput('choice')
    for key in ('rating_overall', 'rating_timeliness', 'rating_quality', 'rating_communication'):
        if out.get(key) and out[key] not in ('1', '2', '3', '4', '5'): raise InvalidInput('rating')
    email = out.get('contact_email')
    if email and (not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email) or '\r' in email or '\n' in email):
        raise InvalidInput('email')
    for uid in out.get('service_uids', []):
        if not re.match(r'^[a-fA-F0-9]{32}$', uid): raise InvalidInput('services')
    for key, allowed in (choices or {}).items():
        if any(item not in allowed for item in out.get(key, [])): raise InvalidInput('choice')
    raw = out.get('sampling_date')
    if raw:
        try:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', raw): raise ValueError()
            date(*[int(item) for item in raw.split('-')])
        except (ValueError, TypeError, OverflowError): raise InvalidInput('date')
    if 'declaration' in out and out['declaration'] not in ('', '1'): raise InvalidInput('declaration')
    return out

class RateLimiter(object):
    """60 submissions / 10 min / client; bounded memory, shared across both forms.

    This is an application guard for the current single-process deployment,
    not a distributed DDoS protection service. Only opaque client hashes live here.
    """
    def __init__(self, clock=None):
        self.clock = clock or time.time
        self.lock = threading.Lock()
        self.clients = {}
    def allow(self, client):
        key = hashlib.sha256(client.encode('utf-8')).hexdigest()
        with self.lock:
            now = self.clock()
            self.clients = {key: record for key, record in self.clients.items() if record[0] > now}
            expiry, count = self.clients.get(key, (now + 600, 0))
            if count >= 60 or (key not in self.clients and len(self.clients) >= 4096): return False
            self.clients[key] = (expiry, count + 1)
            return True

LIMITER = RateLimiter()

def guard(view, choices=None):
    try:
        form = validate_form(view.request.form, choices)
    except InvalidInput:
        reject(view, 'invalid')
        return None
    if form.get('website'): return None
    # Caddy overwrites this dedicated header with the actual socket peer address.
    # Port 8080 is private; direct local access falls back to REMOTE_ADDR.
    client = view.request.environ.get('HTTP_X_TPPC_CLIENT_IP') or view.request.environ.get('REMOTE_ADDR') or 'unknown'
    if not isinstance(client, basestring) or len(client) > 128: client = 'unknown'
    if not LIMITER.allow(client):
        reject(view, 'rate')
        return None
    return form

def reject(view, reason):
    persian = view.lang == 'fa'
    if reason == 'rate':
        view.request.response.setStatus(429)
        view.request.response.setHeader('Retry-After', '600')
        view.error = u'تعداد ارسال‌ها زیاد است؛ ده دقیقه بعد دوباره تلاش کنید.' if persian else u'Too many submissions. Please try again in ten minutes.'
    elif reason == 'services':
        view.request.response.setStatus(400)
        view.error = u'یکی از آزمون‌های انتخابی فعال نیست؛ فهرست آزمون‌ها را تازه کنید.' if persian else u'A selected test is no longer active. Please refresh the test list.'
    elif reason == 'save':
        view.request.response.setStatus(503)
        view.error = u'ثبت درخواست انجام نشد؛ لطفاً دوباره تلاش کنید.' if persian else u'The request could not be saved. Please try again.'
    else:
        view.request.response.setStatus(400)
        view.error = u'ورودی فرم معتبر نیست؛ گزینه‌ها، تاریخ و طول متن‌ها را بررسی کنید.' if persian else u'Invalid form input. Please check the options, date and text lengths.'
