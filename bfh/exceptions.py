"""
Exceptions for BFH

"""
from __future__ import absolute_import

__all__ = [
    "Invalid",
    "Missing",
]


class Invalid(TypeError):
    pass


class Missing(KeyError, AttributeError):
    pass
