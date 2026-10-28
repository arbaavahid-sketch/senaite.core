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

from bika.lims import api
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from senaite.core.api.instrumentcertification import get_certificate_status
from xml.sax.saxutils import escape


class InstrumentQCFailuresViewlet(ViewletBase):
    """ Print a viewlet showing failed instruments
    """
    index = ViewPageTemplateFile("templates/instrument_qc_failures_viewlet.pt")

    def __init__(self, context, request, view, manager=None):
        super(InstrumentQCFailuresViewlet, self).__init__(
            context, request, view, manager=manager)
        self.nr_failed = 0
        self.failed = {
            "out-of-date": [],
            "qc-fail": [],
            "next-test": [],
            "validation": [],
            "calibration": [],
            "no-certificate": [],
            "certificate-unknown": [],
            "certificate-future": [],
        }

    def get_failed_instruments(self):
        """Find invalid instruments

        - instruments who have failed QC tests
        - instruments whose certificate is out of date
        - instruments which are disposed until next calibration test

        Return a dictionary with all info about expired/invalid instruments
        """
        self.nr_failed = 0
        for key in self.failed:
            self.failed[key] = []
        bsc = api.get_tool("senaite_catalog_setup")
        insts = bsc(portal_type="Instrument", is_active=True)
        for i in insts:
            i = i.getObject()
            instr = {
                'uid': i.UID(),
                'title': i.Title(),
            }
            certificate_status = get_certificate_status(i)['status']
            if i.isValidationInProgress():
                instr['link'] = self._instrument_link(i, 'validations')
                self.nr_failed += 1
                self.failed['validation'].append(instr)
            elif i.isCalibrationInProgress():
                instr['link'] = self._instrument_link(i, 'calibrations')
                self.nr_failed += 1
                self.failed['calibration'].append(instr)
            elif certificate_status in ('expired', 'none', 'unknown', 'future'):
                instr['link'] = self._instrument_link(i, 'certifications')
                self.nr_failed += 1
                category = {'expired': 'out-of-date', 'none': 'no-certificate',
                            'unknown': 'certificate-unknown', 'future': 'certificate-future'}[certificate_status]
                self.failed[category].append(instr)
            elif not i.isQCValid():
                instr['link'] = self._instrument_link(i, 'referenceanalyses')
                self.nr_failed += 1
                self.failed['qc-fail'].append(instr)
            elif i.getDisposeUntilNextCalibrationTest():
                instr['link'] = self._instrument_link(i, 'referenceanalyses')
                self.nr_failed += 1
                self.failed['next-test'].append(instr)

    def _instrument_link(self, instrument, tab):
        url = escape(api.safe_unicode(instrument.absolute_url()), {'"': '&quot;'})
        title = escape(api.safe_unicode(instrument.Title()))
        return u'<a href="%s/%s">%s</a>' % (url, tab, title)

    def get_certificate_warnings(self):
        try:
            language = getToolByName(self.context, 'portal_languages').getPreferredLanguage() or 'fa'
        except Exception:
            language = 'fa'
        persian = language.lower().split('-')[0] == 'fa'
        labels = (
            ('no-certificate', u'دستگاه با گواهی ثبت‌نشده:' if persian else u'Instruments with no registered certificate:'),
            ('certificate-unknown', u'دستگاه با اطلاعات گواهی ناقص یا نامشخص:' if persian else u'Instruments with incomplete or unknown certificate information:'),
            ('certificate-future', u'دستگاه با گواهی‌ای که اعتبارش هنوز شروع نشده:' if persian else u'Instruments whose certificate validity has not started:'),
        )
        return [{'label': label, 'items': self.failed[key]}
                for key, label in labels if self.failed[key]]

    def available(self):
        """Control availability of the viewlet
        """
        context_state = api.get_view("plone_context_state")
        url = context_state.current_base_url()
        portal_url = api.get_url(api.get_portal())
        # render on the portal root
        if url.endswith(portal_url):
            return True
        # render on the front-page
        if url.endswith("/front-page"):
            return True
        # render for dashboard
        if url.endswith("/senaite-dashboard"):
            return True
        return False

    def render(self):
        """Render the viewlet
        """
        if not self.available():
            return ""

        mtool = api.get_tool("portal_membership")
        member = mtool.getAuthenticatedMember()
        roles = member.getRoles()
        allowed = "LabManager" in roles or "Manager" in roles

        self.get_failed_instruments()

        if allowed and self.nr_failed:
            return self.index()
        else:
            return ""
