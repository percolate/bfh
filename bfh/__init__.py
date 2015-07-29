"""
BFH: a library for mapping schemas to other schemas.

"""
from __future__ import absolute_import

from .common import nullish
from .interfaces import SchemaInterface, MappingInterface

from . import fields
from . import transformations

__all__ = [
    "Schema",
    "Mapping",
    "fields",
    "transformations",
]


class Schema(SchemaInterface):
    """
    A base class for defining your schemas:

    Declare the shape of an object you expect to handle.

    Just inherit this and add some fields:

        class Animal(Schema):
            name = UnicodeField()
            type = UnicodeField()
            legs = IntegerField()
            noise = UnicodeField()

    """
    def __init__(self, *args, **kwargs):
        """
        Args:
           Pass a dictionary a single positional argument and it will be
           tranformed into kwargs.

        Kwargs:
           Values to assign to fields in the schema. Unknown names are ignored.
        """
        # when a dict is passed as positional argument, transform to kwargs
        if len(args) == 1 and isinstance(args[0], dict):
            return self.__init__(**dict(args[0], **kwargs))

        # stash raw kwargs for downstream
        # since this is set in metaclass, hidden from __dict__
        self._raw_input.update(kwargs)

        # init any subschemas
        for k, v in self._fields.items():
            if isinstance(v, fields.Subschema):
                setattr(self, k, v.subschema_class())

        # init values passed as kwargs
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def serialize(self, implicit_nulls=True):
        """
        Represent this schema as a dictionary.

        Kwargs:
            implicit_nulls (Bool) - drop any keys whose value is nullish

        Returns:
            dict
        """
        outd = {}
        for name in self._field_names:
            value = self.__dict__.get(name)
            field = self._fields.get(name)
            if hasattr(value, "serialize"):
                value = value.serialize(implicit_nulls=implicit_nulls)

            if hasattr(field, "serialize"):
                value = field.serialize(value, implicit_nulls=implicit_nulls)

            if implicit_nulls and nullish(value,
                                          implicit_nulls=implicit_nulls):
                pass
            else:
                outd[name] = value

        return outd

    def validate(self):
        """
        Validate the values in the schema.

        Returns:
            True

        Raises:
            Invalid
        """
        return all([v.validate(getattr(self, k))
                    for k, v in self._fields.items()])

    @property
    def is_empty(self):
        return all(nullish(v) for v in self.__dict__.values())


class GenericSchema(Schema):
    """
    A generic schema to use when none is specified.

    """
    def __init__(self, as_dict=None):
        """
        Args:
            as_dict (dict) - a blob from which to infer a schema
        """
        self.__dict__ = as_dict or {}
        self._field_names = as_dict.keys() if as_dict else []

    def __getattr__(self, name):
        if name not in self._field_names:
            return None
        return self.__dict__[name]

    def validate(self):
        """
        *shrug*

        """
        return True


class Mapping(MappingInterface):
    """
    A base class for defining your mappings:

    Declare a transformation from one shape to another shape.

    Just inherit this and add some fields:

        class DogToAnimal(Mapping):
            source_schema = Dog
            target_schema = Animal

            name = Get('dogname')
            type = Const('dog')
            legs = Const(4)
            noise = Const('woof!')

    """
    def apply(self, blob):
        """
        Take the mapping and push a blob through it.

        Args:
            blob (dict or Schema) - the thing to transform

        Returns:
            instance of `self.target_schema` if declared, or GenericSchema
        """
        if self.source_schema is None:
            loaded_source = blob
        elif isinstance(blob, self.source_schema):
            loaded_source = blob
        else:
            loaded_source = self.source_schema(**blob)

        all_attrs = self._fields.keys()
        target_dict = {}
        for attr_name in all_attrs:
            transform = getattr(self, attr_name)
            result = transform(loaded_source)
            target_dict[attr_name] = result

        if self.target_schema is None:
            return GenericSchema(target_dict)

        return self.target_schema(**target_dict)
