# -*- coding: utf-8 -*-
#
# Customer complaint (Tandis / TPPC, ISO/IEC 17025 clause 7.9 - complaints).
# Lifecycle (received -> in_progress -> resolved -> closed) is handled by the
# senaite_customerrequest_workflow, not by a schema field.

from bika.lims import senaiteMessageFactory as _
from plone.supermodel import model
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.content.base import Container
from senaite.core.interfaces import IComplaint
from zope import schema
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


COMPLAINT_CATEGORIES = SimpleVocabulary([
    SimpleTerm(value=u"result", token="result",
               title=_(u"complaint_category_result", default=u"Analysis result")),
    SimpleTerm(value=u"turnaround", token="turnaround",
               title=_(u"complaint_category_turnaround", default=u"Turnaround / delay")),
    SimpleTerm(value=u"report", token="report",
               title=_(u"complaint_category_report", default=u"Report error")),
    SimpleTerm(value=u"service", token="service",
               title=_(u"complaint_category_service", default=u"Service / staff")),
    SimpleTerm(value=u"sampling", token="sampling",
               title=_(u"complaint_category_sampling", default=u"Sampling")),
    SimpleTerm(value=u"other", token="other",
               title=_(u"complaint_category_other", default=u"Other")),
])

SEVERITIES = SimpleVocabulary([
    SimpleTerm(value=u"low", token="low",
               title=_(u"severity_low", default=u"Low")),
    SimpleTerm(value=u"medium", token="medium",
               title=_(u"severity_medium", default=u"Medium")),
    SimpleTerm(value=u"high", token="high",
               title=_(u"severity_high", default=u"High")),
])


class IComplaintSchema(model.Schema):
    """Schema interface
    """

    title = schema.TextLine(
        title=_(u"title_complaint_title", default=u"Subject"),
        required=True,
    )

    client_name = schema.TextLine(
        title=_(u"title_complaint_client", default=u"Client"),
        required=False,
    )

    contact_name = schema.TextLine(
        title=_(u"title_complaint_contact", default=u"Contact person"),
        required=False,
    )

    related_sample = schema.TextLine(
        title=_(u"title_complaint_sample", default=u"Related sample ID"),
        required=False,
    )

    category = schema.Choice(
        title=_(u"title_complaint_category", default=u"Category"),
        source=COMPLAINT_CATEGORIES,
        required=False,
    )

    severity = schema.Choice(
        title=_(u"title_complaint_severity", default=u"Severity"),
        source=SEVERITIES,
        required=False,
    )

    received_date = schema.Date(
        title=_(u"title_complaint_received", default=u"Received date"),
        required=False,
    )

    description = schema.Text(
        title=_(u"title_complaint_description", default=u"Complaint description"),
        required=True,
    )

    investigation = schema.Text(
        title=_(u"title_complaint_investigation",
                default=u"Investigation (internal)"),
        required=False,
    )

    resolution = schema.Text(
        title=_(u"title_complaint_resolution",
                default=u"Resolution / corrective action (internal)"),
        required=False,
    )


@implementer(IComplaint, IComplaintSchema)
class Complaint(Container):
    """A customer complaint
    """
    _catalogs = [SETUP_CATALOG]

    def Title(self):
        return getattr(self, "title", None) or self.getId()
