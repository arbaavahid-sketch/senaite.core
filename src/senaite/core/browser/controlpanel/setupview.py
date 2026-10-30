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
from senaite.core.i18n import translate as t
from plone.memoize.instance import memoize
from plone.memoize.view import memoize_contextless
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.core.p3compat import cmp
from zope.component import getMultiAdapter
import io
import json
import os


class SetupView(BrowserView):
    """Ordered overview of all Setup Items
    """
    template = ViewPageTemplateFile("templates/setupview.pt")

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        return self.template()

    @memoize
    def ui_metadata(self):
        path = os.path.join(os.path.dirname(__file__), 'setupview-meta.json')
        with io.open(path, encoding='utf-8') as source:
            return json.load(source)

    def is_farsi(self):
        lang = getMultiAdapter((self.context, self.request), name='plone_portal_state').language() or 'fa'
        return lang.lower().startswith('fa')

    def ui_text(self, key):
        return self.ui_metadata()['text'][key][0 if self.is_farsi() else 1]

    def ui_styles(self):
        with io.open(os.path.join(os.path.dirname(__file__), 'setupview.css'), encoding='utf-8') as source:
            return source.read()

    @memoize
    def ui_groups(self):
        """Presentation only: retain every original destination and record."""
        meta = self.ui_metadata()
        fa = self.is_farsi()
        groups = []
        by_id = {}
        for row in meta['groups']:
            group = {'id': row[0], 'title': row[1 if fa else 2],
                     'description': row[3 if fa else 4], 'icon': row[5], 'cards': []}
            groups.append(group)
            by_id[row[0]] = group
        for obj in self.setupitems():
            key = api.get_id(obj)
            row = meta['cards'].get(key)
            title = row[1 if fa else 2] if row else t(api.get_title(obj))
            description = row[3 if fa else 4] if row else self.ui_text('open')
            group_id = row[0] if row else 'management'
            by_id[group_id]['cards'].append({'id': key, 'url': api.get_url(obj),
                'title': title, 'description': description, 'count': self.get_count(obj),
                'kind': self.ui_text('record'), 'icon': by_id[group_id]['icon']})
        by_id['management']['cards'].insert(0, {'id': 'general-settings',
            'url': api.get_url(self.setup), 'title': self.ui_text('general'),
            'description': self.ui_text('general_desc'), 'count': None,
            'kind': self.ui_text('open'), 'icon': 'sliders-h'})
        for index, tile in enumerate(self.extra_tiles()):
            by_id['management']['cards'].append({'id': 'report-%s' % index,
                'url': tile['url'], 'title': tile['title'],
                'description': self.ui_text('report_desc'), 'count': None,
                'kind': self.ui_text('reports'), 'icon': 'chart-line'})
        for group in groups:
            group['count'] = len(group['cards'])
        return groups

    @property
    @memoize
    def bootstrap(self):
        return getMultiAdapter(
            (self.context, self.request),
            name="bootstrapview")

    @property
    def portal(self):
        """Returns the Portal Object
        """
        return api.get_portal()

    @property
    def setup(self):
        """Returns the old Setup Object
        """
        return api.get_senaite_setup()

    @property
    def senaite_setup(self):
        """Returns the new Setup Object
        """
        return api.get_senaite_setup()

    @property
    def bika_setup(self):
        """Returns the old Setup Object
        """
        return api.get_bika_setup()

    @memoize_contextless
    def get_icon_for(self, brain, **kw):
        """Returns the icon URL for the given catalog brain
        """
        return self.bootstrap.get_icon_for(brain, **kw)

    @memoize_contextless
    def get_allowed_content_types(self, obj):
        """Get the allowed content types
        """
        portal_types = api.get_tool("portal_types")
        fti = portal_types.getTypeInfo(api.get_portal_type(obj))
        allowed_types = fti.allowed_content_types
        if len(allowed_types) != 1:
            return None
        # convert from unicode -> str for api.search catalog lookup
        return list(map(str, allowed_types))

    def get_count(self, obj):
        """Retrieve the count of contained items
        """
        contained_types = self.get_allowed_content_types(obj)

        # fallback
        if contained_types is None:
            return len(obj.objectIds())

        query = {
            "portal_type": contained_types,
            "is_active": True,
            "path": {
                "query": api.get_path(obj),
                "level": 0,
            }
        }
        brains = api.search(query)
        return len(brains)

    def extra_tiles(self):
        """Custom (non-content) tiles to append to the setup overview.

        Currently just the analyst performance report. Bilingual (fa/en)
        according to the current site language.
        """
        is_fa = self.is_farsi()
        portal_url = api.get_portal().absolute_url()
        return [{
            "url": portal_url + "/@@analyst-performance",
            "title": u"عملکرد آزمونگرها" if is_fa else u"Analyst Performance",
        }, {
            "url": portal_url + "/@@instrument-status",
            "title": u"وضعیت کالیبراسیون دستگاه‌ها" if is_fa else u"Instrument Calibration Status",
        }, {
            "url": portal_url + "/@@document-review-status",
            "title": u"وضعیت بازنگری اسناد" if is_fa else u"Document Review Status",
        }, {
            "url": portal_url + "/@@customer-care-status",
            "title": u"داشبورد امور مشتریان" if is_fa else u"Customer Care Dashboard",
        }]

    def setupitems(self):
        """Lookup available setup items

        :returns: objects
        """
        items = self.setup.objectValues() + self.bika_setup.objectValues()

        # sort by (translated) title
        def cmp_by_translated_title(obj1, obj2):
            title1 = t(api.get_title(obj1))
            title2 = t(api.get_title(obj2))
            return cmp(title1, title2)

        return sorted(items, cmp=cmp_by_translated_title)
