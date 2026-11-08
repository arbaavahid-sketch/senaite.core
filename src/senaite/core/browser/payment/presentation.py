# -*- coding: utf-8 -*-
"""Payment presentation only. No gateway or amount mutation lives here."""
from xml.sax.saxutils import escape
from bika.lims import api


CSS = u''' .pay-ui{direction:rtl;font-family:Vazirmatn,Tahoma,sans-serif;color:#1b344b;line-height:1.8;max-width:1150px;margin:24px auto}
.pay-ui *{box-sizing:border-box}.pay-ui h1{font-size:27px;line-height:1.5;margin:0 0 8px}.pay-ui h2{font-size:18px;margin:0 0 16px}
.pay-ui .muted{color:#677e91;font-size:13px}.pay-ui .top{display:flex;justify-content:space-between;gap:20px;align-items:center;margin:0 0 24px}.pay-ui .brand{color:#42677f;font-size:13px;margin-bottom:10px}
.pay-ui .panel{background:white;border:1px solid #dbe4ec;border-radius:12px;padding:25px;margin-bottom:20px;box-shadow:0 4px 18px #17334e05}
.pay-ui .cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:22px}.pay-ui .cardx{border:1px solid #dbe4ec;border-radius:10px;background:#fff;padding:18px}.pay-ui .cardx strong{display:block;font-size:23px;margin-top:8px;color:#154762}
.pay-ui .split{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(260px,1fr);gap:22px}.pay-ui .badge{display:inline-block;border-radius:20px;padding:5px 12px;font-size:12px;background:#fff0d6;color:#795215}.pay-ui .paid{background:#e8f4ee;color:#21644d}
.pay-ui .actions{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 0}.pay-ui a{color:#155977;text-decoration:none}.pay-ui button,.pay-ui .button{display:inline-block;border:1px solid #c8d7e3;border-radius:7px;padding:10px 17px;font:inherit;cursor:pointer;background:#fff;color:#234d68;text-decoration:none}
.pay-ui .primary{color:#fff!important;background:#185472!important;border-color:#185472!important}.pay-ui input,.pay-ui select{font:inherit;border:1px solid #bfcedb;border-radius:7px;padding:11px;background:white;max-width:100%}.pay-ui input:focus,.pay-ui button:focus{outline:2px solid #4791aa;outline-offset:2px}
.pay-ui label{display:block;font-weight:600;margin-bottom:8px}.pay-ui input.amount{width:100%;font-size:24px;direction:ltr;text-align:right;font-variant-numeric:tabular-nums}.pay-ui input[readonly]{background:#f2f5f8}
.pay-ui .success{border:1px solid #c1e1d0;background:#ecf7f1;color:#205e44;border-radius:8px;padding:12px 17px;margin:18px 0}.pay-ui .info{background:#f1f6fa;border-radius:8px;padding:15px;color:#526f84;font-size:13px;margin-top:18px}
.pay-ui dl{display:grid;grid-template-columns:110px 1fr;gap:12px 18px;margin:0}.pay-ui dt{color:#74889a;font-size:13px}.pay-ui dd{margin:0;overflow-wrap:anywhere}.pay-ui .table-wrap{overflow-x:auto}.pay-ui table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px}
.pay-ui td,.pay-ui th{text-align:right;padding:14px 12px;border-bottom:1px solid #e4ebf1}.pay-ui th{color:#698094;font-weight:600;background:#f7f9fc}.pay-ui .num{direction:ltr;font-variant-numeric:tabular-nums;unicode-bidi:embed}.pay-ui .tools{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px}.pay-ui .tools input{flex-grow:1}
@media(max-width:700px){.pay-ui{margin:16px auto}.pay-ui .split,.pay-ui .cards{grid-template-columns:1fr}.pay-ui .top{display:block}.pay-ui .panel{padding:18px}.pay-ui h1{font-size:23px}.pay-ui .actions>*{flex-grow:1;text-align:center}}
'''


def h(value):
    return escape(api.safe_unicode(value or u''), {'"':'&quot;'})


def shell(title, body, color='#1e2f5e'):
    content = body if body.startswith(u'<div class="top">') else u'<section class="panel"><div class="brand">آزمایشگاه تندیس پارس</div><h1>%s</h1>%s</section>' % (h(title),body)
    return u'<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><link rel="stylesheet" href="/++plone++senaite.core.static/css/tppc-vazirmatn.css"><style>body{margin:0;background:#f3f6f9;padding:20px} %s</style></head><body><main class="pay-ui">%s</main></body></html>' % (h(title),CSS,content)


def linked_sample(obj):
    uid = getattr(obj,'created_sample_uid','')
    if not uid: return None
    sample = api.get_object(uid, default=None)
    if sample is None or api.get_portal_type(sample) != 'AnalysisRequest': return None
    return sample


def detail(obj, amount, paid, ref, token):
    base = h(api.get_url(api.get_portal()))
    sample = linked_sample(obj)
    code = h(getattr(obj,'tracking_code','') or api.get_id(obj))
    client = h(getattr(obj,'client_name','') or getattr(obj,'contact_name',''))
    readonly = u'readonly="readonly"' if paid else u''
    invoice = u''
    if sample is not None and api.security.check_permission('senaite.core: Manage Invoices',sample):
        invoice = u'<a class="button" href="%s/invoice">مشاهده و اصلاح فاکتور</a>' % h(api.get_url(sample))
    message = u'مبلغ این درخواست پرداخت شده و قابل تغییر نیست.' if paid else u'مبلغ را به ریال وارد کنید. ذخیرهٔ مبلغ شما را به فهرست پرداخت‌ها برمی‌گرداند.'
    body=u'''<div class="top"><div><div class="brand">آزمایشگاه تندیس پارس · امور مالی</div><h1>مدیریت پرداخت درخواست</h1><p class="muted">مبلغ، وضعیت پرداخت و فاکتور مرتبط در یک پرونده</p></div><a class="button" href="%s/@@payments">بازگشت به پرداخت‌ها</a></div>
    <div class="split"><section class="panel"><h2>مبلغ قابل پرداخت</h2><p class="muted">%s</p><form method="post">
    <input type="hidden" name="_authenticator" value="%s"/><label for="payment-amount">مبلغ نهایی (ریال)</label><input class="amount" id="payment-amount" name="payment_amount" value="%s" inputmode="numeric" autocomplete="off" %s/>
    <p class="muted">معادل <span id="payment-toman">%s</span> تومان</p><div class="actions"><button class="primary" type="submit">ذخیرهٔ مبلغ و بازگشت</button><a class="button" href="%s/@@payments">انصراف</a></div></form>
    <div class="info">تغییر مبلغ، تراکنش در انتظار قبلی را نامعتبر می‌کند. اگر فاکتور قبلاً صادر شده باشد، از «مشاهده و اصلاح فاکتور» PDF آن را به‌روز کنید.</div></section>
    <aside class="panel"><h2>مشخصات درخواست</h2><dl><dt>شمارهٔ درخواست</dt><dd dir="ltr">%s</dd><dt>مشتری</dt><dd>%s</dd><dt>وضعیت</dt><dd><span class="badge %s">%s</span></dd><dt>کد رهگیری</dt><dd dir="ltr">%s</dd></dl><div class="actions">%s</div></aside></div>
    <script>(function(){var e=document.getElementById('payment-amount'),t=document.getElementById('payment-toman');e.addEventListener('input',function(){var s=e.value.replace(/[۰-۹]/g,function(c){return c.charCodeAt(0)-1776}).replace(/[٠-٩]/g,function(c){return c.charCodeAt(0)-1632}).replace(/[,٬]/g,'');t.textContent=/^[0-9]+$/.test(s)?(Number(s)/10).toLocaleString('en-US'):'—'})})();</script>''' % (
        base,message,h(token),amount or '',readonly,u'{:,}'.format(amount//10),base,code,client,u'paid' if paid else u'',u'پرداخت‌شده' if paid else u'پرداخت‌نشده',h(ref) or u'—',invoice)


    from . import tariff
    quote=tariff.preview(obj)
    return body+tariff_panel(quote,amount,paid,token)


def tariff_panel(quote,amount,paid,token):
    result=u'<section class="panel"><h2>هزینهٔ محاسبه‌شدهٔ آزمون‌ها</h2>'
    if quote['amount'] is None:
        return result+u'<p class="info">%s</p></section>' % h(quote['error'])
    from bika.lims.browser.analysisrequest.billing import money
    data=quote['data']
    rates=data.get('vat_rates',[])
    tax_label=(u'مالیات (%s٪)' % money(rates[0])) if len(rates)==1 else (u'مالیات (نرخ‌های متفاوت)' if rates else u'مالیات')
    rows=u''.join(u'<tr><td>%s</td><td class="num">%s</td></tr>' % (h(title),money(price)) for title,price in data['items'])
    result+=u'<p class="muted">%s</p><div class="table-wrap"><table><tr><th>آزمون</th><th>تعرفه (ریال)</th></tr>%s<tr><th>تخفیف</th><td class="num">%s</td></tr><tr><th>%s</th><td class="num">%s</td></tr><tr><th>جمع تعرفه (ریال)</th><th class="num">%s</th></tr></table></div>' % (h(quote['basis']),rows,money(data['discount']),h(tax_label),money(data['tax']),money(quote['amount']))
    if paid:result+=u'<p class="info">این تعرفه فقط برای مقایسه است؛ مبلغ پرداخت‌شده تغییر نمی‌کند.</p>'
    elif amount==quote['amount']:result+=u'<p class="success">مبلغ ثبت‌شده با جمع تعرفه برابر است.</p>'
    else:
        label=u'جایگزینی مبلغ ثبت‌شده با تعرفه آزمون‌ها' if amount else u'ثبت مبلغ از تعرفه آزمون‌ها'
        result+=u'<p class="info">ثبت این مبلغ نیاز به تأیید مدیر دارد. با ثبت، مبلغ قابل پرداخت تعیین می‌شود؛ پیام خودکار برای مشتری ارسال نمی‌شود.</p><form method="post"><input type="hidden" name="_authenticator" value="%s"/><input type="hidden" name="tariff_version" value="%s"/><button class="primary" name="payment_action" value="use_tariff">%s</button></form>' % (h(token),h(quote['version']),label)
    return result+u'</section>'


def dashboard(view):
    rows = view.get_rows(); totals = view.get_totals(rows)
    cards = u''.join(u'<div class="cardx"><span class="muted">%s</span><strong class="num">%s <small>ریال</small></strong></div>' % (label,totals[key]) for label,key in ((u'مجموع مبالغ ثبت‌شده','all'),(u'پرداخت‌شده','paid'),(u'در انتظار پرداخت','pending')))
    suggested=sum(r.get('tariff_amount') or 0 for r in rows if not r['paid'] and not r['amount'])
    cards+=u'<div class="cardx"><span class="muted">تعرفهٔ آمادهٔ تأیید مدیر</span><strong class="num">%s <small>ریال</small></strong></div>' % u'{:,}'.format(suggested)
    items=[]
    for row in rows:
        state = 'paid' if row['paid'] else ('pending' if row['amount'] else 'unset')
        label = u'پرداخت‌شده' if row['paid'] else (u'در انتظار پرداخت' if row['amount'] else u'نیازمند تعیین مبلغ')
        items.append(u'<tr data-payment-state="%s"><td><a href="%s">%s</a></td><td>%s</td><td class="num">%s<small class="muted" style="display:block;direction:rtl;white-space:normal">%s</small></td><td class="num">%s</td><td><span class="badge %s">%s</span></td><td class="num">%s</td><td><a href="%s">%s</a></td></tr>' % (state,h(row['url']),h(row['code']),h(row['who']),h(row.get('tariff_fmt',u'—')),h(row.get('tariff_error','')),h(row['amount_fmt']),u'paid' if row['paid'] else u'',label,h(row['ref']) or u'—',h(row['url']),u'مشاهده و ویرایش' if row['amount'] else u'بررسی و ثبت تعرفه'))
    success = u'<p class="success" role="status">مبلغ ذخیره شد.</p>' if view.request.get('saved') == '1' else u''
    return u'''<section class="pay-ui"><style>%s</style><div class="top"><div><div class="brand">امور مالی آزمایشگاه</div><h1>پرداخت‌ها</h1><p class="muted">هزینهٔ آزمون‌ها از تعرفه محاسبه می‌شود؛ برای قابل پرداخت شدن، مدیر باید مبلغ را ثبت کند.</p></div></div>%s
    <div class="cards">%s</div><section class="panel"><div class="tools"><input id="payment-search" type="search" aria-label="جست‌وجوی مشتری یا شمارهٔ درخواست" placeholder="جست‌وجوی مشتری یا شمارهٔ درخواست"/><select id="payment-filter" aria-label="وضعیت پرداخت"><option value="all">همهٔ درخواست‌ها</option><option value="unset">نیازمند تعیین مبلغ</option><option value="pending">در انتظار پرداخت</option><option value="paid">پرداخت‌شده</option></select></div>
    <div class="table-wrap"><table><thead><tr><th>درخواست</th><th>مشتری</th><th>هزینهٔ آزمون‌ها (ریال)</th><th>مبلغ ثبت‌شده (ریال)</th><th>وضعیت</th><th>کد رهگیری</th><th>عملیات</th></tr></thead><tbody id="payment-rows">%s</tbody></table></div><p id="payment-empty" class="muted" hidden="hidden">درخواستی با این مشخصات پیدا نشد.</p></section>
    <script>(function(){var s=document.getElementById('payment-search'),f=document.getElementById('payment-filter'),rows=document.querySelectorAll('#payment-rows tr');function norm(v){return v.replace(/ي/g,'ی').replace(/ك/g,'ک').toLowerCase()}function run(){var n=0;rows.forEach(function(r){var show=norm(r.textContent).indexOf(norm(s.value))!==-1&&(f.value==='all'||r.getAttribute('data-payment-state')===f.value);r.hidden=!show;if(show)n++});document.getElementById('payment-empty').hidden=n>0}s.addEventListener('input',run);f.addEventListener('change',run);run()})();</script></section>''' % (CSS,success,cards,u''.join(items))
