# -*- coding: utf-8 -*-
"""Customer invoices: explicit request totals, immutable issue snapshots."""
from decimal import Decimal
from xml.sax.saxutils import escape
from bika.lims import api
from AccessControl import Unauthorized
from senaite.core.permissions import ManageInvoices


def h(value):
    return escape(api.safe_unicode(value or u''), {'"': '&quot;'})


def allowed(obj):
    return api.security.check_permission(ManageInvoices, obj)


def linked_request(sample):
    # Only a UID association is evidence; matching tracking numbers is unsafe.
    uid = api.get_uid(sample)
    folder = getattr(api.get_senaite_setup(), 'sampleintake', None)
    matches = []
    if folder is not None:
        for obj in folder.objectValues():
            if api.get_portal_type(obj) == 'SampleRequest' and getattr(obj, 'created_sample_uid', '') == uid:
                matches.append(obj)
    if len(matches) > 1:
        raise ValueError('Multiple requests linked to sample')
    return matches[0] if matches else None


def money(value):
    amount=Decimal(str(value or 0))
    return u'{:,.0f}'.format(amount) if amount==amount.to_integral_value() else u'{:,.2f}'.format(amount)


def service_prices(sample):
    """Resolve zero legacy analysis quotes without mutating their stored fields."""
    from bika.lims.interfaces import IAnalysis, IAnalysisProfile
    objects=list(sample.getBillableItems())
    covered=set()
    for obj in objects:
        if IAnalysisProfile.providedBy(obj):
            covered.update(api.get_uid(s) for s in obj.getServices())
    rows=[];subtotal=Decimal('0');vat_total=Decimal('0');fallbacks=[]
    bulk=bool(sample.getClient().getBulkDiscount())
    for obj in objects:
        service=obj.getAnalysisService() if IAnalysis.providedBy(obj) else None
        # Native getBillableItems may also include analyses covered by a fixed profile.
        if service is not None and api.get_uid(service) in covered:continue
        price=Decimal(str(obj.getPrice() or 0))
        rate=obj.getAnalysisProfileVAT() if IAnalysisProfile.providedBy(obj) else obj.getVAT()
        rate=Decimal(str(rate or 0))
        if price==0 and service is not None:
            candidate=Decimal(str((service.getBulkPrice() if bulk else service.getPrice()) or 0))
            if not candidate.is_finite() or candidate<0:raise ValueError('Invalid service price')
            if candidate>0:
                price=candidate;fallbacks.append(api.get_uid(service))
        if not price.is_finite() or price<0 or not rate.is_finite() or rate<0:
            raise ValueError('Invalid analysis price or VAT')
        rows.append((api.safe_unicode(obj.Title()),str(price)))
        subtotal+=price;vat_total+=price*rate/Decimal('100')
    discount=Decimal(str(sample.getDefaultMemberDiscount() or 0)) if sample.getClient().getMemberDiscountApplies() else Decimal('0')
    if not discount.is_finite() or not 0<=discount<=100:raise ValueError('Invalid member discount')
    discount_amount=subtotal*discount/Decimal('100')
    tax=vat_total*(Decimal('1')-discount/Decimal('100'))
    return dict(items=rows,subtotal=str(subtotal),discount=str(discount_amount),tax=str(tax),
                total=str(subtotal-discount_amount+tax),price_fallbacks=fallbacks)


def current_data(sample):
    if not allowed(sample):
        raise Unauthorized('Invoice access denied')
    client = sample.getClient()
    source = linked_request(sample)
    amount = getattr(source, 'payment_amount', 0) if source is not None else 0
    amount = Decimal(str(amount or 0))
    if not amount.is_finite() or amount < 0:
        raise ValueError('Invalid payment amount')
    titles = [api.safe_unicode(obj.Title()) for obj in sample.getBillableItems()]
    data = dict(issuer=issuer_info()[0], issuer_contact=issuer_info()[1], logo=logo_data(),
                client=api.safe_unicode(client.Title()), sample=api.get_id(sample),
                source='services', currency=api.get_senaite_setup().getCurrency(),
                items=[], total='0',subtotal='0',tax='0',discount='0')
    if amount > 0:
        if amount != amount.to_integral_value():
            raise ValueError('Payment amount must be whole Rial')
        data.update(source='request', currency='IRR', total=str(amount),
                    subtotal=None, tax=None, discount=None,
                    items=[(u' / '.join(titles) or u'خدمات آزمایشگاهی', str(amount))])
    else:
        data.update(service_prices(sample))
    from . import template_settings
    from . import party_info
    data.update(party_info.snapshot(sample))
    data["template_settings"]=template_settings.read()
    return data


def data_for(sample):
    invoice = sample.getInvoice()
    frozen = getattr(invoice, 'billing_snapshot', None) if invoice is not None else None
    return dict(frozen) if frozen else current_data(sample)


# -*- coding: utf-8 -*-
STYLE = u'''@page{size:A4;margin:16mm;@bottom-center{content:counter(page);font-size:9pt;color:#64748b}}
.billing{direction:rtl;color:#182f48;font-family:Vazirmatn,Tahoma,sans-serif;max-width:1050px;margin:0 auto;font-size:14px;line-height:1.8}
.billing *{box-sizing:border-box}.billing .document{background:white;border:1px solid #dbe4ed;border-radius:12px;padding:30px}
.billing .masthead{border-bottom:3px solid #194969;padding-bottom:20px;margin-bottom:22px}.billing .eyebrow{color:#627b90;font-size:12px}
.billing .logo{width:180px;max-height:85px;object-fit:contain;float:left;margin:0 15px 12px 0}.billing .masthead:after{content:"";display:block;clear:both}
.billing h1{font-size:25px;margin:5px 0 12px;color:#173d5a}.billing h2{font-size:17px;margin:0 0 14px}.billing p{margin:8px 0}
.billing table{width:100%;border-collapse:collapse;margin:20px 0}.billing td,.billing th{text-align:right;vertical-align:top;padding:12px;border-bottom:1px solid #e3eaf1}
.billing th{background:#eef4f8;font-weight:600;color:#4a6278}.billing .meta td{border:0;padding:7px 12px;width:50%}.billing .meta{background:#f7f9fc;border-radius:8px}
.billing .label{font-size:12px;color:#687f93;display:block}.billing .num{direction:ltr;unicode-bidi:embed;white-space:nowrap;font-variant-numeric:tabular-nums}
.billing .total{background:#edf5f8;border-top:2px solid #1e637c;font-size:20px;font-weight:bold}.billing .total td{border:0}
.billing .note{background:#f6f8fb;padding:14px;border-radius:8px;color:#526b80;font-size:12px}.billing .actions{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}
.billing a{color:#155a7b}.billing .button,.billing button{display:inline-block;padding:10px 17px;border:1px solid #c7d7e3;background:#fff;border-radius:7px;color:#244b68;text-decoration:none;font:inherit;cursor:pointer}
.billing .primary{background:#174c69!important;color:white!important;border-color:#174c69!important}.billing .editor{background:#f5f8fb;border:1px solid #dbe4ed;border-radius:12px;padding:24px;margin:22px 0}
.billing input,.billing textarea{display:block;width:100%;border:1px solid #bdcddd;border-radius:7px;padding:11px;font:inherit;background:white;color:#18334e;margin:5px 0 16px}
.billing input:focus,.billing textarea:focus{outline:2px solid #3b809e;outline-offset:2px}.billing input[readonly]{background:#edf1f5}.billing label{font-weight:600;display:block}.billing small{color:#61768c}
.billing .status{padding:12px 16px;background:#e8f4ef;color:#215e49;border-radius:8px;margin:14px 0}.billing .warning{background:#fff4de;color:#785611}.billing .error{background:#ffeded;color:#922b36}
.billing details{margin:20px 0;border:1px solid #dbe4ed;border-radius:10px;padding:16px}.billing summary{cursor:pointer;font-weight:bold}.billing .revision{color:#526b80;font-size:12px}
@media(max-width:650px){.billing .document,.billing .editor{padding:15px}.billing h1{font-size:21px}.billing td,.billing th{padding:8px}.billing .total{font-size:16px}.billing .actions>*{flex-grow:1}.billing .table-wrap{overflow-x:auto}}
@media print{.billing .actions,.billing .editor,.billing details{display:none}.billing .document{border:0;padding:0}.billing{font-size:10pt}.billing table{page-break-inside:auto}.billing tr{page-break-inside:avoid}.billing .masthead{page-break-after:avoid}}'''


def default_render(data, number=u'', date=u''):
    unit = u'ریال' if data['currency'] == 'IRR' else h(data['currency'])
    rows = u''.join(u'<tr><td class="num">%s</td><td dir="rtl" style="direction:rtl;text-align:right">%s</td><td class="num">%s</td></tr>' % (money(price),h(title),i+1) for i,(title,price) in enumerate(data['items']))
    source = u'جمع مبالغ نهایی نمونه‌های انتخاب‌شده' if data['source']=='aggregate' else (u'مبلغ توافق‌شدهٔ درخواست' if data['source']=='request' else u'تعرفهٔ آزمون‌ها')
    notes = h(data.get('note', u''))
    description = h(data.get('description', u''))
    extras = u''
    if data['source'] == 'services':
        extras = u'<table><tr><td>جمع خدمات</td><td class="num">%s</td></tr><tr><td>تخفیف</td><td class="num">%s</td></tr><tr><td>مالیات</td><td class="num">%s</td></tr></table>' % (money(data['subtotal']),money(data['discount']),money(data['tax']))
    elif data['source'] == 'request':
        extras = u'<p class="revision">این مبلغ نهایی است؛ مالیات یا تخفیف جداگانه‌ای به آن افزوده نشده است.</p>'
    return u'''<section class="billing"><style>%s</style><article class="document">
    <header class="masthead">%s<div class="eyebrow">صورتحساب خدمات آزمایشگاهی</div><h1>%s</h1><strong>%s</strong><p class="revision">%s</p></header>
    <table class="meta"><tr><td><span class="label">صورتحساب برای</span><strong>%s</strong></td><td><span class="label">شمارهٔ فاکتور</span><span dir="ltr">%s</span></td></tr>
    <tr><td><span class="label">شناسهٔ نمونه</span><span dir="ltr">%s</span></td><td><span class="label">تاریخ صدور / اصلاح</span><span dir="ltr">%s</span></td></tr></table>
    %s<div class="table-wrap"><table class="invoice-items" dir="ltr" style="direction:ltr;table-layout:fixed"><colgroup><col style="width:20%%"/><col style="width:74%%"/><col style="width:6%%"/></colgroup><thead><tr><th dir="rtl">مبلغ (%s)</th><th dir="rtl">شرح خدمات</th><th dir="rtl">ردیف</th></tr></thead><tbody>%s</tbody></table></div>
    %s<table class="total" dir="ltr" style="direction:ltr;table-layout:fixed"><tr><td class="num" style="width:20%%">%s</td><td dir="rtl" style="direction:rtl">مبلغ نهایی (%s)</td></tr></table>
    <p class="revision">مبنای محاسبه: %s%s</p>%s<footer class="note">این صورتحساب مربوط به خدمات نمونهٔ درج‌شده است. وضعیت پرداخت، در پروندهٔ پرداخت درخواست ثبت می‌شود.</footer></article></section>''' % (
        STYLE,u'<img class="logo" alt="نشان آزمایشگاه" src="%s"/>' % h(data['logo']) if data.get('logo') else u'',u'فاکتور' if number else u'پیش‌فاکتور',h(data.get('issuer',u'')),h(data.get('issuer_contact',u'')),h(data['client']),h(number) or u'صادر نشده',h(data['sample']),h(date) or u'—',u'<p>%s</p>' % description if description else u'',unit,rows,extras,money(data['total']),unit,source,u' | نسخهٔ %s' % h(data.get('revision',1)) if number else u'',u'<p class="note">%s</p>' % notes if notes else u'')


def pdf_bytes(data, number=u'', date=u''):
    # Standalone HTML avoids fetching the whole site/theme in a PDF request.
    from weasyprint import HTML
    # Vazirmatn TTF is already installed in the application image. Old Pango
    # cannot decode WOFF2 reliably; do not fetch browser webfonts here.
    document = u'<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><body>%s</body></html>' % render(data, number, date)
    return HTML(string=document, encoding='utf-8').write_pdf()


def issuer_info():
    lab = getattr(api.get_senaite_setup(), 'laboratory', None)
    if lab is None:
        return u'آزمایشگاه تندیس پارس', u''
    name = api.safe_unicode(api.get_title(lab))
    phone = api.safe_unicode(getattr(lab,'getPhone',lambda: '')() or '')
    tax = api.safe_unicode(getattr(lab,'getTaxNumber',lambda: '')() or '')
    return name, u' | '.join(v for v in (phone, u'شناسهٔ مالیاتی: '+tax if tax else u'') if v)


def logo_data():
    import os, base64
    import senaite.core.browser
    path = os.path.join(os.path.dirname(senaite.core.browser.__file__),'static','images','senaite-site-logo.png')
    with open(path,'rb') as image:
        return 'data:image/png;base64,' + base64.b64encode(image.read()).decode('ascii')


def render(data, number=u'', date=u''):
    from . import template_settings
    return template_settings.render(data,number,date,default_render)
