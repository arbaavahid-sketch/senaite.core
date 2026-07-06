# -*- coding: utf-8 -*-
#
# Control-panel listing for the controlled documents register (ISO 17025).

import collections

from bika.lims import api
from bika.lims import senaiteMessageFactory as _
from bika.lims.utils import get_link_for
from senaite.core.browser.controlpanel.listing import ControlPanelListingView
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.i18n import translate


class ControlledDocumentsView(ControlPanelListingView):

    def __init__(self, context, request):
        super(ControlledDocumentsView, self).__init__(context, request)

        self.catalog = SETUP_CATALOG

        self.contentFilter = {
            "portal_type": "ControlledDocument",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
            "path": {
                "query": api.get_path(context),
                "depth": 1,
            }
        }

        self.context_actions = {
            _("listing_controlleddocuments_action_add", default="Add"): {
                "url": "++add++ControlledDocument",
                "icon": "senaite_theme/icon/plus"
            }
        }

        self.title = translate(_(
            "listing_controlleddocuments_title",
            default="Controlled Documents"))
        self.icon = api.get_icon("ControlledDocuments", html_tag=False)

        self.show_select_column = True

        self.columns = collections.OrderedDict((
            ("DocumentID", {
                "title": _(u"listing_controlleddocuments_column_code",
                           default=u"Code")}),
            ("Title", {
                "title": _(u"listing_controlleddocuments_column_title",
                           default=u"Title"),
                "index": "sortable_title"}),
            ("DocumentType", {
                "title": _(u"listing_controlleddocuments_column_type",
                           default=u"Type")}),
            ("Version", {
                "title": _(u"listing_controlleddocuments_column_version",
                           default=u"Version")}),
            ("ReviewDate", {
                "title": _(u"listing_controlleddocuments_column_review",
                           default=u"Next review")}),
            ("State", {
                "title": _(u"listing_controlleddocuments_column_state",
                           default=u"State")}),
        ))

        self.review_states = [
            {
                "id": "default",
                "title": _(u"listing_controlleddocuments_state_all",
                           default=u"All"),
                "contentFilter": {},
                "columns": self.columns.keys(),
            }, {
                "id": "effective",
                "title": _(u"listing_controlleddocuments_state_effective",
                           default=u"Effective"),
                "contentFilter": {"review_state": "effective"},
                "columns": self.columns.keys(),
            }, {
                "id": "draft",
                "title": _(u"listing_controlleddocuments_state_draft",
                           default=u"Draft"),
                "contentFilter": {"review_state": "draft"},
                "columns": self.columns.keys(),
            }, {
                "id": "obsolete",
                "title": _(u"listing_controlleddocuments_state_obsolete",
                           default=u"Obsolete"),
                "contentFilter": {"review_state": "obsolete"},
                "columns": self.columns.keys(),
            },
        ]

    def folderitem(self, obj, item, index):
        obj = api.get_object(obj)
        item["replace"]["Title"] = get_link_for(obj)
        item["DocumentID"] = getattr(obj, "document_id", "") or ""
        item["DocumentType"] = getattr(obj, "document_type", "") or ""
        item["Version"] = getattr(obj, "version", "") or ""
        review_date = getattr(obj, "review_date", None)
        item["ReviewDate"] = self._fmt_date(review_date)
        item["State"] = translate(api.get_review_status(obj))
        return item

    def _fmt_date(self, value):
        if not value:
            return ""
        try:
            return value.strftime("%Y-%m-%d")
        except Exception:
            return str(value)
