# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from senaite.core.interfaces import ISenaiteCore
from bika.lims import api
from senaite.core.api.instrumentcertification import get_certificate_status
from senaite.core.browser.instrumentstatus.view import InstrumentStatusView
from bika.lims.browser.viewlets.instruments import InstrumentQCFailuresViewlet

if os.environ.get('TPPC_CERTIFICATE_STAGE') != '1' or not os.path.isfile('/data/.csrf-stage-only'):
    raise SystemExit('Disposable stage required')
app = makerequest(app)
site = app['senaite']
setSite(site)
setRequest(app.REQUEST)
alsoProvides(app.REQUEST, ISenaiteCore)
newSecurityManager(app.REQUEST, SimpleUser('certificate-test', '', ['Manager'], []).__of__(site.acl_users))
try:
    view = InstrumentStatusView(site, app.REQUEST)
    page = view()
    rows = view.get_rows()
    summary = view.get_summary(rows)
    assert sum(summary[key] for key in ('valid', 'due', 'expired', 'none', 'unknown', 'future')) == summary['total']
    warning = InstrumentQCFailuresViewlet(site, app.REQUEST, view)
    warning.get_failed_instruments()
    active = api.get_tool('senaite_catalog_setup')(portal_type='Instrument', is_active=True)
    expected = {'out-of-date': 0, 'no-certificate': 0, 'certificate-unknown': 0, 'certificate-future': 0}
    categories = {'expired': 'out-of-date', 'none': 'no-certificate', 'unknown': 'certificate-unknown', 'future': 'certificate-future'}
    for brain in active:
        obj = brain.getObject()
        status = get_certificate_status(obj)['status']
        if obj.isValidationInProgress() or obj.isCalibrationInProgress():
            continue
        if status in categories:
            expected[categories[status]] += 1
    for key, count in expected.items():
        assert len(warning.failed[key]) == count, key
    warning.index()
    print('REAL_TEMPLATES_RENDERED')
    print('CERTIFICATE_SUMMARY=' + repr(summary))
    print('DASHBOARD_CATEGORIES_MATCH=' + repr(expected))
finally:
    transaction.abort()
    print('TRANSACTION_ABORTED')
