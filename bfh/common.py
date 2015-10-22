"""
Utility functions for BFH

"""
from __future__ import absolute_import

import re
from datetime import timedelta, tzinfo

__all__ = [
    "NULLISH",
    "nullish",
    "utc",
]

"""
Types that are falsey, but not False itself.

"""
NULLISH = (None, {}, [], tuple())


def nullish(value, implicit_nulls=True):
    """
    Kwargs:
        implicit_nulls (bool): accept empty containers as well as None
    """
    if implicit_nulls:
        if hasattr(value, 'is_empty'):
            return value.is_empty

        return value in NULLISH

    return value is None


class UTC(tzinfo):
    """
    UTC tzinfo.

    Why isn't this in the standard library?
    """
    OFFSET = timedelta(0)

    def utcoffset(self, dt):
        return self.OFFSET

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.OFFSET

utc = UTC()


DUNDER_MATCH = re.compile(r'_.+?__')


def dedunder(name):
    if DUNDER_MATCH.match(name):
        return DUNDER_MATCH.sub('', name)
    return name
