# -*- coding: utf-8 -*-
import io
import os
from bika.lims.api import safe_unicode

class PublicCustomerMixin(object):
    def get_request_logo(self):
        from plone.registry.interfaces import IRegistry
        from Products.CMFPlone.interfaces import ISiteSchema
        from Products.CMFPlone.utils import getSiteLogo
        from zope.component import getUtility
        from bika.lims import api
        settings = getUtility(IRegistry).forInterface(ISiteSchema, prefix='plone', check=False)
        if getattr(settings, 'site_logo', False):
            return getSiteLogo()
        return api.get_url(api.get_portal()) + '/++plone++senaite.core.static/images/senaite-site-logo.png'

    def get_customer_styles(self):
        with io.open(os.path.join(os.path.dirname(__file__), 'customer.css'), encoding='utf-8') as source:
            return source.read()

    def get_field_value(self, name, default=u''):
        value = self.request.form.get(name, default)
        return safe_unicode(value)[:10000 if name == 'description' else 512] if isinstance(value, basestring) else default

    def get_kind(self):
        kind = self.get_field_value('kind', u'complaint')
        return kind if kind in ('complaint', 'support', 'survey') else u'complaint'
