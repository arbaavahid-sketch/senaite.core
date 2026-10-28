# -*- coding: utf-8 -*-
from __future__ import print_function
import imp
import os
import unittest
from multiprocessing.dummy import Pool
BASE = os.environ.get('PUBLIC_FORM_SOURCE', os.path.dirname(__file__))
source = os.path.join(BASE, 'publicforms.py')
if not os.path.exists(source): source = os.path.join(BASE, '../browser/publicforms.py')
form = imp.load_source('public_form_tested', source)

class FormTests(unittest.TestCase):
    def test_scalar_list_rejected(self):
        with self.assertRaises(form.InvalidInput): form.validate_form({'subject':['one','two']})
    def test_nested_upload_rejected(self):
        with self.assertRaises(form.InvalidInput): form.validate_form({'description':object()})
    def test_long_text_rejected(self):
        with self.assertRaises(form.InvalidInput): form.validate_form({'description':'x'*10001})
    def test_unknown_enum_rejected(self):
        for key in ('priority','report_delivery','severity','kind','category'):
            with self.assertRaises(form.InvalidInput): form.validate_form({key:'malformed'})
    def test_ratings_must_be_one_to_five(self):
        for value in ('0','6','-1','2.5','NaN'):
            with self.assertRaises(form.InvalidInput): form.validate_form({'rating_overall':value})
    def test_bad_dates_rejected(self):
        for value in ('2026-02-30','2026-2-01','bad'):
            with self.assertRaises(form.InvalidInput): form.validate_form({'sampling_date':value})
    def test_email_header_injection_rejected(self):
        with self.assertRaises(form.InvalidInput): form.validate_form({'contact_email':'one@example.invalid\r\nBcc:other@example.invalid'})
    def test_invalid_uid_and_oversized_list_rejected(self):
        for values in (['not-a-uid'], ['a'*32]*201):
            with self.assertRaises(form.InvalidInput): form.validate_form({'service_uids':values})
    def test_deduplicate_and_preserve_unicode(self):
        valid=form.validate_form({'service_uids':['a'*32,'a'*32], 'subject':u'آزمون فارسی', 'sampling_date':'2026-02-28'})
        self.assertEqual(valid['service_uids'],['a'*32]); self.assertEqual(valid['subject'],u'آزمون فارسی')
    def test_language_choice_allowlist(self):
        with self.assertRaises(form.InvalidInput): form.validate_form({'storage_conditions':['bad']},{'storage_conditions':set(['normal'])})
    def test_rate_limit_and_expiry(self):
        now=[1000]; limiter=form.RateLimiter(lambda:now[0])
        self.assertTrue(all(limiter.allow('client') for _ in range(60)))
        self.assertFalse(limiter.allow('client')); self.assertTrue(limiter.allow('other'))
        now[0]+=601; self.assertTrue(limiter.allow('client'))
    def test_parallel_rate_limit_is_atomic(self):
        limiter=form.RateLimiter()
        pool=Pool(12)
        try: allowed=pool.map(lambda _:limiter.allow('same-client'),range(100))
        finally: pool.close(); pool.join()
        self.assertEqual(sum(allowed),60)
    def test_maximum_clients_is_bounded(self):
        limiter=form.RateLimiter()
        for number in range(4096): self.assertTrue(limiter.allow(str(number)))
        self.assertFalse(limiter.allow('overflow')); self.assertEqual(len(limiter.clients),4096)
    def test_guard_reads_environ_not_forged_form_values(self):
        class Response(object):
            def setStatus(self,code): self.status=code
            def setHeader(self,*args): pass
        class Request(object):
            form={'subject':'test','HTTP_X_TPPC_CLIENT_IP':'forged'}
            environ={'HTTP_X_TPPC_CLIENT_IP':'real-peer'}
            response=Response()
        class View(object): request=Request(); lang='en'
        previous=form.LIMITER; form.LIMITER=form.RateLimiter()
        try:
            for _ in range(60): self.assertIsNotNone(form.guard(View()))
            view=View(); self.assertIsNone(form.guard(view)); self.assertEqual(view.request.response.status,429)
        finally: form.LIMITER=previous

if __name__=='__main__': unittest.main()
