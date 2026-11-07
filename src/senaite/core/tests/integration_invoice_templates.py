# -*- coding: utf-8 -*-
from __future__ import print_function
import os, json, hashlib, sys
import transaction
from six import BytesIO
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from plone.protect.authenticator import createToken
from bika.lims import api
from bika.lims.browser.analysisrequest import billing, template_settings as config
from bika.lims.browser.analysisrequest.template_editor import TemplateEditor
assert os.environ.get('TPPC_TEMPLATE_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);request=app.REQUEST;setRequest(request)
def login(role):newSecurityManager(request,SimpleUser('template-test','',[role],[]).__of__(site.acl_users))
def form(**values):
    request.form.clear();request.form.update(values);request.form['_authenticator']=createToken();request.set('REQUEST_METHOD','POST');request.response.setStatus(200)
class Upload(BytesIO):filename='invoice.html'
login('Manager')
try:
    view=TemplateEditor(site,request);view.template=lambda:view.content()
    before=config.read();old_version=config.revision(before)
    form(action='preview',mode='html',color='#245577',issuer=u'آزمایشگاه آزمایشی',contact=u'اطلاعات تماس',footer=u'متن پایین نمونه',template_file=Upload(config.DEFAULT_HTML.encode('utf-8')))
    result=view()
    assert config.read()==before and u'پیش‌نمایش' in result and 'srcdoc=' in result
    form(action='save',mode='html',color='#245577',issuer=u'آزمایشگاه آزمایشی',footer=u'متن پایین نمونه',version=old_version,template_file=Upload(config.DEFAULT_HTML.encode('utf-8')))
    view();assert request.response.getStatus()==303
    stored=config.read();assert stored['html']==config.DEFAULT_HTML
    print('UPLOAD_PREVIEW_NO_WRITE_SAVE_PRG_OK');sys.stdout.flush()
    sample=api.get_object(api.search({'portal_type':'AnalysisRequest'})[0])
    data=billing.current_data(sample);assert data['template_settings']==stored
    data['client']=u'<script>alert(1)</script>'
    html=billing.render(data,'TEST-001','2026-11-07')
    assert '<script>alert' not in html and '&lt;script&gt;' in html
    assert '{{total}}' not in html and 'TEST-001' in html
    assert u'فاکتور خدمات آزمایشگاهی' in html and u'آزمایشگاه آزمایشی' in html and 'data:image/png' in html
    pdf=billing.pdf_bytes(data,'TEST-001','2026-11-07');assert pdf.startswith(b'%PDF-')
    open('/out/template.pdf','wb').write(pdf)
    open('/out/template-preview.html','wb').write(html.encode('utf-8'))
    old_data=dict(data);old_data.pop('template_settings')
    assert billing.render(old_data,'OLD','')==billing.default_render(old_data,'OLD','')
    frozen=billing.render(data,'TEST-001','2026-11-07')
    config.IAnnotations(api.get_senaite_setup())[config.KEY]=dict(stored,issuer=u'عنوان جدید')
    assert billing.render(data,'TEST-001','2026-11-07')==frozen
    print('PLACEHOLDERS_ESCAPE_PDF_FROZEN_SETTINGS_OK');sys.stdout.flush()
    bad=['<script>alert(1)</script>','<img src="https://evil.invalid/x">','<iframe src="x"></iframe>',
         '<div onclick="evil()">x</div>','<style>div{background-color:url(https://evil.invalid)}</style>',
         '<div style="position:fixed">x</div>','<span title="{{client_name}}">x</span>']
    for fragment in bad:
        try:config.validate_html(fragment+config.DEFAULT_HTML);raise AssertionError('Unsafe HTML accepted')
        except ValueError:pass
    for fragment in ('<style>@import "x";</style>','{{unknown}}','{{bad-name}}'):
        try:config.validate_html(fragment+config.DEFAULT_HTML);raise AssertionError('Invalid template accepted')
        except ValueError:pass
    form(action='save',mode='html',color='#245577',version='stale',html=config.DEFAULT_HTML)
    view();assert request.response.getStatus()==409
    form(action='save',mode='html',color='#245577',html=config.DEFAULT_HTML);request.form.pop('_authenticator')
    try:view();raise AssertionError('CSRF missing accepted')
    except Exception as e:assert e.__class__.__name__ in ('Forbidden','Unauthorized'),repr(e)
    login('LabClerk')
    try:view();raise AssertionError('Clerk accepted')
    except Exception as e:assert e.__class__.__name__=='Unauthorized',repr(e)
    login('Anonymous')
    try:view();raise AssertionError('Anonymous accepted')
    except Exception as e:assert e.__class__.__name__=='Unauthorized',repr(e)
    print('UNSAFE_UPLOAD_STALE_CSRF_ROLES_REJECTED');sys.stdout.flush()
finally:transaction.abort()
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((name,hashlib.sha256(open('/out/'+name,'rb').read()).hexdigest()) for name in json.load(open('/out/files.json')))}))
print('ALL_TEMPLATE_TESTS_PASSED_NO_COMMIT');sys.stdout.flush()
