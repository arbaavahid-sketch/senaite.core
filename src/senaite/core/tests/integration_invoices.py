# -*- coding: utf-8 -*-
from __future__ import print_function
import os, json, hashlib, unittest, imp
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from plone.protect.authenticator import createToken
from bika.lims import api
from bika.lims.browser.analysisrequest import billing, editor
from bika.lims.browser.analysisrequest.invoice import InvoiceView, InvoicePrintView
from senaite.core.browser.payment import views, presentation
assert os.environ.get('TPPC_BILLING_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app); site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
def login(role): newSecurityManager(request,SimpleUser('billing-test','',[role],[]).__of__(site.acl_users))
def form(**values):
    request.form.clear();request.form.update(values);request.form['_authenticator']=createToken();request.set('REQUEST_METHOD','POST');request.response.setStatus(200)
login('Manager')
try:
    samples=[api.get_object(b) for b in api.search({'portal_type':'AnalysisRequest'})]
    sample=next(s for s in samples if s.getInvoice() is None)
    folder=api.get_senaite_setup().sampleintake
    source=next(o for o in folder.objectValues() if api.get_portal_type(o)=='SampleRequest')
    uid=api.get_uid(sample)
    for o in folder.objectValues():
        if getattr(o,'created_sample_uid','')==uid:o.created_sample_uid=''
    source.created_sample_uid=uid;source.payment_amount=150000000;source.payment_paid=False;source.payment_authority='OLD';source.payment_requested_amount=150000000
    source.contact_email='' # No notification is sent from these tests.
    view=InvoiceView(sample,request)
    form(billing_save='1',billing_version=editor.version(sample),billing_amount='150000000',billing_description=u'خدمات آزمون نمونه',billing_note=u'یادداشت آزمایشی',billing_reason='')
    assert editor.save(view)
    invoice=sample.getInvoice();first=invoice.getInvoicePDF().data
    assert first.startswith(b'%PDF-') and invoice.billing_snapshot['total']=='150000000'
    token=editor.version(sample)
    form(billing_save='1',billing_version=token,billing_amount='160000000',billing_description=u'شرح اصلاح‌شده',billing_note=u'توضیح اصلاح',billing_reason=u'اصلاح مبلغ توافق‌شده')
    assert editor.save(view)
    assert source.payment_amount==160000000 and source.payment_authority=='' and source.payment_requested_amount==0
    assert invoice.billing_snapshot['total']=='160000000' and invoice.billing_revision==2
    assert invoice.billing_history[0]['pdf']==first
    assert invoice.billing_history[0]['payment_amount']==150000000
    request.form.clear();request.set('revision','0')
    assert InvoicePrintView(sample,request)()==first
    request.other.pop('revision',None)
    print('ISSUE_REVISION_SHARED_AMOUNT_ARCHIVED_PDF_OK');import sys;sys.stdout.flush()
    form(billing_version=token,billing_amount='170000000',billing_reason=u'تعارض')
    assert not editor.save(view) and request.response.getStatus()==409
    source.payment_paid=True
    form(billing_version=editor.version(sample),billing_amount='170000000',billing_reason=u'تغییر پرداخت‌شده')
    assert not editor.save(view) and source.payment_amount==160000000
    source.payment_paid=False
    old_renderer=billing.pdf_bytes
    def failure(*args):raise RuntimeError('synthetic PDF failure')
    billing.pdf_bytes=failure
    form(billing_version=editor.version(sample),billing_amount='180000000',billing_reason=u'آزمون برگشت')
    try:editor.save(view);raise AssertionError('failure accepted')
    except RuntimeError:pass
    finally:billing.pdf_bytes=old_renderer
    assert source.payment_amount==160000000 and len(invoice.billing_history)==1
    # Legacy invoices remain editable and their original bytes are archived.
    del invoice.billing_snapshot
    legacy=invoice.getInvoicePDF().data
    form(billing_version=editor.version(sample),billing_amount='160000000',billing_reason=u'اصلاح فاکتور قدیمی')
    assert editor.save(view) and invoice.billing_history[-1]['pdf']==legacy
    print('CONFLICT_PAID_LOCK_ROLLBACK_LEGACY_REPAIR_OK');sys.stdout.flush()
    source.payment_amount=170000000
    assert u'تفاوت دارد' in editor.page(view)
    form(payment_amount='160000000')
    views.SetPaymentView(source,request)()
    assert request.response.getStatus()==303 and request.response.getHeader('Location').endswith('/@@payments?saved=1')
    request.set('REQUEST_METHOD','GET');request.form.clear()
    html=views.SetPaymentView(source,request)()
    assert u'بازگشت به پرداخت'.encode('utf-8') in html
    assert '/invoice' in html
    request.other['saved']='1'
    dash=views.PaymentsListView(site,request).content()
    assert 'payment-filter' in dash and u'مبلغ ذخیره شد' in dash
    # Output stage-only samples for visual verification.
    data=billing.data_for(sample)
    open('/out/invoice.pdf','wb').write(billing.pdf_bytes(data,api.get_id(invoice),'2026-11-07'))
    open('/out/invoice.html','wb').write((u'<html lang="fa" dir="rtl"><meta charset="utf-8">'+editor.page(view)+u'</html>').encode('utf-8'))
    open('/out/payment.html','wb').write(html)
    open('/out/payments.html','wb').write((u'<html lang="fa" dir="rtl"><meta charset="utf-8">'+dash+u'</html>').encode('utf-8'))
    print('PAYMENT_PRG_LINKS_FILTERS_MISMATCH_UI_OK');sys.stdout.flush()
    form(billing_version=editor.version(sample),billing_amount='160000000',billing_reason=u'بدون CSRF');request.form.pop('_authenticator')
    try:editor.save(view);raise AssertionError('CSRF missing accepted')
    except Exception as error:assert error.__class__.__name__ in ('Forbidden','Unauthorized'),repr(error)
    login('Anonymous')
    try:InvoiceView(sample,request)();raise AssertionError('Anonymous access')
    except Exception as error:assert error.__class__.__name__=='Unauthorized',repr(error)
finally:transaction.abort()
print('BILLING_INTEGRATION_PASSED_NO_COMMIT');sys.stdout.flush()
# Existing payment security regressions use synthetic gateways / their own ZODB.
os.environ['PAYMENT_SOURCE']='/home/senaite/senaitelims/src/senaite.core/src/senaite/core/browser/payment'
module=imp.load_source('payment_security_regression','/out/test_payment_security.py')
suite=unittest.defaultTestLoader.loadTestsFromModule(module)
result=unittest.TextTestRunner(verbosity=1).run(suite)
assert result.wasSuccessful()
open('/out/tests-passed.json','w').write(json.dumps({'payment_tests':result.testsRun,'sha256':dict((name,hashlib.sha256(open('/out/'+name,'rb').read()).hexdigest()) for name in json.load(open('/out/files.json')))}))
print('ALL_BILLING_AND_PAYMENT_TESTS_PASSED');sys.stdout.flush()
