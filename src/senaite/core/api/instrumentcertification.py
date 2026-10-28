# -*- coding: utf-8 -*-
"""Read-only certificate status for display; does not change instrument eligibility."""
import math
from DateTime import DateTime
from ZODB.POSException import ConflictError


def _as_date(value):
    if not value:
        return None
    try:
        return value if isinstance(value, DateTime) else DateTime(value)
    except Exception:
        return None


def get_certificate_status(instrument, warning_days=30, now=None):
    now = now if now is not None else DateTime()
    result = {'status': 'unknown', 'certificate': None,
              'valid_from': None, 'valid_to': None, 'days': None}
    try:
        certificates = list(instrument.getCertifications() or [])
    except ConflictError:
        raise
    except Exception:
        return result
    if not certificates:
        result['status'] = 'none'
        return result
    parsed = []
    incomplete = False
    for certificate in certificates:
        try:
            start = _as_date(certificate.getValidFrom())
            end = _as_date(certificate.getValidTo())
        except ConflictError:
            raise
        except Exception:
            start = end = None
        if start is None or end is None or start > end:
            incomplete = True
            continue
        parsed.append((certificate, start, end))
    current = [row for row in parsed if row[1] <= now <= row[2]]
    if current:
        chosen = max(current, key=lambda row: row[2])
        status = 'due' if chosen[2] - now <= max(1, warning_days) else 'valid'
    elif incomplete:
        # Incomplete records do not prove that all certificates expired.
        return result
    else:
        expired = [row for row in parsed if row[2] < now]
        if expired:
            chosen = max(expired, key=lambda row: row[2])
            status = 'expired'
        else:
            chosen = min(parsed, key=lambda row: row[1])
            status = 'future'
    certificate, start, end = chosen
    result.update(status=status, certificate=certificate, valid_from=start,
                  valid_to=end, days=int(math.ceil(end - now)))
    return result
