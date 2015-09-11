"""
Exceptions for BFH

"""
from __future__ import absolute_import

__all__ = [
    "Invalid",
    "Missing",
]


class Invalid(TypeError):
    """
    The value in this field is not valid.

    """


class Missing(KeyError, AttributeError):
    """
    A thing that should be here... is not.

    """
