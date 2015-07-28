"""
Interfaces for BFH

"""
from __future__ import absolute_import

from abc import ABCMeta, abstractmethod, abstractproperty

__all__ = [
    "FieldInterface",
    "MappingInterface",
    "SchemaInterface",
    "TransformationInterface",
]


class FieldInterface(object):
    """
    Descriptor that defines a field on a Schema class.

    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def validate(self):
        """
        Validate the field.

        """

    @abstractmethod
    def serialize(self, value):
        """
        Serialize the field.

        """


class TransformationInterface(object):
    """
    Descriptor that defines a field transformation on a Mapping class.

    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def function(self, whole_obj, *call_args, **kwargs):
        """
        The function that is called to transform a field.

        """


class HasFieldsMeta(ABCMeta):
    """
    Metaclass for classes that may have fields.

    """
    def __new__(metaclass, name, bases, attributes, *args, **kwargs):
        new_class = super(HasFieldsMeta, metaclass).__new__(
            metaclass, name, bases, attributes, *args, **kwargs
        )
        setattr(new_class, '_fields', {})
        setattr(new_class, '_field_names', [])
        setattr(new_class, '_raw_input', {})
        for name in dir(new_class):
            attribute = getattr(new_class, name)
            if not isinstance(attribute,
                              (FieldInterface, TransformationInterface)):
                continue
            new_class._fields[name] = attribute
            new_class._field_names.append(name)
            attribute.field_name = name
        return new_class


class SchemaInterface(object):
    """
    Interface for a Schema class.

    """
    __metaclass__ = HasFieldsMeta

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


class MappingInterface(object):
    """
    Interface for a mapping class.

    """
    __metaclass__ = HasFieldsMeta

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
        Apply the mapping to a blob.

        """
