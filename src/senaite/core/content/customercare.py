# -*- coding: utf-8 -*-
#
# Customer-care container (Tandis / TPPC). Holds customer complaints
# (ISO/IEC 17025 clause 7.9), satisfaction surveys and support requests, and is
# managed from the setup overview.

from bika.lims.interfaces import IDoNotSupportSnapshots
from plone.dexterity.content import Container
from plone.supermodel import model
from senaite.core.interfaces import ICustomerCare
from senaite.core.interfaces import IHideActionsMenu
from zope.interface import implementer


class ICustomerCareSchema(model.Schema):
    """Schema interface
    """


@implementer(ICustomerCare, ICustomerCareSchema, IDoNotSupportSnapshots,
             IHideActionsMenu)
class CustomerCare(Container):
    """A container for customer complaints, surveys and support requests
    """
