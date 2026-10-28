# -*- coding: utf-8 -*-
"""Synthetic gateway + real ZODB, transaction and plone.protect regression tests."""
from __future__ import print_function
import ast
import imp
import logging
import os
import re
import unittest
from contextlib import contextmanager
from cStringIO import StringIO
from xml.sax.saxutils import escape
from six.moves.urllib.parse import urlencode
import transaction
from transaction import TransactionManager
from persistent import Persistent
from persistent.mapping import PersistentMapping
from ZODB import DB
from ZODB.MappingStorage import MappingStorage
from ZODB.POSException import ConflictError
from DateTime import DateTime
from plone.protect import CheckAuthenticator, PostOnly
from plone.protect.authenticator import createToken
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from zExceptions import Forbidden

BASE = os.environ.get('PAYMENT_SOURCE') or os.path.dirname(__file__)
if not os.path.isfile(os.path.join(BASE, 'state.py')):
    BASE = os.path.abspath(os.path.join(BASE, '..', 'browser', 'payment'))
state = imp.load_source('payment_state_tested', os.path.join(BASE, 'state.py'))
gateway = imp.load_source('payment_gateway_tested', os.path.join(BASE, 'zarinpal.py'))
state.IAnnotations = lambda setup: setup.annotations

class Record(object):
    def __init__(self, **values):
        self.__dict__.update(values)

class RequestRecord(Persistent):
    def __init__(self, uid):
        self.uid = uid
        self.access_token = 'token-' + uid
        self.payment_amount = 10000
        self.payment_paid = False
        self.payment_ref = ''
        self.payment_authority = ''
        self.contact_email = ''
    def reindexObject(self):
        if getattr(self, '_v_fail_reindex', False):
            raise ValueError('synthetic storage failure')

class Setup(Persistent):
    pass

class Ring(list):
    def random(self):
        return self[0]

@contextmanager
def privileged():
    yield

def load_views(namespace):
    with open(os.path.join(BASE, 'views.py'), 'rb') as source:
        tree = ast.parse(source.read())
    tree.body = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
    eval(compile(tree, 'views.py', 'exec'), namespace)

class PaymentTests(unittest.TestCase):
    def setUp(self):
        self.db = DB(MappingStorage())
        self.connection = self.db.open()
        self.setup = Setup()
        self.setup.annotations = PersistentMapping()
        self.setup.objects = PersistentMapping(a=RequestRecord('a'), b=RequestRecord('b'))
        self.connection.root()['setup'] = self.setup
        self.obj = self.setup.objects['a']
        self.other = self.setup.objects['b']
        self.verify_calls = []
        self.request_calls = []
        self.notices = []
        self.configured = True
        self.manager = {'_anon': Ring(['synthetic-secret']), '_forms': Ring(['synthetic-secret'])}
        self.gateway = Record(
            is_configured=lambda: self.configured, payment_scope=lambda: 'test-scope',
            valid_authority=gateway.valid_authority,
            request_payment=self.new_attempt, verify_payment=self.verify,
            start_pay_url=lambda value: 'https://gateway.invalid/' + value)
        self.ns = {
            'BrowserView': object, 'ViewPageTemplateFile': lambda p: None,
            'logging': logging, 'logger': logging.getLogger('payment-tests'),
            're': re, 'transaction': transaction, 'DateTime': DateTime,
            'safe_unicode': unicode, 'unicode': unicode, 'escape': escape,
            'ConflictError': ConflictError, 'urlencode': urlencode,
            'PostOnly': PostOnly,
            'CheckAuthenticator': lambda req: CheckAuthenticator(req, manager=self.manager),
            'createToken': lambda: createToken(manager=self.manager),
            'alsoProvides': alsoProvides, 'IDisableCSRFProtection': IDisableCSRFProtection,
            'zarinpal': self.gateway, 'PaymentStateError': state.PaymentStateError,
            'get_ledger': state.get_ledger, 'add_attempt': state.add_attempt,
            'bound_attempt': state.bound_attempt, 'claim_paid': state.claim_paid,
            'api': Record(get_senaite_setup=lambda: self.setup,
                get_portal=lambda: self.setup, get_uid=lambda obj: obj.uid,
                get_url=lambda obj: 'https://lims.invalid', get_id=lambda obj: obj.uid,
                security=Record(as_privileged_user=privileged)),
        }
        load_views(self.ns)
        self.ns['is_price_manager'] = lambda obj: True
        self.ns['_find_by_token'] = lambda token: next((o for o in self.setup.objects.values()
            if o.access_token == token), None)
        transaction.commit()

    def tearDown(self):
        transaction.abort()
        self.connection.close()
        self.db.close()

    def new_attempt(self, *args, **kw):
        self.request_calls.append(args)
        return 'AuthorityA', None

    def verify(self, amount, authority):
        self.verify_calls.append((amount, authority))
        return True, '12345', None

    def request(self, method='POST', csrf=True, **form):
        req = HTTPRequest(StringIO(''), {'REQUEST_METHOD': method,
            'SERVER_NAME': 'test', 'SERVER_PORT': '80'}, HTTPResponse())
        if csrf:
            form['_authenticator'] = createToken(manager=self.manager)
        req.form.update(form)
        return req

    def view(self, name, request, context=None):
        view = self.ns[name]()
        view.context = context or self.setup
        view.request = request
        if name == 'PayCallbackView':
            view._notify_lab = lambda *args: self.notices.append(args)
        if name == 'SetPaymentView':
            view._notify_customer = lambda *args: self.notices.append(args)
        return view

    def bind(self, obj=None, authority='AuthorityA'):
        obj = obj or self.obj
        ledger = state.get_ledger(self.setup, create=True)
        state.add_attempt(ledger, 'test-scope', authority, obj.uid, obj.payment_amount, 'synthetic')
        transaction.commit()
        return ledger

    def callback(self, token=None, authority='AuthorityA', status='OK'):
        req = self.request('GET', False, token=token or self.obj.access_token,
                           Authority=authority, Status=status)
        body = self.view('PayCallbackView', req)()
        return req, body

    def test_wrong_authority_never_calls_gateway(self):
        self.bind()
        req, body = self.callback(authority='AuthorityB')
        self.assertEqual(req.response.getStatus(), 400)
        self.assertEqual(self.verify_calls, [])
        self.assertFalse(self.obj.payment_paid)

    def test_authority_cannot_be_replayed_for_other_request(self):
        self.bind()
        req, body = self.callback(token=self.other.access_token)
        self.assertEqual(req.response.getStatus(), 400)
        self.assertFalse(self.other.payment_paid)
        self.assertEqual(self.verify_calls, [])

    def test_amount_change_blocks_old_attempt(self):
        self.bind()
        self.obj.payment_amount = 20000
        req, body = self.callback()
        self.assertEqual(req.response.getStatus(), 400)
        self.assertEqual(self.verify_calls, [])

    def test_success_is_atomic_and_notification_waits_for_commit(self):
        self.bind()
        req, body = self.callback()
        self.assertTrue(self.obj.payment_paid)
        self.assertEqual(self.obj.payment_ref, '12345')
        self.assertEqual(self.notices, [])
        transaction.commit()
        self.assertEqual(len(self.notices), 1)

    def test_duplicate_callback_does_not_verify_or_notify_twice(self):
        self.bind()
        self.callback()
        transaction.commit()
        self.callback()
        transaction.commit()
        self.assertEqual(len(self.verify_calls), 1)
        self.assertEqual(len(self.notices), 1)

    def test_failed_storage_rolls_back_and_never_claims_success(self):
        ledger = self.bind()
        self.obj._v_fail_reindex = True
        req, body = self.callback()
        self.assertEqual(req.response.getStatus(), 503)
        self.assertFalse(self.obj.payment_paid)
        self.assertEqual(len(ledger['references']), 0)
        self.assertEqual(self.notices, [])

    def test_aborted_transaction_sends_no_notice(self):
        self.bind()
        self.callback()
        transaction.abort()
        self.assertFalse(self.obj.payment_paid)
        self.assertEqual(self.notices, [])

    def test_retry_after_storage_failure_can_finish_same_bound_attempt(self):
        self.bind()
        self.obj._v_fail_reindex = True
        req, body = self.callback()
        self.assertEqual(req.response.getStatus(), 503)
        self.obj._v_fail_reindex = False
        req, body = self.callback()
        self.assertTrue(self.obj.payment_paid)
        transaction.commit()
        self.assertEqual(len(self.notices), 1)

    def test_cancelled_callback_never_verifies_or_marks_paid(self):
        self.bind()
        self.callback(status='NOK')
        self.assertEqual(self.verify_calls, [])
        self.assertFalse(self.obj.payment_paid)

    def test_gateway_scope_change_rejects_old_attempt(self):
        self.bind()
        self.gateway.payment_scope = lambda: 'different-merchant-or-environment'
        req, body = self.callback()
        self.assertEqual(req.response.getStatus(), 400)
        self.assertEqual(self.verify_calls, [])

    def test_reference_cannot_be_claimed_for_two_requests(self):
        self.bind()
        self.bind(self.other, 'AuthorityB')
        self.callback()
        transaction.commit()
        req, body = self.callback(token=self.other.access_token, authority='AuthorityB')
        self.assertEqual(req.response.getStatus(), 503)
        self.assertFalse(self.other.payment_paid)

    def test_two_connections_cannot_claim_same_reference(self):
        self.bind()
        self.bind(self.other, 'AuthorityB')
        t1, t2 = TransactionManager(), TransactionManager()
        c1, c2 = self.db.open(transaction_manager=t1), self.db.open(transaction_manager=t2)
        try:
            a, b = c1.root()['setup'], c2.root()['setup']
            state.claim_paid(state.get_ledger(a), 'test-scope', 'AuthorityA', 'a', 10000,
                             '777', a.objects['a'], 'synthetic')
            state.claim_paid(state.get_ledger(b), 'test-scope', 'AuthorityB', 'b', 10000,
                             '777', b.objects['b'], 'synthetic')
            t1.commit()
            with self.assertRaises(ConflictError):
                t2.commit()
        finally:
            t1.abort(); t2.abort(); c1.close(); c2.close()

    def test_get_payment_link_does_not_create_gateway_attempt(self):
        req = self.request('GET', False, token=self.obj.access_token)
        body = self.view('PayView', req)()
        self.assertIn('_authenticator', body)
        self.assertEqual(self.request_calls, [])

    def test_payment_post_requires_csrf(self):
        req = self.request('POST', False, token=self.obj.access_token)
        with self.assertRaises(Forbidden):
            self.view('PayView', req)()
        self.assertEqual(self.request_calls, [])

    def test_payment_post_freezes_attempt_before_redirect(self):
        req = self.request(token=self.obj.access_token)
        self.view('PayView', req)()
        attempt = state.bound_attempt(state.get_ledger(self.setup), 'test-scope', 'AuthorityA', 'a', 10000)
        self.assertEqual(attempt['currency'], 'IRR')
        self.assertEqual(req.response.getHeader('Location'), 'https://gateway.invalid/AuthorityA')

    def test_unconfigured_gateway_never_calls_api_or_schedules_email(self):
        self.configured = False
        self.view('PayView', self.request(token=self.obj.access_token))()
        self.obj.contact_email = 'synthetic@example.invalid'
        req = self.request(payment_amount='20000')
        self.view('SetPaymentView', req, self.obj)()
        transaction.commit()
        self.assertEqual(self.request_calls, [])
        self.assertEqual(self.notices, [])

    def test_paid_quote_cannot_be_reset(self):
        self.obj.payment_paid = True
        self.obj.payment_ref = '12345'
        req = self.request(payment_amount='20000')
        self.view('SetPaymentView', req, self.obj)()
        self.assertEqual(req.response.getStatus(), 409)
        self.assertTrue(self.obj.payment_paid)
        self.assertEqual(self.obj.payment_ref, '12345')

    def test_quote_requires_csrf_and_rejects_negative_amount(self):
        with self.assertRaises(Forbidden):
            self.view('SetPaymentView', self.request(csrf=False, payment_amount='20000'), self.obj)()
        req = self.request(payment_amount='-20000')
        self.view('SetPaymentView', req, self.obj)()
        self.assertEqual(req.response.getStatus(), 400)
        self.assertEqual(self.obj.payment_amount, 10000)

    def test_price_parser_accepts_persian_and_rejects_malformed_values(self):
        self.assertEqual(self.ns['_digits'](u'۱۲٬۳۴۵'), '12345')
        for value in ('-1000', '1.5', '10e3', '12,34', 'amount1000'):
            with self.assertRaises(ValueError):
                self.ns['_digits'](value)

class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.original_post, self.original_merchant = gateway._post, gateway.merchant_id
        gateway.merchant_id = lambda: 'synthetic-merchant'
    def tearDown(self):
        gateway._post, gateway.merchant_id = self.original_post, self.original_merchant
    def test_verified_and_already_verified_require_positive_reference(self):
        for code in (100, 101):
            gateway._post = lambda *args: {'data': {'code': code, 'ref_id': 12345}}
            self.assertEqual(gateway.verify_payment(10000, 'AuthorityA'), (True, '12345', None))
            for ref in (None, '', 0, True, '<script>', '12345\n'):
                gateway._post = lambda *args: {'data': {'code': code, 'ref_id': ref}}
                self.assertFalse(gateway.verify_payment(10000, 'AuthorityA')[0])
        self.assertFalse(gateway.valid_authority('AuthorityA\n'))
    def test_gateway_request_uses_explicit_rial_amount(self):
        captured = []
        def post(path, payload):
            captured.append(payload)
            return {'data': {'code': 100, 'authority': 'AuthorityA'}}
        gateway._post = post
        self.assertEqual(gateway.request_payment(10000, 'https://callback.invalid')[0], 'AuthorityA')
        self.assertEqual(captured[0]['amount'], 10000)
        self.assertEqual(captured[0]['currency'], 'IRR')
    def test_malformed_gateway_response_is_not_success(self):
        for response in (None, [], {'data': []}, {'data': {'code': -1}}):
            gateway._post = lambda *args: response
            self.assertFalse(gateway.verify_payment(10000, 'AuthorityA')[0])

if __name__ == '__main__':
    unittest.main()
