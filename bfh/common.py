"""
Common functions for BFH

"""
from __future__ import absolute_import

from datetime import timedelta, tzinfo

__all__ = [
    "NULLISH",
    "nullish",
    "utc",
]

NULLISH = (None, {}, [], tuple())


def nullish(value, implicit_nulls=True):
    if implicit_nulls:
        if hasattr(value, 'is_empty'):
            return value.is_empty

        return value in NULLISH

    return value is None


class UTC(tzinfo):

    OFFSET = timedelta(0)

    def utcoffset(self, dt):
        return self.OFFSET

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.OFFSET

utc = UTC()
