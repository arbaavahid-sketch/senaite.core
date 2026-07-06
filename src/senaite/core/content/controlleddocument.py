# -*- coding: utf-8 -*-
#
# Controlled document (Tandis / TPPC, ISO/IEC 17025 clause 8.3 - control of
# documents). A single controlled record: SOP, method, form, checklist,
# template, certificate, safety data sheet, or generic controlled record.
# The approval state (draft / effective / obsolete) is handled by the
# senaite_controlleddocument_workflow, not by a schema field.

from bika.lims import senaiteMessageFactory as _
from plone.namedfile.field import NamedBlobFile
from plone.supermodel import model
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.content.base import Container
from senaite.core.interfaces import IControlledDocument
from zope import schema
from zope.interface import implementer
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


DOCUMENT_TYPES = SimpleVocabulary([
    SimpleTerm(value=u"sop", token="sop", title=u"Procedure (SOP)"),
    SimpleTerm(value=u"method", token="method", title=u"Test method"),
    SimpleTerm(value=u"form", token="form", title=u"Form"),
    SimpleTerm(value=u"checklist", token="checklist", title=u"Checklist"),
    SimpleTerm(value=u"template", token="template", title=u"Template"),
    SimpleTerm(value=u"certificate", token="certificate", title=u"Certificate"),
    SimpleTerm(value=u"sds", token="sds", title=u"Safety data sheet (SDS)"),
    SimpleTerm(value=u"record", token="record", title=u"Controlled record"),
])


class IControlledDocumentSchema(model.Schema):
    """Schema interface
    """

    document_id = schema.TextLine(
        title=_(u"title_controlleddocument_document_id", default=u"Document code"),
        description=_(u"description_controlleddocument_document_id",
                      default=u"Unique controlled-document code, e.g. ST75, QP-01"),
        required=True,
    )

    title = schema.TextLine(
        title=_(u"title_controlleddocument_title", default=u"Title"),
        required=True,
    )

    document_type = schema.Choice(
        title=_(u"title_controlleddocument_type", default=u"Document type"),
        source=DOCUMENT_TYPES,
        required=True,
    )

    version = schema.TextLine(
        title=_(u"title_controlleddocument_version", default=u"Version"),
        required=False,
    )

    document_owner = schema.TextLine(
        title=_(u"title_controlleddocument_owner", default=u"Owner / responsible"),
        required=False,
    )

    department = schema.TextLine(
        title=_(u"title_controlleddocument_department", default=u"Department"),
        required=False,
    )

    effective_date = schema.Date(
        title=_(u"title_controlleddocument_effective_date",
                default=u"Effective date"),
        required=False,
    )

    review_date = schema.Date(
        title=_(u"title_controlleddocument_review_date",
                default=u"Next review date"),
        description=_(u"description_controlleddocument_review_date",
                      default=u"Date on which this document must be reviewed again"),
        required=False,
    )

    related_methods = schema.Text(
        title=_(u"title_controlleddocument_related_methods",
                default=u"Related methods / analysis services"),
        description=_(u"description_controlleddocument_related_methods",
                      default=u"Method codes or analysis service keywords this "
                              u"document applies to (one per line)"),
        required=False,
    )

    file = NamedBlobFile(
        title=_(u"title_controlleddocument_file", default=u"Document file"),
        required=False,
    )

    description = schema.Text(
        title=_(u"title_controlleddocument_description", default=u"Notes"),
        required=False,
    )


@implementer(IControlledDocument, IControlledDocumentSchema)
class ControlledDocument(Container):
    """A controlled document
    """
    # Catalogs where this type will be catalogued
    _catalogs = [SETUP_CATALOG]

    def Title(self):
        title = getattr(self, "title", None) or self.getId()
        code = getattr(self, "document_id", None)
        try:
            if code:
                return u"%s - %s" % (code, title)
        except Exception:
            pass
        return title
