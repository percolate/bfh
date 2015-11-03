"""
Interfaces for BFH

"""
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod, abstractproperty
from six import add_metaclass

from .common import dedunder

__all__ = [
    "FieldInterface",
    "MappingInterface",
    "SchemaInterface",
    "TransformationInterface",
]


@add_metaclass(ABCMeta)
class FieldInterface(object):
    """
    Descriptor that defines a field on a Schema class.

    """
    @abstractmethod
    def validate(self):
        """
        Validate the field.

        """

    @abstractmethod
    def serialize(self, value, implicit_nulls=True):
        """
        Serialize the field.

        """


@add_metaclass(ABCMeta)
class TransformationInterface(object):
    """
    Descriptor that defines a field transformation on a Mapping class.

    """
    @abstractmethod
    def function(self, whole_obj, *call_args, **kwargs):
        """
        The function that is called to transform a field.

        """


class HasFieldsMeta(ABCMeta):
    """
    Metaclass for classes that may have fields.

    """
    def __new__(metaclass, classname, bases, attributes, *args, **kwargs):
        new_class = super(HasFieldsMeta, metaclass).__new__(
            metaclass, classname, bases, attributes, *args, **kwargs
        )
        setattr(new_class, '_fields', {})
        setattr(new_class, '_field_names', [])
        for name in dir(new_class):
            attribute = getattr(new_class, name)
            if not isinstance(attribute,
                              (FieldInterface, TransformationInterface)):
                continue
            name = dedunder(name)
            new_class._fields[name] = attribute
            new_class._field_names.append(name)
            attribute.field_name = name
        return new_class


@add_metaclass(HasFieldsMeta)
class SchemaInterface(object):
    """
    Interface for a Schema class.

    """
    @abstractmethod
    def validate(self):
        """
        Validate the schema instance.

        """

    @abstractmethod
    def serialize(self, implicit_nulls=True):
        """
        Serialize the schema instance.

        """

    @abstractproperty
    def is_empty(self):
        """
        Is the schema instance empty?

        """


@add_metaclass(HasFieldsMeta)
class MappingInterface(object):
    """
    Interface for a Mapping class.

    """
    @property
    def source_schema(self):
        """
        Optionally declare the source schema for this mapping.

        """

    @property
    def target_schema(self):
        """
        Optionally declare the target schema for this mapping.

        """

    @abstractmethod
    def apply(self, blob):
        """
        Apply the mapping to an object.

        """
