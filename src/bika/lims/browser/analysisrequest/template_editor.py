# -*- coding: utf-8 -*-
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from AccessControl import Unauthorized
from plone.protect import PostOnly, CheckAuthenticator
from plone.protect.authenticator import createToken
from zope.annotation.interfaces import IAnnotations
from bika.lims import api
from senaite.core.browser.payment.views import is_price_manager
from . import billing, template_settings as config


class TemplateEditor(BrowserView):
    template=ViewPageTemplateFile('templates/invoice.pt')

    def __call__(self):
        if not billing.allowed(self.context) or not is_price_manager(self.context):raise Unauthorized('Template configuration denied')
        if self.request.get('sample')=='1':
            self.request.response.setHeader('Content-Type','text/html; charset=utf-8')
            self.request.response.setHeader('Content-Disposition','attachment; filename="invoice-template.html"')
            return config.DEFAULT_HTML.encode('utf-8')
        self.settings=config.read();self.error='';self.preview=None
        if self.request.get('REQUEST_METHOD')=='POST':
            PostOnly(self.request);CheckAuthenticator(self.request)
            try:
                values=dict(self.settings)
                for key in ('issuer','contact','footer','color'):
                    values[key]=api.safe_unicode(self.request.form.get(key,'')).strip()
                    if len(values[key])>2000:raise ValueError(u'متن بیش از حد طولانی است.')
                import re
                if not re.match(r'^#[a-fA-F0-9]{6}$',values['color']):raise ValueError(u'رنگ باید به صورت کد شش‌رقمی باشد.')
                values['html']=api.safe_unicode(self.request.form.get('html',''))
                upload=self.request.form.get('template_file')
                if getattr(upload,'filename',''):
                    raw=upload.read(150001)
                    values['html']=raw.decode('utf-8-sig')
                if self.request.form.get('mode')!='html':values['html']=''
                elif not values['html'].strip():raise ValueError(u'فایل HTML را بارگذاری کنید یا متن قالب را وارد کنید.')
                if values['html']:config.validate_html(values['html'])
                logo=self.request.form.get('logo_file')
                if getattr(logo,'filename',''):values['logo']=config.logo_upload(logo)
                if self.request.form.get('default_logo'):values.pop('logo',None)
                if self.request.form.get('action')=='save':
                    if self.request.form.get('version')!=config.revision(self.settings):
                        self.request.response.setStatus(409);raise ValueError(u'قالب هم‌زمان تغییر کرده است. صفحه را تازه کنید.')
                    IAnnotations(api.get_senaite_setup())[config.KEY]=values
                    return self.request.response.redirect(api.get_url(api.get_portal())+'/@@invoice-template?saved=1',status=303)
                self.preview=self.make_preview(values)
                self.settings=values
            except (ValueError,UnicodeError,IOError) as error:
                if self.request.response.getStatus()!=409:self.request.response.setStatus(400)
                self.error=api.safe_unicode(error)
        return self.template()

    def make_preview(self,values):
        data=dict(issuer=u'آزمایشگاه نمونه',issuer_contact=u'مشخصات تماس',client=u'مشتری نمونه (پیش‌نمایش)',sample='SAMPLE-001',currency='IRR',source='request',items=[(u'خدمات آزمون نمونه','150000000')],total='150000000',note='',description='',logo=billing.logo_data(),template_settings=values)
        return u'<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><body>'+billing.render(data,'PREVIEW-001','2026-11-07')+u'</body></html>'

    def content(self):
        values=self.settings;h=billing.h;url=h(api.get_url(api.get_portal()))
        notice=u'<p class="status" role="status">قالب ذخیره شد. این قالب در صدور و اصلاحیه‌های بعدی استفاده می‌شود.</p>' if self.request.get('saved')=='1' else ''
        if self.error:notice+=u'<p class="status error" role="alert">%s</p>' % h(self.error)
        if self.preview is None:self.preview=self.make_preview(values)
        tokens=u' '.join(u'<code>{{%s}}</code>' % token for token in config.TOKENS)
        return u'''<section class="billing"><style>%s</style><h1>قالب فاکتور</h1><p>تنظیمات برای همهٔ مشتریان است. PDFهای صادرشده ثابت می‌مانند؛ برای اعمال قالب جدید به آن‌ها، اصلاحیه ثبت کنید.</p>%s
        <form method="post" enctype="multipart/form-data" class="editor"><input type="hidden" name="_authenticator" value="%s"/><input type="hidden" name="version" value="%s"/>
        <label for="template-mode">نوع قالب</label><select id="template-mode" name="mode"><option value="builtin" %s>قالب استاندارد سامانه</option><option value="html" %s>قالب HTML سفارشی</option></select>
        <label for="issuer">نام آزمایشگاه در سربرگ</label><input id="issuer" name="issuer" value="%s" placeholder="خالی: مشخصات فعلی آزمایشگاه"/>
        <label for="contact">اطلاعات تماس سربرگ</label><input id="contact" name="contact" value="%s"/>
        <label for="footer">متن پایین فاکتور</label><textarea id="footer" name="footer" rows="2">%s</textarea>
        <label for="color">رنگ اصلی</label><input id="color" type="color" name="color" value="%s"/>
        <label for="logo-file">بارگذاری لوگو (PNG یا JPG، حداکثر یک مگابایت)</label><input id="logo-file" type="file" name="logo_file" accept="image/png,image/jpeg"/>
        <label><input style="display:inline;width:auto" type="checkbox" name="default_logo" value="1"/> بازگشت به لوگوی اصلی آزمایشگاه</label>
        <hr/><h2>بارگذاری قالب HTML</h2><p><a class="button" href="%s/@@invoice-template?sample=1">دانلود قالب نمونه</a></p>
        <label for="template-file">فایل HTML با کدگذاری UTF-8 (حداکثر ۱۵۰ کیلوبایت)</label><input id="template-file" type="file" name="template_file" accept=".html,.htm,text/html"/>
        <p class="note">برای استفاده از فایل، نوع قالب را «HTML سفارشی» انتخاب کنید. فقط HTML و CSS ساده مجاز است؛ اسکریپت، لینک منابع خارجی و جای‌نگهدار داخل ویژگی‌های HTML پذیرفته نمی‌شود. برای لوگو از {{logo}} استفاده کنید.</p>
        <label for="template-html">متن قالب HTML</label><textarea id="template-html" name="html" rows="12" dir="ltr" style="font-family:monospace!important;text-align:left">%s</textarea>
        <p class="note" dir="ltr">%s</p><div class="actions"><button name="action" value="preview" type="submit">پیش‌نمایش بدون ذخیره</button><button class="primary" name="action" value="save" type="submit">ذخیرهٔ قالب</button></div></form>
        <h2>پیش‌نمایش با اطلاعات نمونه</h2><iframe title="پیش‌نمایش قالب فاکتور" sandbox="" style="width:100%%;height:850px;border:1px solid #dbe4ed;border-radius:10px;background:white" srcdoc="%s"></iframe></section>''' % (
            billing.STYLE,notice,h(createToken()),config.revision(config.read()),'selected="selected"' if not values.get('html') else '', 'selected="selected"' if values.get('html') else '',h(values.get('issuer','')),h(values.get('contact','')),h(values.get('footer','')),h(values.get('color','#174c69')),url,h(values.get('html','')),tokens,h(self.preview))
