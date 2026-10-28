# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import io
import transaction
from lxml import html
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser.samplerequest.view import SampleRequestView,LABELS
if not os.path.isfile('/data/.csrf-stage-only'): raise SystemExit('Stage required')
app=makerequest(app); site=app['senaite']; request=app.REQUEST
setSite(site); setRequest(request); alsoProvides(request,ISenaiteCore)
newSecurityManager(request,SimpleUser('design-stage','',['Manager'],[]).__of__(site.acl_users))
try:
    view=SampleRequestView(site,request)
    for language in ('fa','en'):
        view._lang=lambda:language
        rendered=view()
        tree=html.fromstring(rendered)
        roots=tree.cssselect('.tppc-request'); assert len(roots)==1
        root=roots[0]
        assert len(root.cssselect('.rq-section'))==5
        names=set(root.xpath('.//input/@name|.//select/@name|.//textarea/@name|.//button/@name'))
        assert {'client_name','contact_name','contact_email','contact_phone','subject','declaration','submit','service_uids:list','safety_hazards:list','storage_conditions:list'}.issubset(names)
        for name in ('client_name','contact_name','contact_email','contact_phone','subject'):
            field=root.xpath('.//input[@name="%s"]'%name)[0]
            assert field.get('required') is not None
            assert root.xpath('.//label[@for="%s"]'%field.get('id'))
        # Keep the preview standalone; no application JavaScript or customer data.
        styles=[]
        for link in tree.xpath('//link[@rel="stylesheet"]/@href'):
            link=link.replace('http://nohost/senaite','https://lims.tppc.ir').replace('http://nohost','https://lims.tppc.ir')
            styles.append('<link rel="stylesheet" href="%s" />'%link)
        body=html.tostring(root,encoding='unicode').replace('http://nohost/senaite','https://lims.tppc.ir').replace('http://nohost','https://lims.tppc.ir')
        page=u'<!doctype html><html lang="%s" dir="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">%s<title>TPPC request preview</title></head><body style="margin:0;padding:0 20px">%s</body></html>'%(language,'rtl' if language=='fa' else 'ltr',''.join(styles),body)
        with io.open('/out/request-%s.html'%language,'w',encoding='utf-8') as output: output.write(page)
        view.error='Synthetic validation error'
        request.form.update({'subject':u'<script>alert(1)</script>','contact_name':u'نام آزمایشی','declaration':'1','service_uids':['a'*32]})
        assert view.get_field_value('subject')==u'<script>alert(1)</script>'
        error_html=view.template()
        error_tree=html.fromstring(error_html)
        assert error_tree.xpath('//input[@name="subject"]/@value')==['<script>alert(1)</script>']
        assert not error_tree.xpath('//script[contains(text(),"alert(1)")]')
        assert error_tree.xpath('//input[@name="declaration"]/@checked')
        request.form['subject']=['bad','shape']; assert view.get_field_value('subject')==u''
        request.form.clear()
        print('LANGUAGE_LAYOUT_AND_SAFE_RETENTION_OK='+language)
finally:
    transaction.abort()
    print('TRANSACTION_ABORTED_NO_SUBMISSION')
