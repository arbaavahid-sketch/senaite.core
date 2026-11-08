# -*- coding: utf-8 -*-
from __future__ import print_function
import os,sys
from decimal import Decimal
import transaction
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from bika.lims import api
from bika.lims.interfaces import IAnalysis
from bika.lims.browser.analysisrequest import billing,aggregate
assert os.environ.get('TPPC_AGGREGATE_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
newSecurityManager(request,SimpleUser('pricing-stage','',['Manager'],[]).__of__(site.acl_users))
old_link=billing.linked_request
try:
    candidates=[]
    for brain in api.search({'portal_type':'AnalysisRequest'}):
        sample=api.get_object(brain)
        items=list(sample.getBillableItems())
        if items and all(IAnalysis.providedBy(o) for o in items) and not sample.getInvoice():candidates.append(sample)
    sample=candidates[0];client=sample.getClient();items=list(sample.getBillableItems())
    billing.linked_request=lambda obj:None
    client.setBulkDiscount(False);client.setMemberDiscountApplies(False)
    for obj in items:
        obj.setPrice('0');obj.setVAT('0');obj.getAnalysisService().setPrice('1200000')
    data=billing.current_data(sample)
    assert Decimal(data['total'])==Decimal('1200000')*len(items),data['total']
    assert len(data['price_fallbacks'])==len(items)
    assert all(Decimal(obj.getPrice())==0 for obj in items)
    # Nonzero historical prices remain authoritative even when tariffs change.
    items[0].setPrice('500000');items[0].setVAT('10')
    data=billing.current_data(sample)
    assert Decimal(data['total'])==Decimal('550000')+Decimal('1200000')*(len(items)-1)
    # Bulk tariffs are selected explicitly, without substituting regular prices.
    items[0].setPrice('0');client.setBulkDiscount(True)
    for obj in items:obj.setBulkPrice('0');obj.getAnalysisService().setBulkPrice('700000')
    data=billing.current_data(sample)
    assert Decimal(data['subtotal'])==Decimal('700000')*len(items)
    assert Decimal(data['tax'])==Decimal('70000')
    print('ZERO_LEGACY_CURRENT_TARIFF_NONZERO_QUOTE_VAT_AND_BULK_OK');sys.stdout.flush()
    # An agreed request total always wins over tariff resolution.
    class Payment(object):payment_amount=3333333
    billing.linked_request=lambda obj:Payment()
    data=billing.current_data(sample)
    assert data['source']=='request' and Decimal(data['total'])==3333333
    assert data['currency']=='IRR' and data['tax'] is None
    billing.linked_request=lambda obj:None
    # Fixed profiles suppress their included analyses; do not charge both.
    from zope.interface import alsoProvides
    from bika.lims.interfaces import IAnalysisProfile
    class Profile(object):
        def getServices(self):return [o.getAnalysisService() for o in items]
        def getPrice(self):return '9000000'
        def getAnalysisProfileVAT(self):return '10'
        def Title(self):return u'پروفایل آزمون'
    profile=Profile();alsoProvides(profile,IAnalysisProfile)
    original=sample.__class__.getBillableItems
    sample.__class__.getBillableItems=lambda self:[profile]+items
    try:
        data=billing.service_prices(sample)
        assert len(data['items'])==1 and Decimal(data['total'])==9900000
    finally:sample.__class__.getBillableItems=original
    print('PAYMENT_PRIORITY_AND_FIXED_PROFILE_NO_DOUBLE_CHARGE_OK');sys.stdout.flush()
finally:
    billing.linked_request=old_link;transaction.abort()
# Covers issuance, revisions, frozen PDFs, unchanged payments and rollback.
execfile('/out/aggregate_regression.py')
