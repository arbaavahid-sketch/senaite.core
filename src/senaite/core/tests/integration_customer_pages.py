# -*- coding: utf-8 -*-
from __future__ import print_function
import io
import os
import transaction
from lxml import html
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser.customerfeedback.view import CustomerFeedbackView
from senaite.core.browser.customerfeedback.track import TrackRequestView
from senaite.core.browser.customerfeedback import track
from senaite.core.browser.publicforms import RateLimiter
from bika.lims import api
if not os.path.isfile('/data/.csrf-stage-only'): raise SystemExit('Stage required')
app=makerequest(app);site=app['senaite'];request=app.REQUEST
setSite(site);setRequest(request);alsoProvides(request,ISenaiteCore)
newSecurityManager(request,SimpleUser('customer-stage','',['Manager'],[]).__of__(site.acl_users))
def invoke(cls,values=None,method='GET',language='fa'):
    request.form.clear();request.form.update(values or {})
    request.set('REQUEST_METHOD',method);request.environ['HTTP_X_TPPC_CLIENT_IP']='synthetic-customer-stage'
    request.response.setStatus(200)
    view=cls(site,request);view._lang=lambda:language
    page=view()
    return view,page
def preview(page,name,language):
    tree=html.fromstring(page);root=tree.cssselect('.cc-page')[0]
    links=[]
    for href in tree.xpath('//link[@rel="stylesheet"]/@href'):
        href=href.replace('http://nohost/senaite','https://lims.tppc.ir').replace('http://nohost','https://lims.tppc.ir')
        links.append('<link rel="stylesheet" href="%s" />'%href)
    body=html.tostring(root,encoding='unicode').replace('http://nohost/senaite','https://lims.tppc.ir').replace('http://nohost','https://lims.tppc.ir')
    page=u'<!doctype html><html lang="%s" dir="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">%s<title>Customer preview</title></head><body style="padding:0 20px">%s</body></html>'%(language,'rtl' if language=='fa' else 'ltr',''.join(links),body)
    with io.open('/out/%s-%s.html'%(name,language),'w',encoding='utf-8') as output:output.write(page)
try:
    for language in ('fa','en'):
        view,page=invoke(CustomerFeedbackView,language=language)
        assert 'cc-feedback-form' in page
        tree=html.fromstring(page)
        assert tree.xpath('//select[@name="rating_overall"]/option[@value=""]')
        assert not tree.xpath('//select[contains(@name,"rating_")]/option[@selected]')
        preview(page,'feedback',language)
        view,page=invoke(TrackRequestView,language=language)
        assert 'no-store' in request.response.getHeader('Cache-Control')
        preview(page,'track',language)
    setup=api.get_senaite_setup();container=setup.customercare;before=len(container.objectIds())
    view,page=invoke(CustomerFeedbackView,{'submit':'1','kind':'survey','subject':'Synthetic survey'},'POST')
    assert request.response.getStatus()==400 and len(container.objectIds())==before and not view.tracking
    print('UNRATED_SURVEY_NOT_CREATED_AND_KIND_PRESERVED')
    view,page=invoke(CustomerFeedbackView,{'submit':'1','kind':'survey','subject':'Synthetic survey','rating_overall':'2'},'POST')
    assert view.tracking and not view.error
    survey=container[view.tracking]
    assert survey.rating_overall==2
    print('EXPLICIT_SURVEY_SCORE_STORED')
    complaint=api.create(container,'Complaint',title=u'Synthetic <script>alert(1)</script>',client_name=u'شرکت ساختگی')
    complaint.customer_response=u'پاسخ ساختگی <script>alert(1)</script>'
    blank=api.create(container,'SupportRequest',title=u'Synthetic blank name',client_name=u'')
    transaction.savepoint(optimistic=True)
    uid=api.get_id(complaint)
    view,page=invoke(TrackRequestView,{'track':'1','tracking':uid,'client_name':u'نام اشتباه'})
    assert view.result is None and view.not_found
    view,page=invoke(TrackRequestView,{'track':'1','tracking':api.get_id(blank)})
    assert view.result is None and view.not_found
    view,page=invoke(TrackRequestView,{'token':blank.access_token})
    assert view.result is not None
    view,page=invoke(TrackRequestView,{'token':'f'*32})
    assert view.result is None and view.not_found
    print('WRONG_CLIENT_AND_BLANK_CLIENT_BLOCKED_PRIVATE_TOKEN_ACCEPTED')
    for language in ('fa','en'):
        view,page=invoke(TrackRequestView,{'track':'1','tracking':uid,'client_name':u'شرکت ساختگی'},language=language)
        assert view.result is not None and not view.not_found
        assert not html.fromstring(page).xpath('//script[contains(text(),"alert(1)")]')
        preview(page,'track-result',language)
    complaint.payment_amount=12000;complaint.payment_paid=False
    original=track.zarinpal.is_configured;track.zarinpal.is_configured=lambda:False
    try:
        view,page=invoke(TrackRequestView,{'token':complaint.access_token})
        assert view.result and not view.result['pay_url']
        complaint.payment_amount='malformed'
        view,page=invoke(TrackRequestView,{'token':complaint.access_token})
        assert view.result and view.result['pay_amount']==0
    finally:track.zarinpal.is_configured=original
    print('PAYMENT_UNCONFIGURED_HIDES_BUTTON_AND_BAD_AMOUNT_DOES_NOT_HIDE_REQUEST')
    view,page=invoke(TrackRequestView,{'track':'1','tracking':['bad','shape']})
    assert request.response.getStatus()==400 and view.result is None
    track.TRACK_LIMITER=RateLimiter()
    for _ in range(60):assert track.TRACK_LIMITER.allow('synthetic-customer-stage')
    view,page=invoke(TrackRequestView,{'token':complaint.access_token})
    assert request.response.getStatus()==429 and view.result is None
    print('MALFORMED_LOOKUP_AND_EXCESSIVE_ATTEMPTS_REJECTED')
finally:
    transaction.abort();print('TRANSACTION_ABORTED_NO_REAL_EMAIL_PAYMENT_OR_CUSTOMER_RECORDS')
