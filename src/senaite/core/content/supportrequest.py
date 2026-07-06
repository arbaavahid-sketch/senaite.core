# -*- coding: utf-8 -*-
#
# Customer support request (Tandis / TPPC). Lifecycle (received -> in_progress
# -> resolved -> closed) is handled by the senaite_customerrequest_workflow.

from bika.lims import senaiteMessageFactory as _
from plone.supermodel import model
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.content.base import Container
from senaite.core.interfaces import ISupportRequest
from zope import schema
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


SUPPORT_CATEGORIES = SimpleVocabulary([
    SimpleTerm(value=u"technical", token="technical",
               title=_(u"support_category_technical", default=u"Technical")),
    SimpleTerm(value=u"billing", token="billing",
               title=_(u"support_category_billing", default=u"Billing / invoice")),
    SimpleTerm(value=u"sampling", token="sampling",
               title=_(u"support_category_sampling", default=u"Sampling / logistics")),
    SimpleTerm(value=u"general", token="general",
               title=_(u"support_category_general", default=u"General enquiry")),
])


class ISupportRequestSchema(model.Schema):
    """Schema interface
    """

    title = schema.TextLine(
        title=_(u"title_support_title", default=u"Subject"),
        required=True,
    )

    client_name = schema.TextLine(
        title=_(u"title_support_client", default=u"Client"),
        required=False,
    )

    contact_name = schema.TextLine(
        title=_(u"title_support_contact", default=u"Contact person"),
        required=False,
    )

    category = schema.Choice(
        title=_(u"title_support_category", default=u"Category"),
        source=SUPPORT_CATEGORIES,
        required=False,
    )

    received_date = schema.Date(
        title=_(u"title_support_received", default=u"Received date"),
        required=False,
    )

    description = schema.Text(
        title=_(u"title_support_description", default=u"Request description"),
        required=True,
    )

    response = schema.Text(
        title=_(u"title_support_response",
                default=u"Response to customer (shown to the customer)"),
        required=False,
    )


@implementer(ISupportRequest, ISupportRequestSchema)
class SupportRequest(Container):
    """A customer support request
    """
    _catalogs = [SETUP_CATALOG]

    def Title(self):
        return getattr(self, "title", None) or self.getId()
