# -*- coding: utf-8 -*-
"""Client-scoped consolidated invoices with explicit preview and atomic links."""
import hashlib,json
from decimal import Decimal
from DateTime import DateTime
from AccessControl import Unauthorized, getSecurityManager
from plone.protect import PostOnly, CheckAuthenticator
from plone.protect.authenticator import createToken
from six import string_types
from bika.lims import api
from senaite.core.browser.payment.views import is_price_manager
from . import billing, stamp


def url(client,invoice=None):
    result=api.get_url(client)+'/@@invoices'
    return result+('?invoice='+api.get_id(invoice) if invoice is not None else '')


def samples(client):
    return sorted(client.objectValues('AnalysisRequest'),key=lambda obj:api.get_id(obj))


def exclusion(sample):
    if not billing.allowed(sample):return u'دسترسی صدور فاکتور ندارید'
    if sample.getInvoice() is not None:return u'قبلاً فاکتور شده است'
    if sample.getInvoiceExclude():return u'مستثنا از فاکتور'
    if api.get_review_status(sample) in ('cancelled','invalid','rejected'):return u'نمونه لغو، باطل یا رد شده است'
    return u''


def selected(client,raw,invoice=None):
    if isinstance(raw,string_types):raw=[raw]
    raw=list(raw or [])
    if any(not isinstance(uid,string_types) for uid in raw):raise ValueError(u'شناسهٔ نمونه معتبر نیست.')
    if len(raw)<2 or len(raw)>500:raise ValueError(u'بین ۲ تا ۵۰۰ نمونه را انتخاب کنید.')
    if len(set(raw))!=len(raw):raise ValueError(u'یک نمونه بیش از یک بار انتخاب شده است.')
    own=dict((api.get_uid(obj),obj) for obj in samples(client))
    if any(uid not in own for uid in raw):raise ValueError(u'همهٔ نمونه‌ها باید متعلق به همین مشتری باشند.')
    result=sorted([own[uid] for uid in raw],key=lambda obj:api.get_id(obj))
    for obj in result:
        if invoice is None:
            problem=exclusion(obj)
            if problem:raise ValueError(api.safe_unicode(api.get_id(obj))+u': '+problem)
        elif (not billing.allowed(obj) or obj.getInvoice() is None or api.get_uid(obj.getInvoice())!=api.get_uid(invoice)):
            raise ValueError(u'ارتباط نمونه با فاکتور تغییر کرده است؛ اصلاحیه ثبت نشد.')
    return result


def find_invoice(client,identifier):
    if not identifier:return None
    if '/' in identifier:raise ValueError(u'فاکتور معتبر نیست.')
    obj=client._getOb(str(identifier),None)
    if obj is None or api.get_portal_type(obj)!='Invoice' or not getattr(obj,'aggregate_sample_uids',None):
        raise ValueError(u'فاکتور تجمیعی پیدا نشد.')
    if api.get_uid(obj.getClient())!=api.get_uid(client) or not billing.allowed(obj):raise Unauthorized('Invoice access denied')
    return obj


def sample_rows(obj,data):
    """Show priced services separately while preserving the authoritative total."""
    quote=data
    if data['source']=='request':
        if api.get_senaite_setup().getCurrency()!=data['currency']:
            raise ValueError(u'واحد تعرفه‌ها با مبلغ توافق‌شده یکسان نیست؛ تفکیک مبلغ آزمون‌ها ممکن نیست.')
        quote=billing.service_prices(obj)
    rows=[(api.safe_unicode(title),Decimal(str(price)).quantize(Decimal('0.01'))) for title,price in quote['items']]
    tax=Decimal(str(quote.get('tax') or 0)).quantize(Decimal('0.01'))
    discount=Decimal(str(quote.get('discount') or 0)).quantize(Decimal('0.01'))
    if discount:rows.append((u'تخفیف نمونه',-discount))
    if tax:rows.append((u'مالیات نمونه',tax))
    difference=Decimal(data['total']).quantize(Decimal('0.01'))-sum((price for title,price in rows),Decimal('0'))
    if difference:
        rows.append((u'تعدیل مبلغ توافق‌شده' if data['source']=='request' else u'تعدیل گردکردن مبلغ',difference))
    if not rows:rows=[(u'خدمات آزمایشگاهی',Decimal('0'))]
    prefix=u'نمونهٔ '+api.safe_unicode(api.get_id(obj))+u' — '
    return [(prefix+title,str(price)) for title,price in rows]


def combine(objects):
    rows=[];parts=[];total=Decimal('0');currency=None;seen=set()
    for obj in objects:
        data=billing.current_data(obj)
        amount=Decimal(data['total'])
        if not amount.is_finite() or amount<0:raise ValueError(u'مبلغ یکی از نمونه‌ها معتبر نیست.')
        amount=amount.quantize(Decimal('0.01'))
        if currency is not None and currency!=data['currency']:raise ValueError(u'نمونه‌ها باید واحد پول یکسان داشته باشند؛ تبدیل ارز انجام نمی‌شود.')
        currency=data['currency'];total+=amount
        source=billing.linked_request(obj)
        request_uid=api.get_uid(source) if source is not None else ''
        if request_uid and request_uid in seen:raise ValueError(u'یک درخواست پرداخت به چند نمونه وصل است؛ مبلغ دوباره محاسبه نشد.')
        if request_uid:seen.add(request_uid)
        rows.extend(sample_rows(obj,data))
        parts.append(dict(uid=api.get_uid(obj),sample=api.get_id(obj),total=str(amount),currency=currency,
            request_uid=request_uid,payment_paid=bool(getattr(source,'payment_paid',False)) if source is not None else False))
        if len(parts)==1:combined=dict(data)
    combined.update(source='aggregate',items=rows,total=str(total),subtotal=str(total),discount='0',tax='0',
        sample=u'تجمیعی: %s نمونه' % len(parts),aggregate_members=parts,
        description=u'فاکتور تجمیعی %s نمونه؛ هر آزمون در ردیف جداگانه آمده است. مالیات، تخفیف و تعدیل مبلغ توافق‌شده، در صورت وجود، جدا نمایش داده می‌شود.' % len(parts))
    return combined


def version(objects,invoice=None):
    data=combine(objects)
    state=[data,[(api.get_uid(obj),api.get_uid(obj.getInvoice()) if obj.getInvoice() is not None else '') for obj in objects]]
    if invoice is not None:
        pdf=invoice.getInvoicePDF()
        state.extend([getattr(invoice,'billing_revision',0),hashlib.sha256(pdf.data).hexdigest() if pdf else ''])
    return hashlib.sha256(json.dumps(state,ensure_ascii=True,sort_keys=True).encode('utf-8')).hexdigest()


def issue(client,objects,form,existing=None):
    import transaction
    if not is_price_manager(client) or not billing.allowed(client):raise Unauthorized('Consolidated invoice editing denied')
    if existing is not None and set(api.get_uid(obj) for obj in objects)!=set(existing.aggregate_sample_uids):
        raise ValueError(u'فهرست نمونه‌های فاکتور صادرشده قابل تغییر نیست.')
    # Revalidate immediately before taking a snapshot and claiming each sample.
    objects=selected(client,[api.get_uid(obj) for obj in objects],existing)
    if form.get('aggregate_version')!=version(objects,existing):raise ValueError(u'مبلغ یا وضعیت نمونه‌ها تغییر کرده است. پیش‌نمایش را دوباره بررسی کنید.')
    reason=api.safe_unicode(form.get('reason','')).strip()
    note=api.safe_unicode(form.get('note','')).strip()
    if len(note)>2000 or len(reason)>500:raise ValueError(u'متن واردشده بیش از حد طولانی است.')
    if existing is not None and not reason:raise ValueError(u'علت اصلاح فاکتور را بنویسید.')
    point=transaction.savepoint(optimistic=True)
    try:
        data=combine(objects);data['note']=note
        previous=dict(getattr(existing,'billing_snapshot',{}) or {}) if existing is not None else {}
        stamp.apply(data,form,previous)
        history=list(getattr(existing,'billing_history',[])) if existing is not None else []
        if existing is not None:
            stored=existing.getInvoicePDF()
            if not stored:raise ValueError(u'PDF قبلی برای نگهداری در سابقه موجود نیست.')
            history.append(dict(revision=getattr(existing,'billing_revision',1),pdf=stored.data,snapshot=previous,
                date=getattr(existing,'billing_revision_date','') or str(existing.getInvoiceDate()),reason=reason,
                replaced_at=DateTime().ISO8601(),by=getSecurityManager().getUser().getId()))
        invoice=existing if existing is not None else objects[0].createInvoice(None)
        sequence=int(getattr(invoice,'billing_revision',0))+1;data['revision']=sequence
        date=DateTime().ISO8601();pdf=billing.pdf_bytes(data,api.get_id(invoice),date)
        if not pdf.startswith(b'%PDF-'):raise ValueError(u'ساخت PDF کامل نشد.')
        invoice.aggregate_sample_uids=tuple(api.get_uid(obj) for obj in objects)
        invoice.billing_snapshot=data;invoice.billing_history=history;invoice.billing_revision=sequence
        invoice.billing_revision_date=date;invoice.billing_editor=getSecurityManager().getUser().getId();invoice.billing_reason=reason
        invoice.setInvoicePDF(pdf)
        for obj in objects:
            obj.setInvoice(invoice);obj.reindexObject()
        return invoice
    except Exception:
        point.rollback();raise


def dispatch(view):
    view.error=u'';view.preview=None;view.invoice=None
    try:
        view.invoice=find_invoice(view.context,view.request.get('invoice'))
        if view.request.get('REQUEST_METHOD')!='POST':return False
        PostOnly(view.request);CheckAuthenticator(view.request)
        if not is_price_manager(view.context):raise Unauthorized('Consolidated invoice editing denied')
        invoice=view.invoice
        ids=invoice.aggregate_sample_uids if invoice is not None else view.request.form.get('sample_uids',[])
        objects=selected(view.context,ids,invoice)
        if view.request.form.get('aggregate_action')=='preview':
            draft=combine(objects);draft['note']=api.safe_unicode(view.request.form.get('note',''))
            stamp.apply(draft,view.request.form,dict(getattr(invoice,'billing_snapshot',{}) or {}) if invoice is not None else {})
            view.preview=(objects,draft,version(objects,invoice));return False
        if view.request.form.get('aggregate_action') in ('issue','revise'):
            saved=issue(view.context,objects,view.request.form,invoice)
            view.request.response.redirect(url(view.context,saved)+'&saved=1',status=303);return True
        raise ValueError(u'عملیات معتبر نیست.')
    except ValueError as error:
        view.request.response.setStatus(409 if view.request.get('REQUEST_METHOD')=='POST' else 404)
        view.error=api.safe_unicode(error);return False


def form_fields(objects,digest,form):
    result=u'<input type="hidden" name="_authenticator" value="%s"/><input type="hidden" name="aggregate_version" value="%s"/>' % (billing.h(createToken()),digest)
    for obj in objects:result+=u'<input type="hidden" name="sample_uids:list" value="%s"/>' % billing.h(api.get_uid(obj))
    result+=u'<input type="hidden" name="note" value="%s"/><input type="hidden" name="reason" value="%s"/>' % (billing.h(form.get('note','')),billing.h(form.get('reason','')))
    if form.get('billing_stamp')=='1':result+=u'<input type="hidden" name="billing_stamp" value="1"/>'
    return result


def page(view):
    client=view.context;invoice=getattr(view,'invoice',None);h=billing.h
    html=u'<section class="billing"><style>%s</style><h1>فاکتورهای %s</h1><div class="actions"><a class="button" href="%s">فهرست فاکتورها و نمونه‌ها</a><a class="button" href="%s/@@invoice-template">تنظیم قالب فاکتور</a></div>' % (billing.STYLE,h(api.get_title(client)),h(url(client)),h(api.get_url(api.get_portal())))
    if getattr(view,'error',u''):html+=u'<p class="status error" role="alert">%s</p>' % h(view.error)
    if view.request.get('saved')=='1':html+=u'<p class="status" role="status">فاکتور تجمیعی و PDF ذخیره شد.</p>'
    preview=getattr(view,'preview',None)
    if preview:
        objects,data,digest=preview
        html+=u'<h2>پیش‌نمایش فاکتور تجمیعی</h2><p class="note">هر آزمون با شناسهٔ نمونه و مبلغ خودش در ردیفی جدا آمده است. پرداخت هر درخواست از پروندهٔ خودش مدیریت می‌شود.</p>'
        html+=u'<form method="post">%s<button class="primary" name="aggregate_action" value="%s">%s</button></form>' % (form_fields(objects,digest,view.request.form),'revise' if invoice is not None else 'issue',u'ثبت اصلاحیهٔ فاکتور تجمیعی' if invoice is not None else u'صدور فاکتور تجمیعی و PDF')
        html+=u'</section>'+billing.render(data,api.get_id(invoice) if invoice is not None else '',DateTime().Date())
        return html
    if invoice is not None:
        frozen=dict(invoice.billing_snapshot)
        first_uid=invoice.aggregate_sample_uids[0];first=api.get_object(first_uid,default=None)
        pdf_url=api.get_url(invoice) # Native Invoice view serves the already stored PDF.
        if first is not None:pdf_url=api.get_url(first)+'/invoice_print'
        html+=u'<h2>فاکتور تجمیعی %s</h2><div class="actions"><a class="button primary" href="%s">دریافت PDF تجمیعی</a></div>' % (h(api.get_id(invoice)),h(pdf_url))
        html+=u'<table><tr><th>نمونه</th><th>مبلغ ثبت‌شده</th><th>پرداخت مرتبط</th></tr>'
        for part in frozen.get('aggregate_members',[]):
            payment=api.get_object(part['request_uid'],default=None) if part.get('request_uid') else None
            link=u'<a href="%s/@@set-payment">مشاهده و ویرایش مبلغ درخواست</a>' % h(api.get_url(payment)) if payment is not None and is_price_manager(client) else u'—'
            html+=u'<tr><td>%s</td><td class="num">%s %s</td><td>%s</td></tr>' % (h(part['sample']),billing.money(part['total']),h(part['currency']),link)
        html+=u'</table>'
        if is_price_manager(client):
            try:
                objects=selected(client,invoice.aggregate_sample_uids,invoice)
                fresh=combine(objects)
                if fresh['total']!=frozen['total']:html+=u'<p class="status warning">مبلغ فعلی نمونه‌ها با PDF ذخیره‌شده تفاوت دارد؛ برای به‌روزرسانی، پیش‌نمایش اصلاحیه را بررسی کنید.</p>'
                html+=u'<details><summary>اصلاح فاکتور تجمیعی</summary><form method="post" class="editor"><input type="hidden" name="_authenticator" value="%s"/><label>علت اصلاح</label><input name="reason" required="required" maxlength="500"/><label>متن پایین فاکتور</label><textarea name="note" maxlength="2000">%s</textarea>%s<button name="aggregate_action" value="preview">پیش‌نمایش اصلاحیه با مبالغ فعلی</button></form></details>' % (h(createToken()),h(frozen.get('note','')),stamp.controls(frozen))
            except ValueError as error:html+=u'<p class="status error">%s</p>' % h(error)
        history=list(getattr(invoice,'billing_history',[]))
        if history and first is not None:
            html+=u'<details><summary>نسخه‌های قبلی (%s)</summary><ul>' % len(history)
            for i,record in enumerate(history):html+=u'<li><a href="%s/invoice_print?revision=%s">PDF نسخهٔ قبلی %s</a> — %s</li>' % (h(api.get_url(first)),i,i+1,h(record.get('reason','')))
            html+=u'</ul></details>'
        return html+u'</section>'+billing.render(frozen,api.get_id(invoice),getattr(invoice,'billing_revision_date',''))
    # One row per sample, with issued invoice IDs making claims visible.
    can_edit=is_price_manager(client)
    groups=[inv for inv in client.objectValues('Invoice') if getattr(inv,'aggregate_sample_uids',None) and billing.allowed(inv)]
    if groups:
        html+=u'<h2>فاکتورهای تجمیعی صادرشده</h2><table><tr><th>فاکتور</th><th>تعداد نمونه</th><th>جمع مبلغ</th></tr>'
        for inv in groups:
            snap=inv.billing_snapshot
            html+=u'<tr><td><a href="%s">%s</a></td><td>%s</td><td class="num">%s %s</td></tr>' % (h(url(client,inv)),h(api.get_id(inv)),len(inv.aggregate_sample_uids),billing.money(snap['total']),h(snap['currency']))
        html+=u'</table>'
    if can_edit:html+=u'<h2>صدور فاکتور تجمیعی</h2><p>حداقل دو نمونهٔ بدون فاکتور را انتخاب کنید؛ سپس جمع مبالغ را در پیش‌نمایش بررسی کنید.</p><form method="post"><input type="hidden" name="_authenticator" value="%s"/><div class="actions"><button type="button" id="aggregate-select-all">انتخاب همهٔ نمونه‌های بدون فاکتور</button><button type="button" id="aggregate-clear">پاک‌کردن انتخاب‌ها</button></div>' % h(createToken())
    html+=u'<div style="overflow-x:auto"><table><thead><tr><th>انتخاب</th><th>نمونه</th><th>فاکتور</th><th>عملیات / وضعیت</th></tr></thead><tbody>'
    for obj in samples(client):
        if not billing.allowed(obj):continue
        inv=obj.getInvoice();problem=exclusion(obj)
        choose=u'<input type="checkbox" style="width:auto;display:inline" name="sample_uids:list" value="%s" aria-label="انتخاب نمونه %s"/>' % (h(api.get_uid(obj)),h(api.get_id(obj))) if can_edit and not problem else u'—'
        target=url(client,inv) if inv is not None and getattr(inv,'aggregate_sample_uids',None) else api.get_url(obj)+'/invoice'
        name=api.get_id(inv) if inv is not None else u'صادر نشده'
        html+=u'<tr><td>%s</td><td><a href="%s">%s</a></td><td><a href="%s">%s</a></td><td>%s</td></tr>' % (choose,h(target),h(api.get_id(obj)),h(target),h(name),h(problem) or u'آمادهٔ انتخاب')
    html+=u'</tbody></table></div>'
    if can_edit:html+=u'<label>متن پایین فاکتور</label><textarea name="note" maxlength="2000"></textarea>%s<button class="primary" name="aggregate_action" value="preview">پیش‌نمایش فاکتور تجمیعی</button></form><script>(function(){function select(value){document.querySelectorAll(\'input[name="sample_uids:list"]\').forEach(function(c){c.checked=value})}document.getElementById("aggregate-select-all").addEventListener("click",function(){select(true)});document.getElementById("aggregate-clear").addEventListener("click",function(){select(false)})})();</script>' % stamp.controls({})
    return html+u'</section>'
