# -*- coding: utf-8 -*-
from __future__ import print_function
import os,json,hashlib,sys
import transaction
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from bika.lims import api
from bika.lims.browser.analysisrequest import billing,template_settings as config,party_info
assert os.environ.get('TPPC_FORMAL_STAGE')=='1' and os.path.isfile('/data/.csrf-stage-only')
app=makerequest(app);site=app['senaite'];setSite(site);setRequest(app.REQUEST)
newSecurityManager(app.REQUEST,SimpleUser('formal-template-stage','',['Manager'],[]).__of__(site.acl_users))
try:
    config.validate_html(config.FORMAL_HTML)
    before=config.read()
    sample=api.get_object(api.search({'portal_type':'AnalysisRequest'})[0])
    data=billing.current_data(sample)
    assert 'buyer_address' in data and 'seller_phone' in data
    assert config.read()==before
    data.update(client=u'مشتری نمونه',sample='SAMPLE-001',source='request',currency='IRR',total='150000000',items=[(u'خدمات آزمایشگاهی','150000000')],description=u'شرح خدمات ثبت‌شده در سامانه',note='',template_settings={'html':config.FORMAL_HTML,'color':'#174c69'})
    html=billing.render(data,'TEST-001','2026-11-07')
    assert '150,000,000' in html and '825' not in html and '750.000' not in html
    assert u'طلای سیاه وستا' not in config.FORMAL_HTML
    assert '{{' not in html and '@page{size:A4 landscape' in html
    assert u'مشخصات فروشنده' in html and u'مشخصات خریدار' in html
    assert u'مهر و امضای خریدار' in html
    pdf=billing.pdf_bytes(data,'TEST-001','2026-11-07');assert pdf.startswith(b'%PDF-')
    open('/out/preview.pdf','wb').write(pdf)
    for css in ('@page{size:100000mm}', '@page{margin:0mm}', '@page{background:url(https://x)}'):
        try:config.stylesheet(css);raise AssertionError('Unsafe page rule accepted')
        except ValueError:pass
    print('FORMAL_TEMPLATE_LANDSCAPE_PARTIES_DYNAMIC_TOTAL_SAFE_PAGE_OK');sys.stdout.flush()
finally:transaction.abort()
open('/out/tests-passed.json','w').write(json.dumps({'sha256':dict((name,hashlib.sha256(open('/out/'+name,'rb').read()).hexdigest()) for name in json.load(open('/out/files.json')))}))
print('ALL_FORMAL_TESTS_PASSED_NO_COMMIT');sys.stdout.flush()
