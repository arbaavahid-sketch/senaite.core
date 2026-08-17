# -*- coding: utf-8 -*-
#
# Event handler that assigns an unguessable access token to customer-care
# records (Complaint / SupportRequest / Survey) on creation. The token backs
# the customer's direct tracking link (@@track-request?token=...), so a customer
# can open their answer with a single click, without typing a code or name.

import uuid


def assign_access_token(obj, event):
    """Assign a random access token on creation if not already set."""
    try:
        token = getattr(obj, "access_token", None)
    except Exception:
        token = None
    if not token:
        obj.access_token = uuid.uuid4().hex
