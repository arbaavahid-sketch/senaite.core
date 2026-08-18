# -*- coding: utf-8 -*-
#
# Customer online test request / sample submission (Tandis / TPPC). A customer
# fills the public form (@@sample-request) describing the sample they will send
# and the tests they want, and receives a tracking code + link. Reception then
# converts the request into a real Sample (AnalysisRequest). Lifecycle
# (received -> in_progress -> resolved -> closed) is handled by the
# senaite_customerrequest_workflow, so the auto-email-on-close notification is
# shared with complaints/support requests.

from bika.lims import senaiteMessageFactory as _
from plone.autoform import directives as form
from plone.supermodel import model
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.content.base import Container
from senaite.core.interfaces import ISampleRequest
from zope import schema
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


PRIORITIES = SimpleVocabulary([
    SimpleTerm(value=u"normal", token="normal",
               title=_(u"samplerequest_priority_normal", default=u"Normal")),
    SimpleTerm(value=u"urgent", token="urgent",
               title=_(u"samplerequest_priority_urgent", default=u"Urgent")),
])

REPORT_DELIVERY = SimpleVocabulary([
    SimpleTerm(value=u"email", token="email",
               title=_(u"samplerequest_delivery_email", default=u"Email")),
    SimpleTerm(value=u"inperson", token="inperson",
               title=_(u"samplerequest_delivery_inperson",
                       default=u"In person")),
    SimpleTerm(value=u"post", token="post",
               title=_(u"samplerequest_delivery_post", default=u"Post")),
])


class ISampleRequestSchema(model.Schema):
    """Schema interface
    """

    title = schema.TextLine(
        title=_(u"title_samplerequest_title", default=u"Subject / purpose"),
        required=True,
    )

    client_name = schema.TextLine(
        title=_(u"title_samplerequest_client", default=u"Client / company"),
        required=False,
    )

    contact_name = schema.TextLine(
        title=_(u"title_samplerequest_contact", default=u"Contact person"),
        required=False,
    )

    contact_email = schema.TextLine(
        title=_(u"title_contact_email", default=u"Contact email"),
        description=_(u"desc_contact_email",
                      default=u"The answer link is emailed here when the "
                              u"request is closed."),
        required=False,
    )

    contact_phone = schema.TextLine(
        title=_(u"title_contact_phone", default=u"Contact phone"),
        required=False,
    )

    address = schema.Text(
        title=_(u"title_samplerequest_address", default=u"Address"),
        required=False,
    )

    economic_code = schema.TextLine(
        title=_(u"title_samplerequest_economic_code",
                default=u"National ID / economic code (for invoicing)"),
        required=False,
    )

    sample_type = schema.TextLine(
        title=_(u"title_samplerequest_sampletype",
                default=u"Sample type (as described by the customer)"),
        required=False,
    )

    sampling_date = schema.Date(
        title=_(u"title_samplerequest_sampling_date",
                default=u"Sampling date"),
        required=False,
    )

    sampling_point = schema.TextLine(
        title=_(u"title_samplerequest_sampling_point",
                default=u"Sampling point / source"),
        required=False,
    )

    sample_condition = schema.TextLine(
        title=_(u"title_samplerequest_condition",
                default=u"Sample condition on receipt"),
        required=False,
    )

    priority = schema.Choice(
        title=_(u"title_samplerequest_priority", default=u"Priority"),
        source=PRIORITIES,
        required=False,
    )

    report_delivery = schema.Choice(
        title=_(u"title_samplerequest_delivery",
                default=u"Preferred report delivery"),
        source=REPORT_DELIVERY,
        required=False,
    )

    requested_tests = schema.Text(
        title=_(u"title_samplerequest_tests",
                default=u"Requested tests (as described by the customer)"),
        required=False,
    )

    sample_description = schema.Text(
        title=_(u"title_samplerequest_description",
                default=u"Sample description / notes"),
        required=False,
    )

    quantity = schema.TextLine(
        title=_(u"title_samplerequest_quantity",
                default=u"Number / quantity of samples"),
        required=False,
    )

    lab_note = schema.Text(
        title=_(u"title_samplerequest_labnote",
                default=u"Internal note (not shown to the customer)"),
        required=False,
    )

    response = schema.Text(
        title=_(u"title_samplerequest_response",
                default=u"Response to customer (shown to the customer)"),
        required=False,
    )

    # Id of the Sample (AnalysisRequest) created from this request, if any.
    created_sample_id = schema.TextLine(
        title=_(u"title_samplerequest_created_sample",
                default=u"Registered Sample ID"),
        required=False,
    )

    form.omitted("access_token")
    access_token = schema.TextLine(
        title=_(u"title_access_token", default=u"Access token"),
        required=False,
    )


@implementer(ISampleRequest, ISampleRequestSchema)
class SampleRequest(Container):
    """A customer online test request (sample submission)
    """
    _catalogs = [SETUP_CATALOG]

    def Title(self):
        return getattr(self, "title", None) or self.getId()
