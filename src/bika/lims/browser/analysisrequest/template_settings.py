# -*- coding: utf-8 -*-
"""Restricted HTML invoice templates; saved configuration is snapshotted on issue."""
import re, json, hashlib, base64
from six import string_types, BytesIO
from zope.annotation.interfaces import IAnnotations
from bika.lims import api
from . import billing

KEY='tppc.invoice.template.v1'
FIELDS=('issuer','contact','footer','color','logo','html')
TOKENS=('invoice_number','client_name','sample_id','date','issuer','contact','logo','items_table','total','currency','note','description','stamp','seller_address','seller_postal_code','seller_phone','seller_tax_id','buyer_address','buyer_postal_code','buyer_phone','buyer_tax_id')
DEFAULT_HTML=u'''<style>h1{color:#174c69}table{width:100%;border-collapse:collapse}td,th{padding:12px;border-bottom:1px solid #dbe4ed;text-align:right}.sum{font-size:22px;font-weight:bold}</style>
<header>{{logo}}<h1>فاکتور خدمات آزمایشگاهی</h1><strong>{{issuer}}</strong><p>{{contact}}</p></header>
<p>شمارهٔ فاکتور: {{invoice_number}} | تاریخ: {{date}}</p><p>مشتری: {{client_name}}</p><p>نمونه: {{sample_id}}</p>
<p>{{description}}</p>{{items_table}}<p class="sum">مبلغ نهایی: {{total}} {{currency}}</p><p>{{note}}</p>'''


def read():
    return dict(IAnnotations(api.get_senaite_setup()).get(KEY,{}))


def revision(settings):
    return hashlib.sha256(json.dumps(settings,sort_keys=True,ensure_ascii=True).encode('utf-8')).hexdigest()


PROPERTIES=set(('color background-color font-size font-family font-weight font-style text-align direction line-height width max-width min-width height max-height margin margin-top margin-bottom margin-left margin-right padding padding-top padding-bottom padding-left padding-right border border-top border-bottom border-left border-right border-color border-width border-style border-collapse border-spacing border-radius vertical-align table-layout page-break-before page-break-after page-break-inside display float clear').split())


def declarations(text):
    result=[]
    for chunk in text.split(';'):
        if not chunk.strip():continue
        if ':' not in chunk:raise ValueError(u'ساختار CSS معتبر نیست.')
        name,value=chunk.split(':',1);name=name.strip().lower();value=value.strip()
        if name not in PROPERTIES or not re.match(r'^[a-zA-Z0-9\s#.,%()"\-]+$',value):
            raise ValueError(u'ویژگی CSS مجاز نیست: '+name)
        if re.search(r'url|expression|behavior|binding|javascript',value,re.I):raise ValueError(u'منبع خارجی یا کد اجرایی در CSS مجاز نیست.')
        result.append(name+':'+value)
    return ';'.join(result)


def stylesheet(text):
    result=[];position=0
    for match in re.finditer(r'([^{}]+)\{([^{}]*)\}',text):
        if text[position:match.start()].strip():raise ValueError(u'ساختار CSS معتبر نیست.')
        selectors=match.group(1).strip()
        if selectors=='@page':
            page=[]
            for part in match.group(2).split(';'):
                if not part.strip():continue
                key,sep,value=part.partition(':');key=key.strip();value=value.strip()
                if not sep or not ((key=='size' and value in ('A4 landscape','A4 portrait','A4')) or (key=='margin' and re.match(r'^(?:[5-9]|[1-3][0-9])mm$',value))):
                    raise ValueError(u'تنظیم صفحه فقط A4 و حاشیهٔ ۵ تا ۳۹ میلی‌متر را می‌پذیرد.')
                page.append(key+':'+value)
            result.append('@page{'+ ';'.join(page)+'}');position=match.end();continue
        if not re.match(r'^[a-zA-Z0-9\s.#,:>+()\-]+$',selectors):raise ValueError(u'انتخابگر CSS مجاز نیست. از CSS ساده استفاده کنید.')
        scoped=[]
        for selector in selectors.split(','):
            selector=selector.strip()
            scoped.append('.billing .invoice-custom' if selector in ('html','body') else '.billing .invoice-custom '+selector)
        result.append(','.join(scoped)+'{'+declarations(match.group(2))+'}');position=match.end()
    if text[position:].strip():raise ValueError(u'ساختار CSS معتبر نیست.')
    return u'\n'.join(result)


def validate_html(text):
    from lxml import html, etree
    if len(text.encode('utf-8'))>150000:raise ValueError(u'فایل قالب باید کوچک‌تر از ۱۵۰ کیلوبایت باشد.')
    if not re.search(r'<(?:html|body)\b',text,re.I):
        text=u'<html><body>'+text+u'</body></html>'
    root=html.document_fromstring(text,parser=html.HTMLParser(no_network=True))
    nodes=list(root.iter())
    if len(nodes)>1000:raise ValueError(u'قالب بیش از حد پیچیده است.')
    allowed=set('html head body title meta style div span p strong b em i small h1 h2 h3 table thead tbody tfoot tr th td colgroup col br hr header footer section article main'.split())
    for node in nodes:
        if not isinstance(node.tag,string_types):raise ValueError(u'توضیحات HTML یا کد اجرایی در قالب مجاز نیست.')
        tag=node.tag.lower()
        if tag not in allowed:raise ValueError(u'عنصر HTML مجاز نیست: '+tag)
        if len(list(node.iterancestors()))>25:raise ValueError(u'قالب بیش از حد تو در تو است.')
        for name,value in node.attrib.items():
            if name not in ('class','id','style','dir','colspan','rowspan','lang','charset'):raise ValueError(u'ویژگی HTML مجاز نیست: '+name)
            if '{{' in value or '}}' in value:raise ValueError(u'جای‌نگهدارها فقط داخل متن مجازند، نه داخل ویژگی HTML.')
            if name=='style':declarations(value)
            elif name in ('colspan','rowspan') and not re.match(r'^[1-9][0-9]?$',value):raise ValueError(u'تعداد سطر یا ستون معتبر نیست.')
            elif name not in ('colspan','rowspan') and not re.match(r'^[a-zA-Z0-9_\s\-]+$',value):raise ValueError(u'مقدار ویژگی HTML معتبر نیست.')
        if tag=='style':stylesheet(node.text or '')
    tokens=set(re.findall(r'\{\{\s*([a-z_]+)\s*\}\}',text))
    if tokens-set(TOKENS):raise ValueError(u'جای‌نگهدار ناشناخته در قالب وجود دارد.')
    if '{{' in re.sub(r'\{\{\s*[a-z_]+\s*\}\}','',text):raise ValueError(u'جای‌نگهدار قالب معتبر نیست.')
    visible=root.find('body')
    visible_text=etree.tostring(visible,encoding='unicode') if visible is not None else ''
    visible_tokens=set(re.findall(r'\{\{\s*([a-z_]+)\s*\}\}',visible_text))
    if not set(('invoice_number','client_name','items_table','total','currency')).issubset(visible_tokens):
        raise ValueError(u'قالب باید شمارهٔ فاکتور، نام مشتری، جدول خدمات، مبلغ و واحد پول را داشته باشد.')
    return root


def custom_html(text,values):
    from lxml import html
    root=validate_html(text)
    css=[]
    for node in root.iter():
        if node.tag=='style':css.append(stylesheet(node.text or ''))
        if 'style' in node.attrib:node.attrib['style']=declarations(node.attrib['style'])
    for node in list(root.iter('style')):
        if node.getparent() is not None:node.getparent().remove(node)
    body=root.find('body')
    markup=billing.h(body.text or '')+u''.join(html.tostring(node,encoding='unicode') for node in body) if body is not None else ''
    markup=re.sub(r'\{\{\s*([a-z_]+)\s*\}\}',lambda m:values[m.group(1)],markup)
    return u'<section class="billing"><style>%s</style><article class="document invoice-custom"><style>%s</style>%s</article></section>' % (billing.STYLE,u'\n'.join(css),markup)


def logo_upload(upload):
    from PIL import Image
    raw=upload.read(1000001)
    if len(raw)>1000000:raise ValueError(u'حجم لوگو باید کمتر از یک مگابایت باشد.')
    image=Image.open(BytesIO(raw))
    if image.format not in ('PNG','JPEG') or image.width*image.height>4000000:raise ValueError(u'لوگو باید PNG یا JPG و حداکثر چهار مگاپیکسل باشد.')
    image.load();image.thumbnail((1000,1000));output=BytesIO();image.convert('RGBA').save(output,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode('ascii')


def render(data,number,date,default_render):
    from lxml import html
    settings=data.get('template_settings',{})
    from . import stamp
    if not settings:return stamp.decorate(default_render(data,number,date),data,'')
    copy=dict(data)
    if settings.get('issuer'):copy['issuer']=settings['issuer']
    if settings.get('contact'):copy['issuer_contact']=settings['contact']
    if settings.get('logo'):copy['logo']=settings['logo']
    unit=u'ریال' if data['currency']=='IRR' else data['currency']
    note=u' · '.join(s for s in (data.get('note',''),settings.get('footer','')) if s)
    copy['note']=note
    if settings.get('html'):
        vals=dict(invoice_number=billing.h(number or u'پیش‌فاکتور'),client_name=billing.h(data['client']),sample_id=billing.h(data['sample']),date=billing.h(date),issuer=billing.h(copy.get('issuer','')),contact=billing.h(copy.get('issuer_contact','')),total=billing.money(data['total']),currency=billing.h(unit),note=billing.h(note),description=billing.h(data.get('description','')))
        for key in ('seller_address', 'seller_postal_code', 'seller_phone', 'seller_tax_id', 'buyer_address', 'buyer_postal_code', 'buyer_phone', 'buyer_tax_id'):vals[key]=billing.h(data.get(key,'')) or u'—'
        vals['stamp']=stamp.image(data)
        vals['logo']=u'<img class="logo" alt="لوگو" src="%s"/>' % billing.h(copy['logo']) if copy.get('logo') else ''
        # Use physical LTR column order: old PDF engines ignore RTL table flow.
        # Amount stays left; Persian descriptions retain RTL text on the right.
        vals['items_table']=u'<table class="invoice-items" dir="ltr" style="direction:ltr;table-layout:fixed"><colgroup><col style="width:20%%"/><col style="width:80%%"/></colgroup><thead><tr><th dir="rtl" style="direction:rtl;text-align:center">مبلغ (%s)</th><th dir="rtl" style="direction:rtl;text-align:right">شرح خدمات</th></tr></thead><tbody>%s</tbody></table>' % (billing.h(unit),u''.join(u'<tr><td class="num" dir="ltr" style="direction:ltr;text-align:center">%s</td><td dir="rtl" style="direction:rtl;text-align:right">%s</td></tr>' % (billing.money(p),billing.h(t)) for t,p in data['items']))
        result=custom_html(settings['html'],vals)
        # Keep totals aligned even for formal templates frozen in old invoices.
        tree=html.fragment_fromstring(result,create_parent='div')
        for row in tree.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," formal ")]//tr'):
            if len(row)!=2 or row[0].tag!='th' or row[1].tag!='td':continue
            if u'جمع کل' not in row[0].text_content() or 'money' not in row[1].get('class','').split():continue
            table=row.getparent()
            while table is not None and table.tag!='table':table=table.getparent()
            if table is None:continue
            table.set('dir','ltr');table.set('style',table.get('style','')+';direction:ltr;table-layout:fixed')
            label,amount=row[0],row[1]
            row.remove(label);row.append(label)
            amount.set('style','width:20%;direction:ltr;text-align:center')
            label.set('style','width:80%;direction:rtl;text-align:right')
        result=u''.join(html.tostring(node,encoding='unicode') for node in tree)
    else:result=default_render(copy,number,date)
    color=settings.get('color','#174c69')
    result=stamp.decorate(result,data,settings.get('html',''))
    return result+u'<style>.billing .masthead{border-color:%s}.billing h1{color:%s}.billing .total{border-color:%s}</style>' % (color,color,color)


FORMAL_HTML = u'<style>\n@page{size:A4 landscape;margin:12mm}\n.formal{font-size:11px;line-height:1.8;color:#111111}\n.formal h1{font-size:20px;text-align:center;color:#111111;margin:0;padding:4px}\n.formal table{width:100%;border-collapse:collapse;margin:0;table-layout:fixed}\n.formal td,.formal th{border:1px solid #222222;padding:7px;vertical-align:middle;color:#111111;background-color:#ffffff}\n.formal .band{background-color:#eeeeee;text-align:center;font-weight:bold;font-size:13px}\n.formal .header td{border:0}.formal .caption{width:65%}.formal .sign{height:65px;vertical-align:top}\n.formal .logo{width:100px;max-height:55px;float:right}.formal .money{direction:ltr;text-align:center;font-size:16px;font-weight:bold}\n.formal .services th{background-color:#eeeeee}.formal .services td{height:55px}.formal .muted{color:#555555;font-size:10px}\n</style>\n<section class="formal">\n<table class="header"><tr><td style="width:17%">{{logo}}</td><td class="caption"><h1>فاکتور فروش کالا و خدمات</h1></td><td>شماره: {{invoice_number}}<br/>تاریخ: {{date}}<br/>شناسهٔ نمونه: {{sample_id}}</td></tr></table>\n<table><tr><th class="band" colspan="3">مشخصات فروشنده</th></tr>\n<tr><td style="width:50%">نام شخص حقیقی / حقوقی: {{issuer}}</td><td>شناسهٔ مالیاتی: {{seller_tax_id}}</td><td>کد پستی: {{seller_postal_code}}</td></tr>\n<tr><td colspan="2">نشانی کامل: {{seller_address}}</td><td>تلفن / نمابر: {{seller_phone}}</td></tr>\n<tr><th class="band" colspan="3">مشخصات خریدار</th></tr>\n<tr><td>نام شخص حقیقی / حقوقی: {{client_name}}</td><td>شناسهٔ مالیاتی: {{buyer_tax_id}}</td><td>کد پستی: {{buyer_postal_code}}</td></tr>\n<tr><td colspan="2">نشانی کامل: {{buyer_address}}</td><td>تلفن / نمابر: {{buyer_phone}}</td></tr>\n<tr><th class="band" colspan="3">مشخصات کالا یا خدمات مورد معامله</th></tr></table>\n<div class="services">{{items_table}}</div>\n<table><tr><th class="band" style="width:70%">جمع کل ({{currency}})</th><td class="money">{{total}}</td></tr>\n<tr><td colspan="2">توضیحات: {{description}}<br/>{{note}}</td></tr>\n<tr><td class="sign">مهر و امضای فروشنده</td><td class="sign">مهر و امضای خریدار</td></tr></table>\n</section>\n'
