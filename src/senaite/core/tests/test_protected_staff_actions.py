# -*- coding: utf-8 -*-
"""Actual plone.protect validators + isolated mutation/permission doubles.

Run with the installed application's bin/zopepy; no production data needed.
"""
import ast
import copy
import os
import unittest
from contextlib import contextmanager
from cStringIO import StringIO

from AccessControl import Unauthorized
from plone.protect import CheckAuthenticator, PostOnly
from plone.protect.authenticator import createToken
from ZPublisher.HTTPRequest import HTTPRequest
from ZPublisher.HTTPResponse import HTTPResponse
from zExceptions import Forbidden
from ZODB.POSException import ConflictError


class Record(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


class Ring(list):
    def random(self):
        return self[0]


class Container(dict):
    def manage_delObjects(self, ids):
        for key in ids:
            del self[key]


class StaffActionsTests(unittest.TestCase):
    targets = [
        ('samplerequest/delete.py', 'SampleIntakeDeleteView', '__call__'),
        ('customercare/delete.py', 'CustomerCareDeleteView', '__call__'),
        ('delete_samples.py', 'DeleteSamplesView', '_delete'),
        ('samplerequest/convert.py', 'ConvertToSampleView', '_convert'),
    ]

    def setUp(self):
        self.manager = {'_anon': Ring(['synthetic-test-secret']),
                        '_forms': Ring(['synthetic-test-secret'])}
        self.allowed = True
        self.privileges = 0
        self.savepoints = 0
        self.rollbacks = 0
        self.intake = Container({'keep': Record(id='keep'),
                                 'remove': Record(id='remove')})
        self.care = Container({'keep': Record(id='keep'),
                               'remove': Record(id='remove')})
        self.setup = {'sampleintake': self.intake, 'customercare': self.care}

    @contextmanager
    def privileged(self):
        self.privileges += 1
        yield

    def savepoint(self, **kw):
        self.savepoints += 1
        intake = self.intake.copy()
        care = self.care.copy()

        def rollback():
            self.rollbacks += 1
            self.intake.clear()
            self.intake.update(intake)
            self.care.clear()
            self.care.update(care)
        return Record(rollback=rollback)

    def request(self, method='POST', token='valid', **form):
        req = HTTPRequest(StringIO(''), {'REQUEST_METHOD': method,
                          'SERVER_NAME': 'test', 'SERVER_PORT': '80'}, HTTPResponse())
        if token == 'valid':
            form['_authenticator'] = createToken(manager=self.manager)
        elif token is not None:
            form['_authenticator'] = token
        req.form.update(form)
        return req

    def load(self, target, request):
        root = os.environ.get('STAFF_ACTION_SOURCE') or os.path.join(
            os.path.dirname(__file__), '..', 'browser')
        path, name, method = target
        with open(os.path.join(root, path), 'rb') as source:
            tree = ast.parse(source.read())
        tree.body = [node for node in tree.body if (
            isinstance(node, ast.ClassDef) and node.name == name
        ) or (isinstance(node, ast.FunctionDef) and node.name == '_as_list')]
        namespace = {
            'BrowserView': object, 'ViewPageTemplateFile': lambda path: None,
            'PostOnly': PostOnly,
            'CheckAuthenticator': lambda req: CheckAuthenticator(req, manager=self.manager),
            'Unauthorized': Unauthorized, 'ManageBika': 'manage',
            'AddAnalysisRequest': 'add', 'SAMPLE_CATALOG': 'sample_catalog',
            'ConflictError': ConflictError, 'safe_unicode': unicode,
            'basestring': basestring,
            'transaction': Record(savepoint=self.savepoint),
            'api': Record(
                security=Record(check_permission=lambda *args: self.allowed,
                                as_privileged_user=self.privileged),
                get_senaite_setup=lambda: self.setup,
                get_object_by_uid=lambda *args, **kw: None,
                get_id=lambda obj: obj.id,
                get_url=lambda obj: '/setup',
                get_object=lambda obj: obj,
                search=lambda *args: []),
        }
        eval(compile(tree, path, 'exec'), namespace)
        view = namespace[name]()
        view.request = request
        view.context = Record(created_sample_uid='', created_sample_id='')
        view.labels = {'err_sampletype': 'missing sample type'}
        view.today = lambda: '2026-10-28'
        view.error = ''
        return view, namespace, method

    def assert_blocked(self, method, token, allowed=True):
        for target in self.targets:
            self.allowed = allowed
            req = self.request(method, token, ids='remove', request_ids=['remove'])
            view, namespace, action = self.load(target, req)
            with self.assertRaises(Forbidden if allowed else Unauthorized):
                getattr(view, action)()
            self.assertIn('remove', self.intake)
            self.assertIn('remove', self.care)
            self.assertEqual(self.privileges, 0)
            self.assertEqual(self.savepoints, 0)

    def test_get_with_valid_token_is_rejected_before_mutation(self):
        self.assert_blocked('GET', 'valid')

    def test_missing_token_is_rejected_before_mutation(self):
        self.assert_blocked('POST', None)

    def test_forged_token_is_rejected_before_mutation(self):
        self.assert_blocked('POST', 'forged')

    def test_valid_token_without_permission_is_rejected(self):
        self.assert_blocked('POST', 'valid', allowed=False)

    def test_authorized_delete_only_removes_selected_record(self):
        for target, container in zip(self.targets[:2], [self.intake, self.care]):
            view, namespace, action = self.load(target, self.request(ids='remove'))
            getattr(view, action)()
            self.assertNotIn('remove', container)
            self.assertIn('keep', container)

    def test_authorized_cleanup_removes_selected_request(self):
        view, namespace, action = self.load(self.targets[2], self.request(request_ids=['remove']))
        message = getattr(view, action)()
        self.assertNotIn('remove', self.intake)
        self.assertIn('keep', self.intake)
        self.assertIn(u'1', message)

    def test_foreign_uid_cannot_delete_same_id_from_intake(self):
        view, namespace, action = self.load(self.targets[0], self.request(uids=['foreign-uid']))
        namespace['api'].get_object_by_uid = lambda *args, **kw: Record(id='remove')
        namespace['api'].get_parent = lambda obj: 'another-container'
        namespace['api'].get_path = lambda obj: '/sampleintake' if obj is self.intake else '/other'
        getattr(view, action)()
        self.assertIn('remove', self.intake)

    def test_authorized_conversion_reaches_validation(self):
        view, namespace, action = self.load(self.targets[3], self.request())
        getattr(view, action)()
        self.assertEqual(view.error, 'missing sample type')

    def test_cleanup_failure_rolls_back_previous_deletions(self):
        view, namespace, action = self.load(self.targets[2], self.request(request_ids=['remove']))
        original = self.intake.manage_delObjects
        def failing(ids):
            original(ids)
            raise ValueError('synthetic failure after deletion')
        self.intake.manage_delObjects = failing
        getattr(view, action)()
        self.assertIn('remove', self.intake)
        self.assertEqual(self.rollbacks, 1)
        self.assertTrue(view.error)

    def test_cleanup_conflict_reaches_publisher(self):
        view, namespace, action = self.load(self.targets[2], self.request(request_ids=['remove']))
        def failing(ids):
            raise ConflictError()
        self.intake.manage_delObjects = failing
        with self.assertRaises(ConflictError):
            getattr(view, action)()


if __name__ == '__main__':
    unittest.main()
