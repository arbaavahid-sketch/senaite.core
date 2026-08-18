# -*- coding: utf-8 -*-
#
# Sample-intake container (Tandis / TPPC). Holds online test requests submitted
# by customers through the public form (@@sample-request) before they ship
# their physical samples. Reception converts each request into a real Sample
# (AnalysisRequest). Managed from the setup overview.

from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.dexterity.content import Container
from plone.supermodel import model
from senaite.core.interfaces import IHideActionsMenu
from senaite.core.interfaces import ISampleIntake
from zope.interface import implementer


class ISampleIntakeSchema(model.Schema):
    """Schema interface
    """


@implementer(ISampleIntake, ISampleIntakeSchema, IDoNotSupportSnapshots,
             IHideActionsMenu)
class SampleIntake(Container):
    """A container for customer online test requests (sample submissions)
    """
