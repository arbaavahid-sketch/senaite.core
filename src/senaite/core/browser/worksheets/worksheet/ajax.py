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

import plone.protect
from Products.Five.browser import BrowserView

from bika.lims import api
from bika.lims.api.user import get_user
from senaite.core.permissions.worksheet import can_manage_worksheets
from zExceptions import Unauthorized


def check_assignment(context, request):
    """Authorize the mutation, including direct AJAX requests."""
    plone.protect.PostOnly(request)
    plone.protect.CheckAuthenticator(request)
    if not can_manage_worksheets(context):
        raise Unauthorized('Worksheet assignment is not allowed')
    if api.get_workflow_status_of(context) not in ('open', 'to_be_verified'):
        raise Unauthorized('Worksheet assignment is locked')


class SetAnalyst(BrowserView):
    """The Analysis dropdown sets worksheet.Analyst immediately
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        check_assignment(self.context, self.request)
        value = self.request.get("value", "")
        if not value:
            return
        if not get_user(user=value):
            return
        self.context.setAnalyst(value)


class SetInstrument(BrowserView):
    """The Instrument dropdown sets worksheet.Instrument immediately
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        check_assignment(self.context, self.request)
        value = self.request.get("value", "")
        if not value:
            raise Exception("Invalid instrument")

        instrument = api.get_object_by_uid(value, None)
        if not instrument:
            raise Exception("Unable to lookup instrument")

        # set the instrument to the worksheet and analyses
        self.context.setInstrument(instrument, override_analyses=True)
