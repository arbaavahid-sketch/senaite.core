# -*- coding: utf-8 -*-
"""Read-only tariff previews; a manager must explicitly save a payment quote."""
import hashlib,json
from decimal import Decimal,InvalidOperation
from AccessControl import Unauthorized
from bika.lims import api
from bika.lims.browser.analysisrequest import billing

def preview(obj):
    from .views import is_price_manager
    if not is_price_manager(obj):raise Unauthorized('Payment tariff access denied')
    try:
        setup=api.get_senaite_setup()
        if setup.getCurrency()!='IRR':raise ValueError(u'واحد تعرفه‌ها ریال نیست؛ مبلغ پرداخت باید دستی تعیین شود.')
        uid=getattr(obj,'created_sample_uid','')
        if uid:
            sample=api.get_object(uid,default=None)
            if sample is None or api.get_portal_type(sample)!='AnalysisRequest':raise ValueError(u'نمونهٔ مرتبط پیدا نشد.')
            if not billing.allowed(sample):raise Unauthorized('Sample tariff access denied')
            linked=billing.linked_request(sample)
            if linked is None or api.get_uid(linked)!=api.get_uid(obj):raise ValueError(u'ارتباط درخواست و نمونه معتبر نیست.')
            if api.get_review_status(sample) in ('cancelled','invalid','rejected'):raise ValueError(u'نمونه لغو، باطل یا رد شده است.')
            data=billing.service_prices(sample)
            basis=u'آزمون‌های نمونهٔ '+api.safe_unicode(api.get_id(sample))
        else:
            ids=list(getattr(obj,'requested_service_uids',[]) or [])
            if not ids:raise ValueError(u'برای این درخواست هنوز آزمونی انتخاب نشده است.')
            if len(ids)>500 or len(set(ids))!=len(ids):raise ValueError(u'فهرست آزمون‌های درخواست معتبر نیست.')
            rows=[];subtotal=Decimal('0');tax=Decimal('0')
            for service_uid in ids:
                service=api.get_object(service_uid,default=None)
                if service is None or api.get_portal_type(service)!='AnalysisService':raise ValueError(u'یکی از آزمون‌های درخواست پیدا نشد.')
                if not api.is_active(service):raise ValueError(u'یکی از آزمون‌های درخواستی غیرفعال است؛ انتخاب آزمون‌ها را بررسی کنید.')
                price=Decimal(str(service.getPrice() or 0));rate=Decimal(str(service.getVAT() or 0))
                if not price.is_finite() or price<0 or not rate.is_finite() or rate<0:raise ValueError(u'قیمت یا مالیات آزمون معتبر نیست.')
                rows.append((api.safe_unicode(service.Title()),str(price)))
                subtotal+=price;tax+=price*rate/100
            data=dict(items=rows,subtotal=str(subtotal),tax=str(tax),discount='0',total=str(subtotal+tax))
            basis=u'تعرفهٔ آزمون‌های درخواستی؛ پیش از ایجاد نمونه'
        if not data['items']:raise ValueError(u'آزمون قابل محاسبه‌ای ثبت نشده است.')
        if any(Decimal(str(p))<=0 for t,p in data['items']):raise ValueError(u'قیمت بعضی آزمون‌ها هنوز ثبت نشده یا صفر است؛ مبلغ را بررسی کنید.')
        amount=Decimal(data['total'])
        if not amount.is_finite() or amount<0 or amount!=amount.to_integral_value():raise ValueError(u'جمع تعرفه عدد صحیح ریالی نیست؛ مبلغ را دستی تعیین کنید.')
        if amount>10**15:raise ValueError(u'جمع تعرفه بیش از حد مجاز است.')
        state=[api.get_uid(obj),uid,data,getattr(obj,'payment_amount',0),bool(getattr(obj,'payment_paid',False))]
        version=hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=True).encode('utf-8')).hexdigest()
        return dict(amount=int(amount),data=data,basis=basis,version=version,error=u'')
    except (ValueError,InvalidOperation) as error:
        # Python 2 str(ValueError(unicode)) loses Persian messages in safe_unicode.
        message=api.safe_unicode(error.args[0] if error.args else u'تعرفه قابل محاسبه نیست.') or u'تعرفه قابل محاسبه نیست.'
        return dict(amount=None,data=None,basis=u'',version='',error=message)
