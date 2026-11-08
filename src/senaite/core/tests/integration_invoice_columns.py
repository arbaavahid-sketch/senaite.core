# -*- coding: utf-8 -*-
from __future__ import print_function
import os,sys,imp,json,hashlib
import transaction
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from bika.lims import api
from bika.lims.browser.analysisrequest import billing,template_settings
assert os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);setRequest(app.REQUEST)
newSecurityManager(app.REQUEST,SimpleUser('invoice-column-test','',['Manager'],[]).__of__(site.acl_users))
try:
    sample=next(s for s in site.clients['client-8'].objectValues('AnalysisRequest') if s.getInvoice() is None)
    data=billing.current_data(sample)
    data.update(items=[(u'شرح آزمون اول SERVICE_A','180000001'),(u'شرح آزمون دوم SERVICE_B','6000000')],
        total='186000001',subtotal='186000001',tax='0',discount='0')
    data['template_settings']=dict(template_settings.read(),html=template_settings.FORMAL_HTML)
    formal=billing.pdf_bytes(data,'QA-1','2026/11/08');open('/out/formal.pdf','wb').write(formal)
    default=dict(data);default['template_settings']={}
    open('/out/default.pdf','wb').write(billing.pdf_bytes(default,'QA-2','2026/11/08'))
    invoice=sample.createInvoice(None);invoice.billing_snapshot=data;invoice.billing_revision=1;invoice.setInvoicePDF(formal)
    old=dict(data);old_date=invoice.getInvoiceDate();old_paid=[getattr(o,'payment_amount',0) for o in api.get_senaite_setup().sampleintake.objectValues()]
    helper=imp.load_source('repair_pdf','/out/repair_pdf.py')
    helper.repair(invoice,hashlib.sha256(formal).hexdigest())
    assert invoice.billing_history[-1]['pdf']==formal and invoice.billing_revision==2
    assert invoice.billing_snapshot['items']==old['items'] and invoice.billing_snapshot['total']==old['total']
    assert invoice.getInvoiceDate()==old_date
    assert old_paid==[getattr(o,'payment_amount',0) for o in api.get_senaite_setup().sampleintake.objectValues()]
    try:helper.repair(invoice,'stale');raise AssertionError('Stale repair accepted')
    except AssertionError as error:assert str(error)=='Invoice PDF changed since inspection'
    print('FROZEN_PRICES_ITEMS_INVOICE_DATE_PAYMENTS_ARCHIVE_AND_STALE_GUARD_OK')
finally:transaction.abort()
files=json.load(open('/out/files.json'))
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((n,hashlib.sha256(open('/out/'+n,'rb').read()).hexdigest()) for n in files)}))
print('COLUMN_PDF_RENDER_AND_FROZEN_REPAIR_TESTS_PASSED');sys.stdout.flush()
