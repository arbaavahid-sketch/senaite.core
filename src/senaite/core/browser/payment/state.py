# -*- coding: utf-8 -*-
"""Transaction-bound payment attempts and globally unique gateway references."""
from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from zope.annotation.interfaces import IAnnotations
from six import string_types
import re

ANNOTATION_KEY = 'tppc.payment.ledger.v1'


class PaymentStateError(ValueError):
    pass


def get_ledger(setup, create=False):
    annotations = IAnnotations(setup)
    ledger = annotations.get(ANNOTATION_KEY)
    if ledger is None and create:
        ledger = PersistentMapping(attempts=OOBTree(), references=OOBTree())
        annotations[ANNOTATION_KEY] = ledger
    return ledger


def attempt_key(scope, authority):
    return '%s|%s' % (scope, authority)


def add_attempt(ledger, scope, authority, uid, amount, created):
    key = attempt_key(scope, authority)
    existing = ledger['attempts'].get(key)
    if existing is not None:
        if (existing['uid'] != uid or existing['amount'] != amount
                or existing['state'] != 'pending'):
            raise PaymentStateError('authority_already_bound')
        return existing
    attempt = PersistentMapping(uid=uid, authority=authority, scope=scope,
        amount=amount, currency='IRR', state='pending', created=created, ref='')
    ledger['attempts'][key] = attempt
    return attempt


def bound_attempt(ledger, scope, authority, uid, amount):
    if ledger is None:
        raise PaymentStateError('unknown_attempt')
    attempt = ledger['attempts'].get(attempt_key(scope, authority))
    if attempt is None or attempt['uid'] != uid:
        raise PaymentStateError('authority_request_mismatch')
    if attempt['amount'] != amount or attempt['currency'] != 'IRR':
        raise PaymentStateError('amount_changed')
    if attempt['scope'] != scope or attempt['authority'] != authority:
        raise PaymentStateError('gateway_changed')
    return attempt


def claim_paid(ledger, scope, authority, uid, amount, ref, obj, timestamp):
    if not isinstance(ref, string_types) or not re.match(r'^[0-9]+\Z', ref) or int(ref) <= 0:
        raise PaymentStateError('invalid_reference')
    attempt = bound_attempt(ledger, scope, authority, uid, amount)
    key = attempt_key(scope, authority)
    ref_key = '%s|%s' % (scope, ref)
    owner = ledger['references'].get(ref_key)
    if owner is not None and owner != key:
        raise PaymentStateError('reference_already_used')
    if bool(getattr(obj, 'payment_paid', False)):
        if (attempt['state'] == 'paid' and attempt['ref'] == ref
                and getattr(obj, 'payment_ref', '') == ref and owner == key):
            return False
        raise PaymentStateError('request_already_paid')
    if attempt['state'] != 'pending':
        raise PaymentStateError('inconsistent_attempt')
    updated = PersistentMapping(attempt)
    updated.update(state='paid', ref=ref, verified_at=timestamp)
    ledger['references'][ref_key] = key
    ledger['attempts'][key] = updated
    obj.payment_paid = True
    obj.payment_ref = ref
    obj.payment_authority = authority
    obj.payment_date = timestamp
    obj.reindexObject()
    return True
