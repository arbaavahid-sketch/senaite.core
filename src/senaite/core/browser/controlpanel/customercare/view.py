# -*- coding: utf-8 -*-
#
# Control-panel listing for the customer-care register: complaints, surveys and
# support requests in one view.

import collections

from bika.lims import api
from bika.lims import senaiteMessageFactory as _
from bika.lims.utils import get_link_for
from senaite.core.browser.controlpanel.listing import ControlPanelListingView
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.i18n import translate

TYPE_LABELS = {
    "Complaint": _(u"customercare_type_complaint", default=u"Complaint"),
    "SupportRequest": _(u"customercare_type_support", default=u"Support request"),
    "Survey": _(u"customercare_type_survey", default=u"Satisfaction survey"),
}


class CustomerCareView(ControlPanelListingView):

    def __init__(self, context, request):
        super(CustomerCareView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": ["Complaint", "SupportRequest", "Survey"],
            "sort_on": "created",
            "sort_order": "descending",
            "path": {
                "query": api.get_path(context),
                "depth": 1,
            }
        }

        self.context_actions = collections.OrderedDict((
            (_("customercare_action_add_complaint", default="Add complaint"), {
                "url": "++add++Complaint",
                "icon": "senaite_theme/icon/plus"}),
            (_("customercare_action_add_support", default="Add support request"), {
                "url": "++add++SupportRequest",
                "icon": "senaite_theme/icon/plus"}),
            (_("customercare_action_add_survey", default="Add survey"), {
                "url": "++add++Survey",
                "icon": "senaite_theme/icon/plus"}),
        ))

        self.title = translate(_(
            "customercare_title", default="Customer Care"))
        self.icon = api.get_icon("CustomerCare", html_tag=False)

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("Type", {"title": _(u"customercare_column_type", default=u"Type")}),
            ("Title", {
                "title": _(u"customercare_column_subject", default=u"Subject"),
                "index": "sortable_title"}),
            ("Client", {"title": _(u"customercare_column_client", default=u"Client")}),
            ("Created", {
                "title": _(u"customercare_column_created", default=u"Created")}),
            ("State", {"title": _(u"customercare_column_state", default=u"State")}),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _(u"customercare_state_all", default=u"All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            }, {
                "id": "open",
                "title": _(u"customercare_state_open", default=u"Open"),
                "contentFilter": {
                    "review_state": ["received", "in_progress"]},
                "columns": self.columns.keys(),
            }, {
                "id": "closed",
                "title": _(u"customercare_state_closed", default=u"Closed"),
                "contentFilter": {"review_state": ["resolved", "closed"]},
                "columns": self.columns.keys(),
            },
        ]

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        item["replace"]["Title"] = get_link_for(obj)
        pt = api.get_portal_type(obj)
        label = TYPE_LABELS.get(pt, pt)
        item["Type"] = translate(label)
        item["Client"] = getattr(obj, "client_name", "") or ""
        created = api.get_creation_date(obj)
        try:
            item["Created"] = created.strftime("%Y-%m-%d")
        except Exception:
            item["Created"] = ""
        item["State"] = translate(api.get_review_status(obj))
        return item
