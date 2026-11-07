# -*- coding: utf-8 -*-
"""Invoice editor and revision history; all writes are explicit and atomic."""
import hashlib
import json
from DateTime import DateTime
from AccessControl import getSecurityManager, Unauthorized
from plone.protect.authenticator import createToken
from bika.lims import api
from . import billing


def version(sample):
    invoice = sample.getInvoice()
    source = billing.linked_request(sample)
    pdf = invoice.getInvoicePDF() if invoice is not None else None
    payload = [api.get_uid(invoice) if invoice is not None else '',
               getattr(invoice,'billing_revision',0),
               hashlib.sha256(pdf.data).hexdigest() if pdf else '',
               getattr(source,'payment_amount',0) if source is not None else 0,
               bool(getattr(source,'payment_paid',False)) if source is not None else False,
               billing.current_data(sample)]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=True).encode('utf-8')).hexdigest()


def page(view):
    sample, request = view.context, view.request
    invoice = sample.getInvoice()
    source = billing.linked_request(sample)
    current = billing.current_data(sample)
    frozen = getattr(invoice,'billing_snapshot',None) if invoice is not None else None
    data = dict(frozen) if frozen else current
    number = api.get_id(invoice) if invoice is not None else ''
    date = getattr(invoice,'billing_revision_date','') if invoice is not None else ''
    if not date and invoice is not None: date = str(invoice.getInvoiceDate())
    url = billing.h(api.get_url(sample))
    controls = u'<section class="billing"><style>%s</style><div class="actions"><a class="button" href="%s/invoice_print">دریافت PDF فعلی</a><a class="button" href="%s/@@invoices">فاکتورهای مشتری</a>' % (billing.STYLE,url,billing.h(api.get_url(sample.getClient())))
    if source is not None:
        controls += u'<a class="button" href="%s/@@set-payment">مشاهدهٔ پرداخت مرتبط</a>' % billing.h(api.get_url(source))
    controls += u'</div>'
    if getattr(view,'error',None): controls += u'<p role="alert" class="status error">%s</p>' % billing.h(view.error)
    if request.get('saved') == '1': controls += u'<p role="status" class="status">فاکتور و PDF ذخیره شد. نسخهٔ قبلی در سابقه نگهداری می‌شود.</p>'
    if source is not None:
        controls += u'<p class="status">متصل به درخواست پرداخت <b dir="ltr">%s</b> · مبلغ فعلی: <b>%s ریال</b> · %s</p>' % (billing.h(getattr(source,'tracking_code','') or api.get_id(source)),billing.money(getattr(source,'payment_amount',0)),u'پرداخت‌شده' if getattr(source,'payment_paid',False) else u'پرداخت‌نشده')
    else:
        controls += u'<p class="status warning">درخواست پرداختِ مرتبطی برای این نمونه ثبت نشده است؛ مبلغ از تعرفهٔ آزمون‌ها محاسبه می‌شود.</p>'
    legacy = invoice is not None and not frozen
    mismatch = frozen and (frozen['total'] != current['total'] or frozen['currency'] != current['currency'])
    if legacy:
        controls += u'<p class="status warning">PDF قبلی با قالب قدیمی صادر شده است. پیش‌نمایش زیر مبلغ فعلی را نشان می‌دهد؛ برای جایگزینی PDF اشتباه، فرم اصلاح را ذخیره کنید. فایل قبلی در سابقه می‌ماند.</p>'
    elif mismatch:
        controls += u'<p class="status warning">مبلغ فاکتور ذخیره‌شده با مبلغ فعلی درخواست تفاوت دارد. برای هماهنگ‌کردن آن، اصلاحیه ثبت کنید.</p>'
    from senaite.core.browser.payment.views import is_price_manager
    if is_price_manager(sample):
        locked = source is None or bool(getattr(source,'payment_paid',False))
        amount = getattr(source,'payment_amount',0) if source is not None else 0
        controls += u'''<details open="open"><summary>%s</summary><form method="post" class="editor">
        <input type="hidden" name="_authenticator" value="%s"/><input type="hidden" name="billing_version" value="%s"/>
        <input type="hidden" name="billing_save" value="1"/>
        <label for="billing-amount">مبلغ نهایی درخواست (ریال)</label><input id="billing-amount" name="billing_amount" inputmode="numeric" dir="ltr" value="%s" %s/>
        <small>%s</small><label for="billing-description">توضیحات خدمات</label><textarea id="billing-description" name="billing_description" rows="2" maxlength="2000">%s</textarea>
        <label for="billing-note">متن پایین فاکتور</label><textarea id="billing-note" name="billing_note" rows="2" maxlength="2000">%s</textarea>
        <label for="billing-reason">علت اصلاح / توضیح ثبت</label><input id="billing-reason" name="billing_reason" maxlength="500" %s/>
        <button class="primary" type="submit">%s</button></form></details>''' % (
            u'ویرایش و اصلاح فاکتور' if invoice is not None else u'تکمیل و صدور فاکتور',billing.h(createToken()),version(sample),amount if source is not None else '',u'readonly="readonly"' if locked else '',
            u'مبلغ پرداخت‌شده قابل تغییر نیست.' if source is not None and locked else (u'این مبلغ در درخواست پرداخت مرتبط هم ثبت می‌شود.' if source is not None else u'برای تغییر مبلغ، تعرفهٔ آزمون‌ها را اصلاح کنید.'),billing.h(data.get('description','')),billing.h(data.get('note','')),u'required="required"' if invoice is not None else '',u'ثبت اصلاحیه و ساخت PDF جدید' if invoice is not None else u'صدور و ذخیرهٔ فاکتور')
    history = list(getattr(invoice,'billing_history',[])) if invoice is not None else []
    if history:
        controls += u'<details><summary>سابقهٔ نسخه‌های قبلی (%s)</summary><table><tr><th>نسخه</th><th>تاریخ</th><th>علت جایگزینی</th><th>فایل</th></tr>' % len(history)
        for i,item in enumerate(history):
            controls += u'<tr><td>%s</td><td dir="ltr">%s</td><td>%s</td><td><a href="%s/invoice_print?revision=%s">PDF نسخهٔ قبلی</a></td></tr>' % (billing.h(item.get('revision',0)),billing.h(item.get('date','')),billing.h(item.get('reason','')),url,i)
        controls += u'</table></details>'
    controls += u'</section>'
    return controls + billing.render(data,number,date)


def save(view):
    from plone.protect import PostOnly, CheckAuthenticator
    from senaite.core.browser.payment.views import is_price_manager, _digits, change_amount
    import transaction
    PostOnly(view.request); CheckAuthenticator(view.request)
    sample = view.context
    if not billing.allowed(sample) or not is_price_manager(sample): raise Unauthorized('Invoice editing denied')
    form = view.request.form
    if form.get('billing_version') != version(sample):
        view.request.response.setStatus(409)
        view.error = u'اطلاعات در فاصلهٔ ویرایش تغییر کرده است. صفحه را تازه کنید و دوباره بررسی کنید.'
        return False
    invoice = sample.getInvoice()
    reason = api.safe_unicode(form.get('billing_reason','')).strip()
    if invoice is not None and not reason:
        view.request.response.setStatus(400);view.error = u'علت اصلاح فاکتور را بنویسید.';return False
    if len(reason)>500 or any(len(api.safe_unicode(form.get(k,'')))>2000 for k in ('billing_note','billing_description')):
        view.request.response.setStatus(400);view.error=u'متن واردشده بیش از حد طولانی است.';return False
    source = billing.linked_request(sample)
    previous_amount = getattr(source,'payment_amount',0) if source is not None else None
    point = transaction.savepoint(optimistic=True)
    try:
        if source is not None:
            amount = int(_digits(form.get('billing_amount')) or 0)
            if amount <= 0: raise ValueError('positive_amount_required')
            change_amount(source,amount)
        data = billing.current_data(sample)
        data.update(description=api.safe_unicode(form.get('billing_description','')).strip(), note=api.safe_unicode(form.get('billing_note','')).strip())
        history = list(getattr(invoice,'billing_history',[])) if invoice is not None else []
        if invoice is not None:
            stored = invoice.getInvoicePDF()
            if not stored: raise ValueError('missing_original_pdf')
            history.append(dict(revision=getattr(invoice,'billing_revision',0),pdf=stored.data,
                snapshot=getattr(invoice,'billing_snapshot',None),date=getattr(invoice,'billing_revision_date','') or str(invoice.getInvoiceDate()),payment_amount=previous_amount,
                reason=reason,replaced_at=DateTime().ISO8601(),by=getSecurityManager().getUser().getId()))
        else:
            invoice = sample.createInvoice(None)
        revision = int(getattr(invoice,'billing_revision',0))+1
        data['revision'] = revision
        stamp = DateTime().ISO8601()
        pdf = billing.pdf_bytes(data,api.get_id(invoice),stamp)
        if not pdf.startswith(b'%PDF-'): raise ValueError('invalid_pdf')
        invoice.billing_history = history
        invoice.billing_revision = revision
        invoice.billing_snapshot = data
        invoice.billing_revision_date = stamp
        invoice.billing_editor = getSecurityManager().getUser().getId()
        invoice.billing_reason = reason
        invoice.setInvoicePDF(pdf)
    except ValueError as error:
        point.rollback();view.request.response.setStatus(400)
        view.error = u'مبلغ را به ریال و به‌صورت عدد صحیح مثبت وارد کنید. مبلغ پرداخت‌شده قابل تغییر نیست.'
        return False
    except Exception:
        point.rollback()
        raise
    view.request.response.redirect(api.get_url(sample)+'/invoice?saved=1')
    return True
