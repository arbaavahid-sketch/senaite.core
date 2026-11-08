# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2025 by it's authors.
# Some rights reserved, see README and LICENSE.

from bika.lims import _
from bika.lims import api
from senaite.core.api.currency import get_currency_symbol as currency_symbol
from bika.lims.browser import BrowserView
from bika.lims.interfaces import IAnalysis
from bika.lims.interfaces import IAnalysisProfile
from bika.lims.interfaces import IInvoiceView
from bika.lims.utils import createPdf
from plone.memoize import view
from plone.protect import PostOnly, CheckAuthenticator
from plone.protect.authenticator import createToken
from AccessControl import Unauthorized
import transaction
from bika.lims.browser.analysisrequest import billing, editor, aggregate
from Products.CMFPlone.i18nl10n import ulocalized_time
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.app.supermodel.model import SuperModel
from zope.interface import alsoProvides
from zope.interface import implements


class InvoiceView(BrowserView):
    """Analyses Invoice View
    """
    implements(IInvoiceView)

    template = ViewPageTemplateFile("templates/invoice.pt")
    print_template = ViewPageTemplateFile("templates/invoice_print.pt")
    def content(self):
        return editor.page(self)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        if not billing.allowed(self.context):
            raise Unauthorized('Invoice access denied')
        invoice=self.context.getInvoice()
        if invoice is not None and getattr(invoice,'aggregate_sample_uids',None):
            return self.request.response.redirect(aggregate.url(self.context.getClient(),invoice),status=303)
        if self.request.get('REQUEST_METHOD') == 'POST' and self.request.form.get('billing_save'):
            if editor.save(self):
                return u''
        self.request['verified'] = 0
        return self.template()

    @property
    def sample(self):
        """Returns a supermodel of the sample
        """
        return SuperModel(self.context)

    def to_localized_time(self, date, **kw):
        """Converts the given date to a localized time string
        """
        if date is None:
            return ""
        # default options
        options = {
            "long_format": True,
            "time_only": False,
            "context": api.get_portal(),
            "request": api.get_request(),
            "domain": "senaite.core",
        }
        options.update(kw)
        return ulocalized_time(date, **options)

    @view.memoize
    def get_currency_symbol(self):
        """Return the configured display label without converting amounts."""
        setup = api.get_senaite_setup()
        return currency_symbol(setup.getCurrency(), self.request.get("LANGUAGE", "en"))

    @view.memoize
    def get_decimal_mark(self):
        """Returns the decimal mark
        """
        setup = api.get_senaite_setup()
        return setup.getDecimalMark()

    def format_price(self, price):
        """Formats the price with the set decimal mark and currency
        """
        # ensure we have a float
        price = api.to_float(price, default=0.0)
        dm = self.get_decimal_mark()
        cur = self.get_currency_symbol()
        price = "%s %.2f" % (cur, price)
        return price.replace(".", dm)

    def get_billable_items(self):
        """Return a list of billable items
        """
        items = []
        for obj in self.context.getBillableItems():
            if self.is_profile(obj):
                items.append({
                    "obj": obj,
                    "title": obj.Title(),
                    "vat": obj.getAnalysisProfileVAT(),
                    "price": self.format_price(obj.getAnalysisProfilePrice()),
                })
            if self.is_analysis(obj):
                items.append({
                    "obj": obj,
                    "title": obj.Title(),
                    "vat": obj.getVAT(),
                    "price": self.format_price(obj.getPrice()),
                })
        return items

    def is_profile(self, obj):
        """Checks if the object is a profile
        """
        return IAnalysisProfile.providedBy(obj)

    def is_analysis(self, obj):
        """Checks if the object is an analysis
        """
        return IAnalysis.providedBy(obj)

    def add_status_message(self, message, level="info"):
        """Set a portal status message
        """
        return self.context.plone_utils.addPortalMessage(message, level)


class InvoicePrintView(InvoiceView):
    def __call__(self):
        if not billing.allowed(self.context):
            raise Unauthorized('Invoice access denied')
        invoice = self.context.getInvoice()
        stored = invoice.getInvoicePDF() if invoice is not None else None
        if self.request.get('revision') is not None:
            try:
                index = int(self.request.get('revision'))
                history = list(getattr(invoice,'billing_history',[]))
                if index < 0 or index >= len(history): raise ValueError('revision')
                return self.download(history[index]['pdf'], '{}-revision-{}.pdf'.format(api.get_id(self.context),index))
            except (ValueError, TypeError, IndexError):
                self.request.response.setStatus(404)
                return b'Revision not found'
        pdf = stored.data if stored else self.create_pdf()
        return self.download(pdf, '{}-invoice.pdf'.format(api.get_id(invoice) if invoice is not None and getattr(invoice,'aggregate_sample_uids',None) else api.get_id(self.context)))

    def create_pdf(self):
        invoice = self.context.getInvoice()
        number = api.get_id(invoice) if invoice is not None else ''
        date = str(invoice.getInvoiceDate()) if invoice is not None else ''
        return billing.pdf_bytes(billing.data_for(self.context), number, date)

    def download(self, data, filename, content_type='application/pdf'):
        response = self.request.response
        response.setHeader('Content-Disposition', 'attachment; filename="%s"' % filename)
        response.setHeader('Content-Type', content_type)
        response.setHeader('Content-Length', len(data))
        response.setHeader('Cache-Control', 'no-store')
        return data


class InvoiceCreate(InvoicePrintView):
    def __call__(self):
        PostOnly(self.request)
        CheckAuthenticator(self.request)
        if not billing.allowed(self.context):
            raise Unauthorized('Invoice access denied')
        sample = self.context
        existing = sample.getInvoice()
        if existing is not None:
            # Repeated submissions must never replace an issued PDF/date.
            return self.request.response.redirect(api.get_url(sample) + '/invoice')
        data = billing.current_data(sample)
        savepoint = transaction.savepoint(optimistic=True)
        try:
            invoice = sample.createInvoice(None)
            invoice.billing_snapshot = data
            pdf = billing.pdf_bytes(data, api.get_id(invoice), str(invoice.getInvoiceDate()))
            if not pdf.startswith(b'%PDF-'):
                raise ValueError('Invalid PDF result')
            invoice.setInvoicePDF(pdf)
        except Exception:
            savepoint.rollback()
            raise
        return self.request.response.redirect(api.get_url(sample) + '/invoice')


class ClientInvoicesView(BrowserView):
    template=ViewPageTemplateFile('templates/invoice.pt')

    def __call__(self):
        if not billing.allowed(self.context):
            raise Unauthorized('Invoice access denied')
        if aggregate.dispatch(self):
            return u''
        return self.template()

    def content(self):
        return aggregate.page(self)
