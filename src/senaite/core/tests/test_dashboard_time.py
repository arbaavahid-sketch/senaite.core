# -*- coding: utf-8 -*-
from __future__ import print_function
import ast
import io
import os
import unittest
import datetime
import pytz
from DateTime import DateTime

BASE = os.path.dirname(__file__)
source = os.path.join(BASE, 'dashboard.py')
if not os.path.exists(source):
    source = os.path.join(BASE, '../browser/dashboard/dashboard.py')
tree = ast.parse(io.open(source, encoding='utf-8').read().encode('utf-8'))
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'DashboardView')
methods = ('get_current_date', 'get_current_time', 'get_current_datetime', 'get_current_timezone')
cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in methods]
tree.body = [cls]
class Base(object): pass
namespace = {'BrowserView': Base, 'pytz': pytz}
eval(compile(tree, source, 'exec'), namespace)
DashboardView = namespace['DashboardView']

class DashboardTimeTests(unittest.TestCase):
    def view(self, instant, zone):
        self.calls = 0
        test = self
        class Clock(object):
            @staticmethod
            def now(timezone):
                test.calls += 1
                return datetime.datetime.fromtimestamp(DateTime(instant).timeTime(), timezone)
        class Module(object): pass
        clock_module = Module(); clock_module.datetime = Clock
        namespace['datetime'] = clock_module
        namespace['default_timezone'] = lambda context: zone
        view = DashboardView()
        view.context = None
        return view
    def test_tehran_time_independent_of_container_timezone(self):
        view = self.view('2026/10/28 10:00 UTC', 'Asia/Tehran')
        self.assertEqual(view.get_current_time(), '13:30')
        self.assertEqual(view.get_current_timezone(), 'Asia/Tehran')
    def test_date_rollover_at_local_midnight(self):
        view = self.view('2026/10/28 21:00 UTC', 'Asia/Tehran')
        self.assertEqual(view.get_current_date(), 'Thursday, 29 October 2026')
        self.assertEqual(view.get_current_time(), '00:30')
    def test_shared_snapshot_prevents_mixed_date_and_time(self):
        view = self.view('2026/10/28 20:29:59 UTC', 'Asia/Tehran')
        view.get_current_date(); view.get_current_time(); view.get_current_timezone()
        self.assertEqual(self.calls, 1)
    def test_user_timezone_can_override_portal(self):
        view = self.view('2026/10/28 10:00 UTC', 'Europe/Berlin')
        self.assertEqual(view.get_current_time(), '11:00')
        self.assertEqual(view.get_current_timezone(), 'Europe/Berlin')
    def test_no_daylight_saving_in_iran_in_summer_2026(self):
        view = self.view('2026/07/01 10:00 UTC', 'Asia/Tehran')
        self.assertEqual(view.get_current_time(), '13:30')
    def test_utc_user_setting_is_respected(self):
        view = self.view('2026/10/28 10:00 UTC', 'UTC')
        self.assertEqual(view.get_current_time(), '10:00')

if __name__ == '__main__': unittest.main()
