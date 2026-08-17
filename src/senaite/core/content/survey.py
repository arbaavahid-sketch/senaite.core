# -*- coding: utf-8 -*-
#
# Customer satisfaction survey response (Tandis / TPPC). Records customer
# feedback after report delivery. Uses the one-state workflow (submitted).

from bika.lims import senaiteMessageFactory as _
from plone.autoform import directives as form
from plone.supermodel import model
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.content.base import Container
from senaite.core.interfaces import ISurvey
from zope import schema
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


# 1..5 rating scale (5 = best). Stored as the integer token.
RATINGS = SimpleVocabulary([
    SimpleTerm(value=5, token="5", title=_(u"rating_5", default=u"5 - Excellent")),
    SimpleTerm(value=4, token="4", title=_(u"rating_4", default=u"4 - Good")),
    SimpleTerm(value=3, token="3", title=_(u"rating_3", default=u"3 - Average")),
    SimpleTerm(value=2, token="2", title=_(u"rating_2", default=u"2 - Poor")),
    SimpleTerm(value=1, token="1", title=_(u"rating_1", default=u"1 - Very poor")),
])


class ISurveySchema(model.Schema):
    """Schema interface
    """

    title = schema.TextLine(
        title=_(u"title_survey_title", default=u"Subject"),
        required=True,
    )

    client_name = schema.TextLine(
        title=_(u"title_survey_client", default=u"Client"),
        required=False,
    )

    contact_name = schema.TextLine(
        title=_(u"title_survey_contact", default=u"Contact person"),
        required=False,
    )

    related_report = schema.TextLine(
        title=_(u"title_survey_report", default=u"Related report / sample ID"),
        required=False,
    )

    survey_date = schema.Date(
        title=_(u"title_survey_date", default=u"Survey date"),
        required=False,
    )

    rating_overall = schema.Choice(
        title=_(u"title_survey_overall", default=u"Overall satisfaction"),
        source=RATINGS,
        required=True,
    )

    rating_timeliness = schema.Choice(
        title=_(u"title_survey_timeliness", default=u"Timeliness"),
        source=RATINGS,
        required=False,
    )

    rating_quality = schema.Choice(
        title=_(u"title_survey_quality", default=u"Quality of results"),
        source=RATINGS,
        required=False,
    )

    rating_communication = schema.Choice(
        title=_(u"title_survey_communication", default=u"Communication"),
        source=RATINGS,
        required=False,
    )

    comments = schema.Text(
        title=_(u"title_survey_comments", default=u"Comments"),
        required=False,
    )

    form.omitted("access_token")
    access_token = schema.TextLine(
        title=_(u"title_access_token", default=u"Access token"),
        required=False,
    )


@implementer(ISurvey, ISurveySchema)
class Survey(Container):
    """A customer satisfaction survey response
    """
    _catalogs = [SETUP_CATALOG]

    def Title(self):
        return getattr(self, "title", None) or self.getId()
