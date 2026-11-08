# -*- coding: utf-8 -*-
"""Freeze available organisation details without inventing tax/quantity data."""
from bika.lims import api


def party(obj):
    def field(name):
        method=getattr(obj,name,None) if obj is not None else None
        return method() if callable(method) else None
    address=field('getPhysicalAddress') or field('getPostalAddress') or {}
    if not isinstance(address,dict):address={}
    parts=[api.safe_unicode(address.get(k,'') or '').strip() for k in ('state','district','city','address')]
    return dict(address=u'، '.join(v for i,v in enumerate(parts) if v and v not in parts[:i]),
        postal_code=api.safe_unicode(address.get('zip','') or address.get('postal_code','') or ''),
        phone=api.safe_unicode(field('getPhone') or ''),tax_id=api.safe_unicode(field('getTaxNumber') or ''))


def snapshot(sample):
    seller=party(getattr(api.get_senaite_setup(),'laboratory',None));buyer=party(sample.getClient())
    result={}
    for prefix,values in (('seller',seller),('buyer',buyer)):
        for key,value in values.items():result[prefix+'_'+key]=value
    return result
