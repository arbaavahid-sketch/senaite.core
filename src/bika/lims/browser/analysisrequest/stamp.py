# -*- coding: utf-8 -*-
"""Optional, per-invoice company stamp. No stamp is applied by default."""
from . import billing, template_settings as config


def controls(data):
    available=config.read().get('stamp') or data.get('stamp_file')
    return u'<label><input type="checkbox" style="display:inline;width:auto" name="billing_stamp" value="1" %s %s/> نمایش مهر شرکت در این فاکتور</label><p class="revision">%s</p>' % (
        u'checked="checked"' if data.get('stamp_enabled') else '',u'' if available else u'disabled="disabled"',
        u'با برداشتن تیک، نسخهٔ جدید بدون مهر ساخته می‌شود؛ PDFهای قبلی محفوظ می‌مانند.' if available else u'ابتدا تصویر مهر را از «تنظیم قالب فاکتور» بارگذاری کنید.')


def image(data):
    if not data.get('stamp_enabled') or not data.get('stamp_file'):return u''
    return u'<div class="company-stamp" style="text-align:center;margin:6px 0"><img alt="مهر شرکت" style="width:125px;max-height:85px" src="%s"/></div>' % billing.h(data['stamp_file'])


def decorate(html,data,custom):
    graphic=image(data)
    if not graphic:return html
    if custom and '{{stamp}}' in custom:return html
    label=u'مهر و امضای فروشنده'
    if label in html:return html.replace(label,label+graphic,1)
    return html+u'<section class="billing"><p>مهر شرکت</p>'+graphic+u'</section>'


def apply(data,form,previous):
    enabled=form.get('billing_stamp')=='1'
    picture=(config.read().get('stamp') or previous.get('stamp_file','')) if enabled else ''
    if enabled and not picture:raise ValueError(u'ابتدا تصویر مهر شرکت را بارگذاری کنید.')
    data['stamp_enabled']=enabled;data['stamp_file']=picture
