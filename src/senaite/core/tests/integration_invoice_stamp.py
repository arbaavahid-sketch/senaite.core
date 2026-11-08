# -*- coding: utf-8 -*-
from __future__ import print_function
import os,json,hashlib,sys,base64
import transaction
from six import BytesIO
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from plone.protect.authenticator import createToken
from bika.lims import api
from bika.lims.browser.analysisrequest import billing,template_settings as config,stamp,editor
from bika.lims.browser.analysisrequest.invoice import InvoiceView
assert os.environ.get('TPPC_STAMP_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
newSecurityManager(request,SimpleUser('stamp-stage','',['Manager'],[]).__of__(site.acl_users))
def form(**values):
    request.form.clear();request.form.update(values);request.form['_authenticator']=createToken();request.set('REQUEST_METHOD','POST');request.response.setStatus(200)
try:
    assert billing.money(150000000)=='150,000,000' and billing.money(0)=='0'
    assert billing.money('12.50')=='12.50' and billing.money('12.01')=='12.01'
    fixture=config.logo_upload(BytesIO(base64.b64decode(billing.logo_data().split(',',1)[1])))
    config.IAnnotations(api.get_senaite_setup())[config.KEY]={'stamp':fixture,'html':config.FORMAL_HTML,'color':'#174c69'}
    sample=next(api.get_object(b) for b in api.search({'portal_type':'AnalysisRequest'}) if api.get_object(b).getInvoice() is None)
    # Use an unlinked sample so original zero/positive tariff remains untouched.
    for obj in api.get_senaite_setup().sampleintake.objectValues():
        if getattr(obj,'created_sample_uid','')==api.get_uid(sample):obj.created_sample_uid=''
    data=billing.current_data(sample)
    assert u'alt="مهر شرکت"' not in billing.render(data,'TEST','')
    assert u'نمایش مهر شرکت' in stamp.controls(data) and 'checked="checked"' not in stamp.controls(data)
    form(billing_version=editor.version(sample),billing_reason=u'نسخهٔ بدون مهر')
    view=InvoiceView(sample,request);assert editor.save(view)
    invoice=sample.getInvoice();unstamped=invoice.getInvoicePDF().data
    assert not invoice.billing_snapshot['stamp_enabled']
    form(billing_version=editor.version(sample),billing_reason=u'آزمون مهر اختیاری',billing_stamp='1')
    assert editor.save(view)
    frozen=dict(invoice.billing_snapshot)
    assert frozen['stamp_enabled'] and frozen['stamp_file']==fixture
    html=billing.render(frozen,'TEST','')
    assert html.count(u'alt="مهر شرکت"')==1
    assert invoice.billing_history[-1]['pdf']==unstamped
    # An upload replacement must not change an issued invoice's chosen image.
    config.IAnnotations(api.get_senaite_setup())[config.KEY]={'html':config.FORMAL_HTML}
    assert u'alt="مهر شرکت"' in billing.render(frozen,'TEST','')
    form(billing_version=editor.version(sample),billing_reason=u'حذف مهر از نسخهٔ جدید')
    assert editor.save(view) and not invoice.billing_snapshot['stamp_enabled']
    assert invoice.billing_history[-1]['snapshot']['stamp_enabled']
    assert u'alt="مهر شرکت"' not in billing.render(invoice.billing_snapshot,'TEST','')
    # Explicit HTML placeholder renders exactly once.
    with_token=dict(frozen,template_settings={'html':config.FORMAL_HTML.replace(u'مهر و امضای فروشنده',u'مهر و امضای فروشنده{{stamp}}')})
    assert billing.render(with_token,'TEST','').count(u'alt="مهر شرکت"')==1
    assert 'billing_stamp' in InvoiceView(sample,request).content()
    preview=dict(invoice.billing_snapshot,total='150000000',source='request',currency='IRR',items=[(u'آزمون نمونه','150000000')])
    pdf=billing.pdf_bytes(preview,'TEST','2026-11-08');assert pdf.startswith(b'%PDF-')
    open('/out/preview.pdf','wb').write(pdf)
    print('INTEGER_DISPLAY_FRACTIONS_PRESERVED_OPT_IN_UPLOAD_STAMP_ADD_REMOVE_ARCHIVE_OK');sys.stdout.flush()
finally:transaction.abort()
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((name,hashlib.sha256(open('/out/'+name,'rb').read()).hexdigest()) for name in json.load(open('/out/files.json')))}))
print('ALL_STAMP_TESTS_PASSED_NO_COMMIT');sys.stdout.flush()
