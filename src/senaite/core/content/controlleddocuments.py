# -*- coding: utf-8 -*-
#
# Controlled documents container (Tandis / TPPC, ISO/IEC 17025 clause 8.3).
# Holds the ControlledDocument items and is managed from the setup overview.

from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.dexterity.content import Container
from plone.supermodel import model
from senaite.core.interfaces import IControlledDocuments
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer


class IControlledDocumentsSchema(model.Schema):
    """Schema interface
    """


@implementer(IControlledDocuments, IControlledDocumentsSchema,
             IDoNotSupportSnapshots, IHideActionsMenu)
class ControlledDocuments(Container):
    """A container for controlled documents
    """
