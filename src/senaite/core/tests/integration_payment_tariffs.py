# -*- coding: utf-8 -*-
from __future__ import print_function
import os,json,hashlib,sys,unittest,imp
from decimal import Decimal
import transaction
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from plone.protect.authenticator import createToken
from bika.lims import api
from bika.lims.interfaces import IAnalysis
from senaite.core.browser.payment import views,tariff
assert os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
def login(role):newSecurityManager(request,SimpleUser('tariff-stage','',[role],[]).__of__(site.acl_users))
def form(method='POST',**fields):
    request.form.clear();request.form.update(fields);request.set('REQUEST_METHOD',method);request.response.setStatus(200)
    request.form['_authenticator']=createToken()
original_gateway=views.zarinpal
class NoGateway(object):
    def is_configured(self):return False
try:
    login('Manager');setup=api.get_senaite_setup()
    from bika.lims.browser.analysisrequest import billing
    pairs=[]
    for obj in setup.sampleintake.objectValues():
        uid=getattr(obj,'created_sample_uid','')
        sample=api.get_object(uid,default=None) if uid else None
        if sample is not None and sample.getBillableItems() and all(IAnalysis.providedBy(a) for a in sample.getBillableItems()) and api.get_review_status(sample) not in ('cancelled','invalid','rejected'):
            pairs.append((obj,sample))
    obj,sample=pairs[0];items=list(sample.getBillableItems())
    sample.getClient().setBulkDiscount(False);sample.getClient().setMemberDiscountApplies(False)
    for item in items:item.setPrice('0');item.setVAT('10');item.getAnalysisService().setPrice('1000000')
    obj.payment_amount=0;obj.payment_paid=False;obj.payment_authority='old-pending';obj.payment_requested_amount=1234
    quote=tariff.preview(obj);expected=1100000*len(items)
    assert quote['amount']==expected,quote
    old_state=(obj.payment_amount,obj.payment_authority,obj.payment_requested_amount)
    form('GET');body=views.SetPaymentView(obj,request)()
    assert u'ثبت مبلغ از تعرفه آزمون‌ها'.encode('utf-8') in body
    assert old_state==(obj.payment_amount,obj.payment_authority,obj.payment_requested_amount)
    dashboard=views.PaymentsListView(site,request).content()
    assert u'هزینهٔ آزمون‌ها'.encode('utf-8') in dashboard.encode('utf-8')
    assert old_state==(obj.payment_amount,obj.payment_authority,obj.payment_requested_amount)
    print('TARIFF_PREVIEW_DETAILS_DASHBOARD_NO_WRITES_OK');sys.stdout.flush()
    views.zarinpal=NoGateway()
    form(payment_action='use_tariff',tariff_version=quote['version'])
    views.SetPaymentView(obj,request)()
    assert request.response.getStatus()==303 and obj.payment_amount==expected
    assert not obj.payment_authority and obj.payment_requested_amount==0
    # A changed quote is rejected before an existing amount or authority changes.
    quote=tariff.preview(obj);items[0].setPrice('2000000')
    form(payment_action='use_tariff',tariff_version=quote['version'])
    views.SetPaymentView(obj,request)()
    assert request.response.getStatus()==409 and obj.payment_amount==expected
    obj.payment_paid=True;quote=tariff.preview(obj)
    form(payment_action='use_tariff',tariff_version=quote['version'])
    views.SetPaymentView(obj,request)()
    assert request.response.getStatus()==409 and obj.payment_amount==expected
    print('EXPLICIT_SAVE_REDIRECT_AUTHORITY_INVALIDATION_STALE_AND_PAID_LOCK_OK');sys.stdout.flush()
    obj.payment_paid=False
    form(payment_action='use_tariff',tariff_version=tariff.preview(obj)['version']);request.form.pop('_authenticator')
    try:views.SetPaymentView(obj,request)();raise AssertionError('Missing CSRF accepted')
    except Exception as error:assert error.__class__.__name__=='Forbidden',repr(error)
    login('LabClerk');form('GET')
    views.SetPaymentView(obj,request)();assert request.response.getStatus()==403
    try:tariff.preview(obj);raise AssertionError('Clerk read tariff')
    except Exception as error:assert error.__class__.__name__=='Unauthorized',repr(error)
    login('Manager')
    # Unconverted requests use selected service UIDs, never text matching.
    unconverted=api.create(setup.sampleintake,'SampleRequest',title='Tariff stage only')
    unconverted.requested_service_uids=[api.get_uid(items[0].getAnalysisService())]
    items[0].getAnalysisService().setPrice('3000000');items[0].getAnalysisService().setVAT('10')
    assert tariff.preview(unconverted)['amount']==3300000
    unconverted.requested_service_uids=[];missing=tariff.preview(unconverted)
    assert missing['amount'] is None and u'انتخاب نشده' in missing['error']
    form('GET');assert u'انتخاب نشده'.encode('utf-8') in views.SetPaymentView(unconverted,request)()
    unconverted.requested_service_uids=['missing-service'];assert tariff.preview(unconverted)['amount'] is None
    unconverted.requested_service_uids=[api.get_uid(items[0].getAnalysisService())]
    items[0].getAnalysisService().setPrice('0');assert tariff.preview(unconverted)['amount'] is None
    print('CSRF_ROLE_SELECTED_SERVICES_MISSING_AND_ZERO_PRICE_OK');sys.stdout.flush()
finally:
    views.zarinpal=original_gateway;transaction.abort()
# Existing payment-state/gateway security tests must still pass.
os.environ['PAYMENT_SOURCE']='/home/senaite/senaitelims/src/senaite.core/src/senaite/core/browser/payment'
regression=imp.load_source('tariff_security_regression','/out/test_payment_security.py')
result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(regression))
assert result.wasSuccessful()
files=json.load(open('/out/files.json'))
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((n,hashlib.sha256(open('/out/'+n,'rb').read()).hexdigest()) for n in files)}))
print('PAYMENT_TARIFF_AND_SECURITY_TESTS_PASSED_NO_PRODUCTION_WRITES');sys.stdout.flush()
