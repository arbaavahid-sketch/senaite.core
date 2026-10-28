# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import transaction
from DateTime import DateTime
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from zope.component import getUtility
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from plone.registry.interfaces import IRegistry
from plone.app.event.base import default_timezone
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser.dashboard.dashboard import DashboardView
if not os.path.isfile('/data/.csrf-stage-only'):
    raise SystemExit('Disposable stage required')
app = makerequest(app)
site = app['senaite']
setSite(site)
setRequest(app.REQUEST)
alsoProvides(app.REQUEST, ISenaiteCore)
newSecurityManager(app.REQUEST, SimpleUser('dashboard-time-test', '', ['Manager'], []).__of__(site.acl_users))
try:
    registry = getUtility(IRegistry)
    os.environ['TPPC_OFFLINE_TIMEZONE'] = '1'
    migration = os.path.join(os.path.dirname(__file__), 'configure_timezone.py')
    if not os.path.exists(migration):
        migration = os.environ['TPPC_TIMEZONE_MIGRATION']
    execfile(migration, {'app': app})
    execfile(migration, {'app': app})
    assert default_timezone(site) == 'Asia/Tehran'
    view = DashboardView(site, app.REQUEST)
    page = view()
    assert 'Asia/Tehran' in page
    assert view.get_current_timezone() == 'Asia/Tehran'
    assert abs(DateTime(view.get_current_datetime()) - DateTime()) < (5.0 / 86400)
    print('REAL_DASHBOARD_RENDERED_WITH_TEHRAN_TIME')
    member = site.portal_membership.getAuthenticatedMember()
    # Exercise the actual Plone resolver with user preference through a local stub.
    from plone.app.event import base
    original = base.getToolByName
    class Member(object):
        def getProperty(self, key, default=None): return 'Europe/Berlin'
    class Membership(object):
        def isAnonymousUser(self): return False
        def getAuthenticatedMember(self): return Member()
    base.getToolByName = lambda *args: Membership()
    try:
        user_view = DashboardView(site, app.REQUEST)
        assert user_view.get_current_timezone() == 'Europe/Berlin'
    finally:
        base.getToolByName = original
    print('ACTUAL_USER_TIMEZONE_RESOLVER_RESPECTED')
finally:
    transaction.abort()
    print('TRANSACTION_ABORTED')
