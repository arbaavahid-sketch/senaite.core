# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser import publicforms
from senaite.core.browser.samplerequest.view import SampleRequestView
from senaite.core.browser.customerfeedback.view import CustomerFeedbackView
from bika.lims import api
if not os.path.isfile('/data/.csrf-stage-only'): raise SystemExit('Disposable stage required')
app=makerequest(app); site=app['senaite']; request=app.REQUEST
setSite(site); setRequest(request); alsoProvides(request,ISenaiteCore)
newSecurityManager(request,SimpleUser('public-form-stage','',['Manager'],[]).__of__(site.acl_users))
containers=(api.get_senaite_setup().sampleintake,api.get_senaite_setup().customercare)
before=[len(obj.objectIds()) for obj in containers]
def submit(cls,values):
    request.form.clear(); request.form.update(values)
    request.set('REQUEST_METHOD','POST'); request.environ['HTTP_X_TPPC_CLIENT_IP']='synthetic-stage'
    request.response.setStatus(200)
    view=cls(site,request); view()
    return view
try:
    for cls in (SampleRequestView,CustomerFeedbackView):
        for values in ({'submit':'1','subject':['bad','shape']}, {'submit':'1','subject':'x'*513},
                       {'submit':'1','subject':'test','kind':'invalid'}):
            view=submit(cls,values)
            assert request.response.getStatus()==400 and not view.tracking
    sample={'submit':'1','subject':'Synthetic test','client_name':'Synthetic','contact_name':'Synthetic',
            'contact_email':'synthetic@example.invalid','contact_phone':'000','declaration':'1'}
    invalid=dict(sample,service_uids=['f'*32]); view=submit(SampleRequestView,invalid)
    assert request.response.getStatus()==400 and not view.tracking
    assert [len(obj.objectIds()) for obj in containers]==before
    print('MALFORMED_AND_UNKNOWN_SERVICE_CREATE_NO_RECORDS')
    publicforms.LIMITER=publicforms.RateLimiter()
    for _ in range(60): assert publicforms.LIMITER.allow('synthetic-stage')
    view=submit(SampleRequestView,sample)
    assert request.response.getStatus()==429 and not view.tracking
    assert [len(obj.objectIds()) for obj in containers]==before
    print('RATE_LIMIT_PREVENTS_CREATION')
    publicforms.LIMITER=publicforms.RateLimiter()
    original_create=api.create
    def broken_create(*args,**kwargs):
        original_create(*args,**kwargs)
        raise ValueError('SYNTHETIC_PRIVATE_ERROR_MUST_NOT_LEAK')
    api.create=broken_create
    try:
        view=submit(SampleRequestView,sample)
        assert request.response.getStatus()==503 and not view.tracking
        assert 'SYNTHETIC_PRIVATE_ERROR' not in view.error
        assert [len(obj.objectIds()) for obj in containers]==before
    finally:
        api.create=original_create
    print('FAILED_SAVE_ROLLED_BACK_WITHOUT_PRIVATE_ERROR_DISCLOSURE')
    view=submit(SampleRequestView,sample)
    assert view.tracking and not view.error
    assert len(containers[0].objectIds())==before[0]+1
    view=submit(CustomerFeedbackView,{'submit':'1','subject':'Synthetic feedback','kind':'survey','rating_overall':'4'})
    assert view.tracking and not view.error
    assert len(containers[1].objectIds())==before[1]+1
    print('VALID_SAMPLE_AND_SURVEY_ACCEPTED')
finally:
    transaction.abort()
    print('TRANSACTION_ABORTED_NO_REAL_EMAIL_OR_PAYMENT')
