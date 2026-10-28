# -*- coding: utf-8 -*-
"""Run via bin/instance run on a disposable restored database only."""
from __future__ import print_function
import os
import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import SimpleUser
from Testing.makerequest import makerequest
from plone.protect.authenticator import createToken
from zope.component.hooks import setSite
from zope.globalrequest import setRequest
from zope.interface import alsoProvides
from zExceptions import Forbidden, Unauthorized
from bika.lims import api
from Products.CMFCore.indexing import processQueue
from senaite.core.interfaces import ISenaiteCore
from senaite.core.browser.samplerequest.delete import SampleIntakeDeleteView
from senaite.core.browser.customercare.delete import CustomerCareDeleteView
from senaite.core.browser.samplerequest.convert import ConvertToSampleView
from senaite.core.browser.delete_samples import DeleteSamplesView

if (os.environ.get('TPPC_SECURITY_STAGE') != '1'
        or not os.path.isfile('/data/.csrf-stage-only')):
    raise SystemExit('Refusing to run outside the explicit disposable stage')

app = makerequest(app)  # provided by bin/instance run
site = app['senaite']
setSite(site)
request = app.REQUEST
setRequest(request)
alsoProvides(request, ISenaiteCore)
setup = api.get_senaite_setup()


def login(role):
    user = SimpleUser('synthetic-csrf-' + role, '', [role], [])
    newSecurityManager(request, user.__of__(site.acl_users))


def form(method='POST', token='valid', **values):
    request.form.clear()
    request.set('REQUEST_METHOD', method)
    if token == 'valid':
        values['_authenticator'] = createToken()
    elif token is not None:
        values['_authenticator'] = token
    request.form.update(values)


try:
    login('Manager')
    intake = setup.sampleintake
    care = setup.customercare
    fixtures = {}
    for container, typename in ((intake, 'SampleRequest'), (care, 'Complaint')):
        fixtures[typename] = api.create(container, typename, title=u'Synthetic security test')
    transaction.savepoint(optimistic=True)
    processQueue()
    context = fixtures['SampleRequest']
    request_id = api.get_id(context)
    complaint_id = api.get_id(fixtures['Complaint'])
    endpoints = [
        (SampleIntakeDeleteView(site, request), '__call__'),
        (CustomerCareDeleteView(site, request), '__call__'),
        (DeleteSamplesView(site, request), '_delete'),
        (ConvertToSampleView(context, request), '_convert'),
    ]
    blocked = 0
    for role, method, token, expected in (
            ('Manager', 'GET', 'valid', Forbidden),
            ('Manager', 'POST', None, Forbidden),
            ('Manager', 'POST', 'forged', Forbidden),
            ('Member', 'POST', 'valid', Unauthorized)):
        login(role)
        for view, action in endpoints:
            form(method, token, ids=request_id, request_ids=[request_id])
            try:
                getattr(view, action)()
            except expected:
                blocked += 1
            else:
                raise AssertionError('Unsafe staff action was accepted')
            assert request_id in intake.objectIds()
            assert complaint_id in care.objectIds()
    print('STAGING_NEGATIVE_CASES_OK count=%s' % blocked)
    login('Manager')
    form(ids=complaint_id)
    CustomerCareDeleteView(site, request)()
    assert complaint_id not in care.objectIds()
    form(uids=[api.get_uid(context)])
    SampleIntakeDeleteView(site, request)()
    assert request_id not in intake.objectIds()
    print('STAGING_AUTHORIZED_DELETES_OK')
    # Both admin forms must render an actual authenticator hidden field.
    form('GET')
    cleanup = DeleteSamplesView(site, request)
    request.set('PUBLISHED', cleanup)
    html = cleanup()
    assert 'name="_authenticator"' in html
    assert 'do_delete' in html
    print('STAGING_CLEANUP_FORM_TOKEN_OK')
    # Create a new fixture for the conversion form after deleting the first.
    context = api.create(intake, 'SampleRequest', title=u'Synthetic conversion form')
    convert = ConvertToSampleView(context, request)
    request.set('PUBLISHED', convert)
    html = convert()
    assert 'name="_authenticator"' in html
    assert 'sampletype_uid' in html
    print('STAGING_CONVERSION_FORM_TOKEN_OK')
finally:
    # No changes from this script are committed, even on success.
    transaction.abort()
    print('STAGING_TRANSACTION_ABORTED')
