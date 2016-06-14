"""
BFH: a library for mapping schemas to other schemas.

"""
from __future__ import absolute_import

from .common import nullish, dedunder
from .interfaces import SchemaInterface, MappingInterface

from . import exceptions
from . import fields
from . import transformations

from .version import __version__
assert __version__

__all__ = [
    "Schema",
    "Mapping",
    "exceptions",
    "fields",
    "transformations",
]


def _get_raw_value(value):
    """
    Helper to recurse within a schema structure

    """
    if isinstance(value, SchemaInterface):
        return value._raw

    elif isinstance(value, (list, tuple)):
        result = []
        for i in value:
            result.append(_get_raw_value(i))
        return result

    else:
        return value


class Schema(SchemaInterface):
    """
    A base class for defining your schemas:

    Declare the shape of an object you expect to handle.

    Just inherit this and add some fields::

        class Animal(Schema):
            name = UnicodeField()
            type = UnicodeField()
            legs = IntegerField()
            noise = UnicodeField()

    """
    def __init__(self, *args, **kwargs):
        """
        Args:
           *args: Pass a dictionary as a single positional argument and it will
           be transformed into kwargs.

           **kwargs: Values to assign to fields in the schema. Unknown names are ignored.
        """
        # when a dict is passed as positional argument, transform to kwargs
        if len(args) == 1 and isinstance(args[0], dict):
            return self.__init__(**dict(args[0], **kwargs))

        # stash raw kwargs for downstream
        self._raw_input = kwargs

        # init any subschemas
        for k, v in self._fields.items():
            if isinstance(v, fields.Subschema):
                setattr(self, k, v.subschema_class())

        # init values passed as kwargs
        for k, v in kwargs.items():
            if k.startswith("__"):
                k = k.strip("_")

            if k in self._field_names:
                setattr(self, k, v)

    def __setattr__(self, name, value):
        name = dedunder(name)
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        name = dedunder(name)
        return object.__getattribute__(self, name)

    def serialize(self, implicit_nulls=False):
        """
        Represent this schema as a dictionary.

        Handy for dumping to json or some other further serialization format,
        or splatting into an object constructor.

        Args:
            implicit_nulls (bool): drop any keys whose value is nullish

        Returns:
            dict
        """
        outd = {}
        for name in self._field_names:
            field = self._fields.get(name)
            value = getattr(self, name)
            if hasattr(field, "serialize"):
                value = field.serialize(value, implicit_nulls=implicit_nulls)

            if hasattr(value, "serialize"):
                value = value.serialize(implicit_nulls=implicit_nulls)

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
        for name in self._field_names:
            if not nullish(getattr(self, name)):
                return False
        return True

    @property
    def _raw(self):
        out = dict(**self._raw_input)
        for name in self._field_names:
            value = getattr(self, name)
            out[name] = _get_raw_value(value)

        return GenericSchema(**out)


class GenericSchema(SchemaInterface):
    """
    A generic schema to use when none is specified.

    """
    def __init__(self, **kwargs):
        """
        Args:
            kwargs (dict) - a blob from which to infer a schema
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, name):
        return self.__dict__.get(name)

    def _serialize_value(self, value, implicit_nulls=False):
        """
        Serialize a value, recursively descending through the object to make
        sure any nested objects are also serialized.

        """
        if hasattr(value, "serialize"):
            value = value.serialize(implicit_nulls=implicit_nulls)

        if isinstance(value, (list, tuple)):
            items = []
            for i in value:
                ser = self._serialize_value(
                    i, implicit_nulls=implicit_nulls)

                if not nullish(ser, implicit_nulls=implicit_nulls):
                    items.append(ser)

            value = items

        if implicit_nulls and nullish(
                value, implicit_nulls=implicit_nulls):
            return None
        return value

    def serialize(self, implicit_nulls=False):
        """
        Represent generic schema as a dictionary.

        Args:
            implicit_nulls (bool): drop any keys whose value is nullish

        Returns:
            dict
        """
        outd = {}
        for name, value in self.__dict__.items():
            value = self._serialize_value(value, implicit_nulls=implicit_nulls)
            if implicit_nulls and nullish(
                    value, implicit_nulls=implicit_nulls):
                pass
            else:
                outd[name] = value

        return outd

    def validate(self):
        """
        *shrug*

        """
        return True

    @property
    def is_empty(self):
        return all(nullish(v) for v in self.__dict__.values())

    @property
    def _raw(self):
        out = dict(**self.__dict__)
        for key, val in out.items():
            out[key] = _get_raw_value(val)

        return GenericSchema(**out)


class Mapping(MappingInterface):
    """
    A base class for defining your mappings:

    Declare a transformation from one shape to another shape.

    Just inherit this and add some fields::

        class DogToAnimal(Mapping):
            source_schema = Dog
            target_schema = Animal

            name = Get('dogname')
            type = Const('dog')
            legs = Const(4)
            noise = Const('woof!')

    The action happens when you get an instance of your mapping::

        dog_to_animal_map = DogToAnimal()

    Then apply it to an object. You get a Schema instance::

        my_animal = dog_to_animal_map.apply(my_dog)
        type(my_animal)
        # __main__.Animal

    ... which is full of values::

        my_animal.serialize()
        # {"name": "Fido", "type": "dog", "legs": 4, "noise": "woof!}

    """
    def apply(self, blob):
        """
        Take the mapping and push a blob through it.

        Args:
            blob (dict or Schema): the thing to transform

        Returns:
            instance of `self.target_schema` (if declared) or GenericSchema
        """
        if self.source_schema is None:
            loaded_source = blob
        elif isinstance(blob, self.source_schema):
            loaded_source = blob
        else:
            loaded_source = self.source_schema(**blob or {})

        all_attrs = self._fields.keys()
        target_dict = {}
        for attr_name in all_attrs:
            transform = self._fields[attr_name]
            result = transform(loaded_source)
            target_dict[attr_name] = result

        if self.target_schema is None:
            return GenericSchema(**target_dict)

        return self.target_schema(**target_dict)
