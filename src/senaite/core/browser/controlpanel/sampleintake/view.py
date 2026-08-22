# -*- coding: utf-8 -*-
#
# Control-panel listing for the sample-intake register: online customer test
# requests waiting to be converted into real Samples (AnalysisRequests).

import collections

from bika.lims import api
from bika.lims import senaiteMessageFactory as _
from bika.lims.api import safe_unicode
from bika.lims.utils import get_link_for
from senaite.core.browser.controlpanel.listing import ControlPanelListingView
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.i18n import translate


class SampleIntakeView(ControlPanelListingView):

    def __init__(self, context, request):
        super(SampleIntakeView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": ["SampleRequest"],
            "sort_on": "created",
            "sort_order": "descending",
            "path": {
                "query": api.get_path(context),
                "depth": 1,
            }
        }

        self.title = translate(_(
            "sampleintake_title", default="Sample Intake (online test requests)"))
        self.icon = api.get_icon("SampleIntake", html_tag=False)

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("Title", {
                "title": _(u"sampleintake_column_subject", default=u"Subject"),
                "index": "sortable_title"}),
            ("Client", {
                "title": _(u"sampleintake_column_client", default=u"Client")}),
            ("SampleType", {
                "title": _(u"sampleintake_column_sampletype",
                           default=u"Sample type")}),
            ("Created", {
                "title": _(u"sampleintake_column_created", default=u"Created")}),
            ("State", {
                "title": _(u"sampleintake_column_state", default=u"State")}),
            ("Sample", {
                "title": _(u"sampleintake_column_sample",
                           default=u"Registered sample")}),
            ("Convert", {
                "title": _(u"sampleintake_column_convert",
                           default=u"Action")}),
            ("CustomerLink", {
                "title": _(u"sampleintake_column_link",
                           default=u"Customer link")}),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _(u"sampleintake_state_all", default=u"All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            }, {
                "id": "open",
                "title": _(u"sampleintake_state_open", default=u"Open"),
                "contentFilter": {
                    "review_state": ["received", "in_progress"]},
                "columns": self.columns.keys(),
            }, {
                "id": "closed",
                "title": _(u"sampleintake_state_closed", default=u"Closed"),
                "contentFilter": {"review_state": ["resolved", "closed"]},
                "columns": self.columns.keys(),
            },
        ]

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        item["replace"]["Title"] = get_link_for(obj)
        item["Client"] = safe_unicode(getattr(obj, "client_name", "") or "")
        item["SampleType"] = safe_unicode(getattr(obj, "sample_type", "") or "")
        created = api.get_creation_date(obj)
        try:
            item["Created"] = created.strftime("%Y-%m-%d")
        except Exception:
            item["Created"] = ""
        item["State"] = safe_unicode(translate(api.get_review_status(obj)))

        # Link to the registered Sample, if this request was already converted.
        sample_id = safe_unicode(getattr(obj, "created_sample_id", "") or "")
        item["Sample"] = sample_id

        # "Convert to Sample" action: opens the guided conversion form, unless
        # a sample was already created from this request. The object URL can
        # contain non-ascii (Persian) characters when the id was derived from a
        # Persian subject, so keep everything unicode to avoid a decode error.
        if sample_id:
            item["Convert"] = ""
        else:
            convert_url = safe_unicode(api.get_url(obj)) \
                + u"/@@convert-to-sample"
            item["Convert"] = convert_url
            label = safe_unicode(translate(_(u"sampleintake_convert_action",
                                             default=u"Convert to Sample")))
            item["replace"]["Convert"] = (
                u'<a class="btn btn-sm btn-primary" href="%s">%s</a>'
                % (convert_url, label))

        token = getattr(obj, "access_token", None)
        if token:
            url = u"%s/@@track-request?token=%s" % (
                safe_unicode(api.get_url(api.get_portal())), token)
            item["CustomerLink"] = url
            item["replace"]["CustomerLink"] = (
                u'<a href="%s" target="_blank">%s</a>' % (url, url))
        else:
            item["CustomerLink"] = ""
        return item
