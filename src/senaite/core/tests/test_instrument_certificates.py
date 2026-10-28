# -*- coding: utf-8 -*-
from __future__ import print_function
import ast
import imp
import io
import os
import re
import unittest
from DateTime import DateTime
from ZODB.POSException import ConflictError
from xml.sax.saxutils import escape
from Products.PageTemplates.PageTemplate import PageTemplate
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.User import UnrestrictedUser
from zope.component import provideAdapter
from zope.interface import Interface
from zope.traversing.interfaces import ITraversable
from zope.traversing.adapters import DefaultTraversable

BASE = os.environ.get('CERTIFICATE_TEST_SOURCE') or os.path.dirname(__file__)
PATHS = {
    'instrumentcertification.py': '../api/instrumentcertification.py',
    'status_view.py': '../browser/instrumentstatus/view.py',
    'status.pt': '../browser/instrumentstatus/templates/status.pt',
    'instruments.py': '../../../bika/lims/browser/viewlets/instruments.py',
    'instrument_qc_failures_viewlet.pt': '../../../bika/lims/browser/viewlets/templates/instrument_qc_failures_viewlet.pt',
}
def source_path(name):
    direct = os.path.join(BASE, name)
    return direct if os.path.exists(direct) else os.path.join(BASE, PATHS[name])
helper = imp.load_source('tested_certificate_status', source_path('instrumentcertification.py'))
NOW = DateTime('2026/10/28 12:00:00 UTC')

class Record(object):
    __allow_access_to_unprotected_subobjects__ = 1
    def __init__(self, **values): self.__dict__.update(values)

class Certificate(object):
    def __init__(self, start, end): self.start, self.end = start, end
    def getValidFrom(self): return self.start
    def getValidTo(self): return self.end

class Instrument(object):
    def __init__(self, certificates, title='Synthetic instrument'):
        self.certificates, self.title = certificates, title
        self.validation = self.calibration = self.qc_failed = self.disposed = False
    def getCertifications(self): return self.certificates
    def UID(self): return self.title
    def Title(self): return self.title
    def absolute_url(self): return 'https://test.invalid/instrument'
    def isValidationInProgress(self): return self.validation
    def isCalibrationInProgress(self): return self.calibration
    def isQCValid(self): return not self.qc_failed
    def getDisposeUntilNextCalibrationTest(self): return self.disposed
    def getInstrumentType(self): return None
    def getSerialNo(self): return 'SYNTHETIC'

class Base(object):
    __allow_access_to_unprotected_subobjects__ = 1
    def __init__(self, *args, **kw):
        self.context = args[0] if args else None
        self.request = args[1] if len(args) > 1 else {}

def status(obj, days=30):
    return helper.get_certificate_status(obj, days, now=NOW)

def load_class(filename, name, instruments):
    tree = ast.parse(io.open(source_path(filename), encoding='utf-8').read().encode('utf-8'))
    tree.body = [n for n in tree.body if isinstance(n, ast.Assign)
                 or (isinstance(n, ast.ClassDef) and n.name == name)]
    brains = [Record(getObject=lambda obj=obj: obj) for obj in instruments]
    namespace = {
        'BrowserView': Base, 'ViewletBase': Base,
        'ViewPageTemplateFile': lambda path: lambda *args: '',
        'SETUP_CATALOG': 'setup', 'escape': escape,
        'get_certificate_status': status,
        'getToolByName': lambda *args: Record(getPreferredLanguage=lambda: 'fa'),
        'api': Record(get_tool=lambda key: lambda *args, **kw: brains,
                      get_object=lambda brain: brain.getObject(),
                      get_title=lambda obj: obj.Title(),
                      get_url=lambda obj: obj.absolute_url(), safe_unicode=unicode),
    }
    eval(compile(tree, filename, 'exec'), namespace)
    args = (None, {}, None) if name == 'InstrumentQCFailuresViewlet' else (None, {})
    return namespace[name](*args), namespace

class CertificateTests(unittest.TestCase):
    def test_no_registered_certificate_is_not_expired(self):
        self.assertEqual(status(Instrument([]))['status'], 'none')
    def test_missing_dates_are_unknown(self):
        for start, end in [(None, NOW + 1), (NOW - 1, None), (None, None)]:
            self.assertEqual(status(Instrument([Certificate(start, end)]))['status'], 'unknown')
    def test_invalid_date_interval_is_unknown(self):
        self.assertEqual(status(Instrument([Certificate(NOW + 5, NOW - 5)]))['status'], 'unknown')
    def test_unparseable_dates_are_unknown(self):
        self.assertEqual(status(Instrument([Certificate('bad', 'date')]))['status'], 'unknown')
    def test_expired_within_a_day_is_not_due_soon(self):
        result = status(Instrument([Certificate(NOW - 10, NOW - 0.1)]))
        self.assertEqual(result['days'], 0)
        self.assertEqual(result['status'], 'expired')
    def test_expiry_instant_is_inclusive(self):
        self.assertEqual(status(Instrument([Certificate(NOW - 1, NOW)]))['status'], 'due')
    def test_future_certificate_is_not_currently_valid(self):
        self.assertEqual(status(Instrument([Certificate(NOW + 1, NOW + 60)]))['status'], 'future')
    def test_current_certificate_takes_priority_over_future_one(self):
        current = Certificate(NOW - 10, NOW + 10)
        result = status(Instrument([current, Certificate(NOW + 20, NOW + 400)]))
        self.assertEqual(result['status'], 'due')
        self.assertIs(result['certificate'], current)
    def test_future_certificate_does_not_hide_current_gap(self):
        result = status(Instrument([Certificate(NOW - 10, NOW - 1), Certificate(NOW + 1, NOW + 90)]))
        self.assertEqual(result['status'], 'expired')
    def test_incomplete_record_does_not_prove_all_certificates_expired(self):
        result = status(Instrument([Certificate(NOW - 10, NOW - 1), Certificate(None, NOW + 90)]))
        self.assertEqual(result['status'], 'unknown')
    def test_longest_current_validity_is_selected(self):
        result = status(Instrument([Certificate(NOW - 10, NOW + 10), Certificate(NOW - 5, NOW + 60)]))
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(result['days'], 60)
    def test_read_error_is_unknown_and_conflict_propagates(self):
        class Broken(Instrument):
            def getCertifications(self): raise ValueError('synthetic read error')
        self.assertEqual(status(Broken([]))['status'], 'unknown')
        class Conflicting(Instrument):
            def getCertifications(self): raise ConflictError()
        with self.assertRaises(ConflictError): status(Conflicting([]))

class DisplayTests(unittest.TestCase):
    def fixtures(self):
        return [Instrument([]), Instrument([Certificate(None, NOW + 20)]),
                Instrument([Certificate(NOW + 10, NOW + 30)]),
                Instrument([Certificate(NOW - 10, NOW - 2)]),
                Instrument([Certificate(NOW - 10, NOW + 5)]),
                Instrument([Certificate(NOW - 10, NOW + 60)])]
    def test_dashboard_separates_missing_unknown_future_and_expired(self):
        view, ns = load_class('instruments.py', 'InstrumentQCFailuresViewlet', self.fixtures())
        view.get_failed_instruments()
        self.assertEqual(view.nr_failed, 4)
        for key in ('no-certificate', 'certificate-unknown', 'certificate-future', 'out-of-date'):
            self.assertEqual(len(view.failed[key]), 1)
        view.get_failed_instruments()
        self.assertEqual(view.nr_failed, 4)
    def test_validation_and_qc_categories_are_preserved(self):
        validation = Instrument([]); validation.validation = True
        qc = Instrument([Certificate(NOW - 10, NOW + 60)]); qc.qc_failed = True
        view, ns = load_class('instruments.py', 'InstrumentQCFailuresViewlet', [validation, qc])
        view.get_failed_instruments()
        self.assertEqual(len(view.failed['validation']), 1)
        self.assertEqual(len(view.failed['qc-fail']), 1)
        self.assertEqual(len(view.failed['no-certificate']), 0)
    def test_device_title_is_escaped_in_warning_link(self):
        view, ns = load_class('instruments.py', 'InstrumentQCFailuresViewlet', [Instrument([], '<script>')])
        view.get_failed_instruments()
        link = view.failed['no-certificate'][0]['link']
        self.assertNotIn('<script>', link)
        self.assertIn('&lt;script&gt;', link)
    def test_status_table_summary_and_fa_en_labels(self):
        view, ns = load_class('status_view.py', 'InstrumentStatusView', self.fixtures())
        view.days = 30
        for language in ('fa', 'en'):
            view.labels = ns['LABELS'][language]
            rows = view.get_rows()
            summary = view.get_summary(rows)
            self.assertEqual(summary['total'], 6)
            for key in ('none', 'unknown', 'future', 'expired', 'due', 'valid'):
                self.assertEqual(summary[key], 1)
            self.assertEqual(len(set(row['status_label'] for row in rows)), 6)
    def test_templates_render_new_labels(self):
        newSecurityManager(None, UnrestrictedUser('certificate-layout', '', ['Manager'], []))
        provideAdapter(DefaultTraversable, (Interface,), ITraversable)
        for filename, name, template in [('status_view.py', 'InstrumentStatusView', 'status.pt'),
                                          ('instruments.py', 'InstrumentQCFailuresViewlet', 'instrument_qc_failures_viewlet.pt')]:
            view, ns = load_class(filename, name, self.fixtures())
            if name == 'InstrumentStatusView':
                view.days = 30; view.labels = ns['LABELS']['fa']; view.is_rtl = True
            else:
                view.get_failed_instruments()
            source = io.open(source_path(template), encoding='utf-8').read()
            source = re.sub(r'\s+metal:[\w-]+="[^"]*"', '', source)
            source = re.sub(r'\s+fill-slot="[^"]*"', '', source)
            page = PageTemplate(); page.write(source)
            self.assertFalse(page._v_errors)
            rendered = page.pt_render(extra_context={'view': view, 'request': Record(set=lambda *args: None)})
            self.assertIn(u'ثبت', rendered)

if __name__ == '__main__': unittest.main()
