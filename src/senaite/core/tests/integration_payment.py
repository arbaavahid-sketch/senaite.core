# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from plone.protect.authenticator import createToken
from Products.CMFCore.indexing import processQueue
from bika.lims import api
from senaite.core.browser.payment import views, state

if (os.environ.get('TPPC_PAYMENT_STAGE') != '1'
        or not os.path.isfile('/data/.csrf-stage-only')):
    raise SystemExit('Disposable stage required')

app = makerequest(app)
site = app['senaite']
setSite(site)
request = app.REQUEST
setRequest(request)
def login(role):
    user = SimpleUser('payment-test-' + role, '', [role], [])
    newSecurityManager(request, user.__of__(site.acl_users))

def form(method='POST', **values):
    request.form.clear()
    request.response.setStatus(200)
    request.set('REQUEST_METHOD', method)
    request.form.update(values)

original_gateway = views.zarinpal
notices = []
verify_calls = []
class FakeGateway(object):
    configured = False
    def is_configured(self): return self.configured
    def payment_scope(self): return 'isolated-payment-test'
    def valid_authority(self, value): return original_gateway.valid_authority(value)
    def verify_payment(self, amount, authority):
        verify_calls.append((amount, authority))
        return True, '999888777', None
    def request_payment(self, *args, **kw):
        raise AssertionError('No external gateway request allowed in this test')

try:
    login('Manager')
    setup = api.get_senaite_setup()
    a = api.create(setup.sampleintake, 'SampleRequest', title=u'Synthetic payment A')
    b = api.create(setup.sampleintake, 'SampleRequest', title=u'Synthetic payment B')
    transaction.savepoint(optimistic=True)
    processQueue()
    a.payment_amount = b.payment_amount = 10000
    a.payment_paid = b.payment_paid = False
    fake = FakeGateway()
    views.zarinpal = fake
    login('LabClerk')
    form(payment_amount='20000', _authenticator=createToken())
    views.SetPaymentView(a, request)()
    assert request.response.getStatus() == 403 and a.payment_amount == 10000
    print('PRICE_ROLE_RESTRICTION_OK')
    login('Manager')
    form('GET')
    html = views.SetPaymentView(a, request)()
    assert 'name="_authenticator"' in html
    print('PRICE_FORM_TOKEN_OK')
    form('GET', token=a.access_token)
    body = views.PayView(site, request)()
    assert u'درگاه پیکربندی نشده'.encode('utf-8') in body
    print('UNCONFIGURED_GATEWAY_STAYS_DISABLED')
    fake.configured = True
    ledger = state.get_ledger(setup, create=True)
    state.add_attempt(ledger, fake.payment_scope(), 'SyntheticAuthority', api.get_uid(a), 10000, 'synthetic')
    form('GET', token=b.access_token, Authority='SyntheticAuthority', Status='OK')
    views.PayCallbackView(site, request)()
    assert request.response.getStatus() == 400 and not b.payment_paid
    assert not verify_calls
    form('GET', token=a.access_token, Authority='SyntheticAuthority', Status='OK')
    callback = views.PayCallbackView(site, request)
    callback._notify_lab = lambda *args: notices.append(args)
    callback()
    assert a.payment_paid and a.payment_ref == '999888777'
    callback()
    assert len(verify_calls) == 1 and not notices
    print('BOUND_CALLBACK_AND_IDEMPOTENCE_OK')
finally:
    views.zarinpal = original_gateway
    transaction.abort()
    assert not notices
    print('SYNTHETIC_PAYMENT_TRANSACTION_ABORTED_NO_EMAIL')
