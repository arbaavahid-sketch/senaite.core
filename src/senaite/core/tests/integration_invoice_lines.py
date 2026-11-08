# -*- coding: utf-8 -*-
from __future__ import print_function
import os,json,hashlib,sys
from decimal import Decimal
import transaction
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from plone.protect.authenticator import createToken
from bika.lims import api
from bika.lims.browser.analysisrequest import billing,aggregate,editor,template_settings as config
from bika.lims.browser.analysisrequest.invoice import InvoiceView,InvoicePrintView,ClientInvoicesView
assert os.environ.get('TPPC_AGGREGATE_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
def login(role):newSecurityManager(request,SimpleUser('aggregate-stage','',[role],[]).__of__(site.acl_users))
def form(**values):
    request.form.clear();request.form.update(values);request.form['_authenticator']=createToken();request.set('REQUEST_METHOD','POST');request.response.setStatus(200)
def expect_error(callback):
    try:callback();raise AssertionError('Expected rejection')
    except ValueError:pass
login('Manager')
original_current=billing.current_data
try:
    config.IAnnotations(api.get_senaite_setup())[config.KEY]=dict(config.read(),html=config.FORMAL_HTML)
    def payment_state():
        return [(api.get_uid(o),getattr(o,'payment_amount',0),getattr(o,'payment_paid',False),getattr(o,'payment_authority','')) for o in api.get_senaite_setup().sampleintake.objectValues()]
    original_payments=payment_state()
    import imp
    correct_price_offline=imp.load_source('correct_price_offline','/out/correct_price_offline.py')
    target=site.clients['client-8']['ST36-26-0029']
    target.getClient().setBulkDiscount(False)
    a=api.get_object('b943e0ed752f43a5873de498c9ea31fd')
    a.setPrice('50');a.getAnalysisService().setPrice('150000000')
    old_result=a.getResult();old_state=api.get_review_status(a)
    fixed=correct_price_offline.correct(target)
    assert fixed['changed'] and Decimal(a.getPrice())==150000000
    assert a.getResult()==old_result and api.get_review_status(a)==old_state
    assert not correct_price_offline.correct(target)['changed']
    transaction.abort()
    print('APPROVED_SINGLE_PRICE_CORRECTION_PRESERVES_RESULT_AND_STATE_OK');sys.stdout.flush()
    candidates=[]
    for client in site.clients.objectValues('Client'):
        eligible=[s for s in aggregate.samples(client) if not aggregate.exclusion(s)]
        if len(eligible)>=4:candidates.append((client,eligible))
    client,eligible=max(candidates,key=lambda pair:len(pair[1]))
    objects=eligible[:2];uids=[api.get_uid(s) for s in objects]
    def fixture_data(sample):
        data=original_current(sample)
        amount='150000000' if api.get_uid(sample)==uids[0] else '200000000'
        data.update(total=amount,subtotal=amount,tax='0',discount='0',source='services',currency='IRR',items=[(u'خدمات آزمون',amount)])
        return data
    billing.current_data=fixture_data
    chosen=aggregate.selected(client,uids)
    # Two tests in one sample must remain separate and totals must reconcile.
    original_fixture=billing.current_data
    def itemized(sample):
        row=fixture_data(sample)
        row.update(items=[(u'دانسیته','6000000'),(u'تقطیر','68000000')],subtotal='74000000',total='74000000',tax='0',discount='0')
        return row
    billing.current_data=itemized
    split=aggregate.combine(chosen)
    assert len(split['items'])==4 and Decimal(split['total'])==148000000
    assert [Decimal(price) for title,price in split['items']]==[6000000,68000000,6000000,68000000]
    row=itemized(chosen[0]);row.update(tax='7400000',discount='1000000',total='80400000')
    lines=aggregate.sample_rows(chosen[0],row)
    assert len(lines)==4 and sum(Decimal(p) for t,p in lines)==80400000
    row.update(items=[('fraction','0.005'),('fraction2','0.005')],tax='0',discount='0',total='0.01')
    assert sum(Decimal(p) for t,p in aggregate.sample_rows(chosen[0],row))==Decimal('0.01')
    # Agreed totals remain fixed: show tariffs and an explicit adjustment.
    raw_prices=billing.service_prices
    billing.service_prices=lambda obj:dict(items=[('A','6000000'),('B','68000000')],tax='0',discount='0')
    try:
        row.update(source='request',currency=api.get_senaite_setup().getCurrency(),total='70000000')
        lines=aggregate.sample_rows(chosen[0],row)
        assert len(lines)==3 and Decimal(lines[-1][1])==-4000000
        assert sum(Decimal(p) for t,p in lines)==70000000
    finally:billing.service_prices=raw_prices
    billing.current_data=original_fixture
    print('SEPARATE_ANALYSIS_ROWS_TAX_DISCOUNT_ROUNDING_AND_AGREED_TOTAL_OK');sys.stdout.flush()
    data=aggregate.combine(chosen)
    assert data['total']=='350000000.00' and len(data['items'])==2
    assert sum(Decimal(p) for t,p in data['items'])==Decimal(data['total'])
    for obj in chosen:assert api.get_id(obj) in u' '.join(t for t,p in data['items'])
    expect_error(lambda:aggregate.selected(client,uids+uids))
    foreign=next(s for b in api.search({'portal_type':'AnalysisRequest'}) for s in [api.get_object(b)] if api.get_uid(s.getClient())!=api.get_uid(client))
    expect_error(lambda:aggregate.selected(client,[uids[0],api.get_uid(foreign)]))
    form(sample_uids=uids,aggregate_action='preview',note=u'آزمون فاکتور تجمیعی')
    view=ClientInvoicesView(client,request);assert not aggregate.dispatch(view) and view.preview
    assert all(obj.getInvoice() is None for obj in chosen)
    assert 'aggregate_version' in aggregate.page(view)
    form(sample_uids=uids,aggregate_action='issue',aggregate_version=aggregate.version(chosen),note=u'آزمون فاکتور تجمیعی')
    assert aggregate.dispatch(view) and request.response.getStatus()==303
    invoice=chosen[0].getInvoice();number=api.get_id(invoice)
    assert all(api.get_uid(obj.getInvoice())==api.get_uid(invoice) for obj in chosen)
    assert tuple(invoice.aggregate_sample_uids)==tuple(api.get_uid(o) for o in chosen)
    assert invoice.billing_snapshot['total']=='350000000.00'
    first_pdf=invoice.getInvoicePDF().data;assert first_pdf.startswith(b'%PDF-')
    expect_error(lambda:aggregate.selected(client,uids))
    assert InvoicePrintView(chosen[1],request)()==first_pdf
    form(billing_save='1')
    assert not editor.save(InvoiceView(chosen[1],request)) and request.response.getStatus()==409
    request.set('REQUEST_METHOD','GET');request.form.clear()
    InvoiceView(chosen[0],request)()
    assert request.response.getHeader('Location').endswith('/@@invoices?invoice='+number)
    print('SELECT_PREVIEW_TOTAL_ISSUE_SHARED_LINKS_DUPLICATE_AND_INDIVIDUAL_EDIT_GUARD_OK');sys.stdout.flush()
    # Group revisions are atomic, versioned and keep prior PDFs.
    digest=aggregate.version(chosen,invoice)
    form(aggregate_version=digest,reason=u'توضیح اصلاح گروهی',note=u'اصلاحیه')
    aggregate.issue(client,chosen,request.form,invoice)
    assert invoice.billing_history[-1]['pdf']==first_pdf and invoice.billing_revision==2
    assert payment_state()==original_payments
    expect_error(lambda:aggregate.issue(client,[chosen[0],eligible[2]],request.form,invoice))
    expect_error(lambda:aggregate.issue(client,chosen,dict(aggregate_version=digest,reason='stale'),invoice))
    # Mixed currencies are rejected before linking anything.
    spare=eligible[2:4]
    def mixed(obj):
        row=fixture_data(obj)
        if api.get_uid(obj)==api.get_uid(spare[1]):row['currency']='USD'
        return row
    billing.current_data=mixed
    expect_error(lambda:aggregate.combine(spare))
    billing.current_data=fixture_data
    old_renderer=billing.pdf_bytes
    def failed(*args):raise RuntimeError('synthetic PDF failure')
    billing.pdf_bytes=failed
    form(aggregate_version=aggregate.version(spare),note='')
    try:aggregate.issue(client,spare,request.form);raise AssertionError('Render failure accepted')
    except RuntimeError:pass
    finally:billing.pdf_bytes=old_renderer
    assert all(obj.getInvoice() is None for obj in spare)
    # GET and missing CSRF cannot issue a new aggregate.
    request.set('REQUEST_METHOD','GET');request.form.clear()
    assert not aggregate.dispatch(ClientInvoicesView(client,request))
    form(sample_uids=[api.get_uid(s) for s in spare],aggregate_action='preview');request.form.pop('_authenticator')
    try:aggregate.dispatch(ClientInvoicesView(client,request));raise AssertionError('CSRF missing accepted')
    except Exception as error:assert error.__class__.__name__ in ('Forbidden','Unauthorized'),repr(error)
    print('REVISION_ARCHIVE_STALE_CURRENCY_ROLLBACK_AND_CSRF_OK');sys.stdout.flush()
    # Render the group detail and client selection UI in the same runtime.
    request.set('REQUEST_METHOD','GET');request.form.clear();request.set('invoice',number)
    view=ClientInvoicesView(client,request);assert not aggregate.dispatch(view)
    detail=aggregate.page(view)
    assert number in detail and u'دریافت PDF تجمیعی' in detail
    request.other.pop('invoice',None)
    view=ClientInvoicesView(client,request);aggregate.dispatch(view)
    listing=aggregate.page(view)
    assert 'aggregate-select-all' in listing and number in listing
    open('/out/preview.pdf','wb').write(invoice.getInvoicePDF().data)
    login('LabClerk')
    form(aggregate_version='unauthorized-test')
    try:aggregate.issue(client,spare,request.form);raise AssertionError('Clerk issued invoice')
    except Exception as error:assert error.__class__.__name__=='Unauthorized',repr(error)
    login('Anonymous')
    try:ClientInvoicesView(client,request)();raise AssertionError('Anonymous view allowed')
    except Exception as error:assert error.__class__.__name__=='Unauthorized',repr(error)
    print('CLIENT_DETAIL_LIST_ROLE_AND_ANONYMOUS_ACCESS_OK');sys.stdout.flush()
finally:
    billing.current_data=original_current;transaction.abort()
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((name,hashlib.sha256(open('/out/'+name,'rb').read()).hexdigest()) for name in json.load(open('/out/files.json')))}))
print('ALL_AGGREGATE_TESTS_PASSED_NO_COMMIT');sys.stdout.flush()
